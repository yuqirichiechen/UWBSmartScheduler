"""Load and serve the bundled CSS course-catalog snapshot.

The snapshot (css_catalog.json) is produced by parse_catalog.py from the
descriptions text. This module is the read-side: load it, look courses up by
code, and render it into documents for the RAG knowledge base.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_HERE = Path(__file__).resolve().parent
_SNAPSHOT = _HERE.parent.parent / "data" / "catalog" / "css_catalog.json"


def load_catalog(path: Optional[Path] = None) -> List[Dict]:
    """Load the parsed catalog snapshot. Returns [] if missing."""
    p = Path(path) if path else _SNAPSHOT
    if not p.exists():
        logger.warning("Catalog snapshot not found at %s", p)
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load catalog snapshot: %s", e)
        return []


class CatalogStore:
    """In-memory view over the course catalog snapshot."""

    def __init__(self, courses: Optional[List[Dict]] = None):
        self.courses = courses if courses is not None else load_catalog()
        self._by_code = {self._norm(c["code"]): c for c in self.courses}

    @staticmethod
    def _norm(code: str) -> str:
        return code.upper().replace(" ", "")

    def get(self, code: str) -> Optional[Dict]:
        return self._by_code.get(self._norm(code))

    def prerequisites(self, code: str) -> List[str]:
        c = self.get(code)
        return c.get("prerequisite_codes", []) if c else []

    def __len__(self) -> int:
        return len(self.courses)

    # -- RAG document rendering ------------------------------------------

    def to_document(self, course: Dict) -> str:
        """Render a single course as a self-contained text chunk for retrieval."""
        lines = [f"{course['code']} — {course['title']} ({course['credits']} credits)"]
        if course.get("attributes"):
            lines.append(f"Gen-ed attributes: {', '.join(course['attributes'])}")
        if course.get("description"):
            lines.append(course["description"])
        if course.get("prerequisite_text"):
            lines.append(f"Prerequisite: {course['prerequisite_text']}.")
        if course.get("prerequisite_codes"):
            lines.append(f"Prerequisite course codes: {', '.join(course['prerequisite_codes'])}.")
        if course.get("offered"):
            lines.append(f"Offered: {course['offered']}.")
        return "\n".join(lines)

    def to_corpus(self) -> str:
        """One big document combining every course — handy for File Search upload."""
        return "\n\n".join(self.to_document(c) for c in self.courses)

    def to_documents(self) -> List[Dict]:
        """List of {code, title, text} per course for per-file uploads."""
        return [
            {"code": c["code"], "title": c["title"], "text": self.to_document(c)}
            for c in self.courses
        ]
