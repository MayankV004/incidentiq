import os

# Provide offline fake defaults for test collection when no .env file is present.
# Tests that explicitly verify missing-secret fail-fast behavior use monkeypatch.delenv().
os.environ.setdefault("API_KEY", "test_fake_api_key_for_pytest")
os.environ.setdefault("APPROVAL_TOKEN_SECRET", "test_fake_approval_secret_for_pytest")
