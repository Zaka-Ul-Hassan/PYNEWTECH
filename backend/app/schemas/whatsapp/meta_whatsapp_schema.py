# backend\app\schemas\whatsapp\meta_whatsapp_schema.py

from pydantic import BaseModel

class CreateGroupRequest(BaseModel):
    subject: str
    description: str
    join_approval_mode: str = "auto_approve"