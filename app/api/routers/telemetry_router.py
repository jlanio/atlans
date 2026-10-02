# app/api/routers/telemetry.py  (ou no mesmo arquivo do workflow)

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
    Rota WebSocket para enviar métricas da VM em tempo real.
    Autenticação JWT via primeira mensagem (frame de texto com o token),
    não por query param — evita vazamento do token em logs de proxy.

    Restrita a admin: são métricas de INFRA do host do servidor (CPU, memória,
    disco, load). Um usuário comum não tem por que vê-las, e expô-las permite
    inferir janelas de saturação para timing/DoS.
    """
    if await ws_authenticate(ws, require_role=ROLE_ADMIN) is None:
        return  # conexão já fechada pela ws_authenticate
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
