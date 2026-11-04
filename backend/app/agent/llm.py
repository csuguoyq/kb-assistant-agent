"""LLM 客户端：DeepSeek Chat，供 LangGraph 智能体使用。"""
from functools import lru_cache

from langchain_deepseek import ChatDeepSeek

from app.config import settings


@lru_cache
def get_llm() -> ChatDeepSeek:
    return ChatDeepSeek(
        model=settings.DEEPSEEK_MODEL,
        api_key=settings.DEEPSEEK_API_KEY,
        temperature=0.3,
        streaming=True,
    )
