"""
Quiz Generator Module
Generates quiz questions using AI/LLM APIs.
"""

import os
import json
import re
import random
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

# Try to import AI libraries
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from modules.content_processor import ContentProcessor


@dataclass
class Question:
    """Represents a quiz question."""
    question_text: str
    options: List[str]
    correct_answer: str
    explanation: str
    difficulty: str = "medium"
    question_type: str = "mcq"
    category: str = ""
    score: int = 1


@dataclass
class Quiz:
    """Represents a complete quiz."""
    title: str
    questions: List[Question]
    created_at: datetime = field(default_factory=datetime.now)
    total_score: int = field(default=0)
    
    def __post_init__(self):
        self.total_score = sum(q.score for q in self.questions)


class QuizGenerator:
    """Generates quiz questions from study materials."""
    
    def __init__(self, api_key: str = None, api_type: str = "openai"):
        """
        Initialize the quiz generator.
        
        Args:
            api_key: API key for the AI service
            api_type: Type of API to use ("openai", "openrouter", or "gemini")
        """
        self.api_key = api_key or os.environ.get('AI_API_KEY')
        self.api_type = (api_type or "openai").lower()
        self.content_processor = ContentProcessor()
        # Default OpenAI-compatible model; overridden per provider below.
        self.openai_model = os.environ.get('AI_MODEL', 'gpt-3.5-turbo')
        
        if self.api_type == "openai" and OPENAI_AVAILABLE and self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        elif self.api_type == "openrouter" and OPENAI_AVAILABLE and self.api_key:
            # OpenRouter is OpenAI-API-compatible; just point base_url at it.
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url="https://openrouter.ai/api/v1",
            )
            # OpenRouter requires fully-qualified model names.
            self.openai_model = os.environ.get('AI_MODEL', 'openai/gpt-3.5-turbo')
        elif self.api_type == "gemini" and GEMINI_AVAILABLE and self.api_key:
            # Ensure we don't use OpenAI client for Gemini
            if hasattr(self, 'client'):
                delattr(self, 'client')
            self.client = genai.Client(api_key=self.api_key)
            self.model = 'gemini-1.5-flash'
    
    def generate_quiz_from_text(self, text: str, num_questions: int = 10,
                                difficulty: str = "medium") -> Quiz:
        """
        Generate a quiz from text content.
        
        Args:
            text: Study material text
            num_questions: Number of questions to generate
            difficulty: Difficulty level ("easy", "medium", "hard")
            
        Returns:
            Quiz object with generated questions
        """
        # Clean and chunk the text
        cleaned_text = self.content_processor.clean_text(text)
        chunks = self.content_processor.chunk_text(cleaned_text)

        # For small quizzes, select a random chunk from the middle sections
        # to avoid always using the first chunk / preface content.
        if len(chunks) > 1:
            chunk_count = len(chunks)
            if num_questions <= 10:
                if chunk_count > 2:
                    start_idx = max(1, chunk_count // 4)
                    end_idx = max(start_idx + 1, chunk_count - max(1, chunk_count // 4))
                    candidate_chunks = chunks[start_idx:end_idx]
                else:
                    candidate_chunks = chunks[1:]

                if candidate_chunks:
                    chunks = [random.choice(candidate_chunks)]
                else:
                    chunks = [chunks[-1]]
            else:
                # For larger quizzes, sample a few different chunks from the middle.
                if chunk_count > 3:
                    start_idx = max(1, chunk_count // 4)
                    end_idx = max(start_idx + 1, chunk_count - max(1, chunk_count // 4))
                    candidate_chunks = chunks[start_idx:end_idx]
                else:
                    candidate_chunks = chunks

                num_chunk_samples = min(len(candidate_chunks), 3)
                chunks = random.sample(candidate_chunks, num_chunk_samples)

        # Generate questions from chunks
        all_questions = []

        for chunk in chunks:
            try:
                questions = self._generate_questions_from_chunk(
                    chunk, num_questions // len(chunks) + 1, difficulty
                )
                all_questions.extend(questions)
            except Exception as e:
                print(f"Error generating questions from chunk: {e}")
                continue
        
        # Limit to requested number
        all_questions = all_questions[:num_questions]
        
        # Create quiz title
        title = self._generate_quiz_title(text)
        
        return Quiz(title=title, questions=all_questions)
    
    def _generate_questions_from_chunk(self, chunk: str, num_questions: int,
                                       difficulty: str) -> List[Question]:
        """Generate questions from a single text chunk."""
        prompt = self._build_generation_prompt(chunk, num_questions, difficulty)
        
        try:
            if self.api_type in ("openai", "openrouter") and OPENAI_AVAILABLE:
                response = self._call_openai(prompt)
            elif self.api_type == "gemini" and GEMINI_AVAILABLE:
                response = self._call_gemini(prompt)
            else:
                # Fallback to mock data if no API available
                return self._generate_mock_questions(num_questions, difficulty)
            
            return self._parse_questions(response)
            
        except Exception as e:
            print(f"Error calling AI API: {e}")
            return self._generate_mock_questions(num_questions, difficulty)
    
    def _build_generation_prompt(self, text: str, num_questions: int,
                                  difficulty: str) -> str:
        """Build the prompt for question generation."""
        difficulty_map = {
            "easy": "Beginner level - basic concepts and definitions",
            "medium": "Intermediate level - understanding and application",
            "hard": "Advanced level - analysis and critical thinking"
        }
        
        return f"""You are an expert educational content creator. Generate {num_questions} 
multiple-choice questions based on the following study material.

Study Material:
{text}

Instructions:
1. Generate {num_questions} multiple-choice questions
2. Each question should have 4 options (A, B, C, D)
3. The difficulty level should be: {difficulty_map.get(difficulty, "medium")}
4. Provide the correct answer and a clear explanation
5. Focus on testing understanding, not just memorization

Format your response as a JSON object with the following structure:
{{
    "questions": [
        {{
            "question": "Question text here?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": "A",
            "explanation": "Explanation of why this is correct.",
            "difficulty": "easy|medium|hard"
        }}
    ]
}}

JSON Response:"""
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI-compatible API (OpenAI or OpenRouter)."""
        try:
            extra_headers = {}
            if self.api_type == "openrouter":
                # Optional but recommended by OpenRouter for app attribution.
                extra_headers = {
                    "HTTP-Referer": os.environ.get(
                        "OPENROUTER_REFERRER", "http://localhost"
                    ),
                    "X-Title": os.environ.get(
                        "OPENROUTER_APP_TITLE", "Smart Study Buddy"
                    ),
                }

            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates quiz questions. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1200,
                extra_headers=extra_headers or None,
            )

            # Some OpenAI-compatible providers (incl. OpenRouter) may return
            # an error object, an empty choices list, or None content.
            if not getattr(response, "choices", None):
                err = getattr(response, "error", None) or response
                raise Exception(f"Empty response from API: {err}")

            content = response.choices[0].message.content
            if not content:
                finish_reason = getattr(response.choices[0], "finish_reason", "unknown")
                raise Exception(
                    f"Model returned empty content (finish_reason={finish_reason}). "
                    f"Try a different model via AI_MODEL in .env."
                )
            return content
        except Exception as e:
            raise Exception(f"OpenAI API error: {e}")
    
    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API."""
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt]
            )
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API error: {e}")
    
    def _parse_questions(self, response: str) -> List[Question]:
        """Parse AI response and extract questions."""
        questions = []

        if not response:
            return questions

        # Try to extract JSON from response
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                for q_data in data.get('questions', []):
                    question = Question(
                        question_text=q_data.get('question', ''),
                        options=q_data.get('options', []),
                        correct_answer=q_data.get('correct_answer', ''),
                        explanation=q_data.get('explanation', ''),
                        difficulty=q_data.get('difficulty', 'medium')
                    )
                    questions.append(question)
        except json.JSONDecodeError:
            # Fallback to parsing if JSON extraction fails
            questions = self._parse_questions_fallback(response)

        return questions
    
    def _parse_questions_fallback(self, response: str) -> List[Question]:
        """Fallback method to parse questions if JSON parsing fails."""
        questions = []
        
        # Simple fallback parsing
        question_blocks = response.split("Question:")[1:]
        
        for block in question_blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 4:
                question_text = lines[0].strip()
                options = []
                correct_answer = ""
                explanation = ""
                
                for line in lines[1:]:
                    line = line.strip()
                    if line.startswith(('A)', 'B)', 'C)', 'D)', 'A.', 'B.', 'C.', 'D.')):
                        options.append(line[2:].strip())
                    elif 'Correct' in line or 'Answer' in line:
                        correct_answer = line.split(':')[1].strip() if ':' in line else line
                    elif 'Explanation' in line:
                        explanation = line.split(':', 1)[1].strip() if ':' in line else line
                
                if options:
                    questions.append(Question(
                        question_text=question_text,
                        options=options,
                        correct_answer=correct_answer,
                        explanation=explanation,
                        difficulty="medium"
                    ))
        
        return questions
    
    def _generate_mock_questions(self, num_questions: int, difficulty: str) -> List[Question]:
        """Generate mock questions when API is unavailable."""
        questions = []
        
        for i in range(num_questions):
            question = Question(
                question_text=f"Mock Question {i+1}: What is the main concept discussed in this section?",
                options=[
                    "Option A: The importance of studying",
                    "Option B: Key concepts from the material",
                    "Option C: Advanced applications",
                    "Option D: Historical context"
                ],
                correct_answer="B",
                explanation="This is a mock explanation for demonstration purposes.",
                difficulty=difficulty
            )
            questions.append(question)
        
        return questions
    
    def _generate_quiz_title(self, text: str) -> str:
        """Generate a title for the quiz based on content."""
        # Extract key terms
        key_terms = self.content_processor.extract_key_terms(text, 3)
        
        if key_terms:
            return f"Quiz: {', '.join(key_terms)}"
        return f"Quiz: {datetime.now().strftime('%Y-%m-%d')}"


def generate_quiz(text: str, num_questions: int = 10, difficulty: str = "medium",
                  api_key: str = None, api_type: str = "openai") -> Quiz:
    """
    Convenience function to generate a quiz.
    
    Args:
        text: Study material text
        num_questions: Number of questions
        difficulty: Difficulty level
        api_key: API key for AI service
        api_type: Type of API to use
        
    Returns:
        Quiz object with generated questions
    """
    generator = QuizGenerator(api_key=api_key, api_type=api_type)
    return generator.generate_quiz_from_text(text, num_questions, difficulty)
