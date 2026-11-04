# 从零实现企业智能知识库：新手一步步教程

> 本教程还原 kb-assistant-agent 的完整搭建过程。跟着做完，你会独立实现一个「RAG + AI Agent + 前后端分离」的完整项目。每一步都有：目标 → 原理 → 代码 → 验证方式。
>
> 建议配套阅读源码，教程中的文件路径都对应仓库里的真实文件。

## 目录

- [第 0 步：准备知识与环境](#第-0-步准备知识与环境)
- [第 1 步：项目骨架与配置读取](#第-1-步项目骨架与配置读取)
- [第 2 步：数据库与第一个模型](#第-2-步数据库与第一个模型)
- [第 3 步：统一响应与 JWT 认证](#第-3-步统一响应与-jwt-认证)
- [第 4 步：用户注册登录接口](#第-4-步用户注册登录接口)
- [第 5 步：文章与分类 CRUD（权限体系）](#第-5-步文章与分类-crud权限体系)
- [第 6 步：理解 RAG——先跑通最小 Demo](#第-6-步理解-rag先跑通最小-demo)
- [第 7 步：结构感知切片](#第-7-步结构感知切片)
- [第 8 步：向量库入库与检索服务](#第-8-步向量库入库与检索服务)
- [第 9 步：Prompt Engineering 与上下文拼装](#第-9-步prompt-engineering-与上下文拼装)
- [第 10 步：LangGraph 工作流 + Function Calling](#第-10-步langgraph-工作流--function-calling)
- [第 11 步：SSE 流式问答接口](#第-11-步sse-流式问答接口)
- [第 12 步：前端——请求封装与路由守卫](#第-12-步前端请求封装与路由守卫)
- [第 13 步：前端聊天页（Markdown 渲染 + 状态提示）](#第-13-步前端聊天页markdown-渲染--状态提示)
- [第 14 步：文档导入与管理端页面](#第-14-步文档导入与管理端页面)
- [第 15 步：Docker 部署](#第-15-步docker-部署)
- [常见坑清单](#常见坑清单)

---

## 第 0 步：准备知识与环境

**需要会的基础**：Python 基本语法、HTTP 请求响应的概念、一点 SQL。不需要会 Vue 或 LangChain，用到时会讲。

**安装**：

| 工具 | 版本要求 | 用途 |
|---|---|---|
| Python | ≥ 3.10 | 后端 |
| Node.js | ≥ 18 | 前端构建 |
| Git | 任意 | 版本管理 |
| VS Code / Cursor | - | 编辑器（用 Cursor/Claude Code 等 AI 编码工具效率更高） |

**两个 API Key**（本项目唯一的外部依赖）：

1. **智谱 GLM**（https://open.bigmodel.cn）：对话生成模型，兼容 OpenAI 接口协议
2. **硅基流动**（https://siliconflow.cn）：BGE-m3 免费嵌入模型，用于向量化

> 为什么嵌入和对话用两家？嵌入模型只要"把文字变成向量"，免费额度就够用；对话模型才需要强推理能力。

**验证**：`python --version`、`node -v`、`git --version` 都能输出版本号即可。

---

## 第 1 步：项目骨架与配置读取

**目标**：搭出目录结构，让 `.env` 配置能被代码读到。

```
kb-assistant-agent/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py      # 本步
│   │   ├── database.py    # 第 2 步
│   │   ├── models/  schemas/  routers/  services/  agent/  utils/
│   │   └── main.py        # 第 4 步
│   ├── requirements.txt
│   └── .env.example       # 模板，真实 .env 不进 git
└── fronted/
```

`backend/app/config.py` 的核心思路：**用 `os.getenv` 读环境变量 + 给默认值**，不用 pydantic-settings 也完全够：

```python
import os
from dotenv import load_dotenv

load_dotenv()  # 把 .env 文件内容加载进环境变量

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./kb.db")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-secret")
    DEEPSEEK_API_KEY: str = os.getenv("GLM_API_KEY", "")
    ...

settings = Settings()  # 全局单例，其他文件 from app.config import settings
```

`.gitignore` 必须从一开始就写好（`.env`、`venv/`、`__pycache__/`、`*.db`、`node_modules/`、`chroma_data/`）——密钥和数据库永远不进仓库。

**验证**：`python -c "from app.config import settings; print(settings.DATABASE_URL)"` 能打印出默认值。

---

## 第 2 步：数据库与第一个模型

**目标**：用 SQLAlchemy 定义表结构，自动建表。

选 **SQLite**（零配置，一个文件就是数据库）起步，代码里留好换 MySQL 的口子（连接串改一行即可）。

`app/database.py`，三样东西是 SQLAlchemy 的固定套路：

```python
engine = create_engine(url, connect_args={"check_same_thread": False})  # 引擎
SessionLocal = sessionmaker(bind=engine)   # 会话工厂
Base = declarative_base()                  # 所有模型的基类

def get_db():                              # FastAPI 依赖：每个请求一个会话
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**模型 = 一张表的 Python 描述**。用户表（`models/user.py`）：

```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)   # 永远不存明文密码
    name = Column(String(50), nullable=True)
    role = Column(String(20), default="user")   # user/editor/admin
    created_at = Column(DateTime, default=datetime.utcnow)
```

设计经验：
- **role 用字符串不用 Enum**：加新角色不用改表结构
- 文章表（`models/article.py`）关键设计：`status`（draft/published，**只有发布才进向量库**）、`editor_id`（谁写的）、`content_hash`（内容指纹，判断要不要重新向量化）
- 会话表 `chat_sessions` / 消息表 `chat_messages` 一对多，消息里的 `sources` 存 JSON 字符串（引用来源）

**验证**：`Base.metadata.create_all(engine)` 后目录里出现 `kb.db`，用 DB 工具打开能看到表。

---

## 第 3 步：统一响应与 JWT 认证

**目标**：所有接口返回同一格式；登录后发令牌，后续请求凭令牌识别身份。

**统一响应**（`utils/response.py`）——前端只需要写一套处理逻辑：

```python
def success(data=None, message="success", code=200):
    return {"code": code, "message": message, "data": data}
```

**JWT 是什么**：登录成功后服务器签发一个含用户名的加密字符串（token），之后每次请求放在 `Authorization: Bearer <token>` 头里，服务器验签就知道你是谁——不需要存 session。

`utils/security.py` 三个函数，bcrypt 加密密码、python-jose 签发/校验 token：

```python
def create_access_token(data: dict) -> str:
    to_encode = {"sub": username, "role": role, "exp": 过期时间}
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

def decode_token(token) -> dict | None:   # 校验失败返回 None
```

`utils/deps.py` 是 FastAPI **依赖注入**的精髓——把"当前用户是谁"变成一个可复用的参数：

```python
def get_current_user(token = Depends(oauth2_scheme), db = Depends(get_db)) -> User:
    payload = decode_token(token)
    ...  # 查库返回 User，失败抛 401

def get_current_editor(user = Depends(get_current_user)) -> User:
    if user.role not in ("admin", "editor"):
        raise HTTPException(403, "需要知识编辑权限")
    return user   # 依赖可以套依赖，层层叠加权限
```

之后任何接口只要加一个参数 `current_user: User = Depends(get_current_user)` 就自动要求登录。

**验证**：Swagger `/docs` 里调 `/api/auth/token` 拿到 token，Authorize 填入后受保护接口能通。

---

## 第 4 步：用户注册登录接口

**目标**：写出第一组完整接口，理解 FastAPI 的路由写法。

`routers/auth.py` 的模式就是全项目所有路由的模式：

```python
router = APIRouter(prefix="/api/auth", tags=["认证"])

@router.post("/register")
def register(payload: UserRegister, db: Session = Depends(get_db)):
    # 1. 校验（用户名/邮箱重复）
    # 2. 密码 bcrypt 加密后入库
    # 3. return success(data=UserResponse.model_validate(user).model_dump())
```

**Pydantic schema**（`schemas/user.py`）负责"请求长什么样"：

```python
class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr          # 自动校验邮箱格式
    password: str = Field(min_length=6)
    role: Literal["user", "editor"] = "user"   # 不允许注册成 admin
```

**main.py 的 lifespan** 是启动钩子：建表 → 创建默认 admin/editor 账号 → 写入种子文章。全局异常处理器把所有错误也转成统一格式：

```python
@app.exception_handler(HTTPException)
async def handler(request, exc):
    return JSONResponse(status_code=exc.status_code,
                        content={"code": exc.status_code, "message": exc.detail, "data": None})
```

**验证**：注册 → 登录 → 带 token 访问 `/api/users/me` 返回自己的信息。

---

## 第 5 步：文章与分类 CRUD（权限体系）

**目标**：实现核心业务表的管理接口，掌握分页搜索和对象级权限。

文章接口（`routers/articles.py`）注意四点：

```python
@router.get("")
def list_articles(page: int = Query(1, ge=1), page_size: int = Query(10, le=100),
                  search: str = Query(""), db = Depends(get_db),
                  _: User = Depends(get_current_editor)):      # 管理接口要权限
    query = db.query(Article)
    if search:
        query = query.filter(Article.title.ilike(f"%{search}%"))  # 模糊搜索
    total = query.count()
    items = query.offset((page-1)*page_size).limit(page_size).all()  # 分页 = offset/limit
    return success(data={"total": total, "items": [...]})
```

1. **列表接口返回 `total + items`**，前端分页组件直接用
2. **发布接口独立成 `POST /{id}/publish`**，语义比"改 status 字段"清晰，且发布时触发向量化（第 8 步）
3. **public 接口与管理接口分开**：`/api/articles/public` 所有登录用户能看已发布文章，管理 CRUD 要 editor 权限
4. Pydantic 响应模型用 `ConfigDict(from_attributes=True)` 直接从 ORM 对象转换，**列表和详情用不同 schema**（列表不带大字段 content）

**验证**：创建分类 → 新建草稿 → 发布 → 公开列表能看到。

---

## 第 6 步：理解 RAG——先跑通最小 Demo

**目标**：在写服务代码前，先用 10 行代码理解 RAG 全流程。

RAG（检索增强生成）本质三句话：

1. **离线**：把知识切成片段，每段算一个向量（一串浮点数，代表语义），存进向量库
2. **在线**：用户提问 → 问题也算向量 → 找"向量距离最近"的几个片段
3. **生成**：把片段塞进提示词，让 LLM"根据以下资料回答"

最小 Demo（先 `pip install openai chromadb`）：

```python
from openai import OpenAI
import chromadb

client = OpenAI(api_key="硅基流动key", base_url="https://api.siliconflow.cn/v1")
col = chromadb.PersistentClient(path="./demo_chroma").get_or_create_collection("demo")

# 离线入库
docs = ["年假满1年5天满3年10天", "迟到每月前3次不扣款"]
col.add(ids=["1","2"], documents=docs,
        embeddings=[client.embeddings.create(model="BAAI/bge-m3", input=[d]).data[0].embedding for d in docs])

# 在线检索
q = client.embeddings.create(model="BAAI/bge-m3", input=["年假几天"]).data[0].embedding
print(col.query(query_embeddings=[q], n_results=1))  # 命中"年假满1年5天..."
```

理解了"**向量相似 = 语义相似**"，后面全是工程化。

---

## 第 7 步：结构感知切片

**目标**：把"整篇存一条"升级为聪明的切分（`services/rag.py` 的 `chunk_text`）。

为什么不能整篇一条：向量会"稀释"主题，检索不准；为什么不固定 500 字硬切：会把句子拦腰截断，语义残缺。所以**优先用文档自带的结构**：

```
标题层级(# / ##)  →  章节是硬边界，跨章节零重叠
段落边界          →  贪心装填到 500 字，天然切分点，零重叠
单段超长          →  按句子边界(。！？；)细分，此时才留 ~15% 重叠
```

实现要点（`chunk_text` 返回 `[{text, section}]`）：

```python
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")      # 识别 Markdown 标题
_SENTENCE_RE = re.compile(r"(?<=[。！？!?；;\n])")  # 句子边界切分

# 1. 扫描行，遇标题更新章节路径（如 "产品手册 > 安装指南"）
# 2. 章节内段落贪心装填：装得下就并入当前块，装不下先定稿当前块
# 3. 超长块递归细分到句子级，滑窗重叠取 chunk_size 的 15%
```

另外两个提升检索命中的细节：
- **每块开头拼上文章标题和章节路径**再向量化——"第一步下载安装包"这种孤立片段也带着"它在讲安装"的信息
- **重叠要克制**：重叠过大→近重复切片挤占 top-K 名额→模型看到同一段话的多个变体

**验证**：拿一篇带 `##` 的 Markdown 调用 `chunk_text`，打印每块的 section 和长度。

---

## 第 8 步：向量库入库与检索服务

**目标**：封装成可复用的服务（`services/rag.py`），并挂到文章发布流程上。

```python
def upsert_article(article_id, title, content, category, tags) -> int:
    col.delete(where={"article_id": article_id})    # 先删旧块（文章改过）
    chunks = chunk_text(content, title=title)
    embeddings = embed_texts([c["text"] for c in chunks])
    col.add(ids=..., documents=..., embeddings=embeddings,
            metadatas=[{"article_id":..., "title":..., "section":..., "chunk_index":...} ...])
```

**元数据是切片的身份证**：检索命中后能溯源到文章；引用展示按文章去重就靠它。

检索加**相关性阈值**（重要，防幻觉的第一道闸）：

```python
def search(query, top_k=4):
    result = col.query(query_embeddings=[_embed_query(query)], n_results=top_k)
    hits = [...]
    return [h for h in hits if h["distance"] <= MAX_DISTANCE]  # 距离超过 0.75 的丢弃
```

最后接线：`_sync_vector(article)` —— 发布/更新时 upsert，撤销发布/删除时从向量库移除。**数据库永远是事实来源，向量库只是它的索引**。

**验证**：发布一篇文章 → `search("相关问题")` 能命中且带 section。

---

## 第 9 步：Prompt Engineering 与上下文拼装

**目标**：写好系统提示词（`prompts.py`），让模型"只依据资料回答"。

防幻觉提示词的四个要素：

```python
SYSTEM_PROMPT = """你是公司知识库助手「小知」...
1. 涉及公司内部知识的问题，必须先调用工具检索知识库，再基于检索结果回答，禁止凭空编造。
2. 若参考知识不足以回答，明确说明"知识库中暂无相关内容"，不要猜测。   ← 给模型"承认不知道"的出口
3. 回答末尾用「来源：」列出引用的文章标题。                          ← 强制溯源
5. 闲聊或无关问题，直接回应，不必调用工具。                          ← 区分场景
"""
```

**上下文拼装**（Context Engineering）也是函数，不是散落的字符串拼接：

```python
def build_context_block(hits):
    # [1] 《年假与请假流程》（分类：公司制度，章节：年假天数）
    # <切片内容>
    # 每片带编号和元信息，模型引用时"有据可查"
```

**验证**：不接 Agent，直接 `llm.invoke([SystemMessage(SYSTEM_PROMPT), Human("参考知识... 问题...")])` 看回答是否老老实实引用资料。

---

## 第 10 步：LangGraph 工作流 + Function Calling

**目标**：让模型自己决定"要不要查库、要不要看全文"（`agent/` 目录）。

**Function Calling**：你告诉模型有哪些工具（名字 + 描述 + 参数 schema），模型在对话中输出"我要调 search_knowledge_base，参数是..."，由**你的代码**执行后把结果喂回去。工具的 docstring 就是给模型看的说明书，要写清楚"什么情况下该调我"：

```python
@tool
def search_knowledge_base(query: str, top_k: int = 4) -> str:
    """在公司知识库中进行语义检索。凡涉及公司制度、流程、产品等内部知识的问题，必须先调用本工具。"""
    hits = rag.search(query, top_k)
    _record_sources(hits)          # 顺手把命中记进 contextvars，回答完返回给前端做引用
    return build_context_block(hits)
```

**LangGraph 把"模型↔工具循环"画成图**（`agent/graph.py`）：

```python
graph = StateGraph(AgentState)               # 状态 = messages 列表
graph.add_node("agent", agent_node)          # 节点：调 LLM
graph.add_node("tools", ToolNode(ALL_TOOLS)) # 节点：执行工具
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", route_after_agent, ["tools", END])
# route_after_agent: 有 tool_calls → tools；没有 → END
graph.add_edge("tools", "agent")             # 工具结果喂回模型，循环
kb_graph = graph.compile(checkpointer=MemorySaver())
```

这就是 **ReAct 模式**：Reason（模型思考）→ Act（调工具）→ 再 Reason → ... 直到模型不再要求工具、直接给出答案。

多轮记忆靠 **checkpointer + thread_id**：同一个 `thread_id` 的对话历史自动延续，前端传会话 ID 即可。

**验证**：`kb_graph.invoke({"messages": [HumanMessage("你好")]})` 闲聊不走工具；`"年假几天"` 会看到 tool_calls。

---

## 第 11 步：SSE 流式问答接口

**目标**：回答像打字机一样逐字出现（`routers/chat.py`）。

**SSE（Server-Sent Events）**比 WebSocket 简单：普通 HTTP 响应，`Content-Type: text/event-stream`，服务器持续 `yield` 文本。

三个关键实现：

```python
def event_stream():
    hits = rag.search(question)          # ① 强制预检索：每个问题先查一次，
    sources_collector.set(sources)       #    结果注入上下文，不赌模型会不会自己查
    input_messages = [HumanMessage(question), SystemMessage(build_context_block(hits))]
    for mode, data in kb_graph.stream(..., stream_mode=["messages", "updates"]):
        if mode == "messages":                       # ② 模型生成的每个字
            chunk, meta = data                       #    （注意多路模式下是元组！）
            yield f"data: {json.dumps({'type':'chunk','content':text})}\n\n"
        elif mode == "updates" and 是 tools 节点:     # ③ 工具执行事件
            yield f"data: {json.dumps({'type':'tool','name':...})}\n\n"
    yield f"data: {json.dumps({'type':'sources','items':sources})}\n\n"  # 引用
    yield f"data: {json.dumps({'type':'done','session_id':...})}\n\n"
    _save_message(...)                   # 流结束后才落库（要有完整内容）
```

前端约定一套事件协议：`chunk`（增量文本）、`tool`（工具调用状态）、`sources`（引用）、`done`（结束）。**接口本质是"状态机直播"**。

**验证**：`curl -N POST .../chat/ask` 能看到 data: 行一个个吐出来。

---

## 第 12 步：前端——请求封装与路由守卫

**目标**：Vue 3 骨架（`fronted/`），不依赖 UI 组件库，手写 CSS。

先做三件基础设施：

**① 请求封装**（`api/request.js`）——token 自动携带、401 自动踢回登录、错误统一抛出：

```js
export async function apiFetch(path, options = {}) {
  const token = localStorage.getItem('token')
  headers.Authorization = token ? `Bearer ${token}` : ''
  const resp = await fetch(`${API_BASE}${path}`, {...})
  if (resp.status === 401) { localStorage.removeItem('token'); location.href = '/login' }
  const json = await resp.json()
  if (json.code !== 200) throw new Error(json.message)
  return json.data      // 统一响应格式的好处：这里永远只拿 data
}
```

**② 全局状态不用 Pinia**，模块级 reactive 单例就够：

```js
// composables/useAuth.js
const state = reactive({ user: null, ready: false })
export function useAuth() { return { state, login, logout, isEditor, homePath } }
```

**③ 路由守卫**（`router/index.js`）——登录拦截 + 按角色分流：

```js
router.beforeEach(async (to) => {
  if (!auth.state.ready) await auth.restoreSession()      // 刷新后恢复登录态
  if (!auth.isLoggedIn()) {
    if (to.path === '/login' || to.path === '/register') return true   // 白名单！
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresEditor && !auth.isEditor()) return '/user/chat'
})
```

> 坑：白名单一开始漏了 `/register`，点"立即注册"被守卫踢回登录页。

侧边栏菜单按角色渲染：`auth.isEditor() ? staffNav : userNav`——**同一套框架，权限不同菜单不同**。

---

## 第 13 步：前端聊天页（Markdown 渲染 + 状态提示）

**目标**：实现体验的核心页（`views/user/Chat.vue`）。

**SSE 客户端**（`streamChat`）：`fetch` 拿到流 → `getReader()` 循环读 → 按 `\n\n` 切事件 → 解析 `data:` JSON → 回调：

```js
const reader = resp.body.getReader()
while (true) {
  const { done, value } = await reader.read()
  if (done) break
  buffer += decoder.decode(value, { stream: true })
  const events = buffer.split('\n\n'); buffer = events.pop()  // 半包留到下轮
  for (const e of events) {
    const payload = JSON.parse(e.slice(5))
    if (payload.type === 'chunk') onChunk(payload.content)      // 追加到气泡
    else if (payload.type === 'tool') onTool(payload.name)      // "🔍 正在检索..."
  }
}
```

**三个体验细节**：
1. **消息存全局单例**（`useChat.js`）——路由切换组件销毁，状态不丢；刷新后调接口恢复最近会话
2. **AI 回答用 `marked` 渲染 Markdown**，用户消息保持纯文本；流式期间每来一个 chunk 重新渲染
3. **回答为空时显示状态**（"正在思考…" → "🔍 正在调用工具…"），第一个 chunk 到达后切正文

---

## 第 14 步：文档导入与管理端页面

**目标**：编辑能"扔个文件进去就进知识库"。

后端 `POST /api/articles/import`（multipart）：按扩展名分发解析——

```python
def extract_text(filename, raw):
    if filename.endswith(".pdf"):   # pypdf 逐页提取
    if filename.endswith(".docx"):  # python-docx 提取段落
    if filename.endswith((".txt", ".md")):  # utf-8 失败退 gbk
    # 提取不到文本要明确报错（扫描版 PDF 无文字层），不能静默入库空文章
```

入库后走同一套 `upsert_article` 向量化——**导入和手动创建最终汇合到同一条流水线**。

前端注意：文件上传不能用 `apiFetch`（JSON 封装），单独写 `uploadFile` 用 `FormData`。上传后先弹窗选分类和状态再确认提交。

管理端页面套路一致：列表（分页/搜索/筛选）+ 编辑表单 + 弹窗确认，参考 `views/admin/Articles.vue`。

---

## 第 15 步：Docker 部署

**目标**：两条命令在任何机器跑起来。

后端 Dockerfile：slim 镜像 + 装依赖 + 拷代码；前端多阶段构建：node 构建 → 产物拷进 nginx，`/api` 反代到后端容器（**SSE 必须关缓冲** `proxy_buffering off`）：

```yaml
# docker-compose.yml 核心
services:
  backend:
    build: ./backend
    env_file: ./backend/.env
    volumes: [kb_chroma:/app/chroma_data]   # 向量库持久化，容器重建不丢
  frontend:
    build: ./fronted
    ports: ["5174:80"]
```

`docker compose up -d --build` 完成。

---

## 常见坑清单

本项目开发过程中真实踩过的坑，收藏备用：

| 坑 | 现象 | 原因/解法 |
|---|---|---|
| CORS 报错但接口其实是 500 | 浏览器说没有 Allow-Origin 头 | 异常处理器返回的响应没经过 CORS 中间件；**根因是接口 500**，看后端日志 |
| Pydantic 校验 500 | datetime 字段声明成 str | 响应模型类型要与 ORM 实际类型一致 |
| SQLA relationship NameError | 启动即崩 | `relationship` 忘了 import |
| 依赖版本冲突 | pip ResolutionImpossible | langchain 生态版本耦合紧，参考已有可用项目的版本组合 |
| 路由守卫拦截注册页 | 点注册被踢回登录 | 免登录白名单要包含 `/register` |
| 切页面聊天记录丢失 | 返回会话页空白 | 组件销毁重建；状态放全局单例 + onMounted 恢复 |
| Markdown 满屏 `**` | 回答格式原始 | 用 marked 渲染 AI 回答 |
| Duplicate export | 前端白屏 | `export {}` 与函数上 `export` 重复 |
| 多路流模式回答为空 | chunk 事件收不到 | LangGraph `stream_mode=[...]` 时 messages 事件的数据是 `(chunk, meta)` 元组 |
| streamChat 报 onTool undefined | 前端异常 | 参数解构列表里漏写新增的回调 |
| 引用来源重复 | 同一篇文章出现多次 | 检索命中同一文章的多个分块；按 article_id 去重 |
| Windows 下目录改不了名 | Permission denied | 有进程占着句柄，先停服务 |
| GitHub push Internal Server Error | remote rejected | 服务端临时故障，隔一会儿重试 |

## 学习建议

1. **按步骤顺序做**，每步验证通过再往下——本项目每一步都可独立验证是刻意设计的
2. **对照源码读教程**：仓库每个文件都不长，重点读 `rag.py`、`graph.py`、`chat.py`、`Chat.vue` 四个核心文件
3. **改造练习**（由易到难）：
   - 把 `CHUNK_SIZE` 调成 800，观察检索效果变化
   - 给文章加"可见范围"字段（部门级知识库）
   - 接入硅基流动的 BGE-reranker 做检索重排序
   - 用 BM25 加一路关键词检索，做混合检索（专有名词命中率会明显提升）
