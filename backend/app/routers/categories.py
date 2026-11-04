from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.article import Article
from app.models.category import Category
from app.models.user import User
from app.schemas.article import CategoryCreate, CategoryResponse
from app.utils.deps import get_current_editor
from app.utils.response import success

router = APIRouter(prefix="/api/categories", tags=["分类"])


@router.get("", summary="分类列表")
def list_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).order_by(Category.id).all()
    return success(data=[CategoryResponse.model_validate(c).model_dump() for c in categories])


@router.post("", summary="新建分类（编辑/管理员）")
def create_category(payload: CategoryCreate, db: Session = Depends(get_db), _: User = Depends(get_current_editor)):
    if db.query(Category).filter(Category.name == payload.name).first():
        raise HTTPException(status_code=400, detail="分类名已存在")
    category = Category(name=payload.name, description=payload.description)
    db.add(category)
    db.commit()
    db.refresh(category)
    return success(data=CategoryResponse.model_validate(category).model_dump(), message="创建成功")


@router.delete("/{category_id}", summary="删除分类（编辑/管理员，分类下有文章时不可删）")
def delete_category(category_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_editor)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    if db.query(Article).filter(Article.category_id == category_id).count() > 0:
        raise HTTPException(status_code=400, detail="该分类下还有文章，无法删除")
    db.delete(category)
    db.commit()
    return success(message="删除成功")
