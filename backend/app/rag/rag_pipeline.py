"""RAG pipeline for schedule recommendation."""
from openai import OpenAI, OpenAIError
from typing import List, Dict, Optional, Tuple
import logging
import json

logger = logging.getLogger(__name__)


class RAGPipeline:
    """RAG pipeline for retrieving courses and generating recommendations."""
    
    def __init__(self, openai_api_key: str, openai_model: str = "gpt-4"):
        """Initialize RAG pipeline.
        
        Args:
            openai_api_key: OpenAI API key
            openai_model: Model to use for LLM
        """
        self.client = OpenAI(api_key=openai_api_key)
        self.model = openai_model
        logger.info(f"Initialized RAG pipeline with model: {openai_model}")
    
    def recommend_schedule(
        self,
        constraints: Dict,
        retrieved_courses: List[Dict],
        completed_courses: Optional[List[str]] = None
    ) -> Dict:
        """Generate schedule recommendations using RAG.
        
        Args:
            constraints: Parsed constraints from user query
            retrieved_courses: Top relevant courses from vector store
            completed_courses: Courses student has already completed
            
        Returns:
            Recommended schedule
        """
        completed_courses = completed_courses or []
        
        # Format context from retrieved courses
        context = self._format_context(retrieved_courses)
        
        # Build prompt with constraints and context
        prompt = self._build_prompt(constraints, context, completed_courses)
        
        # Call LLM
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"}, # Enforce JSON output for models that support it
                temperature=0.7,
                max_tokens=2000
            )
            
            recommendation_text = response.choices[0].message.content
            logger.debug(f"Raw LLM response: {recommendation_text}")
            logger.info("Generated schedule recommendation")
            
            # Parse the recommendation to extract structured data
            return self._parse_recommendation(
                recommendation_text,
                retrieved_courses,
                constraints
            )
            
        except OpenAIError as e:
            logger.error(f"Failed to generate recommendation: {e}")
            return {
                "status": "error",
                "error": str(e),
                "recommendation": "Failed to generate schedule. Please try again."
            }
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for LLM."""
        return """You are an expert UW Bothell course scheduling assistant. Your task is to create a conflict-free weekly schedule based on the user's request and the available courses.

Your final output MUST be a single JSON object with two keys:
1. "recommendation": A markdown-formatted string containing your step-by-step reasoning and the final recommended schedule. In your reasoning, explain why each course was chosen and how it fits the constraints.
2. "recommended_courses": A JSON list of strings, where each string is the course code of a recommended course (e.g., ["CSS 342", "CSS 385"]).

Follow these rules:
- Analyze the user's constraints and completed courses.
- Select a set of course sections from the available list that meets all constraints (credit limits, day preferences, prerequisites, no time conflicts).
- Do not recommend courses if the student has not met the prerequisites.
- Ensure there are no time conflicts between any of the recommended sections.
- If you cannot create a valid schedule, explain why in the "recommendation" field and leave "recommended_courses" as an empty list.
"""
    
    def _format_context(self, courses: List[Dict]) -> str:
        """Format retrieved courses as context.
        
        Args:
            courses: Retrieved course data
            
        Returns:
            Formatted context string
        """
        if not courses:
            return "No courses available matching the search criteria."
        
        context_parts = []
        for course in courses:
            context_parts.append(self._format_course(course))
        
        return "\n".join(context_parts)
    
    def _format_course(self, course: dict) -> str:
        """Format a single course with its sections."""
        code = course.get('code', 'UNKNOWN')
        title = course.get('title', '')
        credits = course.get('credit_hours', 0)
        prerequisites = course.get('prerequisites', [])
        prereq_str = ", ".join(prerequisites) if prerequisites else "None"
        
        sections_text = "\n".join([
            self._format_section(code, s) for s in course.get('sections', [])
        ])
        
        return f"""
{code}: {title}
Credits: {credits} | Prerequisites: {prereq_str}
Sections:
{sections_text}"""
    
    def _format_section(self, course_code: str, section: Dict) -> str:
        """Format a single section."""
        section_num = section.get('section_number', 'A')
        instructor = section.get('instructor', 'TBA')
        meetings = section.get('meeting_times', [])
        
        if not meetings or not meetings[0].get('days'):
            time_str = "Online or TBA"
        else:
            meeting = meetings[0]
            days = " ".join(meeting.get('days', []))
            start = meeting.get('start_time', '00:00')
            end = meeting.get('end_time', '00:00')
            time_str = f"{days} {start}-{end}"
        
        return f"  Section {section_num}: {time_str}, Instructor: {instructor}"
    
    def _build_prompt(self, constraints: Dict, context: str, 
                     completed_courses: List[str]) -> str:
        """Build prompt for LLM.
        
        Args:
            constraints: Parsed constraints
            context: Retrieved course context
            completed_courses: Courses student has completed
            
        Returns:
            Prompt string
        """
        completed_str = ", ".join(completed_courses) if completed_courses else "None"
        
        return f"""Based on the student's constraints, completed courses, and available courses, recommend the best schedule:

STUDENT INFORMATION:
Completed Courses: {completed_str}

STUDENT CONSTRAINTS:
{self._format_constraints(constraints)}

AVAILABLE COURSES AND SECTIONS:
{context}

REQUIREMENTS:
1. Recommend specific course sections (not just courses)
2. Ensure no scheduling conflicts between sections
3. Verify student meets prerequisites for each course
4. Respect all stated constraints
5. Explain your reasoning for each recommendation

Please provide clear, actionable schedule recommendations."""
    
    def _format_constraints(self, constraints: Dict) -> str:
        """Format constraints for display."""
        parts = []
        
        if constraints.get('max_credits'):
            parts.append(f"• Maximum credits: {constraints['max_credits']}")
        if constraints.get('min_credits'):
            parts.append(f"• Minimum credits: {constraints['min_credits']}")
        if constraints.get('preferred_days'):
            days = ", ".join(constraints['preferred_days'])
            parts.append(f"• Preferred days: {days}")
        if constraints.get('avoid_days'):
            days = ", ".join(constraints['avoid_days'])
            parts.append(f"• Avoid days: {days}")
        if constraints.get('required_courses'):
            courses = ", ".join(constraints['required_courses'])
            parts.append(f"• Must include: {courses}")
        if constraints.get('no_online'):
            parts.append(f"• No online courses")
        
        return "\n".join(parts) if parts else "• No specific constraints"
    
    def _parse_recommendation(self, recommendation: str, 
                             retrieved_courses: List[Dict],
                             constraints: Dict) -> Dict:
        """Parse LLM recommendation output.
        
        Args:
            recommendation: Raw LLM output
            retrieved_courses: Original retrieved courses
            constraints: Original constraints
            
        Returns:
            Structured recommendation
        """
        try:
            # The LLM is now expected to return a JSON string
            parsed_json = json.loads(recommendation)
            
            return {
                "status": "success",
                "recommendation": parsed_json.get("recommendation", "No recommendation text provided."),
                "recommended_courses": parsed_json.get("recommended_courses", []),
                "constraints": constraints,
                "timestamp": self._get_timestamp()
            }
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse JSON from LLM response: {e}. Falling back to text extraction.")
            # Fallback to old parsing method if JSON fails
            return {
                "status": "success_fallback",
                "recommendation": recommendation,
                "recommended_courses": self._extract_course_mentions(recommendation),
                "constraints": constraints,
                "timestamp": self._get_timestamp()
            }
    
    def _extract_course_mentions(self, text: str) -> List[str]:
        """Extract course codes mentioned in recommendation.
        
        Args:
            text: Recommendation text
            
        Returns:
            List of course codes
        """
        import re
        # Match patterns like "CSS 342" or "CSS342"
        pattern = r'([A-Z]{2,3})\s*(\d{3})'
        matches = re.findall(pattern, text)
        courses = [f"{code} {num}" for code, num in matches]
        # Remove duplicates while preserving order
        seen = set()
        result = []
        for course in courses:
            if course not in seen:
                result.append(course)
                seen.add(course)
        return result
    
    def _get_timestamp(self) -> str:
        """Get current ISO timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()
