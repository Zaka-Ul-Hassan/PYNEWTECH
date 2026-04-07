# backend\app\services\whatsapp\whatsapp_service.py

from fastapi import Request, Response
from app.core.load_env import WEBHOOK_VERIFY_TOKEN


def verify_webhook_service(mode: str, token: str, challenge: str):
    if mode == "subscribe" and token == WEBHOOK_VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    
    return Response(content="Verification failed", status_code=403)


async def process_whatsapp_message_service(request: Request):
    body = await request.json()

    print(f"Incoming: {body}")

    return {
        "status": True,
        "message": "Message received successfully",
        "data": {"event": "message_received"}
    }