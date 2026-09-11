import os

from dotenv import load_dotenv
from openai import OpenAI

from .retriever import retrieve_documents


load_dotenv("/home/ubuntu/ai-devops-agent/.env")


BASE_URL = "https://llmfoundry.straive.com/gemini/v1beta/openai"
MODEL_NAME = "models/gemini-2.5-flash"

TOKEN = os.getenv("LLMFOUNDRY_TOKEN")


def build_prompt(query, results):
    context_parts = []

    for i, document in enumerate(results["documents"][0]):
        metadata = results["metadatas"][0][i]

        context_parts.append(
            f"""
Source: {metadata['source']}
Chunk: {metadata['chunk_index']}

{document}
"""
        )

    context = "\n\n---\n\n".join(context_parts)

    prompt = f"""
You are a Kubernetes troubleshooting assistant.

Answer the user's question using the provided Kubernetes documentation.

Rules:
- Use the provided context as your primary source.
- Do not invent Kubernetes facts that are not supported by the context.
- Give practical troubleshooting steps.
- If the context does not contain enough information, say so.

Context:
{context}

User Question:
{query}

Answer:
"""

    return prompt


def generate_answer(query):
    results = retrieve_documents(query, top_k=5)

    prompt = build_prompt(query, results)

    client = OpenAI(
        api_key=TOKEN,
        base_url=BASE_URL
    )

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content


if __name__ == "__main__":

    query = "Why is my Kubernetes Pod stuck in Pending state?"

    answer = generate_answer(query)

    print("\nFinal Answer:")
    print(answer)
