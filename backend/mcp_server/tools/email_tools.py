# backend\mcp_server\tools\email_tools.py

import time
from mcp_server.mcp_instance import mcp
from app.schemas.email.email_schema import SendSystemEmailSchema
from app.services.email import email_service

@mcp.tool()
def send_system_email(
    recipient: list[str],
    subject: str,
    body: str,
) -> str:
    
    start = time.time()
    try:
        payload = SendSystemEmailSchema(
            recipient=recipient,
            subject=subject,
            body=body,
        )

        # email_service returns ResponseSchema — unwrap it to str for MCP
        result = email_service.send_system_email(payload)

        elapsed = int((time.time() - start) * 1000)
        print(f"[MCP] send_system_email OK ({elapsed}ms)")

        if not result.status:
            # Raise so the error bubbles up cleanly to chat_service
            raise RuntimeError(result.message)

        return f"Email sent successfully to {', '.join(recipient)}."

    except RuntimeError:
        raise
    except Exception as e:
        print(f"[MCP] send_system_email ERROR: {e}")
        raise
