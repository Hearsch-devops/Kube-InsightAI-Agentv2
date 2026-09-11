from hybrid_retrieval import retrieve_documents


TEST_CASES = [
    {
        "query": "Why is my Kubernetes Pod stuck in Pending state?",
        "expected_sources": [
            "scheduling.md",
            "pod.md"
        ]
    },
    {
        "query": "How does a Kubernetes Service expose a Pod?",
        "expected_sources": [
            "services.md",
            "networking.md"
        ]
    },
    {
        "query": "How do I troubleshoot a Kubernetes Ingress that is not working?",
        "expected_sources": [
            "ingress.md"
        ]
    },
    {
        "query": "Why does my Kubernetes Pod keep restarting?",
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
        "query": "Why is my Kubernetes container being throttled on CPU?",
        "expected_sources": [
            "resources.md"
        ]
    }
]


def evaluate_test_case(test_case, top_k=5):

    results = retrieve_documents(
        test_case["query"],
        top_k=top_k
    )

    retrieved_sources = [
        metadata["source"].split("/")[-1]
        for metadata in results["metadatas"][0]
    ]

    expected_sources = set(
        test_case["expected_sources"]
    )

    retrieved_source_set = set(
        retrieved_sources
    )

    matched_sources = (
        expected_sources
        & retrieved_source_set
    )

    hit = len(matched_sources) > 0

    precision = (
        len(matched_sources)
        / len(retrieved_source_set)
        if retrieved_source_set
        else 0
    )

    recall = (
        len(matched_sources)
        / len(expected_sources)
        if expected_sources
        else 0
    )

    return {
        "hit": hit,
        "precision": precision,
        "recall": recall,
        "retrieved_sources": retrieved_sources,
        "missing_sources": list(
            expected_sources - retrieved_source_set
        )
    }


def run_evaluation():

    total_tests = len(TEST_CASES)

    passed_tests = 0
    total_precision = 0
    total_recall = 0

    print("\n==============================")
    print("Hybrid RAG Evaluation")
    print("==============================")

    for index, test_case in enumerate(
        TEST_CASES,
        start=1
    ):

        print("\n--------------------------------")
        print(f"Test {index}")
        print("--------------------------------")

        print(f"Query: {test_case['query']}")

        result = evaluate_test_case(test_case)

        if result["hit"]:
            passed_tests += 1
            print("Hit: PASS")
        else:
            print("Hit: FAIL")

        print(
            f"Precision@5: "
            f"{result['precision']:.2%}"
        )

        print(
            f"Recall@5: "
            f"{result['recall']:.2%}"
        )

        print(
            "Retrieved sources:",
            result["retrieved_sources"]
        )

        if result["missing_sources"]:
            print(
                "Missing:",
                result["missing_sources"]
            )

        total_precision += result["precision"]
        total_recall += result["recall"]

    hit_rate = (
        passed_tests / total_tests
    )

    average_precision = (
        total_precision / total_tests
    )

    average_recall = (
        total_recall / total_tests
    )

    print("\n==============================")
    print("Final Results")
    print("==============================")

    print(
        f"Tests Passed: "
        f"{passed_tests}/{total_tests}"
    )

    print(
        f"Hit Rate: "
        f"{hit_rate:.2%}"
    )

    print(
        f"Average Precision@5: "
        f"{average_precision:.2%}"
    )

    print(
        f"Average Recall@5: "
        f"{average_recall:.2%}"
    )


if __name__ == "__main__":
    run_evaluation()
