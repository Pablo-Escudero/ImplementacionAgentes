import pytest
from langchain_core.documents import Document

from app.agents import graph as agent
from app.agents.language import detect_language
from app.agents.prompts import REFUSAL


class FakeStore:
    def __init__(self, results):
        self.results = results

    def similarity_search_with_score(self, question, k=4):
        return self.results[:k]


class FakeLLM:
    def __init__(self, text):
        self.text = text
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        self.system = messages[0].content

        class R:
            content = self.text

        return R()


def doc(text="Johnny Silverhand fue el vocalista de Samurai.", idx=0):
    return Document(page_content=text, metadata={"filename": "lore.txt", "document_id": "d1", "chunk_index": idx})


@pytest.fixture
def setup(monkeypatch):
    def _setup(results, llm_text="Fue el vocalista de Samurai."):
        llm = FakeLLM(llm_text)
        monkeypatch.setattr(agent, "get_vector_store", lambda: FakeStore(results))
        monkeypatch.setattr(agent, "get_llm", lambda: llm)
        return llm

    return _setup


def test_language_detection():
    assert detect_language("¿Quién es Johnny Silverhand?") == "es"
    assert detect_language("Who is Johnny Silverhand?") == "en"
    assert detect_language("Tell me about Night City") == "en"
    assert detect_language("Johnny Silverhand") == "es"  # sin pistas -> español


def test_answers_with_sources(setup):
    llm = setup([(doc(), 0.2)])  # distancia 0.2 -> similitud 0.8
    r = agent.run_agent("¿Quién es Johnny Silverhand?")
    assert r["answered"] is True and r["answer"] == "Fue el vocalista de Samurai."
    assert r["sources"][0]["filename"] == "lore.txt"
    assert r["sources"][0]["score"] == 0.8 and r["sources"][0]["chunk_index"] == 0
    assert "Spanish" in llm.system and "Johnny Silverhand fue" in llm.system


def test_rejects_below_threshold_without_calling_llm(setup):
    llm = setup([(doc(), 0.8)])  # similitud 0.2 < umbral 0.5
    r = agent.run_agent("¿Receta de sushi?")
    assert r["answered"] is False and r["answer"] == REFUSAL["es"] and r["sources"] == []
    assert llm.calls == 0


def test_rejects_in_english(setup):
    setup([])
    r = agent.run_agent("What is the best sushi recipe?")
    assert r["answer"] == REFUSAL["en"] and r["language"] == "en"


def test_model_no_info_marker_becomes_refusal(setup):
    llm = setup([(doc(), 0.2)], llm_text="NO_INFO")
    r = agent.run_agent("¿Quién es el hermano de Johnny Silverhand?")
    assert llm.calls == 1 and r["answered"] is False and r["answer"] == REFUSAL["es"]


def test_invalid_question_asks_clarification(setup):
    llm = setup([(doc(), 0.1)])
    for q in ("  ", "a", "x" * 501):
        r = agent.run_agent(q)
        assert r["answered"] is False and r["answer"] != REFUSAL["es"]
    assert llm.calls == 0


def test_only_relevant_chunks_in_prompt(setup):
    llm = setup([(doc("fragmento bueno", 0), 0.2), (doc("fragmento malo", 1), 0.9)])
    r = agent.run_agent("¿Quién es Johnny?")
    assert "fragmento bueno" in llm.system and "fragmento malo" not in llm.system
    assert len(r["sources"]) == 1
