# backend\app\routes\whatsapp\whatsapp_route.py

from fastapi import APIRouter, Request, Query

from app.schemas.response_schema import ResponseSchema
from app.services.whatsapp import meta_whatsapp_service
from app.schemas.whatsapp.meta_whatsapp_schema import CreateGroupRequest

router = APIRouter()


@router.get("/webhook")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge")
):
    return meta_whatsapp_service.verify_webhook_service(mode, token, challenge)


@router.post("/webhook", response_model=ResponseSchema)
async def receive_whatsapp_message(request: Request):
    result = await meta_whatsapp_service.process_whatsapp_message_service(request)
    return result


@router.get("/groups/{group_id}/join-requests", response_model=ResponseSchema)
async def get_join_requests(group_id: str):
    return await meta_whatsapp_service.get_join_requests(group_id)

@router.post("/groups/{group_id}/approve-join", response_model=ResponseSchema)
async def approve_join_requests(group_id: str, request: Request):
    body = await request.json()
    return await meta_whatsapp_service.approve_join_requests(group_id, body)

@router.get("/groups", response_model=ResponseSchema)
async def get_all_groups():
    return await meta_whatsapp_service.get_all_groups()

@router.post("/groups/create")
async def create_group(request: CreateGroupRequest):
    return meta_whatsapp_service.create_group(request.dict())