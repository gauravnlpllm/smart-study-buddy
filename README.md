# Smart Study Buddy - AI Tutor Application

## 📌 Problem Description

Studying is often repetitive and ineffective when learners simply re-read materials. Students need a smarter way to learn that adapts to their understanding level by providing:

- Personalized practice questions
- Clear explanations of concepts
- Progress tracking
- Structured study plans

## 💡 Solution Overview

Smart Study Buddy is an AI-powered tutoring system that:

- Reads study materials (PDF/text)
- Generates quiz questions automatically from random content sections
- Explains difficult concepts in multiple ways
- Tracks learning progress with database persistence
- Adapts difficulty based on performance
- Provides a smooth, cached user experience

---

## 🏗️ System Architecture

The application follows a simple layered architecture:

```
[ User Interface ]
        ↓
[ Application Layer ]
        ↓
[ AI Services ]
        ↓
[ Database ]
```

### Architecture Diagram

```
               ┌──────────────────────┐
               │   User Interface     │
               │ (Streamlit Web App)  │
               └─────────┬────────────┘
                         │
                         ↓
               ┌──────────────────────┐
               │ Application Layer    │
               │ (Main Controller)    │
               └─────────┬────────────┘
                         │
         ┌────────────────┼────────────────┐
         ↓                ↓                ↓
┌──────────────┐  ┌────────────────┐  ┌──────────────┐
│ Content      │  │ Quiz Engine    │  │ Progress     │
│ Processor    │  │ (LLM Calls)    │  │ Tracker      │
└──────┬───────┘  └──────┬─────────┘  └──────┬───────┘
       ↓                 ↓                   ↓
        ┌──────────────────────────────┐
        │       SQLite Database        │
        └──────────────────────────────┘
```

---

## ⚙️ Components Description

### 1. User Interface
- Built using Streamlit web framework
- Handles input/output with user
- Displays quizzes, results, explanations
- Features caching to prevent repeated operations
- Includes shutdown button for graceful termination

### 2. Application Layer
- Central controller of the app
- Connects UI with backend modules
- Manages session state and caching

### 3. Content Processor
- Extracts text from PDFs or input text
- Prepares text for AI processing
- Chunks content for efficient processing

### 4. AI Engine
- Generates quiz questions from random content sections
- Provides answers and explanations
- Uses OpenRouter API with various LLM models
- Implements intelligent chunk selection to avoid preface content

### 5. Progress Tracker
- Stores quiz performance in SQLite database
- Tracks strengths and weaknesses
- Provides user statistics and recommendations

### 6. Database (SQLite)
- Stores user data and learning history
- Lightweight and easy to use
- Includes retry logic for concurrent access

---

## 🔄 Data Flow

1. User uploads study material (PDF/text)
2. System extracts and caches text content
3. AI generates questions from random middle sections
4. User answers questions with navigation controls
5. System evaluates answers and saves to database
6. Results displayed with explanations and recommendations

---

## 🛠️ Tech Stack

- **Python 3.8+**
- **Streamlit** (Web UI)
- **OpenRouter API** (AI models: Gemma, GPT-4, etc.)
- **SQLite** (Database)
- **pdfplumber** (PDF parsing)
- **python-dotenv** (Environment management)

---

## 📂 Project Structure

```
smart-study-buddy/
│
├── app.py                 # CLI entry point
├── ui.py                  # Streamlit web interface
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (gitignored)
│
├── modules/
│   ├── content_processor.py    # Text extraction and processing
│   ├── quiz_generator.py       # AI-powered question generation
│   ├── explanation.py          # Concept explanations
│   ├── progress_tracker.py     # Learning analytics
│   └── adaptive.py             # Difficulty adaptation
│
├── database/
│   └── db.py                   # SQLite database operations
│
├── data/
│   └── learning.db            # SQLite database file
│
└── prompts/
    └── prompts.txt            # AI prompt templates
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- OpenRouter API key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd smart-study-buddy
   ```

2. **Install dependencies**
   ```bash
   pip install -p requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your OpenRouter API key
   ```

4. **Run the application**
   ```bash
   streamlit run ui.py
   ```

### Configuration

Create a `.env` file with:
```env
AI_API_KEY=sk-or-v1-your-openrouter-api-key-here
AI_API_TYPE=openrouter
AI_MODEL=google/gemma-4-26b-a4b-it:free
```

---

## 🎯 Key Features

### ✅ Smart Content Processing
- PDF text extraction with caching
- Intelligent chunk selection (avoids preface content)
- Random section sampling for varied questions

### ✅ AI-Powered Learning
- Multiple-choice question generation
- Concept explanations with examples
- Adaptive difficulty adjustment

### ✅ Progress Tracking
- SQLite database persistence
- Performance analytics
- Weak area identification

### ✅ User Experience
- Session state caching (no repeated operations)
- Clear status messages
- Graceful shutdown option

---

## 🔧 Recent Improvements

- **Caching System**: Prevents repeated PDF extraction and API calls
- **Smart Chunk Selection**: Randomly selects content from middle sections
- **Database Reliability**: Added retry logic for concurrent access
- **Simplified Setup**: Auto-detects OpenRouter API configuration
- **Better UX**: Clear status messages and shutdown button

---

## ⭐ Advanced Features (Optional)

- Multiple learning styles
- Study schedule generator
- Spaced repetition
- Study groups collaboration

---

## 📝 Development Notes

### Database Schema
- Users, study materials, quizzes, questions, answers
- Progress tracking with timestamps
- Foreign key relationships for data integrity

### AI Integration
- OpenRouter API for flexible model selection
- Retry logic for API reliability
- Token optimization for cost efficiency

### Performance Optimizations
- Session state caching
- Chunk-based processing
- Database connection pooling

---

## ✅ Conclusion

This project demonstrates a practical AI-powered learning assistant using simple, modular architecture. It features intelligent content processing, reliable database operations, and a smooth user experience. The app is easy to deploy, scalable, and showcases real-world AI application development with modern web technologies.
