"""Pruebas de chat e historial con SQLite en memoria y el agente con piezas simuladas."""

import uuid

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.agents import graph as agent
from app.agents.prompts import REFUSAL
from app.config import Settings
from app.database import Base, get_db
from app.dependencies import get_current_user
from app.main import app


@compiles(JSONB, "sqlite")
def _jsonb_as_json(type_, compiler, **kw):  # solo para estas pruebas con SQLite
    return "JSON"


class FakeStore:
    def __init__(self, distance):
        self.distance = distance

    def similarity_search_with_score(self, question, k=4):
        d = Document(
            page_content="Johnny Silverhand fue el vocalista de Samurai.",
            metadata={"filename": "lore.txt", "document_id": "d1", "chunk_index": 0},
        )
        return [(d, self.distance)]


class FakeLLM:
    def invoke(self, messages):
        class R:
            content = "Fue el vocalista de Samurai."

        return R()


@pytest.fixture
def env(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    db = Session()
    alice = models.User(email="alice@test.co", password_hash="x")
    bob = models.User(email="bob@test.co", password_hash="x")
    db.add_all([alice, bob])
    db.commit()
    state = {"user": alice}

    def _get_db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_current_user] = lambda: state["user"]
    monkeypatch.setattr(agent, "get_vector_store", lambda: FakeStore(0.2))
    monkeypatch.setattr(agent, "get_llm", lambda: FakeLLM())
    yield TestClient(app), state, alice, bob, monkeypatch
    app.dependency_overrides.clear()


def test_endpoints_require_token():
    client = TestClient(app)
    assert client.post("/chat", json={"question": "hola"}).status_code == 401
    assert client.get("/conversations").status_code == 401
    assert client.get(f"/conversations/{uuid.uuid4()}").status_code == 401
    assert client.delete(f"/conversations/{uuid.uuid4()}").status_code == 401


def test_chat_creates_and_continues_conversation(env):
    client, *_ = env
    r = client.post("/chat", json={"question": "¿Quién es Johnny Silverhand?"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["answered"] is True and body["sources"][0]["filename"] == "lore.txt"
    cid = body["conversation_id"]

    r2 = client.post("/chat", json={"question": "Who is Johnny Silverhand?", "conversation_id": cid})
    assert r2.json()["conversation_id"] == cid

    detail = client.get(f"/conversations/{cid}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant", "user", "assistant"]
    assert detail["messages"][1]["sources"][0]["score"] == 0.8
    assert detail["title"].startswith("¿Quién es")
    assert [c["id"] for c in client.get("/conversations").json()] == [cid]


def test_refusal_is_saved(env):
    client, _, _, _, monkeypatch = env
    monkeypatch.setattr(agent, "get_vector_store", lambda: FakeStore(0.9))
    r = client.post("/chat", json={"question": "¿Receta de sushi?"}).json()
    assert r["answered"] is False and r["answer"] == REFUSAL["es"] and r["sources"] == []
    msgs = client.get(f"/conversations/{r['conversation_id']}").json()["messages"]
    assert msgs[1]["answered"] is False and msgs[0]["answered"] is None


def test_users_are_isolated(env):
    client, state, alice, bob, _ = env
    cid = client.post("/chat", json={"question": "¿Quién es Johnny?"}).json()["conversation_id"]
    state["user"] = bob
    assert client.get("/conversations").json() == []
    assert client.get(f"/conversations/{cid}").status_code == 404
    assert client.delete(f"/conversations/{cid}").status_code == 404
    assert client.post("/chat", json={"question": "hola", "conversation_id": cid}).status_code == 404


def test_delete_conversation(env):
    client, *_ = env
    cid = client.post("/chat", json={"question": "¿Quién es Johnny?"}).json()["conversation_id"]
    assert client.delete(f"/conversations/{cid}").status_code == 204
    assert client.get(f"/conversations/{cid}").status_code == 404
    assert client.get("/conversations").json() == []


def test_ollama_failure_returns_502(env):
    client, _, _, _, monkeypatch = env

    class Broken:
        def invoke(self, messages):
            raise ConnectionError("ollama apagado")

    monkeypatch.setattr(agent, "get_llm", lambda: Broken())
    r = client.post("/chat", json={"question": "¿Quién es Johnny Silverhand?"})
    assert r.status_code == 502 and "Ollama" in r.json()["detail"]
    assert client.get("/conversations").json() == []  # nada a medias


def test_cors_origin_list_parsing():
    s = Settings(jwt_secret="x", cors_origins="http://localhost:5173/, https://front.app ,")
    assert s.cors_origin_list == ["http://localhost:5173", "https://front.app"]
    assert Settings(jwt_secret="x").cors_origin_list == []
