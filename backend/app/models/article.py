from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    content = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    editor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # draft: 草稿（不入向量库）；published: 已发布（入向量库，可被 RAG 检索）
    status = Column(String(20), default="draft", nullable=False, index=True)
    tags = Column(String(255), nullable=True)
    # 发布/更新后内容指纹，用于判断是否需要重新向量化
    content_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    category = relationship("Category", lazy="joined")
    editor = relationship("User", lazy="joined")

    def __repr__(self):
        return f"<Article(id={self.id}, title={self.title}, status={self.status})>"
