import os

import requests


class OllamaError(RuntimeError):
    """An Ollama request failed or returned an invalid response."""


def generate_response(prompt):
    base_url = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    data = {
        "model": os.environ.get("OLLAMA_MODEL", "llama3"),
        "prompt": prompt,
        "stream": False,
    }
    error_message = (
        "Could not get a response from Ollama. "
        "Make sure Ollama is running and the configured model is installed."
    )

    try:
        response = requests.post(f"{base_url}/api/generate", json=data, timeout=45)
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.RequestException:
        raise OllamaError(error_message) from None

    if not isinstance(result, dict) or not isinstance(result.get("response"), str):
        raise OllamaError(error_message)
    return result["response"]
