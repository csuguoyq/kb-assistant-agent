"""RAG 服务：结构感知切片、向量化、混合检索（向量 + BM25）与重排序。

切片策略：结构感知递归切分
1. 按 Markdown 标题层级（#/##/###）切出章节，每个 Chunk 携带章节路径元数据
2. 章节内按段落贪心装填（段落边界天然是切分点，重叠为零）
3. 单段超长时按句子边界递归细分，相邻块保留约 15% 重叠（克制，防跨界信息丢失）

检索策略：混合检索
1. 向量召回（BGE-m3 语义匹配）+ BM25 召回（关键词精确命中，专有名词/编号友好）
2. RRF（Reciprocal Rank Fusion）融合两路排名
3. BGE-reranker（硅基流动）对融合候选做精排
4. 相关性阈值过滤剔除噪声后返回 Top-K
"""
import hashlib
import logging
import os
import re
import threading
from typing import Optional

import chromadb
import httpx
import jieba
from openai import OpenAI
from rank_bm25 import BM25Okapi

from app.config import settings

logger = logging.getLogger("app.rag")

_collection = None
_embedding_client = None
_lock = threading.Lock()

COLLECTION_NAME = "kb_articles"

# 相关性阈值：cosine distance 超过该值的切片视为噪声，不进入上下文
MAX_DISTANCE = float(os.environ.get("RAG_MAX_DISTANCE", "0.75"))

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
# 句子边界：中英文句号、问叹号、分号等
_SENTENCE_RE = re.compile(r"(?<=[。！？!?；;\n])")


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


def _split_long_paragraph(paragraph: str, chunk_size: int, overlap: int) -> list[str]:
    """单段超长：按句子边界递归细分，块间保留约 15% 重叠。"""
    sentences = [s for s in _SENTENCE_RE.split(paragraph) if s.strip()]
    if len(sentences) <= 1:
        # 连句子边界都没有（极端情况），才按字符硬切
        step = chunk_size - overlap
        return [paragraph[i:i + chunk_size] for i in range(0, len(paragraph), step)] or [paragraph]

    chunks: list[str] = []
    buf = ""
    for sent in sentences:
        if len(buf) + len(sent) <= chunk_size:
            buf += sent
            continue
        if buf:
            chunks.append(buf)
        # 单句仍超长时才退化为字符滑窗
        if len(sent) > chunk_size:
            step = chunk_size - overlap
            for i in range(0, len(sent), step):
                piece = sent[i:i + chunk_size]
                if i > 0 and chunks and chunks[-1].endswith(piece[:overlap]):
                    continue  # 与上一块重叠部分去重
                chunks.append(piece)
            buf = ""
        else:
            buf = sent
    if buf:
        chunks.append(buf)
    return chunks


def chunk_text(content: str, title: str = "", chunk_size: int = None, overlap: int = None) -> list[dict]:
    """结构感知切分，返回 [{text, section}]。

    - 章节边界（Markdown 标题）是硬切分点，跨章节不重叠
    - 章节内按段落贪心装填，段落边界切分时重叠为零
    - 仅单段超长递归细分到句子级时保留约 15% 重叠
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    # 段落级切分不需要重叠；句子级细分时用 chunk_size 的 15%
    sentence_overlap = max(20, int(chunk_size * 0.15))
    text = re.sub(r"\r\n", "\n", content).strip()
    if not text:
        return []

    # 1. 按标题层级切章节
    sections: list[tuple[str, list[str]]] = []  # (章节路径, 段落列表)
    current_path = []
    current_paras: list[str] = []

    def flush_section():
        if current_paras:
            sections.append((" > ".join(current_path) if current_path else "", list(current_paras)))
            current_paras.clear()

    for line in text.split("\n"):
        m = _HEADING_RE.match(line.strip())
        if m:
            flush_section()
            level = len(m.group(1))
            heading = m.group(2).strip()
            # 维护标题层级路径：三级以内够用，深层标题平铺
            current_path = current_path[:level - 1] + [heading]
        elif line.strip():
            current_paras.append(line.strip())
    flush_section()

    if not sections and text:
        sections = [("", [text])]

    # 2. 章节内按段落贪心装填：装得下就并入当前块，装不下则定稿当前块、段落开新块
    #    （段落边界是天然切分点，此处重叠为零；首块前缀带文章标题保证全局语义）
    chunks: list[dict] = []
    for si, (section, paras) in enumerate(sections):
        header = f"{title}\n\n" if (title and si == 0) else ""
        header = f"{header}{section}\n\n" if section else header
        buf = ""
        buf_len = 0
        for para in paras:
            if buf_len and buf_len + len(para) + 1 > chunk_size:
                chunks.append({"text": buf.strip(), "section": section})
                buf = ""
                buf_len = 0
            if not buf:
                buf = header
                buf_len = len(buf)
            buf += para + "\n"
            buf_len = len(buf)
        if buf.strip():
            chunks.append({"text": buf.strip(), "section": section})

    # 3. 超长块递归细分到句子级
    final: list[dict] = []
    for c in chunks:
        if len(c["text"]) <= chunk_size + 50:
            final.append(c)
        else:
            for piece in _split_long_paragraph(c["text"], chunk_size, sentence_overlap):
                final.append({"text": piece, "section": c["section"]})
    return final


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def _doc_id(article_id: int, chunk_index: int) -> str:
    return f"a{article_id}_c{chunk_index}"


def upsert_article(article_id: int, title: str, content: str,
                   category: Optional[str] = None, tags: Optional[str] = None) -> int:
    """将文章结构化切片并向量化写入 Chroma（先清除该文章旧块）。返回块数。"""
    col = _get_collection()
    col.delete(where={"article_id": article_id})

    chunks = chunk_text(content, title=title)
    if not chunks:
        return 0

    embeddings = embed_texts([c["text"] for c in chunks])
    col.add(
        ids=[_doc_id(article_id, i) for i in range(len(chunks))],
        documents=[c["text"] for c in chunks],
        embeddings=embeddings,
        metadatas=[{
            "article_id": article_id,
            "title": title,
            "category": category or "",
            "tags": tags or "",
            "section": c["section"],
            "chunk_index": i,
        } for i, c in enumerate(chunks)],
    )
    logger.info("文章 %s 已结构化入库（%s 块）", article_id, len(chunks))
    _invalidate_bm25()
    return len(chunks)


def delete_article(article_id: int) -> None:
    _get_collection().delete(where={"article_id": article_id})
    _invalidate_bm25()


# ---------- BM25 关键词检索（混合检索的一路） ----------

_bm25 = None          # BM25Okapi 实例
_bm25_docs = None     # 与 BM25 语料对齐的 [{id, document, metadata}]
_bm25_lock = threading.Lock()
_bm25_dirty = True    # 文章增删改后置脏，下次检索时重建


def _invalidate_bm25() -> None:
    global _bm25_dirty
    _bm25_dirty = True


def tokenize_zh(text: str) -> list[str]:
    """中文分词：jieba 切词 + 保留原文中的英文/数字串（专有名词、编号精确命中）。"""
    return [t for t in jieba.lcut(text.lower()) if t.strip()]


def _get_bm25():
    """懒加载构建 BM25 索引（语料来自 Chroma 全量切片），脏标记触发重建。"""
    global _bm25, _bm25_docs, _bm25_dirty
    with _bm25_lock:
        if _bm25 is not None and not _bm25_dirty:
            return _bm25, _bm25_docs
        col = _get_collection()
        if col.count() == 0:
            _bm25, _bm25_docs, _bm25_dirty = None, None, False
            return None, None
        data = col.get(include=["documents", "metadatas"])
        _bm25_docs = [
            {"id": id_, "document": doc, "metadata": meta}
            for id_, doc, meta in zip(data["ids"], data["documents"], data["metadatas"])
        ]
        corpus = [tokenize_zh(d["document"]) for d in _bm25_docs]
        _bm25 = BM25Okapi(corpus)
        _bm25_dirty = False
        return _bm25, _bm25_docs


def bm25_search(query: str, fetch_k: int) -> list[dict]:
    """BM25 关键词召回，返回与向量召回同构的 hit 列表（无 distance）。"""
    bm25, docs = _get_bm25()
    if bm25 is None:
        return []
    scores = bm25.get_scores(tokenize_zh(query))
    ranked = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)[:fetch_k]
    hits = []
    for i in ranked:
        if scores[i] <= 0:
            continue
        d = docs[i]
        m = d["metadata"]
        hits.append({
            "article_id": m.get("article_id"),
            "title": m.get("title", ""),
            "category": m.get("category", ""),
            "tags": m.get("tags", ""),
            "section": m.get("section", ""),
            "text": d["document"],
            "distance": None,
            "bm25_score": scores[i],
        })
    return hits


# ---------- 重排序（硅基流动 BGE-reranker） ----------

def rerank(query: str, hits: list[dict], top_k: int) -> list[dict]:
    """调用 BGE-reranker 对候选精排；服务不可用时降级为原顺序。"""
    if not settings.RERANK_MODEL or not settings.SILICONFLOW_API_KEY or not hits:
        return hits[:top_k]
    try:
        resp = httpx.post(
            f"{settings.SILICONFLOW_BASE_URL}/rerank",
            headers={"Authorization": f"Bearer {settings.SILICONFLOW_API_KEY}"},
            json={
                "model": settings.RERANK_MODEL,
                "query": query,
                "documents": [h["text"] for h in hits],
                "top_n": top_k,
            },
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return [hits[r["index"]] | {"rerank_score": r["relevance_score"]} for r in results]
    except Exception as e:
        logger.warning("重排序失败，降级为 RRF 原顺序: %s", e)
        return hits[:top_k]


def search(query: str, top_k: int = None) -> list[dict]:
    """混合检索：向量 + BM25 召回 → RRF 融合 → reranker 精排 → 阈值过滤。

    返回 [{article_id, title, category, tags, section, text, distance}]。
    """
    top_k = top_k or settings.RAG_TOP_K
    fetch_k = max(settings.HYBRID_FETCH_K, top_k)
    col = _get_collection()
    if col.count() == 0:
        return []

    # ① 向量召回
    result = col.query(
        query_embeddings=[_embed_query(query)],
        n_results=min(fetch_k, col.count()),
        include=["documents", "metadatas", "distances"],
    )
    vec_hits = []
    for doc, meta, dist in zip(
        result["documents"][0], result["metadatas"][0], result["distances"][0]
    ):
        if dist <= MAX_DISTANCE:  # 阈值过滤：不相关的切片不进入候选
            vec_hits.append(_hit_from(doc, meta, dist))

    # ② BM25 关键词召回
    kw_hits = bm25_search(query, fetch_k)

    # ③ RRF 融合两路排名（常数 60 为论文经验值）
    K = 60
    fused: dict[str, dict] = {}
    for rank, hit in enumerate(vec_hits):
        key = f"a{hit['article_id']}_{hit['text'][:32]}"
        entry = fused.setdefault(key, {"hit": hit, "score": 0.0})
        entry["score"] += 1.0 / (K + rank + 1)
    for rank, hit in enumerate(kw_hits):
        key = f"a{hit['article_id']}_{hit['text'][:32]}"
        entry = fused.setdefault(key, {"hit": hit, "score": 0.0})
        entry["score"] += 1.0 / (K + rank + 1)
    candidates = [e["hit"] for e in sorted(fused.values(), key=lambda e: -e["score"])]

    # ④ 重排序精排（失败自动降级为 RRF 顺序）
    return rerank(query, candidates, top_k)


def _hit_from(doc: str, meta: dict, dist: float) -> dict:
    return {
        "article_id": meta.get("article_id"),
        "title": meta.get("title", ""),
        "category": meta.get("category", ""),
        "tags": meta.get("tags", ""),
        "section": meta.get("section", ""),
        "text": doc,
        "distance": dist,
    }
