"""Schedule conflict detection."""
from datetime import datetime, time
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class ConflictChecker:
    """Detects scheduling conflicts between courses."""
    
    @staticmethod
    def check_conflicts(sections: List[Dict]) -> Tuple[bool, List[str]]:
        """Check for conflicts between sections.
        
        Args:
            sections: List of course sections with meeting times
            
        Returns:
            Tuple of (no_conflicts, conflict_descriptions)
        """
        conflicts = []
        
        if not sections or len(sections) < 2:
            return True, []
        
        for i in range(len(sections)):
            for j in range(i + 1, len(sections)):
                conflict = ConflictChecker._check_section_pair_conflict(
                    sections[i], sections[j]
                )
                if conflict:
                    conflicts.append(conflict)
                    logger.warning(f"Conflict detected: {conflict}")
        
        no_conflicts = len(conflicts) == 0
        return no_conflicts, conflicts
    
    @staticmethod
    def _check_section_pair_conflict(section1: Dict, section2: Dict) -> str:
        """Check if two sections conflict and return description.
        
        Args:
            section1: First section
            section2: Second section
            
        Returns:
            Conflict description or empty string if no conflict
        """
        meetings1 = section1.get('meeting_times', [])
        meetings2 = section2.get('meeting_times', [])
        
        course1 = section1.get('course_code', 'Unknown')
        section1_num = section1.get('section_number', 'A')
        course2 = section2.get('course_code', 'Unknown')
        section2_num = section2.get('section_number', 'A')
        
        for m1 in meetings1:
            for m2 in meetings2:
                if ConflictChecker._meetings_overlap(m1, m2):
                    return f"{course1} Section {section1_num} overlaps with {course2} Section {section2_num}"
        
        return ""
    
    @staticmethod
    def _meetings_overlap(meeting1: Dict, meeting2: Dict) -> bool:
        """Check if two meeting times overlap.
        
        Args:
            meeting1: First meeting with days, start_time, end_time
            meeting2: Second meeting with days, start_time, end_time
            
        Returns:
            True if meetings overlap on any day
        """
        days1 = set(meeting1.get('days', []))
        days2 = set(meeting2.get('days', []))
        
        # If no shared days, no conflict
        if not days1 or not days2 or not days1.intersection(days2):
            return False
        
        # Convert times to comparable format
        start1 = ConflictChecker._time_to_minutes(meeting1.get('start_time', '00:00'))
        end1 = ConflictChecker._time_to_minutes(meeting1.get('end_time', '00:00'))
        start2 = ConflictChecker._time_to_minutes(meeting2.get('start_time', '00:00'))
        end2 = ConflictChecker._time_to_minutes(meeting2.get('end_time', '00:00'))
        
        # Check if times overlap (allowing no same-minute starts/ends)
        # Conflict if: start1 < end2 AND start2 < end1
        return start1 < end2 and start2 < end1
    
    @staticmethod
    def _time_to_minutes(time_str: str) -> int:
        """Convert time string to minutes since midnight.
        
        Args:
            time_str: Time string in format "HH:MM" or time object
            
        Returns:
            Minutes since midnight
        """
        if isinstance(time_str, time):
            return time_str.hour * 60 + time_str.minute
        
        try:
            if isinstance(time_str, str):
                parts = time_str.split(':')
                hours = int(parts[0])
                minutes = int(parts[1]) if len(parts) > 1 else 0
                return hours * 60 + minutes
        except (ValueError, IndexError, AttributeError):
            logger.warning(f"Could not parse time: {time_str}")
            return 0
        
        return 0
    
    @staticmethod
    def check_prerequisite_eligibility(
        course_code: str,
        prerequisites: List[str],
        completed_courses: List[str]
    ) -> Tuple[bool, List[str]]:
        """Check if student is eligible for a course based on prerequisites.
        
        Args:
            course_code: Course to check
            prerequisites: List of prerequisite courses
            completed_courses: Courses student has completed
            
        Returns:
            Tuple of (is_eligible, missing_prerequisites)
        """
        completed_set = set(c.upper() for c in completed_courses)
        missing = []
        
        for prereq in prerequisites:
            if prereq.upper() not in completed_set:
                missing.append(prereq)
                logger.debug(f"Student missing prerequisite {prereq} for {course_code}")
        
        is_eligible = len(missing) == 0
        return is_eligible, missing
    
    @staticmethod
    def validate_schedule_constraints(
        sections: List[Dict],
        constraints: Dict,
        completed_courses: List[str]
    ) -> Tuple[bool, List[str]]:
        """Validate a full schedule against constraints.
        
        Args:
            sections: List of recommended sections
            constraints: Student constraints
            completed_courses: Courses student has completed
            
        Returns:
            Tuple of (is_valid, issues)
        """
        issues = []
        
        # Check for conflicts
        no_conflicts, conflicts = ConflictChecker.check_conflicts(sections)
        if not no_conflicts:
            issues.extend(conflicts)
        
        # Check credit limits
        total_credits = sum(s.get('credits', 0) for s in sections)
        
        max_credits = constraints.get('max_credits')
        if max_credits and total_credits > max_credits:
            issues.append(
                f"Total credits ({total_credits}) exceeds maximum ({max_credits})"
            )
            logger.warning(f"Schedule exceeds max credits: {total_credits} > {max_credits}")
        
        min_credits = constraints.get('min_credits')
        if min_credits and total_credits < min_credits:
            issues.append(
                f"Total credits ({total_credits}) below minimum ({min_credits})"
            )
            logger.warning(f"Schedule below min credits: {total_credits} < {min_credits}")
        
        # Check day preferences
        avoid_days = set(constraints.get('avoid_days') or [])
        for section in sections:
            meetings = section.get('meeting_times', [])
            for meeting in meetings:
                section_days = set(meeting.get('days', []))
                if section_days & avoid_days:
                    bad_day = list(section_days & avoid_days)[0]
                    course = section.get('course_code', 'Unknown')
                    issues.append(
                        f"{course} Section {section.get('section_number')} meets on {bad_day} (avoided)"
                    )
                    logger.warning(f"Section on avoided day: {bad_day}")
        
        # Check prerequisites
        for section in sections:
            course_code = section.get('course_code')
            prerequisites = section.get('prerequisites', [])
            
            if prerequisites:
                eligible, missing = ConflictChecker.check_prerequisite_eligibility(
                    course_code,
                    prerequisites,
                    completed_courses
                )
                if not eligible:
                    issues.append(
                        f"Missing prerequisites for {course_code}: {', '.join(missing)}"
                    )
                    logger.warning(f"Student missing prerequisites for {course_code}")
        
        is_valid = len(issues) == 0
        return is_valid, issues
