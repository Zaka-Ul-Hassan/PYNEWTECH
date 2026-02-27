# backend\app\routes\linkedin\linkedin_auth_route.py

from fastapi import APIRouter
from app.services.linkedin import linkedin_auth_service

router = APIRouter()

@router.get("/generate/auth-url")
def generate_linkedin_auth_url_route():
    """
    Generate LinkedIn authentication URL
    """
    return linkedin_auth_service.generate_linkedin_auth_url()

@router.get("/callback")
def linkedin_auth_callback_route(code: str):
    """
    Handle LinkedIn OAuth callback
    """
    return linkedin_auth_service.exchange_code_for_token(auth_code=code)