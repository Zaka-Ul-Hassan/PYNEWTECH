# backend\app\routes\whatsapp\whatsapp_route.py

from fastapi import APIRouter, Request, Query

from app.schemas.response_schema import ResponseSchema
from app.services.whatsapp import whatsapp_service

router = APIRouter()


@router.get("/webhook")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge")
):
    return whatsapp_service.verify_webhook_service(mode, token, challenge)


@router.post("/webhook", response_model=ResponseSchema)
async def receive_whatsapp_message(request: Request):
    result = await whatsapp_service.process_whatsapp_message_service(request)

    return ResponseSchema(**result)