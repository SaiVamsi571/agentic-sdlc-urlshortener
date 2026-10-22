"""
OpenAI LLM Integration Client.
Provides async text and structured generation with automatic fallback to deterministic simulation.
"""
import os
import json
import logging
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from src.constants import (
    AI_ENGINE_DETERMINISTIC,
    AI_ENGINE_OPENAI,
    DEFAULT_OPENAI_MODEL,
    ENV_OPENAI_API_KEY,
    ENV_OPENAI_MODEL,
    MSG_LLM_FALLBACK,
    MSG_LLM_INITIALIZED,
)

logger = logging.getLogger("aethersdlc.llm")

# Load environment variables from .env if present
load_dotenv()


class LLMClient:
    """Manages LLM interactions with OpenAI and graceful fallback."""

    def __init__(self):
        self.api_key: Optional[str] = os.getenv(ENV_OPENAI_API_KEY)
        self.model: str = os.getenv(ENV_OPENAI_MODEL, DEFAULT_OPENAI_MODEL)
        self._client = None

        # Check if a valid, non-placeholder key is provided
        if self.api_key and not self.api_key.strip().startswith("your_"):
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key.strip())
                logger.info(MSG_LLM_INITIALIZED.format(model=self.model))
            except Exception as e:
                logger.warning(f"{MSG_LLM_FALLBACK}: {str(e)}")
                self._client = None
        else:
            logger.info(MSG_LLM_FALLBACK)

    @property
    def is_enabled(self) -> bool:
        """Returns True if the OpenAI client is configured and ready."""
        return self._client is not None

    def get_status(self) -> Dict[str, Any]:
        """Returns current engine status for API diagnostics and web UI."""
        return {
            "enabled": self.is_enabled,
            "engine": AI_ENGINE_OPENAI if self.is_enabled else AI_ENGINE_DETERMINISTIC,
            "model": self.model if self.is_enabled else "N/A (Deterministic)",
            "provider": "openai" if self.is_enabled else "internal",
        }

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 2500,
    ) -> Optional[str]:
        """
        Generate text completion via OpenAI.
        Returns None on any error to allow the caller to fall back seamlessly.
        """
        if not self.is_enabled:
            return None

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            return content.strip() if content else None
        except Exception as e:
            logger.warning(f"OpenAI call failed ({str(e)}). Falling back to deterministic output.")
            return None

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate structured JSON output via OpenAI.
        Returns None on any error to allow caller fallback.
        """
        if not self.is_enabled:
            return None

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
            )
            raw = response.choices[0].message.content
            if raw:
                return json.loads(raw)
            return None
        except Exception as e:
            logger.warning(f"OpenAI JSON generation failed ({str(e)}). Falling back to deterministic output.")
            return None


# Global singleton instance
_llm_instance: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Returns singleton instance of LLMClient, refreshing if environment changed."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMClient()
    return _llm_instance


def reload_llm_client() -> LLMClient:
    """Force reloads configuration from environment (.env)."""
    global _llm_instance
    load_dotenv(override=True)
    _llm_instance = LLMClient()
    return _llm_instance
