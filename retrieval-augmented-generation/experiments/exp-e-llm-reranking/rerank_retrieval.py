import chromadb

from embeddings import create_embeddings


CHROMA_PATH = "../chroma_db"
COLLECTION_NAME = "kubernetes_docs_hybrid"

DISTANCE_THRESHOLD = 0.70


def calculate_rerank_score(query, document):

    query_words = set(
        query.lower().split()
    )

    document_words = set(
        document.lower().split()
    )

    if not query_words:
        return 0

    matched_words = (
        query_words & document_words
    )

    score = (
        len(matched_words)
        / len(query_words)
    )

    return score


def retrieve_and_rerank(
    query,
    top_k=5,
    candidate_k=15
):

    client = chromadb.PersistentClient(
        path=CHROMA_PATH
    )

    collection = client.get_collection(
        name=COLLECTION_NAME
    )

    # --------------------------------
    # 1. Embed query
    # --------------------------------

    query_embedding = create_embeddings([
        {
            "content": query
        }
    ])[0]

    # --------------------------------
    # 2. Retrieve candidate chunks
    # --------------------------------

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=candidate_k
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    # --------------------------------
    # 3. Apply relevance threshold
    # --------------------------------

    candidates = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances
    ):

        if distance <= DISTANCE_THRESHOLD:

            candidates.append({
                "document": document,
                "metadata": metadata,
                "distance": distance
            })

    if not candidates:

        return {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
            "rerank_scores": [[]]
        }

    # --------------------------------
    # 4. Rerank candidates
    # --------------------------------

    for candidate in candidates:

        candidate["rerank_score"] = (
            calculate_rerank_score(
                query,
                candidate["document"]
            )
        )

    # --------------------------------
    # 5. Sort by reranker score
    # --------------------------------

    candidates.sort(
        key=lambda item: item["rerank_score"],
        reverse=True
    )

    # --------------------------------
    # 6. Select final Top-K
    # --------------------------------

    selected = candidates[:top_k]

    return {
        "documents": [[
            item["document"]
            for item in selected
        ]],
        "metadatas": [[
            item["metadata"]
            for item in selected
        ]],
        "distances": [[
            item["distance"]
            for item in selected
        ]],
        "rerank_scores": [[
            item["rerank_score"]
            for item in selected
        ]]
    }


if __name__ == "__main__":

    query = "Why is my Kubernetes Pod stuck in Pending state?"

    results = retrieve_and_rerank(query)

    print("\nQuery:")
    print(query)

    print("\nReranked Documents:")

    if not results["documents"][0]:

        print("No relevant documents found.")

    else:

        for i, document in enumerate(
            results["documents"][0]
        ):

            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i]
            rerank_score = results["rerank_scores"][0][i]

            print("\n--------------------------------")
            print(f"Result: {i + 1}")
            print(f"Source: {metadata['source']}")
            print(f"Chunk: {metadata['chunk_index']}")
            print(f"Vector Distance: {distance}")
            print(f"Rerank Score: {rerank_score}")

            print("\nContent:")
            print(document)
