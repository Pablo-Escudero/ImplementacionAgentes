"""Detección sencilla de idioma (español / inglés) sin depender del modelo."""

import re

_ES = {
    "el", "la", "los", "las", "de", "del", "que", "qué", "quién", "quien", "cómo", "como",
    "cuál", "cual", "cuáles", "es", "son", "fue", "un", "una", "y", "en", "por", "para",
    "con", "su", "sus", "se", "sobre", "dónde", "donde", "cuándo", "cuando", "hay", "tiene",
    "pasó", "pasa", "lo", "al", "me", "dime", "háblame", "información", "cuántos", "cuántas",
}
_EN = {
    "the", "who", "what", "how", "which", "is", "are", "was", "were", "of", "and", "in",
    "for", "with", "about", "where", "when", "does", "do", "did", "his", "her", "their",
    "tell", "me", "a", "an", "to", "has", "have", "why", "many", "much", "between",
}


def detect_language(text: str) -> str:
    """Devuelve 'es' o 'en'. En caso de duda, español."""
    words = re.findall(r"[a-záéíóúñü]+", text.lower())
    es = sum(w in _ES for w in words)
    en = sum(w in _EN for w in words)
    if "¿" in text or "¡" in text or re.search(r"[ñáéíóú]", text.lower()):
        es += 2
    return "en" if en > es else "es"
