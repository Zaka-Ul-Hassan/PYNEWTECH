# backend\mcp_server\tools\tool_executor.py

from mcp_server.tools.email_tools import send_system_email
from mcp_server.tools.zoom_tools import (
    join_zoom_as_me,
    join_zoom_as_bot,
    get_zoom_transcript,
)

# Keys must match the @mcp.tool() function names exactly —
# that is what bind_tools() exposes to the LLM.
TOOL_REGISTRY: dict[str, callable] = {
    "send_system_email":   send_system_email,    # (recipient: list[str], subject, body)
    "join_zoom_as_me":     join_zoom_as_me,      # (meeting_id, password)
    "join_zoom_as_bot":    join_zoom_as_bot,     # (meeting_id, password, bot_name)
    "get_zoom_transcript": get_zoom_transcript,  # (meeting_id, password, bot_name, duration_seconds)
}


def execute_tool(tool_name: str, tool_args: dict) -> str:
    """
    Execute a registered MCP tool by name with the given keyword arguments.
    Raises ValueError for unknown tools; re-raises any tool execution errors.
    """
    fn = TOOL_REGISTRY.get(tool_name)
    if fn is None:
        raise ValueError(
            f"Unknown tool '{tool_name}'. "
            f"Available: {list(TOOL_REGISTRY.keys())}"
        )
    return fn(**tool_args)