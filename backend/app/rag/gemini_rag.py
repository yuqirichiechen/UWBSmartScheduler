"""Gemini-backed RAG over the CSS course catalog.

Two modes:

1. File Search mode — when a `file_search_store` name is configured (produced by
   scripts/build_file_search_store.py). Gemini retrieves from the hosted store.

2. Inline-context mode — no store configured. The (small) catalog corpus is
   stuffed directly into the prompt. Works without any pre-built store, which
   is convenient for a class project / first run.

The deterministic ScheduleBuilder remains the authority on *which sections* get
picked (conflict-free, prereq-checked). Gemini's job here is to explain and
sanity-check that schedule using the catalog knowledge base, and to answer
free-form questions about courses.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class GeminiRAG:
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
        file_search_store: Optional[str] = None,
        catalog_corpus: Optional[str] = None,
        catalog_store=None,
    ):
        from google import genai  # imported lazily so the dep is optional

        self._genai = genai
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.file_search_store = file_search_store
        # `catalog_store` (a CatalogStore) lets us ground on only the *relevant*
        # courses per request instead of inlining the whole catalog — this keeps
        # input-token usage tiny, which matters a lot on the Gemini free tier.
        self.catalog_store = catalog_store
        # Full-corpus string is the last-resort grounding for free-form Q&A.
        self.catalog_corpus = catalog_corpus or (
            catalog_store.to_corpus() if catalog_store else ""
        )
        mode = "file_search" if file_search_store else "inline"
        logger.info("GeminiRAG initialized (model=%s, mode=%s)", model, mode)

    # ------------------------------------------------------------------
    def _ground_courses(self, codes: List[str]) -> str:
        """Catalog text for just the given course codes (small, targeted)."""
        if self.file_search_store or not self.catalog_store:
            return ""
        seen, docs = set(), []
        for code in codes:
            norm = code.upper().replace(" ", "")
            if norm in seen:
                continue
            seen.add(norm)
            course = self.catalog_store.get(code)
            if course:
                docs.append(self.catalog_store.to_document(course))
        if not docs:
            return ""
        return "\n\nRELEVANT CATALOG ENTRIES:\n" + "\n\n".join(docs)

    # ------------------------------------------------------------------
    def _generate(self, prompt: str, use_tools: bool = True) -> str:
        """Call generate_content, wiring the File Search tool when available."""
        config = {}
        if use_tools and self.file_search_store:
            config["tools"] = [{
                "file_search": {
                    "file_search_store_names": [self.file_search_store]
                }
            }]
        try:
            resp = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config or None,
            )
            return (getattr(resp, "text", None) or "").strip()
        except Exception as e:  # pragma: no cover — network/SDK errors
            logger.warning("Gemini generate_content failed: %s", _short_err(e))
            raise

    # ------------------------------------------------------------------
    def recommend_schedule(
        self,
        constraints: Dict,
        retrieved_courses: List[Dict],
        completed_courses: Optional[List[str]] = None,
    ) -> Dict:
        """Produce a short, grounded recommendation message for an already-built
        schedule. Returns {recommendation, recommended_courses}."""
        completed = completed_courses or []
        picked = [c.get("code") for c in retrieved_courses]

        schedule_lines = []
        for c in retrieved_courses:
            sec = (c.get("sections") or [{}])[0]
            mt = (sec.get("meeting_times") or [{}])[0]
            days = mt.get("days") or []
            days_s = " ".join(days) if isinstance(days, list) else str(days)
            schedule_lines.append(
                f"- {c.get('code')} ({c.get('credits', 0)} cr) "
                f"Sec {sec.get('section_number', '?')}: "
                f"{days_s} {mt.get('start_time', '')}-{mt.get('end_time', '')}"
            )
        schedule_text = "\n".join(schedule_lines) or "(no courses selected)"

        constraint_text = json.dumps(
            {k: v for k, v in constraints.items() if v not in (None, [], False, "")
             and k != "query"},
            default=str,
        )

        # Ground on ONLY the picked + completed courses (a handful), not the
        # whole catalog — keeps the request well under free-tier token limits.
        grounding = self._ground_courses(picked + completed)

        prompt = f"""You are a UW Bothell CSS academic advisor. A deterministic
scheduler already produced the conflict-free schedule below. Using the course
catalog as your source of truth, write a SHORT (2-3 sentence) recommendation.

Mention only what's useful: whether the schedule meets the student's stated
constraints, any prerequisite the student should be aware of, and one concrete
suggestion if relevant. Do NOT restate the whole schedule. Be concise and warm.

STUDENT QUERY: {constraints.get('query', '')}
PARSED CONSTRAINTS: {constraint_text}
COMPLETED COURSES: {', '.join(completed) or 'none reported'}

PROPOSED SCHEDULE:
{schedule_text}
{grounding}

Respond with plain text only."""

        try:
            text = self._generate(prompt)
            if not text:
                raise ValueError("empty response")
            return {"recommendation": text, "recommended_courses": picked}
        except Exception as e:
            # Return an EMPTY recommendation so the caller keeps the
            # deterministic builder's summary instead of a worse placeholder.
            logger.warning("Gemini recommendation unavailable (%s) — using deterministic summary",
                           _short_err(e))
            return {"recommendation": "", "recommended_courses": picked}

    # ------------------------------------------------------------------
    def ask(self, question: str) -> str:
        """Free-form Q&A over the catalog knowledge base."""
        grounding = ""
        if not self.file_search_store and self.catalog_corpus:
            grounding = (
                "\n\nCOURSE CATALOG:\n" + self.catalog_corpus[:120000]
            )
        prompt = (
            "You are a UW Bothell CSS advisor. Answer the student's question "
            "using the course catalog as your source of truth. Be concise and "
            "cite specific course codes where relevant.\n\n"
            f"QUESTION: {question}{grounding}"
        )
        try:
            return self._generate(prompt)
        except Exception as e:
            if _is_quota_error(e):
                return ("The catalog assistant hit its Gemini quota. Check the "
                        "model/billing for your API key and try again shortly.")
            return "Sorry — the catalog assistant is unavailable right now."


def _short_err(e: Exception) -> str:
    """Condense a noisy SDK exception (e.g. a full 429 JSON blob) to one line."""
    msg = str(e)
    if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
        return "429 quota exceeded (check GEMINI_MODEL / billing for your key)"
    if len(msg) > 200:
        return msg[:200] + "…"
    return msg


def _is_quota_error(e: Exception) -> bool:
    msg = str(e)
    return "RESOURCE_EXHAUSTED" in msg or "429" in msg
