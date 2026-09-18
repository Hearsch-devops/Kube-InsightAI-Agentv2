import os

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI


load_dotenv()

BASE_URL = "https://llmfoundry.straive.com/gemini/v1beta/openai"
MODEL_NAME = "models/gemini-2.5-flash"
TOKEN = os.getenv("LLMFOUNDRY_TOKEN")


prompt = ChatPromptTemplate.from_template(
    """
    You are a Kubernetes assistant.

    Explain this Kubernetes concept clearly:

    {topic}
    """
)

model = ChatOpenAI(
    model=MODEL_NAME,
    api_key=TOKEN,
    base_url=BASE_URL
)

parser = StrOutputParser()

chain = prompt | model | parser


topics = [
    "What is a Kubernetes Pod?",
    "What is a Kubernetes Deployment?",
    "What is a Kubernetes Service?"
]


for topic in topics:
    result = chain.invoke({"topic": topic})

    print("\n================================")
    print(topic)
    print("================================")
    print(result)
