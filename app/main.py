"""API mínima para practicar Docker, CI/CD, Kubernetes y GitOps."""

import os
import platform
import random
import socket
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

APP_VERSION = os.getenv("APP_VERSION", "dev")


# Chaos engineering: fracción de peticiones que responden 500 a propósito (0 = desactivado).
# Sirve para comprobar que las alertas del SLO saltan con un fallo real. Nunca afecta a
# /health (las probes siguen pasando y Kubernetes no reinicia los pods) ni a /metrics.
def chaos_rate(value: str) -> float:
    """Convierte CHAOS_ERROR_RATE en una fracción entre 0 y 1."""
    return min(max(float(value), 0.0), 1.0)


CHAOS_ERROR_RATE = chaos_rate(os.getenv("CHAOS_ERROR_RATE", "0"))
CHAOS_EXCLUDED = {"/health", "/metrics"}

app = FastAPI(title="demo-api", version=APP_VERSION)


# Se registra ANTES que el Instrumentator: así queda por dentro y los 500 provocados se
# cuentan en http_requests_total igual que un error de verdad.
@app.middleware("http")
async def chaos(request: Request, call_next):
    path = request.url.path
    if CHAOS_ERROR_RATE and path not in CHAOS_EXCLUDED and random.random() < CHAOS_ERROR_RATE:
        return JSONResponse({"detail": "chaos: error provocado"}, status_code=500)
    return await call_next(request)


# Expone /metrics en formato Prometheus: peticiones, latencias y códigos de estado
Instrumentator(excluded_handlers=["/health", "/metrics"]).instrument(app).expose(
    app, include_in_schema=False
)


@app.get("/")
def root() -> dict:
    return {"message": "Hola desde demo-api", "version": APP_VERSION}


@app.get("/health")
def health() -> dict:
    """Endpoint de salud para Docker HEALTHCHECK, Kubernetes probes, etc."""
    return {"status": "ok"}


@app.get("/info")
def info() -> dict:
    """Qué réplica responde: pod (hostname), nodo de Kubernetes y arquitectura de CPU."""
    return {
        "hostname": socket.gethostname(),
        "node": os.getenv("NODE_NAME", "unknown"),
        "arch": platform.machine(),
        "version": APP_VERSION,
        "time": datetime.now(UTC).isoformat(),
    }
