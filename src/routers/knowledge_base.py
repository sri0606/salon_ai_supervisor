
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import logging

from src.models.schemas import KBEntry
from src.services import KnowledgeBaseService
from src.core.dependencies import get_knowledge_base_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/knowledge-base",
    tags=["Knowledge Base"]
)



@router.get("/")
async def get_knowledge_base(service: KnowledgeBaseService = Depends(get_knowledge_base_service)):
    """Get all learned answers"""
    try:
        answers = service.get_all_learned_answers()
        return {
            "success": True,
            "count": len(answers),
            "answers": answers
        }
    except Exception as e:
        logger.error(f"Error fetching knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def add_to_knowledge_base(entry:KBEntry , service: KnowledgeBaseService = Depends(get_knowledge_base_service)):
    """Manually add entry to knowledge base"""
    try:
        await service.add_answer(
            question=entry.question,
            answer=entry.answer,
            source="manual"
        )
        return {
            "success": True,
            "message": "Entry added to knowledge base"
        }
    except Exception as e:
        logger.error(f"Error adding to knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_knowledge_base(query: str, service: KnowledgeBaseService = Depends(get_knowledge_base_service)):
    """Search knowledge base for answer"""
    try:
        answer = await service.search(query)
        return {
            "success": True,
            "found": answer is not None,
            "answer": answer
        }
    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{kb_id}")
async def delete_from_knowledge_base(kb_id: int, service: KnowledgeBaseService = Depends(get_knowledge_base_service)):
    """Delete entry from knowledge base"""
    try:
        service.delete_answer(kb_id)
        return {
            "success": True,
            "message": "Entry deleted"
        }
    except Exception as e:
        logger.error(f"Error deleting from knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))

