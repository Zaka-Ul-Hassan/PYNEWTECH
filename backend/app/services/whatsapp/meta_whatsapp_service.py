# backend\app\services\whatsapp\meta_whatsapp_service.py

from fastapi import Request, Response
from app.core.load_env import WEBHOOK_VERIFY_TOKEN, WHATSAPP_ACCESS_TOKEN, META_WHATSAPP_API_URL,PHONE_NUMBER_ID
from app.schemas.response_schema import ResponseSchema
import requests



# Webhook verification for Meta WhatsApp
def verify_webhook_service(mode: str, token: str, challenge: str):
    if mode == "subscribe" and token == WEBHOOK_VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    
    return Response(content="Verification failed", status_code=403)


# Process incoming WhatsApp messages
async def process_whatsapp_message_service(request: Request):
    body = await request.json()

    print(f"Incoming: {body}")

    return ResponseSchema(
        status=True,
        message="Message received successfully",
        data={"event": "message_received"}
    )



#  Get Group Join Requests
async def get_join_requests(group_id: str):
    try:
        url = f"{META_WHATSAPP_API_URL}/{group_id}/join_requests"

        headers = {
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"
        }

        response = requests.get(url, headers=headers)
        data = response.json()

        return ResponseSchema(
            status=True,
            message="Join requests fetched",
            data=data
        )

    except Exception as e:
        return ResponseSchema(
            status=False,
            message="Failed to fetch join requests",
            data={"error": str(e)}
        )


# Approve Join Requests (THIS = user joins group)
async def approve_join_requests(group_id: str, body: dict):
    try:
        url = f"{META_WHATSAPP_API_URL}/{group_id}/join_requests"

        headers = {
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        payload = {
            "messaging_product": "whatsapp",
            "join_requests": body.get("join_requests", [])
        }

        response = requests.post(url, headers=headers, json=payload)
        data = response.json()

        return ResponseSchema(
            status=True,
            message="Join requests approved",
            data=data
        )

    except Exception as e:
        return ResponseSchema(
            status=False,
            message="Failed to approve join requests",
            data={"error": str(e)}
        )
    

# Get All Groups
async def get_all_groups():
    try:
        url = f"{META_WHATSAPP_API_URL}/{PHONE_NUMBER_ID}/groups"

        headers = {
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"
        }

        response = requests.get(url, headers=headers)
        data = response.json()

        # Optional: extract clean list
        groups = data.get("data", {}).get("groups", [])

        return ResponseSchema(
            status=True,
            message="Groups fetched successfully",
            data={
                "total_groups": len(groups),
                "groups": groups
            }
        )

    except Exception as e:
        return ResponseSchema(
            status=False,
            message="Failed to fetch groups",
            data={"error": str(e)}
        )

def create_group(request: dict):
    try:
        # Update version to v25.0 as per the documentation
        url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/groups"

        headers = {
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        payload = {
            "messaging_product": "whatsapp",
            "subject": request["subject"][:128], # Ensure length limit
            "description": request.get("description", "")[:2048],
            "join_approval_mode": request.get("join_approval_mode", "auto_approve")
        }

        response = requests.post(url, json=payload, headers=headers)
        
        # It's better to use .status_code to check for success
        if response.status_code == 200 or response.status_code == 201:
            return {
                "status": True,
                "message": "Group created successfully",
                "data": response.json()
            }
        else:
            return {
                "status": False,
                "message": f"Meta API Error: {response.status_code}",
                "data": response.json()
            }

    except Exception as e:
        return {"status": False, "data": {"error": str(e)}}