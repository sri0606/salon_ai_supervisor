"""
Help Request Router
Handles all help request endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import logging

from src.models.schemas import ResolveRequestBody
from src.services.help_request import HelpRequestService
from src.core.dependencies import get_help_request_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/help-requests",
    tags=["Help Requests"]
)

@router.get("/stats", response_model=dict)
async def get_stats(
    service: HelpRequestService = Depends(get_help_request_service)
):
    """Get statistics about help requests"""
    try:
        stats = service.get_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/maintenance/check-timeouts", response_model=dict)
async def check_timeouts(
    service: HelpRequestService = Depends(get_help_request_service)
):
    """Check and mark timed-out requests as unresolved"""
    try:
        count = await service.check_timeouts()
        return {
            "success": True,
            "timed_out_count": count,
            "message": f"Marked {count} requests as unresolved due to timeout"
        }
    except Exception as e:
        logger.error(f"Error checking timeouts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/pending", response_model=dict)
async def get_pending_requests(
    service: HelpRequestService = Depends(get_help_request_service)
):
    """Get all pending help requests"""
    try:
        requests = service.get_pending_requests()
        return {
            "success": True,
            "count": len(requests),
            "requests": requests
        }
    except Exception as e:
        logger.error(f"Error fetching pending requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all", response_model=dict)
async def get_all_requests(
    status: Optional[str] = None,
    service: HelpRequestService = Depends(get_help_request_service)
):
    """Get all help requests, optionally filtered by status"""
    try:
        requests = service.get_all_requests(status)
        return {
            "success": True,
            "count": len(requests),
            "requests": requests
        }
    except Exception as e:
        logger.error(f"Error fetching requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{request_id}", response_model=dict)
async def get_request_details(
    request_id: int,
    service: HelpRequestService = Depends(get_help_request_service)
):
    """Get details of specific help request"""
    try:
        requests = service.get_all_requests()
        request = next((r for r in requests if r["id"] == request_id), None)
        
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        return {
            "success": True,
            "request": request
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching request {request_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{request_id}/resolve", response_model=dict)
async def resolve_request(
    request_id: int,
    body: ResolveRequestBody,
    service: HelpRequestService = Depends(get_help_request_service)
):
    """
    Supervisor resolves a help request
    This triggers:
    1. Update request status to resolved
    2. Follow up with customer
    3. Add answer to knowledge base (if requested)
    """
    try:
        result = await service.resolve_request(
            request_id=request_id,
            supervisor_response=body.supervisor_response,
            add_to_kb=body.add_to_kb
        )
        
        return {
            "success": True,
            "message": "Request resolved and customer notified",
            "result": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error resolving request {request_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))