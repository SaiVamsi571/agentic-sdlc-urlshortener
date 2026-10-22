"""
Tests for LLM Client and Fallback Engine.
Validates OpenAI integration, fallback resilience, and dynamic configuration.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock
from httpx import ASGITransport, AsyncClient

from src.constants import (
    AI_ENGINE_DETERMINISTIC,
    AI_ENGINE_OPENAI,
    DEFAULT_OPENAI_MODEL,
)
from src.llm.client import LLMClient
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
