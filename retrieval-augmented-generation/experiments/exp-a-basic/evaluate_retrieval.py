from retrieval import retrieve_documents


TEST_CASES = [
    {
        "query": "Why is my Kubernetes Pod stuck in Pending state?",
        "expected": "relevant"
    },
    {
        "query": "How does a Kubernetes Service expose a Pod?",
        "expected": "relevant"
    },
    {
        "query": "How do I troubleshoot a Kubernetes Ingress problem?",
        "expected": "relevant"
    },
    {
        "query": "Why does my Kubernetes Pod keep restarting?",
        "expected": "relevant"
    },
    {
        "query": "How does Kubernetes storage work for Pods?",
        "expected": "relevant"
    },
    {
        "query": "What causes CPU throttling in Kubernetes?",
        "expected": "relevant"
    },
    {
        "query": "What is the capital of France?",
        "expected": "irrelevant"
    },
    {
        "query": "How do I bake a chocolate cake?",
        "expected": "irrelevant"
    },
    {
        "query": "Who invented the telephone?",
        "expected": "irrelevant"
    },
    {
        "query": "What is a Python list comprehension?",
        "expected": "irrelevant"
    }
]


for test in TEST_CASES:

    query = test["query"]

    results = retrieve_documents(query, top_k=1)

    distance = results["distances"][0][0]

    source = results["metadatas"][0][0]["source"]

    print("\n--------------------------------")
    print(f"Query: {query}")
    print(f"Expected: {test['expected']}")
    print(f"Distance: {distance:.4f}")
    print(f"Source: {source}")
