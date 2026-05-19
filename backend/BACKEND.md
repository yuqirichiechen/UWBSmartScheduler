# Backend Development Guide

## Overview

The backend is a Python FastAPI application that implements the RAG pipeline, course scraping, embeddings, and schedule recommendation logic.

## Project Structure

```
backend/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── config.py                # Environment configuration
│   ├── models/                  # Data models
│   │   ├── course.py            # Course, Section, Schedule models
│   │   └── constraint.py        # ScheduleConstraint model
│   ├── scraper/                 # Web scraping
│   │   └── uw_scheduler_scraper.py   # UW Bothell scraper
│   ├── embedding/               # Embeddings & vector store
│   │   ├── embedding_service.py # OpenAI embeddings
│   │   └── vector_store.py      # Pinecone integration
│   ├── rag/                     # RAG pipeline
│   │   ├── rag_pipeline.py      # Main RAG coordination
│   │   ├── constraint_parser.py # NLP constraint extraction
│   │   └── conflict_checker.py  # Schedule conflict detection
│   └── utils/                   # Utilities
│       ├── prerequisites.py     # Prerequisite graph
│       └── logging_config.py    # Logging setup
├── main.py                      # FastAPI application entry point
├── requirements.txt             # Python dependencies
├── test_system.py               # Integration tests
└── .env.example                 # Environment template
```

## Quick Start

### 1. Setup Environment

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy env template
cp .env.example .env
```

## Quick Start

### 1. Setup Environment

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy env template
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` and add your API keys:

```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4
PINECONE_API_KEY=your-pinecone-key
```

### 3. Using the Course Scraper

The scraper is fully implemented and ready to use:

```python
from app.scraper import UWScheduleScraper

# Initialize scraper
scraper = UWScheduleScraper(cache_dir="data/cache")

# Scrape courses from Bothell
courses = scraper.scrape_all_courses(campus="Bothell", departments=["CSS"])

# Or scrape all departments (parallel)
all_courses = scraper.scrape_all_courses(campus="Bothell")
```

**Features:**
- ✅ Multi-campus support (Bothell, Seattle, Tacoma)
- ✅ Intelligent caching with hash validation
- ✅ Parallel department scraping (4 workers)
- ✅ Robust error handling with exponential backoff
- ✅ Comprehensive data extraction (meeting times, locations, instructors)
- ✅ Prerequisites database
- ✅ Fallback to sample courses for testing

See [SCRAPER_INTEGRATION.md](./SCRAPER_INTEGRATION.md) for detailed integration guide.
See [app/scraper/SCRAPER_GUIDE.md](./app/scraper/SCRAPER_GUIDE.md) for API reference.
See [app/scraper/examples.py](./app/scraper/examples.py) for usage examples.

### 4. Run Backend
PINECONE_ENVIRONMENT=your-env
PINECONE_INDEX_NAME=uwbothell-courses
```


### 3. Run Backend

```bash
python main.py
```

The server will start at `http://localhost:8000`

### 4. Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Core Components

### Web Scraper (`app/scraper/uw_scheduler_scraper.py`)

**Comprehensive DawgPath course scraper with multi-campus support.**

**Features**:
- ✅ Scrapes from all UW campuses (Bothell, Seattle, Tacoma)
- ✅ Supports 13+ departments (CSS, CSE, MATH, PHYS, CHEM, BIOL, ENG, ACCT, ECON, PSYCH, HIST, POLS, GEOL)
- ✅ Parallel department scraping with ThreadPoolExecutor (4 workers)
- ✅ Intelligent caching with SHA-256 hash validation
- ✅ Exponential backoff retry logic (3 attempts by default)
- ✅ Multiple HTML parsing strategies (DawgPath format + generic tables)
- ✅ Flexible time/day parsing (handles multiple formats)
- ✅ Location and instructor extraction
- ✅ Prerequisite database integration
- ✅ Fallback to sample courses for development/testing
- ✅ Full backward compatibility

**Usage**:
```python
from app.scraper import UWScheduleScraper

# Initialize
scraper = UWScheduleScraper(cache_dir="data/cache", max_retries=3, timeout=15)

# Scrape with filters
courses = scraper.scrape_all_courses(
    campus="Bothell",
    quarter="Spring 2026",
    departments=["CSS", "MATH"]
)

# Scrape all departments (parallel)
all_courses = scraper.scrape_all_courses(campus="Bothell")

# Direct URL scraping (backward compatible)
courses = scraper.scrape_courses("https://uwb.edu/schedule?dept=CSS")
```

**Data Structure**:
```python
{
    'code': 'CSS 342',
    'title': 'Data Structures',
    'credit_hours': 4,
    'department': 'CSS',
    'prerequisites': ['CSS 211'],
    'sections': [{
        'section_number': 'A',
        'section_id': '13411',  # SLN
        'instructor': 'Dr. Emma Martinez',
        'meeting_times': [{
            'days': ['M', 'W'],
            'start_time': '14:00',
            'end_time': '15:20',
            'location': 'UWB 301'
        }],
        'credits': 4
    }]
}
```

**Cache System**:
- Caches by campus/quarter/department combination
- Stores with hash validation
- Auto-loads most recent cache
- Manual cache validation: `scraper.validate_cache()`

**Performance**:
- Single department: 2-5 seconds
- All departments (parallel): 15-30 seconds  
- Cache hit: <100ms

**Documentation**:
- [SCRAPER_GUIDE.md](./app/scraper/SCRAPER_GUIDE.md) - Complete API reference
- [SCRAPER_INTEGRATION.md](./SCRAPER_INTEGRATION.md) - Integration patterns
- [examples.py](./app/scraper/examples.py) - 10 usage examples
- [test_scraper.py](./app/scraper/test_scraper.py) - Unit tests


# Cache courses with hash validation
hash_value = scraper.cache_courses(courses)

# Validate cache integrity
is_valid = scraper.validate_cache()
```

### Embedding Service (`app/embedding/embedding_service.py`)

Generates OpenAI embeddings for course data.

**Features**:
- OpenAI API integration
- Batch embedding for efficiency
- Course-specific text formatting
- Error handling and logging

**Usage**:
```python
from app.embedding import EmbeddingService

service = EmbeddingService(api_key="sk-...", model="text-embedding-3-small")

# Single embedding
embedding = service.embed_course_data("CSS 342: Data Structures...")

# Batch embeddings
embeddings = service.batch_embed_courses(course_texts, batch_size=100)

# Format course for embedding
formatted = service.format_course_for_embedding(course_dict)
```

### Vector Store (`app/embedding/vector_store.py`)

Manages embeddings in Pinecone (with mock fallback).

**Features**:
- Pinecone integration
- Mock in-memory storage for development
- Similarity search
- Metadata filtering
- Index statistics

**Usage**:
```python
from app.embedding import VectorStore

# With Pinecone
store = VectorStore(api_key="...", environment="...", index_name="courses")

# Or mock mode (development)
store = VectorStore()  # Uses in-memory storage

# Upsert embeddings
vectors = [
    ("id1", embedding_vector, metadata),
    ("id2", embedding_vector, metadata),
]
store.upsert_embeddings(vectors)

# Query
results = store.query(query_vector, top_k=5)
```

### Constraint Parser (`app/rag/constraint_parser.py`)

Extracts scheduling constraints from natural language queries.

**Features**:
- Natural language parsing with regex
- Extracts: credits, days, times, required courses
- Prerequisite eligibility check
- Day preference/avoidance detection
- Time window parsing (morning, afternoon, evening)

**Usage**:
```python
from app.rag import ConstraintParser

query = "I want CSS core requirements, only Tuesday and Thursday, max 14 credits"
constraints = ConstraintParser.parse_query(query)

# Returns:
# {
#   "query": "...",
#   "max_credits": 14,
#   "preferred_days": ["T", "Th"],
#   "required_courses": ["CSS ..."],
#   "no_online": False
# }
```

### RAG Pipeline (`app/rag/rag_pipeline.py`)

Generates schedule recommendations using RAG and LLM.

**Features**:
- Retrieval: semantic search from vector store
- Augmentation: formatting context for LLM
- Generation: GPT-4 reasoning for recommendations
- Prompt engineering for schedule-specific optimization

**Usage**:
```python
from app.rag import RAGPipeline

pipeline = RAGPipeline(openai_api_key="sk-...", openai_model="gpt-4")

recommendation = pipeline.recommend_schedule(
    constraints=parsed_constraints,
    retrieved_courses=courses_from_vector_store,
    completed_courses=["CSS 143", "CSS 161"]
)
```

### Conflict Checker (`app/rag/conflict_checker.py`)

Detects and validates schedule conflicts.

**Features**:
- Time overlap detection
- Prerequisite validation
- Credit limit checking
- Day preference enforcement
- Comprehensive schedule validation

**Usage**:
```python
from app.rag import ConflictChecker

# Check for time conflicts
no_conflicts, conflicts = ConflictChecker.check_conflicts(sections)

# Check prerequisite eligibility
eligible, missing = ConflictChecker.check_prerequisite_eligibility(
    course_code, prerequisites, completed_courses
)

# Full schedule validation
is_valid, issues = ConflictChecker.validate_schedule_constraints(
    sections, constraints, completed_courses
)
```

## API Endpoints

### POST `/api/schedule`

Generate schedule recommendations.

**Request**:
```json
{
  "query": "I want CSS core requirements, only come Tuesday and Thursday, max 14 credits",
  "completed_courses": ["CSS 143", "CSS 161"]
}
```

**Response**:
```json
{
  "query": "...",
  "recommendations": "Based on your constraints, I recommend...",
  "constraints": {...},
  "recommended_courses": ["CSS 342", "CSS 385"],
  "is_valid": true,
  "issues": []
}
```

### GET `/api/courses`

Get all available courses.

**Response**:
```json
{
  "courses": [...],
  "count": 5,
  "status": "ready"
}
```

### GET `/api/courses/{course_code}`

Get details for a specific course.

### POST `/api/scrape`

Manually trigger course data scraping.

### GET `/health`

Health check with service status.

### GET `/api/vector-store/stats`

Get vector store statistics.

## Testing

Run the comprehensive integration test suite:

```bash
python test_system.py
```

This runs all 7 major component tests:
1. Web Scraper
2. Constraint Parser
3. Conflict Checker
4. Embedding Service
5. Vector Store
6. RAG Pipeline
7. Prerequisite Graph

## Development Workflow

### Adding a New Constraint Type

Edit `app/rag/constraint_parser.py`:

```python
@staticmethod
def _extract_new_constraint(query: str) -> Optional[SomeType]:
    """Extract new constraint from query."""
    # Add regex patterns
    # Add to parse_query() return dict
    pass
```

### Adding a New Validation Rule

Edit `app/rag/conflict_checker.py`:

```python
def validate_new_rule(self, sections, constraints):
    """Validate new scheduling rule."""
    # Add validation logic
    # Return (is_valid, issues)
    pass
```

### Improving Course Scraper

Edit `app/scraper/uw_scheduler_scraper.py`:

```python
def _parse_html(self, html_content: str) -> List[Dict]:
    """Improve HTML parsing."""
    # Add better selectors
    # Add more data extraction
    pass
```

## Deployment

### Production Checklist

- [ ] Set secure OpenAI API key
- [ ] Configure Pinecone with production credentials
- [ ] Set `ENVIRONMENT=production` and `DEBUG=False`
- [ ] Enable request logging
- [ ] Setup error monitoring (Sentry, etc.)
- [ ] Configure CORS appropriately
- [ ] Add rate limiting
- [ ] Setup CI/CD pipeline

### Docker Deployment

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

## Troubleshooting

### OpenAI API Key Issues

```bash
# Check if key is set
echo $OPENAI_API_KEY

# Verify in .env
cat .env | grep OPENAI_API_KEY
```

### Pinecone Connection Errors

```bash
# Verify credentials
echo $PINECONE_API_KEY
echo $PINECONE_ENVIRONMENT

# Test connection separately
python -c "import pinecone; pinecone.init(...)"
```

### Course Data Not Loading

```bash
# Check cache directory
ls -la data/cache/

# Force rescrape
curl -X POST http://localhost:8000/api/scrape

# Check /health endpoint
curl http://localhost:8000/health
```

## Performance Optimization

### Embedding Generation
- Use batch processing for efficiency
- Cache embeddings to avoid regeneration
- Consider async processing for large datasets

### Vector Search
- Monitor query latency
- Tune `top_k` parameter
- Use metadata filtering to reduce search space

### LLM Calls
- Cache similar recommendations
- Use temperature=0.7 for balance
- Monitor token usage and costs

## Monitoring & Logging

All components log to stdout:

```bash
# View logs
tail -f app.log

# Filter by component
grep "EmbeddingService" app.log
grep "RAGPipeline" app.log
```

Configure logging in `app/utils/logging_config.py`.

## Contributing

1. Create feature branch: `git checkout -b feature/new-feature`
2. Make changes and test: `python test_system.py`
3. Commit: `git commit -m "Add new feature"`
4. Push: `git push origin feature/new-feature`
5. Create Pull Request

## Resources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [OpenAI API](https://platform.openai.com/docs/api-reference)
- [Pinecone Docs](https://docs.pinecone.io/)
- [BeautifulSoup Guide](https://www.crummy.com/software/BeautifulSoup/)
