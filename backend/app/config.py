"""Configuración de la aplicación, leída de variables de entorno o del archivo .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env en la raíz del repositorio (backend/app/config.py -> raíz = parents[2]).
# Si el archivo no existe (por ejemplo en Docker), se usan solo las variables de entorno.
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Base de datos
    pg_user: str = "postgres"
    pg_password: str = "postgres"
    pg_db: str = "cyberpunk_agent"
    pg_host: str = "localhost"
    pg_port: int = 5433

    # Autenticación
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Documentación interactiva (Swagger en /docs). Desactívala en producción.
    enable_docs: bool = True

    # Modelo local (Ollama)
    ollama_base_url: str = "http://localhost:11434"
    chat_model: str = "qwen2.5:3b"
    embedding_model: str = "bge-m3"

    # RAG
    collection_name: str = "cyberpunk_kb"
    chunk_size: int = 1000
    chunk_overlap: int = 150
    top_k: int = 4
    similarity_threshold: float = 0.5

    # Carga de documentos
    max_upload_mb: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()
