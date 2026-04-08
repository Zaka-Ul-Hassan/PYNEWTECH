# backend\app\routes\whatsapp\whapi_whatsapp_route.py

from fastapi import APIRouter, Request

from app.schemas.response_schema import ResponseSchema
from app.services.whatsapp import whapi_whatsapp_service

router = APIRouter()


@router.post("/whatsapp", response_model=ResponseSchema)
async def handle_whapi_webhook(request: Request):
    # 1. Parse the JSON body
    raw_json = await request.json() 
    
    # 2. Print it so you can see it in your terminal
    print(f"Received WhatsApp webhook: {raw_json}")

    # 3. Pass the DICTIONARY (raw_json), not the request object
    result = await whapi_whatsapp_service.process_whapi_message(raw_json)

    return result