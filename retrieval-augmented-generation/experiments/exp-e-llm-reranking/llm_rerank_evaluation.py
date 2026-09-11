import os

from llm_rerank_retrieval import retrieve_candidates, rerank_candidates


# --------------------------------------------------
# Evaluation dataset
# --------------------------------------------------

TEST_CASES = [
    {
        "query": "Why is my Pod stuck in Pending state?",
        "expected_sources": [
            "pod.md",
            "scheduling.md"
        ]
    },
    {
        "query": "How do I expose a Pod using a Kubernetes Service?",
        "expected_sources": [
            "services.md",
            "networking.md"
        ]
    },
    {
        "query": "How do I troubleshoot a Kubernetes Ingress?",
        "expected_sources": [
            "ingress.md"
        ]
    },
    {
        "query": "Why does my Pod keep restarting?",
        "expected_sources": [
            "troubleshooting.md",
            "pod.md"
        ]
    },
    {
        "query": "How does Kubernetes storage work?",
        "expected_sources": [
            "storage.md"
        ]
    },
    {
        "query": "Why is my Kubernetes Pod experiencing CPU throttling?",
        "expected_sources": [
            "resources.md"
        ]
    }
]


# --------------------------------------------------
# Evaluation
# --------------------------------------------------

def evaluate():

    total_tests = len(TEST_CASES)

    passed = 0
    precision_scores = []
    recall_scores = []

    print("=" * 70)
    print("LLM RERANKING EVALUATION")
    print("=" * 70)

    for index, test_case in enumerate(TEST_CASES, start=1):

        query = test_case["query"]
        expected_sources = set(test_case["expected_sources"])

        print(f"\nTest {index}/{total_tests}")
        print(f"Query: {query}")

        # ------------------------------------------
        # Retrieve candidates
        # ------------------------------------------

        candidates = retrieve_candidates(query)

        # ------------------------------------------
        # LLM reranking
        # ------------------------------------------

        reranked = rerank_candidates(
            query,
            candidates,
            top_k=5
        )

        # ------------------------------------------
        # Extract retrieved sources
        # ------------------------------------------

        retrieved_sources = []

        for candidate in reranked:

            source = os.path.basename(
                candidate["metadata"]["source"]
            )

            retrieved_sources.append(source)

        retrieved_source_set = set(retrieved_sources)

        # ------------------------------------------
        # Calculate metrics
        # ------------------------------------------

        matched_sources = (
            expected_sources &
            retrieved_source_set
        )

        # Document-level precision
        if retrieved_source_set:
            precision = (
                len(matched_sources) /
                len(retrieved_source_set)
            )
        else:
            precision = 0.0

        # Document-level recall
        if expected_sources:
            recall = (
                len(matched_sources) /
                len(expected_sources)
            )
        else:
            recall = 0.0

        precision_scores.append(precision)
        recall_scores.append(recall)

        # ------------------------------------------
        # Test passed?
        # ------------------------------------------

        if expected_sources.issubset(retrieved_source_set):
            passed += 1
            status = "PASS"
        else:
            status = "FAIL"

        # ------------------------------------------
        # Print results
        # ------------------------------------------

        print(f"Status: {status}")

        print(
            f"Expected sources: "
            f"{sorted(expected_sources)}"
        )

        print(
            f"Retrieved sources: "
            f"{retrieved_sources}"
        )

        print(
            f"Matched sources: "
            f"{sorted(matched_sources)}"
        )

        print(
            f"Precision@5: "
            f"{precision * 100:.2f}%"
        )

        print(
            f"Recall@5: "
            f"{recall * 100:.2f}%"
        )

    # --------------------------------------------------
    # Final metrics
    # --------------------------------------------------

    hit_rate = (
        passed / total_tests
        if total_tests
        else 0
    )

    average_precision = (
        sum(precision_scores) /
        len(precision_scores)
        if precision_scores
        else 0
    )

    average_recall = (
        sum(recall_scores) /
        len(recall_scores)
        if recall_scores
        else 0
    )

    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)

    print(
        f"Tests Passed: "
        f"{passed}/{total_tests}"
    )

    print(
        f"Hit Rate: "
        f"{hit_rate * 100:.2f}%"
    )

    print(
        f"Average Precision@5: "
        f"{average_precision * 100:.2f}%"
    )

    print(
        f"Average Recall@5: "
        f"{average_recall * 100:.2f}%"
    )


# --------------------------------------------------
# Run evaluation
# --------------------------------------------------

if __name__ == "__main__":
    evaluate()
