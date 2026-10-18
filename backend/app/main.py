"""Punto de entrada de la API.

Todos los endpoints requieren un token Bearer, salvo el registro y el login.
La documentación interactiva (/docs) se controla con la variable ENABLE_DOCS.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.controllers import auth_controller, health_controller
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
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
    redoc_url=None,
)

app.include_router(auth_controller.router)
app.include_router(health_controller.router)
