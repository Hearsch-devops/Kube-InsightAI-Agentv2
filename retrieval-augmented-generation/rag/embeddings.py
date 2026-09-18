import os

import httpx
from dotenv import load_dotenv

from .text_splitter import split_documents
from .document_loader import load_documents

load_dotenv()

MODEL_NAME = "models/gemini-embedding-001"
BASE_URL = "https://llmfoundry.straive.com/gemini/v1beta/openai"
TOKEN = os.getenv("LLMFOUNDRY_TOKEN")


def create_embeddings(chunks):
    texts = [chunk["content"] for chunk in chunks]

    all_embeddings = []

    batch_size = 100

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }

    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]

        print(
            f"Embedding batch: "
            f"{start + 1}-{min(start + batch_size, len(texts))}"
        )

        response = httpx.post(
            f"{BASE_URL}/embeddings",
            headers=headers,
            json={
                "model": MODEL_NAME,
                "input": batch,
            },
            timeout=60,
        )

        response.raise_for_status()

        data = response.json()

        batch_embeddings = [
            item["embedding"]
            for item in data["data"]
        ]

        all_embeddings.extend(batch_embeddings)

        print(
            f"Embedded "
            f"{min(start + batch_size, len(texts))}/{len(texts)} chunks"
        )

    return all_embeddings


if __name__ == "__main__":
    documents = load_documents()
    chunks = split_documents(documents)

    embeddings = create_embeddings(chunks)

    print(f"Documents: {len(documents)}")
    print(f"Chunks: {len(chunks)}")
    print(f"Embeddings: {len(embeddings)}")
    print(f"Vector dimensions: {len(embeddings[0])}")
