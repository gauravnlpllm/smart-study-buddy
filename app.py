"""
Main Application Controller
Smart Study Buddy - AI Tutor Application
"""

import os
import sys
import json
import streamlit as st
import re
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.content_processor import ContentProcessor, process_file
from modules.quiz_generator import QuizGenerator, generate_quiz, Question
from modules.explanation import ExplanationGenerator
from modules.progress_tracker import ProgressTracker, track_quiz_completion
from modules.adaptive import AdaptiveLearning
from database.db import init_database, get_user_stats, get_weak_areas


class SmartStudyBuddy:
    """Main application controller for Smart Study Buddy."""
    
    def __init__(self):
        """Initialize the application."""
        # Initialize database
        init_database()
        
        # Initialize user session first (needed by _initialize_generators)
        self.current_user_id = 1  # Default user
        self.current_material = None
        self.current_quiz = None
        
        # Initialize components
        self.content_processor = ContentProcessor()
        self.quiz_generator = None
        self.explanation_generator = None
        self.tracker = None
        self.adaptive = None
        
        # Load API key from environment
        self.api_key = os.environ.get('AI_API_KEY')
        self.api_type = os.environ.get('AI_API_TYPE', 'openai').lower()
        
        # Initialize generators if API key is available
        if self.api_key:
            self._initialize_generators()
    
    def _initialize_generators(self):
        """Initialize AI generators with API key."""
        self.quiz_generator = QuizGenerator(
            api_key=self.api_key,
            api_type=self.api_type
        )
        self.explanation_generator = ExplanationGenerator(
            api_key=self.api_key,
            api_type=self.api_type
        )
        self.tracker = ProgressTracker(user_id=self.current_user_id)
        self.adaptive = AdaptiveLearning(user_id=self.current_user_id)
    
    def load_material(self, file_path: str = None, text: str = None) -> bool:
        """
        Load study material from file or text.
        
        Args:
            file_path: Path to file (PDF or text)
            text: Direct text input
            
        Returns:
            True if material loaded successfully
        """
        try:
            if file_path:
                document = process_file(file_path)
                self.current_material = document.content
            elif text:
                self.current_material = text
            else:
                return False
            
            return True
        except Exception as e:
            print(f"Error loading material: {e}")
            return False
    
    def generate_quiz(self, num_questions: int = 10, 
                      difficulty: str = "medium") -> Optional[List[Question]]:
        """
        Generate quiz questions from loaded material.
        
        Args:
            num_questions: Number of questions to generate
            difficulty: Difficulty level
            
        Returns:
            List of generated questions or None
        """
        if not self.current_material:
            print("No material loaded!")
            return None
        
        if not self.quiz_generator:
            print("API not configured!")
            return None
        
        try:
            quiz = self.quiz_generator.generate_quiz_from_text(
                text=self.current_material,
                num_questions=num_questions,
                difficulty=difficulty
            )
            self.current_quiz = quiz
            return quiz.questions
        except Exception as e:
            print(f"Error generating quiz: {e}")
            return None
    
    def generate_adaptive_quiz(self, num_questions: int = 10) -> Optional[List[Question]]:
        """
        Generate adaptive quiz based on user performance.
        
        Args:
            num_questions: Number of questions to generate
            
        Returns:
            List of generated questions or None
        """
        if not self.current_material:
            print("No material loaded!")
            return None
        
        if not self.adaptive:
            print("Adaptive learning not initialized!")
            return None
        
        try:
            questions = self.adaptive.generate_adaptive_quiz(
                material_text=self.current_material,
                num_questions=num_questions
            )
            self.current_quiz = questions
            return questions
        except Exception as e:
            print(f"Error generating adaptive quiz: {e}")
            return None
    
    def evaluate_answer(self, question: Question, user_answer: str) -> Dict:
        """
        Evaluate a user's answer to a question.
        
        Args:
            question: The question object
            user_answer: User's selected answer
            
        Returns:
            Dictionary with evaluation results
        """
        # Convert answers (user or stored) to zero-based option indices for comparison
        def _answer_to_index(q: Question, ans: Optional[str]) -> Optional[int]:
            if not ans:
                return None
            s_raw = ans.strip()
            # Leading letter like 'A', 'A.' or 'A)'
            m = re.match(r"^\s*([A-Da-d])\s*[\.|\)]?\s*(.*)$", s_raw)
            if m:
                return ord(m.group(1).upper()) - ord('A')

            s = re.sub(r"\s+", " ", s_raw).strip().lower()
            for idx, opt in enumerate(q.options or []):
                opt_norm = re.sub(r"\s+", " ", (opt or "")).strip().lower()
                if s == opt_norm or s in opt_norm or opt_norm in s:
                    return idx

            return None

        user_idx = _answer_to_index(question, user_answer)
        # Determine correct index either from a letter or by matching option text
        correct_idx = None
        if question.correct_answer:
            ca = (question.correct_answer or '').strip()
            if re.match(r"^[A-Da-d]$", ca):
                correct_idx = ord(ca.upper()) - ord('A')
            else:
                correct_idx = _answer_to_index(question, ca)

        is_correct = (user_idx is not None and correct_idx is not None and user_idx == correct_idx)
        # Final fallback: if user provided full option text that equals the correct option, accept it
        if not is_correct and correct_idx is not None and user_answer:
            ua_norm = re.sub(r"\s+", " ", user_answer.strip()).lower()
            correct_opt = (question.options or [])[correct_idx] if (question.options and len(question.options) > correct_idx) else None
            if correct_opt and ua_norm == re.sub(r"\s+", " ", correct_opt.strip()).lower():
                is_correct = True
        
        # Save to progress tracker
        if self.tracker:
            self.tracker.record_answer(
                question_id=id(question),
                selected_option=user_answer,
                is_correct=is_correct
            )
        
        return {
            "is_correct": is_correct,
            "question": question.question_text,
            "user_answer": user_answer,
            "correct_answer": question.correct_answer,
            "explanation": question.explanation
        }
    
    def get_explanation(self, concept: str, context: str = None) -> str:
        """
        Get explanation for a concept.
        
        Args:
            concept: Concept to explain
            context: Additional context
            
        Returns:
            Explanation text
        """
        if not self.explanation_generator:
            return "Explanation generator not available. Please configure API key."
        
        try:
            explanation = self.explanation_generator.generate_explanation(
                concept=concept,
                context=context
            )
            return explanation.explanation_text
        except Exception as e:
            return f"Error generating explanation: {e}"
    
    def get_user_stats(self) -> Dict:
        """Get current user statistics."""
        if not self.tracker:
            return {}
        return self.tracker.get_user_stats()
    
    def get_weak_areas(self) -> List[Dict]:
        """Get list of user's weak areas."""
        if not self.tracker:
            return []
        return self.tracker.get_weak_areas()
    
    def get_recommendations(self) -> List[str]:
        """Get personalized recommendations."""
        if not self.tracker:
            return ["Configure API key to get recommendations."]
        return self.tracker.get_recommendations()
    
    def get_performance_trend(self) -> Dict:
        """Get user's performance trend."""
        if not self.tracker:
            return {"trend": "unknown"}
        return self.tracker.get_performance_trend()
    
    def finish_quiz(self, questions: List[Question], answers: Dict) -> Dict:
        """
        Finish a quiz and record results.
        
        Args:
            questions: List of questions
            answers: Dictionary of question index to answer
            
        Returns:
            Quiz results dictionary
        """
        correct_count = 0
        total_questions = len(questions)
        
        def _answer_to_index_local(q: Question, ans: Optional[str]) -> Optional[int]:
            if not ans:
                return None
            s_raw = ans.strip()
            m = re.match(r"^\s*([A-Da-d])\s*[\.|\)]?\s*(.*)$", s_raw)
            if m:
                return ord(m.group(1).upper()) - ord('A')
            s = re.sub(r"\s+", " ", s_raw).strip().lower()
            for idx, opt in enumerate(q.options or []):
                opt_norm = re.sub(r"\s+", " ", (opt or "")).strip().lower()
                if s == opt_norm or s in opt_norm or opt_norm in s:
                    return idx
            return None

        for i, question in enumerate(questions):
            user_answer = answers.get(i)
            user_idx = _answer_to_index_local(question, user_answer)
            correct_idx = None
            if question.correct_answer:
                ca = (question.correct_answer or '').strip()
                if re.match(r"^[A-Da-d]$", ca):
                    correct_idx = ord(ca.upper()) - ord('A')
                else:
                    correct_idx = _answer_to_index_local(question, ca)

            is_correct = (user_idx is not None and correct_idx is not None and user_idx == correct_idx)
            if not is_correct and correct_idx is not None and user_answer:
                ua_norm = re.sub(r"\s+", " ", user_answer.strip()).lower()
                correct_opt = (question.options or [])[correct_idx] if (question.options and len(question.options) > correct_idx) else None
                if correct_opt and ua_norm == re.sub(r"\s+", " ", correct_opt.strip()).lower():
                    is_correct = True

            if is_correct:
                correct_count += 1
            
            # Save answer
            if self.tracker:
                self.tracker.record_answer(
                    question_id=i + 1,
                    selected_option=user_answer or "",
                    is_correct=is_correct
                )
        
        # Calculate score
        score = (correct_count / total_questions) * 100
        
        # Save progress
        if self.tracker:
            self.tracker.record_quiz_result(
                quiz_id=1,
                score=score,
                total_questions=total_questions,
                correct_answers=correct_count,
                time_spent=0
            )
        
        return {
            "score": score,
            "correct": correct_count,
            "total": total_questions,
            "accuracy": score
        }
    
    def get_adaptive_difficulty(self) -> str:
        """Get recommended difficulty based on performance."""
        if not self.adaptive:
            return "medium"
        return self.adaptive.get_next_difficulty()
    
    def create_study_plan(self, goal: str = "master") -> Dict:
        """Create a personalized study plan."""
        if not self.adaptive or not self.current_material:
            return {"error": "Not enough data to create study plan"}
        
        return self.adaptive.create_personalized_study_plan(
            material_text=self.current_material,
            goal=goal
        )


def main():
    """Main entry point for the application."""
    app = SmartStudyBuddy()
    
    # Check for API key
    if not app.api_key:
        print("=" * 50)
        print("[WARNING] API Key Not Configured")
        print("=" * 50)
        print("\nTo use Smart Study Buddy, you need to configure an API key.")
        print("\nSupported AI Providers:")
        print("1. OpenAI - Get API key from https://platform.openai.com")
        print("2. Google Gemini - Get API key from https://aistudio.google.com")
        print("\nSet your API key using:")
        print("  export AI_API_KEY='your-api-key-here'")
        print("  export AI_API_TYPE='openai'  # or 'gemini'")
        print("\n" + "=" * 50)
        return
    
    print("Smart Study Buddy initialized successfully!")
    print(f"API Provider: {app.api_type}")
    print(f"User ID: {app.current_user_id}")
    
    # Example usage
    print("\n" + "=" * 50)
    print("Example Usage:")
    print("=" * 50)
    print("""
# Load material from file
app.load_material(file_path='study_material.pdf')

# Or load from text
app.load_material(text='Your study material text here...')

# Generate a quiz
questions = app.generate_quiz(num_questions=10, difficulty='medium')

# Or generate adaptive quiz
questions = app.generate_adaptive_quiz(num_questions=10)

# Get user stats
stats = app.get_user_stats()

# Get recommendations
recommendations = app.get_recommendations()
""")


if __name__ == "__main__":
    main()
