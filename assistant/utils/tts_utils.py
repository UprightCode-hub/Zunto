"""
TTS Utilities - Groq TTS API Integration with Caching
Handles text-to-speech generation for assistant responses.
Created by Wisdom Ekwugha
"""
import os
import hashlib
import logging
import requests
from typing import Optional, Dict, Tuple
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class GroqTTSService:
    """Service for handling Groq TTS API calls with intelligent caching."""
    
    # Voice mapping: Map common voice names to Groq PlayAI voices
    VOICE_MAPPING = {
        "alloy": "Jennifer-PlayAI",      # Female, friendly
        "echo": "Angelo-PlayAI",          # Male, neutral
        "fable": "Eleanor-PlayAI",        # Female, expressive
        "onyx": "Cillian-PlayAI",         # Male, deep
        "nova": "Ruby-PlayAI",            # Female, warm
        "shimmer": "Adelaide-PlayAI",     # Female, bright
        # Direct Groq voices also supported
        "jennifer": "Jennifer-PlayAI",
        "angelo": "Angelo-PlayAI",
        "eleanor": "Eleanor-PlayAI",
        "ruby": "Ruby-PlayAI",
        "adelaide": "Adelaide-PlayAI",
        "celeste": "Celeste-PlayAI",
        "gail": "Gail-PlayAI",
        "judy": "Judy-PlayAI",
        "nia": "Nia-PlayAI",
        "cillian": "Cillian-PlayAI",
        "calum": "Calum-PlayAI",
        "mason": "Mason-PlayAI",
        "mitch": "Mitch-PlayAI",
        "thunder": "Thunder-PlayAI",
    }
    
    # All available Groq PlayAI voices
    AVAILABLE_VOICES = [
        "Aaliyah-PlayAI", "Adelaide-PlayAI", "Angelo-PlayAI", "Arista-PlayAI",
        "Atlas-PlayAI", "Basil-PlayAI", "Briggs-PlayAI", "Calum-PlayAI",
        "Celeste-PlayAI", "Cheyenne-PlayAI", "Chip-PlayAI", "Cillian-PlayAI",
        "Deedee-PlayAI", "Eleanor-PlayAI", "Fritz-PlayAI", "Gail-PlayAI",
        "Indigo-PlayAI", "Jennifer-PlayAI", "Judy-PlayAI", "Mamaw-PlayAI",
        "Mason-PlayAI", "Mikail-PlayAI", "Mitch-PlayAI", "Nia-PlayAI",
        "Quinn-PlayAI", "Ruby-PlayAI", "Thunder-PlayAI"
    ]
    
    def __init__(self):
        self.api_key = getattr(settings, 'GROQ_API_KEY', os.environ.get('GROQ_API_KEY'))
        self.api_url = "https://api.groq.com/openai/v1/audio/speech"
        self.model = "playai-tts"
        self.voice = "Jennifer-PlayAI"  # Default Groq voice (friendly female)
        self.response_format = "mp3"  # mp3, opus, aac, flac, wav, pcm
        self.speed = 1.0  # 0.25 to 4.0
        self.cache_timeout = 3600 * 24 * 7  # 7 days for audio files
        
        if not self.api_key:
            logger.error("GROQ_API_KEY not found in environment variables!")
    
    def _normalize_voice(self, voice: Optional[str]) -> str:
        """
        Normalize voice name to Groq PlayAI format.
        Supports both OpenAI-style names and Groq native names.
        """
        if not voice:
            return self.voice
        
        voice_lower = voice.lower().strip()
        
        # Check if it's in the mapping
        if voice_lower in self.VOICE_MAPPING:
            return self.VOICE_MAPPING[voice_lower]
        
        # Check if it's already a valid Groq voice
        if voice in self.AVAILABLE_VOICES:
            return voice
        
        # Try to find a case-insensitive match
        for available_voice in self.AVAILABLE_VOICES:
            if available_voice.lower() == voice_lower or \
               available_voice.lower().replace("-playai", "") == voice_lower:
                return available_voice
        
        # Fallback to default
        logger.warning(f"Unknown voice '{voice}', using default: {self.voice}")
        return self.voice
    
    def _get_cache_key(self, text: str, voice: str = None, speed: float = None) -> str:
        """Generate a unique cache key based on text, voice, and speed."""
        voice = self._normalize_voice(voice)
        speed = speed or self.speed
        content = f"{text}:{voice}:{speed}:{self.model}"
        return f"tts_audio:{hashlib.md5(content.encode()).hexdigest()}"
    
    def generate_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        use_cache: bool = True
    ) -> Tuple[bool, Optional[bytes], Optional[str]]:
        """
        Generate speech from text using Groq TTS API.
        
        Args:
            text: Text to convert to speech
            voice: Voice to use (supports OpenAI names or Groq PlayAI names)
            speed: Speech speed 0.25-4.0 (default: 1.0)
            use_cache: Whether to use cached audio (default: True)
        
        Returns:
            Tuple of (success, audio_bytes, error_message)
        """
        # Validate input
        if not text or not text.strip():
            return False, None, "Empty text provided"
        
        if not self.api_key:
            return False, None, "Groq API key not configured"
        
        # Sanitize text (remove excessive whitespace)
        text = " ".join(text.split())
        
        # Limit text length to avoid rate limits (Groq free tier)
        if len(text) > 4000:
            logger.warning(f"Text too long ({len(text)} chars), truncating to 4000")
            text = text[:3997] + "..."
        
        # Normalize voice to Groq format
        normalized_voice = self._normalize_voice(voice)
        
        # Check cache first
        cache_key = self._get_cache_key(text, normalized_voice, speed)
        if use_cache:
            cached_audio = cache.get(cache_key)
            if cached_audio:
                logger.info(f"Cache HIT for text: {text[:50]}...")
                return True, cached_audio, None
        
        # Prepare API request
        speed = speed or self.speed
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "input": text,
            "voice": normalized_voice,
            "response_format": self.response_format,
            "speed": speed
        }
        
        try:
            logger.info(f"Generating TTS for: {text[:50]}... (voice={normalized_voice}, speed={speed})")
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=15  # 15 second timeout
            )
            
            # Check for errors
            if response.status_code != 200:
                error_msg = self._parse_error(response)
                logger.error(f"Groq TTS API error {response.status_code}: {error_msg}")
                return False, None, error_msg
            
            # Get audio bytes
            audio_bytes = response.content
            
            if not audio_bytes:
                return False, None, "Empty audio response from API"
            
            # Cache the audio
            if use_cache:
                cache.set(cache_key, audio_bytes, self.cache_timeout)
                logger.info(f"Cached audio for: {text[:50]}...")
            
            logger.info(f"TTS generated successfully ({len(audio_bytes)} bytes)")
            return True, audio_bytes, None
        
        except requests.exceptions.Timeout:
            logger.error("Groq TTS API timeout")
            return False, None, "Request timeout - please try again"
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return False, None, f"Network error: {str(e)}"
        
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return False, None, f"Unexpected error: {str(e)}"
    
    def _parse_error(self, response: requests.Response) -> str:
        """Parse error message from API response."""
        try:
            error_data = response.json()
            error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            return error_msg
        except:
            return response.text or f"HTTP {response.status_code}"
    
    def get_available_voices(self) -> list:
        """Get list of all available Groq PlayAI voices."""
        return self.AVAILABLE_VOICES.copy()
    
    def get_voice_mapping(self) -> dict:
        """Get the voice name mapping for reference."""
        return self.VOICE_MAPPING.copy()
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics for monitoring."""
        return {
            'cache_timeout_seconds': self.cache_timeout,
            'cache_enabled': True,
            'model': self.model,
            'default_voice': self.voice,
            'available_voices': len(self.AVAILABLE_VOICES),
            'voice_mappings': len(self.VOICE_MAPPING)
        }
    
    def clear_cache(self, text: Optional[str] = None):
        """
        Clear cached audio.
        
        Args:
            text: If provided, clear only this text. Otherwise clear all TTS cache.
        """
        if text:
            cache_key = self._get_cache_key(text)
            cache.delete(cache_key)
            logger.info(f"Cleared cache for: {text[:50]}...")
        else:
            # Note: Django cache doesn't support wildcard delete easily
            # You'd need to track keys separately for this
            logger.warning("Full cache clear not implemented - clear specific texts instead")


# Singleton instance
_tts_service_instance = None


def get_tts_service() -> GroqTTSService:
    """Get singleton TTS service instance."""
    global _tts_service_instance
    if _tts_service_instance is None:
        _tts_service_instance = GroqTTSService()
    return _tts_service_instance


# Convenience function
def text_to_speech(
    text: str,
    voice: Optional[str] = None,
    speed: Optional[float] = None,
    use_cache: bool = True
) -> Tuple[bool, Optional[bytes], Optional[str]]:
    """
    Quick text-to-speech conversion.
    
    Args:
        text: Text to convert to speech
        voice: Voice name (supports both OpenAI and Groq formats)
        speed: Speech speed (0.25 to 4.0)
        use_cache: Whether to use cached audio
    
    Returns:
        Tuple of (success, audio_bytes, error_message)
    """
    service = get_tts_service()
    return service.generate_speech(text, voice, speed, use_cache)