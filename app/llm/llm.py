import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

TOKEN = os.getenv("LLMFOUNDRY_TOKEN")
PROJECT = os.getenv("PROJECT_NAME")

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"


def get_chat_model():
    """
    Create the LangChain chat model connected to LLMFoundry.
    """

    if not TOKEN:
        raise ValueError("LLMFOUNDRY_TOKEN is not configured")

    if not PROJECT:
        raise ValueError("PROJECT_NAME is not configured")

    return ChatOpenAI(
        model="models/gemini-2.5-flash",
        base_url=BASE_URL,
        api_key=TOKEN,
        temperature=0,
    )


def get_llm_response(message: str) -> str:
    """
    Existing simple LLM call.
    Keeps our current CalcCast behavior working.
    """

    llm = get_chat_model()

    response = llm.invoke(message)

    return response.content