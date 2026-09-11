import chromadb

from embeddings import create_embeddings


CHROMA_PATH = "../chroma_db"
COLLECTION_NAME = "kubernetes_docs_structure"

DISTANCE_THRESHOLD = 0.70


def retrieve_documents(query, top_k=5):

    client = chromadb.PersistentClient(
        path=CHROMA_PATH
    )

    collection = client.get_collection(
        name=COLLECTION_NAME
    )

    query_embedding = create_embeddings([
        {
            "content": query
        }
    ])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    filtered_documents = []
    filtered_metadatas = []
    filtered_distances = []

    for i, distance in enumerate(results["distances"][0]):

        if distance <= DISTANCE_THRESHOLD:

            filtered_documents.append(
                results["documents"][0][i]
            )

            filtered_metadatas.append(
                results["metadatas"][0][i]
            )

            filtered_distances.append(distance)

    return {
        "documents": [filtered_documents],
        "metadatas": [filtered_metadatas],
        "distances": [filtered_distances]
    }


if __name__ == "__main__":

    query = "Why is my Kubernetes Pod stuck in Pending state?"

    results = retrieve_documents(query)

    print("\nQuery:")
    print(query)

    print("\nRetrieved Documents:")

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
            print(
                f"Section: "
                f"{metadata['chunk_index']}"
            )
            print(f"Distance: {distance}")

            print("\nContent:")
            print(document)
