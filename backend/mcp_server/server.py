# backend\mcp_server\server.py

from mcp_server.mcp_instance import mcp
from mcp_server.tools import zoom_tools, email_tools

sse_app = mcp.sse_app()

if __name__ == "__main__":
    mcp.run()
    