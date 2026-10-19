"""Agente RAG con LangGraph.

Flujo:
    validate_intent -> retrieve -> grade_context -> generate -> save_history
                  \\__________________\\__ reject __________/

Estrategias anti-alucinación: umbral de similitud (grade_context), nodo dedicado a validar
el contexto, prompt que obliga a usar solo lo recuperado, marcador NO_INFO del modelo,
rechazo explícito y fuentes citadas.
"""

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from app.agents.language import detect_language
from app.agents.prompts import (
    CLARIFY,
    LANGUAGE_NAME,
    NO_INFO_MARKER,
    REFUSAL,
    SYSTEM_PROMPT,
)
from app.config import get_settings
from app.vectorstore.store import get_vector_store

logger = logging.getLogger("app.agent")

MIN_QUESTION_CHARS = 3
BLOCKLIST = [
    "witcher", "geralt", "blade runner", "neuromancer", "harry potter", 
    "elden ring", "sushi", "fútbol", "capital of france", "python"
]
MAX_QUESTION_CHARS = 500
EXCERPT_CHARS = 200
NUM_CTX = 4096


class AgentState(TypedDict, total=False):
    question: str
    language: str
    valid: bool
    domain_valid: bool
    retrieved: list[dict[str, Any]]  # todo lo recuperado, con puntaje
    relevant: list[dict[str, Any]]  # lo que supera el umbral
    answer: str
    sources: list[dict[str, Any]]
    answered: bool
    conversation_id: str | None


@lru_cache
def get_llm() -> ChatOllama:
    s = get_settings()
    return ChatOllama(
        model=s.chat_model,
        base_url=s.ollama_base_url,
        temperature=0,
        num_ctx=NUM_CTX,
    )


def _excerpt(text: str) -> str:
    flat = re.sub(r"\s+", " ", text).strip()
    return flat if len(flat) <= EXCERPT_CHARS else flat[:EXCERPT_CHARS].rstrip() + "…"


# ----------------------------------------------------------------------------- nodos


def validate_intent(state: AgentState) -> AgentState:
    """Nodo 1-2: recibe la pregunta, detecta el idioma y valida que sea procesable y del dominio."""
    question = (state.get("question") or "").strip()
    language = detect_language(question)
    valid = MIN_QUESTION_CHARS <= len(question) <= MAX_QUESTION_CHARS
    domain_valid = True
    
    if valid:
        # 1. Filtro determinista (Blocklist)
        q_lower = question.lower()
        if any(word in q_lower for word in BLOCKLIST):
            domain_valid = False
        else:
            # 2. Filtro LLM (para preguntas no listadas)
            prompt = (
                "Answer strictly YES or NO. Is the following question about the Cyberpunk franchise "
                "(Cyberpunk 2077, Phantom Liberty, Cyberpunk: Edgerunners, Cyberpunk tabletop RPG, "
                "its characters, lore, or locations)?\n"
                f"Question: {question}"
            )
            try:
                reply = get_llm().invoke(prompt).content.strip().upper()
                if "NO" in reply and "YES" not in reply:
                    domain_valid = False
            except Exception as e:
                logger.error("Error en validación de intención: %s", e)
            
    return {"question": question, "language": language, "valid": valid, "domain_valid": domain_valid}


def retrieve(state: AgentState) -> AgentState:
    """Nodo 3: búsqueda por similitud en la base vectorial (distancia coseno -> similitud)."""
    k = get_settings().top_k
    results = get_vector_store().similarity_search_with_score(state["question"], k=k)
    retrieved = []
    for doc, distance in results:
        retrieved.append(
            {
                "text": doc.page_content,
                "filename": doc.metadata.get("filename"),
                "document_id": doc.metadata.get("document_id"),
                "chunk_index": doc.metadata.get("chunk_index"),
                "score": round(1.0 - float(distance), 4),
            }
        )
    return {"retrieved": retrieved}


def grade_context(state: AgentState) -> AgentState:
    """Nodo 4: valida la relevancia. Solo pasan los fragmentos sobre el umbral de similitud."""
    threshold = get_settings().similarity_threshold
    relevant = [r for r in state.get("retrieved", []) if r["score"] >= threshold]
    logger.info(
        "Contexto: %d recuperados, %d sobre el umbral %.2f",
        len(state.get("retrieved", [])),
        len(relevant),
        threshold,
    )
    return {"relevant": relevant}


def generate(state: AgentState) -> AgentState:
    """Nodo 5: responde usando solo el contexto relevante."""
    relevant = state["relevant"]
    context = "\n\n".join(
        f"[{i}] ({r['filename']}) {r['text']}" for i, r in enumerate(relevant, start=1)
    )
    system = SYSTEM_PROMPT.format(
        marker=NO_INFO_MARKER,
        language=LANGUAGE_NAME[state["language"]],
        context=context,
    )
    reply = get_llm().invoke([SystemMessage(content=system), HumanMessage(content=state["question"])])
    answer = (reply.content if isinstance(reply.content, str) else str(reply.content)).strip()

    if not answer or NO_INFO_MARKER in answer:
        # El propio modelo indica que el contexto no alcanza: se trata como rechazo.
        return {"answer": "", "answered": False}

    sources = [
        {
            "filename": r["filename"],
            "document_id": r["document_id"],
            "chunk_index": r["chunk_index"],
            "excerpt": _excerpt(r["text"]),
            "score": r["score"],
        }
        for r in relevant
    ]
    return {"answer": answer, "sources": sources, "answered": True}


def reject(state: AgentState) -> AgentState:
    """Nodo 6: rechazo explícito (o petición de aclaración si la pregunta no es válida)."""
    lang = state.get("language", "es")
    message = REFUSAL[lang] if state.get("valid") else CLARIFY[lang]
    return {"answer": message, "sources": [], "answered": False}


def save_history(state: AgentState, config: RunnableConfig) -> AgentState:
    """Nodo 7: guarda la interacción. Sin sesión de base de datos no hace nada."""
    cfg = config.get("configurable", {})
    db = cfg.get("db")
    user = cfg.get("user")
    if db is None or user is None:
        return {}

    from app.models import Conversation, Message  # evita importaciones circulares

    conversation_id = state.get("conversation_id")
    if conversation_id:
        conversation = db.get(Conversation, uuid.UUID(conversation_id))
        if conversation is None or conversation.user_id != user.id:
            raise ValueError("Conversación no encontrada")
    else:
        conversation = Conversation(user_id=user.id, title=state["question"][:60])
        db.add(conversation)
        db.flush()

    now = datetime.now(timezone.utc)
    db.add(
        Message(
            conversation_id=conversation.id,
            role="user",
            content=state["question"],
            sources=[],
            answered=None,
            created_at=now,
        )
    )
    db.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content=state["answer"],
            sources=state.get("sources", []),
            answered=state.get("answered", False),
            created_at=now + timedelta(milliseconds=1),
        )
    )
    db.commit()
    return {"conversation_id": str(conversation.id)}


# ----------------------------------------------------------------------------- grafo

def _after_validate(state: AgentState) -> str:
    if not state.get("valid", False):
        return "reject"
    if not state.get("domain_valid", True):
        return "reject"
    return "retrieve"


def _after_grade(state: AgentState) -> str:
    return "generate" if state.get("relevant") else "reject"


def _after_generate(state: AgentState) -> str:
    return "save_history" if state.get("answered") else "reject"


@lru_cache
def get_graph():
    g = StateGraph(AgentState)
    g.add_node("validate_intent", validate_intent)
    g.add_node("retrieve", retrieve)
    g.add_node("grade_context", grade_context)
    g.add_node("generate", generate)
    g.add_node("reject", reject)
    g.add_node("save_history", save_history)

    g.add_edge(START, "validate_intent")
    g.add_conditional_edges("validate_intent", _after_validate, {"retrieve": "retrieve", "reject": "reject"})
    g.add_edge("retrieve", "grade_context")
    g.add_conditional_edges("grade_context", _after_grade, {"generate": "generate", "reject": "reject"})
    g.add_conditional_edges("generate", _after_generate, {"save_history": "save_history", "reject": "reject"})
    g.add_edge("reject", "save_history")
    g.add_edge("save_history", END)
    return g.compile()


def run_agent(
    question: str,
    db=None,
    user=None,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    """Ejecuta el grafo. Con db y user guarda el historial; sin ellos solo responde."""
    final = get_graph().invoke(
        {"question": question, "conversation_id": conversation_id},
        config={"configurable": {"db": db, "user": user}},
    )
    return {
        "answer": final["answer"],
        "sources": final.get("sources", []),
        "answered": final.get("answered", False),
        "language": final.get("language", "es"),
        "conversation_id": final.get("conversation_id"),
    }
