"""Lógica de negocio de usuarios: registro y autenticación."""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.security import hash_password, verify_password

# Hash de relleno para que el login tarde parecido exista o no el usuario.
_DUMMY_HASH = hash_password("contraseña-de-relleno")


class EmailAlreadyRegistered(Exception):
    """Ya existe un usuario con ese correo."""


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalize_email(email)))


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def register_user(db: Session, email: str, password: str) -> User:
    email = normalize_email(email)
    if get_user_by_email(db, email) is not None:
        raise EmailAlreadyRegistered(email)

    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Otro registro con el mismo correo se coló entre la consulta y el commit.
        db.rollback()
        raise EmailAlreadyRegistered(email)
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
