"""
Database module for Smart Study Buddy.
Handles SQLite database operations for user data and learning history.
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Database file path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'learning.db')


def get_connection() -> sqlite3.Connection:
    """Create and return a database connection."""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    """Initialize the database with required tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_studied_hours REAL DEFAULT 0,
            total_quizzes_taken INTEGER DEFAULT 0,
            average_score REAL DEFAULT 0
        )
    ''')
    
    # Create study materials table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS study_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            content TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Create quizzes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            material_id INTEGER,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (material_id) REFERENCES study_materials(id)
        )
    ''')
    
    # Create questions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            options TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            explanation TEXT,
            difficulty INTEGER DEFAULT 1,
            question_type TEXT DEFAULT 'mcq',
            FOREIGN KEY (quiz_id) REFERENCES quizzes(id)
        )
    ''')
    
    # Create answers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            selected_option TEXT NOT NULL,
            is_correct INTEGER NOT NULL,
            answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    ''')
    
    # Create progress_summary table for tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS progress_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            material_id INTEGER,
            quiz_id INTEGER,
            score REAL,
            total_questions INTEGER,
            correct_answers INTEGER,
            time_spent INTEGER,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (material_id) REFERENCES study_materials(id),
            FOREIGN KEY (quiz_id) REFERENCES quizzes(id)
        )
    ''')
    
    conn.commit()
    conn.close()


def create_user(username: str, email: str = None) -> int:
    """Create a new user and return their ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            'INSERT INTO users (username, email) VALUES (?, ?)',
            (username, email)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except sqlite3.IntegrityError:
        # User already exists, return existing ID
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        return result['id'] if result else None
    finally:
        conn.close()


def get_user(user_id: int) -> Optional[Dict]:
    """Get user by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return dict(result) if result else None


def save_study_material(user_id: int, filename: str, content: str) -> int:
    """Save study material and return its ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT INTO study_materials (user_id, filename, content) VALUES (?, ?, ?)',
        (user_id, filename, content)
    )
    conn.commit()
    material_id = cursor.lastrowid
    conn.close()
    return material_id


def get_study_material(material_id: int) -> Optional[Dict]:
    """Get study material by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM study_materials WHERE id = ?', (material_id,))
    result = cursor.fetchone()
    conn.close()
    return dict(result) if result else None


def create_quiz(user_id: int, material_id: int = None, title: str = None) -> int:
    """Create a new quiz and return its ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT INTO quizzes (user_id, material_id, title) VALUES (?, ?, ?)',
        (user_id, material_id, title)
    )
    conn.commit()
    quiz_id = cursor.lastrowid
    conn.close()
    return quiz_id


def save_question(quiz_id: int, question_text: str, options: List[str], 
                  correct_answer: str, explanation: str = None, 
                  difficulty: int = 1, question_type: str = 'mcq') -> int:
    """Save a question to a quiz."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Convert options list to JSON string
    options_str = str(options)
    
    cursor.execute('''
        INSERT INTO questions (quiz_id, question_text, options, correct_answer, 
                              explanation, difficulty, question_type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (quiz_id, question_text, options_str, correct_answer, explanation, 
          difficulty, question_type))
    
    conn.commit()
    question_id = cursor.lastrowid
    conn.close()
    return question_id


def save_answer(user_id: int, question_id: int, selected_option: str, 
                is_correct: bool) -> int:
    """Save an answer to the database with retry logic for locks."""
    import time
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO answers (user_id, question_id, selected_option, is_correct)
                VALUES (?, ?, ?, ?)
            ''', (user_id, question_id, selected_option, 1 if is_correct else 0))
            
            conn.commit()
            answer_id = cursor.lastrowid
            conn.close()
            return answer_id
        except sqlite3.OperationalError as e:
            if 'locked' in str(e).lower():
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(0.5)  # Wait before retrying
                else:
                    raise
            else:
                raise
        except Exception:
            conn.close()
            raise


def save_progress_summary(user_id: int, material_id: int, quiz_id: int,
                          score: float, total_questions: int, 
                          correct_answers: int, time_spent: int) -> int:
    """Save a progress summary with retry logic for locks."""
    import time
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO progress_summary (user_id, material_id, quiz_id, score,
                                             total_questions, correct_answers, time_spent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, material_id, quiz_id, score, total_questions, 
                  correct_answers, time_spent))
            
            conn.commit()
            summary_id = cursor.lastrowid
            conn.close()
            return summary_id
        except sqlite3.OperationalError as e:
            if 'locked' in str(e).lower():
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(0.5)  # Wait before retrying
                else:
                    raise
            else:
                raise
        except Exception:
            conn.close()
            raise


def get_user_progress(user_id: int, limit: int = 10) -> List[Dict]:
    """Get user's recent progress summaries."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM progress_summary 
        WHERE user_id = ? 
        ORDER BY completed_at DESC 
        LIMIT ?
    ''', (user_id, limit))
    
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]


def get_user_stats(user_id: int) -> Dict:
    """Get comprehensive user statistics."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get total quizzes taken
    cursor.execute('SELECT COUNT(*) as count FROM progress_summary WHERE user_id = ?', 
                   (user_id,))
    total_quizzes = cursor.fetchone()['count']
    
    # Get average score
    cursor.execute('SELECT AVG(score) as avg_score FROM progress_summary WHERE user_id = ?', 
                   (user_id,))
    avg_score = cursor.fetchone()['avg_score'] or 0
    
    # Get correct answers count
    cursor.execute('SELECT SUM(correct_answers) as total_correct FROM progress_summary WHERE user_id = ?', 
                   (user_id,))
    total_correct = cursor.fetchone()['total_correct'] or 0
    
    # Get total questions
    cursor.execute('SELECT SUM(total_questions) as total_questions FROM progress_summary WHERE user_id = ?', 
                   (user_id,))
    total_questions = cursor.fetchone()['total_questions'] or 1
    
    # Get accuracy
    accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0
    
    conn.close()
    
    return {
        'total_quizzes': total_quizzes,
        'average_score': round(avg_score, 2) if avg_score else 0,
        'total_correct': total_correct,
        'total_questions': total_questions,
        'accuracy': round(accuracy, 2)
    }


def get_weak_areas(user_id: int) -> List[Dict]:
    """Get list of weak areas based on user's performance."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get questions with low correct rate
    cursor.execute('''
        SELECT q.question_text, q.difficulty, 
               AVG(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) as correct_rate
        FROM questions q
        JOIN answers a ON q.id = a.question_id
        WHERE a.user_id = ?
        GROUP BY q.id
        HAVING correct_rate < 0.7
        ORDER BY correct_rate ASC
        LIMIT 10
    ''', (user_id,))
    
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]


# Initialize database on module import
init_database()
