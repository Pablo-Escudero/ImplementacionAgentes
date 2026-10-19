"""Esquemas de entrada y salida de la API (Pydantic)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.security import MAX_PASSWORD_BYTES

MIN_PASSWORD_LENGTH = 8


class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres")
        if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError(f"La contraseña no puede superar {MAX_PASSWORD_BYTES} bytes")
        return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    chunk_count: int
    owner_id: uuid.UUID
    created_at: datetime
    # Se calcula en el controlador: True si el usuario autenticado subió el documento.
    is_owner: bool = False


class ChatRequest(BaseModel):
    question: str = Field(max_length=2000)
    # Si se omite, se crea una conversación nueva.
    conversation_id: uuid.UUID | None = None


class SourceOut(BaseModel):
    filename: str | None = None
    document_id: str | None = None
    chunk_index: int | None = None
    excerpt: str
    score: float


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    answer: str
    sources: list[SourceOut]
    answered: bool
    language: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    sources: list[SourceOut]
    answered: bool | None
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]
