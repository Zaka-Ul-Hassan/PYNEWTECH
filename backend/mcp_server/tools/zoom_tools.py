# backend\mcp_server\tools\zoom_tools.py

import time
from mcp_server.mcp_instance import mcp

from app.services.zoom import zoom_service

@mcp.tool()
def join_zoom_as_me(meeting_id: str, password: str = "") -> str:
    start = time.time()
    try:
        # zoom_service returns ResponseSchema — unwrap to str
        result = zoom_service.join_meeting_gui(meeting_id, password or None)
        elapsed = int((time.time() - start) * 1000)
        print(f"[MCP] join_zoom_as_me OK ({elapsed}ms)")

        if not result.status:
            raise RuntimeError(result.message)
        return f"Joined meeting {meeting_id} with your desktop account. Mic and camera are OFF."
    except RuntimeError:
        raise
    except Exception as e:
        print(f"[MCP] join_zoom_as_me ERROR: {e}")
        raise


@mcp.tool()
def join_zoom_as_bot(
    meeting_id: str,
    password: str = "",
    bot_name: str = "Meeting Bot",
) -> str:

    start = time.time()
    try:
        result = zoom_service.join_meeting_bot(meeting_id, password or None, bot_name)
        elapsed = int((time.time() - start) * 1000)
        print(f"[MCP] join_zoom_as_bot OK ({elapsed}ms)")

        if not result.status:
            raise RuntimeError(result.message)
        return f"Bot '{bot_name}' joined meeting {meeting_id} as a silent guest."
    except RuntimeError:
        raise
    except Exception as e:
        print(f"[MCP] join_zoom_as_bot ERROR: {e}")
        raise


@mcp.tool()
def get_zoom_transcript(
    meeting_id: str,
    password: str = "",
    bot_name: str = "Transcript Bot",
    duration_seconds: int = 300,
) -> str:

    start = time.time()
    try:
        result = zoom_service.get_meeting_transcript(
            meeting_id, password or None, bot_name, duration_seconds
        )
        elapsed = int((time.time() - start) * 1000)
        print(f"[MCP] get_zoom_transcript OK ({elapsed}ms)")

        if not result.status:
            raise RuntimeError(result.message)

        # result.data = {"meeting_id": ..., "transcript": [...lines...]}
        lines = result.data.get("transcript", []) if result.data else []
        if lines:
            return "\n".join(lines)
        return "Transcript captured — no captions were detected during the session."
    except RuntimeError:
        raise
    except Exception as e:
        print(f"[MCP] get_zoom_transcript ERROR: {e}")
        raise
