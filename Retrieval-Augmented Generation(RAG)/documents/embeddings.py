from sentence_transformers import SentenceTransformer
from text_splitter import split_documents
from document_loader import load_documents


MODEL_NAME = "all-MiniLM-L6-v2"


def create_embeddings(chunks):
    model = SentenceTransformer(MODEL_NAME)

    texts = [chunk["content"] for chunk in chunks]

    embeddings = model.encode(texts)

    return embeddings


if __name__ == "__main__":
    documents = load_documents()

    chunks = split_documents(documents)

    embeddings = create_embeddings(chunks)

    print(f"Documents: {len(documents)}")
    print(f"Chunks: {len(chunks)}")
    print(f"Embeddings: {len(embeddings)}")
    print(f"Vector dimensions: {len(embeddings[0])}")
