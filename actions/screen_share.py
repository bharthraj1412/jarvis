# actions/screen_share.py
"""
Real-time screen sharing for JARVIS MK37.

Uses mss for high-performance screen capture (primary) with
pyautogui.screenshot() as fallback. Broadcasts JPEG frames over
WebSocket to connected viewers.

Public API:
    start_sharing(port, token, monitor, fps, quality)
    stop_sharing()
    get_status() -> dict
    list_monitors() -> list[dict]
"""
from __future__ import annotations

import io
import threading
import time
from typing import Any

# Screen capture backends
_mss_available = False
try:
    import mss
    _mss_available = True
except ImportError:
    pass

_pyautogui_available = False
try:
    import pyautogui
    _pyautogui_available = True
except ImportError:
    pass

_pil_available = False
try:
    from PIL import Image
    _pil_available = True
except ImportError:
    pass


# ── Global state ──────────────────────────────────────────────────────────

_sharing_thread: threading.Thread | None = None
_stop_event = threading.Event()
_server_ref: Any = None
_status: dict = {
    "is_running": False,
    "viewer_count": 0,
    "fps": 0,
    "monitor": 1,
    "port": 8765,
    "quality": 60,
}


def list_monitors() -> list[dict]:
    """Enumerate available monitors.

    Returns a list of dicts with keys: id, width, height, left, top.
    Monitor 0 is the combined virtual screen (all monitors).
    """
    if _mss_available:
        try:
            with mss.mss() as sct:
                result = []
                for i, mon in enumerate(sct.monitors):
                    result.append({
                        "id": i,
                        "width": mon["width"],
                        "height": mon["height"],
                        "left": mon["left"],
                        "top": mon["top"],
                    })
                return result
        except Exception as e:
            return [{"id": 0, "error": str(e)}]

    if _pyautogui_available:
        try:
            size = pyautogui.size()
            return [{
                "id": 0,
                "width": size.width,
                "height": size.height,
                "left": 0,
                "top": 0,
            }]
        except Exception as e:
            return [{"id": 0, "error": str(e)}]

    return [{"id": 0, "error": "No screen capture library available (install mss or pyautogui)"}]


def _capture_frame_mss(monitor_index: int, quality: int) -> tuple[bytes, int, int]:
    """Capture a single frame using mss and return (jpeg_bytes, width, height)."""
    with mss.mss() as sct:
        monitors = sct.monitors
        if monitor_index >= len(monitors):
            monitor_index = 1 if len(monitors) > 1 else 0
        mon = monitors[monitor_index]
        raw = sct.grab(mon)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue(), mon["width"], mon["height"]


def _capture_frame_pyautogui(quality: int) -> tuple[bytes, int, int]:
    """Capture a single frame using pyautogui and return (jpeg_bytes, width, height)."""
    screenshot = pyautogui.screenshot()
    buf = io.BytesIO()
    screenshot.save(buf, format="JPEG", quality=quality)
    w, h = screenshot.size
    return buf.getvalue(), w, h


def _capture_loop(port: int, token: str | None, monitor: int, fps: int, quality: int) -> None:
    """Main capture loop — runs in a dedicated thread."""
    import asyncio

    async def _run_server():
        from screen_server.ws_server import ScreenShareServer

        server = ScreenShareServer(port=port, token=token)
        global _server_ref
        _server_ref = server

        # Determine initial dimensions
        try:
            if _mss_available and _pil_available:
                _, w, h = _capture_frame_mss(monitor, quality)
            elif _pyautogui_available:
                _, w, h = _capture_frame_pyautogui(quality)
            else:
                print("[ScreenShare] ERROR: No capture backend available")
                return
        except Exception as e:
            print(f"[ScreenShare] Capture init error: {e}")
            return

        server.meta = {"type": "meta", "width": w, "height": h, "fps": fps}

        # Start the WebSocket server
        await server.start()

        _status["is_running"] = True
        _status["port"] = port
        _status["monitor"] = monitor
        _status["fps"] = fps
        _status["quality"] = quality

        frame_interval = 1.0 / max(1, min(fps, 30))

        try:
            while not _stop_event.is_set():
                start_t = time.monotonic()

                try:
                    if _mss_available and _pil_available:
                        frame_data, _, _ = _capture_frame_mss(monitor, quality)
                    else:
                        frame_data, _, _ = _capture_frame_pyautogui(quality)
                except Exception:
                    await asyncio.sleep(frame_interval)
                    continue

                await server.broadcast(frame_data)
                _status["viewer_count"] = server.viewer_count

                elapsed = time.monotonic() - start_t
                sleep_time = max(0, frame_interval - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
        finally:
            await server.stop()
            _status["is_running"] = False
            _status["viewer_count"] = 0
            _server_ref = None

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_server())
    except Exception as e:
        print(f"[ScreenShare] Server error: {e}")
    finally:
        loop.close()


def start_sharing(
    port: int = 8765,
    token: str | None = None,
    monitor: int = 1,
    fps: int = 10,
    quality: int = 60,
) -> str:
    """Start the screen sharing server.

    Args:
        port:    WebSocket port (default 8765)
        token:   optional authentication token
        monitor: monitor index (0=all combined, 1=primary, 2=secondary, ...)
        fps:     frames per second (default 10, max 30)
        quality: JPEG quality 1-100 (default 60)

    Returns:
        Status message.
    """
    global _sharing_thread

    if _status["is_running"]:
        return f"Screen sharing already running on port {_status['port']}"

    if not _mss_available and not _pyautogui_available:
        return "ERROR: No screen capture library. Install: pip install mss Pillow"

    if _mss_available and not _pil_available:
        return "ERROR: PIL/Pillow required for JPEG encoding. Install: pip install Pillow"

    fps = max(1, min(fps, 30))
    quality = max(10, min(quality, 100))

    _stop_event.clear()
    _sharing_thread = threading.Thread(
        target=_capture_loop,
        args=(port, token, monitor, fps, quality),
        daemon=True,
        name="screen-share",
    )
    _sharing_thread.start()

    # Wait briefly for server to start
    time.sleep(0.5)

    return (
        f"Screen sharing started on ws://127.0.0.1:{port}\n"
        f"Monitor: {monitor} | FPS: {fps} | Quality: {quality}\n"
        f"Open viewer: screen_server/viewer.html?port={port}"
    )


def stop_sharing() -> str:
    """Stop the screen sharing server."""
    global _sharing_thread

    if not _status["is_running"]:
        return "Screen sharing is not running."

    _stop_event.set()
    if _sharing_thread and _sharing_thread.is_alive():
        _sharing_thread.join(timeout=5)
    _sharing_thread = None
    _status["is_running"] = False
    return "Screen sharing stopped."


def get_status() -> dict:
    """Return the current screen sharing status."""
    return dict(_status)
