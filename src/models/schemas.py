from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class HelpRequestCreate(BaseModel):
    caller_id: str
    question: str
    escalation_reason: str
    caller_phone: Optional[str] = None

class HelpRequestResponse(BaseModel):
    id: int
    caller_id: str
    question: str
    status: str
    created_at: datetime
    
class ResolveRequestBody(BaseModel):
    supervisor_response: str
    add_to_kb: bool = True

class KBEntry(BaseModel):
    question: str
    answer: str
    source: str = "manual"