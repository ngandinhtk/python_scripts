"""Knowledge base endpoints."""
from fastapi import APIRouter, HTTPException
from app.services.retrieval import retrieval_service
from app.core.logging import logger

router = APIRouter()


@router.get("/search")
async def search(q: str, limit: int = 5):
    """Search knowledge base."""
    try:
        results = await retrieval_service.search(q, n_results=limit)
        return {"query": q, "results": results}
    except Exception as e:
        logger.error("knowledge.search_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
