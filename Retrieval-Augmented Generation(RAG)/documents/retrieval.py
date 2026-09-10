import chromadb

from embeddings import create_embeddings


CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "kubernetes_docs"


def retrieve_documents(query, top_k=5):
    # Create ChromaDB client
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Get existing collection
    collection = client.get_collection(
        name=COLLECTION_NAME
    )

    # Create embedding for the user question
    query_embedding = create_embeddings([
        {
            "content": query
        }
    ])[0]

    # Search ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    return results


if __name__ == "__main__":

    query = "Why is my Kubernetes Pod stuck in Pending state?"

    results = retrieve_documents(query)

    print("\nQuery:")
    print(query)

    print("\nRetrieved Documents:")

    for i, document in enumerate(results["documents"][0]):
        metadata = results["metadatas"][0][i]
        distance = results["distances"][0][i]

        print("\n--------------------------------")
        print(f"Result: {i + 1}")
        print(f"Source: {metadata['source']}")
        print(f"Chunk: {metadata['chunk_index']}")
        print(f"Distance: {distance}")
        print("\nContent:")
        print(document)