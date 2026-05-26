"""Vercel serverless entrypoint.

Vercel auto-detects FastAPI apps and serves them as ASGI. This file just adds
the project root to sys.path so the existing `backend/main.py` app can be
imported as-is, then re-exports the FastAPI instance as `app`.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Mark the runtime so backend code can skip cold-start-unfriendly work
# (live scraping, embedding generation) when deployed.
os.environ.setdefault("SMARTSCHED_SERVERLESS", "1")

# Make `backend/` importable from this file's location (project_root/api/).
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "backend"))

# Import the existing FastAPI app. Vercel detects this `app` attribute and
# serves it as an ASGI handler.
from main import app  # noqa: E402,F401
