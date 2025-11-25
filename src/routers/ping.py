from fastapi import APIRouter, Request
from datetime import datetime, timezone, timedelta
import time

router = APIRouter(
    prefix="/ping",
    tags=["Sistema"]
)

@router.get("/", summary="Verificar status da API")
async def ping(request: Request):
    start_time = time.time()

    # Fuso horário UTC-3 (Brasil)
    tz_brasil = timezone(timedelta(hours=-3))
    now_brasil = datetime.now(tz_brasil)

    # Latência (ms)
    latency = (time.time() - start_time) * 1000

    return {
        "ok": True,
        "message": "Pong! 🏓",
        "timestamp": int(now_brasil.timestamp()),  # Unix timestamp
        "time": now_brasil.strftime("%d/%m/%Y %I:%M %p UTC-3"),  # DD/MM/YYYY 00:00 AM/PM UTC-3
        "latency_ms": round(latency, 2),
        "client_ip": request.client.host if request.client else None
    }