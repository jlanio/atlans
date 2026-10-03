# app/api/routers/telemetry.py  (or in the same file as the workflow)

import os
import asyncio
import psutil
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.dependencies import check_ws_rate_limit, ws_authenticate
from app.core.rbac import ROLE_ADMIN

router = APIRouter()

@router.websocket("/ws/telemetry")
async def websocket_telemetry(ws: WebSocket):
    """
    WebSocket route to send VM metrics in real time.
    JWT authentication via the first message (text frame with the token),
    not via query param — avoids leaking the token in proxy logs.

    Restricted to admin: these are INFRA metrics of the server host (CPU, memory,
    disk, load). A regular user has no reason to see them, and exposing them allows
    inferring saturation windows for timing/DoS.
    """
    if await ws_authenticate(ws, require_role=ROLE_ADMIN) is None:
        return  # connection already closed by ws_authenticate
    if not await check_ws_rate_limit(ws, limit=5, period=60):
        return
    try:
        while True:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage("/").percent
            load1, load5, load15 = os.getloadavg()

            await ws.send_json({
                "cpu_percent": cpu,
                "memory_percent": mem,
                "disk_percent": disk,
                "load_avg": {"1m": load1, "5m": load5, "15m": load15},
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    finally:
        await ws.close()
