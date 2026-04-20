import requests

def generate_response(prompt):
    url = "http://localhost:11434/api/generate"

    data = {
        "model": "llama3",  # or "mistral"
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(url, json=data)
    return response.json()["response"]