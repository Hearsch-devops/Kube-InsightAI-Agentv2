from langchain_core.runnables import RunnableLambda


def add_exclamation(text):
    return text + "!"


runnable = RunnableLambda(add_exclamation)

result = runnable.invoke("Hello LangChain")

print(result)
