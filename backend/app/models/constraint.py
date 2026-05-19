"""Constraint models for schedule requests."""
from pydantic import BaseModel
from typing import Optional, List


class ScheduleConstraint(BaseModel):
    """Constraints extracted from user query."""
    query: str  # Original user query
    max_credits: Optional[int] = None
    min_credits: Optional[int] = None
    preferred_days: Optional[List[str]] = None  # ['T', 'Th']
    avoid_days: Optional[List[str]] = None  # ['F']
    time_windows: Optional[List[dict]] = None  # [{"start": "09:00", "end": "17:00"}]
    required_courses: Optional[List[str]] = None  # ["CSS 342", "CSS 385"]
    prerequisites_met: Optional[List[str]] = None  # Courses student has already taken
    no_online: Optional[bool] = False
