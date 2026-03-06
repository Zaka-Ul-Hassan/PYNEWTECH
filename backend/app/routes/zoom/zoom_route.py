# backend\app\routes\zoom\zoom_route.py

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.services.zoom import zoom_service
from app.schemas.zoom.zoom_schema import ZoomMeeting, ZoomBotMeeting, ZoomTranscriptRequest

router = APIRouter()


@router.post("/me/join-meeting")
def join_as_me(data: ZoomMeeting):
    # Join using YOUR logged-in Zoom desktop account. Camera and mic turned off automatically.
    return zoom_service.join_meeting_gui(data.meeting_id, data.password)


@router.post("/bot/join-meeting")
def join_as_bot(data: ZoomBotMeeting):
    # Join as a guest bot via Zoom Web Client. Camera and mic blocked at browser level.
    return zoom_service.join_meeting_bot(data.meeting_id, data.password, data.bot_name)


@router.post("/bot/transcript")
def get_transcript(data: ZoomTranscriptRequest):
    # Join as bot, collect full transcript, return all at once after duration_seconds.
    return zoom_service.get_meeting_transcript(
        data.meeting_id, data.password, data.bot_name, data.duration_seconds,
    )


@router.get("/bot/transcript/live")
def stream_transcript(
    meeting_id: str,
    password: str = None,
    bot_name: str = "Transcript Bot",
    duration_seconds: int = 3600,
) -> StreamingResponse:
    # Stream live captions as SSE — one event per caption line as it's spoken.
    # Connect with EventSource in frontend or curl:
    #   curl -N "http://localhost:8000/zoom/bot/transcript/live?meeting_id=123&duration_seconds=3600"
    return zoom_service.stream_meeting_transcript(
        meeting_id, password, bot_name, duration_seconds,
    )