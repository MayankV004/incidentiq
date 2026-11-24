import os

import pytest

_LIVE_SECRET_ENV_VARS = (
    "GROQ_API_KEY",
    "LLM_API_KEY_PRIMARY",
    "LLM_API_KEY_FALLBACK",
    "LLM_API_KEY_JUDGE",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "OPENROUTER_API_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
)

# Provide offline fake defaults for test collection when no .env file is present.
os.environ.setdefault("API_KEY", "test_fake_api_key_for_pytest")
os.environ.setdefault("APPROVAL_TOKEN_SECRET", "test_fake_approval_secret_for_pytest")


@pytest.fixture(autouse=True)
def _force_offline_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent accidental live LLM or Langfuse calls during pytest even if .env is loaded."""
    for var in _LIVE_SECRET_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
