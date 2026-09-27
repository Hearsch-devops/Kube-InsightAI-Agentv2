import os
import time

import httpx
from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings

load_dotenv()

TOKEN = os.getenv("LLMFOUNDRY_TOKEN")
BASE_URL = "https://llmfoundry.straive.com/gemini/v1beta/openai"
#BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
EMBEDDING_MODEL = "models/gemini-embedding-001"

MAX_RETRIES = 4
REQUEST_TIMEOUT = 180


class GeminiEmbeddings(Embeddings):

    def embed_documents(self, texts):
        if not TOKEN:
            raise ValueError("LLMFOUNDRY_TOKEN is not configured")

        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
                    response = client.post(
                        f"{BASE_URL}/embeddings",
                        headers=headers,
                        json={
                            "model": EMBEDDING_MODEL,
                            "input": texts,
                        },
                    )

                response.raise_for_status()
                data = response.json()

                embeddings = [
                    item["embedding"]
                    for item in data["data"]
                ]

                if len(embeddings) != len(texts):
                    raise ValueError(
                        f"Expected {len(texts)} embeddings, "
                        f"received {len(embeddings)}"
                    )

                return embeddings

            except (
                httpx.TimeoutException,
                httpx.NetworkError,
                httpx.HTTPStatusError,
            ) as exc:
                if attempt == MAX_RETRIES:
                    raise RuntimeError(
                        "Embedding request failed after "
                        f"{MAX_RETRIES} attempts"
                    ) from exc

                wait_seconds = 2 ** attempt
                print(
                    f"Embedding request failed "
                    f"(attempt {attempt}/{MAX_RETRIES}): {exc}"
                )
                print(f"Retrying in {wait_seconds} seconds...")
                time.sleep(wait_seconds)

    def embed_query(self, text):
        return self.embed_documents([text])[0]