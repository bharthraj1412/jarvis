# tools/mcp_connector.py
# Compatible with any MCP server (Claude Desktop, Open Claw, Paperclip, custom)
import httpx

class MCPConnector:
    def __init__(self, server_url: str, api_key: str = None):
        self.url = server_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    def list_tools(self) -> list[dict]:
        r = httpx.get(f"{self.url}/tools", headers=self.headers)
        return r.json()["tools"]

    def call_tool(self, name: str, args: dict) -> dict:
        payload = {"name": name, "arguments": args}
        r = httpx.post(f"{self.url}/tools/call",
                        json=payload, headers=self.headers)
        return r.json()
