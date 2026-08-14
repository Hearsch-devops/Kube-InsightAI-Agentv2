import os

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("LLMFOUNDRY_TOKEN")
PROJECT = os.getenv("PROJECT_NAME")

URL = "https://llmfoundry.straive.com/gemini/v1beta/openai/chat/completions"


def get_llm_response(message: str) -> str:
    if not TOKEN:
        raise ValueError("LLMFOUNDRY_TOKEN is not configured")

    if not PROJECT:
        raise ValueError("PROJECT_NAME is not configured")

    headers = {
        "Authorization": f"Bearer {TOKEN}:{PROJECT}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "models/gemini-2.5-flash",
        "messages": [
            {
                "role": "user",
                "content": message,
            }
        ],
    }

    response = requests.post(
        URL,
        headers=headers,
        json=payload,
        timeout=30,
    )

    response.raise_for_status()

    result = response.json()

    return result["choices"][0]["message"]["content"]