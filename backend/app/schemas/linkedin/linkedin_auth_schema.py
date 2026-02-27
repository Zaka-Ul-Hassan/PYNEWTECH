# backend\app\schemas\linkedin\linkedin_auth_schema.py

from typing import Optional
from pydantic import BaseModel


class LinkedInAuthURLSchema(BaseModel):
    auth_url: str


class LinkedInTokenResponseSchema(BaseModel):
    access_token: str
    expires_in: int
    scope: str
    token_type: str
    id_token: Optional[str] = None 