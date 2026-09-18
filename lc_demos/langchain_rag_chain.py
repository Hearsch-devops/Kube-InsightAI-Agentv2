import os
import httpx

from dotenv import load_dotenv
from openai import OpenAI

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import (
    RunnablePassthrough,
    RunnableLambda,
    RunnableParallel,
)

from lc_demos.langchain_retriever_demo import retriever

# --------------------------------------------------
# 1. Format retrieved documents
# --------------------------------------------------

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


# --------------------------------------------------
# 2. Create the prompt template
# --------------------------------------------------

prompt = ChatPromptTemplate.from_template("""
You are a Kubernetes troubleshooting assistant.

Answer the user's question using only the provided context.

If the answer is not present in the context, say:
"I don't have enough information in the provided context."

Explain the answer clearly and include kubectl commands when useful.

Context:
{context}

User Question:
{question}
""")


# --------------------------------------------------
# 3. Configure the LLM
# --------------------------------------------------

load_dotenv()

TOKEN = os.getenv("LLMFOUNDRY_TOKEN")

client = OpenAI(
    api_key=TOKEN,
    base_url="https://llmfoundry.straive.com/gemini/v1beta/openai",
)


def call_llm(prompt_value):
    messages = [
        {
            "role": message.type,
            "content": message.content,
        }
        for message in prompt_value.to_messages()
    ]

    # Convert LangChain message types to OpenAI roles
    for message in messages:
        if message["role"] == "human":
            message["role"] = "user"
        elif message["role"] == "ai":
            message["role"] = "assistant"

    response = client.chat.completions.create(
        model="models/gemini-2.5-flash",
        messages=messages,
        temperature=0,
    )

    return response.choices[0].message.content


# --------------------------------------------------
# 4. Build the RAG chain
# --------------------------------------------------

rag_chain = (
    RunnableParallel(
        context=retriever | RunnableLambda(format_documents),
        question=RunnablePassthrough(),
    )
    | prompt
    | RunnableLambda(call_llm)
    | StrOutputParser()
)
