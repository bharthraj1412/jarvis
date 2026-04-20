# screen_server/ws_server.py
"""
Asyncio WebSocket server for JARVIS MK37 screen sharing.

Broadcasts JPEG frames to all connected viewers. Supports optional
Bearer token authentication.

Protocol:
  1. On connect, server sends a JSON "meta" message:
     {"type": "meta", "width": W, "height": H, "fps": F}
  2. Then sends raw binary JPEG frames continuously.
  3. Viewer disconnect is handled gracefully.
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
from typing import Any, Set

try:
    import websockets
    from websockets.server import serve as ws_serve
    _ws_available = True
except ImportError:
    _ws_available = False


class ScreenShareServer:
    """Manages WebSocket connections and frame broadcasting."""

    def __init__(self, port: int = 8765, token: str | None = None):
        self.port = port
        self.token = token
        self.host = os.environ.get("SCREEN_SHARE_HOST", "127.0.0.1")
        self.meta: dict = {"type": "meta", "width": 1920, "height": 1080, "fps": 10}
        self._viewers: Set[Any] = set()
        self._viewers_lock = threading.Lock()
        self._server: Any = None

    @property
    def viewer_count(self) -> int:
        with self._viewers_lock:
            return len(self._viewers)

    async def _handler(self, websocket: Any) -> None:
        """Handle a single viewer connection."""
        # Token authentication
        if self.token:
            try:
                # Check for auth in the first message or headers
                auth_header = ""
                if hasattr(websocket, "request") and hasattr(websocket.request, "headers"):
                    auth_header = websocket.request.headers.get("Authorization", "")
                elif hasattr(websocket, "request_headers"):
                    auth_header = websocket.request_headers.get("Authorization", "")

                if auth_header != f"Bearer {self.token}":
                    # Try reading first message as auth
                    try:
                        first_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        if isinstance(first_msg, str):
                            auth_data = json.loads(first_msg)
                            if auth_data.get("token") != self.token:
                                await websocket.close(1008, "Unauthorized")
                                return
                    except (asyncio.TimeoutError, json.JSONDecodeError, Exception):
                        await websocket.close(1008, "Unauthorized")
                        return
            except Exception:
                await websocket.close(1008, "Auth error")
                return

        # Send meta message
        try:
            await websocket.send(json.dumps(self.meta))
        except Exception:
            return

        # Register viewer
        with self._viewers_lock:
            self._viewers.add(websocket)

        try:
            # Keep connection alive — just wait for disconnect
            async for _ in websocket:
                pass  # Ignore any messages from viewers
        except Exception:
            pass
        finally:
            with self._viewers_lock:
                self._viewers.discard(websocket)

    async def start(self) -> None:
        """Start the WebSocket server (non-blocking)."""
        if not _ws_available:
            raise RuntimeError("websockets library not installed. Run: pip install websockets")

        self._server = await ws_serve(
            self._handler,
            self.host,
            self.port,
        )
        print(f"[ScreenShare] WebSocket server listening on ws://{self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop the WebSocket server and disconnect all viewers."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        # Close all viewer connections
        with self._viewers_lock:
            viewers_copy = set(self._viewers)
            self._viewers.clear()

        for ws in viewers_copy:
            try:
                await ws.close(1001, "Server shutting down")
            except Exception:
                pass

        print("[ScreenShare] WebSocket server stopped")

    async def broadcast(self, frame_data: bytes) -> None:
        """Send a JPEG frame to all connected viewers."""
        with self._viewers_lock:
            viewers_copy = set(self._viewers)

        if not viewers_copy:
            return

        # Send to all viewers concurrently, remove disconnected ones
        disconnected: list[Any] = []
        for ws in viewers_copy:
            try:
                await ws.send(frame_data)
            except Exception:
                disconnected.append(ws)

        if disconnected:
            with self._viewers_lock:
                for ws in disconnected:
                    self._viewers.discard(ws)
