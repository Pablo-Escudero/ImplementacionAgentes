"""Ingesta, listado y eliminación de documentos de la base de conocimiento."""

import logging
import os
import uuid

from fastapi import HTTPException, status
from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Document, User
from app.services import extraction_service
from app.services.extraction_service import ExtractionError, UnsupportedFormatError
from app.vectorstore.store import chunk_id, get_vector_store

logger = logging.getLogger("app.documents")

EMBED_BATCH_SIZE = 32


def _split(text: str) -> list[str]:
    s = get_settings()
    splitter = RecursiveCharacterTextSplitter(chunk_size=s.chunk_size, chunk_overlap=s.chunk_overlap)
    return [c for c in splitter.split_text(text) if c.strip()]


def _remove_vectors(document_id: uuid.UUID, count: int) -> None:
    if count <= 0:
        return
    ids = [chunk_id(str(document_id), i) for i in range(count)]
    get_vector_store().delete(ids=ids)


def ingest_document(
    db: Session, user: User, filename: str, content_type: str | None, data: bytes
) -> Document:
    filename = os.path.basename(filename or "").strip()[:255] or "sin_nombre"

    try:
        text = extraction_service.extract_text(filename, data)
    except UnsupportedFormatError:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Formato no soportado. Usa PDF, TXT, MD, CSV o DOCX.",
        )
    except ExtractionError as exc:
        raise HTTPException(422, str(exc))

    chunks = _split(text)
    if not chunks:
        raise HTTPException(422, "El documento no contiene texto útil.")

    doc = Document(
        filename=filename,
        content_type=(content_type or "application/octet-stream")[:100],
        size_bytes=len(data),
        chunk_count=0,
        owner_id=user.id,
    )
    db.add(doc)
    db.flush()  # asigna el id sin confirmar todavía

    store = get_vector_store()
    doc_id = str(doc.id)
    stored = 0
    try:
        for start in range(0, len(chunks), EMBED_BATCH_SIZE):
            batch = chunks[start : start + EMBED_BATCH_SIZE]
            lc_docs = [
                LCDocument(
                    page_content=chunk,
                    metadata={
                        "document_id": doc_id,
                        "filename": filename,
                        "chunk_index": start + i,
                    },
                )
                for i, chunk in enumerate(batch)
            ]
            ids = [chunk_id(doc_id, start + i) for i in range(len(batch))]
            store.add_documents(lc_docs, ids=ids)
            stored += len(batch)
        doc.chunk_count = stored
        db.commit()
    except Exception:
        logger.exception("Falló la ingesta de %s", filename)
        db.rollback()
        try:
            _remove_vectors(uuid.UUID(doc_id), len(chunks))
        except Exception:
            logger.exception("No se pudieron limpiar los fragmentos de %s", filename)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "No se pudieron generar o guardar los embeddings. Verifica que Ollama esté activo "
            "y que el modelo de embeddings esté descargado.",
        )
    return doc


def list_documents(db: Session) -> list[Document]:
    return list(db.scalars(select(Document).order_by(Document.created_at.desc())))


def delete_document(db: Session, user: User, document_id: uuid.UUID) -> None:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado.")
    if doc.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo quien subió el documento puede eliminarlo.")

    try:
        _remove_vectors(doc.id, doc.chunk_count)
    except Exception:
        logger.exception("No se pudieron borrar los fragmentos de %s", doc.id)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "No se pudieron eliminar los fragmentos de la base vectorial.",
        )
    db.delete(doc)
    db.commit()
