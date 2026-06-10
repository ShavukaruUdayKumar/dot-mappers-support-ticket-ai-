"""LLM service using Groq API."""
import json
import logging
import re
from typing import Optional
from groq import Groq

from app.core.config import get_settings
from app.core.exceptions import LLMError

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with Groq LLM."""
    
    def __init__(self):
        self.settings = get_settings()
        try:
            self.client = Groq(api_key=self.settings.groq_api_key)
            logger.info("LLM service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {str(e)}")
            raise LLMError(f"LLM initialization failed: {str(e)}")
        
        self.call_count = 0
    
    def chat(
        self, 
        system_prompt: str, 
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Send chat completion request to LLM.
        
        Args:
            system_prompt: System context
            user_prompt: User message
            temperature: Sampling temperature (default from config)
            max_tokens: Max tokens to generate (default from config)
            
        Returns:
            LLM response text
            
        Raises:
            LLMError: If API call fails
        """
        try:
            self.call_count += 1
            
            response = self.client.chat.completions.create(
                model=self.settings.groq_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature or self.settings.groq_temperature,
                max_tokens=max_tokens or self.settings.groq_max_tokens
            )
            
            result = response.choices[0].message.content
            logger.debug(f"LLM call #{self.call_count} completed")
            
            return result
            
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            raise LLMError(f"LLM API error: {str(e)}")
    
    def extract_json(self, text: str) -> dict:
        """
        Extract JSON from LLM response that may contain markdown or text.
        
        Args:
            text: LLM response text
            
        Returns:
            Parsed JSON object
            
        Raises:
            LLMError: If JSON extraction fails
        """
        try:
            # Try direct parse first
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
            
            # Extract from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Extract standalone JSON object
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            
            raise LLMError("No valid JSON found in response")
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            raise LLMError(f"Invalid JSON in LLM response: {str(e)}")
    
    def get_call_count(self) -> int:
        """Get total number of LLM calls made."""
        return self.call_count
    
    def reset_call_count(self):
        """Reset call counter."""
        self.call_count = 0


# Global instance
llm_service = LLMService()
