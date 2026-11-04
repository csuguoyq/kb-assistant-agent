import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.models import User, Category, Article, ChatSession, ChatMessage  # noqa: F401 确保模型被注册
from app.utils.security import get_password_hash
from app.routers import auth, users, categories, articles, chat
from app.seed import init_seed_data

logger = logging.getLogger("app")


def _ensure_schema_columns() -> None:
    """对已存在的表幂等补齐新增列（无 alembic 的轻量自迁移）。"""
    insp = inspect(engine)
    if insp.has_table("chat_messages"):
        existing = {c["name"] for c in insp.get_columns("chat_messages")}
        if "duration_ms" not in existing:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE chat_messages ADD COLUMN duration_ms INTEGER"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_schema_columns()
    db = SessionLocal()
    try:
        for username, email, password, role, name in [
            (settings.DEFAULT_ADMIN_USERNAME, "admin@example.com", settings.DEFAULT_ADMIN_PASSWORD, "admin", "系统管理员"),
            (settings.DEFAULT_EDITOR_USERNAME, "editor@example.com", settings.DEFAULT_EDITOR_PASSWORD, "editor", "知识编辑"),
        ]:
            if not db.query(User).filter(User.username == username).first():
                db.add(User(username=username, email=email,
                            password_hash=get_password_hash(password), role=role, name=name))
                db.commit()
                logger.info("默认账号已创建: %s (%s)", username, role)
        init_seed_data(db)
        logger.info("种子数据初始化完成")
    finally:
        db.close()
    yield


app = FastAPI(
    title="公司知识库 API",
    description="基于 FastAPI + LangGraph + RAG 的公司智能知识库",
    version="1.0.0",
    lifespan=lifespan,
)

_origins = ["*"] if settings.CORS_ORIGINS.strip() == "*" else [
    o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(articles.router)
app.include_router(chat.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail, "data": None},
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content={"code": 409, "message": "数据冲突，请检查输入的唯一字段", "data": None},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("未处理的异常: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误", "data": None},
    )


@app.get("/", tags=["默认"])
def root():
    return {"code": 200, "message": "success", "data": "公司知识库 API，请访问 /docs 查看文档"}


@app.get("/health", tags=["默认"])
def health():
    return {"code": 200, "message": "success", "data": "ok"}
