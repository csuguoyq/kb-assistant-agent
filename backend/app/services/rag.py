"""RAG 服务：向量化、分块、Chroma 持久化与检索。

向量库：ChromaDB（本地持久化）
嵌入模型：硅基流动 BAAI/bge-m3（OpenAI 兼容接口）
"""
import hashlib
import logging
import re
import threading
from typing import Optional

import chromadb
from openai import OpenAI

from app.config import settings

logger = logging.getLogger("app.rag")

_collection = None
_embedding_client = None
_lock = threading.Lock()

COLLECTION_NAME = "kb_articles"


def _get_embedding_client() -> OpenAI:
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = OpenAI(
            api_key=settings.SILICONFLOW_API_KEY,
            base_url=settings.SILICONFLOW_BASE_URL,
        )
    return _embedding_client


def _get_collection():
    global _collection
    with _lock:
        if _collection is None:
            client = chromadb.PersistentClient(path=settings.CHROMA_DIR)
            _collection = client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
    return _collection


def embed_texts(texts: list[str]) -> list[list[float]]:
    resp = _get_embedding_client().embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in resp.data]


def _embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> list[str]:
    """按段落优先、长度兜底的中文分块。"""
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP
    text = re.sub(r"\r\n", "\n", text).strip()
    if len(text) <= chunk_size:
        return [text] if text else []

    chunks: list[str] = []
    buf = ""
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            continue
        if len(buf) + len(para) + 1 <= chunk_size:
            buf = f"{buf}\n{para}" if buf else para
            continue
        if buf:
            chunks.append(buf)
        if len(para) > chunk_size:
            start = 0
            while start < len(para):
                chunks.append(para[start:start + chunk_size])
                start += chunk_size - overlap
            buf = ""
        else:
            buf = para
    if buf:
        chunks.append(buf)
    return chunks


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def _doc_id(article_id: int, chunk_index: int) -> str:
    return f"a{article_id}_c{chunk_index}"


def upsert_article(article_id: int, title: str, content: str,
                   category: Optional[str] = None, tags: Optional[str] = None) -> int:
    """将文章分块并向量化写入 Chroma（先清除该文章旧块）。返回块数。"""
    col = _get_collection()
    col.delete(where={"article_id": article_id})

    chunks = chunk_text(f"{title}\n\n{content}")
    if not chunks:
        return 0

    embeddings = embed_texts(chunks)
    col.add(
        ids=[_doc_id(article_id, i) for i in range(len(chunks))],
        documents=chunks,
        embeddings=embeddings,
        metadatas=[{
            "article_id": article_id,
            "title": title,
            "category": category or "",
            "tags": tags or "",
            "chunk_index": i,
        } for i in range(len(chunks))],
    )
    logger.info("文章 %s 已向量化入库（%s 块）", article_id, len(chunks))
    return len(chunks)


def delete_article(article_id: int) -> None:
    _get_collection().delete(where={"article_id": article_id})


def search(query: str, top_k: int = None) -> list[dict]:
    """语义检索知识库，返回 [{article_id, title, category, tags, text, distance}]。"""
    top_k = top_k or settings.RAG_TOP_K
    col = _get_collection()
    if col.count() == 0:
        return []

    result = col.query(
        query_embeddings=[_embed_query(query)],
        n_results=min(top_k, col.count()),
        include=["documents", "metadatas", "distances"],
    )
    hits = []
    for doc, meta, dist in zip(
        result["documents"][0], result["metadatas"][0], result["distances"][0]
    ):
        hits.append({
            "article_id": meta.get("article_id"),
            "title": meta.get("title", ""),
            "category": meta.get("category", ""),
            "tags": meta.get("tags", ""),
            "text": doc,
            "distance": dist,
        })
    return hits
