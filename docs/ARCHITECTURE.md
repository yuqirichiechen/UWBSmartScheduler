# CSS 382 Course Scheduler - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     User (Browser)                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ HTTP/REST
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   React Frontend                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  QueryInput Component  │  ScheduleOutput Component   │  │
│  │  - Natural language    │  - Schedule display         │  │
│  │    query input         │  - Calendar view            │  │
│  │  - Example prompts     │  - Conflict indicators      │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ POST /api/schedule
                     │ GET /api/courses
                     │ POST /api/scrape
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend Server                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  RAG Pipeline                                        │  │
│  │  ├─ Constraint Parser (NLP extraction)              │  │
│  │  ├─ Vector Store Query (Semantic search)            │  │
│  │  ├─ LLM Reasoning (GPT-4)                           │  │
│  │  └─ Conflict Checker (Schedule validation)          │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Data Pipeline                                      │  │
│  │  ├─ UW Schedule Scraper                             │  │
│  │  ├─ Embedding Service (OpenAI)                      │  │
│  │  └─ Vector Store (Pinecone)                         │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Utilities                                           │  │
│  │  ├─ Prerequisite Graph                              │  │
│  │  ├─ Logging                                         │  │
│  │  └─ Configuration Management                        │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
    ┌────────┐  ┌──────────┐  ┌────────┐
    │ OpenAI │  │ Pinecone │  │UW Time │
    │  API   │  │ Vector   │  │Schedule│
    │ (GPT4) │  │  Store   │  │(Scrape)│
    └────────┘  └──────────┘  └────────┘
```

## Data Flow

### 1. Schedule Recommendation Flow

```
User Query (Natural Language)
        ↓
Constraint Parser
├─ Extract max credits
├─ Extract preferred days
├─ Extract required courses
├─ Extract time constraints
└─ Output: Structured Constraints
        ↓
Vector Store Query
├─ Embed query
├─ Semantic search
└─ Output: Top 5-10 relevant courses
        ↓
RAG Pipeline
├─ Format context from retrieved courses
├─ Build LLM prompt with constraints
├─ Call GPT-4 for reasoning
└─ Output: Course recommendations
        ↓
Conflict Checker
├─ Parse recommended sections
├─ Check for overlapping meeting times
├─ Validate prerequisite eligibility
└─ Output: Validated schedule (with warnings if conflicts)
        ↓
Schedule Response
```

### 2. Data Ingestion Flow

```
UW Bothell Time Schedule (Web)
        ↓
Web Scraper
├─ Parse HTML structure
├─ Extract course data
├─ Extract section info
├─ Validate data schema
└─ Output: Course objects with metadata
        ↓
Cache Layer
├─ Save to JSON file
├─ Compute hash for validation
└─ Persist locally
        ↓
Embedding Generation
├─ Format course text
├─ Call OpenAI embedding API
├─ Generate vectors
└─ Output: Course embeddings
        ↓
Vector Store (Pinecone)
├─ Create index
├─ Upsert embeddings
├─ Index metadata
└─ Ready for retrieval
```

## Module Details

### Frontend (`/frontend/src`)

**Components**:
- `QueryInput.js` - Text input for natural language queries
- `ScheduleOutput.js` - Display recommended schedules

**Services**:
- `api.js` - HTTP client for backend communication

**Styles**:
- `App.css` - Main styling
- `QueryInput.css` - Input component styles
- `ScheduleOutput.css` - Output component styles

### Backend (`/backend/app`)

**Models** (`models/`):
- `course.py` - Course, CourseSection, MeetingTime, Schedule data models
- `constraint.py` - ScheduleConstraint model for parsed user preferences

**Scraper** (`scraper/`):
- `uw_scheduler_scraper.py` - Web scraper for UW Time Schedule
  - Fetches HTML from UW website
  - Parses course/section data
  - Caches with hash validation

**Embedding** (`embedding/`):
- `embedding_service.py` - OpenAI embedding generation
- `vector_store.py` - Pinecone vector store operations

**RAG** (`rag/`):
- `rag_pipeline.py` - Main RAG coordination
- `constraint_parser.py` - Natural language → constraints extraction
- `conflict_checker.py` - Schedule conflict detection

**Utils** (`utils/`):
- `prerequisites.py` - Prerequisite graph and eligibility checking
- `logging_config.py` - Application logging setup

**Core**:
- `config.py` - Environment configuration
- `main.py` - FastAPI application and endpoints

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/schedule` | Generate schedule recommendations |
| GET | `/api/courses` | Get available courses from cache |
| POST | `/api/scrape` | Trigger course data scraping |
| GET | `/health` | Health check |
| GET | `/docs` | Interactive API docs (Swagger) |
| GET | `/redoc` | Alternative API docs (ReDoc) |

## Data Models

### Course
```python
{
  "code": "CSS 342",
  "title": "Data Structures",
  "credits": 4,
  "prerequisites": ["CSS 143"],
  "sections": [CourseSection, ...]
}
```

### CourseSection
```python
{
  "section_number": "A",
  "instructor": "Dr. Smith",
  "meeting_times": [MeetingTime, ...],
  "enrolled": 25,
  "capacity": 30
}
```

### MeetingTime
```python
{
  "days": ["T", "Th"],
  "start_time": "14:00",
  "end_time": "15:20",
  "location": "UWB 105"
}
```

### ScheduleConstraint
```python
{
  "query": "User's natural language query",
  "max_credits": 14,
  "preferred_days": ["T", "Th"],
  "required_courses": ["CSS 342", "CSS 385"],
  "prerequisites_met": ["CSS 143", "CSS 161"]
}
```

## Error Handling

### Backend
- FastAPI HTTPException for all error responses
- Logging of errors with context
- Graceful fallback to cached data if scrape fails
- Validation of all inputs using Pydantic

### Frontend
- Catch API errors and display to user
- Show loading states during requests
- Display conflict warnings
- Clear error messages

## Performance Considerations

1. **Caching**: Course data cached locally to avoid repeated scrapes
2. **Vector Search**: Semantic search is fast (typically <100ms)
3. **LLM Calls**: ~2-5 seconds per request (main latency)
4. **Conflict Detection**: O(n²) but typically n < 20 courses

## Security Considerations

1. **API Keys**: Stored in .env, not in code
2. **CORS**: Currently allows all origins (restrict in production)
3. **Input Validation**: All inputs validated with Pydantic
4. **Error Messages**: Generic messages to prevent information leakage

## Future Enhancements

1. User authentication and schedule history
2. Real-time MyPlan integration
3. Multi-major planning support
4. Corequisite support
5. Waitlist recommendations
6. Schedule comparison tool
7. Export to calendar
8. Mobile app
