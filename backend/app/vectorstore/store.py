"""Acceso a la base vectorial (PGVector de langchain-postgres)."""

from functools import lru_cache

from langchain_ollama import OllamaEmbeddings
from langchain_postgres import PGVector

from app.config import get_settings
from app.database import engine


@lru_cache
def get_embeddings() -> OllamaEmbeddings:
    s = get_settings()
    return OllamaEmbeddings(model=s.embedding_model, base_url=s.ollama_base_url)


@lru_cache
def get_vector_store() -> PGVector:
    """Colección única compartida por todos los usuarios.

    Reutiliza el engine de SQLAlchemy de la aplicación. La extensión vector ya la
    activa init_db(), por eso create_extension=False.
    """
    s = get_settings()
    return PGVector(
        embeddings=get_embeddings(),
        collection_name=s.collection_name,
        connection=engine,
        use_jsonb=True,
        create_extension=False,
    )


def chunk_id(document_id: str, index: int) -> str:
    """Id determinista de cada fragmento: permite borrarlos sin consultar la tabla interna."""
    return f"{document_id}:{index}"
