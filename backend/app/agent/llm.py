"""LLM 客户端：智谱 GLM（OpenAI 兼容接口），供 LangGraph 智能体使用。"""
from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import settings


@lru_cache
def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.GLM_MODEL,
        api_key=settings.GLM_API_KEY,
        base_url=settings.GLM_BASE_URL,
        temperature=0.3,
        streaming=True,
        # 推理模型（如 glm-5.3-flash）默认先思考再回答，问答场景关闭以降低延迟
        extra_body={"thinking": {"type": settings.LLM_THINKING}},
    )
