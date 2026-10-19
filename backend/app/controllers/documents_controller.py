"""Endpoints de documentos de la base de conocimiento (todos requieren autenticación)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import DocumentOut
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["documents"])


def _to_out(doc, user: User) -> DocumentOut:
    out = DocumentOut.model_validate(doc)
    out.is_owner = doc.owner_id == user.id
    return out


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentOut:
    max_mb = get_settings().max_upload_mb
    max_bytes = max_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(
            413,
            f"El archivo supera el máximo de {max_mb} MB.",
        )
    doc = document_service.ingest_document(db, user, file.filename, file.content_type, data)
    return _to_out(doc, user)


@router.get("", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DocumentOut]:
    return [_to_out(d, user) for d in document_service.list_documents(db)]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    document_service.delete_document(db, user, document_id)
