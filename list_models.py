from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/ai-devops-agent/.env")

client = OpenAI(
    api_key=os.getenv("LLMFOUNDRY_TOKEN"),
    base_url="https://llmfoundry.straive.com/gemini/v1beta/openai"
)

models = client.models.list()

for model in models.data:
    print(model.id)
