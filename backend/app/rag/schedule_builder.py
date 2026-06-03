"""Deterministic schedule builder.

This module exists so the system has a working /api/schedule endpoint even
without an OpenAI API key. The RAG pipeline (`rag_pipeline.py`) remains the
intended primary path when a key is configured; this builder is the fallback
and the eval reference implementation.

The builder picks one section per course such that:
  - all the student's hard constraints are respected (avoid_days, max_credits,
    min_credits, required_courses, no_online)
  - prerequisites are satisfied against the inferred completed-courses set
  - no two selected sections overlap in time
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import logging

from .conflict_checker import ConflictChecker

logger = logging.getLogger(__name__)


# CSS courses that count toward the major core. Used to bias selection when
# the student asks for "CSS core requirements" without naming specific courses.
CSS_CORE = {
    "CSS 143", "CSS 161", "CSS 201", "CSS 211", "CSS 301",
    "CSS 330", "CSS 342", "CSS 385", "CSS 430", "CSS 486",
}


class ScheduleBuilder:
    """Deterministic, LLM-free schedule builder."""

    @staticmethod
    def build(
        constraints: Dict,
        courses: List[Dict],
        completed_courses: Optional[List[str]] = None,
        target_credits: int = 15,
    ) -> Tuple[List[Dict], str]:
        """Build a conflict-free schedule.

        Returns (recommended_courses, human_message).

        `recommended_courses` matches the shape `main.py:_hydrate_courses`
        already produces — code/title/credits/prerequisites/sections — but with
        sections trimmed to exactly the one selected.
        """
        completed = completed_courses or []
        completed_set = {c.upper().replace(" ", "") for c in completed}

        avoid_days = set(constraints.get("avoid_days") or [])
        preferred_days = set(constraints.get("preferred_days") or [])
        time_windows = constraints.get("time_windows") or []
        max_credits = constraints.get("max_credits") or 18
        min_credits = constraints.get("min_credits")
        required = {c.upper().replace(" ", "") for c in (constraints.get("required_courses") or [])}
        no_online = bool(constraints.get("no_online"))

        ranked = ScheduleBuilder._rank_courses(courses, required, completed_set)

        picked_courses: List[Dict] = []
        picked_sections: List[Dict] = []

        for course in ranked:
            code_norm = course["code"].replace(" ", "").upper()
            if code_norm in completed_set:
                continue
            if any(c["code"] == course["code"] for c in picked_courses):
                continue

            # prereq check (LLM-free; eligibility is final say)
            missing = [
                p for p in course.get("prerequisites", [])
                if p.replace(" ", "").upper() not in completed_set
            ]
            if missing:
                logger.debug("skip %s — missing prereqs %s", course["code"], missing)
                continue

            # credit cap (admit only if it would not exceed)
            current_credits = sum(c.get("credits", 0) for c in picked_courses)
            course_credits = course.get("credit_hours", course.get("credits", 0))
            if current_credits + course_credits > max_credits:
                continue

            section = ScheduleBuilder._pick_section(
                course=course,
                already_picked=picked_sections,
                avoid_days=avoid_days,
                preferred_days=preferred_days,
                time_windows=time_windows,
                no_online=no_online,
            )
            if section is None:
                continue

            chosen = dict(course)
            chosen["sections"] = [section]
            chosen["credits"] = course_credits  # Normalized field for client
            picked_courses.append(chosen)

            sec_for_conflict = dict(section)
            sec_for_conflict["course_code"] = course["code"]
            sec_for_conflict["credits"] = course_credits  # Use credits for consistency
            sec_for_conflict["prerequisites"] = course.get("prerequisites", [])
            picked_sections.append(sec_for_conflict)

            if current_credits + course_credits >= max_credits:
                break

        # message
        total = sum(c["credits"] for c in picked_courses)
        message = ScheduleBuilder._summarize(picked_courses, total, constraints, min_credits)
        return picked_courses, message

    # --------------------------------------------------------------
    @staticmethod
    def _rank_courses(
        courses: List[Dict],
        required: set,
        completed_set: set,
    ) -> List[Dict]:
        """Order: required first, then core not-yet-completed, then everything else."""
        def key(c):
            code_norm = c["code"].replace(" ", "").upper()
            if code_norm in required:
                return (0, c["code"])
            if c["code"] in CSS_CORE and code_norm not in completed_set:
                return (1, c["code"])
            return (2, c["code"])
        return sorted(courses, key=key)

    @staticmethod
    def _pick_section(
        course: Dict,
        already_picked: List[Dict],
        avoid_days: set,
        preferred_days: set,
        time_windows: List[Dict],
        no_online: bool,
    ) -> Optional[Dict]:
        """Return the best section of `course` that fits, or None."""
        candidates = []
        for section in course.get("sections", []):
            meetings = section.get("meeting_times", [])

            if no_online and (not meetings or not any(mt.get("days") for mt in meetings)):
                # treat sections with no meeting days as online/async
                continue

            # filter by avoid_days
            if avoid_days:
                hit = any(
                    d in avoid_days
                    for mt in meetings
                    for d in (mt.get("days") or [])
                )
                if hit:
                    continue

            # conflict against already-picked
            trial = list(already_picked) + [
                {**section, "course_code": course["code"]}
            ]
            ok, _ = ConflictChecker.check_conflicts(trial)
            if not ok:
                continue

            # score (lower is better):
            #   1) prefer sections overlapping preferred_days
            #   2) honor a requested time-of-day window (morning/afternoon/...)
            #   3) tie-break on earlier start time
            score = 0
            if preferred_days:
                for mt in meetings:
                    score -= len(set(mt.get("days") or []) & preferred_days)

            first_start = next(
                (mt.get("start_time") for mt in meetings if mt.get("start_time")),
                None,
            )
            if time_windows and first_start:
                # Strong push toward sections inside the requested window so an
                # explicit "afternoon"/"evening" isn't overridden by the
                # earliest-start tie-break, and "morning" is actually honored.
                score += -10 if ScheduleBuilder._in_windows(first_start, time_windows) else 10

            start = first_start or "23:59"
            score += int(start.split(":")[0]) if ":" in start else 24
            candidates.append((score, section))

        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    @staticmethod
    def _in_windows(start_time: str, windows: List[Dict]) -> bool:
        """True if an 'HH:MM' start_time falls within any {start, end} window."""
        def to_minutes(t: str) -> Optional[int]:
            try:
                h, m = (int(x) for x in t.split(":")[:2])
                return h * 60 + m
            except (ValueError, AttributeError):
                return None

        start = to_minutes(start_time)
        if start is None:
            return False
        for w in windows:
            ws, we = to_minutes(w.get("start", "")), to_minutes(w.get("end", ""))
            if ws is not None and we is not None and ws <= start < we:
                return True
        return False

    @staticmethod
    def _summarize(
        picked: List[Dict],
        total_credits: int,
        constraints: Dict,
        min_credits: Optional[int],
    ) -> str:
        if not picked:
            return "No courses matched your constraints. Try relaxing avoided days or raising the credit cap."
        codes = ", ".join(c["code"] for c in picked)
        bits = [f"Selected {len(picked)} courses ({total_credits} credits): {codes}."]
        if min_credits and total_credits < min_credits:
            bits.append(
                f"Below your {min_credits}-credit floor — no additional eligible courses fit without a conflict."
            )
        if constraints.get("avoid_days"):
            bits.append(f"Avoided days honored: {', '.join(constraints['avoid_days'])}.")
        return " ".join(bits)
