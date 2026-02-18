#server/assistant/processors/local_model.py
"""
Local Model Adapter - Groq API integration for fast LLM responses.
"""
import logging
import os
import time
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from threading import BoundedSemaphore

from django.conf import settings

from groq import Groq, RateLimitError

logger = logging.getLogger(__name__)


class NoModelAvailable(Exception):
    """Raised when no local model is available or LLM fails to initialize."""
    pass


class LocalModelAdapter:
    """
    Adapter for LLM generation using Groq API.
    Includes bulkhead, timeout guards, and deterministic error signaling.
    """

    _instance = None

    def __init__(self):
        """Initialize Groq client and concurrency controls."""
        self.client = None
        self.model_name = getattr(settings, 'GROQ_MODEL', 'llama-3.3-70b-versatile')
        self.is_initialized = False
        self.request_count = 0
        self.error_count = 0

        self.timeout_seconds = getattr(settings, 'GROQ_TIMEOUT_SECONDS', 8)
        self.bulkhead_limit = max(1, int(getattr(settings, 'GROQ_BULKHEAD_LIMIT', 16)))
        self.cooldown_seconds = int(getattr(settings, 'GROQ_RATE_LIMIT_COOLDOWN_SECONDS', 30))
        self.rate_limited_until = 0.0

        self._bulkhead = BoundedSemaphore(self.bulkhead_limit)
        self._executor = ThreadPoolExecutor(max_workers=self.bulkhead_limit)

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
            api_key = getattr(settings, 'GROQ_API_KEY', None) or os.environ.get('GROQ_API_KEY')

            if not api_key:
                logger.warning("GROQ_API_KEY not found in environment variables")
                logger.warning("LLM will not be available. Set GROQ_API_KEY to enable.")
                return

            self.client = Groq(api_key=api_key)
            self.is_initialized = True

            logger.info("✅ Groq LLM initialized successfully")
            logger.info(f"   Model: {self.model_name}")
            logger.info("   Free tier: 30 req/min, 14,400 req/day")

        except Exception as e:
            logger.error(f"Failed to initialize Groq: {e}")
            self.client = None
            self.is_initialized = False

    def is_available(self) -> bool:
        """Check if LLM is available and not in cooldown."""
        return self.is_initialized and self.client is not None and time.time() >= self.rate_limited_until

    def _build_messages(self, prompt: str, system_prompt: Optional[str]):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _call_groq(self, *, prompt: str, max_tokens: int, temperature: float, system_prompt: Optional[str]):
        messages = self._build_messages(prompt, system_prompt)
        return self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def _error_result(self, *, code: str, generation_time: float = 0.0, message: str = '') -> Dict:
        return {
            'response': '',
            'tokens_generated': 0,
            'generation_time': generation_time,
            'model': self.model_name if self.model_name else 'none',
            'error': code,
            'error_message': message,
        }

    def generate(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.3,
        system_prompt: Optional[str] = None
    ) -> Dict:
        """Generate response using Groq API with scalability guards."""
        if not self.is_initialized or self.client is None:
            return self._error_result(code='unavailable', message='LLM not initialized')

        now = time.time()
        if now < self.rate_limited_until:
            return self._error_result(code='rate_limit_cooldown', message='LLM temporarily cooling down')

        start_time = time.time()
        acquired = self._bulkhead.acquire(blocking=False)
        if not acquired:
            self.error_count += 1
            return self._error_result(code='overloaded', generation_time=time.time() - start_time, message='LLM concurrency limit reached')

        try:
            future = self._executor.submit(
                self._call_groq,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                system_prompt=system_prompt,
            )

            try:
                response = future.result(timeout=self.timeout_seconds)
            except FutureTimeoutError:
                self.error_count += 1
                return self._error_result(code='timeout', generation_time=time.time() - start_time, message='LLM request timed out')

            generated_text = response.choices[0].message.content if response.choices else ''
            tokens_used = response.usage.total_tokens if response.usage else 0

            generation_time = time.time() - start_time
            self.request_count += 1

            logger.info(f"✅ Groq generation successful ({generation_time:.2f}s, {tokens_used} tokens)")

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
            self.rate_limited_until = time.time() + self.cooldown_seconds
            return self._error_result(
                code='rate_limit',
                generation_time=time.time() - start_time,
                message='Rate limit exceeded',
            )

        except Exception as e:
            logger.error(f"❌ Groq generation failed: {e}")
            self.error_count += 1
            return self._error_result(
                code='provider_error',
                generation_time=time.time() - start_time,
                message=str(e),
            )
        finally:
            self._bulkhead.release()

    def get_model_info(self) -> Dict:
        """Get model information."""
        return {
            'model_type': 'groq',
            'model_name': self.model_name,
            'available': self.is_available(),
            'request_count': self.request_count,
            'error_count': self.error_count,
            'free_tier_limit': '30 req/min, 14,400 req/day',
            'bulkhead_limit': self.bulkhead_limit,
            'timeout_seconds': self.timeout_seconds,
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
            'estimated_daily_usage': self.request_count,
            'free_tier_remaining': max(0, 14400 - self.request_count),
            'rate_limited_until': self.rate_limited_until,
        }
