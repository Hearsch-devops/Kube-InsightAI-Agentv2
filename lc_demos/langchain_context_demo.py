from langchain_core.documents import Document


def format_documents(docs):
    context_parts = []

    for i, doc in enumerate(docs, start=1):

        source = doc.metadata.get("source", "unknown")
        chunk = doc.metadata.get("chunk_index", "unknown")

        context_parts.append(
            f"""
--- Document {i} ---
Source: {source}
Chunk: {chunk}

{doc.page_content}
"""
        )

    return "\n".join(context_parts)


# Test with sample Documents

docs = [
    Document(
        page_content="A Pod is the smallest deployable unit in Kubernetes.",
        metadata={
            "source": "pod.md",
            "chunk_index": 0
        }
    ),
    Document(
        page_content="Pods can contain one or more containers.",
        metadata={
            "source": "pod.md",
            "chunk_index": 1
        }
    )
]


context = format_documents(docs)

print("\n==============================================")
print("Formatted Context")
print("==============================================")
print(context)
