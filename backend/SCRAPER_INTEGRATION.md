# UW DawgPath Scraper Integration Guide

## Quick Start

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Basic Usage in Your Code
```python
from app.scraper import UWScheduleScraper

# Initialize scraper
scraper = UWScheduleScraper()

# Scrape courses
courses = scraper.scrape_all_courses(
    campus="Bothell",
    departments=["CSS"]
)

# Use the data
for course in courses:
    print(f"{course['code']}: {course['title']}")
```

## Integration with FastAPI Backend

### Setup in main.py
```python
from fastapi import FastAPI
from app.scraper import UWScheduleScraper

app = FastAPI()
scraper = UWScheduleScraper(cache_dir="data/cache")

@app.get("/api/courses")
async def get_courses(campus: str = "Bothell", departments: str = "CSS"):
    """Get courses for given campus and departments."""
    dept_list = departments.split(",")
    courses = scraper.scrape_all_courses(
        campus=campus,
        departments=dept_list
    )
    return {"courses": courses}

@app.get("/api/courses/{course_code}")
async def get_course(course_code: str):
    """Get specific course details."""
    courses = scraper.scrape_all_courses(campus="Bothell")
    course = next((c for c in courses if c['code'] == course_code), None)
    return course or {"error": "Course not found"}
```

### Setup in RAG Pipeline
```python
from app.scraper import UWScheduleScraper
from app.embedding import EmbeddingService
from app.rag import RAGPipeline

class ScheduleRAGPipeline:
    def __init__(self):
        self.scraper = UWScheduleScraper(cache_dir="data/cache")
        self.embedder = EmbeddingService()
        
    def initialize(self):
        """Initialize the RAG system with course data."""
        # Scrape all courses
        courses = self.scraper.scrape_all_courses(
            campus="Bothell",
            departments=["CSS", "MATH"]  # Add more as needed
        )
        
        # Embed course data
        for course in courses:
            course_text = f"{course['code']}: {course['title']}. " \
                         f"Credits: {course['credit_hours']}. " \
                         f"Sections: {len(course['sections'])}"
            embedding = self.embedder.embed_text(course_text)
            # Store in vector database
```

## API Endpoints

### Course Retrieval
```
GET /api/courses?campus=Bothell&departments=CSS,MATH
GET /api/courses/CSS342
GET /api/schedule?quarter=Spring+2026&campus=Bothell
```

### Schedule Generation
```
POST /api/schedule
{
  "query": "I want CSS core courses on MWF in the morning",
  "completed_courses": ["CSS 143", "CSS 161"],
  "max_credits": 12
}
```

## Data Validation

### Validate Scraped Courses
```python
from pydantic import ValidationError
from app.models import Course, CourseSection

def validate_courses(courses):
    """Validate scraped course data."""
    validated = []
    for course_data in courses:
        try:
            # Convert to Pydantic model for validation
            sections = [
                CourseSection(
                    section_number=s['section_number'],
                    section_id=s['section_id'],
                    instructor=s['instructor'],
                    meeting_times=s['meeting_times'],
                    credits=s['credits']
                )
                for s in course_data['sections']
            ]
            
            course = Course(
                code=course_data['code'],
                title=course_data['title'],
                prerequisites=course_data['prerequisites'],
                sections=sections,
                credit_hours=course_data['credit_hours'],
                department=course_data['department']
            )
            validated.append(course)
        except ValidationError as e:
            logger.error(f"Validation error for {course_data['code']}: {e}")
    
    return validated
```

## Performance Optimization

### Caching Strategy
```python
# Cache courses for 24 hours by default
# Check cache before scraping

def get_courses_optimized(campus, departments):
    scraper = UWScheduleScraper()
    
    # Try cache first
    courses = scraper._load_cached_courses(
        cache_key=scraper._get_cache_key(campus, None, departments)
    )
    
    if courses:
        logger.info("Using cached courses")
        return courses
    
    # Live scrape if cache miss
    logger.info("Cache miss, scraping live data")
    courses = scraper.scrape_all_courses(campus, departments=departments)
    return courses
```

### Batch Scraping
```python
# Scrape multiple departments efficiently
all_courses = {}

for campus in ["Bothell", "Seattle", "Tacoma"]:
    courses = scraper.scrape_all_courses(campus=campus)
    all_courses[campus] = courses
```

## Error Handling

### Graceful Fallbacks
```python
def get_courses_with_fallback(campus, departments):
    """Get courses with multiple fallback strategies."""
    
    try:
        # Try primary scrape
        courses = scraper.scrape_all_courses(campus, departments=departments)
        if courses:
            return courses
    except Exception as e:
        logger.error(f"Primary scrape failed: {e}")
    
    try:
        # Try loading from cache
        courses = scraper._load_cached_courses()
        if courses:
            logger.info("Using fallback cache")
            return courses
    except Exception as e:
        logger.error(f"Cache loading failed: {e}")
    
    # Final fallback to sample data
    logger.warning("Using sample data")
    return scraper._generate_sample_courses()
```

## Database Integration

### Store Scraped Data
```python
from app.models import db, CourseModel

def store_courses_to_db(courses):
    """Store scraped courses in database."""
    for course_data in courses:
        # Check if course exists
        existing = CourseModel.query.filter_by(
            code=course_data['code']
        ).first()
        
        if existing:
            # Update existing
            existing.update(course_data)
        else:
            # Create new
            course = CourseModel(
                code=course_data['code'],
                title=course_data['title'],
                credits=course_data['credit_hours'],
                department=course_data['department'],
                data=course_data  # Store full data as JSON
            )
            db.session.add(course)
    
    db.session.commit()
```

## Monitoring & Logging

### Setup Logging
```python
import logging
from app.utils.logging_config import setup_logging

# Configure detailed logging for scraper
setup_logging(level=logging.DEBUG)
logger = logging.getLogger("app.scraper")

# Usage
scraper = UWScheduleScraper()
courses = scraper.scrape_all_courses(campus="Bothell")
# Logs will show all details about scraping process
```

### Monitor Scrape Success
```python
def monitor_scrape_health():
    """Monitor scraper health metrics."""
    scraper = UWScheduleScraper()
    
    metrics = {
        'timestamp': datetime.now(),
        'cache_valid': scraper.validate_cache(),
        'cache_files': len(list(scraper.cache_dir.glob("courses_*.json"))),
    }
    
    try:
        courses = scraper.scrape_all_courses(campus="Bothell", departments=["CSS"])
        metrics['courses_scraped'] = len(courses)
        metrics['status'] = 'success'
    except Exception as e:
        metrics['error'] = str(e)
        metrics['status'] = 'failed'
    
    return metrics
```

## Testing

### Run Scraper Tests
```bash
cd backend
pytest app/scraper/test_scraper.py -v
```

### Run Examples
```bash
cd backend
python -m app.scraper.examples
```

## Troubleshooting

### Issue: "No courses parsed"
**Check**:
1. Website structure hasn't changed
2. URL is accessible
3. Department code is valid
4. Try with sample courses: `scraper._generate_sample_courses()`

**Solution**:
```python
# Debug parsing
html = scraper._fetch_with_retry(url)
soup = BeautifulSoup(html, 'html.parser')
tables = soup.find_all('table')
print(f"Found {len(tables)} tables")
# Inspect HTML structure
```

### Issue: Slow scraping
**Solution**:
```python
# Use department filters
courses = scraper.scrape_all_courses(
    campus="Bothell",
    departments=["CSS"]  # Faster than all departments
)

# Use cache
courses = scraper.scrape_all_courses(
    campus="Bothell",
    departments=["CSS"]
)
# Second call will be instant
```

### Issue: Network timeouts
**Solution**:
```python
# Increase timeout
scraper = UWScheduleScraper(
    timeout=30,      # 30 second timeout
    max_retries=5    # More retries
)
```

## Production Deployment

### Environment Setup
```bash
# .env file
SCRAPER_CACHE_DIR=data/cache
SCRAPER_MAX_RETRIES=3
SCRAPER_TIMEOUT=15
```

### Health Check Endpoint
```python
@app.get("/api/health")
async def health_check():
    """Check scraper health."""
    try:
        # Validate cache
        is_valid = scraper.validate_cache()
        
        # Try light scrape
        courses = scraper.scrape_all_courses(
            campus="Bothell",
            departments=["CSS"]
        )
        
        return {
            "status": "healthy",
            "cache_valid": is_valid,
            "courses_available": len(courses) > 0
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
```

### Scheduled Updates
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

def refresh_course_cache():
    """Refresh course cache periodically."""
    logger.info("Starting scheduled course cache refresh")
    try:
        courses = scraper.scrape_all_courses(campus="Bothell")
        logger.info(f"Successfully refreshed {len(courses)} courses")
    except Exception as e:
        logger.error(f"Failed to refresh cache: {e}")

# Refresh every 6 hours
scheduler.add_job(refresh_course_cache, 'interval', hours=6)
scheduler.start()
```

## Next Steps

1. **Test with live data**: Run examples and verify parsing works
2. **Integrate with RAG**: Connect to embedding service
3. **Set up database**: Store courses for fast access
4. **Deploy**: Add to production FastAPI backend
5. **Monitor**: Set up logging and health checks
