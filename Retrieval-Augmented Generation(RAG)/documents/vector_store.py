import chromadb

from document_loader import load_documents
from text_splitter import split_documents
from embeddings import create_embeddings


CHROMA_PATH = "../chroma_db"
COLLECTION_NAME = "kubernetes_docs"


def create_vector_store():
    # Load documents
    documents = load_documents()

    # Split documents into chunks
    chunks = split_documents(documents)

    # Create embeddings
    embeddings = create_embeddings(chunks)

    # Create ChromaDB client
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Create or get collection
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME
    )

    # Prepare data
    ids = [f"chunk_{i}" for i in range(len(chunks))]

    texts = [chunk["content"] for chunk in chunks]

    metadatas = [chunk["metadata"] for chunk in chunks]

    # Store everything in ChromaDB
    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas
    )

    print(f"Stored {len(chunks)} chunks in ChromaDB")


if __name__ == "__main__":
    create_vector_store()