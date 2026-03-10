# backend\app\routes\email\email_route.py

from fastapi import APIRouter

from app.schemas.response_schema import ResponseSchema
from app.schemas.email.email_schema import SendSystemEmailSchema
from app.services.email import email_service


router = APIRouter()

# Send System Email
@router.post("/send-system", response_model=ResponseSchema)
def send_system_email(
payload: SendSystemEmailSchema
):
    return email_service.send_system_email(payload)