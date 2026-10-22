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
    ERROR_CODE_EMPTY_KEY,
    ERROR_CODE_INVALID_KEY,
    ERROR_CODE_NETWORK_ERROR,
    ERROR_CODE_QUOTA_EXHAUSTED,
    MSG_API_KEY_EMPTY,
    MSG_API_KEY_INVALID,
    MSG_API_KEY_VALIDATED,
    MSG_LLM_FALLBACK,
    MSG_LLM_INITIALIZED,
    MSG_QUOTA_EXHAUSTED,
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


def reset_to_deterministic() -> Dict[str, Any]:
    """Force reset the LLM client to disabled state (Deterministic Simulation Engine)."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMClient()
    _llm_instance._client = None
    return _llm_instance.get_status()


async def validate_api_key(api_key: str) -> Dict[str, Any]:
    """
    Validates an OpenAI API key against the OpenAI API.
    1. Checks if empty/placeholder.
    2. Calls models.list() to verify key validity.
    3. Performs a lightweight completion probe to verify billing quota status.
    4. Filters and returns available chat models.
    """
    clean_key = api_key.strip() if api_key else ""
    if not clean_key or clean_key.startswith("your_"):
        return {
            "valid": False,
            "error_code": ERROR_CODE_EMPTY_KEY,
            "message": MSG_API_KEY_EMPTY,
            "models": [],
        }

    try:
        from openai import AsyncOpenAI, AuthenticationError, RateLimitError
    except ImportError:
        return {
            "valid": False,
            "error_code": ERROR_CODE_NETWORK_ERROR,
            "message": "OpenAI library is not installed.",
            "models": [],
        }

    client = AsyncOpenAI(api_key=clean_key)

    # Step 1: Validate key authenticity and list models
    try:
        model_list_resp = await client.models.list()
    except AuthenticationError:
        return {
            "valid": False,
            "error_code": ERROR_CODE_INVALID_KEY,
            "message": MSG_API_KEY_INVALID,
            "models": [],
        }
    except RateLimitError as e:
        err_msg = str(e).lower()
        if "quota" in err_msg or "insufficient" in err_msg or "billing" in err_msg:
            return {
                "valid": False,
                "error_code": ERROR_CODE_QUOTA_EXHAUSTED,
                "message": MSG_QUOTA_EXHAUSTED,
                "models": [],
            }
        return {
            "valid": False,
            "error_code": ERROR_CODE_NETWORK_ERROR,
            "message": str(e),
            "models": [],
        }
    except Exception as e:
        err_str = str(e).lower()
        if "401" in err_str or "incorrect api key" in err_str or "invalid" in err_str:
            return {
                "valid": False,
                "error_code": ERROR_CODE_INVALID_KEY,
                "message": MSG_API_KEY_INVALID,
                "models": [],
            }
        return {
            "valid": False,
            "error_code": ERROR_CODE_NETWORK_ERROR,
            "message": f"Connection error: {str(e)}",
            "models": [],
        }

    # Filter chat-capable models
    available_models = []
    preferred_order = [
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
        "o1-mini",
        "o1-preview",
        "o3-mini",
    ]

    raw_ids = set()
    if hasattr(model_list_resp, "data"):
        raw_ids = {m.id for m in model_list_resp.data if hasattr(m, "id")}

    # Priority list
    for pref in preferred_order:
        if pref in raw_ids:
            available_models.append(pref)

    # Any other gpt or o1/o3 models
    for m_id in sorted(raw_ids):
        if (m_id.startswith("gpt-") or m_id.startswith("o1-") or m_id.startswith("o3-")) and m_id not in available_models:
            if not any(excluded in m_id for excluded in ["embed", "audio", "realtime", "tts", "whisper", "search"]):
                available_models.append(m_id)

    if not available_models:
        available_models = [DEFAULT_OPENAI_MODEL]

    # Step 2: Quota probe using the first available model
    probe_model = available_models[0]
    try:
        await client.chat.completions.create(
            model=probe_model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
    except RateLimitError as e:
        err_msg = str(e).lower()
        if "quota" in err_msg or "insufficient" in err_msg or "billing" in err_msg:
            return {
                "valid": False,
                "error_code": ERROR_CODE_QUOTA_EXHAUSTED,
                "message": MSG_QUOTA_EXHAUSTED,
                "models": available_models,
            }
    except Exception as e:
        err_msg = str(e).lower()
        if "insufficient_quota" in err_msg or "exceeded your current quota" in err_msg:
            return {
                "valid": False,
                "error_code": ERROR_CODE_QUOTA_EXHAUSTED,
                "message": MSG_QUOTA_EXHAUSTED,
                "models": available_models,
            }
        if "401" in err_msg or "invalid_api_key" in err_msg:
            return {
                "valid": False,
                "error_code": ERROR_CODE_INVALID_KEY,
                "message": MSG_API_KEY_INVALID,
                "models": [],
            }

    return {
        "valid": True,
        "error_code": None,
        "message": MSG_API_KEY_VALIDATED,
        "models": available_models,
        "default_model": probe_model,
    }
