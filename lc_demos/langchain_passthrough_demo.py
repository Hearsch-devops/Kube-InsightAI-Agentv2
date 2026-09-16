from langchain_core.runnables import RunnablePassthrough

passthrough = RunnablePassthrough()

question = "Why is my Kubernetes Pod stuck in Pending state?"

result = passthrough.invoke(question)

print("Original Question:")
print(question)

print("\nResult from RunnablePassthrough:")
print(result)
