from pathlib import Path

import chromadb

from .document_loader import load_documents
from .text_splitter import split_documents
from .embeddings import create_embeddings


CHROMA_PATH = Path(__file__).parent.parent / "chroma_db"
COLLECTION_NAME = "kubernetes_docs"


def create_vector_store():

    documents = load_documents()

    chunks = split_documents(documents)

    print(f"Documents: {len(documents)}")
    print(f"Chunks: {len(chunks)}")

    embeddings = create_embeddings(chunks)

    client = chromadb.PersistentClient(
        path=str(CHROMA_PATH)
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME
    )

    ids = [
        f"chunk_{i}"
        for i in range(len(chunks))
    ]

    texts = [
        chunk["content"]
        for chunk in chunks
    ]

    metadatas = [
        chunk["metadata"]
        for chunk in chunks
    ]

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas
    )

    print(
        f"Stored {len(chunks)} chunks "
        f"in {COLLECTION_NAME}"
    )


if __name__ == "__main__":
    create_vector_store()
