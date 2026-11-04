from datetime import datetime
from typing import Literal, Optional, List

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None


class ArticleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    category_id: Optional[int] = None
    tags: Optional[str] = None
    status: Literal["draft", "published"] = "draft"


class ArticleUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    content: Optional[str] = None
    category_id: Optional[int] = None
    tags: Optional[str] = None
    status: Optional[Literal["draft", "published"]] = None


class ArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    category_id: Optional[int] = None
    editor_id: int
    status: str
    tags: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ArticleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    category_id: Optional[int] = None
    editor_id: int
    status: str
    tags: Optional[str] = None
    updated_at: Optional[datetime] = None
