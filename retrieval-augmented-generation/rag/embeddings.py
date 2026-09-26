import os
import time

import httpx
from dotenv import load_dotenv

from .text_splitter import split_documents
from .document_loader import load_documents

load_dotenv()

MODEL_NAME = "models/gemini-embedding-001"
BASE_URL = "https://llmfoundry.straive.com/gemini/v1beta/openai"
TOKEN = os.getenv("LLMFOUNDRY_TOKEN")

BATCH_SIZE = 50
MAX_RETRIES = 4
REQUEST_TIMEOUT = 180


def create_embeddings(chunks):
    if not TOKEN:
        raise ValueError("LLMFOUNDRY_TOKEN is not configured")

    texts = [chunk["content"] for chunk in chunks]
    all_embeddings = []

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        for start in range(0, len(texts), BATCH_SIZE):
            batch = texts[start:start + BATCH_SIZE]
            end = min(start + BATCH_SIZE, len(texts))

            print(f"Embedding batch: {start + 1}-{end}")

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    response = client.post(
                        f"{BASE_URL}/embeddings",
                        headers=headers,
                        json={
                            "model": MODEL_NAME,
                            "input": batch,
                        },
                    )

                    response.raise_for_status()

                    content_type = response.headers.get("content-type", "")

                    if "application/json" not in content_type.lower():
                        raise RuntimeError(
                            f"Embedding service returned non-JSON response "
                            f"(status={response.status_code}, "
                            f"content-type={content_type}): "
                            f"{response.text[:500]}"
                        )
                    
                    data = response.json()

                    batch_embeddings = [
                        item["embedding"]
                        for item in data["data"]
                    ]

                    if len(batch_embeddings) != len(batch):
                        raise ValueError(
                            f"Expected {len(batch)} embeddings, "
                            f"received {len(batch_embeddings)}"
                        )

                    all_embeddings.extend(batch_embeddings)

                    print(f"Embedded {end}/{len(texts)} chunks")
                    break

                except httpx.HTTPError as exc:
                    if attempt == MAX_RETRIES:
                        raise RuntimeError(
                            f"Embedding batch {start + 1}-{end} failed "
                            f"after {MAX_RETRIES} attempts"
                        ) from exc

                    wait_seconds = 2 ** attempt

                    print(
                        f"Embedding request failed "
                        f"(attempt {attempt}/{MAX_RETRIES}): {exc}"
                    )
                    print(f"Retrying in {wait_seconds} seconds...")

                    time.sleep(wait_seconds)

    return all_embeddings


if __name__ == "__main__":
    documents = load_documents()
    chunks = split_documents(documents)

    print(f"Documents: {len(documents)}")
    print(f"Chunks: {len(chunks)}")

    embeddings = create_embeddings(chunks)

    print(f"Embeddings: {len(embeddings)}")
    print(f"Vector dimensions: {len(embeddings[0])}")