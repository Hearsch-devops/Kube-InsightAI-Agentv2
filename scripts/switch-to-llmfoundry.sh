#!/bin/bash

set -euo pipefail

NAMESPACE="kube-insightaiv2"
SECRET_NAME="kube-insightai-llm"
DEPLOYMENT_NAME="kube-insightaiv2-agent"
PROJECT_NAME="kube-insight-ai"

echo "============================================"
echo " Kube-InsightAI - Switch to LLM Foundry"
echo "============================================"
echo

read -r -s -p "Enter LLM Foundry token: " LLMFOUNDRY_TOKEN
echo

if [[ -z "$LLMFOUNDRY_TOKEN" ]]; then
    echo "ERROR: LLM Foundry token cannot be empty."
    exit 1
fi

echo
echo "Updating Kubernetes secret..."

kubectl create secret generic "$SECRET_NAME" \
    -n "$NAMESPACE" \
    --from-literal=LLMFOUNDRY_TOKEN="$LLMFOUNDRY_TOKEN" \
    --from-literal=PROJECT_NAME="$PROJECT_NAME" \
    --dry-run=client \
    -o yaml | kubectl apply -f -

echo
echo "Secret updated successfully."

echo
echo "Restarting Kube-InsightAI agent..."

kubectl rollout restart deployment/"$DEPLOYMENT_NAME" \
    -n "$NAMESPACE"

echo
echo "Waiting for rollout..."

kubectl rollout status deployment/"$DEPLOYMENT_NAME" \
    -n "$NAMESPACE" \
    --timeout=180s

echo
echo "============================================"
echo " LLM Foundry switch completed successfully."
echo "============================================"
echo