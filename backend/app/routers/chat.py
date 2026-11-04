import json
import logging
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agent.graph import kb_graph
from app.models.article import Article
from app.database import get_db, SessionLocal
from app.models.chat import ChatSession, ChatMessage
from app.models.user import User
from app.prompts import build_context_block
from app.services import rag
from app.utils.deps import get_current_user, get_current_editor
from app.utils.response import success

logger = logging.getLogger("app")
router = APIRouter(prefix="/api/chat", tags=["AI 问答"])


class ChatRequest(BaseModel):
    question: str
    session_id: str = ""


def _save_message(db: Session, session_id: str, role: str, content: str, sources: list | None = None):
    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        sources=json.dumps(sources, ensure_ascii=False) if sources else None,
    )
    db.add(message)
    db.commit()


@router.post("/ask", summary="AI 问答（SSE 流式返回）")
def ask(payload: ChatRequest, current_user: User = Depends(get_current_user)):
    """LangGraph 智能体流式问答。

    SSE 事件：`data: {"type": "chunk", "content": ...}` 增量文本；
    `data: {"type": "sources", "items": [...]}` 引用来源；
    `data: {"type": "done"}` 结束。
    """
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")

    session_id = payload.session_id or uuid.uuid4().hex
    db = SessionLocal()
    try:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session is None:
            session = ChatSession(id=session_id, user_id=current_user.id,
                                  title=payload.question[:60])
            db.add(session)
            db.commit()
        elif session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权访问该会话")
        _save_message(db, session_id, "user", payload.question)
    finally:
        db.close()

    def event_stream():
        # 强制预检索（Context Engineering）：每个问题先静默检索一次，
        # 结果注入上下文，模型只需决定"用不用"，不依赖它决定"查不查"
        try:
            hits = rag.search(payload.question)
        except Exception:
            logger.exception("预检索失败（Embedding 服务不可用？），降级为纯对话")
            hits = []
        # 来源收集：按文章去重，编号即列表序号（1-based）。
        # 预检索占据 [1..n]；Agent 工具命中的新文章从工具输出解析追加（编号顺延）
        sources = []
        seen_titles = set()
        for h in hits:
            if h["title"] in seen_titles:
                continue
            seen_titles.add(h["title"])
            sources.append({
                "article_id": h["article_id"],
                "title": h["title"],
                "snippet": h["text"][:120],
            })
        context_message = (
            SystemMessage(content=build_context_block(hits, start_index=1)) if hits else None
        )
        config = {"configurable": {"thread_id": session_id, "user_id": current_user.id}}
        answer_parts = []
        try:
            input_messages = [HumanMessage(content=payload.question)]
            if context_message:
                input_messages.append(context_message)
            for mode, data in kb_graph.stream(
                {"messages": input_messages},
                config=config,
                stream_mode=["messages", "updates"],
            ):
                if mode == "messages":
                    chunk, meta = data
                    if isinstance(chunk, AIMessageChunk) and chunk.content:
                        text = chunk.content if isinstance(chunk.content, str) else "".join(
                            p.get("text", "") for p in chunk.content if isinstance(p, dict))
                        if text:
                            answer_parts.append(text)
                            yield f"data: {json.dumps({'type': 'chunk', 'content': text}, ensure_ascii=False)}\n\n"
                    continue
                # mode == "updates"：广播工具调用状态，并从工具输出解析新命中的文章
                for node_name, update in data.items():
                    if node_name != "tools":
                        continue
                    for msg in update.get("messages", []):
                        if not isinstance(msg, ToolMessage):
                            continue
                        yield f"data: {json.dumps({'type': 'tool', 'name': msg.name}, ensure_ascii=False)}\n\n"
                        content = msg.content if isinstance(msg.content, str) else ""
                        for _n, title in re.findall(r"\[(\d+)\] 《(.+?)》", content):
                            if title not in seen_titles:
                                seen_titles.add(title)
                                sources.append({"article_id": None, "title": title, "snippet": ""})

            answer = "".join(answer_parts)
            # 把解析出的标题补全为 article_id（工具输出只有标题）
            if any(s["article_id"] is None for s in sources):
                db = SessionLocal()
                try:
                    for s in sources:
                        if s["article_id"] is None:
                            row = db.query(Article).filter(Article.title == s["title"]).first()
                            s["article_id"] = row.id if row else None
                finally:
                    db.close()
            sources = [s for s in sources if s["article_id"] is not None]

            # 只保留 LLM 实际引用的来源：从回答解析 [n]，无效编号回退为全部命中
            total = len(sources)
            cited = {int(m) for m in re.findall(r"\[(\d{1,2})\]", answer) if int(m) <= total}
            used_sources = (
                [s for i, s in enumerate(sources, 1) if i in cited] if cited else list(sources)
            )
            yield f"data: {json.dumps({'type': 'sources', 'items': used_sources}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

            db = SessionLocal()
            try:
                _save_message(db, session_id, "assistant", answer, used_sources)
            finally:
                db.close()
        except Exception as e:
            logger.exception("问答流异常: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'message': 'AI 服务异常，请稍后重试（请检查 GLM_API_KEY / SILICONFLOW_API_KEY 配置）'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/sessions", summary="我的会话列表")
def my_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    return success(data=[{
        "id": s.id,
        "title": s.title,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "message_count": len(s.messages),
    } for s in sessions])


@router.get("/sessions/{session_id}", summary="会话消息详情")
def session_messages(session_id: str, current_user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.user_id != current_user.id and current_user.role not in ("admin", "editor"):
        raise HTTPException(status_code=403, detail="无权访问该会话")
    return success(data=[{
        "role": m.role,
        "content": m.content,
        "sources": m.sources_list,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    } for m in session.messages])


@router.delete("/sessions/{session_id}", summary="删除我的会话")
def delete_session(session_id: str, current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除该会话")
    db.delete(session)
    db.commit()
    return success(message="删除成功")


@router.get("/records", summary="问答记录查看（编辑/管理员，用于运营分析）")
def all_records(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_editor),
):
    query = db.query(ChatSession).order_by(ChatSession.created_at.desc())
    total = query.count()
    sessions = query.offset((page - 1) * page_size).limit(page_size).all()
    return success(data={
        "total": total,
        "items": [{
            "session_id": s.id,
            "title": s.title,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "message_count": len(s.messages),
        } for s in sessions],
    })
