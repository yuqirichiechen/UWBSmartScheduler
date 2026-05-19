"""Scraper for UW Bothell Time Schedule."""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple
from datetime import datetime, time
import json
import hashlib
from pathlib import Path
import logging
import re

logger = logging.getLogger(__name__)


class UWScheduleScraper:
    """Scrapes course schedule data from UW Bothell Time Schedule."""
    
    # CSS Core courses for MVP
    CSS_CORE_COURSES = {
        "CSS 143", "CSS 161", "CSS 201", "CSS 211", "CSS 301", 
        "CSS 330", "CSS 342", "CSS 385", "CSS 430", "CSS 486"
    }
    
    def __init__(self, cache_dir: str = "../data/cache"):
        """Initialize the scraper.
        
        Args:
            cache_dir: Directory to cache scraped data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
        })
        
    def scrape_courses(self, url: Optional[str] = None) -> List[Dict]:
        """Scrape courses from UW Bothell Time Schedule.
        
        Args:
            url: URL of the Time Schedule (optional)
            
        Returns:
            List of course dictionaries
        """
        try:
            if url:
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                courses = self._parse_html(response.text)
            else:
                courses = self._generate_sample_courses()
            
            if not courses:
                logger.warning("No courses parsed, using cached data")
                return self._load_cached_courses()
            
            logger.info(f"Successfully scraped {len(courses)} courses")
            return courses
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch schedule: {e}")
            return self._load_cached_courses()
    
    def _parse_html(self, html_content: str) -> List[Dict]:
        """Parse HTML content to extract courses.
        
        Args:
            html_content: Raw HTML from Time Schedule
            
        Returns:
            List of course dictionaries
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        courses_dict = {}
        
        # Look for course rows in various table formats
        # UW Bothell uses a table-based layout
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                course_info = self._parse_row(row)
                if course_info:
                    course_code = course_info['code']
                    if course_code not in courses_dict:
                        courses_dict[course_code] = course_info
                    else:
                        # Merge sections
                        courses_dict[course_code]['sections'].extend(
                            course_info['sections']
                        )
        
        courses = list(courses_dict.values())
        logger.info(f"Parsed HTML, found {len(courses)} unique courses")
        
        return courses
    
    def _parse_row(self, row) -> Optional[Dict]:
        """Parse a single course row from HTML.
        
        Args:
            row: BeautifulSoup row element
            
        Returns:
            Course info dict or None
        """
        cells = row.find_all('td')
        if len(cells) < 8:
            return None
        
        try:
            code_text = cells[0].text.strip()
            # Match pattern like "CSS 342"
            match = re.search(r'([A-Z]{2,3})\s*(\d{3})', code_text)
            if not match:
                return None
            
            course_code = f"{match.group(1)} {match.group(2)}"
            
            # Only include CSS core courses
            if course_code not in self.CSS_CORE_COURSES:
                return None
            
            title = cells[1].text.strip()
            credits_text = cells[2].text.strip()
            credits = int(re.search(r'\d+', credits_text).group()) if credits_text else 3
            
            section_num = cells[3].text.strip()
            sln = cells[4].text.strip()
            days_text = cells[5].text.strip()
            time_text = cells[6].text.strip()
            instructor = cells[7].text.strip()
            
            meeting_times = self._parse_meeting_time(days_text, time_text)
            
            return {
                'code': course_code,
                'title': title,
                'credit_hours': credits,
                'department': match.group(1),
                'prerequisites': self._get_prerequisites(course_code),
                'sections': [{
                    'section_number': section_num,
                    'section_id': sln,
                    'instructor': instructor,
                    'meeting_times': meeting_times,
                    'credits': credits,
                    'capacity': None,
                    'enrolled': None,
                    'available_seats': None
                }]
            }
        except (IndexError, ValueError, AttributeError) as e:
            logger.debug(f"Could not parse row: {e}")
            return None
    
    def _parse_meeting_time(self, days_text: str, time_text: str) -> List[Dict]:
        """Parse meeting days and times.
        
        Args:
            days_text: Days string like "T Th" or "MWF"
            time_text: Time string like "10:30am - 11:50am"
            
        Returns:
            List of meeting time dicts
        """
        meetings = []
        
        # Parse days
        days_map = {
            'M': 'M', 'Tu': 'T', 'T': 'T', 'W': 'W', 
            'Th': 'Th', 'F': 'F', 'S': 'S'
        }
        
        days = []
        days_text = days_text.replace('Monday', 'M').replace('Tuesday', 'Tu')
        days_text = days_text.replace('Wednesday', 'W').replace('Thursday', 'Th')
        days_text = days_text.replace('Friday', 'F').replace('Saturday', 'S')
        
        for day_code in days_map.keys():
            if day_code in days_text:
                days.append(days_map[day_code])
        
        # Parse times
        time_match = re.search(
            r'(\d{1,2}):(\d{2})\s*(am|pm)\s*[-–]\s*(\d{1,2}):(\d{2})\s*(am|pm)',
            time_text.lower()
        )
        
        if time_match:
            start_hour = int(time_match.group(1))
            start_min = int(time_match.group(2))
            start_ampm = time_match.group(3)
            end_hour = int(time_match.group(4))
            end_min = int(time_match.group(5))
            end_ampm = time_match.group(6)
            
            # Convert to 24-hour format
            if start_ampm == 'pm' and start_hour != 12:
                start_hour += 12
            elif start_ampm == 'am' and start_hour == 12:
                start_hour = 0
            
            if end_ampm == 'pm' and end_hour != 12:
                end_hour += 12
            elif end_ampm == 'am' and end_hour == 12:
                end_hour = 0
            
            start_time = f"{start_hour:02d}:{start_min:02d}"
            end_time = f"{end_hour:02d}:{end_min:02d}"
            
            if days:
                meetings.append({
                    'days': days,
                    'start_time': start_time,
                    'end_time': end_time,
                    'location': None
                })
        
        return meetings if meetings else [{
            'days': [],
            'start_time': '00:00',
            'end_time': '00:00',
            'location': None
        }]
    
    def _get_prerequisites(self, course_code: str) -> List[str]:
        """Get prerequisites for a course.
        
        Args:
            course_code: Course code like "CSS 342"
            
        Returns:
            List of prerequisite courses
        """
        prerequisites = {
            "CSS 143": [],
            "CSS 161": ["CSS 143"],
            "CSS 201": ["CSS 161"],
            "CSS 211": ["CSS 161"],
            "CSS 301": ["CSS 201"],
            "CSS 330": ["CSS 201"],
            "CSS 342": ["CSS 211"],
            "CSS 385": ["CSS 342"],
            "CSS 430": ["CSS 330"],
            "CSS 486": ["CSS 342", "CSS 330"],
        }
        return prerequisites.get(course_code, [])
    
    def _generate_sample_courses(self) -> List[Dict]:
        """Generate sample CSS core courses for development/testing.
        
        Returns:
            List of sample course dictionaries
        """
        sample_courses = [
            {
                'code': 'CSS 143',
                'title': 'Computer Science I',
                'credit_hours': 4,
                'department': 'CSS',
                'prerequisites': [],
                'sections': [
                    {
                        'section_number': 'A',
                        'section_id': '11111',
                        'instructor': 'Dr. Alice Johnson',
                        'meeting_times': [{
                            'days': ['M', 'W', 'F'],
                            'start_time': '10:00',
                            'end_time': '10:50',
                            'location': 'UWB 105'
                        }],
                        'credits': 4,
                    },
                    {
                        'section_number': 'B',
                        'section_id': '11112',
                        'instructor': 'Dr. Bob Smith',
                        'meeting_times': [{
                            'days': ['T', 'Th'],
                            'start_time': '14:00',
                            'end_time': '15:20',
                            'location': 'UWB 110'
                        }],
                        'credits': 4,
                    }
                ]
            },
            {
                'code': 'CSS 161',
                'title': 'Computer Science II',
                'credit_hours': 4,
                'department': 'CSS',
                'prerequisites': ['CSS 143'],
                'sections': [
                    {
                        'section_number': 'A',
                        'section_id': '11211',
                        'instructor': 'Dr. Carol Davis',
                        'meeting_times': [{
                            'days': ['M', 'W', 'F'],
                            'start_time': '11:00',
                            'end_time': '11:50',
                            'location': 'UWB 205'
                        }],
                        'credits': 4,
                    }
                ]
            },
            {
                'code': 'CSS 201',
                'title': 'Discrete Mathematics',
                'credit_hours': 3,
                'department': 'CSS',
                'prerequisites': ['CSS 161'],
                'sections': [
                    {
                        'section_number': 'A',
                        'section_id': '12111',
                        'instructor': 'Dr. David Wilson',
                        'meeting_times': [{
                            'days': ['T', 'Th'],
                            'start_time': '10:00',
                            'end_time': '11:20',
                            'location': 'UWB 115'
                        }],
                        'credits': 3,
                    }
                ]
            },
            {
                'code': 'CSS 342',
                'title': 'Data Structures',
                'credit_hours': 4,
                'department': 'CSS',
                'prerequisites': ['CSS 211'],
                'sections': [
                    {
                        'section_number': 'A',
                        'section_id': '13411',
                        'instructor': 'Dr. Emma Martinez',
                        'meeting_times': [{
                            'days': ['M', 'W'],
                            'start_time': '14:00',
                            'end_time': '15:20',
                            'location': 'UWB 301'
                        }],
                        'credits': 4,
                    },
                    {
                        'section_number': 'B',
                        'section_id': '13412',
                        'instructor': 'Dr. Frank Lee',
                        'meeting_times': [{
                            'days': ['T', 'Th'],
                            'start_time': '16:00',
                            'end_time': '17:20',
                            'location': 'UWB 310'
                        }],
                        'credits': 4,
                    }
                ]
            },
            {
                'code': 'CSS 385',
                'title': 'Software Engineering',
                'credit_hours': 4,
                'department': 'CSS',
                'prerequisites': ['CSS 342'],
                'sections': [
                    {
                        'section_number': 'A',
                        'section_id': '13851',
                        'instructor': 'Dr. Grace Chen',
                        'meeting_times': [{
                            'days': ['T', 'Th'],
                            'start_time': '12:30',
                            'end_time': '13:50',
                            'location': 'UWB 320'
                        }],
                        'credits': 4,
                    }
                ]
            },
        ]
        
        logger.info(f"Generated {len(sample_courses)} sample courses")
        return sample_courses
    
    def _load_cached_courses(self) -> List[Dict]:
        """Load previously cached courses.
        
        Returns:
            List of cached courses or sample courses if no cache
        """
        cache_file = self.cache_dir / "courses_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    courses = json.load(f)
                    logger.info(f"Loaded {len(courses)} courses from cache")
                    return courses
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load cache: {e}")
        
        # Fall back to sample data
        return self._generate_sample_courses()
    
    def cache_courses(self, courses: List[Dict]) -> str:
        """Cache scraped courses to file with hash for validation.
        
        Args:
            courses: List of courses to cache
            
        Returns:
            Hash of cached data
        """
        cache_file = self.cache_dir / "courses_cache.json"
        data_str = json.dumps(courses, sort_keys=True)
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(courses, f, indent=2)
            
            # Save hash for validation
            hash_file = self.cache_dir / "courses_cache.hash"
            with open(hash_file, 'w') as f:
                f.write(data_hash)
            
            logger.info(f"Cached {len(courses)} courses with hash {data_hash[:8]}")
            return data_hash
        except IOError as e:
            logger.error(f"Failed to cache courses: {e}")
            return data_hash
    
    def validate_cache(self) -> bool:
        """Validate cached data hasn't corrupted.
        
        Returns:
            True if cache is valid, False otherwise
        """
        cache_file = self.cache_dir / "courses_cache.json"
        hash_file = self.cache_dir / "courses_cache.hash"
        
        if not cache_file.exists() or not hash_file.exists():
            logger.info("No cache files found")
            return False
        
        try:
            with open(cache_file, 'r') as f:
                courses = json.load(f)
            
            with open(hash_file, 'r') as f:
                stored_hash = f.read().strip()
            
            data_str = json.dumps(courses, sort_keys=True)
            computed_hash = hashlib.sha256(data_str.encode()).hexdigest()
            
            is_valid = computed_hash == stored_hash
            if is_valid:
                logger.info("Cache validation passed")
            else:
                logger.warning("Cache validation failed - hash mismatch")
            
            return is_valid
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Cache validation error: {e}")
            return False
