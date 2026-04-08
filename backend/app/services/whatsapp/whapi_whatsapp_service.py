# backend\app\services\whatsapp\whapi_whatsapp_service.py


from app.schemas.response_schema import ResponseSchema

async def process_whapi_message(data: dict):
    messages = data.get("messages", [])
    processed_list = []

    for msg in messages:
        # Don't process messages sent by the bot itself
        if msg.get("from_me"):
            continue

        text = msg.get("text", {}).get("body", "")
        chat_id = msg.get("chat_id", "")

        # Logic to decide if it's a task or just a chat
        # You can replace this with your AI LLM call later
        is_task = False
        if any(word in text.lower() for word in ["todo", "remind", "task", "assign"]):
            is_task = True

        info = {
            "chat_id": chat_id,
            "sender": msg.get("from_name"),
            "content": text,
            "is_group": "@g.us" in chat_id,
            "category": "task" if is_task else "chat"
        }
        
        # If it's a task, you could call a DB save function here
        # if is_task: save_task_to_db(info)

        processed_list.append(info)
        
    return ResponseSchema(
        status=True,
        message="Messages processed successfully",
        data={"processed_messages": processed_list}
    )

