from langchain_core.runnables import (
    RunnablePassthrough,
    RunnableLambda,
    RunnableParallel,
)

from langchain_retriever_demo import retriever


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


# Build parallel input branches
rag_input = RunnableParallel(
    context=retriever | RunnableLambda(format_documents),
    question=RunnablePassthrough(),
)


# User question
question = "Why is my Kubernetes Pod stuck in Pending state?"


# Execute the runnable mapping
result = rag_input.invoke(question)


# Display results
print("Question:")
print(result["question"])

print("\nRetrieved Context:")
print(result["context"])
