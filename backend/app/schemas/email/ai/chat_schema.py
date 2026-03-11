# backend\app\schemas\email\ai\chat_schema.py

from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class ChatMessage(BaseModel):
    role: str 
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    action_confirmed: bool = False
    pending_action: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    type: str
    message: str
    action: Optional[Dict[str, Any]] = None