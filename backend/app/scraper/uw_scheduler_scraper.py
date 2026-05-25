"""Scraper for UW Bothell Time Schedule (public course offerings)."""
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
import time as time_module

logger = logging.getLogger(__name__)


# Base URL for the public (no-auth) UW Time Schedule
UW_TIMESCHD_BASE = "http://www.washington.edu/students/timeschd/pub/B"

# Quarter code mapping
QUARTER_CODES = {
    "autumn": "AUT",
    "winter": "WIN",
    "spring": "SPR",
    "summer": "SUM",
}


class UWScheduleScraper:
    """Scraper for UW Bothell course schedules from the public Time Schedule."""

    CSS_CORE_COURSES = {
        "CSS 143", "CSS 161", "CSS 201", "CSS 211", "CSS 301",
        "CSS 330", "CSS 342", "CSS 385", "CSS 430", "CSS 486"
    }

    def __init__(self, cache_dir: str = "../data/cache", max_retries: int = 3, timeout: int = 15):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scrape_courses(self, url: Optional[str] = None) -> List[Dict]:
        """Scrape CSS courses from UW Bothell public time schedule.

        Tries the live UW site first, falls back to cache, then sample data.
        """
        # Try cache first (valid for 24 hours)
        cached = self._load_cached_courses("bothell_css")
        if cached:
            logger.info(f"Loaded {len(cached)} courses from cache")
            return cached

        # Scrape live
        courses = self._scrape_live()
        if courses:
            self.cache_courses(courses, "bothell_css")
            return courses

        # Fallback: any cache, or sample data
        fallback = self._load_cached_courses() or self._generate_sample_courses()
        logger.warning(f"Using fallback data: {len(fallback)} courses")
        return fallback

    def scrape_all_courses(self, campus: str = "Bothell", quarter: Optional[str] = None,
                           departments: Optional[List[str]] = None) -> List[Dict]:
        """Backward-compatible method."""
        return self.scrape_courses()

    # ------------------------------------------------------------------
    # Live scraping
    # ------------------------------------------------------------------

    def _scrape_live(self) -> List[Dict]:
        """Scrape courses from the live UW Time Schedule."""
        # Determine current quarter
        quarter_code = self._current_quarter_code()
        url = f"{UW_TIMESCHD_BASE}/{quarter_code}/css.html"
        logger.info(f"Scraping live schedule from {url}")

        html = self._fetch_with_retry(url)
        if not html or "Shibboleth" in html:
            logger.warning("Live scrape failed or requires auth")
            return []

        courses = self._parse_uw_timeschedule(html)
        # Attach prerequisites
        for course in courses:
            course['prerequisites'] = self._get_prerequisites(course['code'])

        logger.info(f"Scraped {len(courses)} courses from live schedule")
        return courses

    def _current_quarter_code(self) -> str:
        """Determine the current UW quarter code like 'SPR2026'."""
        now = datetime.now()
        month = now.month
        year = now.year

        if month <= 3:
            q = "WIN"
        elif month <= 6:
            q = "SPR"
        elif month <= 9:
            q = "SUM"
        else:
            q = "AUT"

        return f"{q}{year}"

    def _parse_uw_timeschedule(self, html: str) -> List[Dict]:
        """Parse the UW public time schedule HTML format.

        The page uses <pre> formatted text with fixed-width columns
        and green course-header tables with anchor tags.
        """
        # Course header: <A NAME=css342>CSS&nbsp;&nbsp; 342 </A>&nbsp;<A HREF=...>DATA, ALG, MATH I</A>
        course_re = re.compile(
            r'<A NAME=css(\d+)>CSS&nbsp;&nbsp;\s*(\d+)\s*</A>\s*&nbsp;'
            r'<A HREF=[^>]*>([^<]+)</A>'
        )

        # Section line inside <pre> blocks
        section_re = re.compile(
            r'<A HREF=[^>]*>(\d{5})</A>\s+'   # SLN
            r'(\w+)\s+'                         # Section letter
            r'(\d+)\s+'                         # Credits
            r'([A-Za-z]{1,5})\s+'              # Days
            r'(\d{3,4})-(\d{3,4})\s+'          # Start-End time
            r'.*?(Open|Closed)\s+'             # Status
            r'(\d+)/\s*(\d+)'                   # Enrolled/Limit
        )

        # Find course positions
        course_positions = [
            (m.start(), m.group(2), m.group(3).strip())
            for m in course_re.finditer(html)
        ]

        courses = []
        for i, (pos, num, title) in enumerate(course_positions):
            end_pos = course_positions[i + 1][0] if i + 1 < len(course_positions) else len(html)
            chunk = html[pos:end_pos]

            sections = []
            for m in section_re.finditer(chunk):
                sln, sec, credits, days_raw, start_raw, end_raw, status, enrolled, limit = m.groups()

                parsed_days = self._parse_uw_days(days_raw)
                start_time = self._parse_uw_time(start_raw)
                end_time = self._parse_uw_time(end_raw)

                sections.append({
                    'section_number': sec,
                    'section_id': sln,
                    'instructor': 'TBA',
                    'meeting_times': [{
                        'days': parsed_days,
                        'start_time': start_time,
                        'end_time': end_time,
                        'location': 'UW Bothell'
                    }],
                    'credits': int(credits),
                    'status': status,
                    'enrolled': int(enrolled),
                    'capacity': int(limit),
                })

            if sections:
                courses.append({
                    'code': f'CSS {num}',
                    'title': title,
                    'credit_hours': sections[0]['credits'],
                    'department': 'CSS',
                    'sections': sections,
                })

        return courses

    @staticmethod
    def _parse_uw_days(days_str: str) -> List[str]:
        """Parse UW day abbreviations like 'MW', 'TTh', 'MWF'."""
        days = []
        i = 0
        while i < len(days_str):
            if i + 1 < len(days_str) and days_str[i] == 'T' and days_str[i + 1] == 'h':
                days.append('Th')
                i += 2
            elif days_str[i] in ('M', 'T', 'W', 'F', 'S'):
                days.append(days_str[i])
                i += 1
            else:
                i += 1
        return days

    @staticmethod
    def _parse_uw_time(t: str) -> str:
        """Parse UW time like '1100' -> '11:00', '100' -> '13:00', '530' -> '17:30'."""
        t = t.zfill(4)
        h = int(t[:-2])
        m = int(t[-2:])
        # UW uses 12-hour without AM/PM: hours 1-6 are PM
        if 1 <= h <= 6:
            h += 12
        return f"{h:02d}:{m:02d}"

    # ------------------------------------------------------------------
    # Network
    # ------------------------------------------------------------------

    def _fetch_with_retry(self, url: str) -> Optional[str]:
        """Fetch URL with retry logic."""
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                wait_time = 2 ** attempt
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    time_module.sleep(wait_time)
        logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
        return None

    # ------------------------------------------------------------------
    # Caching
    # ------------------------------------------------------------------

    def cache_courses(self, courses: List[Dict], cache_key: Optional[str] = None) -> str:
        if not cache_key:
            cache_key = datetime.now().strftime("%Y%m%d_%H%M%S")
        cache_file = self.cache_dir / f"courses_{cache_key}.json"
        data_str = json.dumps(courses, sort_keys=True, default=str)
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()
        try:
            with open(cache_file, 'w') as f:
                json.dump(courses, f, indent=2, default=str)
            hash_file = self.cache_dir / f"courses_{cache_key}.hash"
            with open(hash_file, 'w') as f:
                f.write(data_hash)
            logger.info(f"Cached {len(courses)} courses to {cache_file}")
        except IOError as e:
            logger.error(f"Failed to cache courses: {e}")
        return data_hash

    def _load_cached_courses(self, cache_key: Optional[str] = None) -> Optional[List[Dict]]:
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
        else:
            cache_files = sorted(self.cache_dir.glob("courses_*.json"), reverse=True)
            for cache_file in cache_files:
                try:
                    with open(cache_file, 'r') as f:
                        courses = json.load(f)
                    logger.info(f"Loaded {len(courses)} from cache: {cache_file.stem}")
                    return courses
                except (json.JSONDecodeError, IOError):
                    continue
        return None

    def validate_cache(self) -> bool:
        cache_files = sorted(self.cache_dir.glob("courses_*.json"), reverse=True)
        if not cache_files:
            return False
        cache_file = cache_files[0]
        hash_file = cache_file.with_suffix('.hash')
        if not hash_file.exists():
            return False
        try:
            with open(cache_file, 'r') as f:
                courses = json.load(f)
            with open(hash_file, 'r') as f:
                stored_hash = f.read().strip()
            data_str = json.dumps(courses, sort_keys=True, default=str)
            return hashlib.sha256(data_str.encode()).hexdigest() == stored_hash
        except (json.JSONDecodeError, IOError):
            return False

    # ------------------------------------------------------------------
    # Prerequisites
    # ------------------------------------------------------------------

    def _get_prerequisites(self, course_code: str) -> List[str]:
        """Get prerequisites for a course."""
        prerequisites = {
            "CSS 101": [],
            "CSS 107": [],
            "CSS 112": [],
            "CSS 132": [],
            "CSS 142": [],
            "CSS 143": ["CSS 142"],
            "CSS 161": ["CSS 143"],
            "CSS 162": ["CSS 161"],
            "CSS 201": ["CSS 161"],
            "CSS 211": ["CSS 161"],
            "CSS 225": ["CSS 143"],
            "CSS 290": [],
            "CSS 295": [],
            "CSS 301": ["CSS 201"],
            "CSS 310": ["CSS 161"],
            "CSS 330": ["CSS 201"],
            "CSS 337": ["CSS 310"],
            "CSS 342": ["CSS 211", "CSS 201"],
            "CSS 343": ["CSS 342"],
            "CSS 350": ["CSS 342"],
            "CSS 360": ["CSS 342"],
            "CSS 370": ["CSS 342"],
            "CSS 371": ["CSS 350"],
            "CSS 382": ["CSS 342"],
            "CSS 383": ["CSS 342"],
            "CSS 385": ["CSS 342"],
            "CSS 390": ["CSS 342"],
            "CSS 397": [],
            "CSS 411": ["CSS 211"],
            "CSS 421": ["CSS 342"],
            "CSS 422": ["CSS 343"],
            "CSS 427": ["CSS 343"],
            "CSS 430": ["CSS 343"],
            "CSS 431": ["CSS 343"],
            "CSS 436": ["CSS 343"],
            "CSS 448": ["CSS 343"],
            "CSS 449": ["CSS 343"],
            "CSS 451": ["CSS 342"],
            "CSS 461": ["CSS 360"],
            "CSS 473": [],
            "CSS 474": ["CSS 473"],
            "CSS 475": ["CSS 343"],
            "CSS 480": ["CSS 342"],
            "CSS 481": ["CSS 342"],
            "CSS 486": ["CSS 342", "CSS 330"],
            "CSS 487": ["CSS 342"],
            "CSS 490": ["CSS 343"],
            "CSS 495": [],
            "CSS 496": ["CSS 360"],
            "CSS 497": ["CSS 360"],
            # CSE
            "CSE 142": [],
            "CSE 143": ["CSE 142"],
            "CSE 373": ["CSE 143"],
            "CSE 421": ["CSE 373"],
        }
        return prerequisites.get(course_code, [])

    # ------------------------------------------------------------------
    # Sample data fallback
    # ------------------------------------------------------------------

    def _generate_sample_courses(self) -> List[Dict]:
        """Generate sample CSS courses when live scraping is unavailable."""
        sample_courses = [
            {
                'code': 'CSS 142',
                'title': 'Computer Programming I',
                'credit_hours': 5,
                'department': 'CSS',
                'prerequisites': [],
                'sections': [
                    {'section_number': 'A', 'section_id': '12888', 'instructor': 'TBA',
                     'meeting_times': [{'days': ['M', 'W'], 'start_time': '11:00', 'end_time': '13:00', 'location': 'UW Bothell'}], 'credits': 5},
                    {'section_number': 'B', 'section_id': '12889', 'instructor': 'TBA',
                     'meeting_times': [{'days': ['M', 'W'], 'start_time': '15:30', 'end_time': '17:30', 'location': 'UW Bothell'}], 'credits': 5},
                ]
            },
            {
                'code': 'CSS 143',
                'title': 'Computer Programming II',
                'credit_hours': 5,
                'department': 'CSS',
                'prerequisites': ['CSS 142'],
                'sections': [
                    {'section_number': 'A', 'section_id': '12891', 'instructor': 'TBA',
                     'meeting_times': [{'days': ['T', 'Th'], 'start_time': '15:30', 'end_time': '17:30', 'location': 'UW Bothell'}], 'credits': 5},
                ]
            },
            {
                'code': 'CSS 342',
                'title': 'Data Structures, Algorithms, and Discrete Math I',
                'credit_hours': 5,
                'department': 'CSS',
                'prerequisites': ['CSS 211', 'CSS 201'],
                'sections': [
                    {'section_number': 'A', 'section_id': '13411', 'instructor': 'TBA',
                     'meeting_times': [{'days': ['M', 'W'], 'start_time': '13:15', 'end_time': '15:15', 'location': 'UW Bothell'}], 'credits': 5},
                    {'section_number': 'B', 'section_id': '13412', 'instructor': 'TBA',
                     'meeting_times': [{'days': ['T', 'Th'], 'start_time': '11:00', 'end_time': '13:00', 'location': 'UW Bothell'}], 'credits': 5},
                ]
            },
            {
                'code': 'CSS 343',
                'title': 'Data Structures, Algorithms, and Discrete Math II',
                'credit_hours': 5,
                'department': 'CSS',
                'prerequisites': ['CSS 342'],
                'sections': [
                    {'section_number': 'B', 'section_id': '13431', 'instructor': 'TBA',
                     'meeting_times': [{'days': ['M', 'W'], 'start_time': '11:00', 'end_time': '13:00', 'location': 'UW Bothell'}], 'credits': 5},
                ]
            },
            {
                'code': 'CSS 360',
                'title': 'Software Engineering',
                'credit_hours': 5,
                'department': 'CSS',
                'prerequisites': ['CSS 342'],
                'sections': [
                    {'section_number': 'B', 'section_id': '13601', 'instructor': 'TBA',
                     'meeting_times': [{'days': ['T', 'Th'], 'start_time': '11:00', 'end_time': '13:00', 'location': 'UW Bothell'}], 'credits': 5},
                ]
            },
            {
                'code': 'CSS 370',
                'title': 'Analysis and Design',
                'credit_hours': 5,
                'department': 'CSS',
                'prerequisites': ['CSS 342'],
                'sections': [
                    {'section_number': 'C', 'section_id': '13701', 'instructor': 'TBA',
                     'meeting_times': [{'days': ['T', 'Th'], 'start_time': '13:15', 'end_time': '15:15', 'location': 'UW Bothell'}], 'credits': 5},
                ]
            },
            {
                'code': 'CSS 382',
                'title': 'Introduction to Artificial Intelligence',
                'credit_hours': 5,
                'department': 'CSS',
                'prerequisites': ['CSS 342'],
                'sections': [
                    {'section_number': 'A', 'section_id': '13821', 'instructor': 'TBA',
                     'meeting_times': [{'days': ['T', 'Th'], 'start_time': '11:00', 'end_time': '13:00', 'location': 'UW Bothell'}], 'credits': 5},
                ]
            },
            {
                'code': 'CSS 385',
                'title': 'Intro to Game Development',
                'credit_hours': 5,
                'department': 'CSS',
                'prerequisites': ['CSS 342'],
                'sections': [
                    {'section_number': 'A', 'section_id': '13851', 'instructor': 'TBA',
                     'meeting_times': [{'days': ['M', 'W'], 'start_time': '15:30', 'end_time': '17:30', 'location': 'UW Bothell'}], 'credits': 5},
                ]
            },
            {
                'code': 'CSS 475',
                'title': 'Database Systems',
                'credit_hours': 5,
                'department': 'CSS',
                'prerequisites': ['CSS 343'],
                'sections': [
                    {'section_number': 'A', 'section_id': '14751', 'instructor': 'TBA',
                     'meeting_times': [{'days': ['M'], 'start_time': '15:30', 'end_time': '17:30', 'location': 'UW Bothell'}], 'credits': 5},
                    {'section_number': 'B', 'section_id': '14752', 'instructor': 'TBA',
                     'meeting_times': [{'days': ['T', 'Th'], 'start_time': '11:00', 'end_time': '13:00', 'location': 'UW Bothell'}], 'credits': 5},
                ]
            },
        ]
        logger.info(f"Generated {len(sample_courses)} sample courses")
        return sample_courses
