import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agent.graph import kb_graph
from app.agent.tools import sources_collector
from app.database import get_db, SessionLocal
from app.models.chat import ChatSession, ChatMessage
from app.models.user import User
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
        sources = []
        sources_collector.set(sources)
        config = {"configurable": {"thread_id": session_id, "user_id": current_user.id}}
        answer_parts = []
        try:
            from langchain_core.messages import AIMessageChunk, HumanMessage
            for chunk, meta in kb_graph.stream(
                {"messages": [HumanMessage(content=payload.question)]},
                config=config,
                stream_mode="messages",
            ):
                if isinstance(chunk, AIMessageChunk) and chunk.content and meta.get("langgraph_node") == "agent":
                    text = chunk.content if isinstance(chunk.content, str) else "".join(
                        p.get("text", "") for p in chunk.content if isinstance(p, dict))
                    if text:
                        answer_parts.append(text)
                        yield f"data: {json.dumps({'type': 'chunk', 'content': text}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'sources', 'items': sources}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

            db = SessionLocal()
            try:
                _save_message(db, session_id, "assistant", "".join(answer_parts), sources)
            finally:
                db.close()
        except Exception as e:
            logger.exception("问答流异常: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'message': 'AI 服务异常，请稍后重试（请检查 DEEPSEEK_API_KEY / SILICONFLOW_API_KEY 配置）'}, ensure_ascii=False)}\n\n"

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
def all_records(db: Session = Depends(get_db), _: User = Depends(get_current_editor)):
    sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).limit(100).all()
    return success(data=[{
        "session_id": s.id,
        "title": s.title,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "message_count": len(s.messages),
    } for s in sessions])
