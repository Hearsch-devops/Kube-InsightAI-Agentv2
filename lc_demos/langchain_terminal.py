from langchain_rag_chain import rag_chain


while True:
    question = input(
        "\nAsk a Kubernetes question (or type 'exit' to quit): "
    )

    if question.lower() == "exit":
        print("Exiting Kube-InsightAI...")
        break

    if not question.strip():
        print("Please enter a question.")
        continue

    print("\nSearching Kubernetes knowledge base...")

    answer = rag_chain.invoke(question)

    print("\n==============================================")
    print("Kube-InsightAI Answer")
    print("==============================================\n")
    print(answer)
