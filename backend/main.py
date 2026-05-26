"""Main FastAPI application."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import logging
import json

from app.config import settings
from app.utils import setup_logging, PrerequisiteGraph
from app.rag import ConstraintParser, RAGPipeline, ConflictChecker, ScheduleBuilder
from app.embedding import EmbeddingService, VectorStore
from app.scraper import UWScheduleScraper

# Setup logging
setup_logging(debug=settings.debug)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI-powered course scheduling assistant for UW Bothell students"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
embedding_service = None
vector_store = None
rag_pipeline = None
scraper = None
preprocessed_courses = None  # Cache for courses
prereq_graph = None  # Prerequisite graph for inference



@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global embedding_service, vector_store, rag_pipeline, scraper, preprocessed_courses, prereq_graph
    
    try:
        logger.info("=" * 60)
        logger.info("Initializing UW Bothell Course Scheduler Backend")
        logger.info("=" * 60)
        
        # Initialize scraper
        scraper = UWScheduleScraper(cache_dir=settings.cache_dir)
        logger.info("✓ Scraper initialized")
        
        # Load courses
        preprocessed_courses = scraper.scrape_courses()
        logger.info(f"✓ Loaded {len(preprocessed_courses)} courses")

        # Build prerequisite graph from the scraper's full prerequisite database
        prereq_graph = PrerequisiteGraph()
        for num in range(100, 500):
            for prefix in ("CSS", "CSE"):
                code = f"{prefix} {num}"
                prereqs = scraper._get_prerequisites(code)
                if prereqs:
                    prereq_graph.add_course(code, prereqs)
        # Also add any loaded courses not yet in the graph
        for course in preprocessed_courses:
            if course['code'] not in prereq_graph.graph:
                prereq_graph.add_course(course['code'], course.get('prerequisites', []))
        logger.info(f"✓ Prerequisite graph built ({len(prereq_graph.graph)} courses)")

        # Initialize embedding service
        if settings.openai_api_key:
            embedding_service = EmbeddingService(
                api_key=settings.openai_api_key,
                model="text-embedding-3-small"
            )
            logger.info("✓ Embedding service initialized")
        else:
            logger.warning("⚠ OpenAI API key not configured")
        
        # Initialize vector store
        vector_store = VectorStore(
            api_key=settings.pinecone_api_key if settings.pinecone_api_key else None,
            environment=settings.pinecone_environment if settings.pinecone_environment else None,
            index_name=settings.pinecone_index_name
        )
        logger.info("✓ Vector store initialized")
        
        # Prepare embeddings (if embedding service is available)
        if embedding_service and preprocessed_courses:
            logger.info("Generating course embeddings...")
            course_texts = [
                embedding_service.format_course_for_embedding(course)
                for course in preprocessed_courses
            ]
            embeddings = embedding_service.batch_embed_courses(course_texts)
            
            # Prepare vectors for upsert
            vectors = []
            for i, (course, embedding) in enumerate(zip(preprocessed_courses, embeddings)):
                if embedding:
                    vector_id = f"{course['code'].replace(' ', '_')}_{i}"
                    metadata = {
                        'course_code': course['code'],
                        'course_title': course['title'],
                        'credits': course['credit_hours'],
                        'department': course['department'],
                    }
                    vectors.append((vector_id, embedding, metadata))
            
            if vectors:
                vector_store.upsert_embeddings(vectors)
                logger.info(f"✓ Uploaded {len(vectors)} course embeddings")
        
        # Initialize RAG pipeline
        if settings.openai_api_key:
            rag_pipeline = RAGPipeline(
                openai_api_key=settings.openai_api_key,
                openai_model=settings.openai_model
            )
            logger.info("✓ RAG pipeline initialized")
        else:
            logger.warning("⚠ OpenAI API key required for RAG pipeline")
        
        logger.info("=" * 60)
        logger.info("Backend initialization complete!")
        logger.info("=" * 60)
    
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise


class ScheduleRequest(BaseModel):
    """Schedule request from frontend."""
    query: str
    completed_courses: Optional[List[str]] = None


class ScheduleResponse(BaseModel):
    """Schedule response to frontend."""
    query: str
    recommendations: str
    constraints: dict
    recommended_courses: List[dict]
    is_valid: bool
    issues: List[str]


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "courses_loaded": len(preprocessed_courses) if preprocessed_courses else 0,
        "rag_ready": rag_pipeline is not None,
        "embeddings_ready": embedding_service is not None
    }


@app.post("/api/schedule", response_model=ScheduleResponse)
async def get_schedule(request: ScheduleRequest):
    """Get schedule recommendations based on natural language query.
    
    Args:
        request: Schedule request with query and completed courses
        
    Returns:
        Schedule recommendations with validation
    """
    try:
        if not preprocessed_courses:
            raise HTTPException(
                status_code=500,
                detail="No courses loaded. Please ensure course data is available."
            )

        # 1. Parse constraints from query
        constraints = ConstraintParser.parse_query(request.query)
        logger.info(f"Constraint parsing result: {json.dumps(constraints, indent=2, default=str)}")

        # 2. Retrieve courses using vector store (semantic search) when available,
        #    otherwise fall back to simple constraint-based filtering.
        retrieved_courses = _retrieve_courses(
            request.query, constraints, preprocessed_courses,
            embedding_service, vector_store
        )
        logger.info(f"Retrieved {len(retrieved_courses)} courses matching constraints")

        # 3. Expand completed courses by inferring transitive prerequisites.
        #    e.g. completing CSS 342 implies CSS 211, CSS 161, CSS 143 are done.
        completed = request.completed_courses or []
        if prereq_graph and completed:
            completed = prereq_graph.infer_completed(completed)
            logger.info(f"Expanded completed courses: {completed}")

        # 4. Drop courses the student already completed before building
        completed_set = set(c.upper().replace(' ', '') for c in completed)
        eligible_courses = [
            c for c in retrieved_courses
            if c['code'].replace(' ', '').upper() not in completed_set
        ]
        logger.info(f"{len(eligible_courses)} courses eligible after completion filter")

        # 5. Build schedule — deterministic builder is primary, RAG is optional.
        hydrated_courses, message = ScheduleBuilder.build(
            constraints=constraints,
            courses=eligible_courses,
            completed_courses=completed,
        )

        # Optional RAG pass: only runs if an OpenAI key was configured at
        # startup. It currently overrides the deterministic recommendation
        # message only — the builder remains the source of truth for sections.
        if rag_pipeline:
            try:
                rec = rag_pipeline.recommend_schedule(
                    constraints=constraints,
                    retrieved_courses=eligible_courses,
                    completed_courses=completed,
                )
                if rec.get("recommendation"):
                    message = rec["recommendation"]
            except Exception as e:  # pragma: no cover — best-effort augmentation
                logger.warning(f"RAG augmentation failed, sticking with deterministic build: {e}")

        # Validate schedule constraints (informational — builder already
        # enforces them, but we surface any residual issues to the UI).
        recommended_sections = _parse_sections_from_hydrated(hydrated_courses)
        is_valid, issues = ConflictChecker.validate_schedule_constraints(
            recommended_sections,
            constraints,
            completed,
        )
        logger.info(f"Schedule validation: valid={is_valid}, issues={len(issues)}")

        return ScheduleResponse(
            query=request.query,
            recommendations=message,
            constraints=constraints,
            recommended_courses=hydrated_courses,
            is_valid=is_valid,
            issues=issues,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating schedule: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate schedule: {str(e)}"
        )


@app.get("/api/courses")
async def get_courses():
    """Get available courses.
    
    Returns:
        List of all available courses
    """
    try:
        if not preprocessed_courses:
            return {"courses": [], "count": 0, "status": "loading"}
        
        return {
            "courses": preprocessed_courses,
            "count": len(preprocessed_courses),
            "status": "ready"
        }
    
    except Exception as e:
        logger.error(f"Error retrieving courses: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve courses: {str(e)}"
        )


@app.get("/api/courses/{course_code}")
async def get_course(course_code: str):
    """Get details for a specific course.
    
    Args:
        course_code: Course code like "CSS 342"
        
    Returns:
        Course details with sections
    """
    try:
        if not preprocessed_courses:
            raise HTTPException(status_code=404, detail="No courses available")
        
        for course in preprocessed_courses:
            if course['code'].upper() == course_code.upper():
                return course
        
        raise HTTPException(status_code=404, detail=f"Course {course_code} not found")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving course {course_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scrape")
async def trigger_scrape():
    """Trigger course data scraping and update cache.
    
    Returns:
        Scrape result
    """
    try:
        if not scraper:
            raise HTTPException(
                status_code=500,
                detail="Scraper not initialized"
            )
        
        logger.info("Initiating course data scrape...")
        courses = scraper.scrape_courses(settings.uw_time_schedule_url)
        scraper.cache_courses(courses)
        
        logger.info(f"Successfully scraped {len(courses)} courses")
        return {
            "status": "success",
            "courses_scraped": len(courses),
            "message": "Course data updated successfully"
        }
    
    except Exception as e:
        logger.error(f"Error during scrape: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scrape courses: {str(e)}"
        )


@app.get("/api/vector-store/stats")
async def get_vector_store_stats():
    """Get vector store statistics.
    
    Returns:
        Vector store stats
    """
    try:
        if not vector_store:
            raise HTTPException(status_code=500, detail="Vector store not initialized")
        
        stats = vector_store.get_stats()
        return stats
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting vector store stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions

def _retrieve_courses(
    query: str,
    constraints: dict,
    all_courses: List[dict],
    emb_service,
    vec_store,
) -> List[dict]:
    """Retrieve relevant courses using vector search + constraint filtering.

    If the embedding service and vector store are available, the user query is
    embedded and a semantic search is performed.  The results are then merged
    with any explicitly-required courses from constraint parsing so nothing
    the student asked for by name is dropped.

    Falls back to simple constraint filtering when embeddings aren't set up.
    """
    # --- semantic retrieval path ---
    if emb_service and vec_store:
        try:
            # Only attempt if the vector store actually has vectors
            stats = vec_store.get_stats()
            if stats.get('vector_count', 0) > 0:
                query_embedding = emb_service.embed_course_data(query)
                if query_embedding:
                    results = vec_store.query(query_embedding, top_k=10)
                    # Map vector-store hits back to full course objects
                    hit_codes = set()
                    for r in results:
                        code = r.get('course_code') or r.get('metadata', {}).get('course_code')
                        if code:
                            hit_codes.add(code.replace(' ', '').upper())

                    retrieved = []
                    for course in all_courses:
                        if course['code'].replace(' ', '').upper() in hit_codes:
                            retrieved.append(course)

                    # Merge in any explicitly-required courses the student named
                    required = set(
                        c.upper().replace(' ', '')
                        for c in (constraints.get('required_courses') or [])
                    )
                    already = set(c['code'].replace(' ', '').upper() for c in retrieved)
                    for course in all_courses:
                        if course['code'].replace(' ', '').upper() in required and \
                           course['code'].replace(' ', '').upper() not in already:
                            retrieved.append(course)

                    if retrieved:
                        logger.info(f"Vector search returned {len(retrieved)} courses")
                        return retrieved
        except Exception as e:
            logger.warning(f"Vector retrieval failed, falling back to filter: {e}")

    # --- fallback: simple constraint filter ---
    return _filter_courses_by_constraints(all_courses, constraints)


def _filter_courses_by_constraints(courses: List[dict], constraints: dict) -> List[dict]:
    """Filter courses based on constraints.
    
    Args:
        courses: List of all courses
        constraints: Parsed constraints
        
    Returns:
        Filtered list of relevant courses
    """
    filtered = []
    max_results = 30
    
    required_codes = set(c.upper().replace(' ', '') for c in (constraints.get('required_courses') or []))
    
    for course in courses:
        # Prioritize required courses
        if required_codes:
            course_code_clean = course['code'].replace(' ', '').upper()
            if course_code_clean in required_codes:
                filtered.append(course)
                continue
        
        # Include courses that match department (CSS)
        if course.get('department') == 'CSS':
            # Check credit filter
            max_credits = constraints.get('max_credits')
            if max_credits and course.get('credit_hours', 0) > max_credits:
                continue
            
            filtered.append(course)
        
        if len(filtered) >= max_results:
            break
    
    return filtered[:max_results]


def _hydrate_courses(course_codes: List[str], available_courses: List[dict],
                     constraints: Optional[dict] = None) -> List[dict]:
    """Map course code strings to full course objects for the frontend.

    Filters out sections that violate avoid_days constraints so the frontend
    only shows sections the student can actually take.
    """
    code_set = set(c.upper().replace(' ', '') for c in course_codes)
    avoid_days = set(constraints.get('avoid_days') or []) if constraints else set()
    hydrated = []

    for course in available_courses:
        course_clean = course['code'].replace(' ', '').upper()
        if course_clean in code_set:
            sections = []
            for s in course.get('sections', []):
                # Filter out sections that meet on avoided days
                if avoid_days:
                    meetings = s.get('meeting_times', [])
                    has_avoided_day = any(
                        day in avoid_days
                        for mt in meetings
                        for day in (mt.get('days') or [])
                    )
                    if has_avoided_day:
                        continue

                section = dict(s)
                if not section.get('location'):
                    meetings = section.get('meeting_times', [])
                    section['location'] = meetings[0].get('location', 'TBA') if meetings else 'TBA'
                sections.append(section)

            # Only include the course if it has at least one valid section
            if sections:
                hydrated.append({
                    'code': course['code'],
                    'title': course.get('title', ''),
                    'credits': course.get('credit_hours', course.get('credits', 0)),
                    'prerequisites': course.get('prerequisites', []),
                    'department': course.get('department', ''),
                    'sections': sections,
                })

    return hydrated


def _parse_sections_from_recommendation(recommended_courses: List[str],
                                       retrieved_courses: List[dict]) -> List[dict]:
    """Extract sections from recommended courses.
    
    Args:
        recommended_courses: List of course codes from recommendation
        retrieved_courses: Available courses with sections
        
    Returns:
        List of section dictionaries
    """
    sections = []
    recommended_set = set(c.upper().replace(' ', '') for c in recommended_courses)
    
    for course in retrieved_courses:
        course_code_clean = course['code'].replace(' ', '').upper()
        if course_code_clean in recommended_set:
            # Take first section of each recommended course
            if course.get('sections'):
                section = course['sections'][0].copy()
                section['course_code'] = course['code']
                section['prerequisites'] = course.get('prerequisites', [])
                section['credits'] = course.get('credit_hours', 0)
                sections.append(section)
    
    return sections


def _parse_sections_from_hydrated(hydrated_courses: List[dict]) -> List[dict]:
    """Extract first section from each hydrated course for validation."""
    sections = []
    for course in hydrated_courses:
        if course.get('sections'):
            section = course['sections'][0].copy()
            section['course_code'] = course['code']
            section['prerequisites'] = course.get('prerequisites', [])
            section['credits'] = course.get('credits', 0)
            sections.append(section)
    return sections


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
