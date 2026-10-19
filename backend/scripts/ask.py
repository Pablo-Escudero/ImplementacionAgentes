"""Prueba rápida del agente desde la terminal (no guarda historial).

Uso (desde backend/):  python -m scripts.ask "¿Quién es Johnny Silverhand?"
"""

import json
import sys

from app.agents.graph import run_agent

if __name__ == "__main__":
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        sys.exit('Uso: python -m scripts.ask "tu pregunta"')
    print(json.dumps(run_agent(question), ensure_ascii=False, indent=2))
