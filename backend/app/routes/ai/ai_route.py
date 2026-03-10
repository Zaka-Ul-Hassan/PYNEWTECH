# backend\app\routes\ai\ai_route.py

from fastapi import APIRouter
from app.schemas.response_schema import ResponseSchema
from app.services.ai import ai_service


router = APIRouter()

# AI Response Endpoint
@router.post("/response", response_model=ResponseSchema)
def get_ai_response(prompt: str):
    response = ai_service.get_ai_response(prompt)
    return response