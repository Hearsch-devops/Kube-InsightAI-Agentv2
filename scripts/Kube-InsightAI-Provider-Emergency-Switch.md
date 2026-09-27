Kube-InsightAI Provider Emergency Switch

Purpose

Use this guide only if LLM Foundry is unavailable and the application needs to use the direct Gemini API.

The Kubernetes Secret scripts switch the token stored in the existing Secret. They do not change the Jenkins credential name.

1. Switch Kubernetes Secret to Gemini

Run on the Kubernetes control-plane/admin server:

cd ~/kube-insight-ai-agentv-2
bash scripts/switch-to-gemini.sh

The script:

Prompts for the Gemini API key securely.

Stores it as LLMFOUNDRY_TOKEN.

Preserves PROJECT_NAME=kube-insight-ai.

Restarts kube-insightaiv2-agent.

Waits for the rollout.

Verify:

kubectl get pods -n kube-insightaiv2

Expected:

kube-insightaiv2-agent   1/1   Running

2. Application Changes for Gemini

app/llm/llm.py

Change:

BASE_URL = "https://llmfoundry.straive.com/gemini/v1beta/openai"

to:

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

Change:

api_key=f"{TOKEN}:{PROJECT}"

to:

api_key=TOKEN

PROJECT_NAME is not required for direct Gemini API-key authentication.

retrieval-augmented-generation/rag/embeddings.py

Change:

BASE_URL = "https://llmfoundry.straive.com/gemini/v1beta/openai"

to:

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

Keep the existing Bearer-token authentication and:

MODEL_NAME = "models/gemini-embedding-001"

3. Jenkins Credential

Keep the existing Jenkins credential ID unchanged:

llmfoundry_token

For emergency Gemini mode, update the secret value stored under this credential to the Gemini API key. Do not rename the credential.

4. Build and Deploy

After the application changes:

git add app/llm/llm.py retrieval-augmented-generation/rag/embeddings.py
git commit -m "chore: add Gemini emergency provider fallback"
git push origin main

Then run the Jenkins pipeline.

5. Test the Application

After deployment:

curl -s -X POST \
  http://192.168.48.169:30082/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Explain Kubernetes in one sentence."}'

Kubernetes/RAG test:

curl -s -X POST \
  http://192.168.48.169:30082/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What Kubernetes resources are currently running in this namespace?"}'

6. Roll Back to LLM Foundry

When LLM Foundry is available again:

cd ~/kube-insight-ai-agentv-2
bash scripts/switch-to-llmfoundry.sh

Enter the LLM Foundry token when prompted.

Restore app/llm/llm.py:

BASE_URL = "https://llmfoundry.straive.com/gemini/v1beta/openai"

and:

api_key=f"{TOKEN}:{PROJECT}"

Restore retrieval-augmented-generation/rag/embeddings.py:

BASE_URL = "https://llmfoundry.straive.com/gemini/v1beta/openai"

Then commit, push, and run Jenkins again.

Quick Reference

Item

LLM Foundry

Emergency Gemini

LLM URL

https://llmfoundry.straive.com/gemini/v1beta/openai

https://generativelanguage.googleapis.com/v1beta/openai/

LLM auth

TOKEN:PROJECT

TOKEN

Embedding URL

https://llmfoundry.straive.com/gemini/v1beta/openai

https://generativelanguage.googleapis.com/v1beta/openai/

Embedding model

models/gemini-embedding-001

models/gemini-embedding-001

Jenkins credential ID

llmfoundry_token

llmfoundry_token

Kubernetes Secret

kube-insightai-llm

kube-insightai-llm

PROJECT_NAME

kube-insight-ai

kube-insight-ai

Important

Do not give the Kube-InsightAI agent additional Kubernetes Secret permissions. The switch scripts are intended to run from an administrative Kubernetes context on the control-plane server.