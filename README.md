# UW Bothell Course Scheduler

An AI-powered course scheduling assistant that helps UW Bothell students plan their academic schedules based on their constraints and preferences.

## Project Overview

This project addresses the tedious process of manually cross-referencing MyPlan, the Time Schedule, and degree requirements. Students describe their scheduling needs in plain English, and our RAG-powered system recommends personalized course sections that fit their constraints.

### Key Features

- **Natural Language Interface**: Describe scheduling needs in plain English
- **Section-Level Awareness**: Recommendations include specific course sections with meeting times
- **Constraint Support**: Day/time preferences, credit load limits, prerequisite checking, conflict detection
- **CSS Core Requirements**: Focused on CSS major requirements for MVP
- **Schedule Conflict Detection**: Ensures no overlapping meeting times

## Project Structure

```
planner/
├── backend/                 # Python FastAPI backend
│   ├── app/
│   │   ├── models/         # Data models (Course, Section, Schedule)
│   │   ├── scraper/        # Web scraping module
│   │   ├── embedding/      # Embedding and vector store services
│   │   ├── rag/            # RAG pipeline, constraint parsing, conflict detection
│   │   └── utils/          # Utilities (prerequisites graph, logging)
│   ├── main.py             # FastAPI application entry point
│   ├── requirements.txt    # Python dependencies
│   └── .env.example        # Environment configuration template
│
├── frontend/               # React single-page app
│   ├── src/
│   │   ├── components/     # React components (QueryInput, ScheduleOutput)
│   │   ├── services/       # API client service
│   │   ├── styles/         # CSS styling
│   │   └── App.js          # Main app component
│   ├── package.json        # Node.js dependencies
│   └── .env.example        # Frontend environment template
│
├── data/
│   ├── scripts/            # Data processing scripts
│   └── cache/              # Cached course data
│
└── docs/                   # Documentation
```

## Technology Stack

### Backend
- **Framework**: FastAPI (Python web framework)
- **LLM**: OpenAI API (GPT-4)
- **Vector Store**: Pinecone (embeddings storage)
- **Embeddings**: OpenAI text-embedding-3-small
- **Web Scraping**: BeautifulSoup, requests, lxml
- **Database**: In-memory cache (MVP)

### Frontend
- **Framework**: React 18
- **HTTP Client**: Axios
- **Styling**: CSS3
- **Build Tool**: react-scripts (Create React App)

## Getting Started

### Backend Setup

1. **Install Python dependencies**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys:
   # - OPENAI_API_KEY: Your OpenAI API key
   # - PINECONE_API_KEY: Your Pinecone API key
   # - PINECONE_ENVIRONMENT: Your Pinecone environment
   ```

3. **Run the backend**:
   ```bash
   python main.py
   # Server runs on http://localhost:8000
   ```

4. **API Documentation**:
   - Visit http://localhost:8000/docs for interactive API documentation
   - Visit http://localhost:8000/redoc for ReDoc documentation

### Frontend Setup

1. **Install Node dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env if needed (defaults to localhost:8000)
   ```

3. **Run the frontend**:
   ```bash
   npm start
   # App runs on http://localhost:3000
   ```

## API Endpoints

### `POST /api/schedule`
Generate schedule recommendations based on user query.

**Request**:
```json
{
  "query": "I want to finish my CSS core requirements, only come to campus Tuesday and Thursday, and keep my total credit load under 14.",
  "completed_courses": ["CSS 143", "CSS 161"]
}
```

**Response**:
```json
{
  "query": "...",
  "recommendations": "Based on your constraints...",
  "conflicts": [],
  "is_valid": true
}
```

### `GET /api/courses`
Get available courses from cache.

### `POST /api/scrape`
Trigger course data scraping from UW Time Schedule.

### `GET /health`
Health check endpoint.

## Module Responsibilities

### Richie Chen - Backend / Data Pipeline
- Python scraper for UW Bothell Time Schedule
- Embedding pipeline and vector store setup
- Data validation and caching

### Kevin Vo - LLM / RAG Integration
- RAG pipeline implementation
- LLM prompt engineering
- Conflict detection logic

### Yousuf Al-Bassyiouni - Frontend / UX
- Web app interface design
- Query input component
- Schedule display and visualization

## Development Workflow

1. **Backend Development**:
   ```bash
   cd backend
   # Activate virtual environment
   source venv/bin/activate
   # Run in development mode with auto-reload
   python main.py
   ```

2. **Frontend Development**:
   ```bash
   cd frontend
   npm start
   # Frontend with hot reload
   ```

3. **Testing**:
   ```bash
   # Backend tests
   cd backend
   pytest

   # Frontend tests
   cd frontend
   npm test
   ```

## MVP Scope

✓ CSS major core requirements only  
✓ Spring 2026 Time Schedule data  
✓ Day/time and credit-load constraints  
✓ Basic prerequisite enforcement  
✓ Schedule conflict detection  
✓ Web interface with query input and schedule output

### Out of Scope for MVP
- Multi-major planning
- Real-time MyPlan integration
- User account persistence
- Online class handling

## Evaluation Criteria

| Test Case | Success Criterion | Method |
|-----------|-------------------|--------|
| 10 student constraint queries | Zero schedule conflicts in output | Manual verification |
| Prerequisite enforcement | No ineligible courses recommended | Graph comparison |
| Scraper uptime | Successful data pull across 3 test runs | Automated re-run |
| Natural language parsing | ≥80% correct constraint extraction | Structured output comparison |

## Environment Variables

### Backend (.env)
```
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4
PINECONE_API_KEY=your_key_here
PINECONE_ENVIRONMENT=your_env
PINECONE_INDEX_NAME=uwbothell-courses
ENVIRONMENT=development
DEBUG=True
API_HOST=localhost
API_PORT=8000
UW_TIME_SCHEDULE_URL=https://www.bothell.uw.edu/time-schedule/
CACHE_DIR=../data/cache
```

### Frontend (.env)
```
REACT_APP_API_URL=http://localhost:8000
REACT_APP_API_TIMEOUT=30000
```

## Next Steps

1. **Implement web scraper** - Parse UW Bothell Time Schedule HTML
2. **Set up vector store** - Initialize Pinecone index
3. **Embed course data** - Generate and store embeddings
4. **Implement RAG pipeline** - Retrieve courses and prompt LLM
5. **Build schedule calendar** - Add weekly calendar visualization
6. **User testing** - Validate with students and refine recommendations

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Pinecone Documentation](https://docs.pinecone.io/)
- [RAG Best Practices](https://www.pinecone.io/learn/retrieval-augmented-generation/)

## License

This project is part of CSS 382 Capstone at UW Bothell.
# SmartScheduler
