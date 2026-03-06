# backend\app\schemas\zoom\zoom_schema.py

from pydantic import BaseModel
from typing import Optional


class ZoomMeeting(BaseModel):
    meeting_id: str
    password: Optional[str] = None


class ZoomBotMeeting(BaseModel):
    meeting_id: str
    password: Optional[str] = None
    bot_name: Optional[str] = "Meeting Bot"


class ZoomTranscriptRequest(BaseModel):
    meeting_id: str
    password: Optional[str] = None
    bot_name: Optional[str] = "Transcript Bot"
    duration_seconds: Optional[int] = 300  # how long to listen before returning