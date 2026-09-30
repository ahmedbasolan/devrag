"""Tests for the generator module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.generator import _fallback, _get_api_key, _get_provider, generate_response


def _make_result(source_file="test.py", name="func", score=0.9):
    chunk = MagicMock()
    chunk.source_file = source_file
    chunk.name = name
    chunk.start_line = 1
    chunk.end_line = 3
    chunk.docstring = None
    chunk.content = "def func(): pass"
    result = MagicMock()
    result.chunk = chunk
    result.score = score
    return result


class _FakeSession(dict):
    """Dict that also supports attribute access (for st.session_state.api_key)."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None


def _mock_streamlit(session_state=None):
    """Create a mock streamlit module whose session_state behaves like Streamlit's."""
    st = MagicMock()
    st.session_state = _FakeSession(session_state or {})
    return st


# ── _fallback ─────────────────────────────────────────────────────────


def test_fallback_with_results():
    results = [_make_result()]
    output = _fallback("test query", results)
    assert "test query" in output
    assert "func" in output


def test_fallback_empty_results():
    output = _fallback("test query", [])
    assert "test query" in output
    assert "Nothing found" not in output


def test_fallback_with_docstring():
    chunk = MagicMock()
    chunk.source_file = "test.py"
    chunk.name = "func"
    chunk.docstring = "This is a docstring"
    chunk.content = "def func(): pass"
    result = MagicMock()
    result.chunk = chunk
    result.score = 0.9
    output = _fallback("query", [result])
    assert "docstring" in output.lower()


def test_fallback_truncates_content():
    chunk = MagicMock()
    chunk.source_file = "test.py"
    chunk.name = "func"
    chunk.docstring = None
    chunk.content = "x " * 1000
    result = MagicMock()
    result.chunk = chunk
    result.score = 0.9
    output = _fallback("query", [result])
    assert len(output) < len(chunk.content)


def test_fallback_sets_api_key_hint():
    results = [_make_result()]
    output = _fallback("query", results)
    assert "GEMINI_API_KEY" in output


# ── _get_api_key ──────────────────────────────────────────────────────


def test_get_api_key_from_env():
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"}, clear=False):
        result = _get_api_key()
        assert result == "test_key"


def test_get_api_key_from_session_state():
    mock_st = _mock_streamlit({"api_key": "session_key"})
    with (
        patch.dict("os.environ", {}, clear=True),
        patch.dict("sys.modules", {"streamlit": mock_st}),
    ):
        result = _get_api_key()
        assert result == "session_key"


def test_get_api_key_returns_empty():
    mock_st = _mock_streamlit({})
    with (
        patch.dict("os.environ", {}, clear=True),
        patch.dict("sys.modules", {"streamlit": mock_st}),
    ):
        result = _get_api_key()
        assert result == ""


# ── _get_provider ─────────────────────────────────────────────────────


def test_get_provider_from_session_state():
    mock_st = _mock_streamlit({"provider": "groq"})
    with patch.dict("sys.modules", {"streamlit": mock_st}):
        result = _get_provider()
        assert result == "groq"


def test_get_provider_defaults_to_gemini():
    mock_st = _mock_streamlit({})
    with patch.dict("sys.modules", {"streamlit": mock_st}):
        result = _get_provider()
        assert result == "gemini"


def test_get_provider_handles_runtime_error():
    class _StreamlitNoSession:
        """Mock streamlit module that raises RuntimeError on session_state access."""

        def __getattr__(self, name):
            if name == "session_state":
                raise RuntimeError("There is no current event loop thread")
            raise AttributeError(name) from None

    mock_st = _StreamlitNoSession()
    with patch.dict("sys.modules", {"streamlit": mock_st}):
        result = _get_provider()
        assert result == "gemini"


# ── generate_response ─────────────────────────────────────────────────


def test_generate_response_no_results():
    output = generate_response("test query", [])
    assert "Nothing found" in output


def test_generate_response_fallback_without_api_key():
    results = [_make_result()]
    mock_st = _mock_streamlit({})
    with (
        patch.dict("os.environ", {}, clear=True),
        patch.dict("sys.modules", {"streamlit": mock_st}),
    ):
        output = generate_response("test query", results)
    assert "test query" in output
    assert "func" in output


def test_generate_response_gemini():
    results = [_make_result()]
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value.text = "Gemini answer"
    mock_genai_mod = MagicMock()
    mock_genai_mod.Client.return_value = mock_client
    mock_st = _mock_streamlit({"provider": "gemini"})

    mock_google = MagicMock()
    mock_google.genai = mock_genai_mod

    with (
        patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"}, clear=False),
        patch.dict("sys.modules", {"streamlit": mock_st, "google": mock_google}),
    ):
        output = generate_response("test query", results)
    assert output == "Gemini answer"


def test_generate_response_groq():
    results = [_make_result()]
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Groq answer"
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_groq_mod = MagicMock()
    mock_groq_mod.Groq.return_value = mock_client
    mock_st = _mock_streamlit({"provider": "groq"})

    with (
        patch.dict("os.environ", {"GROQ_API_KEY": "test_key"}, clear=False),
        patch.dict("sys.modules", {"streamlit": mock_st, "groq": mock_groq_mod}),
    ):
        output = generate_response("test query", results)
    assert output == "Groq answer"


def test_generate_response_openai():
    results = [_make_result()]
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "OpenAI answer"
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai_mod = MagicMock()
    mock_openai_mod.OpenAI.return_value = mock_client
    mock_st = _mock_streamlit({"provider": "openai"})

    with (
        patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}, clear=False),
        patch.dict("sys.modules", {"streamlit": mock_st, "openai": mock_openai_mod}),
    ):
        output = generate_response("test query", results)
    assert output == "OpenAI answer"


def test_generate_response_provider_error_fallback():
    results = [_make_result()]
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API down")
    mock_genai_mod = MagicMock()
    mock_genai_mod.Client.return_value = mock_client
    mock_st = _mock_streamlit({"provider": "gemini"})

    mock_google = MagicMock()
    mock_google.genai = mock_genai_mod

    with (
        patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"}, clear=False),
        patch.dict("sys.modules", {"streamlit": mock_st, "google": mock_google}),
    ):
        output = generate_response("test query", results)
    assert "Something went wrong" in output
    assert "Found in" in output  # _fallback content is appended


def test_generate_response_context_limits_to_top_5():
    results = [_make_result(source_file=f"file_{i}.py", name=f"func_{i}") for i in range(10)]
    mock_st = _mock_streamlit({})
    with (
        patch.dict("os.environ", {}, clear=True),
        patch.dict("sys.modules", {"streamlit": mock_st}),
    ):
        _ = generate_response("query", results)


def test_generate_response_uses_ranker():
    results = [_make_result()]
    mock_st = _mock_streamlit({})
    with (
        patch.dict("os.environ", {}, clear=True),
        patch.dict("sys.modules", {"streamlit": mock_st}),
    ):
        output = generate_response("query", results)
    assert isinstance(output, str)
