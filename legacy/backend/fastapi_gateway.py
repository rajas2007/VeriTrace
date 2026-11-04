"""VeriTrace Local FastAPI Application Entrypoint.

Binds exclusively to loopback (127.0.0.1) on a dynamically assigned port
communicated to the Tauri desktop shell via the local Process Supervisor.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="VeriTrace Desktop Internal API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)

# Restrict CORS to local Tauri origin and dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "tauri://localhost", "http://tauri.localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/health")
async def health_check():
    """Health endpoint queried by Tauri Process Supervisor during application startup."""
    return {
        "status": "healthy",
        "service": "veritrace-local-api",
        "version": "0.1.0"
    }
