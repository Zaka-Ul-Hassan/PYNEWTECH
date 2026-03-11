# backend\app\routes\mcp\mcp_route.py

from fastapi import APIRouter

from app.services.mcp import chat_service
from app.schemas.email.ai.chat_schema import ChatRequest, ChatResponse

router = APIRouter()

#  MCP Chatbot with human-in-the-loop
@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Multi-turn MCP chatbot: normal message may return text or a tool confirmation.
    If user sends "yes" with action_confirmed=true, the tool runs and returns action_result; otherwise the pending action is ignored.
    """
    return chat_service.process_chat(request)