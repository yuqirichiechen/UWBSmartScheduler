"""Scraper for UW DawgPath Course Schedule - Supports all UW campuses and departments."""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime
import json
import hashlib
from pathlib import Path
import logging
import re
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor, as_completed
import time as time_module

logger = logging.getLogger(__name__)


class UWScheduleScraper:
    """Comprehensive scraper for UW DawgPath course schedules across all campuses and departments."""
    
    # UW Campuses with their base URLs for course schedules
    UW_CAMPUSES = {
        "Seattle": "https://www.washington.edu/students/crscat/",
        "Bothell": "https://www.uwb.edu/students/schedule",
        "Tacoma": "https://www.tacoma.uw.edu/students/class-schedule"
    }
    
    # Common departments (expandable)
    DEPARTMENTS = {
        "CSS": "Computer Science & Software Engineering",
        "CSE": "Computer Science & Engineering",
        "MATH": "Mathematics",
        "PHYS": "Physics",
        "CHEM": "Chemistry",
        "BIOL": "Biology",
        "ENG": "English",
        "ACCT": "Accounting",
        "ECON": "Economics",
        "PSYCH": "Psychology",
        "HIST": "History",
        "POLS": "Political Science",
        "GEOL": "Geology"
    }
    
    # CSS Core courses for MVP
    CSS_CORE_COURSES = {
        "CSS 143", "CSS 161", "CSS 201", "CSS 211", "CSS 301", 
        "CSS 330", "CSS 342", "CSS 385", "CSS 430", "CSS 486"
    }
    
    def __init__(self, cache_dir: str = "../data/cache", max_retries: int = 3, timeout: int = 15):
        """Initialize the scraper with DawgPath support.
        
        Args:
            cache_dir: Directory to cache scraped data
            max_retries: Maximum number of retry attempts for failed requests
            timeout: Request timeout in seconds
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.session.verify = True
    
    def scrape_all_courses(self, campus: str = "Bothell", quarter: Optional[str] = None, 
                          departments: Optional[List[str]] = None) -> List[Dict]:
        """Scrape all courses for a given campus and optional filters.
        
        Args:
            campus: UW campus ("Bothell", "Seattle", "Tacoma")
            quarter: Quarter filter (e.g., "Spring 2026", "Winter 2026")
            departments: List of department codes to filter (None = all)
            
        Returns:
            List of course dictionaries
        """
        logger.info(f"Starting scrape for {campus} campus" + 
                   (f", quarter: {quarter}" if quarter else "") +
                   (f", departments: {departments}" if departments else ""))
        
        try:
            cache_key = self._get_cache_key(campus, quarter, departments)
            
            # Check cache first
            cached_courses = self._load_cached_courses(cache_key)
            if cached_courses:
                logger.info(f"Loaded {len(cached_courses)} courses from cache")
                return cached_courses
            
            # Scrape from DawgPath
            courses = self._scrape_dawgpath(campus, quarter, departments)
            
            if not courses:
                logger.warning("No courses scraped, trying fallback cache")
                return self._load_cached_courses() or self._generate_sample_courses()
            
            # Cache the results
            self.cache_courses(courses, cache_key)
            
            logger.info(f"Successfully scraped {len(courses)} courses")
            return courses
            
        except Exception as e:
            logger.error(f"Error during scrape: {e}", exc_info=True)
            return self._load_cached_courses() or self._generate_sample_courses()
    
    def _scrape_dawgpath(self, campus: str, quarter: Optional[str], 
                        departments: Optional[List[str]]) -> List[Dict]:
        """Scrape courses from UW DawgPath system.
        
        Args:
            campus: UW campus name
            quarter: Quarter string (optional)
            departments: List of department codes (optional)
            
        Returns:
            List of parsed course dictionaries
        """
        courses_dict = {}
        
        # Determine departments to scrape
        depts_to_scrape = departments or list(self.DEPARTMENTS.keys())
        
        logger.info(f"Scraping departments: {depts_to_scrape}")
        
        # Use ThreadPoolExecutor for parallel department scraping
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}
            for dept in depts_to_scrape:
                future = executor.submit(self._scrape_department, campus, dept, quarter)
                futures[future] = dept
            
            for future in as_completed(futures):
                dept = futures[future]
                try:
                    dept_courses = future.result()
                    courses_dict.update({c['code']: c for c in dept_courses})
                    logger.info(f"Scraped {len(dept_courses)} courses from {dept}")
                except Exception as e:
                    logger.error(f"Error scraping {dept}: {e}")
        
        return list(courses_dict.values())
    
    def _scrape_department(self, campus: str, department: str, quarter: Optional[str]) -> List[Dict]:
        """Scrape courses for a specific department.
        
        Args:
            campus: UW campus
            department: Department code (e.g., "CSS")
            quarter: Quarter string (optional)
            
        Returns:
            List of course dictionaries for the department
        """
        # Build DawgPath-style URL
        base_url = self._get_campus_url(campus)
        if not base_url:
            return []
        
        # DawgPath allows department filtering
        params = {
            'dept': department,
        }
        
        if quarter:
            params['quarter'] = quarter
        
        full_url = f"{base_url}?{urlencode(params)}"
        
        logger.debug(f"Scraping {department} from {campus}: {full_url}")
        
        html_content = self._fetch_with_retry(full_url)
        if not html_content:
            return []
        
        return self._parse_html(html_content, department)
    
    def _fetch_with_retry(self, url: str) -> Optional[str]:
        """Fetch URL with retry logic and exponential backoff.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content or None if all retries failed
        """
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                logger.debug(f"Successfully fetched {url}")
                return response.text
            except requests.RequestException as e:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    time_module.sleep(wait_time)
        
        logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
        return None
    
    def _get_campus_url(self, campus: str) -> Optional[str]:
        """Get the base URL for a UW campus.
        
        Args:
            campus: Campus name
            
        Returns:
            Base URL or None if campus not found
        """
        return self.UW_CAMPUSES.get(campus)
    
    def scrape_courses(self, url: Optional[str] = None) -> List[Dict]:
        """Scrape courses from UW Time Schedule (backward compatibility).
        
        Args:
            url: URL of the Time Schedule (optional)
            
        Returns:
            List of course dictionaries
        """
        if url:
            html_content = self._fetch_with_retry(url)
            if not html_content:
                return self._load_cached_courses() or self._generate_sample_courses()
            return self._parse_html(html_content)
        else:
            # Default to Bothell CSS core courses
            return self.scrape_all_courses(campus="Bothell", departments=["CSS"])
    
    def _parse_html(self, html_content: str, department: Optional[str] = None) -> List[Dict]:
        """Parse HTML content to extract courses from DawgPath or Time Schedule.
        
        Args:
            html_content: Raw HTML from Time Schedule/DawgPath
            department: Department code if filtering (optional)
            
        Returns:
            List of course dictionaries
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        courses_dict = {}
        
        # Strategy 1: Try DawgPath table format
        courses = self._parse_dawgpath_format(soup, department)
        if courses:
            for course in courses:
                courses_dict[course['code']] = course
        
        # Strategy 2: Try generic time schedule format
        if not courses_dict:
            courses = self._parse_schedule_format(soup, department)
            for course in courses:
                courses_dict[course['code']] = course
        
        logger.info(f"Parsed HTML, found {len(courses_dict)} unique courses")
        return list(courses_dict.values())
    
    def _parse_dawgpath_format(self, soup: BeautifulSoup, department: Optional[str] = None) -> List[Dict]:
        """Parse DawgPath HTML table format (commonly used by UW).
        
        Args:
            soup: BeautifulSoup object
            department: Department code (optional)
            
        Returns:
            List of parsed courses
        """
        courses = []
        
        # DawgPath typically uses structured tables with specific class names
        tables = soup.find_all('table', class_=re.compile(r'schedule|course|class', re.IGNORECASE))
        
        for table in tables:
            rows = table.find_all('tr')[1:]  # Skip header
            for row in rows:
                course_info = self._parse_dawgpath_row(row, department)
                if course_info:
                    courses.append(course_info)
        
        return courses
    
    def _parse_dawgpath_row(self, row, department: Optional[str] = None) -> Optional[Dict]:
        """Parse a single row from DawgPath table.
        
        Args:
            row: Table row element
            department: Department code (optional)
            
        Returns:
            Course info dict or None
        """
        try:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 8:
                return None
            
            # Extract course code
            code_text = cells[0].text.strip()
            match = re.search(r'([A-Z]{2,4})\s*(\d{3,4})', code_text)
            if not match:
                return None
            
            dept_code = match.group(1)
            course_num = match.group(2)
            course_code = f"{dept_code} {course_num}"
            
            # Filter by department if specified
            if department and dept_code != department:
                return None
            
            title = cells[1].text.strip()
            credits_text = cells[2].text.strip()
            credits = int(re.search(r'\d+', credits_text).group()) if re.search(r'\d+', credits_text) else 3
            
            section_num = cells[3].text.strip()
            sln = cells[4].text.strip()
            days_text = cells[5].text.strip()
            time_text = cells[6].text.strip()
            instructor = cells[7].text.strip()
            
            # Extract location if available
            location = None
            if len(cells) > 8:
                location = cells[8].text.strip()
            
            meeting_times = self._parse_meeting_time(days_text, time_text, location)
            
            return {
                'code': course_code,
                'title': title,
                'credit_hours': credits,
                'department': dept_code,
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
            logger.debug(f"Could not parse DawgPath row: {e}")
            return None
    
    def _parse_schedule_format(self, soup: BeautifulSoup, department: Optional[str] = None) -> List[Dict]:
        """Parse generic time schedule HTML format.
        
        Args:
            soup: BeautifulSoup object
            department: Department code (optional)
            
        Returns:
            List of parsed courses
        """
        courses = []
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                course_info = self._parse_row(row, department)
                if course_info:
                    courses.append(course_info)
        
        return courses
    
    def _parse_row(self, row, department: Optional[str] = None) -> Optional[Dict]:
        """Parse a single course row from HTML.
        
        Args:
            row: BeautifulSoup row element
            department: Department code filter (optional)
            
        Returns:
            Course info dict or None
        """
        cells = row.find_all('td')
        if len(cells) < 8:
            return None
        
        try:
            code_text = cells[0].text.strip()
            # Match pattern like "CSS 342" or "CSS342"
            match = re.search(r'([A-Z]{2,4})\s*(\d{3,4})', code_text)
            if not match:
                return None
            
            dept_code = match.group(1)
            course_num = match.group(2)
            course_code = f"{dept_code} {course_num}"
            
            # Filter by department if specified
            if department and dept_code != department:
                return None
            
            title = cells[1].text.strip()
            credits_text = cells[2].text.strip()
            credits = int(re.search(r'\d+', credits_text).group()) if credits_text else 3
            
            section_num = cells[3].text.strip()
            sln = cells[4].text.strip()
            days_text = cells[5].text.strip()
            time_text = cells[6].text.strip()
            instructor = cells[7].text.strip()
            
            # Extract location if available
            location = None
            if len(cells) > 8:
                location = cells[8].text.strip()
            
            meeting_times = self._parse_meeting_time(days_text, time_text, location)
            
            return {
                'code': course_code,
                'title': title,
                'credit_hours': credits,
                'department': dept_code,
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
    
    def _parse_meeting_time(self, days_text: str, time_text: str, location: Optional[str] = None) -> List[Dict]:
        """Parse meeting days and times.
        
        Args:
            days_text: Days string like "T Th", "MWF", or "MW"
            time_text: Time string like "10:30am - 11:50am" or "10:30 AM - 11:50 AM"
            location: Location string (optional)
            
        Returns:
            List of meeting time dicts
        """
        meetings = []
        
        # Normalize days text
        days_text = days_text.strip()
        if not days_text or days_text.lower() in ['arranged', 'online', 'web']:
            return [{
                'days': [],
                'start_time': '00:00',
                'end_time': '00:00',
                'location': location or 'Arranged/Online'
            }]
        
        # Parse days - handle various formats
        day_patterns = {
            r'Monday|Mon': 'M',
            r'Tuesday|Tue|Tu': 'T',
            r'Wednesday|Wed': 'W',
            r'Thursday|Thu|Th': 'Th',
            r'Friday|Fri': 'F',
            r'Saturday|Sat': 'S',
            r'Sunday|Sun': 'U'
        }
        
        days = []
        for pattern, day_code in day_patterns.items():
            if re.search(pattern, days_text, re.IGNORECASE):
                days.append(day_code)
        
        # If no pattern matched, try single letters
        if not days:
            for char in days_text:
                if char in 'MTWFSU':
                    days.append(char)
                elif char == 'h' and 'Th' not in days:  # Handle 'Th'
                    days.append('Th')
        
        # Parse times - multiple formats supported
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)\s*[-–−]\s*(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)',
            r'(\d{1,2}):(\d{2})\s*[-–−]\s*(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)',
        ]
        
        for pattern in time_patterns:
            time_match = re.search(pattern, time_text)
            if time_match:
                groups = time_match.groups()
                
                if len(groups) == 6:  # Format: HH:MM AM - HH:MM AM
                    start_hour, start_min, start_ampm, end_hour, end_min, end_ampm = groups
                elif len(groups) == 5:  # Format: HH:MM - HH:MM AM
                    start_hour, start_min, end_hour, end_min, end_ampm = groups
                    start_ampm = end_ampm
                else:
                    continue
                
                start_hour = int(start_hour)
                start_min = int(start_min)
                end_hour = int(end_hour)
                end_min = int(end_min)
                
                # Convert to 24-hour format
                start_ampm = start_ampm.lower()
                end_ampm = end_ampm.lower()
                
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
                        'location': location or None
                    })
                break  # Successfully parsed, exit loop
        
        return meetings if meetings else [{
            'days': days or [],
            'start_time': '00:00',
            'end_time': '00:00',
            'location': location or None
        }]
    
    def _get_prerequisites(self, course_code: str) -> List[str]:
        """Get prerequisites for a course.
        
        Args:
            course_code: Course code like "CSS 342"
            
        Returns:
            List of prerequisite courses
        """
        # Expandable prerequisites database
        prerequisites = {
            # CSS Courses
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
            
            # CSE (University of Washington) courses
            "CSE 143": [],
            "CSE 373": ["CSE 143"],
            "CSE 421": ["CSE 373"],
            "CSE 422": ["CSE 421"],
        }
        return prerequisites.get(course_code, [])
    
    def _get_cache_key(self, campus: str, quarter: Optional[str], 
                      departments: Optional[List[str]]) -> str:
        """Generate a unique cache key for the scrape parameters.
        
        Args:
            campus: Campus name
            quarter: Quarter string (optional)
            departments: List of departments (optional)
            
        Returns:
            Cache key string
        """
        key_parts = [campus]
        if quarter:
            key_parts.append(quarter.replace(" ", "_"))
        if departments:
            key_parts.append("_".join(sorted(departments)))
        
        return "_".join(key_parts).lower()
    
    def cache_courses(self, courses: List[Dict], cache_key: Optional[str] = None) -> str:
        """Cache scraped courses to file with hash for validation.
        
        Args:
            courses: List of courses to cache
            cache_key: Optional cache key (defaults to timestamp)
            
        Returns:
            Hash of cached data
        """
        if not cache_key:
            cache_key = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        cache_file = self.cache_dir / f"courses_{cache_key}.json"
        data_str = json.dumps(courses, sort_keys=True, default=str)
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(courses, f, indent=2, default=str)
            
            # Save hash for validation
            hash_file = self.cache_dir / f"courses_{cache_key}.hash"
            with open(hash_file, 'w') as f:
                f.write(data_hash)
            
            logger.info(f"Cached {len(courses)} courses to {cache_file} with hash {data_hash[:8]}")
            return data_hash
        except IOError as e:
            logger.error(f"Failed to cache courses: {e}")
            return data_hash
    
    def _load_cached_courses(self, cache_key: Optional[str] = None) -> Optional[List[Dict]]:
        """Load previously cached courses.
        
        Args:
            cache_key: Specific cache key to load (optional, uses most recent if not specified)
            
        Returns:
            List of cached courses or None if no cache found
        """
        if cache_key:
            cache_file = self.cache_dir / f"courses_{cache_key}.json"
            if cache_file.exists():
                try:
                    with open(cache_file, 'r') as f:
                        courses = json.load(f)
                        logger.info(f"Loaded {len(courses)} courses from cache: {cache_key}")
                        return courses
                except (json.JSONDecodeError, IOError) as e:
                    logger.error(f"Failed to load cache {cache_key}: {e}")
                    return None
        else:
            # Find most recent cache
            cache_files = sorted(self.cache_dir.glob("courses_*.json"), reverse=True)
            for cache_file in cache_files:
                try:
                    with open(cache_file, 'r') as f:
                        courses = json.load(f)
                        logger.info(f"Loaded {len(courses)} courses from cache: {cache_file.stem}")
                        return courses
                except (json.JSONDecodeError, IOError) as e:
                    logger.error(f"Failed to load cache {cache_file}: {e}")
        
        return None
    
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
    
    def validate_cache(self) -> bool:
        """Validate cached data hasn't been corrupted.
        
        Returns:
            True if cache is valid, False otherwise
        """
        # Find most recent cache
        cache_files = sorted(self.cache_dir.glob("courses_*.json"), reverse=True)
        if not cache_files:
            logger.info("No cache files found")
            return False
        
        cache_file = cache_files[0]
        hash_file = cache_file.with_suffix('.hash')
        
        if not hash_file.exists():
            logger.warning(f"No hash file for {cache_file}")
            return False
        
        try:
            with open(cache_file, 'r') as f:
                courses = json.load(f)
            
            with open(hash_file, 'r') as f:
                stored_hash = f.read().strip()
            
            data_str = json.dumps(courses, sort_keys=True, default=str)
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
