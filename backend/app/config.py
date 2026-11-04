import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./kb.db")

    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY", "please-change-this-to-a-random-secret-key-in-production"
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
    )

    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

    DEFAULT_ADMIN_USERNAME: str = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
    DEFAULT_EDITOR_USERNAME: str = os.getenv("DEFAULT_EDITOR_USERNAME", "editor")
    DEFAULT_EDITOR_PASSWORD: str = os.getenv("DEFAULT_EDITOR_PASSWORD", "editor123")

    # 智谱 GLM：问答生成 LLM（OpenAI 兼容接口，也兼容 Z.ai Coding Plan 的 base_url）
    GLM_API_KEY: str = os.getenv("GLM_API_KEY", "")
    GLM_BASE_URL: str = os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    GLM_MODEL: str = os.getenv("GLM_MODEL", "glm-4.6")

    # 硅基流动：BGE 向量嵌入（OpenAI 兼容接口）
    SILICONFLOW_API_KEY: str = os.getenv("SILICONFLOW_API_KEY", "")
    SILICONFLOW_BASE_URL: str = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

    # RAG 检索参数
    CHROMA_DIR: str = os.getenv("CHROMA_DIR", "./chroma_data")
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "4"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


settings = Settings()
