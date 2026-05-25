"""Prerequisite graph for course dependencies."""
from typing import List, Dict, Set
import logging

logger = logging.getLogger(__name__)


class PrerequisiteGraph:
    """Manages prerequisite relationships between courses."""
    
    def __init__(self):
        """Initialize prerequisite graph."""
        self.graph: Dict[str, Set[str]] = {}  # course -> set of prerequisites
    
    def add_course(self, course_code: str, prerequisites: List[str]) -> None:
        """Add course and its prerequisites to graph.
        
        Args:
            course_code: Code of the course (e.g., "CSS 342")
            prerequisites: List of prerequisite course codes
        """
        self.graph[course_code] = set(prerequisites)
        logger.debug(f"Added {course_code} with prerequisites: {prerequisites}")
    
    def is_eligible(self, course_code: str, completed_courses: List[str]) -> bool:
        """Check if student is eligible to take a course.
        
        Args:
            course_code: Course to check
            completed_courses: Courses student has completed
            
        Returns:
            True if student meets all prerequisites
        """
        if course_code not in self.graph:
            return True
        
        required_prereqs = self.graph[course_code]
        completed_set = set(completed_courses)
        
        return required_prereqs.issubset(completed_set)
    
    def get_ineligible_courses(
        self, 
        courses: List[str], 
        completed_courses: List[str]
    ) -> List[str]:
        """Get courses from list that student is ineligible for.
        
        Args:
            courses: Courses to check
            completed_courses: Courses student has completed
            
        Returns:
            List of ineligible courses
        """
        ineligible = []
        for course in courses:
            if not self.is_eligible(course, completed_courses):
                ineligible.append(course)
        
        return ineligible
    
    def get_prerequisites(self, course_code: str) -> List[str]:
        """Get prerequisites for a course.

        Args:
            course_code: Course code

        Returns:
            List of prerequisite courses
        """
        return list(self.graph.get(course_code, set()))

    def infer_completed(self, completed_courses: List[str]) -> List[str]:
        """Expand a list of completed courses by adding all transitive prerequisites.

        If a student completed CSS 342, they must have completed CSS 211,
        CSS 161, and CSS 143.  This walks the prerequisite chain backwards
        so students don't need to list every course they've ever taken.

        Args:
            completed_courses: Courses the student explicitly listed

        Returns:
            Expanded list including all inferred prerequisites
        """
        expanded = set(c.upper() for c in completed_courses)
        queue = list(expanded)

        while queue:
            course = queue.pop()
            for prereq in self.graph.get(course, set()):
                prereq_upper = prereq.upper()
                if prereq_upper not in expanded:
                    expanded.add(prereq_upper)
                    queue.append(prereq_upper)
                    logger.debug(f"Inferred completed: {prereq_upper} (prerequisite of {course})")

        added = expanded - set(c.upper() for c in completed_courses)
        if added:
            logger.info(f"Inferred {len(added)} additional completed courses: {sorted(added)}")

        return sorted(expanded)
