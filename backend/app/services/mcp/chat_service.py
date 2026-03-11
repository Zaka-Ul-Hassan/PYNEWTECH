# backend\app\services\mcp\chat_service.py

from typing import List
from langchain_groq import ChatGroq
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.core.load_env import GROQ_API_KEY, GROQ_MODEL
from app.schemas.email.ai.chat_schema import ChatMessage, ChatRequest, ChatResponse
from mcp_server.tools.tool_executor import TOOL_REGISTRY, execute_tool



# System prompt

SYSTEM_PROMPT = """You are a helpful AI assistant with access to tools for:
- Sending emails
- Joining Zoom meetings (as the user or as a silent bot)
- Getting Zoom meeting transcripts

When the user asks you to perform one of these actions, use the appropriate tool.
If the user asks for something you have no tool for, politely explain what you CAN do.
Keep all non-tool responses concise and friendly."""


# Build LangChain StructuredTools from the MCP registry

def _build_lc_tools() -> List[StructuredTool]:
    """
    Wrap every function in TOOL_REGISTRY as a LangChain StructuredTool.
    bind_tools() uses these to teach the LLM the tool schemas.
    """
    tools = []
    for name, fn in TOOL_REGISTRY.items():
        tools.append(
            StructuredTool.from_function(
                func=fn,
                name=name,
                description=fn.__doc__ or name,
            )
        )
    return tools


LC_TOOLS = _build_lc_tools()


# LLM with tools bound

_llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model=GROQ_MODEL,
    temperature=0.2,  # low = deterministic tool detection
)

_llm_with_tools = _llm.bind_tools(LC_TOOLS)


#  History helpers

def _to_lc_messages(history: List[ChatMessage], current: str):
    """
    Convert our ChatMessage history + the new user message into
    LangChain message objects with a system prompt prepended.
    """
    # FIX — ChatMessage from our schema has .role / .content
    # Do NOT confuse with langchain_core.messages.ChatMessage
    msgs = [SystemMessage(content=SYSTEM_PROMPT)]
    for turn in history:
        if turn.role == "user":
            msgs.append(HumanMessage(content=turn.content))
        else:
            msgs.append(AIMessage(content=turn.content))
    msgs.append(HumanMessage(content=current))
    return msgs


# Main entry point

def process_chat(request: ChatRequest) -> ChatResponse:
    """
    Handle one chat turn.
    Called by POST /mcp/chat in mcp_route.py.
    """

    # Branch A: execute a confirmed tool
    if request.action_confirmed and request.pending_action:
        action = request.pending_action

        try:
            outcome = execute_tool(action["tool_name"], action["tool_args"])
            return ChatResponse(
                type="action_result",
                message=outcome,
                action=action,
            )
        except Exception as exc:
            return ChatResponse(
                type="error",
                message=f"Tool execution failed: {str(exc)}",
            )

    # Branch B: call LLM with tools bound
    try:
        lc_messages = _to_lc_messages(request.history, request.message)
        ai_msg: AIMessage = _llm_with_tools.invoke(lc_messages)
    except Exception as exc:
        return ChatResponse(
            type="error",
            message=f"LLM error: {str(exc)}",
        )

    #  Did the LLM request a tool call?
    if ai_msg.tool_calls:
        tc = ai_msg.tool_calls[0]          # take the first (LLMs rarely batch)
        tool_name = tc["name"]
        tool_args = tc["args"]

        return ChatResponse(
            type="confirmation",
            message=_build_summary(tool_name, tool_args),
            action={
                "tool_name": tool_name,
                "tool_args": tool_args,
            },
        )

    #  Plain text reply
    return ChatResponse(
        type="text",
        message=ai_msg.content or "I'm not sure how to help with that.",
    )


#  Confirmation card summary

def _build_summary(tool_name: str, tool_args: dict) -> str:
    """One-line human-readable description shown in the confirmation card."""

    # FIX — key matches @mcp.tool() function name: send_system_email
    if tool_name == "send_system_email":
        recipients = tool_args.get("recipient", [])
        to_str = ", ".join(recipients) if isinstance(recipients, list) else str(recipients)
        return (
            f"Send an email to **{to_str}** "
            f"with subject: \"{tool_args.get('subject', '')}\""
        )

    if tool_name == "join_zoom_as_me":
        return (
            f"Join Zoom meeting **{tool_args.get('meeting_id', '?')}** "
            f"using your desktop account."
        )

    if tool_name == "join_zoom_as_bot":
        bot = tool_args.get("bot_name", "Meeting Bot")
        mid = tool_args.get("meeting_id", "?")
        return f"Add bot **{bot}** to Zoom meeting **{mid}** as a silent guest."

    if tool_name == "get_zoom_transcript":
        secs = int(tool_args.get("duration_seconds", 300))
        mins = secs // 60
        return (
            f"Record transcript of meeting **{tool_args.get('meeting_id', '?')}** "
            f"for {mins} minute(s)."
        )

    return f"Execute tool **{tool_name}**."