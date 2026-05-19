"""Tests for the UW DawgPath Course Scraper."""

import pytest
import json
from pathlib import Path
from datetime import datetime
from app.scraper import UWScheduleScraper


class TestUWScheduleScraper:
    """Test suite for UWScheduleScraper."""
    
    @pytest.fixture
    def scraper(self, tmp_path):
        """Create a scraper instance with temporary cache directory."""
        return UWScheduleScraper(cache_dir=str(tmp_path))
    
    def test_scraper_initialization(self, scraper):
        """Test that scraper initializes correctly."""
        assert scraper.cache_dir.exists()
        assert scraper.max_retries == 3
        assert scraper.timeout == 15
        assert scraper.session is not None
    
    def test_get_campus_url_valid(self, scraper):
        """Test getting valid campus URLs."""
        assert scraper._get_campus_url("Bothell") == "https://www.uwb.edu/students/schedule"
        assert scraper._get_campus_url("Seattle") == "https://www.washington.edu/students/crscat/"
        assert scraper._get_campus_url("Tacoma") == "https://www.tacoma.uw.edu/students/class-schedule"
    
    def test_get_campus_url_invalid(self, scraper):
        """Test getting invalid campus URL."""
        assert scraper._get_campus_url("InvalidCampus") is None
    
    def test_get_cache_key(self, scraper):
        """Test cache key generation."""
        key1 = scraper._get_cache_key("Bothell", None, None)
        assert key1 == "bothell"
        
        key2 = scraper._get_cache_key("Bothell", "Spring 2026", None)
        assert key2 == "bothell_spring_2026"
        
        key3 = scraper._get_cache_key("Bothell", "Spring 2026", ["CSS", "MATH"])
        assert key3 == "bothell_spring_2026_css_math"
        
        # Verify consistency
        assert scraper._get_cache_key("Bothell", "Spring 2026", ["MATH", "CSS"]) == key3
    
    def test_parse_meeting_time_mwf(self, scraper):
        """Test parsing MWF meeting times."""
        meetings = scraper._parse_meeting_time("MWF", "10:30am - 11:50am")
        
        assert len(meetings) == 1
        assert set(meetings[0]['days']) == {'M', 'W', 'F'}
        assert meetings[0]['start_time'] == "10:30"
        assert meetings[0]['end_time'] == "11:50"
    
    def test_parse_meeting_time_tth(self, scraper):
        """Test parsing TTh meeting times."""
        meetings = scraper._parse_meeting_time("T Th", "2:00pm - 3:20pm")
        
        assert len(meetings) == 1
        assert set(meetings[0]['days']) == {'T', 'Th'}
        assert meetings[0]['start_time'] == "14:00"
        assert meetings[0]['end_time'] == "15:20"
    
    def test_parse_meeting_time_arranged(self, scraper):
        """Test parsing arranged/online courses."""
        meetings = scraper._parse_meeting_time("Arranged", "")
        
        assert len(meetings) == 1
        assert meetings[0]['days'] == []
        assert meetings[0]['location'] == 'Arranged/Online'
    
    def test_parse_meeting_time_midnight_boundary(self, scraper):
        """Test time parsing with midnight boundary."""
        meetings = scraper._parse_meeting_time("M", "11:30pm - 12:30am")
        
        assert len(meetings) == 1
        assert meetings[0]['start_time'] == "23:30"
        assert meetings[0]['end_time'] == "00:30"
    
    def test_get_prerequisites_css143(self, scraper):
        """Test getting prerequisites for CSS 143."""
        prerequisites = scraper._get_prerequisites("CSS 143")
        assert prerequisites == []
    
    def test_get_prerequisites_css342(self, scraper):
        """Test getting prerequisites for CSS 342."""
        prerequisites = scraper._get_prerequisites("CSS 342")
        assert "CSS 211" in prerequisites
    
    def test_get_prerequisites_css486(self, scraper):
        """Test getting prerequisites for CSS 486."""
        prerequisites = scraper._get_prerequisites("CSS 486")
        assert "CSS 342" in prerequisites
        assert "CSS 330" in prerequisites
    
    def test_get_prerequisites_unknown_course(self, scraper):
        """Test getting prerequisites for unknown course."""
        prerequisites = scraper._get_prerequisites("UNK 999")
        assert prerequisites == []
    
    def test_cache_and_load_courses(self, scraper):
        """Test caching and loading courses."""
        sample_courses = [
            {
                'code': 'CSS 143',
                'title': 'Computer Science I',
                'credit_hours': 4,
                'department': 'CSS',
                'prerequisites': [],
                'sections': []
            }
        ]
        
        # Cache courses
        hash1 = scraper.cache_courses(sample_courses, cache_key="test_cache")
        assert hash1 is not None
        
        # Load courses
        loaded = scraper._load_cached_courses(cache_key="test_cache")
        assert loaded is not None
        assert len(loaded) == 1
        assert loaded[0]['code'] == 'CSS 143'
    
    def test_generate_sample_courses(self, scraper):
        """Test sample course generation."""
        courses = scraper._generate_sample_courses()
        
        assert len(courses) > 0
        assert all('code' in c for c in courses)
        assert all('title' in c for c in courses)
        assert all('sections' in c for c in courses)
        
        # Check sample CSS courses are included
        codes = {c['code'] for c in courses}
        assert 'CSS 143' in codes
        assert 'CSS 342' in codes
    
    def test_validate_cache_no_files(self, scraper):
        """Test cache validation with no cache files."""
        is_valid = scraper.validate_cache()
        assert is_valid is False
    
    def test_validate_cache_valid_file(self, scraper):
        """Test cache validation with valid cache."""
        courses = scraper._generate_sample_courses()
        scraper.cache_courses(courses, cache_key="valid_test")
        
        is_valid = scraper.validate_cache()
        assert is_valid is True
    
    def test_scrape_courses_backward_compatibility(self, scraper):
        """Test backward compatible scrape_courses method."""
        # Should return sample courses when no URL provided
        courses = scraper.scrape_courses()
        assert len(courses) > 0
        assert any(c['code'] == 'CSS 143' for c in courses)
    
    def test_department_constants(self, scraper):
        """Test that department constants are defined."""
        assert len(scraper.DEPARTMENTS) > 0
        assert 'CSS' in scraper.DEPARTMENTS
        assert 'MATH' in scraper.DEPARTMENTS
    
    def test_campus_constants(self, scraper):
        """Test that campus constants are defined."""
        assert len(scraper.UW_CAMPUSES) == 3
        assert 'Bothell' in scraper.UW_CAMPUSES
        assert 'Seattle' in scraper.UW_CAMPUSES
        assert 'Tacoma' in scraper.UW_CAMPUSES
    
    def test_css_core_courses(self, scraper):
        """Test CSS core courses list."""
        assert len(scraper.CSS_CORE_COURSES) == 10
        assert 'CSS 143' in scraper.CSS_CORE_COURSES
        assert 'CSS 486' in scraper.CSS_CORE_COURSES


class TestParsingFunctions:
    """Test HTML parsing functions."""
    
    @pytest.fixture
    def scraper(self, tmp_path):
        """Create a scraper instance."""
        return UWScheduleScraper(cache_dir=str(tmp_path))
    
    def test_parse_meeting_time_single_day(self, scraper):
        """Test parsing single day meeting times."""
        meetings = scraper._parse_meeting_time("Monday", "10:00 AM - 11:00 AM")
        assert len(meetings) == 1
        assert 'M' in meetings[0]['days']
    
    def test_parse_meeting_time_multiple_formats(self, scraper):
        """Test parsing various time formats."""
        # Test format: 10:30am - 11:50am
        m1 = scraper._parse_meeting_time("MWF", "10:30am - 11:50am")
        assert m1[0]['start_time'] == "10:30"
        
        # Test format: 10:30 AM - 11:50 AM (capitals)
        m2 = scraper._parse_meeting_time("MWF", "10:30 AM - 11:50 AM")
        assert m2[0]['start_time'] == "10:30"
        
        # Test format: 10:30am-11:50am (no spaces)
        m3 = scraper._parse_meeting_time("MWF", "10:30am-11:50am")
        assert m3[0]['start_time'] == "10:30"


class TestIntegration:
    """Integration tests."""
    
    @pytest.fixture
    def scraper(self, tmp_path):
        """Create a scraper instance."""
        return UWScheduleScraper(cache_dir=str(tmp_path))
    
    def test_scrape_all_courses_returns_list(self, scraper):
        """Test that scrape_all_courses returns a list."""
        courses = scraper.scrape_all_courses(campus="Bothell", departments=["CSS"])
        
        assert isinstance(courses, list)
        # Should return sample courses at minimum
        assert len(courses) > 0
    
    def test_scrape_all_courses_structures(self, scraper):
        """Test that returned courses have correct structure."""
        courses = scraper.scrape_all_courses(campus="Bothell", departments=["CSS"])
        
        for course in courses:
            assert 'code' in course
            assert 'title' in course
            assert 'credit_hours' in course
            assert 'department' in course
            assert 'prerequisites' in course
            assert 'sections' in course
            
            for section in course['sections']:
                assert 'section_number' in section
                assert 'section_id' in section
                assert 'instructor' in section
                assert 'meeting_times' in section
    
    def test_multiple_scrapes_same_parameters_use_cache(self, scraper):
        """Test that multiple scrapes with same parameters use cache."""
        # First scrape
        courses1 = scraper.scrape_all_courses(campus="Bothell", departments=["CSS"])
        
        # Second scrape should be cached
        courses2 = scraper.scrape_all_courses(campus="Bothell", departments=["CSS"])
        
        assert len(courses1) == len(courses2)
        assert courses1[0]['code'] == courses2[0]['code']


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
