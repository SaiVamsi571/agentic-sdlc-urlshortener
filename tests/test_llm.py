"""
Tests for LLM Client, Validation, Quota Handling, and Fallback Engine.
Validates OpenAI integration, key validation, error codes, and dynamic configuration.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import ASGITransport, AsyncClient

from src.constants import (
    AI_ENGINE_DETERMINISTIC,
    AI_ENGINE_OPENAI,
    DEFAULT_OPENAI_MODEL,
    ERROR_CODE_EMPTY_KEY,
    ERROR_CODE_INVALID_KEY,
    ERROR_CODE_QUOTA_EXHAUSTED,
    MSG_API_KEY_EMPTY,
    MSG_API_KEY_INVALID,
    MSG_QUOTA_EXHAUSTED,
)
from src.llm.client import LLMClient, validate_api_key
from src.web.server import dashboard_app


def test_llm_client_initialization_no_key(monkeypatch):
    """Verify that when no API key is provided, the client defaults safely to deterministic engine."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = LLMClient()
    assert client.is_enabled is False
    status = client.get_status()
    assert status["enabled"] is False
    assert status["engine"] == AI_ENGINE_DETERMINISTIC
    assert status["provider"] == "internal"


def test_llm_client_placeholder_key_ignored(monkeypatch):
    """Verify placeholder key from .env.example is treated as unconfigured."""
    monkeypatch.setenv("OPENAI_API_KEY", "your_openai_api_key_here")
    client = LLMClient()
    assert client.is_enabled is False


def test_llm_client_graceful_fallback_when_disabled(monkeypatch):
    """Verify text and JSON generation gracefully return None when disabled."""
    async def _inner():
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        client = LLMClient()
        
        text_res = await client.generate_text("System", "User")
        assert text_res is None

        json_res = await client.generate_json("System", "User")
        assert json_res is None

    asyncio.run(_inner())


def test_llm_client_with_mocked_openai_text(monkeypatch):
    """Verify that when OpenAI responds, generate_text returns valid content."""
    async def _inner():
        monkeypatch.setenv("OPENAI_API_KEY", "sk-mock-valid-key-for-testing")
        client = LLMClient()

        mock_choice = MagicMock()
        mock_choice.message.content = "OpenAI synthesized analysis."
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai = MagicMock()
        mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)
        client._client = mock_openai

        assert client.is_enabled is True
        res = await client.generate_text("System prompt", "User prompt")
        assert res == "OpenAI synthesized analysis."

    asyncio.run(_inner())


def test_llm_client_with_mocked_openai_json(monkeypatch):
    """Verify that generate_json parses structured outputs correctly."""
    async def _inner():
        monkeypatch.setenv("OPENAI_API_KEY", "sk-mock-valid-key-for-testing")
        client = LLMClient()

        mock_choice = MagicMock()
        mock_choice.message.content = '{"title": "Distributed Cache ADR", "decision": "Adopt Redis"}'
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai = MagicMock()
        mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)
        client._client = mock_openai

        res = await client.generate_json("System", "User")
        assert isinstance(res, dict)
        assert res["title"] == "Distributed Cache ADR"
        assert res["decision"] == "Adopt Redis"

    asyncio.run(_inner())


def test_llm_client_error_fallback(monkeypatch):
    """Verify that when OpenAI raises a network or API error, None is returned without crashing."""
    async def _inner():
        monkeypatch.setenv("OPENAI_API_KEY", "sk-mock-valid-key-for-testing")
        client = LLMClient()

        mock_openai = MagicMock()
        mock_openai.chat.completions.create = AsyncMock(side_effect=RuntimeError("OpenAI connection timed out"))
        client._client = mock_openai

        res = await client.generate_text("System", "User")
        assert res is None

    asyncio.run(_inner())


def test_validate_api_key_empty():
    """Verify empty or placeholder key returns error."""
    async def _inner():
        res1 = await validate_api_key("")
        assert res1["valid"] is False
        assert res1["error_code"] == ERROR_CODE_EMPTY_KEY

        res2 = await validate_api_key("your_openai_api_key_here")
        assert res2["valid"] is False
        assert res2["error_code"] == ERROR_CODE_EMPTY_KEY

    asyncio.run(_inner())


def test_validate_api_key_invalid():
    """Verify invalid key raising AuthenticationError returns INVALID_KEY."""
    async def _inner():
        from openai import AuthenticationError

        with patch("openai.AsyncOpenAI") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.models.list = AsyncMock(side_effect=AuthenticationError(
                message="Incorrect API key provided",
                response=MagicMock(status_code=401),
                body=None
            ))
            mock_cls.return_value = mock_inst

            res = await validate_api_key("sk-invalid-test-key")
            assert res["valid"] is False
            assert res["error_code"] == ERROR_CODE_INVALID_KEY
            assert res["message"] == MSG_API_KEY_INVALID

    asyncio.run(_inner())


def test_validate_api_key_quota_exhausted():
    """Verify quota exhausted error triggers QUOTA_EXHAUSTED."""
    async def _inner():
        from openai import RateLimitError

        with patch("openai.AsyncOpenAI") as mock_cls:
            mock_inst = MagicMock()
            
            # models.list succeeds
            m1 = MagicMock(); m1.id = "gpt-4o-mini"
            mock_models_resp = MagicMock()
            mock_models_resp.data = [m1]
            mock_inst.models.list = AsyncMock(return_value=mock_models_resp)

            # probe completion fails with quota error
            mock_inst.chat.completions.create = AsyncMock(side_effect=RateLimitError(
                message="You exceeded your current quota, please check your plan and billing details.",
                response=MagicMock(status_code=429),
                body=None
            ))
            mock_cls.return_value = mock_inst

            res = await validate_api_key("sk-valid-key-but-no-quota")
            assert res["valid"] is False
            assert res["error_code"] == ERROR_CODE_QUOTA_EXHAUSTED
            assert res["message"] == MSG_QUOTA_EXHAUSTED

    asyncio.run(_inner())


def test_validate_api_key_valid():
    """Verify valid key returns available models sorted correctly."""
    async def _inner():
        with patch("openai.AsyncOpenAI") as mock_cls:
            mock_inst = MagicMock()
            
            m1 = MagicMock(); m1.id = "gpt-4o"
            m2 = MagicMock(); m2.id = "gpt-4o-mini"
            m3 = MagicMock(); m3.id = "text-embedding-3-small"  # should be excluded
            mock_models_resp = MagicMock()
            mock_models_resp.data = [m1, m2, m3]
            mock_inst.models.list = AsyncMock(return_value=mock_models_resp)

            # Probe completion succeeds
            mock_choice = MagicMock()
            mock_choice.message.content = "pong"
            mock_resp = MagicMock()
            mock_resp.choices = [mock_choice]
            mock_inst.chat.completions.create = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_inst

            res = await validate_api_key("sk-fully-valid-key")
            assert res["valid"] is True
            assert res["error_code"] is None
            assert "gpt-4o-mini" in res["models"]
            assert "gpt-4o" in res["models"]
            assert "text-embedding-3-small" not in res["models"]

    asyncio.run(_inner())


def test_api_endpoint_llm_status():
    """Verify FastAPI endpoint GET /api/pipeline/llm-status returns valid structure."""
    async def _inner():
        transport = ASGITransport(app=dashboard_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/pipeline/llm-status")
            assert response.status_code == 200
            data = response.json()
            assert "enabled" in data
            assert "engine" in data
            assert "model" in data
            assert "provider" in data

    asyncio.run(_inner())


def test_api_endpoint_validate_key():
    """Verify FastAPI endpoint POST /api/pipeline/validate-llm-key rejects empty key."""
    async def _inner():
        transport = ASGITransport(app=dashboard_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/api/pipeline/validate-llm-key", json={"api_key": ""})
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert data["error_code"] == ERROR_CODE_EMPTY_KEY

    asyncio.run(_inner())


def test_api_endpoint_configure_llm_rejects_invalid():
    """Verify FastAPI endpoint POST /api/pipeline/configure-llm rejects invalid keys with 400."""
    async def _inner():
        transport = ASGITransport(app=dashboard_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/api/pipeline/configure-llm", json={"api_key": ""})
            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["valid"] is False
            assert data["detail"]["error_code"] == ERROR_CODE_EMPTY_KEY

    asyncio.run(_inner())
