# backend\app\routes\ai\ai_route.py

from fastapi import APIRouter
from app.schemas.response_schema import ResponseSchema
from app.services.ai import ai_service


router = APIRouter()


# Groq AI completion endpoint
@router.post("/response", response_model=ResponseSchema)
def get_ai_response(prompt: str):
    """
    Single-turn AI completion — no tools, no history.
    Send a plain string prompt, receive a plain text response.
    """
    return ai_service.get_ai_response(prompt)


