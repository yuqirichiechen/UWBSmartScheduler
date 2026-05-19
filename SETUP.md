# Development Setup Guide

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm or yarn
- Git
- API keys for OpenAI and Pinecone

## Initial Setup

### 1. Clone the Repository and Install Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Backend Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

**Required API Keys**:
- `OPENAI_API_KEY`: Get from [platform.openai.com](https://platform.openai.com/account/api-keys)
- `PINECONE_API_KEY`: Get from [app.pinecone.io](https://app.pinecone.io)

### 3. Install Frontend Dependencies

```bash
cd ../frontend

# Install Node dependencies
npm install

# Copy example env file
cp .env.example .env
```

## Running the Application

### Start Backend Server

```bash
cd backend

# Activate virtual environment (if not already activated)
source venv/bin/activate

# Run the server
python main.py
```

The backend will be available at `http://localhost:8000`

### Start Frontend Development Server

In a new terminal:

```bash
cd frontend

# Start React development server
npm start
```

The frontend will open at `http://localhost:3000`

## Project Structure Overview

```
planner/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py              # Configuration management
│   │   ├── models/                # Data models
│   │   ├── scraper/               # Web scraper module
│   │   ├── embedding/             # Vector embedding services
│   │   ├── rag/                   # RAG pipeline
│   │   └── utils/                 # Utility functions
│   ├── main.py                    # FastAPI entry point
│   ├── requirements.txt           # Python dependencies
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/            # React components
│   │   ├── services/              # API client
│   │   ├── styles/                # CSS styles
│   │   ├── App.js
│   │   └── index.js
│   ├── package.json
│   └── .env.example
│
├── data/
│   ├── scripts/                   # Data processing scripts
│   └── cache/                     # Cached course data
│
└── docs/                          # Documentation
```

## Common Commands

### Backend

```bash
# Run tests
pytest

# Run specific test file
pytest tests/test_constraint_parser.py

# Run with coverage
pytest --cov=app

# Format code
black app/

# Type checking
mypy app/

# Run linter
pylint app/
```

### Frontend

```bash
# Run tests
npm test

# Build for production
npm build

# Run linter
npm run lint

# Format code
npm run format
```

## Troubleshooting

### Backend Issues

**Import errors**: Make sure virtual environment is activated
```bash
source venv/bin/activate
```

**API key issues**: Verify .env file has correct keys
```bash
cat .env  # Check if keys are present
```

**Port already in use**: Change API_PORT in .env or use different port
```bash
python main.py --port 8001
```

### Frontend Issues

**Port 3000 already in use**: Kill process or use different port
```bash
# macOS/Linux:
lsof -ti:3000 | xargs kill -9
# Or set different port:
PORT=3001 npm start
```

**Module not found**: Install dependencies again
```bash
rm -rf node_modules
npm install
```

## API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Team Development Workflow

### Backend Team (Richie)
1. Work in `backend/app/` directories
2. Test changes with pytest
3. Commit with descriptive messages
4. Ensure main.py still runs without errors

### Frontend Team (Yousuf)
1. Work in `frontend/src/` directories
2. Test changes with npm test
3. Ensure components render properly
4. Update styles incrementally

### Integration (Kevin)
1. Implement RAG pipeline in `app/rag/`
2. Ensure backend API contracts match frontend expectations
3. Test end-to-end flows

## Next Development Steps

1. **Implement course scraper** - Start in `app/scraper/uw_scheduler_scraper.py`
2. **Test constraint parser** - Write tests in `tests/test_rag/`
3. **Set up Pinecone** - Configure vector store connection
4. **Build embedding pipeline** - Process course data
5. **Integrate RAG** - Connect retrieval to LLM
6. **Frontend Polish** - Enhance UI/UX

## Resources

- [FastAPI Guide](https://fastapi.tiangolo.com/deployment/concepts/)
- [React Hooks](https://react.dev/reference/react)
- [Testing with pytest](https://docs.pytest.org/)
- [Testing with React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
