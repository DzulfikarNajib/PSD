"""Global test fixtures and environment configuration."""

import pytest


@pytest.fixture(autouse=True)
def disable_network_defaults(monkeypatch):
    """Default to offline local storage for tests unless explicitly overridden."""
    monkeypatch.setenv("AUTOMATCH_OFFLINE", "1")
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "")
