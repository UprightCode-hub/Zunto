"""
Local Model Adapter - Now using Groq API for fast LLM responses
"""
import logging
import os
import time
from typing import Dict, Optional
from django.conf import settings

from groq import Groq, RateLimitError

logger = logging.getLogger(__name__)

class NoModelAvailable(Exception):
    """Raised when no local model is available or LLM fails to initialize."""
    pass


class LocalModelAdapter:
    """
    Adapter for LLM generation using Groq API.
    Fast, free tier available, with automatic fallback.
    """
    
    _instance = None
    
    def __init__(self):
        """Initialize Groq client."""
        self.client = None
        self.model_name = getattr(settings, 'GROQ_MODEL', 'llama-3.3-70b-versatile')
        self.is_initialized = False
        self.request_count = 0  # Track usage
        self.error_count = 0
        
        self._initialize_groq()
    
    @classmethod
    def get_instance(cls):
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _initialize_groq(self):
        """Initialize Groq API client."""
        try:
            # Get API key from environment variable
            api_key = getattr(settings, 'GROQ_API_KEY', None) or os.environ.get('GROQ_API_KEY')
            
            if not api_key:
                logger.warning("GROQ_API_KEY not found in environment variables")
                logger.warning("LLM will not be available. Set GROQ_API_KEY to enable.")
                return
            
            # Initialize client
            self.client = Groq(api_key=api_key)
            self.is_initialized = True
            
            logger.info(f"✅ Groq LLM initialized successfully")
            logger.info(f"   Model: {self.model_name}")
            logger.info(f"   Free tier: 30 req/min, 14,400 req/day")
            
        except Exception as e:
            logger.error(f"Failed to initialize Groq: {e}")
            self.client = None
            self.is_initialized = False
    
    def is_available(self) -> bool:
        """Check if LLM is available."""
        return self.is_initialized and self.client is not None
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.3,
        system_prompt: Optional[str] = None
    ) -> Dict:
        """
        Generate response using Groq API.
        
        Args:
            prompt: User query or prompt
            max_tokens: Maximum tokens to generate
            temperature: Creativity (0.0 = focused, 1.0 = creative)
            system_prompt: Optional system instructions
        
        Returns:
            {
                'response': str,
                'tokens_generated': int,
                'generation_time': float,
                'model': str,
                'error': Optional[str]
            }
        """
        if not self.is_available():
            return {
                'response': '',
                'tokens_generated': 0,
                'generation_time': 0.0,
                'model': 'none',
                'error': 'LLM not initialized'
            }
        
        start_time = time.time()
        
        try:
            # Build messages
            messages = []
            
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # Call Groq API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            # Extract response
            generated_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            generation_time = time.time() - start_time
            
            # Track usage
            self.request_count += 1
            
            logger.info(f"✅ Groq generation successful ({generation_time:.2f}s, {tokens_used} tokens)")
            logger.debug(f"   Total requests this session: {self.request_count}")
            
            return {
                'response': generated_text,
                'tokens_generated': tokens_used,
                'generation_time': generation_time,
                'model': self.model_name,
                'error': None
            }
        
        except RateLimitError as e:
            logger.warning(f"⚠️ Groq rate limit exceeded: {e}")
            self.error_count += 1
            
            return {
                'response': '',
                'tokens_generated': 0,
                'generation_time': time.time() - start_time,
                'model': self.model_name,
                'error': 'rate_limit'
            }
        
        except Exception as e:
            logger.error(f"❌ Groq generation failed: {e}")
            self.error_count += 1
            
            return {
                'response': '',
                'tokens_generated': 0,
                'generation_time': time.time() - start_time,
                'model': self.model_name,
                'error': str(e)
            }
    
    def get_model_info(self) -> Dict:
        """Get model information."""
        return {
            'model_type': 'groq',
            'model_name': self.model_name,
            'available': self.is_available(),
            'request_count': self.request_count,
            'error_count': self.error_count,
            'free_tier_limit': '30 req/min, 14,400 req/day'
        }
    
    def get_usage_stats(self) -> Dict:
        """Get usage statistics for monitoring."""
        return {
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'success_rate': (
                (self.request_count - self.error_count) / self.request_count * 100
                if self.request_count > 0 else 0
            ),
            'estimated_daily_usage': self.request_count,  # Rough estimate
            'free_tier_remaining': max(0, 14400 - self.request_count)
        }