from loader import load_documents


CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def split_text(text, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    chunks = []

    start = 0

    while start < len(text):
        end = start + chunk_size

        chunk = text[start:end]

        chunks.append(chunk)

        start += chunk_size - chunk_overlap

    return chunks


def split_documents(documents):
    chunks = []

    for document in documents:
        document_chunks = split_text(document["content"])

        for index, chunk in enumerate(document_chunks):
            chunks.append({
                "content": chunk,
                "metadata": {
                    "source": document["source"],
                    "chunk_index": index
                }
            })

    return chunks


if __name__ == "__main__":
    documents = load_documents()

    chunks = split_documents(documents)

    print(f"Loaded documents: {len(documents)}")
    print(f"Generated chunks: {len(chunks)}")

    for chunk in chunks[:5]:
        print("--------------------------------")
        print(f"Source: {chunk['metadata']['source']}")
        print(f"Chunk: {chunk['metadata']['chunk_index']}")
        print(chunk["content"][:300])