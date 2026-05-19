"""Service for generating embeddings of course data."""
from openai import OpenAI, OpenAIError
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generates embeddings for course data using OpenAI."""
    
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        """Initialize embedding service.
        
        Args:
            api_key: OpenAI API key
            model: Embedding model to use
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        logger.info(f"Initialized EmbeddingService with model: {model}")
    
    def embed_course_data(self, course_text: str) -> Optional[List[float]]:
        """Generate embedding for a course.
        
        Args:
            course_text: Formatted course information
            
        Returns:
            Embedding vector or None on error
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=course_text
            )
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding
        except OpenAIError as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def batch_embed_courses(self, course_texts: List[str], batch_size: int = 100) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple courses.
        
        Args:
            course_texts: List of formatted course information
            batch_size: Number of items to embed per request
            
        Returns:
            List of embedding vectors (None for failed items)
        """
        embeddings = []
        
        for i in range(0, len(course_texts), batch_size):
            batch = course_texts[i:i + batch_size]
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
                logger.info(f"Generated embeddings for batch {i//batch_size + 1}")
            except OpenAIError as e:
                logger.error(f"Failed to batch embed courses at index {i}: {e}")
                # Add None for failed items
                embeddings.extend([None] * len(batch))
        
        logger.info(f"Generated embeddings for {len(embeddings)} courses")
        return embeddings
    
    def format_course_for_embedding(self, course: dict) -> str:
        """Format course data for embedding.
        
        Args:
            course: Course dictionary
            
        Returns:
            Formatted string representation
        """
        sections_text = "\n".join([
            self._format_section(s) for s in course.get('sections', [])
        ])
        
        prereqs = ", ".join(course.get('prerequisites', [])) or "None"
        
        return f"""
Course: {course.get('code')} - {course.get('title')}
Department: {course.get('department')}
Credits: {course.get('credit_hours')}
Prerequisites: {prereqs}
Description: {course.get('title')} is a course in the {course.get('department')} department.
Available Sections:
{sections_text}
"""
    
    def _format_section(self, section: dict) -> str:
        """Format a single section for embedding."""
        meetings = section.get('meeting_times', [])
        
        if not meetings or not meetings[0].get('days'):
            time_str = "Online or TBA"
        else:
            meeting = meetings[0]
            days_str = " ".join(meeting.get('days', []))
            start = meeting.get('start_time', '00:00')
            end = meeting.get('end_time', '00:00')
            time_str = f"{days_str} {start}-{end}"
        
        instructor = section.get('instructor', 'TBA')
        section_id = section.get('section_number', 'A')
        
        return f"  Section {section_id}: {time_str}, Instructor: {instructor}"
