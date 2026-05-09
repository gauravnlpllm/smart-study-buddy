"""
Explanation Module
Generates explanations for concepts and answers.
"""

import os
import re
import json
from typing import List, Dict, Optional
from dataclasses import dataclass

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


@dataclass
class Explanation:
    """Represents an explanation for a concept or answer."""
    concept: str
    explanation_text: str
    examples: List[str]
    analogies: List[str]
    related_concepts: List[str]


class ExplanationGenerator:
    """Generates explanations for concepts and answers."""
    
    def __init__(self, api_key: str = None, api_type: str = "openai"):
        """
        Initialize the explanation generator.
        
        Args:
            api_key: API key for the AI service
            api_type: Type of API to use ("openai", "openrouter", or "gemini")
        """
        self.api_key = api_key or os.environ.get('AI_API_KEY')
        self.api_type = (api_type or "openai").lower()
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
    
    def generate_explanation(self, concept: str, context: str = None) -> Explanation:
        """
        Generate an explanation for a concept.
        
        Args:
            concept: The concept to explain
            context: Additional context from study material
            
        Returns:
            Explanation object with detailed explanation
        """
        prompt = self._build_explanation_prompt(concept, context)
        
        try:
            if self.api_type in ("openai", "openrouter") and OPENAI_AVAILABLE:
                response = self._call_openai(prompt)
            elif self.api_type == "gemini" and GEMINI_AVAILABLE:
                response = self._call_gemini(prompt)
            else:
                return self._generate_mock_explanation(concept)
            
            return self._parse_explanation(response, concept)
            
        except Exception as e:
            print(f"Error generating explanation: {e}")
            return self._generate_mock_explanation(concept)
    
    def generate_answer_explanation(self, question: str, correct_answer: str,
                                    user_answer: str = None) -> Explanation:
        """
        Generate an explanation for an answer.
        
        Args:
            question: The question being answered
            correct_answer: The correct answer
            user_answer: The user's answer (optional)
            
        Returns:
            Explanation object with answer explanation
        """
        context = f"Question: {question}\nCorrect Answer: {correct_answer}"
        if user_answer:
            context += f"\nUser Answer: {user_answer}"
        
        return self.generate_explanation("Answer Explanation", context)
    
    def _build_explanation_prompt(self, concept: str, context: str = None) -> str:
        """Build the prompt for explanation generation."""
        prompt = f"""You are a patient and skilled tutor. Explain the following concept 
in a clear, easy-to-understand way.

Concept: {concept}
"""
        
        if context:
            prompt += f"""
Additional Context:
{context}
"""
        
        prompt += """
Instructions:
1. Start with a simple, clear definition
2. Provide 2-3 real-world examples
3. Break down complex ideas into smaller parts
4. Use analogies to help understanding
5. List related concepts
6. Keep the explanation concise but thorough

Format your response as a JSON object:
{{
    "concept": "Concept name",
    "explanation": "Clear explanation text",
    "examples": ["Example 1", "Example 2", "Example 3"],
    "analogies": ["Analogy 1", "Analogy 2"],
    "related_concepts": ["Related concept 1", "Related concept 2"]
}}
"""
        
        return prompt
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI-compatible API (OpenAI or OpenRouter)."""
        try:
            extra_headers = {}
            if self.api_type == "openrouter":
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
                    {"role": "system", "content": "You are a helpful tutor that explains concepts clearly. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500,
                extra_headers=extra_headers or None,
            )

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
    
    def _parse_explanation(self, response: str, concept: str) -> Explanation:
        """Parse AI response and extract explanation data."""
        if not response:
            return self._generate_mock_explanation(concept)

        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return Explanation(
                    concept=concept,
                    explanation_text=data.get('explanation', ''),
                    examples=data.get('examples', []),
                    analogies=data.get('analogies', []),
                    related_concepts=data.get('related_concepts', [])
                )
        except json.JSONDecodeError:
            pass

        # Fallback parsing
        return self._parse_explanation_fallback(response, concept)
    
    def _parse_explanation_fallback(self, response: str, concept: str) -> Explanation:
        """Fallback method to parse explanation if JSON parsing fails."""
        explanation_text = response
        examples = []
        analogies = []
        related_concepts = []
        
        # Try to extract examples
        example_matches = re.findall(r'Example[:\s]+(.+?)(?:\n|$)', response, re.IGNORECASE)
        examples = [e.strip() for e in example_matches[:3]]
        
        # Try to extract analogies
        analogy_matches = re.findall(r'Analogy[:\s]+(.+?)(?:\n|$)', response, re.IGNORECASE)
        analogies = [a.strip() for a in analogy_matches[:2]]
        
        return Explanation(
            concept=concept,
            explanation_text=explanation_text,
            examples=examples,
            analogies=analogies,
            related_concepts=related_concepts
        )
    
    def _generate_mock_explanation(self, concept: str) -> Explanation:
        """Generate a mock explanation when API is unavailable."""
        return Explanation(
            concept=concept,
            explanation_text=f"This is a mock explanation for the concept: {concept}. "
                           f"In a real application, this would be generated by an AI model "
                           f"providing detailed information about this topic.",
            examples=[
                f"For example, {concept} can be seen in real-world applications where "
                f"similar principles are applied.",
                f"Another example would be when {concept} is used in practical scenarios."
            ],
            analogies=[
                f"Think of {concept} like a building block - it's a fundamental part of "
                f"understanding more complex ideas.",
                f"Just like learning to walk before running, {concept} is the foundation "
                f"for more advanced topics."
            ],
            related_concepts=["Related Topic 1", "Related Topic 2", "Related Topic 3"]
        )
    
    def generate_multiple_explanations(self, concepts: List[str], 
                                       context: str = None) -> List[Explanation]:
        """
        Generate explanations for multiple concepts.
        
        Args:
            concepts: List of concepts to explain
            context: Additional context
            
        Returns:
            List of Explanation objects
        """
        return [self.generate_explanation(concept, context) for concept in concepts]


def generate_explanation(concept: str, context: str = None,
                         api_key: str = None, api_type: str = "openai") -> Explanation:
    """
    Convenience function to generate an explanation.
    
    Args:
        concept: The concept to explain
        context: Additional context
        api_key: API key for AI service
        api_type: Type of API to use
        
    Returns:
        Explanation object
    """
    generator = ExplanationGenerator(api_key=api_key, api_type=api_type)
    return generator.generate_explanation(concept, context)
