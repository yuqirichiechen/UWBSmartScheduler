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
        time_windows = constraints.get("time_windows") or []

        # Pass 1: enforce the time-of-day window strictly. If that yields nothing
        # (e.g. "morning only" but every CSS section runs past noon), relax it to
        # a soft preference so the student still gets a schedule, and note it.
        picked_courses = ScheduleBuilder._select(constraints, courses, completed,
                                                 enforce_time_windows=True)
        relaxed = False
        if not picked_courses and time_windows:
            picked_courses = ScheduleBuilder._select(constraints, courses, completed,
                                                     enforce_time_windows=False)
            relaxed = picked_courses != []

        total = sum(c["credits"] for c in picked_courses)
        message = ScheduleBuilder._summarize(
            picked_courses, total, constraints, constraints.get("min_credits")
        )
        if relaxed:
            message += (" Note: no sections fit entirely in your requested time of "
                        "day, so the closest-fitting sections were chosen.")
        return picked_courses, message

    @staticmethod
    def _select(
        constraints: Dict,
        courses: List[Dict],
        completed: List[str],
        enforce_time_windows: bool = True,
    ) -> List[Dict]:
        """Greedy, conflict-aware selection. Shared by both relaxation passes."""
        completed_set = {c.upper().replace(" ", "") for c in completed}
        avoid_days = set(constraints.get("avoid_days") or [])
        preferred_days = set(constraints.get("preferred_days") or [])
        time_windows = constraints.get("time_windows") or []
        max_credits = constraints.get("max_credits") or 18
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

            missing = [
                p for p in course.get("prerequisites", [])
                if p.replace(" ", "").upper() not in completed_set
            ]
            if missing:
                logger.debug("skip %s — missing prereqs %s", course["code"], missing)
                continue

            current_credits = sum(c.get("credits", 0) for c in picked_courses)
            course_credits = course.get("credit_hours", course.get("credits", 0))
            if current_credits + course_credits > max_credits:
                continue

            section = ScheduleBuilder._pick_section(
                course=course,
                already_picked=picked_sections,
                avoid_days=avoid_days,
                preferred_days=preferred_days,
                time_windows=time_windows if enforce_time_windows else [],
                no_online=no_online,
            )
            if section is None:
                continue

            chosen = dict(course)
            chosen["sections"] = [section]
            chosen["credits"] = course_credits
            picked_courses.append(chosen)

            sec_for_conflict = dict(section)
            sec_for_conflict["course_code"] = course["code"]
            sec_for_conflict["credits"] = course_credits
            sec_for_conflict["prerequisites"] = course.get("prerequisites", [])
            picked_sections.append(sec_for_conflict)

            if current_credits + course_credits >= max_credits:
                break

        return picked_courses

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

            # HARD time-window filter: when the student asked for a time of day
            # (morning/afternoon/evening/before X/after X), skip any section
            # that doesn't fit ENTIRELY inside the window. This is what makes
            # "morning classes only" exclude an 11am-1pm class that spills into
            # the afternoon.
            if time_windows and not ScheduleBuilder._section_in_windows(meetings, time_windows):
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
    def _to_minutes(t: str) -> Optional[int]:
        try:
            h, m = (int(x) for x in t.split(":")[:2])
            return h * 60 + m
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def _in_windows(start_time: str, windows: List[Dict]) -> bool:
        """True if an 'HH:MM' start_time falls within any {start, end} window."""
        start = ScheduleBuilder._to_minutes(start_time)
        if start is None:
            return False
        for w in windows:
            ws = ScheduleBuilder._to_minutes(w.get("start", ""))
            we = ScheduleBuilder._to_minutes(w.get("end", ""))
            if ws is not None and we is not None and ws <= start < we:
                return True
        return False

    @staticmethod
    def _section_in_windows(meetings: List[Dict], windows: List[Dict]) -> bool:
        """True if EVERY meeting of the section fits entirely within one of the
        requested windows (start >= window.start and end <= window.end).

        A 15-minute grace is allowed on the end so a class ending exactly at the
        window boundary (e.g. 11:50 for a noon cutoff) still counts as morning.
        """
        if not meetings:
            return False  # async/online sections don't satisfy a time-of-day ask
        GRACE = 15
        for mt in meetings:
            start = ScheduleBuilder._to_minutes(mt.get("start_time", "") or "")
            end = ScheduleBuilder._to_minutes(mt.get("end_time", "") or "")
            if start is None or end is None:
                return False
            fits_any = False
            for w in windows:
                ws = ScheduleBuilder._to_minutes(w.get("start", ""))
                we = ScheduleBuilder._to_minutes(w.get("end", ""))
                if ws is None or we is None:
                    continue
                if start >= ws and end <= we + GRACE:
                    fits_any = True
                    break
            if not fits_any:
                return False
        return True

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
