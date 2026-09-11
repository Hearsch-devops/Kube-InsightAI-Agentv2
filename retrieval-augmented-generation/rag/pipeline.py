from .generator import generate_answer


def run_rag(query):
    """
    Run the complete Retrieval-Augmented Generation pipeline.

    Flow:
        User Query
            ↓
        Retrieval
            ↓
        Context Construction
            ↓
        LLM Generation
            ↓
        Final Answer
    """

    return generate_answer(query)


if __name__ == "__main__":

    query = "Why is my Kubernetes Pod stuck in Pending state?"

    answer = run_rag(query)

    print("\n==============================================")
    print("RAG Answer")
    print("==============================================")
    print(answer)
