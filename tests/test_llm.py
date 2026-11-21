from unittest.mock import Mock

import pytest
import requests

from llm import OllamaError, generate_response


@pytest.fixture
def post(monkeypatch):
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    post = Mock()
    monkeypatch.setattr(requests, "post", post)
    return post


def test_posts_default_payload_and_returns_text(post):
    post.return_value.json.return_value = {"response": "I think I understand."}

    assert generate_response("Student prompt") == "I think I understand."

    post.assert_called_once_with(
        "http://localhost:11434/api/generate",
        json={"model": "llama3", "prompt": "Student prompt", "stream": False},
        timeout=45,
    )
    post.return_value.raise_for_status.assert_called_once_with()


def test_reads_environment_overrides(post, monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:8080/")
    monkeypatch.setenv("OLLAMA_MODEL", "custom-model")
    post.return_value.json.return_value = {"response": "Answer"}

    generate_response("Student prompt")

    post.assert_called_once_with(
        "http://127.0.0.1:8080/api/generate",
        json={"model": "custom-model", "prompt": "Student prompt", "stream": False},
        timeout=45,
    )


@pytest.mark.parametrize(
    ("stage", "failure"),
    [
        ("post", requests.exceptions.ConnectionError("connection failed")),
        ("post", requests.exceptions.Timeout("timed out")),
        ("status", requests.exceptions.HTTPError("server returned an error")),
        ("json", requests.exceptions.JSONDecodeError("invalid JSON", "bad payload", 0)),
    ],
)
def test_reports_request_failures(post, stage, failure):
    if stage == "post":
        post.side_effect = failure
    elif stage == "status":
        post.return_value.raise_for_status.side_effect = failure
    else:
        post.return_value.json.side_effect = failure

    with pytest.raises(OllamaError, match="Make sure Ollama is running") as error:
        generate_response("Student prompt")

    assert str(failure) not in str(error.value)


@pytest.mark.parametrize("payload", [[], {}, {"response": None}, {"response": 42}])
def test_rejects_invalid_response_payload(post, payload):
    post.return_value.json.return_value = payload

    with pytest.raises(OllamaError, match="Make sure Ollama is running"):
        generate_response("Student prompt")
