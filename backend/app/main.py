"""Punto de entrada de la API.

Todos los endpoints requieren un token Bearer, salvo el registro y el login.
La documentación interactiva (/docs) se controla con la variable ENABLE_DOCS.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.controllers import (
    auth_controller,
    chat_controller,
    conversations_controller,
    documents_controller,
    health_controller,
)
from app.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Base de datos lista (extensión vector y tablas verificadas).")
    yield


app = FastAPI(
    title="Agente RAG - Cyberpunk 2077",
    description="API de un agente con LangChain y LangGraph sobre la franquicia Cyberpunk 2077.",
    version="0.5.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
    redoc_url=None,
)

# CORS solo si se configuraron orígenes. La autenticación usa el header Authorization
# (no cookies), por eso allow_credentials=False.
if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth_controller.router)
app.include_router(health_controller.router)
app.include_router(documents_controller.router)
app.include_router(chat_controller.router)
app.include_router(conversations_controller.router)
