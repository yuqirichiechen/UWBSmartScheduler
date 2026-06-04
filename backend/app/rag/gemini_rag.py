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
    def select_schedule(
        self,
        constraints: Dict,
        available_courses: List[Dict],
        completed_courses: Optional[List[str]] = None,
    ) -> Optional[Dict]:
        """LLM-driven course selection.

        The model is given the student's request and the REAL available sections
        (already prereq-filtered) and returns which course+section to take, plus
        a short rationale. We then validate those picks against the real data and
        the conflict checker upstream — the LLM proposes, code disposes.

        Returns {"picks": [{"code","section_number"}...], "summary": str} or None
        if the model is unavailable / returns nothing parseable.
        """
        completed = completed_courses or []

        # Compact catalog of what's actually offered, so the model can only pick
        # real sections (prevents hallucinated courses/times).
        lines = []
        for c in available_courses:
            for s in c.get("sections", []):
                mt = (s.get("meeting_times") or [{}])[0]
                days = mt.get("days") or []
                days_s = "".join(days) if isinstance(days, list) else str(days)
                lines.append(
                    f"{c['code']} | sec {s.get('section_number', '?')} | "
                    f"{days_s or 'async'} {mt.get('start_time', '')}-{mt.get('end_time', '')} | "
                    f"{c.get('credit_hours', c.get('credits', 0))}cr | {c.get('title', '')}"
                )
        offerings = "\n".join(lines) or "(no eligible sections)"

        constraint_text = json.dumps(
            {k: v for k, v in constraints.items()
             if v not in (None, [], False, "") and k != "query"},
            default=str,
        )

        prompt = f"""You are a UW Bothell CSS academic advisor building a quarter schedule.

Pick the best set of courses+sections from the AVAILABLE OFFERINGS below that
satisfies the student's request. Rules:
- Choose ONE section per course, by its exact section letter.
- Respect hard constraints: avoided days, credit cap, required courses, time of day.
- No two chosen sections may overlap in time.
- Prefer 3-4 courses (~15 credits) unless the student asked for fewer/more.
- Only pick from the offerings listed — never invent a course or section.

STUDENT REQUEST: {constraints.get('query', '')}
PARSED CONSTRAINTS: {constraint_text}
COMPLETED COURSES: {', '.join(completed) or 'none reported'}

AVAILABLE OFFERINGS (code | section | days/time | credits | title):
{offerings}

Return ONLY a JSON object, no prose, of the form:
{{"picks": [{{"code": "CSS 342", "section_number": "A"}}], "summary": "one or two sentences explaining the choice and any tradeoff"}}"""

        try:
            raw = self._generate(prompt)
            data = _parse_json(raw)
            if not data or "picks" not in data:
                return None
            # normalize
            picks = []
            for p in data.get("picks", []):
                code = (p.get("code") or "").strip()
                sec = str(p.get("section_number") or p.get("section") or "").strip()
                if code:
                    picks.append({"code": code, "section_number": sec})
            return {"picks": picks, "summary": data.get("summary", "")}
        except Exception as e:
            logger.warning("Gemini select_schedule unavailable (%s)", _short_err(e))
            return None

    # ------------------------------------------------------------------
    def clarify_question(
        self,
        query: str,
        completed_courses: Optional[List[str]] = None,
    ) -> Dict:
        """Generate ONE multiple-choice clarifying question for a vague request.

        Returns {"question": str, "options": [3 short strings]}. Uses Gemini when
        available; otherwise a sensible default question so the UX never breaks.
        """
        completed = completed_courses or []
        fallback = {
            "question": "What's your main goal for this quarter?",
            "options": [
                "Make progress on my CSS core requirements",
                "A lighter load — electives or fewer credits",
                "Catch up on prerequisites I still need",
            ],
        }
        if not query:
            return fallback

        prompt = (
            "A UW Bothell CSS student asked a vague scheduling question. As their "
            "advisor, ask ONE short multiple-choice clarifying question that would "
            "most help you recommend the right courses. Give EXACTLY 3 concise, "
            "distinct options (each under 8 words). Don't ask what they've already "
            "told you.\n\n"
            f"STUDENT: \"{query}\"\n"
            f"COMPLETED COURSES: {', '.join(completed) or 'none reported'}\n\n"
            'Return ONLY JSON: {"question": "...", "options": ["...","...","..."]}'
        )
        try:
            data = _parse_json(self._generate(prompt))
            if data and data.get("question") and isinstance(data.get("options"), list):
                opts = [str(o).strip() for o in data["options"] if str(o).strip()][:3]
                if len(opts) >= 2:
                    return {"question": str(data["question"]).strip(), "options": opts}
        except Exception as e:
            logger.warning("Gemini clarify_question unavailable (%s)", _short_err(e))
        return fallback

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


def _parse_json(text: str) -> Optional[Dict]:
    """Parse a JSON object out of an LLM response, tolerating ```json fences."""
    if not text:
        return None
    t = text.strip()
    # strip code fences
    if t.startswith("```"):
        t = t.split("```", 2)[1] if "```" in t[3:] else t[3:]
        if t.startswith("json"):
            t = t[4:]
    # grab the outermost {...}
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(t[start:end + 1])
    except json.JSONDecodeError:
        return None


def _short_err(e: Exception) -> str:
    """Condense a noisy SDK exception (e.g. a full 429 JSON blob) to one line."""
    msg = str(e)
    if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
        return "429 quota exceeded (check GEMINI_MODEL / billing for your key)"
    if "503" in msg or "UNAVAILABLE" in msg:
        return "503 model temporarily overloaded (transient — fell back to deterministic)"
    if len(msg) > 200:
        return msg[:200] + "…"
    return msg


def _is_quota_error(e: Exception) -> bool:
    msg = str(e)
    return "RESOURCE_EXHAUSTED" in msg or "429" in msg
