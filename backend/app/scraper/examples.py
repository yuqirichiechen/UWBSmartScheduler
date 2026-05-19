"""Example usage of the UW DawgPath Course Scraper."""

from app.scraper import UWScheduleScraper
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_1_basic_scraping():
    """Example 1: Basic course scraping with defaults."""
    logger.info("=== Example 1: Basic Scraping ===")
    
    scraper = UWScheduleScraper()
    
    # Scrape all courses from Bothell CSS department
    courses = scraper.scrape_courses()
    
    print(f"\nScraped {len(courses)} courses:")
    for course in courses:
        print(f"  {course['code']}: {course['title']} ({course['credit_hours']} credits)")


def example_2_scrape_multiple_departments():
    """Example 2: Scrape multiple departments with quarter filter."""
    logger.info("=== Example 2: Multiple Departments ===")
    
    scraper = UWScheduleScraper()
    
    # Scrape CSS and MATH from Bothell for Spring 2026
    courses = scraper.scrape_all_courses(
        campus="Bothell",
        quarter="Spring 2026",
        departments=["CSS", "MATH"]
    )
    
    print(f"\nScraped {len(courses)} courses from CSS and MATH departments:")
    for course in courses:
        print(f"  {course['code']}: {course['title']}")


def example_3_scrape_all_departments():
    """Example 3: Scrape all available departments (full campus)."""
    logger.info("=== Example 3: Full Campus Scrape ===")
    
    scraper = UWScheduleScraper()
    
    # This will scrape all 13+ departments in parallel
    courses = scraper.scrape_all_courses(campus="Bothell")
    
    print(f"\nScraped {len(courses)} total courses from all departments")
    
    # Group by department
    by_dept = {}
    for course in courses:
        dept = course['department']
        by_dept[dept] = by_dept.get(dept, 0) + 1
    
    print("\nBreakdown by department:")
    for dept in sorted(by_dept.keys()):
        print(f"  {dept}: {by_dept[dept]} courses")


def example_4_analyze_course_details():
    """Example 4: Detailed analysis of course information."""
    logger.info("=== Example 4: Course Detail Analysis ===")
    
    scraper = UWScheduleScraper()
    courses = scraper.scrape_all_courses(
        campus="Bothell",
        departments=["CSS"]
    )
    
    for course in courses[:3]:  # Analyze first 3 courses
        print(f"\n{course['code']}: {course['title']}")
        print(f"  Credits: {course['credit_hours']}")
        print(f"  Prerequisites: {', '.join(course['prerequisites']) if course['prerequisites'] else 'None'}")
        print(f"  Total Sections: {len(course['sections'])}")
        
        for section in course['sections']:
            print(f"\n  Section {section['section_number']} (SLN: {section['section_id']})")
            print(f"    Instructor: {section['instructor']}")
            
            for meeting in section['meeting_times']:
                if meeting['days']:
                    days = ", ".join(meeting['days'])
                    time_str = f"{meeting['start_time']}-{meeting['end_time']}"
                    location = f"@ {meeting['location']}" if meeting['location'] else ""
                    print(f"    {days}: {time_str} {location}")
                else:
                    print(f"    Arranged/Online")


def example_5_filter_by_schedule():
    """Example 5: Filter courses by meeting time preference."""
    logger.info("=== Example 5: Schedule Filtering ===")
    
    scraper = UWScheduleScraper()
    courses = scraper.scrape_all_courses(
        campus="Bothell",
        departments=["CSS", "MATH"]
    )
    
    # Find all MWF courses
    mwf_courses = []
    for course in courses:
        for section in course['sections']:
            for meeting in section['meeting_times']:
                if set(['M', 'W', 'F']).issubset(set(meeting['days'])):
                    mwf_courses.append({
                        'code': course['code'],
                        'section': section['section_number'],
                        'time': f"{meeting['start_time']}-{meeting['end_time']}",
                        'location': meeting['location']
                    })
    
    print(f"\nFound {len(mwf_courses)} MWF course sections:")
    for item in mwf_courses:
        print(f"  {item['code']} Section {item['section']}: {item['time']} @ {item['location']}")


def example_6_prerequisite_checking():
    """Example 6: Check prerequisites for courses."""
    logger.info("=== Example 6: Prerequisite Checking ===")
    
    scraper = UWScheduleScraper()
    courses = scraper.scrape_all_courses(
        campus="Bothell",
        departments=["CSS"]
    )
    
    # Find courses with prerequisites
    courses_with_prereqs = [c for c in courses if c['prerequisites']]
    
    print(f"\nCourses with prerequisites:")
    for course in courses_with_prereqs:
        print(f"  {course['code']}: {' → '.join(course['prerequisites'])}")


def example_7_cache_management():
    """Example 7: Work with cached data."""
    logger.info("=== Example 7: Cache Management ===")
    
    scraper = UWScheduleScraper()
    
    # First call - live scrape
    logger.info("First scrape (live)...")
    courses1 = scraper.scrape_all_courses(
        campus="Bothell",
        departments=["CSS"]
    )
    print(f"Retrieved {len(courses1)} courses")
    
    # Second call - from cache (much faster)
    logger.info("Second scrape (cached)...")
    courses2 = scraper.scrape_all_courses(
        campus="Bothell",
        departments=["CSS"]
    )
    print(f"Retrieved {len(courses2)} courses (from cache)")
    
    # Validate cache
    is_valid = scraper.validate_cache()
    print(f"Cache valid: {is_valid}")


def example_8_different_campuses():
    """Example 8: Compare courses across different UW campuses."""
    logger.info("=== Example 8: Multi-Campus Comparison ===")
    
    scraper = UWScheduleScraper()
    
    campuses_data = {}
    for campus in ["Bothell", "Seattle", "Tacoma"]:
        try:
            courses = scraper.scrape_all_courses(
                campus=campus,
                departments=["CSS"]
            )
            campuses_data[campus] = len(courses)
        except Exception as e:
            logger.error(f"Error scraping {campus}: {e}")
            campuses_data[campus] = 0
    
    print("\nCSS Courses by Campus:")
    for campus, count in campuses_data.items():
        print(f"  {campus}: {count} courses")


def example_9_export_to_json():
    """Example 9: Export scraped data to JSON file."""
    logger.info("=== Example 9: Export to JSON ===")
    
    scraper = UWScheduleScraper()
    courses = scraper.scrape_all_courses(
        campus="Bothell",
        departments=["CSS"]
    )
    
    # Export to JSON
    output_file = "css_courses.json"
    with open(output_file, 'w') as f:
        json.dump(courses, f, indent=2)
    
    print(f"\nExported {len(courses)} courses to {output_file}")
    print(f"File size: {len(json.dumps(courses, indent=2)) / 1024:.1f} KB")


def example_10_find_conflicts():
    """Example 10: Find scheduling conflicts."""
    logger.info("=== Example 10: Schedule Conflict Detection ===")
    
    def time_overlap(time1_start, time1_end, time2_start, time2_end):
        """Check if two times overlap."""
        return not (time1_end <= time2_start or time2_end <= time1_start)
    
    scraper = UWScheduleScraper()
    courses = scraper.scrape_all_courses(
        campus="Bothell",
        departments=["CSS"]
    )
    
    # Find MW courses and TTh courses (no conflicts)
    mw_sections = []
    tth_sections = []
    
    for course in courses:
        for section in course['sections']:
            for meeting in section['meeting_times']:
                if meeting['days']:
                    days_set = set(meeting['days'])
                    if days_set <= {'M', 'W', 'F'}:
                        mw_sections.append(course['code'] + f" Sec {section['section_number']}")
                    elif days_set <= {'T', 'Th'}:
                        tth_sections.append(course['code'] + f" Sec {section['section_number']}")
    
    print(f"\nMWF Sections: {len(mw_sections)}")
    for sec in mw_sections[:5]:
        print(f"  {sec}")
    
    print(f"\nTTh Sections: {len(tth_sections)}")
    for sec in tth_sections[:5]:
        print(f"  {sec}")


if __name__ == "__main__":
    # Run examples
    print("=" * 60)
    print("UW DawgPath Course Scraper - Usage Examples")
    print("=" * 60)
    
    # Uncomment examples to run
    
    example_1_basic_scraping()
    # example_2_scrape_multiple_departments()
    # example_3_scrape_all_departments()
    # example_4_analyze_course_details()
    # example_5_filter_by_schedule()
    # example_6_prerequisite_checking()
    # example_7_cache_management()
    # example_8_different_campuses()
    # example_9_export_to_json()
    # example_10_find_conflicts()
