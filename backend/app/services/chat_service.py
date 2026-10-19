"""Lógica de chat e historial de conversaciones."""

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.agents.graph import run_agent
from app.models import Conversation, User

logger = logging.getLogger("app.chat")


def _get_owned_conversation(db: Session, user: User, conversation_id: uuid.UUID) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    # Una conversación ajena responde igual que una inexistente (no revela que existe).
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversación no encontrada.")
    return conversation


def ask(db: Session, user: User, question: str, conversation_id: uuid.UUID | None) -> dict:
    if conversation_id is not None:
        _get_owned_conversation(db, user, conversation_id)  # falla rápido, antes de usar el modelo

    try:
        result = run_agent(
            question,
            db=db,
            user=user,
            conversation_id=str(conversation_id) if conversation_id else None,
        )
    except Exception:
        logger.exception("Falló la ejecución del agente")
        db.rollback()
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "No se pudo consultar el modelo local. Verifica que Ollama esté activo "
            "y que los modelos estén descargados.",
        )
    return result


def list_conversations(db: Session, user: User) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
    )
    return list(db.scalars(stmt))


def get_conversation(db: Session, user: User, conversation_id: uuid.UUID) -> Conversation:
    conversation = db.scalar(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    )
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversación no encontrada.")
    return conversation


def delete_conversation(db: Session, user: User, conversation_id: uuid.UUID) -> None:
    conversation = _get_owned_conversation(db, user, conversation_id)
    db.delete(conversation)
    db.commit()
