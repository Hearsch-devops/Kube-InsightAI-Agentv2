import chromadb

from embeddings import create_embeddings


CHROMA_PATH = "../chroma_db"
COLLECTION_NAME = "kubernetes_docs_hybrid"

DISTANCE_THRESHOLD = 0.70


def cosine_similarity(vector_a, vector_b):

    dot_product = sum(
        a * b
        for a, b in zip(vector_a, vector_b)
    )

    magnitude_a = sum(
        a * a
        for a in vector_a
    ) ** 0.5

    magnitude_b = sum(
        b * b
        for b in vector_b
    ) ** 0.5

    if magnitude_a == 0 or magnitude_b == 0:
        return 0

    return dot_product / (
        magnitude_a * magnitude_b
    )


def retrieve_documents(
    query,
    top_k=5,
    candidate_k=15,
    lambda_param=0.8
):

    client = chromadb.PersistentClient(
        path=CHROMA_PATH
    )

    collection = client.get_collection(
        name=COLLECTION_NAME
    )

    # --------------------------------
    # 1. Embed the query
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
        n_results=candidate_k,
        include=[
            "documents",
            "metadatas",
            "distances",
            "embeddings"
        ]
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    embeddings = results["embeddings"][0]

    # --------------------------------
    # 3. Apply relevance threshold
    # --------------------------------

    candidates = []

    for document, metadata, distance, embedding in zip(
        documents,
        metadatas,
        distances,
        embeddings
    ):

        if distance <= DISTANCE_THRESHOLD:

            candidates.append({
                "document": document,
                "metadata": metadata,
                "distance": distance,
                "embedding": embedding
            })

    if not candidates:

        return {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }

    # --------------------------------
    # 4. MMR selection
    # --------------------------------

    selected = []

    # First result = most relevant result.
    first = min(
        candidates,
        key=lambda item: item["distance"]
    )

    selected.append(first)
    candidates.remove(first)

    while candidates and len(selected) < top_k:

        best_candidate = None
        best_score = float("-inf")

        for candidate in candidates:

            # --------------------------------
            # Query ↔ Candidate similarity
            # --------------------------------

            relevance = cosine_similarity(
                query_embedding,
                candidate["embedding"]
            )

            # --------------------------------
            # Candidate ↔ Selected similarity
            # --------------------------------

            max_similarity = 0

            for selected_item in selected:

                similarity = cosine_similarity(
                    candidate["embedding"],
                    selected_item["embedding"]
                )

                max_similarity = max(
                    max_similarity,
                    similarity
                )

            # --------------------------------
            # MMR formula
            # --------------------------------

            mmr_score = (
                lambda_param * relevance
                -
                (1 - lambda_param) * max_similarity
            )

            if mmr_score > best_score:

                best_score = mmr_score
                best_candidate = candidate

        selected.append(best_candidate)
        candidates.remove(best_candidate)

    # --------------------------------
    # 5. Return selected chunks
    # --------------------------------

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
        ]]
    }


if __name__ == "__main__":

    query = "Why is my Kubernetes Pod stuck in Pending state?"

    results = retrieve_documents(query)

    print("\nQuery:")
    print(query)

    print("\nMMR Retrieved Documents:")

    if not results["documents"][0]:

        print("No relevant documents found.")

    else:

        for i, document in enumerate(
            results["documents"][0]
        ):

            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i]

            print("\n--------------------------------")
            print(f"Result: {i + 1}")
            print(f"Source: {metadata['source']}")
            print(f"Chunk: {metadata['chunk_index']}")
            print(f"Distance: {distance}")

            print("\nContent:")
            print(document)