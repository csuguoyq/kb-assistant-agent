import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models.article import Article
from app.models.category import Category
from app.models.user import User
from app.schemas.article import ArticleCreate, ArticleUpdate, ArticleResponse, ArticleListItem
from app.services import rag
from app.utils.deps import get_current_editor, get_current_user
from app.utils.response import success

logger = logging.getLogger("app")
router = APIRouter(prefix="/api/articles", tags=["知识文章"])


def _sync_vector(article: Article) -> None:
    """文章发布/更新后同步向量库：已发布则 upsert，撤销发布则删除。"""
    try:
        if article.status == "published":
            category_name = article.category.name if article.category else None
            rag.upsert_article(article.id, article.title, article.content,
                               category_name, article.tags)
        else:
            rag.delete_article(article.id)
    except Exception:
        logger.exception("向量库同步失败（文章 %s），不影响文章保存", article.id)


@router.get("", summary="文章列表（编辑/管理员），支持分页与标题搜索")
def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str = Query("", description="按标题/标签搜索"),
    status: str = Query("", description="按状态筛选：draft/published"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_editor),
):
    query = db.query(Article)
    if search:
        query = query.filter(or_(Article.title.ilike(f"%{search}%"), Article.tags.ilike(f"%{search}%")))
    if status:
        query = query.filter(Article.status == status)
    total = query.count()
    articles = (
        query.order_by(Article.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return success(data={
        "total": total,
        "items": [ArticleListItem.model_validate(a).model_dump(mode="json") for a in articles],
    })


@router.get("/public", summary="已发布文章列表（所有登录用户可见，用于浏览知识库）")
def public_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Article).filter(Article.status == "published")
    if search:
        query = query.filter(or_(Article.title.ilike(f"%{search}%"), Article.tags.ilike(f"%{search}%")))
    total = query.count()
    articles = (
        query.order_by(Article.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return success(data={
        "total": total,
        "items": [ArticleListItem.model_validate(a).model_dump(mode="json") for a in articles],
    })


@router.get("/public/{article_id}", summary="已发布文章详情（所有登录用户可见）")
def public_article(article_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    article = db.query(Article).filter(Article.id == article_id, Article.status == "published").first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在或未发布")
    return success(data=ArticleResponse.model_validate(article).model_dump(mode="json"))


@router.get("/{article_id}", summary="文章详情（编辑/管理员，含草稿）")
def get_article(article_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_editor)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    return success(data=ArticleResponse.model_validate(article).model_dump(mode="json"))


@router.post("", summary="新建文章（编辑/管理员）")
def create_article(payload: ArticleCreate, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_editor)):
    if payload.category_id and not db.query(Category).filter(Category.id == payload.category_id).first():
        raise HTTPException(status_code=400, detail="分类不存在")
    article = Article(
        title=payload.title,
        content=payload.content,
        category_id=payload.category_id,
        editor_id=current_user.id,
        tags=payload.tags,
        status=payload.status,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    _sync_vector(article)
    return success(data=ArticleResponse.model_validate(article).model_dump(mode="json"), message="创建成功")


@router.put("/{article_id}", summary="更新文章（编辑/管理员）")
def update_article(article_id: int, payload: ArticleUpdate, db: Session = Depends(get_db),
                   _: User = Depends(get_current_editor)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    if payload.category_id and not db.query(Category).filter(Category.id == payload.category_id).first():
        raise HTTPException(status_code=400, detail="分类不存在")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(article, field, value)
    db.commit()
    db.refresh(article)
    _sync_vector(article)
    return success(data=ArticleResponse.model_validate(article).model_dump(mode="json"), message="更新成功")


@router.post("/{article_id}/publish", summary="发布文章（发布后自动向量化入库，可被 AI 检索）")
def publish_article(article_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_editor)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    article.status = "published"
    db.commit()
    db.refresh(article)
    _sync_vector(article)
    return success(data=ArticleResponse.model_validate(article).model_dump(mode="json"), message="发布成功，已同步至 AI 知识库")


@router.post("/{article_id}/unpublish", summary="撤销发布（同时从 AI 知识库移除）")
def unpublish_article(article_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_editor)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    article.status = "draft"
    db.commit()
    _sync_vector(article)
    return success(data=ArticleResponse.model_validate(article).model_dump(mode="json"), message="已撤销发布")


@router.delete("/{article_id}", summary="删除文章（同时从 AI 知识库移除）")
def delete_article(article_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_editor)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    db.delete(article)
    db.commit()
    rag.delete_article(article_id)
    return success(message="删除成功")
