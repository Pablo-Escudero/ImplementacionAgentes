"""Pruebas de hash de contraseñas, tokens JWT y validación de esquemas (sin base de datos)."""

import uuid

import pytest
from pydantic import ValidationError

from app.schemas import UserCreate
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_y_verificacion_de_contrasena():
    hashed = hash_password("clave-segura-123")
    assert hashed != "clave-segura-123"
    assert verify_password("clave-segura-123", hashed)
    assert not verify_password("otra-clave", hashed)


def test_token_valido_devuelve_el_sujeto():
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id)
    assert decode_access_token(token) == user_id


def test_token_manipulado_es_rechazado():
    token = create_access_token(str(uuid.uuid4()))
    assert decode_access_token(token + "x") is None
    assert decode_access_token("no-es-un-token") is None


def test_esquema_acepta_datos_validos():
    user = UserCreate(email="v@nightcity.com", password="clave-segura-123")
    assert user.email == "v@nightcity.com"


@pytest.mark.parametrize(
    "email, password",
    [
        ("no-es-un-correo", "clave-segura-123"),
        ("v@nightcity.com", "corta"),
        ("v@nightcity.com", "a" * 73),
    ],
)
def test_esquema_rechaza_datos_invalidos(email, password):
    with pytest.raises(ValidationError):
        UserCreate(email=email, password=password)
