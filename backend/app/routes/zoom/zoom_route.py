# backend\app\routes\zoom\zoom_route.py

from fastapi import APIRouter
from app.services.zoom import zoom_service

router = APIRouter()


@router.post("/my/join-meeting")
def join_as_me(meeting_id: str, password: str = None):
    """
    Join a Zoom meeting using YOUR logged-in Zoom desktop account.
    Camera and mic are turned off automatically.
    """
    return zoom_service.join_meeting_gui(meeting_id, password)


@router.post("/bot/join-meeting")
def join_as_bot(meeting_id: str, password: str = None, bot_name: str = "Meeting Bot"):
    """
    Join a Zoom meeting as a GUEST BOT via the Zoom Web Client (no account needed).
    This is a SEPARATE participant from your logged-in Zoom account.
    Camera and mic are blocked at the browser level — never turns on.
    """
    return zoom_service.join_meeting_bot(meeting_id, password, bot_name)