"""
Adaptive Learning Module
Adjusts difficulty and content based on user performance.
"""

import os
from typing import List, Dict, Optional
from dataclasses import dataclass
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

from modules.quiz_generator import QuizGenerator, Question
from modules.progress_tracker import ProgressTracker


@dataclass
class AdaptiveConfig:
    """Configuration for adaptive learning."""
    min_difficulty: str = "easy"
    max_difficulty: str = "hard"
    difficulty_levels: List[str] = None
    performance_thresholds: Dict[str, float] = None
    min_questions_per_session: int = 5
    max_questions_per_session: int = 20
    
    def __post_init__(self):
        if self.difficulty_levels is None:
            self.difficulty_levels = ["easy", "medium", "hard"]
        
        if self.performance_thresholds is None:
            self.performance_thresholds = {
                "easy": 0.7,      # 70% to advance from easy
                "medium": 0.6,    # 60% to advance from medium
                "hard": 0.5       # 50% to advance from hard
            }


class AdaptiveLearning:
    """Implements adaptive learning based on user performance."""
    
    def __init__(self, user_id: int = None, username: str = None,
                 config: AdaptiveConfig = None):
        """
        Initialize the adaptive learning system.
        
        Args:
            user_id: User ID
            username: Username
            config: Adaptive configuration
        """
        self.user_id = user_id
        self.username = username
        self.config = config or AdaptiveConfig()
        self.tracker = ProgressTracker(user_id=user_id, username=username)
        self.quiz_generator = QuizGenerator()
    
    def get_next_difficulty(self) -> str:
        """
        Determine the next difficulty level based on user performance.
        
        Returns:
            Difficulty level: "easy", "medium", or "hard"
        """
        stats = self.tracker.get_user_stats()
        accuracy = stats.get('accuracy', 0)
        
        if accuracy >= 80:
            return "hard"
        elif accuracy >= 60:
            return "medium"
        else:
            return "easy"
    
    def adjust_difficulty(self, current_difficulty: str, 
                          last_score: float) -> str:
        """
        Adjust difficulty based on last quiz score.
        
        Args:
            current_difficulty: Current difficulty level
            last_score: Score from last quiz (0-100)
            
        Returns:
            New difficulty level
        """
        difficulty_levels = self.config.difficulty_levels
        current_index = difficulty_levels.index(current_difficulty)
        
        # Calculate performance ratio
        performance_ratio = last_score / 100
        
        # Get threshold for current difficulty
        threshold = self.config.performance_thresholds.get(
            current_difficulty, 0.6
        )
        
        # Adjust difficulty
        if performance_ratio >= threshold:
            # Perform well, increase difficulty
            if current_index < len(difficulty_levels) - 1:
                return difficulty_levels[current_index + 1]
        else:
            # Struggled, decrease difficulty
            if current_index > 0:
                return difficulty_levels[current_index - 1]
        
        return current_difficulty
    
    def generate_adaptive_quiz(self, material_text: str, 
                               target_difficulty: str = None,
                               num_questions: int = None) -> List[Question]:
        """
        Generate a quiz with adaptive difficulty.
        
        Args:
            material_text: Study material text
            target_difficulty: Target difficulty level
            num_questions: Number of questions to generate
            
        Returns:
            List of generated questions
        """
        if target_difficulty is None:
            target_difficulty = self.get_next_difficulty()
        
        if num_questions is None:
            num_questions = self.config.min_questions_per_session
        
        # Generate quiz with appropriate difficulty
        quiz = self.quiz_generator.generate_quiz_from_text(
            text=material_text,
            num_questions=num_questions,
            difficulty=target_difficulty
        )
        
        return quiz.questions
    
    def create_personalized_study_plan(self, material_text: str,
                                       goal: str = "master") -> Dict:
        """
        Create a personalized study plan based on user performance.
        
        Args:
            material_text: Study material text
            goal: Learning goal ("master", "review", "prepare")
            
        Returns:
            Dictionary with study plan
        """
        stats = self.tracker.get_user_stats()
        weak_areas = self.tracker.get_weak_areas()
        current_difficulty = self.get_next_difficulty()
        
        # Determine plan based on goal and performance
        if goal == "master":
            plan_type = "comprehensive"
            difficulty_progression = ["easy", "medium", "hard"]
        elif goal == "review":
            plan_type = "review"
            difficulty_progression = [current_difficulty, current_difficulty]
        else:  # prepare
            plan_type = "practice"
            difficulty_progression = ["medium", "hard"]
        
        # Calculate number of sessions needed
        if stats.get('total_quizzes', 0) < 3:
            num_sessions = 5
        elif stats.get('accuracy', 0) < 60:
            num_sessions = 7
        else:
            num_sessions = 3
        
        # Generate plan
        study_plan = {
            "goal": goal,
            "plan_type": plan_type,
            "num_sessions": num_sessions,
            "difficulty_progression": difficulty_progression,
            "weak_areas_to_focus": [q['question_text'][:50] for q in weak_areas[:3]],
            "sessions": []
        }
        
        # Generate session details
        for i in range(num_sessions):
            session_difficulty = difficulty_progression[
                i % len(difficulty_progression)
            ]
            session = {
                "session_number": i + 1,
                "difficulty": session_difficulty,
                "questions_count": 10,
                "focus": "weak_areas" if i % 2 == 0 else "general"
            }
            study_plan["sessions"].append(session)
        
        return study_plan
    
    def get_adaptive_recommendations(self) -> List[Dict]:
        """
        Get adaptive recommendations based on user performance.
        
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        stats = self.tracker.get_user_stats()
        weak_areas = self.tracker.get_weak_areas()
        trend = self.tracker.get_performance_trend()
        
        # Difficulty recommendation
        current_difficulty = self.get_next_difficulty()
        recommendations.append({
            "type": "difficulty",
            "recommendation": f"Current difficulty level: {current_difficulty}",
            "suggestion": "Continue with this difficulty or adjust based on comfort level"
        })
        
        # Weak areas recommendation
        if weak_areas:
            recommendations.append({
                "type": "weak_areas",
                "recommendation": "Focus on these weak areas:",
                "areas": [q['question_text'][:50] for q in weak_areas[:3]],
                "suggestion": "Review material and practice questions on these topics"
            })
        
        # Study frequency recommendation
        if stats.get('total_quizzes', 0) < 5:
            recommendations.append({
                "type": "frequency",
                "recommendation": "Study frequency:",
                "suggestion": "Aim for 3-5 study sessions per week for best results"
            })
        
        # Trend-based recommendation
        if trend['trend'] == 'declining':
            recommendations.append({
                "type": "rest",
                "recommendation": "Performance trend:",
                "suggestion": "Your scores are declining. Consider taking a short break "
                             "and returning to studying when refreshed."
            })
        
        return recommendations
    
    def calculate_mastery_level(self) -> Dict:
        """
        Calculate user's mastery level across different areas.
        
        Returns:
            Dictionary with mastery levels
        """
        stats = self.tracker.get_user_stats()
        weak_areas = self.tracker.get_weak_areas()
        
        accuracy = stats.get('accuracy', 0)
        
        if accuracy >= 90:
            mastery_level = "expert"
        elif accuracy >= 75:
            mastery_level = "advanced"
        elif accuracy >= 60:
            mastery_level = "intermediate"
        elif accuracy >= 40:
            mastery_level = "beginner"
        else:
            mastery_level = "novice"
        
        return {
            "mastery_level": mastery_level,
            "accuracy": accuracy,
            "total_quizzes": stats.get('total_quizzes', 0),
            "weak_areas_count": len(weak_areas),
            "recommendation": self._get_mastery_recommendation(mastery_level)
        }
    
    def _get_mastery_recommendation(self, mastery_level: str) -> str:
        """Get recommendation based on mastery level."""
        recommendations = {
            "expert": "You're an expert! Try teaching others or tackling "
                     "advanced topics to further solidify your knowledge.",
            "advanced": "Great job! You have a strong understanding. Consider "
                       "exploring related advanced topics.",
            "intermediate": "Good progress! Continue practicing and review "
                           "your weak areas to improve further.",
            "beginner": "Keep going! Focus on understanding the basics and "
                       "practice regularly.",
            "novice": "Don't give up! Start with the fundamentals and take "
                     "your time to build a strong foundation."
        }
        return recommendations.get(mastery_level, "Keep learning!")


def get_adaptive_quiz(material_text: str, user_id: int = None,
                      username: str = None) -> List[Question]:
    """
    Convenience function to get an adaptive quiz.
    
    Args:
        material_text: Study material text
        user_id: User ID
        username: Username
        
    Returns:
        List of questions
    """
    adaptive = AdaptiveLearning(user_id=user_id, username=username)
    return adaptive.generate_adaptive_quiz(material_text)
