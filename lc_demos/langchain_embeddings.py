import os
import httpx

from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings


load_dotenv()


TOKEN = os.getenv("LLMFOUNDRY_TOKEN")

BASE_URL = "https://llmfoundry.straive.com/gemini/v1beta/openai"
EMBEDDING_MODEL = "models/gemini-embedding-001"


class GeminiEmbeddings(Embeddings):

    def embed_documents(self, texts):
        response = httpx.post(
            f"{BASE_URL}/embeddings",
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": texts,
            },
            timeout=60,
        )

        response.raise_for_status()

        data = response.json()

        return [
            item["embedding"]
            for item in data["data"]
        ]

    def embed_query(self, text):
        return self.embed_documents([text])[0]
