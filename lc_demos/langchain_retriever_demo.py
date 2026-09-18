import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from lc_demos.langchain_embeddings import GeminiEmbeddings

# Load environment variables
load_dotenv()

TOKEN = os.getenv("LLMFOUNDRY_TOKEN")

BASE_URL = "https://llmfoundry.straive.com/gemini/v1beta/openai"
EMBEDDING_MODEL = "models/gemini-embedding-001"

# Existing ChromaDB created by our manual RAG
CHROMA_PATH = (
    Path(__file__).parent.parent
    / "retrieval-augmented-generation"
    / "chroma_db"
)


# Connect LangChain to the existing embedding model
embeddings = GeminiEmbeddings()

# Connect LangChain to our existing Chroma collection
vectorstore = Chroma(
    collection_name="kubernetes_docs",
    persist_directory=str(CHROMA_PATH),
    embedding_function=embeddings
)

# Create a LangChain Retriever
retriever = vectorstore.as_retriever(
    search_kwargs={"k": 5}
)

# Test retrieval only when this file is executed directly
if __name__ == "__main__":

    query = "Why is my Kubernetes Pod stuck in Pending state?"

    docs = retriever.invoke(query)

    print("\n==============================================")
    print("LangChain Retriever Results")
    print("==============================================")

    print(f"\nRetrieved documents: {len(docs)}")

    for i, doc in enumerate(docs, start=1):

        print(f"\n----------- Result {i} -----------")

        print("Source:", doc.metadata.get("source"))
        print("Chunk:", doc.metadata.get("chunk_index"))

        print("\nContent:")
        print(doc.page_content[:500])
