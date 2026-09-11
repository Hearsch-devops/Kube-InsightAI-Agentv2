import math
import os

from llm_rerank_retrieval import (
    retrieve_candidates,
    rerank_candidates
)


# --------------------------------------------------
# Evaluation dataset
# --------------------------------------------------

TEST_CASES = [
    {
        "query": "Why is my Pod stuck in Pending state?",
        "relevance": {
            "pod.md": 3,
            "scheduling.md": 3,
            "troubleshooting.md": 2,
            "resources.md": 1
        }
    },
    {
        "query": "How do I expose a Pod using a Kubernetes Service?",
        "relevance": {
            "services.md": 3,
            "networking.md": 2
        }
    },
    {
        "query": "How do I troubleshoot a Kubernetes Ingress?",
        "relevance": {
            "ingress.md": 3,
            "networking.md": 2,
            "troubleshooting.md": 2
        }
    },
    {
        "query": "Why does my Pod keep restarting?",
        "relevance": {
            "pod.md": 3,
            "troubleshooting.md": 3,
            "deployments.md": 1
        }
    },
    {
        "query": "How does Kubernetes storage work?",
        "relevance": {
            "storage.md": 3,
            "resources.md": 1
        }
    },
    {
        "query": "Why is my Kubernetes Pod experiencing CPU throttling?",
        "relevance": {
            "resources.md": 3,
            "troubleshooting.md": 2
        }
    }
]


# --------------------------------------------------
# Convert source list to relevance scores
# --------------------------------------------------

def get_relevance_scores(results, relevance):

    scores = []

    for source in results:
        scores.append(
            relevance.get(source, 0)
        )

    return scores


# --------------------------------------------------
# MRR
# --------------------------------------------------

def reciprocal_rank(results, relevance):

    for rank, source in enumerate(results, start=1):

        if relevance.get(source, 0) > 0:
            return 1 / rank

    return 0.0


# --------------------------------------------------
# DCG
# --------------------------------------------------

def dcg_at_k(relevance_scores, k=5):

    score = 0.0

    for rank, rel in enumerate(
        relevance_scores[:k],
        start=1
    ):

        score += (
            (2 ** rel - 1) /
            math.log2(rank + 1)
        )

    return score


# --------------------------------------------------
# NDCG@K
# --------------------------------------------------

def ndcg_at_k(results, relevance, k=5):

    actual_scores = get_relevance_scores(
        results,
        relevance
    )

    actual_dcg = dcg_at_k(
        actual_scores,
        k
    )

    # ----------------------------------------------
    # Build the ideal ranking.
    #
    # We create one relevance score for every
    # retrieved position and sort those scores
    # from highest to lowest.
    #
    # This guarantees the ideal list has the same
    # length as the actual ranking.
    # ----------------------------------------------

    ideal_scores = sorted(
        actual_scores,
        reverse=True
    )

    ideal_dcg = dcg_at_k(
        ideal_scores,
        k
    )

    if ideal_dcg == 0:
        return 0.0

    score = actual_dcg / ideal_dcg

    # Safety guard: NDCG must be between 0 and 1.
    return min(score, 1.0)


# --------------------------------------------------
# Evaluation
# --------------------------------------------------

def evaluate():

    mrr_scores = []
    ndcg_scores = []

    print("=" * 70)
    print("MMR + NDCG@5 RANKING EVALUATION")
    print("=" * 70)

    for index, test_case in enumerate(
        TEST_CASES,
        start=1
    ):

        query = test_case["query"]
        relevance = test_case["relevance"]

        print(f"\nTest {index}/{len(TEST_CASES)}")
        print(f"Query: {query}")

        # ------------------------------------------
        # Retrieve candidates
        # ------------------------------------------

        candidates = retrieve_candidates(query)

        # ------------------------------------------
        # Gemini LLM reranking
        # ------------------------------------------

        reranked = rerank_candidates(
            query,
            candidates,
            top_k=5
        )

        # ------------------------------------------
        # Extract sources
        # ------------------------------------------

        sources = []

        for candidate in reranked:

            source = os.path.basename(
                candidate["metadata"]["source"]
            )

            sources.append(source)

        # ------------------------------------------
        # Relevance scores
        # ------------------------------------------

        relevance_scores = get_relevance_scores(
            sources,
            relevance
        )

        # ------------------------------------------
        # Calculate metrics
        # ------------------------------------------

        mrr = reciprocal_rank(
            sources,
            relevance
        )

        ndcg = ndcg_at_k(
            sources,
            relevance,
            k=5
        )

        mrr_scores.append(mrr)
        ndcg_scores.append(ndcg)

        # ------------------------------------------
        # Print results
        # ------------------------------------------

        print(
            f"Ranking: {sources}"
        )

        print(
            f"Relevance: {relevance_scores}"
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
    print("FINAL RANKING RESULTS")
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
