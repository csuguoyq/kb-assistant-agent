"""Function Calling 工具集：智能体可调用的知识库工具。

每个工具的 docstring 会作为 Function Calling 的函数描述传给模型，
模型据此自主决定何时调用哪个工具（Tool Calling）。

引用来源的收集不在工具内做（LangGraph 在线程池执行同步工具，
contextvars 无法跨线程回传），而是由路由层解析工具输出的
"[n] 《标题》" 文本完成——见 routers/chat.py。
"""
from typing import Annotated

from langchain_core.tools import tool
from pydantic import Field

from app.database import SessionLocal
from app.models.article import Article
from app.prompts import build_context_block
from app.services import rag


@tool
def search_knowledge_base(
    query: Annotated[str, Field(description="检索关键词或完整问题，建议使用与用户问题相同的语言")],
    top_k: Annotated[int, Field(description="返回的参考片段数量，默认 4")] = 4,
) -> str:
    """在公司知识库中进行语义检索。凡涉及公司制度、流程、产品、福利等内部知识的问题，必须先调用本工具。"""
    hits = rag.search(query, top_k=top_k)
    return build_context_block(hits)


@tool
def get_article_detail(
    article_id: Annotated[int, Field(description="知识库文章 ID")],
) -> str:
    """根据文章 ID 获取知识库文章的完整内容。当检索片段不足以完整回答时可调用本工具查看全文。"""
    db = SessionLocal()
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        if article is None:
            return f"未找到 ID 为 {article_id} 的文章"
        category = article.category.name if article.category else "未分类"
        return f"《{article.title}》（分类：{category}）\n\n{article.content}"
    finally:
        db.close()


@tool
def list_categories() -> str:
    """列出知识库中现有的全部分类，帮助确定用户问题所属的知识范围。"""
    db = SessionLocal()
    try:
        articles = db.query(Article).filter(Article.status == "published").all()
        names = sorted({a.category.name for a in articles if a.category})
        return "知识库现有分类：" + ("、".join(names) if names else "（空）")
    finally:
        db.close()


ALL_TOOLS = [search_knowledge_base, get_article_detail, list_categories]
