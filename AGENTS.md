# AGENTS.md — AI 编码代理工作指南

本文件供 AI 编码代理（Claude Code / Cursor / Codex 等）在本仓库工作时参考。

## 项目概览

企业智能知识库：FastAPI + LangGraph(Function Calling) + RAG(Chroma + BGE 嵌入) 后端，Vue 3 前端。
- 后端：`backend/`，端口 8001，入口 `app/main.py`，venv 在 `backend/venv/`
- 前端：`fronted/`，dev 端口 5174（占用时 Vite 自动顺延），纯手写 CSS 无 UI 库
- 详细教程：`docs/TUTORIAL.md`

## 常用命令

```bash
# 后端（在 backend/ 下，用 venv）
./venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8001   # Windows
# 前端（在 fronted/ 下）
npm run dev
# 依赖安装
./venv/Scripts/pip install -r requirements.txt
npm install
```

注意：本机 8000/5173 端口被另一个项目（booking-agent-new）占用，本项目的服务必须用 8001/5174+。

## 架构约定

- **分层**：`routers/`（接口）→ `services/`（业务/rag）→ `models/`（ORM）；工具在 `agent/tools.py`，提示词集中在 `app/prompts.py`，不要散落硬编码
- **统一响应**：所有接口返回 `{code, message, data}`（`utils/response.py`），错误抛 HTTPException 由 main.py 全局处理器转换
- **认证**：接口按需挂 `Depends(get_current_user / get_current_editor / get_current_admin)`；角色 user/editor/admin，注册只能注册前两种
- **向量化时机**：文章 publish/update/delete 时同步 Chroma（`routers/articles.py` 的 `_sync_vector`），数据库是事实来源，向量库只是索引
- **SSE 事件协议**：`chunk`（增量文本）/ `tool`（工具调用状态）/ `sources`（引用来源）/ `done`（结束）/ `error`

## 关键约束（改动前必读）

1. **引用来源机制**：上下文块编号化（`prompts.build_context_block`），来源 = 从回答文本解析 `[n]`，禁止改动为"返回全部检索命中"
2. **不要用 contextvars 在工具内收集状态**：LangGraph 线程池执行同步工具，子线程写不可回传（已踩坑）
3. **LangGraph 多路流**：`stream_mode=["messages","updates"]` 时 messages 事件的数据是 `(chunk, meta)` 元组，必须拆包
4. **前端请求**：统一走 `api/request.js` 的 `apiFetch`/`uploadFile`/`streamChat`，不要绕过；API_BASE 在该文件顶部（8001）
5. **敏感文件不进 git**：`.env`、`*.db`、`chroma_data/`、`venv/` 已在 .gitignore，新增同类文件先补 ignore
6. **响应模型类型**：Pydantic 响应 schema 的字段类型要与 ORM 实际类型一致（datetime 别写成 str，会 500 且 CORS 头丢失，报错有迷惑性）
7. **扫描版 PDF**：文本提取为空时报错拒绝入库，不允许静默保存空文章

## Git 约定

- 提交信息用中文一句话，说清楚"为什么"而不只是"改了什么"
- **日常改动只本地 commit，不 push**：功能做完或告一段落时 commit 一次即可，让改动成组地留在本地
- **push 仅在所有者明确说"推送/push"时执行**，且此时把本地积压的提交一次性推上去
- 原因：边改边推会在远端留下大量半成品提交，后续继续修改时本地与远端来回分叉，合并和回退都很麻烦；本地成组的提交既好审阅也好整体回滚
