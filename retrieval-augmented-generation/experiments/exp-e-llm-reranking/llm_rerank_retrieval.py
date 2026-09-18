import json
import os

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

from embeddings import create_embeddings


# --------------------------------------------------
# Configuration
# --------------------------------------------------

CHROMA_PATH = "../chroma_db"
COLLECTION_NAME = "kubernetes_docs_hybrid"

EMBEDDING_MODEL = "models/gemini-embedding-001"
RERANK_MODEL = "models/gemini-2.5-flash"

BASE_URL = "https://llmfoundry.straive.com/gemini/v1beta/openai"

DISTANCE_THRESHOLD = 0.70

CANDIDATE_K = 15
TOP_K = 5


# --------------------------------------------------
# Load environment
# --------------------------------------------------

load_dotenv()

TOKEN = os.getenv("LLMFOUNDRY_TOKEN")


# --------------------------------------------------
# Clients
# --------------------------------------------------

client = OpenAI(
    api_key=TOKEN,
    base_url=BASE_URL
)


# --------------------------------------------------
# Vector retrieval
# --------------------------------------------------

def retrieve_candidates(query, candidate_k=CANDIDATE_K):

    chroma_client = chromadb.PersistentClient(
        path=CHROMA_PATH
    )

    collection = chroma_client.get_collection(
        name=COLLECTION_NAME
    )

    query_embedding = create_embeddings([
        {"content": query}
    ])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=candidate_k
    )

    candidates = []

    for i, distance in enumerate(results["distances"][0]):

        if distance <= DISTANCE_THRESHOLD:

            candidates.append({
                "candidate_id": i,
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": distance
            })

    return candidates


# --------------------------------------------------
# LLM reranking
# --------------------------------------------------

def rerank_candidates(query, candidates, top_k=TOP_K):

    candidate_text = ""

    for candidate in candidates:

        candidate_text += (
            f"\n\n"
            f"Candidate ID: {candidate['candidate_id']}\n"
            f"Source: {candidate['metadata']['source']}\n"
            f"Chunk: {candidate['metadata']['chunk_index']}\n"
            f"Content:\n{candidate['content']}\n"
        )

    prompt = f"""
You are a document relevance reranker.

Your task is to rank the retrieved Kubernetes documentation
chunks according to how useful they are for answering the
user's question.

User question:
{query}

Retrieved candidates:
{candidate_text}

Instructions:

1. Rank candidates from most relevant to least relevant.
2. Prefer candidates that directly answer the question.
3. Prefer specific troubleshooting or explanatory information.
4. Do not rank a candidate highly merely because it shares
   individual words with the query.
5. Do not invent information.
6. Return exactly the top {top_k} candidates.
7. Give each candidate a relevance score from 0 to 100.
8. Give a short reason for each ranking.

Return ONLY valid JSON in this format:

[
  {{
    "candidate_id": 0,
    "score": 95,
    "reason": "Directly explains the causes of the issue."
  }}
]
"""

    response = client.chat.completions.create(
        model=RERANK_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    content = response.choices[0].message.content

    # Remove markdown code fences if Gemini adds them
    content = content.strip()

    if content.startswith("```"):
        content = content.replace("```json", "")
        content = content.replace("```", "")
        content = content.strip()

    rankings = json.loads(content)

    reranked = []

    candidate_map = {
        candidate["candidate_id"]: candidate
        for candidate in candidates
    }

    for ranking in rankings:

        candidate_id = ranking["candidate_id"]

        if candidate_id not in candidate_map:
            continue

        candidate = candidate_map[candidate_id].copy()

        candidate["rerank_score"] = ranking["score"]
        candidate["rerank_reason"] = ranking["reason"]

        reranked.append(candidate)

    return reranked


# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":

    query = "Why is my Pod stuck in Pending state?"

    print("=" * 70)
    print("LLM-BASED RERANKING")
    print("=" * 70)

    candidates = retrieve_candidates(query)

    print(f"\nRetrieved candidates: {len(candidates)}")

    print("\n--- Vector Retrieval ---")

    for rank, candidate in enumerate(candidates, start=1):

        print(
            f"{rank}. "
            f"{os.path.basename(candidate['metadata']['source'])} "
            f"| chunk {candidate['metadata']['chunk_index']} "
            f"| distance {candidate['distance']:.4f}"
        )

    reranked = rerank_candidates(
        query,
        candidates
    )

    print("\n--- LLM Reranked Results ---")

    for rank, candidate in enumerate(reranked, start=1):

        print(
            f"{rank}. "
            f"{os.path.basename(candidate['metadata']['source'])} "
            f"| chunk {candidate['metadata']['chunk_index']} "
            f"| score {candidate['rerank_score']}"
        )

        print(
            f"   Reason: {candidate['rerank_reason']}"
        )
