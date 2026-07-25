from fastapi import APIRouter
from pydantic import BaseModel
from classifier.services.classifier import classify_document, extract_keywords, suggest_knowledge_tree

router = APIRouter(prefix="/classify", tags=["classify"])


class ClassifyRequest(BaseModel):
    content: str
    model: str = "qwen2.5:7b"


class BatchClassifyRequest(BaseModel):
    documents: list[dict]
    model: str = "qwen2.5:7b"


@router.post("")
async def classify(req: ClassifyRequest):
    result = await classify_document(req.content, req.model)
    return result


@router.post("/batch")
async def batch_classify(req: BatchClassifyRequest):
    results = []
    for doc in req.documents:
        r = await classify_document(doc.get("content", ""), req.model)
        r["doc_id"] = doc.get("id")
        results.append(r)
    return {"results": results}


@router.post("/keywords")
async def keywords(req: ClassifyRequest):
    result = await extract_keywords(req.content, req.model)
    return {"keywords": result}


@router.post("/suggest-tree")
async def suggest_tree(documents: list[dict]):
    result = await suggest_knowledge_tree(documents)
    return result
