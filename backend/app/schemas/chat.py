from typing import Optional, List

from pydantic import BaseModel


class ChatMessageOut(BaseModel):
    role: str
    content: str
    sources: List[dict] = []


class ChatSessionOut(BaseModel):
    id: str
    title: Optional[str] = None
    created_at: Optional[str] = None
    message_count: int = 0


class SourceItem(BaseModel):
    article_id: int
    title: str
    snippet: str
