import json
import math
import os

from dotenv import load_dotenv
from openai import OpenAI

from llm_rerank_retrieval import retrieve_candidates, rerank_candidates


# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_URL = "https://llmfoundry.straive.com/gemini/v1beta/openai"
JUDGE_MODEL = "models/gemini-2.5-flash"

load_dotenv()

TOKEN = os.getenv("LLMFOUNDRY_TOKEN")

client = OpenAI(
    api_key=TOKEN,
    base_url=BASE_URL
)


# --------------------------------------------------
# Evaluation queries
# --------------------------------------------------

TEST_QUERIES = [
    "Why is my Pod stuck in Pending state?",
    "How do I expose a Pod using a Kubernetes Service?",
    "How do I troubleshoot a Kubernetes Ingress?",
    "Why does my Pod keep restarting?",
    "How does Kubernetes storage work?",
    "Why is my Kubernetes Pod experiencing CPU throttling?"
]


# --------------------------------------------------
# Gemini relevance judge
# --------------------------------------------------

def judge_relevance(query, candidates):

    candidate_text = ""

    for index, candidate in enumerate(candidates):

        candidate_text += f"""
Candidate ID: {index}

Source:
{os.path.basename(candidate["metadata"]["source"])}

Chunk:
{candidate["metadata"]["chunk_index"]}

Content:
{candidate["content"]}

----------------------------------------
"""

    prompt = f"""
You are evaluating document relevance for a Kubernetes RAG system.

User question:
{query}

Evaluate every candidate chunk below.

Assign a relevance score:

3 = Highly relevant
    Directly answers the question or contains critical information
    needed to answer it.

2 = Relevant
    Useful supporting information for answering the question.

1 = Somewhat relevant
    Related to the topic but provides limited value.

0 = Irrelevant
    Does not help answer the question.

Important:
- Judge the actual content of each chunk.
- Do not judge based only on the filename.
- Do not give a high score simply because the chunk contains
  words from the question.
- Evaluate each candidate independently.

Return ONLY valid JSON.

Required format:

[
    {{
        "candidate_id": 0,
        "relevance": 3
    }}
]

Candidates:

{candidate_text}
"""

    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    content = response.choices[0].message.content.strip()

    if content.startswith("```"):
        content = content.replace("```json", "")
        content = content.replace("```", "")
        content = content.strip()

    return json.loads(content)


# --------------------------------------------------
# DCG
# --------------------------------------------------

def dcg_at_k(relevance_scores, k=5):

    score = 0.0

    for rank, relevance in enumerate(
        relevance_scores[:k],
        start=1
    ):

        score += (
            (2 ** relevance - 1) /
            math.log2(rank + 1)
        )

    return score


# --------------------------------------------------
# NDCG@5
# --------------------------------------------------

def ndcg_at_k(relevance_scores, k=5):

    actual_dcg = dcg_at_k(
        relevance_scores,
        k
    )

    ideal_scores = sorted(
        relevance_scores,
        reverse=True
    )

    ideal_dcg = dcg_at_k(
        ideal_scores,
        k
    )

    if ideal_dcg == 0:
        return 0.0

    return actual_dcg / ideal_dcg


# --------------------------------------------------
# MRR
# --------------------------------------------------

def reciprocal_rank(relevance_scores):

    for rank, relevance in enumerate(
        relevance_scores,
        start=1
    ):

        if relevance > 0:
            return 1 / rank

    return 0.0


# --------------------------------------------------
# Evaluation
# --------------------------------------------------

def evaluate():

    mrr_scores = []
    ndcg_scores = []

    print("=" * 70)
    print("CHUNK-LEVEL MRR + NDCG@5 EVALUATION")
    print("=" * 70)

    for index, query in enumerate(
        TEST_QUERIES,
        start=1
    ):

        print(f"\nTest {index}/{len(TEST_QUERIES)}")
        print(f"Query: {query}")

        # ------------------------------------------
        # Retrieve 15 vector candidates
        # ------------------------------------------

        candidates = retrieve_candidates(
            query,
            candidate_k=15
        )

        print(
            f"Retrieved candidates: "
            f"{len(candidates)}"
        )

        # ------------------------------------------
        # Gemini judges all candidates
        # ------------------------------------------

        judgments = judge_relevance(
            query,
            candidates
        )

        relevance_map = {
            item["candidate_id"]: item["relevance"]
            for item in judgments
        }

        # ------------------------------------------
        # Rerank candidates
        # ------------------------------------------

        reranked = rerank_candidates(
            query,
            candidates,
            top_k=5
        )

        # ------------------------------------------
        # Find relevance of reranked chunks
        # ------------------------------------------

        reranked_relevance = []

        for candidate in reranked:

            candidate_id = candidate["candidate_id"]

            relevance = relevance_map.get(
                candidate_id,
                0
            )

            reranked_relevance.append(
                relevance
            )

        # ------------------------------------------
        # Metrics
        # ------------------------------------------

        mrr = reciprocal_rank(
            reranked_relevance
        )

        ndcg = ndcg_at_k(
            reranked_relevance,
            k=5
        )

        mrr_scores.append(mrr)
        ndcg_scores.append(ndcg)

        # ------------------------------------------
        # Print ranking
        # ------------------------------------------

        print("\nReranked chunks:")

        for rank, candidate in enumerate(
            reranked,
            start=1
        ):

            candidate_id = candidate["candidate_id"]

            relevance = relevance_map.get(
                candidate_id,
                0
            )

            source = os.path.basename(
                candidate["metadata"]["source"]
            )

            chunk = candidate["metadata"]["chunk_index"]

            print(
                f"{rank}. "
                f"{source} "
                f"| chunk {chunk} "
                f"| relevance {relevance}"
            )

        print(
            f"\nRelevance scores: "
            f"{reranked_relevance}"
        )

        print(
            f"MRR: {mrr:.4f}"
        )

        print(
            f"NDCG@5: {ndcg:.4f}"
        )

    # --------------------------------------------------
    # Final results
    # --------------------------------------------------

    average_mrr = (
        sum(mrr_scores) /
        len(mrr_scores)
    )

    average_ndcg = (
        sum(ndcg_scores) /
        len(ndcg_scores)
    )

    print("\n" + "=" * 70)
    print("FINAL CHUNK-LEVEL RESULTS")
    print("=" * 70)

    print(
        f"Mean Reciprocal Rank (MRR): "
        f"{average_mrr:.4f}"
    )

    print(
        f"Average NDCG@5: "
        f"{average_ndcg:.4f}"
    )


# --------------------------------------------------
# Run
# --------------------------------------------------

if __name__ == "__main__":
    evaluate()
