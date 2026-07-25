"""
Enterprise KM Search — 企业知识库搜索服务
Meilisearch 全文搜索 + Qdrant 向量搜索 + RAG 问答
"""
import json
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
import meilisearch
from qdrant_client import QdrantClient
from qdrant_client.models import SearchRequest, Filter, FieldCondition, MatchValue
import httpx
from typing import Optional
from loguru import logger

from search.core.config import (
    MEILISEARCH_URL, MEILISEARCH_KEY, QDRANT_URL,
    OLLAMA_URL, OLLAMA_MODEL, EMBEDDING_MODEL,
)
from search.core.permissions import get_visibility_filter, get_user_from_token

app = FastAPI(title="Enterprise KM Search")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

meili = meilisearch.Client(MEILISEARCH_URL, MEILISEARCH_KEY)
qdrant = QdrantClient(url=QDRANT_URL)
INDEX_NAME = "enterprise_km"
COLLECTION_NAME = "enterprise_km"


@app.get("/health")
async def health():
    return {"status": "ok", "service": "search"}


@app.get("/api/search")
async def search(
    q: str = Query(..., description="搜索关键词"),
    doc_type: Optional[str] = Query(None, description="文档类型筛选"),
    category: Optional[str] = Query(None, description="分类筛选"),
    limit: int = Query(20, ge=1, le=100),
    authorization: str = Depends(get_user_from_token),
):
    """
    混合搜索：Meilisearch 全文 + Qdrant 向量，RRF 合并排序。
    按用户权限过滤。
    """
    user_id, team_ids = authorization
    visibility_filter = get_visibility_filter(user_id, team_ids)

    # 1. Meilisearch 全文搜索
    meili_filter = visibility_filter
    if doc_type:
        meili_filter.append(f"doc_type = {doc_type}")
    if category:
        meili_filter.append(f"category = {category}")

    try:
        meili_results = meili.index(INDEX_NAME).search(
            q,
            {
                "limit": limit,
                "filter": meili_filter,
                "attributesToHighlight": ["title", "content"],
            },
        )
    except Exception as e:
        logger.warning(f"Meilisearch error: {e}")
        meili_results = {"hits": []}

    # 2. Qdrant 向量搜索
    try:
        # Generate query embedding
        embed_resp = httpx.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": q},
            timeout=30,
        )
        query_vector = embed_resp.json()["embedding"]

        qdrant_results = qdrant.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=limit,
        )
    except Exception as e:
        logger.warning(f"Qdrant error: {e}")
        qdrant_results = []

    # 3. RRF 合并排序
    merged = _rrf_merge(meili_results.get("hits", []), qdrant_results, limit)

    return {
        "query": q,
        "total": len(merged),
        "results": merged,
    }


@app.post("/api/ask")
async def ask(
    question: str = Query(...),
    doc_type: Optional[str] = Query(None),
    limit: int = Query(5, ge=1, le=10),
    authorization: str = Depends(get_user_from_token),
):
    """
    RAG 问答：搜索 Top-N 相关文档片段，调用 Ollama 生成回答。
    """
    user_id, team_ids = authorization

    # Search for relevant context
    try:
        embed_resp = httpx.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": question},
            timeout=30,
        )
        query_vector = embed_resp.json()["embedding"]

        qdrant_results = qdrant.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

    if not qdrant_results:
        return {
            "question": question,
            "answer": "抱歉，未找到相关知识来回答您的问题。",
            "sources": [],
        }

    # Build context from search results
    context_parts = []
    sources = []
    for r in qdrant_results:
        payload = r.payload or {}
        fields = payload.get("fields", {})
        source_id = payload.get("source_id", "")
        doc_type = payload.get("doc_type", "")

        context_parts.append(json.dumps(fields, ensure_ascii=False))
        sources.append({
            "doc_id": source_id,
            "doc_type": doc_type,
            "score": round(r.score, 3),
        })

    context = "\n\n".join(context_parts[:3])  # Top 3 for context

    # Generate answer via Ollama
    prompt = f"""你是一个制造业知识助手。请根据以下知识库内容回答用户问题。
如果知识库中没有相关信息，请明确告知，不要编造。

知识库内容：
{context}

用户问题：{question}

请用中文回答，并引用知识库中的具体信息。"""

    try:
        resp = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=60,
        )
        answer = resp.json()["response"].strip()
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        raise HTTPException(status_code=500, detail="AI generation failed")

    return {
        "question": question,
        "answer": answer,
        "sources": sources,
    }


def _rrf_merge(meili_hits: list, qdrant_hits: list, limit: int, k: int = 60):
    """Reciprocal Rank Fusion 合并排序"""
    scores = {}

    for rank, hit in enumerate(meili_hits):
        doc_id = hit.get("id", "")
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)

    for rank, hit in enumerate(qdrant_hits):
        doc_id = hit.id if hasattr(hit, "id") else str(hit.id)
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)

    # Sort by RRF score
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:limit]

    # Build result
    results = []
    for doc_id in sorted_ids:
        # Find in meili hits for metadata
        meta = next((h for h in meili_hits if h.get("id") == doc_id), {})
        results.append({
            "id": doc_id,
            "title": meta.get("title", ""),
            "doc_type": meta.get("doc_type", ""),
            "category": meta.get("category", ""),
            "score": round(scores[doc_id], 4),
            "highlight": meta.get("_formatted", {}).get("content", "")[:200],
        })

    return results
