from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)
    name: Optional[str] = Field(default=None, max_length=50)
    role: Literal["user", "editor"] = "user"


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    name: Optional[str] = None
    role: str
    created_at: Optional[datetime] = None


class Token(BaseModel):
    access_token: str
    token_type: str
