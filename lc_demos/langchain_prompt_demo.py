from langchain_core.prompts import ChatPromptTemplate


prompt = ChatPromptTemplate.from_template(
    """
You are a Kubernetes troubleshooting assistant.

Answer the user's question using the provided Kubernetes documentation.

Rules:
- Use the context as your primary source.
- Do not invent facts that are not supported by the context.
- Give practical troubleshooting steps.
- If the context does not contain enough information, say so.

Context:
{context}

User Question:
{question}
"""
)


context = """
Source: scheduling.md

A Pod may remain in Pending state when the Kubernetes scheduler
cannot find a suitable node. Check node resources, scheduling
constraints, taints, and tolerations.

---

Source: pod.md

A Pod is the smallest deployable unit in Kubernetes.
"""


question = "Why is my Kubernetes Pod stuck in Pending state?"


formatted_prompt = prompt.invoke(
    {
        "context": context,
        "question": question
    }
)


print("\n==============================================")
print("Formatted Prompt")
print("==============================================")

print(formatted_prompt)
