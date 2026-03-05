# backend\app\routes\zoom\zoom_route.py

from fastapi import APIRouter
from app.services.zoom import zoom_service
from app.schemas.zoom.zoom_schema import ZoomMeeting, ZoomBotMeeting

router = APIRouter()


@router.post("/me/join-meeting")
def join_as_me(data: ZoomMeeting):
    """
    Join a Zoom meeting using YOUR logged-in Zoom desktop account.
    Camera and mic are turned off automatically.
    """
    return zoom_service.join_meeting_gui(data.meeting_id, data.password)


@router.post("/bot/join-meeting")
def join_as_bot(data: ZoomBotMeeting):
    """
    Join a Zoom meeting as a GUEST BOT via the Zoom Web Client (no account needed).
    This is a SEPARATE participant from your logged-in Zoom account.
    Camera and mic are blocked at the browser level — never turns on.
    """
    return zoom_service.join_meeting_bot(data.meeting_id, data.password, data.bot_name)