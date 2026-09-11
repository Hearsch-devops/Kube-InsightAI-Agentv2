from structure_retrieval import retrieve_documents


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
        "query": "How do I troubleshoot a Kubernetes Ingress problem?",
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
        "query": "How does Kubernetes storage work for Pods?",
        "expected_sources": [
            "storage.md"
        ]
    },
    {
        "query": "What causes CPU throttling in Kubernetes?",
        "expected_sources": [
            "resources.md"
        ]
    }
]


def get_filename(source):
    return source.split("/")[-1]


def evaluate_retrieval(top_k=5):

    total_tests = len(TEST_CASES)

    total_precision = 0
    total_recall = 0

    passed_tests = 0

    print("\n==============================")
    print("STRUCTURE RAG EVALUATION")
    print("==============================")

    for test in TEST_CASES:

        query = test["query"]
        expected_sources = set(
            test["expected_sources"]
        )

        results = retrieve_documents(
            query,
            top_k=top_k
        )

        retrieved_sources = [
            get_filename(metadata["source"])
            for metadata in results["metadatas"][0]
        ]

        retrieved_set = set(retrieved_sources)

        relevant_retrieved = (
            retrieved_set & expected_sources
        )

        missing_sources = (
            expected_sources - retrieved_set
        )

        hit = len(relevant_retrieved) > 0

        if hit:
            passed_tests += 1

        if len(retrieved_set) > 0:
            precision = (
                len(relevant_retrieved)
                / len(retrieved_set)
            )
        else:
            precision = 0

        recall = (
            len(relevant_retrieved)
            / len(expected_sources)
        )

        total_precision += precision
        total_recall += recall

        status = "PASS" if hit else "FAIL"

        print("\n--------------------------------")
        print(f"Query: {query}")
        print(f"Expected: {sorted(expected_sources)}")
        print(f"Retrieved: {retrieved_sources}")
        print(f"Relevant: {sorted(relevant_retrieved)}")
        print(f"Missing: {sorted(missing_sources)}")
        print(f"Precision@{top_k}: {precision:.2%}")
        print(f"Recall@{top_k}: {recall:.2%}")
        print(f"Status: {status}")

    hit_rate = passed_tests / total_tests

    average_precision = (
        total_precision / total_tests
    )

    average_recall = (
        total_recall / total_tests
    )

    print("\n==============================")
    print(f"Tests Passed: {passed_tests}/{total_tests}")
    print(f"Hit Rate: {hit_rate:.2%}")
    print(
        f"Average Precision@{top_k}: "
        f"{average_precision:.2%}"
    )
    print(
        f"Average Recall@{top_k}: "
        f"{average_recall:.2%}"
    )
    print("==============================")


if __name__ == "__main__":
    evaluate_retrieval(top_k=5)