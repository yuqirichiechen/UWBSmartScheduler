"""Course and section data models."""
from pydantic import BaseModel
from typing import List, Optional
from datetime import time


class MeetingTime(BaseModel):
    """Meeting time information for a section."""
    days: List[str]  # ['M', 'W', 'F'] or ['T', 'Th']
    start_time: time
    end_time: time
    location: Optional[str] = None


class CourseSection(BaseModel):
    """Individual course section."""
    section_number: str
    section_id: str  # SLN or internal ID
    instructor: str
    meeting_times: List[MeetingTime]
    credits: int
    capacity: Optional[int] = None
    enrolled: Optional[int] = None
    available_seats: Optional[int] = None


class Course(BaseModel):
    """Course information with sections."""
    code: str  # e.g., "CSS 342"
    title: str
    prerequisites: List[str] = []
    sections: List[CourseSection]
    credit_hours: int
    department: str


class ScheduleEntry(BaseModel):
    """A single entry in a recommended schedule."""
    course: Course
    section: CourseSection
    reason: str  # Explanation for why this was recommended


class Schedule(BaseModel):
    """Recommended schedule for a student."""
    entries: List[ScheduleEntry]
    total_credits: int
    schedule_conflicts: List[str] = []  # Empty if no conflicts
    is_valid: bool
