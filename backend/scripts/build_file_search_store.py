"""One-time builder for the Gemini File Search store.

Creates a hosted File Search store, uploads the CSS catalog corpus, and prints
the store name. Put that name into the GEMINI_FILE_SEARCH_STORE env var (locally
in backend/.env, on Vercel in Project Settings) so the backend queries the
hosted store instead of inlining the catalog into each prompt.

Usage:
    cd backend && source venv/bin/activate
    export GEMINI_API_KEY=...        # or put it in backend/.env
    python -m scripts.build_file_search_store

Re-running creates a NEW store each time; delete old ones from the Google AI
Studio / API if you don't want them to pile up.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Make `app` importable when run as a module from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.catalog import CatalogStore  # noqa: E402

try:
    from app.config import settings
    DEFAULT_KEY = settings.gemini_api_key
    EMBED_MODEL = settings.gemini_embedding_model
except Exception:  # pragma: no cover
    DEFAULT_KEY = os.environ.get("GEMINI_API_KEY")
    EMBED_MODEL = os.environ.get("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")


def main() -> int:
    api_key = os.environ.get("GEMINI_API_KEY") or DEFAULT_KEY
    if not api_key:
        print("ERROR: set GEMINI_API_KEY (env var or backend/.env)")
        return 1

    store = CatalogStore()
    if len(store) == 0:
        print("ERROR: catalog snapshot is empty. Run: python -m app.catalog.parse_catalog")
        return 1
    print(f"Loaded {len(store)} courses from the catalog snapshot.")

    from google import genai

    client = genai.Client(api_key=api_key)

    print("Creating File Search store…")
    fs_store = client.file_search_stores.create(
        config={
            "display_name": "uwb-css-catalog",
            "embedding_model": EMBED_MODEL,
        }
    )
    print(f"  store name: {fs_store.name}")

    # Write the corpus to a temp file and upload it.
    corpus = store.to_corpus()
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        fh.write(corpus)
        corpus_path = fh.name

    print("Uploading catalog corpus…")
    op = client.file_search_stores.upload_to_file_search_store(
        file=corpus_path,
        file_search_store_name=fs_store.name,
        config={"display_name": "uwb-css-course-catalog"},
    )
    # Best-effort wait if the SDK returns a long-running operation
    try:
        while not getattr(op, "done", True):
            import time
            time.sleep(2)
            op = client.operations.get(op)
    except Exception:
        pass

    os.unlink(corpus_path)

    print("\nDone. Set this in your environment:")
    print(f"  GEMINI_FILE_SEARCH_STORE={fs_store.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
