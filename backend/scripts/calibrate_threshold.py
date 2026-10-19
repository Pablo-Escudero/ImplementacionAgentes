"""Ayuda para calibrar SIMILARITY_THRESHOLD.

Imprime, para cada pregunta, la similitud (1 - distancia coseno) de los fragmentos
recuperados. Edita las listas con preguntas reales de tu base de conocimiento.
Uso (desde backend/):  python -m scripts.calibrate_threshold
El umbral ideal queda ENTRE la similitud más baja de las preguntas que SÍ debe responder
y la más alta de las que debe rechazar.
"""

from app.config import get_settings
from app.vectorstore.store import get_vector_store

DEBE_RESPONDER = [
    "¿Quién es Johnny Silverhand?",
    "Who is Johnny Silverhand?",
    "¿Qué es Night City?",
    "¿Qué es Phantom Liberty?",
    "Who is David Martinez in Edgerunners?",
    "¿Qué es la cibersicosis?",
    "What is the Blackwall?",
    "¿Quién es Adam Smasher?",
    "¿Qué es Dogtown?",
    "¿Qué empresa desarrolló Cyberpunk 2077?",
    "¿Quién es Mike Pondsmith?",
]

DEBE_RECHAZAR = [
    "¿Cuál es la mejor receta para preparar sushi?",
    "¿Quién ganó el mundial de fútbol de 2018?",
    "What is the capital of France?",
    "¿Cómo se programa un bucle for en Python?",
    "Who is Geralt of Rivia?",
    "¿Quién escribió Neuromancer?",
    "¿De qué trata Blade Runner?",
    "¿Qué es The Witcher 3?",
    "¿Cuándo salió Elden Ring?",
]


def top_scores(question: str, k: int) -> list[float]:
    results = get_vector_store().similarity_search_with_score(question, k=k)
    return [round(1.0 - float(distance), 3) for _, distance in results]


if __name__ == "__main__":
    s = get_settings()
    print(f"Umbral actual: {s.similarity_threshold} | TOP_K: {s.top_k}\n")
    for title, questions in (("DEBE RESPONDER", DEBE_RESPONDER), ("DEBE RECHAZAR", DEBE_RECHAZAR)):
        print(f"== {title} ==")
        lows = []
        for q in questions:
            scores = top_scores(q, s.top_k)
            best = scores[0] if scores else None
            lows.append(best)
            print(f"{best!s:>7}  {scores}  <- {q}")
        valid = [x for x in lows if x is not None]
        if valid:
            print(f"   mejor puntaje mínimo: {min(valid)} | máximo: {max(valid)}\n")
