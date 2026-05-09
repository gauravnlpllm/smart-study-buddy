"""
Progress Tracker Module
Tracks and analyzes user learning progress.
"""

import os
import json
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import sqlite3

from database.db import (
    save_answer, save_progress_summary, get_user_progress,
    get_user_stats, get_weak_areas, get_user, create_user
)


@dataclass
class QuizResult:
    """Represents the result of a quiz."""
    user_id: int
    quiz_id: int
    score: float
    total_questions: int
    correct_answers: int
    time_spent: int  # in seconds
    answers: List[Dict] = field(default_factory=list)


class ProgressTracker:
    """Tracks and analyzes user learning progress."""
    
    def __init__(self, user_id: int = None, username: str = None):
        """
        Initialize the progress tracker.
        
        Args:
            user_id: User ID (optional if username provided)
            username: Username (optional if user_id provided)
        """
        self.user_id = user_id
        self.username = username
        
        if not self.user_id and self.username:
            self.user_id = self._get_or_create_user()
    
    def _get_or_create_user(self) -> int:
        """Get or create a user in the database."""
        if self.username:
            return create_user(self.username)
        return 1  # Default user ID
    
    def record_answer(self, question_id: int, selected_option: str,
                      is_correct: bool) -> int:
        """
        Record a user's answer to a question.
        
        Args:
            question_id: ID of the question
            selected_option: The option selected by the user
            is_correct: Whether the answer was correct
            
        Returns:
            ID of the saved answer
        """
        return save_answer(self.user_id, question_id, selected_option, is_correct)
    
    def record_quiz_result(self, quiz_id: int, score: float,
                           total_questions: int, correct_answers: int,
                           time_spent: int) -> int:
        """
        Record the result of a completed quiz.
        
        Args:
            quiz_id: ID of the quiz
            score: Score achieved (percentage)
            total_questions: Total number of questions
            correct_answers: Number of correct answers
            time_spent: Time spent on quiz (in seconds)
            
        Returns:
            ID of the saved progress summary
        """
        return save_progress_summary(
            user_id=self.user_id,
            material_id=None,  # Can be updated if material tracking is needed
            quiz_id=quiz_id,
            score=score,
            total_questions=total_questions,
            correct_answers=correct_answers,
            time_spent=time_spent
        )
    
    def get_user_stats(self) -> Dict:
        """
        Get comprehensive user statistics.
        
        Returns:
            Dictionary with user statistics
        """
        return get_user_stats(self.user_id)
    
    def get_recent_progress(self, limit: int = 10) -> List[Dict]:
        """
        Get user's recent progress summaries.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of progress summary dictionaries
        """
        return get_user_progress(self.user_id, limit)
    
    def get_weak_areas(self) -> List[Dict]:
        """
        Get list of weak areas based on user's performance.
        
        Returns:
            List of dictionaries with weak area information
        """
        return get_weak_areas(self.user_id)
    
    def calculate_difficulty_adjustment(self) -> str:
        """
        Calculate appropriate difficulty adjustment based on performance.
        
        Returns:
            Difficulty level: "easy", "medium", or "hard"
        """
        stats = self.get_user_stats()
        accuracy = stats.get('accuracy', 0)
        
        if accuracy >= 80:
            return "hard"
        elif accuracy >= 60:
            return "medium"
        else:
            return "easy"
    
    def get_performance_trend(self) -> Dict:
        """
        Analyze user's performance trend over time.
        
        Returns:
            Dictionary with trend analysis
        """
        progress = self.get_recent_progress(limit=20)
        
        if len(progress) < 2:
            return {
                "trend": "insufficient_data",
                "improving": False,
                "recent_scores": []
            }
        
        scores = [p['score'] for p in progress]
        recent_scores = scores[:5]
        
        # Calculate trend
        if len(scores) >= 2:
            first_half = scores[:len(scores)//2]
            second_half = scores[len(scores)//2:]
            
            first_avg = sum(first_half) / len(first_half) if first_half else 0
            second_avg = sum(second_half) / len(second_half) if second_half else 0
            
            if second_avg > first_avg + 5:
                trend = "improving"
            elif second_avg < first_avg - 5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "trend": trend,
            "improving": trend == "improving",
            "recent_scores": recent_scores,
            "average_score": sum(scores) / len(scores) if scores else 0,
            "last_5_average": sum(recent_scores) / len(recent_scores) if recent_scores else 0
        }
    
    def get_recommendations(self) -> List[str]:
        """
        Generate recommendations based on user's performance.
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        stats = self.get_user_stats()
        weak_areas = self.get_weak_areas()
        trend = self.get_performance_trend()
        
        # Recommendation based on accuracy
        if stats.get('accuracy', 0) < 60:
            recommendations.append(
                "Your accuracy is below 60%. Consider reviewing the material "
                "and trying easier questions first."
            )
        elif stats.get('accuracy', 0) < 80:
            recommendations.append(
                "Good progress! Your accuracy is between 60-80%. Continue "
                "practicing with medium difficulty questions."
            )
        else:
            recommendations.append(
                "Excellent! Your accuracy is above 80%. Try challenging "
                "harder questions to further improve."
            )
        
        # Recommendation based on weak areas
        if weak_areas:
            recommendations.append(
                f"Focus on improving in these areas: "
                f"{', '.join([q['question_text'][:50] for q in weak_areas[:3]])}"
            )
        
        # Recommendation based on trend
        if trend['trend'] == 'declining':
            recommendations.append(
                "Your recent scores are declining. Consider taking a break and "
                "returning to studying later."
            )
        elif trend['trend'] == 'stable':
            recommendations.append(
                "Your performance is stable. Try mixing up your study topics "
                "to keep learning engaging."
            )
        
        # Recommendation based on activity
        if stats.get('total_quizzes', 0) < 3:
            recommendations.append(
                "You've taken fewer than 3 quizzes. Try to complete at least "
                "one quiz per day for better learning retention."
            )
        
        return recommendations
    
    def get_detailed_report(self) -> Dict:
        """
        Generate a detailed progress report.
        
        Returns:
            Dictionary with complete progress report
        """
        return {
            "user_id": self.user_id,
            "username": self.username,
            "generated_at": datetime.now().isoformat(),
            "statistics": self.get_user_stats(),
            "performance_trend": self.get_performance_trend(),
            "weak_areas": self.get_weak_areas()[:5],  # Top 5 weak areas
            "recommendations": self.get_recommendations(),
            "recent_progress": self.get_recent_progress(limit=5)
        }


def track_quiz_completion(user_id: int, quiz_id: int, score: float,
                          total_questions: int, correct_answers: int,
                          time_spent: int) -> int:
    """
    Convenience function to track quiz completion.
    
    Args:
        user_id: User ID
        quiz_id: Quiz ID
        score: Score achieved
        total_questions: Total questions
        correct_answers: Correct answers
        time_spent: Time spent (seconds)
        
    Returns:
        ID of saved progress summary
    """
    tracker = ProgressTracker(user_id=user_id)
    return tracker.record_quiz_result(
        quiz_id=quiz_id,
        score=score,
        total_questions=total_questions,
        correct_answers=correct_answers,
        time_spent=time_spent
    )
