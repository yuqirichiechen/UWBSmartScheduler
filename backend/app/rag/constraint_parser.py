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

        # "only Tue/Thu" or "only Tuesday" implies the remaining weekdays
        # should be avoided — promote preferred_days to a hard avoid for the
        # complement so the builder won't pick sections on Mon/Wed/Fri.
        if re.search(r'\bonly\b', query.lower()) and constraints["preferred_days"]:
            weekdays = {"M", "T", "W", "Th", "F"}
            implied_avoid = sorted(weekdays - set(constraints["preferred_days"]))
            existing = set(constraints["avoid_days"] or [])
            constraints["avoid_days"] = sorted(existing | set(implied_avoid))
            logger.info(f"'only' clause promoted preferred_days -> avoid_days {constraints['avoid_days']}")
        
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
        
        # Patterns: "under 14 credits", "less than 15 credits", "max 12 credits",
        # "credits under 10", "keep credits under 10", "credit load under 14"
        patterns = [
            r'(?:under|less than|max|maximum|no more than)\s+(\d+)\s*(?:credits?|credi|hrs?)',
            r'(\d+)\s*(?:credits?|credi|hrs?)\s*(?:or less|max|maximum|or fewer)',
            r'(?:credits?|load).*?(?:under|less than|below)\s+(\d+)',
            r'(?:under|less than|max|maximum|no more than)\s+(\d+)',
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
    
    # Order matters: longer keys first so "thursday" doesn't match "tuesday" prefix etc.
    _DAY_WORDS = [
        ('thursdays', 'Th'), ('thursday', 'Th'), ('thurs', 'Th'), ('thur', 'Th'), ('thu', 'Th'),
        ('tuesdays', 'T'), ('tuesday', 'T'), ('tues', 'T'), ('tue', 'T'),
        ('wednesdays', 'W'), ('wednesday', 'W'), ('weds', 'W'), ('wed', 'W'),
        ('mondays', 'M'), ('monday', 'M'), ('mon', 'M'),
        ('fridays', 'F'), ('friday', 'F'), ('fri', 'F'),
        ('saturdays', 'S'), ('saturday', 'S'), ('sat', 'S'),
        ('sundays', 'Su'), ('sunday', 'Su'), ('sun', 'Su'),
    ]

    @staticmethod
    def _scan_days(text: str) -> List[str]:
        """Return ordered list of day-codes mentioned in `text`.

        Greedy word-boundary scan over the longer-first day word list so
        substrings like 'tue' don't shadow 'tuesday' and 'thu' doesn't
        match inside 'thursday'.
        """
        found: List[str] = []
        consumed = [False] * len(text)
        for word, code in ConstraintParser._DAY_WORDS:
            for m in re.finditer(rf'\b{re.escape(word)}\b', text):
                if any(consumed[m.start():m.end()]):
                    continue
                for i in range(m.start(), m.end()):
                    consumed[i] = True
                if code not in found:
                    found.append(code)
        return found

    @staticmethod
    def _extract_preferred_days(query: str) -> Optional[List[str]]:
        """Extract preferred days from query. Triggered by 'only', 'prefer',
        'want', 'on', 'mostly', or explicit ranges like 'Tue/Thu'."""
        query_lower = query.lower()

        # If there's a positive trigger, scan the rest of the sentence after it.
        # 'on' alone is too generic (it appears inside 'on Fridays' after a
        # negation), so we require it to be preceded by an explicit verb.
        triggers = [
            r'\b(?:only|prefer|prefers?|want|wants?|mostly)\b',
            r'\bcome(?:\s+to\s+campus)?\s+(?:on\s+)?',
            r'\b(?:i\s+can|can)\s+do\b',
        ]
        for pat in triggers:
            for m in re.finditer(pat, query_lower):
                # Skip if a negation precedes this trigger AND there is no
                # 'but' / 'except' clause between them flipping the polarity.
                preceding = query_lower[max(0, m.start() - 40):m.start()]
                neg_match = re.search(r"\b(?:no|not|don'?t|cannot|can'?t|avoid|skip|without)\b", preceding)
                if neg_match:
                    between = preceding[neg_match.end():]
                    if not re.search(r"\b(?:but|except|however|though)\b", between):
                        continue
                fragment = query_lower[m.end():m.end() + 80]
                # stop the scan if we hit another negation
                fragment = re.split(r"\b(?:but|except|no|not|avoid|skip)\b", fragment, maxsplit=1)[0]
                days = ConstraintParser._scan_days(fragment)
                if days:
                    logger.debug(f"Extracted preferred days: {days}")
                    return sorted(days)

        # Fallback: slash-separated abbreviations like "Tue/Thu" or "T/Th"
        if re.search(r'\b(?:tue|thu|mon|wed|fri)[a-z]*\s*/\s*(?:tue|thu|mon|wed|fri)', query_lower):
            days = ConstraintParser._scan_days(query_lower)
            if days:
                logger.debug(f"Extracted preferred days (slash form): {days}")
                return sorted(days)
        return None

    @staticmethod
    def _extract_avoid_days(query: str) -> Optional[List[str]]:
        """Extract days to avoid. Only scans the clause directly following a
        negative trigger (can't / cannot / no / avoid / skip / not / without /
        don't / no more) so that 'no Fridays but prefer Tuesday' doesn't put
        Tuesday in the avoid list."""
        query_lower = query.lower()
        triggers = re.finditer(
            r"\b(?:can'?t|cannot|no(?!t\s+at)|avoid|not(?!\s+at)|skip|don'?t|without)\b",
            query_lower,
        )

        avoid: List[str] = []
        for trig in triggers:
            # Scan the next ~40 characters or until a positive flip word.
            tail = query_lower[trig.end():trig.end() + 60]
            tail = re.split(r"\b(?:but|prefer|want|only|except|on)\b", tail, maxsplit=1)[0]
            for code in ConstraintParser._scan_days(tail):
                if code not in avoid:
                    avoid.append(code)

        if avoid:
            logger.debug(f"Extracted avoid days: {avoid}")
            return sorted(avoid)
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
