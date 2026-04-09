# backend\app\services\whatsapp\whapi_whatsapp_service.py

from app.schemas.response_schema import ResponseSchema

async def process_whapi_message(data: dict):
    messages = data.get("messages", [])
    processed_list = []

    for msg in messages:
        if msg.get("from_me"):
            continue

        text = msg.get("text", {}).get("body", "")
        chat_id = msg.get("chat_id", "")


        info = {
            "chat_id": chat_id,
            "sender": msg.get("from_name"),
            "content": text,
            "is_group": "@g.us" in chat_id
        }
        
        processed_list.append(info)
        
    return ResponseSchema(
        status=True,
        message="Messages processed successfully",
        data={"processed_messages": processed_list}
    )

