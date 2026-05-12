"""
User Interface Module
Streamlit-based UI for Smart Study Buddy.
"""

import streamlit as st
import os
import sys
import json
from typing import List, Dict, Optional

from modules.content_processor import ContentProcessor, process_file
from modules.quiz_generator import QuizGenerator, generate_quiz
from modules.explanation import ExplanationGenerator
from modules.progress_tracker import ProgressTracker
from modules.adaptive import AdaptiveLearning


class StudyBuddyUI:
    """Streamlit UI for Smart Study Buddy."""
    
    def __init__(self):
        """Initialize the UI components."""
        self.content_processor = ContentProcessor()
        self.quiz_generator = None
        self.explanation_generator = None
        self.tracker = None
        self.adaptive = None
        
        # Initialize API key from environment or session
        self.api_key = os.environ.get('AI_API_KEY', '')
        self.api_type = os.environ.get('AI_API_TYPE', 'openrouter').lower()
        
        # Initialize session state for caching
        self._init_session_state()
        
        # Initialize generators if API key is available
        if self.api_key:
            self._initialize_generators()
    
    def _init_session_state(self):
        """Initialize session state variables for caching."""
        if 'material_text' not in st.session_state:
            st.session_state.material_text = None
        if 'uploaded_file_name' not in st.session_state:
            st.session_state.uploaded_file_name = None
        if 'user_id' not in st.session_state:
            st.session_state.user_id = 1  # Default user ID
        if 'quiz_started' not in st.session_state:
            st.session_state.quiz_started = False
        if 'show_results' not in st.session_state:
            st.session_state.show_results = False
        if 'questions' not in st.session_state:
            st.session_state.questions = []
        if 'current_question' not in st.session_state:
            st.session_state.current_question = 0
        if 'answers' not in st.session_state:
            st.session_state.answers = {}
        if 'quiz_results' not in st.session_state:
            st.session_state.quiz_results = {}
    
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
    
    def render_header(self):
        """Render the header section."""
        st.set_page_config(
            page_title="🎓 Smart Study Buddy",
            page_icon="📚",
            layout="wide"
        )
        
        st.title("🎓 Smart Study Buddy")
        st.markdown("Your AI-powered personal tutor")
        st.markdown("---")
    
    def render_api_key_input(self):
        """Render API key input section."""
        with st.expander("⚙️ API Configuration", expanded=not self.api_key):
            # Auto-detect provider from environment
            env_api_type = os.environ.get('AI_API_TYPE', 'openrouter').lower()
            provider_map = {
                "openai": "OpenAI",
                "openrouter": "OpenRouter",
                "gemini": "Gemini",
            }
            current_provider = provider_map.get(env_api_type, "OpenRouter")
            
            st.info(f"🔗 Using **{current_provider}** API (configured in .env file)")
            
            api_key = st.text_input(
                "Enter API Key:",
                type="password",
                value=self.api_key
            )

            if api_key and api_key != self.api_key:
                self.api_key = api_key
                os.environ['AI_API_KEY'] = api_key
                self._initialize_generators()
                st.success("API Key saved successfully!")
    
    def render_upload_section(self):
        """Render file upload section."""
        st.header("📁 Upload Study Material")
        
        uploaded_file = st.file_uploader(
            "Upload a PDF or text file",
            type=['pdf', 'txt']
        )
        
        # Check if file is cached and hasn't changed
        if uploaded_file is not None:
            current_file_name = uploaded_file.name
            
            # If same file is already cached, use cached version
            if (st.session_state.uploaded_file_name == current_file_name and 
                st.session_state.material_text is not None):
                st.info("📂 Using cached material...")
                return st.session_state.material_text
            
            # New file or no cache - process it
            file_type = uploaded_file.type
            
            if file_type == "application/pdf":
                material_text = self._process_pdf(uploaded_file)
            elif file_type == "text/plain":
                material_text = self._process_text_file(uploaded_file)
            else:
                material_text = None
            
            # Cache the material
            if material_text:
                st.session_state.material_text = material_text
                st.session_state.uploaded_file_name = current_file_name
            
            return material_text
        
        # Option to paste text directly
        st.markdown("### Or paste text directly")
        text_input = st.text_area(
            "Paste your study material here:",
            height=200,
            placeholder="Paste your text content here..."
        )
        
        if text_input:
            material_text = self._process_text_input(text_input)
            # Cache text input
            st.session_state.material_text = material_text
            st.session_state.uploaded_file_name = "text_input"
            return material_text
        
        # Return cached material if available even if no new upload
        if st.session_state.material_text is not None:
            st.info("📂 Using previously loaded material...")
            return st.session_state.material_text
        
        return None
    
    def _process_pdf(self, file) -> str:
        """Process uploaded PDF file."""
        with st.spinner("Extracting text from PDF..."):
            # Save uploaded file temporarily
            temp_path = f"temp_{file.name}"
            with open(temp_path, "wb") as f:
                f.write(file.getvalue())
            
            try:
                document = process_file(temp_path)
                os.remove(temp_path)
                return document.content
            except Exception as e:
                st.error(f"Error processing PDF: {e}")
                return None
    
    def _process_text_file(self, file) -> str:
        """Process uploaded text file."""
        try:
            content = file.read().decode('utf-8')
            return content
        except Exception as e:
            st.error(f"Error reading text file: {e}")
            return None
    
    def _process_text_input(self, text: str) -> str:
        """Process directly input text."""
        return text
    
    def render_quiz_section(self, material_text: str):
        """Render quiz generation and taking section."""
        if not material_text:
            return
        
        st.header("📝 Generate Quiz")
        
        # Quiz settings
        col1, col2 = st.columns(2)
        with col1:
            num_questions = st.slider(
                "Number of Questions:",
                min_value=5,
                max_value=20,
                value=10
            )
        with col2:
            difficulty = st.selectbox(
                "Difficulty Level:",
                ["easy", "medium", "hard", "adaptive"]
            )
        
        if st.button("🚀 Generate Quiz", type="primary"):
            with st.spinner("⏳ Generating quiz questions... (this may take a moment)"):
                try:
                    if difficulty == "adaptive":
                        # Use adaptive learning
                        self.adaptive = AdaptiveLearning()
                        questions = self.adaptive.generate_adaptive_quiz(
                            material_text,
                            num_questions=num_questions
                        )
                    else:
                        # Generate quiz with specified difficulty
                        if not self.quiz_generator:
                            st.error("Please configure API key first!")
                            return
                        
                        quiz = self.quiz_generator.generate_quiz_from_text(
                            text=material_text,
                            num_questions=num_questions,
                            difficulty=difficulty
                        )
                        questions = quiz.questions
                    
                    if questions:
                        st.session_state.questions = questions
                        st.session_state.current_question = 0
                        st.session_state.answers = {}
                        st.session_state.quiz_started = True
                        st.success(f"✅ Generated {len(questions)} questions!")
                        st.rerun()
                    else:
                        st.error("Failed to generate questions. Please try again.")
                        
                except Exception as e:
                    st.error(f"Error generating quiz: {e}")
    
    def render_quiz_taking(self):
        """Render quiz taking interface."""
        if not st.session_state.get('quiz_started'):
            return
        
        questions = st.session_state.get('questions', [])
        current_question = st.session_state.get('current_question', 0)
        answers = st.session_state.get('answers', {})
        
        if not questions:
            return
        
        st.header("📝 Quiz Time!")
        
        # Progress bar
        progress = (current_question + 1) / len(questions)
        st.progress(progress)
        st.write(f"Question {current_question + 1} of {len(questions)}")
        
        # Display current question
        question = questions[current_question]
        
        st.subheader(f"Question {current_question + 1}")
        st.write(question.question_text)
        
        # Display options
        selected_option = st.radio(
            "Select your answer:",
            question.options,
            key=f"question_{current_question}"
        )
        
        # Navigation buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if current_question > 0:
                if st.button("⬅️ Previous"):
                    st.session_state.current_question = current_question - 1
                    st.rerun()
        
        with col2:
            if current_question < len(questions) - 1:
                if st.button("Next ➡️"):
                    # Save answer
                    answers[current_question] = selected_option
                    st.session_state.answers = answers
                    st.session_state.current_question = current_question + 1
                    st.rerun()
            else:
                if st.button("✅ Finish Quiz"):
                    self._finish_quiz(questions, answers)
        
        with col3:
            if st.button("❌ Cancel"):
                self._reset_quiz()
    
    def _finish_quiz(self, questions: list, answers: dict):
        """Finish the quiz and calculate results."""
        correct_count = 0
        
        # Ensure tracker is initialized with proper user_id
        if self.tracker is None:
            self.tracker = ProgressTracker(user_id=st.session_state.get('user_id', 1))
        
        for i, question in enumerate(questions):
            user_answer = answers.get(i)
            
            # Use SmartStudyBuddy's evaluation logic if available, or implement robust matching
            is_correct = self._evaluate_answer_robust(question, user_answer)
            
            if is_correct:
                correct_count += 1
            
            # Save answer to database
            try:
                self.tracker.record_answer(
                    question_id=i + 1,
                    selected_option=user_answer or "",
                    is_correct=is_correct
                )
            except Exception as e:
                st.error(f"Error saving answer: {e}")
                continue
        
        # Calculate score
        score = (correct_count / len(questions)) * 100
        
        # Save quiz result
        if self.tracker:
            try:
                self.tracker.record_quiz_result(
                    quiz_id=1,  # Default quiz ID
                    score=score,
                    total_questions=len(questions),
                    correct_answers=correct_count,
                    time_spent=0  # Would need timer implementation
                )
            except Exception as e:
                st.error(f"Error saving quiz result: {e}")
        
        # Store results
        st.session_state.quiz_results = {
            'score': score,
            'correct': correct_count,
            'total': len(questions),
            'questions': questions,
            'answers': answers
        }
        
        st.session_state.quiz_started = False
        st.session_state.show_results = True
        st.rerun()
    
    def render_quiz_results(self):
        """Render quiz results section."""
        if not st.session_state.get('show_results'):
            return
        
        results = st.session_state.get('quiz_results', {})
        
        st.header("📊 Quiz Results")
        
        # Score display
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Score", f"{results.get('score', 0):.1f}%")
        with col2:
            st.metric("Correct", results.get('correct', 0))
        with col3:
            st.metric("Total", results.get('total', 0))
        
        # Detailed results
        st.subheader("Detailed Results")
        
        for i, question in enumerate(results.get('questions', [])):
            user_answer = results.get('answers', {}).get(i)
            is_correct = self._evaluate_answer_robust(question, user_answer)
            
            with st.expander(f"Question {i + 1}: {'✅ Correct' if is_correct else '❌ Incorrect'}"):
                st.write(f"**Question:** {question.question_text}")
                st.write(f"**Your Answer:** {user_answer}")
                st.write(f"**Correct Answer:** {question.correct_answer}")
                
                if question.explanation:
                    with st.expander("View Explanation"):
                        st.write(question.explanation)
        
        # Show weak areas
        if self.tracker:
            weak_areas = self.tracker.get_weak_areas()
            if weak_areas:
                st.subheader("Weak Areas to Focus On")
                for area in weak_areas[:3]:
                    st.info(f"• {area['question_text'][:80]}...")
        
        # Show recommendations
        if self.tracker:
            recommendations = self.tracker.get_recommendations()
            if recommendations:
                st.subheader("Recommendations")
                for rec in recommendations:
                    st.success(f"💡 {rec}")
        
        if st.button("🔄 Start New Quiz"):
            self._reset_quiz()
    
    def render_progress_section(self):
        """Render progress tracking section."""
        st.header("📈 Progress Tracking")
        
        if self.tracker is None:
            self.tracker = ProgressTracker()
        
        stats = self.tracker.get_user_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Quizzes", stats.get('total_quizzes', 0))
        with col2:
            st.metric("Average Score", f"{stats.get('average_score', 0):.1f}%")
        with col3:
            st.metric("Accuracy", f"{stats.get('accuracy', 0):.1f}%")
        with col4:
            st.metric("Questions Answered", stats.get('total_questions', 0))
        
        # Performance trend
        trend = self.tracker.get_performance_trend()
        st.subheader("Performance Trend")
        
        if trend.get('trend') == 'improving':
            st.success("📈 Your performance is improving!")
        elif trend.get('trend') == 'declining':
            st.warning("📉 Your performance is declining. Take a break and try again!")
        else:
            st.info("➡️ Your performance is stable")
        
        # Recent progress
        recent = self.tracker.get_recent_progress(limit=5)
        if recent:
            st.subheader("Recent Progress")
            for i, progress in enumerate(recent):
                st.write(f"**Quiz {i+1}:** {progress['score']:.1f}% - "
                        f"{progress['correct_answers']}/{progress['total_questions']} correct")
    
    def render_explanation_section(self):
        """Render explanation generation section."""
        st.header("❓ Need Help Understanding?")
        
        concept = st.text_input(
            "Enter a concept you want to understand:",
            placeholder="e.g., Photosynthesis, Newton's Laws, etc."
        )
        
        if st.button("Get Explanation"):
            if concept:
                with st.spinner("Generating explanation..."):
                    if self.explanation_generator:
                        explanation = self.explanation_generator.generate_explanation(concept)
                        
                        st.subheader(f"Explanation: {concept}")
                        st.write(explanation.explanation_text)
                        
                        if explanation.examples:
                            st.subheader("Examples")
                            for example in explanation.examples:
                                st.write(f"• {example}")
                        
                        if explanation.analogies:
                            st.subheader("Analogies")
                            for analogy in explanation.analogies:
                                st.write(f"💡 {analogy}")
                    else:
                        st.error("Please configure API key first!")
            else:
                st.warning("Please enter a concept!")
    
    def render_shutdown_section(self):
        """Render shutdown button section."""
        st.markdown("---")
        st.subheader("⚙️ App Controls")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button("🛑 Shutdown App", type="secondary", use_container_width=True):
                # Show confirmation
                st.warning("⚠️ App is shutting down...")
                st.info("You can close this window or restart the app when needed.")
                sys.exit(0)
    
    def _evaluate_answer_robust(self, question, user_answer) -> bool:
        """Robustly evaluate if the user answer is correct."""
        if not user_answer:
            return False
            
        import re
        
        # 1. Direct match
        if user_answer == question.correct_answer:
            return True
            
        # 2. Match by index (if correct_answer is 'A', 'B', 'C', or 'D')
        ca = str(question.correct_answer).strip().upper()
        if ca in ['A', 'B', 'C', 'D']:
            idx = ord(ca) - ord('A')
            if 0 <= idx < len(question.options):
                correct_option_text = question.options[idx]
                if user_answer == correct_option_text:
                    return True
                    
        # 3. Match by letter prefix (if user_answer is 'A. Option Text')
        m = re.match(r"^\s*([A-Da-d])\s*[\.|\)]?\s*(.*)$", str(user_answer))
        if m:
            user_letter = m.group(1).upper()
            if user_letter == ca:
                return True
            
            # Also check if the text part matches the correct option text
            user_text = m.group(2).strip().lower()
            if ca in ['A', 'B', 'C', 'D']:
                idx = ord(ca) - ord('A')
                if 0 <= idx < len(question.options):
                    correct_text = question.options[idx].strip().lower()
                    if user_text == correct_text:
                        return True

        # 4. Normalized text match
        def normalize(s):
            return re.sub(r"\s+", " ", str(s)).strip().lower()
            
        ua_norm = normalize(user_answer)
        
        # Check if user answer matches any option text that is the correct one
        if ca in ['A', 'B', 'C', 'D']:
            idx = ord(ca) - ord('A')
            if 0 <= idx < len(question.options):
                if ua_norm == normalize(question.options[idx]):
                    return True
        else:
            # If correct_answer is not a letter, compare it directly with normalized user answer
            if ua_norm == normalize(question.correct_answer):
                return True
                
        return False

    def _reset_quiz(self):
        """Reset quiz state while keeping cached material."""
        st.session_state.quiz_started = False
        st.session_state.show_results = False
        st.session_state.questions = []
        st.session_state.current_question = 0
        st.session_state.answers = {}
        st.session_state.quiz_results = {}
        st.rerun()
    
    def run(self):
        """Run the main UI loop."""
        self.render_header()
        self.render_api_key_input()
        
        # Initialize tracker with proper user_id
        if self.tracker is None:
            self.tracker = ProgressTracker(user_id=st.session_state.get('user_id', 1))
        
        # Main content
        material_text = self.render_upload_section()
        
        if material_text:
            st.success("✅ Material loaded successfully!")
            
            # Show material preview
            with st.expander("📄 View Material Preview"):
                st.text(material_text[:500] + "..." if len(material_text) > 500 else material_text)
            
            # Quiz section
            self.render_quiz_section(material_text)
            
            # Quiz taking
            if st.session_state.get('quiz_started'):
                self.render_quiz_taking()
            
            # Results
            if st.session_state.get('show_results'):
                self.render_quiz_results()
            
            # Progress tracking
            self.render_progress_section()
            
            # Explanation section
            self.render_explanation_section()
        else:
            st.info("Upload a study material to get started!")
        
        # Shutdown section at the bottom
        self.render_shutdown_section()


def main():
    """Main entry point."""
    ui = StudyBuddyUI()
    ui.run()


if __name__ == "__main__":
    main()
