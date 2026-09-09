import os

from dotenv import load_dotenv
from openai import OpenAI

from text_splitter import split_documents
from document_loader import load_documents


load_dotenv("/home/ubuntu/ai-devops-agent/.env")


MODEL_NAME = "models/gemini-embedding-001"

BASE_URL = "https://llmfoundry.straive.com/gemini/v1beta/openai"

TOKEN = os.getenv("LLMFOUNDRY_TOKEN")


def create_embeddings(chunks):
    client = OpenAI(
        api_key=TOKEN,
        base_url=BASE_URL
    )

    texts = [chunk["content"] for chunk in chunks]

    all_embeddings = []

    batch_size = 100

    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]

        print(
            f"Embedding batch: "
            f"{start + 1}-{min(start + batch_size, len(texts))}"
        )

        response = client.embeddings.create(
            model=MODEL_NAME,
            input=batch
        )

        batch_embeddings = [item.embedding for item in response.data]

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