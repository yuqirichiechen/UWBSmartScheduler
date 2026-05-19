"""Parser for extracting constraints from natural language queries."""
import logging
from typing import Dict, Optional, List
import re

logger = logging.getLogger(__name__)


class ConstraintParser:
    """Parses natural language queries into structured constraints."""
    
    @staticmethod
    def parse_query(query: str) -> Dict:
        """Parse user query into constraints.
        
        Args:
            query: Natural language query from user
            
        Returns:
            Structured constraint dictionary
        """
        constraints = {
            "query": query,
            "max_credits": ConstraintParser._extract_max_credits(query),
            "min_credits": ConstraintParser._extract_min_credits(query),
            "preferred_days": ConstraintParser._extract_preferred_days(query),
            "avoid_days": ConstraintParser._extract_avoid_days(query),
            "required_courses": ConstraintParser._extract_required_courses(query),
            "time_windows": ConstraintParser._extract_time_windows(query),
            "no_online": ConstraintParser._extract_no_online(query)
        }
        
        logger.info(f"Parsed query: '{query}'")
        logger.info(f"Extracted constraints: {constraints}")
        return constraints
    
    @staticmethod
    def _extract_max_credits(query: str) -> Optional[int]:
        """Extract maximum credit limit from query.
        
        Args:
            query: User query
            
        Returns:
            Maximum credits or None
        """
        query_lower = query.lower()
        
        # Patterns: "under 14", "less than 15", "max 12", "no more than 13"
        patterns = [
            r'(?:under|less than|max|maximum|no more than)\s+(\d+)\s*(?:credits?|credi|hrs?)',
            r'(\d+)\s*(?:credits?|credi|hrs?)\s*(?:or less|max|maximum|or fewer)',
            r'keep.*?(?:under|less than|below)\s+(\d+)\s*(?:credits?|credi)',
            r'load.*?(?:under|less than)\s+(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    credits = int(match.group(1))
                    if credits > 0 and credits <= 20:  # Reasonable bounds
                        logger.debug(f"Extracted max credits: {credits}")
                        return credits
                except (ValueError, IndexError):
                    pass
        
        return None
    
    @staticmethod
    def _extract_min_credits(query: str) -> Optional[int]:
        """Extract minimum credit requirement.
        
        Args:
            query: User query
            
        Returns:
            Minimum credits or None
        """
        query_lower = query.lower()
        
        patterns = [
            r'(?:at least|minimum|more than|over|need)\s+(\d+)\s*(?:credits?|credi)',
            r'(?:want|take|get)\s+(?:at least|minimum|over|at)\s+(\d+)\s*(?:credits?|credi)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    credits = int(match.group(1))
                    if credits > 0 and credits <= 20:
                        logger.debug(f"Extracted min credits: {credits}")
                        return credits
                except (ValueError, IndexError):
                    pass
        
        return None
    
    @staticmethod
    def _extract_preferred_days(query: str) -> Optional[List[str]]:
        """Extract preferred days from query.
        
        Args:
            query: User query
            
        Returns:
            List of preferred days or None
        """
        query_lower = query.lower()
        days_map = {
            'monday': 'M', 'mon': 'M',
            'tuesday': 'T', 'tue': 'T', 'tues': 'T',
            'wednesday': 'W', 'wed': 'W',
            'thursday': 'Th', 'thurs': 'Th', 'thu': 'Th',
            'friday': 'F', 'fri': 'F',
            'saturday': 'S', 'sat': 'S',
            'sunday': 'Su', 'sun': 'Su'
        }
        
        preferred = []
        
        # Look for "come on", "only on", "prefer", "want"
        patterns = [
            r'(?:only|come|class)\s+(?:on\s+)?([MTWFSu\s,and]+)',
            r'(?:prefer|want|schedule).*?(?:on\s+)?([MTWFSu\s,and]+)',
            r'tuesday.*?thursday|t.*?th',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                days_text = match.group(1)
                for day_name, day_code in days_map.items():
                    if day_name in days_text:
                        if day_code not in preferred:
                            preferred.append(day_code)
        
        # Also check for direct day abbreviations
        for day_code in ['M', 'T', 'W', 'F', 'Th', 'S']:
            if re.search(rf'\b{day_code}\b', query):
                if day_code not in preferred:
                    preferred.append(day_code)
        
        result = sorted(list(set(preferred)))
        if result:
            logger.debug(f"Extracted preferred days: {result}")
            return result
        return None
    
    @staticmethod
    def _extract_avoid_days(query: str) -> Optional[List[str]]:
        """Extract days to avoid from query.
        
        Args:
            query: User query
            
        Returns:
            List of days to avoid or None
        """
        query_lower = query.lower()
        days_map = {
            'monday': 'M', 'mon': 'M',
            'tuesday': 'T', 'tue': 'T', 'tues': 'T',
            'wednesday': 'W', 'wed': 'W',
            'thursday': 'Th', 'thurs': 'Th',
            'friday': 'F', 'fri': 'F',
            'saturday': 'S', 'sat': 'S',
            'sunday': 'Su', 'sun': 'Su'
        }
        
        avoid = []
        
        # Patterns: "can't come Friday", "no Fridays", "avoid Tuesday"
        patterns = [
            r"(?:can't|cannot|no|avoid|not|skip|don't)\s+(?:come\s+)?(?:on\s+)?([mtfswu\s,and]+?days?)",
            r"(?:can't|cannot|no|avoid)\s+(?:on\s+)?([mtfswu\s,and]+?days?)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                days_text = match.group(1)
                for day_name, day_code in days_map.items():
                    if day_name in days_text:
                        if day_code not in avoid:
                            avoid.append(day_code)
        
        # Special cases
        if re.search(r"can't drive.*friday|friday.*drive", query_lower):
            if 'F' not in avoid:
                avoid.append('F')
        
        result = sorted(list(set(avoid)))
        if result:
            logger.debug(f"Extracted avoid days: {result}")
            return result
        return None
    
    @staticmethod
    def _extract_required_courses(query: str) -> Optional[List[str]]:
        """Extract required courses from query.
        
        Args:
            query: User query
            
        Returns:
            List of required courses or None
        """
        # Look for course codes like "CSS 342", "CSE 143", "C S 342"
        pattern = r'([A-Z]{2,3})\s*(\d{3})'
        matches = re.findall(pattern, query)
        
        courses = list(set([f"{code.upper()} {num}" for code, num in matches]))
        
        if courses:
            logger.debug(f"Extracted required courses: {courses}")
            return courses
        return None
    
    @staticmethod
    def _extract_time_windows(query: str) -> Optional[List[Dict]]:
        """Extract preferred time windows from query.
        
        Args:
            query: User query
            
        Returns:
            List of time windows or None
        """
        # Pattern: "morning", "afternoon", "evening", or specific times like "before 2pm"
        time_windows = []
        query_lower = query.lower()
        
        time_map = {
            'morning': {'start': '08:00', 'end': '12:00'},
            'afternoon': {'start': '12:00', 'end': '17:00'},
            'evening': {'start': '17:00', 'end': '21:00'},
        }
        
        for time_label, times in time_map.items():
            if time_label in query_lower:
                time_windows.append(times)
                logger.debug(f"Extracted {time_label} time window")
        
        # Extract specific times like "before 2pm" or "after 10am"
        specific_time_pattern = r'(?:before|after|until|starting)\s+(\d{1,2}):?(\d{2})?\s*(am|pm)'
        specific_matches = re.findall(specific_time_pattern, query_lower)
        
        for hour, minute, ampm in specific_matches:
            h = int(hour)
            m = int(minute) if minute else 0
            
            if ampm == 'pm' and h != 12:
                h += 12
            elif ampm == 'am' and h == 12:
                h = 0
            
            time_str = f"{h:02d}:{m:02d}"
            logger.debug(f"Extracted specific time: {time_str}")
        
        return time_windows if time_windows else None
    
    @staticmethod
    def _extract_no_online(query: str) -> bool:
        """Check if student wants only in-person classes.
        
        Args:
            query: User query
            
        Returns:
            True if student wants no online classes
        """
        query_lower = query.lower()
        
        patterns = [
            r'(?:no|avoid|not|in-person|in person|campus|face-to-face)',
            r'(?:come to|need to be|show up)',
        ]
        
        online_patterns = [
            r'(?:online|remote|zoom|virtual)',
        ]
        
        has_online_mention = any(
            bool(re.search(pattern, query_lower)) 
            for pattern in online_patterns
        )
        
        has_in_person_mention = any(
            bool(re.search(pattern, query_lower)) 
            for pattern in patterns
        )
        
        if has_in_person_mention and not re.search(r'online.*ok|ok.*online', query_lower):
            logger.debug("Extracted no_online preference")
            return True
        
        return False
