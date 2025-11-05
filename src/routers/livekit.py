
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import logging
from livekit import api
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from src.core.logging import get_plain_logger

logger = get_plain_logger(__name__)

load_dotenv()

router = APIRouter(
    prefix="/api/livekit",
    tags=["Livekit agent"]
)

class TokenRequest(BaseModel):
    roomName: str
    participantName: str


@router.post("/token")
async def generate_livekit_token(request: TokenRequest):
    """
    Generate LiveKit access token for phone simulator
    This allows web clients to join rooms and "call" the agent
    """
    try:
        
        # Get LiveKit credentials from environment
        livekit_url = os.getenv("LIVEKIT_URL")
        api_key = os.getenv("LIVEKIT_API_KEY")
        api_secret = os.getenv("LIVEKIT_API_SECRET")
        
        if not all([livekit_url, api_key, api_secret]):
            raise HTTPException(
                status_code=500,
                detail="LiveKit credentials not configured. Check .env file."
            )
        
        # Generate token
        token = api.AccessToken(api_key, api_secret)
        token.with_identity(request.participantName)
        token.with_name(request.participantName)
        token.with_grants(api.VideoGrants(
            room_join=True,
            room=request.roomName,
            can_publish=True,
            can_subscribe=True,
        ))
        
        jwt_token = token.to_jwt()
        
        return {
            "success": True,
            "token": jwt_token,
            "url": livekit_url,
            "roomName": request.roomName
        }
        
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="LiveKit SDK not installed. Run: pip install livekit"
        )
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        raise HTTPException(status_code=500, detail=str(e))