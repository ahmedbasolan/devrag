"""The app must be usable without an API key: that is the zero-cost promise."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).parent.parent / "src" / "app.py")


@pytest.fixture
def app(monkeypatch):
    for var in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    at = AppTest.from_file(APP, default_timeout=60)
    # Skip first-run indexing; these tests are about the key gate, not search.
    at.session_state["indexed"] = True
    at.session_state["chunk_count"] = 0
    return at.run()


def _button(at, label):
    return next(b for b in at.button if label in b.label)


def test_without_a_key_the_welcome_screen_is_shown(app):
    assert not app.exception
    assert len(app.chat_input) == 0
    assert _button(app, "Continue without AI")


def test_continue_without_ai_reaches_search(app):
    # It used to clear the key and rerun straight back onto the welcome screen.
    _button(app, "Continue without AI").click().run()
    assert not app.exception
    assert len(app.chat_input) == 1
    assert not any("Continue without AI" in b.label for b in app.button)
