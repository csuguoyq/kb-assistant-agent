from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse
from app.utils.deps import get_current_user
from app.utils.response import success

router = APIRouter(prefix="/api/users", tags=["用户"])


@router.get("/me", summary="获取当前登录用户信息")
def me(current_user: User = Depends(get_current_user)):
    return success(data=UserResponse.model_validate(current_user).model_dump(mode="json"))


@router.put("/me", summary="更新当前用户资料（姓名）")
def update_me(name: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.name = name
    db.commit()
    db.refresh(current_user)
    return success(data=UserResponse.model_validate(current_user).model_dump(mode="json"), message="更新成功")
