from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .capabilities import CAPABILITY_DOCUMENT
from .models import ServiceConnectRequest
from .orchestrator_ws import OrchestratorWSClient
from .session_manager import SessionManager

logger = logging.getLogger(__name__)

session_manager = SessionManager()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Document Summarizer Agent starting")
    yield
    logger.info("Document Summarizer Agent shutting down")


app = FastAPI(
    title="Document Summarizer Agent",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _verify_orchestrator_key(key: str) -> None:
    from .config import settings

    if key != settings.ORCHESTRATOR_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid orchestrator key",
        )


@app.get("/capabilities")
async def capabilities(x_orchestrator_key: str = Header(...)) -> dict:
    _verify_orchestrator_key(x_orchestrator_key)
    return {"message": CAPABILITY_DOCUMENT}


@app.post("/connect", status_code=status.HTTP_200_OK)
async def connect(
    request: ServiceConnectRequest,
    x_orchestrator_key: str = Header(...),
) -> dict:
    _verify_orchestrator_key(x_orchestrator_key)

    state = session_manager.create(request.session_id)

    ws_client = OrchestratorWSClient(
        session_id=request.session_id,
        token=request.token,
        orchestrator_ws_url=request.orchestrator_ws_url,
        orchestrator_key=request.orchestrator_key,
        session_manager=session_manager,
    )

    state.orchestrator_ws = ws_client

    asyncio.create_task(ws_client.run())

    logger.info("Session %s created, dialling back to orchestrator", request.session_id)
    return {"status": "connected"}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "active_sessions": session_manager.active_count}
