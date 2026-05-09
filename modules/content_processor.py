"""
Content Processor Module
Handles extraction and preprocessing of study materials from PDFs and text.
"""

import os
import re
import pdfplumber
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Document:
    """Represents a processed document."""
    content: str
    metadata: Dict
    pages: List[str]


class ContentProcessor:
    """Processes study materials for AI analysis."""
    
    def __init__(self):
        self.max_chunk_size = 3000  # Characters per chunk for AI processing
        self.overlap_size = 200
    
    def extract_text_from_pdf(self, pdf_path: str) -> Document:
        """
        Extract text from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Document object with content and metadata
        """
        pages = []
        full_content = ""
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    pages.append(page_text)
                    full_content += page_text + "\n\n"
                    
                metadata = {
                    "filename": os.path.basename(pdf_path),
                    "total_pages": len(pdf.pages),
                    "extracted_at": str(__import__('datetime').datetime.now())
                }
                
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")
        
        return Document(
            content=full_content.strip(),
            metadata=metadata,
            pages=pages
        )
    
    def extract_text_from_txt(self, txt_path: str) -> Document:
        """
        Extract text from a plain text file.
        
        Args:
            txt_path: Path to the text file
            
        Returns:
            Document object with content and metadata
        """
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            metadata = {
                "filename": os.path.basename(txt_path),
                "total_pages": 1,
                "extracted_at": str(__import__('datetime').datetime.now())
            }
            
            return Document(
                content=content.strip(),
                metadata=metadata,
                pages=[content.strip()]
            )
            
        except Exception as e:
            raise Exception(f"Error reading text file: {str(e)}")
    
    def extract_text_from_input(self, text: str) -> Document:
        """
        Process text input directly.
        
        Args:
            text: The input text
            
        Returns:
            Document object with content and metadata
        """
        metadata = {
            "filename": "user_input",
            "total_pages": 1,
            "extracted_at": str(__import__('datetime').datetime.now())
        }
        
        return Document(
            content=text.strip(),
            metadata=metadata,
            pages=[text.strip()]
        )
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters (keep basic punctuation)
        text = re.sub(r'[^\w\s.,!?;:\'\"-]', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def chunk_text(self, text: str, chunk_size: int = None) -> List[str]:
        """
        Split text into manageable chunks for AI processing.
        
        Args:
            text: Text to chunk
            chunk_size: Maximum size of each chunk
            
        Returns:
            List of text chunks
        """
        if chunk_size is None:
            chunk_size = self.max_chunk_size
        
        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            
            if current_length + word_length > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
        
        # Add the last chunk if it exists
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def get_text_statistics(self, text: str) -> Dict:
        """
        Calculate text statistics.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with text statistics
        """
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        paragraphs = text.split('\n\n')
        
        return {
            "word_count": len(words),
            "sentence_count": len([s for s in sentences if s.strip()]),
            "paragraph_count": len([p for p in paragraphs if p.strip()]),
            "char_count": len(text),
            "avg_word_length": sum(len(w) for w in words) / len(words) if words else 0,
            "avg_sentence_length": len(words) / len([s for s in sentences if s.strip()]) if sentences else 0
        }
    
    def extract_key_terms(self, text: str, top_n: int = 10) -> List[str]:
        """
        Extract key terms from text (simple implementation).
        
        Args:
            text: Text to analyze
            top_n: Number of top terms to return
            
        Returns:
            List of key terms
        """
        # Common stop words to exclude
        stop_words = {
            'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
            'we', 'they', 'what', 'which', 'who', 'whom', 'whose', 'where',
            'when', 'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
            'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'just', 'don',
            'now', 'here', 'there', 'then', 'once', 'if', 'because', 'as', 'until',
            'while', 'about', 'against', 'between', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over',
            'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when',
            'where', 'why', 'how', 'each', 'few', 'more', 'most', 'other', 'some',
            'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
            'very', 's', 't', 'can', 'just', 'don', 'now'
        }
        
        # Count word frequencies
        word_counts = {}
        for word in text.lower().split():
            # Remove punctuation
            clean_word = re.sub(r'[^\w]', '', word)
            if clean_word and clean_word not in stop_words and len(clean_word) > 2:
                word_counts[clean_word] = word_counts.get(clean_word, 0) + 1
        
        # Get top N words
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:top_n]]


def process_file(file_path: str) -> Document:
    """
    Convenience function to process a file based on its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Document object with extracted content
    """
    processor = ContentProcessor()
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        return processor.extract_text_from_pdf(file_path)
    elif ext == '.txt':
        return processor.extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def process_text(text: str) -> Document:
    """
    Convenience function to process text directly.
    
    Args:
        text: Input text
        
    Returns:
        Document object with processed content
    """
    processor = ContentProcessor()
    return processor.extract_text_from_input(text)
