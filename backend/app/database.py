"""Conexión a PostgreSQL con SQLAlchemy (síncrono) y creación inicial de tablas."""

from collections.abc import Generator

from sqlalchemy import URL, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Clase base de todos los modelos."""


def _build_url() -> URL:
    s = get_settings()
    # URL.create escapa correctamente caracteres especiales en la contraseña.
    return URL.create(
        drivername="postgresql+psycopg",
        username=s.pg_user,
        password=s.pg_password,
        host=s.pg_host,
        port=s.pg_port,
        database=s.pg_db,
    )


engine = create_engine(_build_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Dependencia de FastAPI: una sesión por petición."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Activa la extensión pgvector y crea las tablas que no existan."""
    # Importar los modelos registra sus tablas en Base.metadata.
    from app import models  # noqa: F401

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(conn)
