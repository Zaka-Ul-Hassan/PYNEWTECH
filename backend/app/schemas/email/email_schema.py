# backend\app\schemas\email\email_schema.py

from pydantic import BaseModel, EmailStr, Field

class SendSystemEmailSchema(BaseModel):
    recipient: list[EmailStr] = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Subject of the email")
    body: str = Field(..., description="Body content of the email")
