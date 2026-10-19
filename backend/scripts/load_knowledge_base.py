"""Descarga artículos de Wikipedia (ES/EN) y de la wiki de Cyberpunk y los carga por el
mismo flujo de ingesta que POST /documents (extracción -> fragmentos -> embeddings -> PGVector).

Uso (desde backend/, con Docker y Ollama activos):
    python -m scripts.load_knowledge_base --email TU_CORREO
    python -m scripts.load_knowledge_base --email TU_CORREO --dry-run          # solo descarga y cuenta
    python -m scripts.load_knowledge_base --email TU_CORREO --sources wikipedia-es,wikipedia-en
    python -m scripts.load_knowledge_base --email TU_CORREO --limit 5          # prueba corta

Es reanudable: omite los documentos cuyo nombre de archivo ya existe en la base.
Licencia del contenido: Wikipedia (CC BY-SA 4.0) y la wiki de Cyberpunk (CC BY-SA).
"""

import argparse
import re
import sys
import time
from collections.abc import Iterator
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException
from sqlalchemy import select

from scripts.kb_sources import FANDOM_TITLES, WIKIPEDIA_TITLES

USER_AGENT = (
    "CyberpunkRAG-UniversityProject/1.0 "
    "(educational project; https://github.com/Pablo-Escudero/ImplementacionAgentes)"
)
FANDOM_API = "https://cyberpunk.fandom.com/api.php"
DEFAULT_MAX_CHARS = 60_000
MIN_BODY_CHARS = 200
PAUSE_SECONDS = 0.4
MAX_CONSECUTIVE_FAILURES = 3

STOP_SECTIONS = {
    "referencias", "enlaces externos", "véase también", "notas", "bibliografía", "notas y referencias",
    "references", "external links", "see also", "notes", "further reading", "bibliography",
    "sources", "gallery", "galería", "navigation", "videos", "trivia", "behind the scenes",
}
_HEADING = re.compile(r"^==+\s*(.+?)\s*==+$")

LICENSE_LINE = "Licencia: CC BY-SA"


# --------------------------------------------------------------------------- limpieza


def cut_trailing_sections(text: str) -> str:
    """Corta el texto en la primera sección de relleno (referencias, galería, etc.)."""
    kept = []
    for line in text.splitlines():
        m = _HEADING.match(line.strip())
        if m and m.group(1).strip().lower() in STOP_SECTIONS:
            break
        kept.append(line)
    return "\n".join(kept)


def html_to_text(html: str) -> str:
    """Convierte el HTML de una página de la wiki en texto plano (títulos como '== X ==')."""
    soup = BeautifulSoup(html, "html.parser")

    infobox = []
    for item in soup.select(".pi-data"):
        label, value = item.select_one(".pi-data-label"), item.select_one(".pi-data-value")
        if label and value:
            l, v = re.sub(r"\s+", " ", label.get_text()).strip(), re.sub(r"\s+", " ", value.get_text()).strip()
            if l and v:
                infobox.append(f"{l}: {v}")

    for selector in (
        "script", "style", "table", "aside", "figure", ".thumb", ".toc", "#toc", ".navbox",
        ".mw-editsection", "sup.reference", ".reference", ".noprint", ".gallery",
    ):
        for tag in soup.select(selector):
            tag.decompose()

    lines = []
    for el in soup.find_all(["h2", "h3", "h4", "p", "li"]):
        text = re.sub(r"\s+", " ", el.get_text()).strip()
        if not text:
            continue
        if el.name in ("h2", "h3", "h4"):
            lines.append(f"\n== {text} ==")
        elif el.name == "li":
            lines.append(f"- {text}")
        else:
            lines.append(text)

    body = "\n".join(lines)
    if infobox:
        body = "\n".join(infobox) + "\n\n" + body
    return re.sub(r"\n{3,}", "\n\n", body).strip()


def truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    boundary = cut.rfind("\n")
    return (cut[:boundary] if boundary > max_chars * 0.7 else cut).rstrip()


def safe_filename(source_key: str, title: str) -> str:
    slug = re.sub(r"[^\w\-]+", "_", title, flags=re.UNICODE).strip("_")
    return f"{source_key}__{slug}.txt"


def build_document_text(title: str, source_name: str, url: str, body: str) -> str:
    return f"{title}\nFuente: {source_name} ({url}). {LICENSE_LINE}\n\n{body}"


# --------------------------------------------------------------------------- descarga


def _get_json(client: httpx.Client, url: str, params: dict) -> dict | None:
    for attempt in range(3):
        try:
            r = client.get(url, params=params)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError):
            time.sleep(1 + attempt)
    return None


def fetch_wikipedia(client: httpx.Client, lang: str, title: str) -> tuple[str, str, str] | None:
    """Devuelve (título real, url, texto) o None si no existe."""
    data = _get_json(
        client,
        f"https://{lang}.wikipedia.org/w/api.php",
        {
            "action": "query", "prop": "extracts", "explaintext": 1, "redirects": 1,
            "titles": title, "format": "json", "formatversion": 2,
        },
    )
    pages = (data or {}).get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing") or not pages[0].get("extract"):
        return None
    page = pages[0]
    url = f"https://{lang}.wikipedia.org/wiki/{quote(page['title'].replace(' ', '_'))}"
    return page["title"], url, page["extract"]


def fetch_fandom(client: httpx.Client, title: str) -> tuple[str, str, str] | None:
    data = _get_json(
        client,
        FANDOM_API,
        {"action": "parse", "page": title, "prop": "text", "redirects": 1,
         "format": "json", "formatversion": 2},
    )
    parsed = (data or {}).get("parse")
    if not parsed or not parsed.get("text"):
        return None
    real = parsed.get("title", title)
    url = f"https://cyberpunk.fandom.com/wiki/{quote(real.replace(' ', '_'))}"
    return real, url, html_to_text(parsed["text"])


def collect(
    client: httpx.Client, sources: list[str], max_chars: int, limit: int | None
) -> Iterator[tuple[str, str]]:
    """Genera (nombre de archivo, texto) por cada artículo encontrado."""
    plan: list[tuple[str, str, str]] = []  # (source_key, source_name, title)
    for src in sources:
        if src.startswith("wikipedia-"):
            lang = src.split("-", 1)[1]
            titles = WIKIPEDIA_TITLES.get(lang, [])
            plan += [(src, f"Wikipedia ({lang.upper()})", t) for t in titles]
        elif src == "fandom":
            plan += [(src, "Cyberpunk Wiki (Fandom)", t) for t in dict.fromkeys(FANDOM_TITLES)]
        else:
            sys.exit(f"Fuente desconocida: {src}")

    seen: set[tuple[str, str]] = set()
    for source_key, source_name, title in plan:
        if limit is not None and sum(1 for k in seen if k[0] == source_key) >= limit:
            continue
        if source_key.startswith("wikipedia-"):
            found = fetch_wikipedia(client, source_key.split("-", 1)[1], title)
        else:
            found = fetch_fandom(client, title)
        time.sleep(PAUSE_SECONDS)

        if found is None:
            print(f"  [no encontrado] {source_key}: {title}")
            continue
        real_title, url, raw = found
        if (source_key, real_title) in seen:  # redirecciones al mismo artículo
            continue
        body = truncate(cut_trailing_sections(raw).strip(), max_chars)
        if len(body) < MIN_BODY_CHARS:
            print(f"  [muy corto]     {source_key}: {real_title} ({len(body)} caracteres)")
            continue
        seen.add((source_key, real_title))
        yield safe_filename(source_key, real_title), build_document_text(real_title, source_name, url, body)


# --------------------------------------------------------------------------- ingesta


def ingest_all(db, user, documents: Iterator[tuple[str, str]], dry_run: bool = False) -> dict:
    from app.models import Document
    from app.services.document_service import ingest_document

    existing = set(db.scalars(select(Document.filename)))
    stats = {"loaded": 0, "skipped": 0, "failed": 0, "chunks": 0}
    consecutive_failures = 0

    for filename, text in documents:
        if filename in existing:
            print(f"  [ya existe]     {filename}")
            stats["skipped"] += 1
            continue
        if dry_run:
            print(f"  [descargado]    {filename} ({len(text)} caracteres)")
            stats["loaded"] += 1
            continue

        started = time.time()
        try:
            doc = ingest_document(db, user, filename, "text/plain", text.encode("utf-8"))
        except HTTPException as exc:
            stats["failed"] += 1
            consecutive_failures += 1
            print(f"  [ERROR {exc.status_code}]    {filename}: {exc.detail}")
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                print("Demasiados errores seguidos: ¿Ollama está activo? Abortando (es reanudable).")
                break
            continue
        consecutive_failures = 0
        stats["loaded"] += 1
        stats["chunks"] += doc.chunk_count
        print(f"  [cargado]       {filename}: {doc.chunk_count} fragmentos en {time.time() - started:.1f}s")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", required=True, help="Correo del usuario dueño de los documentos")
    parser.add_argument("--sources", default="wikipedia-es,wikipedia-en,fandom")
    parser.add_argument("--limit", type=int, default=None, help="Máximo de artículos por fuente")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--dry-run", action="store_true", help="Descarga y cuenta, sin guardar")
    args = parser.parse_args()

    from app.database import SessionLocal
    from app.models import User

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == args.email))
        if user is None:
            sys.exit(f"No existe el usuario {args.email}. Regístralo primero con POST /auth/register.")

        sources = [s.strip() for s in args.sources.split(",") if s.strip()]
        started = time.time()
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True) as client:
            stats = ingest_all(db, user, collect(client, sources, args.max_chars, args.limit), args.dry_run)
        print(
            f"\nListo en {time.time() - started:.0f}s: {stats['loaded']} documentos, "
            f"{stats['chunks']} fragmentos, {stats['skipped']} ya existentes, {stats['failed']} con error."
        )


if __name__ == "__main__":
    main()
