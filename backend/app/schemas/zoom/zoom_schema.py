# backend\app\schemas\zoom\zoom_schema.py

from pydantic import BaseModel
from typing import Optional


class ZoomMeeting(BaseModel):
    meeting_id: str
    password: Optional[str] = None


class ZoomBotMeeting(ZoomMeeting):
    bot_name: Optional[str] = "Meeting Bot"

