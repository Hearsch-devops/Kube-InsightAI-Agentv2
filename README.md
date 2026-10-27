> **📝 Note — Previewing Mermaid Diagrams in VS Code**
>
> To view the architecture diagrams and workflow charts in this README:
>
> 1. Install the **Markdown Preview Mermaid Support** extension in VS Code.
> 2. Open `README.md`.
> 3. Press **`Ctrl + Shift + V`** to open the Markdown preview.
> 4. The Mermaid diagrams will render visually in the preview.
>
> Alternatively, use **`Ctrl + K`**, then **`V`** to open the preview to the side.

------------------------------------------------------------------------

# Kube-InsightAI-Agentv2.0

**An AI-powered Kubernetes troubleshooting assistant that combines
LangGraph orchestration, LangChain retrieval, MCP-based live cluster
investigation, and evidence-based root-cause analysis.**

Kube-InsightAI helps users ask Kubernetes and DevOps questions through a
web interface. The FastAPI backend routes requests into specialized
workflows: Kubernetes documentation retrieval, live cluster queries
through a Model Context Protocol (MCP) server, general responses, and
remediation proposals.

> **Safety boundary:** Remediation requests produce proposals only. The
> documented remediation-proposal workflow does not execute Kubernetes
> changes.

------------------------------------------------------------------------

## Table of Contents

-   [Overview](#overview)
-   [Key Features](#key-features)
-   [Architecture](#architecture)
-   [Request Workflow](#request-workflow)
-   [Technology Stack](#technology-stack)
-   [Repository Structure](#repository-structure)
-   [LLM Configuration](#llm-configuration)
-   [RAG and Knowledge Retrieval](#rag-and-knowledge-retrieval)
-   [MCP and Live Kubernetes
    Investigation](#mcp-and-live-kubernetes-investigation)
-   [Remediation Safety](#remediation-safety)
-   [Running Locally](#running-locally)
-   [Kubernetes Deployment](#kubernetes-deployment)
-   [Testing](#testing)
-   [Security Notes](#security-notes)
-   [Troubleshooting](#troubleshooting)

------------------------------------------------------------------------

## Overview

Kubernetes troubleshooting often requires moving between cluster state,
pod logs, Kubernetes events, operational documentation, and possible
corrective actions. Kube-InsightAI brings these activities into a
conversational workflow.

The main LangGraph workflow is defined in `app/langgraph/graph.py`. It
analyzes a user's question, routes it based on intent, and invokes the
appropriate response path.

### Main workflows

  -----------------------------------------------------------------------
  Workflow                            What it does
  ----------------------------------- -----------------------------------
  Kubernetes documentation            Retrieves relevant Kubernetes SOP
                                      content through the configured
                                      LangChain retriever and generates
                                      an answer using that context.

  Live cluster query                  Calls Kubernetes tools through an
                                      MCP client and the deployed
                                      Kubernetes MCP server.

  Root-cause analysis (RCA)           Uses live investigation evidence to
                                      generate an evidence-based
                                      explanation, confidence level,
                                      recommendations, and verification
                                      steps.

  General DevOps response             Generates a response for questions
                                      routed to the general workflow.

  Remediation proposal                Describes a proposed action and
                                      target resource without executing
                                      the operation.
  -----------------------------------------------------------------------

## Key Features

-   **Intent-based routing with LangGraph** for documentation,
    live-cluster, general, investigation, and remediation requests.
-   **LangChain-based retrieval** of Kubernetes SOP content for
    documentation-focused answers.
-   **MCP integration** for retrieving live Kubernetes information
    through a dedicated server.
-   **Evidence-based RCA** that distinguishes confirmed evidence, likely
    causes, possible contributing factors, and uncertainty.
-   **LLM integration** through LangChain's `ChatOpenAI` interface,
    configured for Gemini 2.5 Flash through LLMFoundry.
-   **Remediation proposals** that clearly state that no Kubernetes
    operation was executed.
-   **FastAPI backend** with separate main, authentication,
    administration, and remediation routers.
-   **Kubernetes manifests** for deploying application components and
    configuring cluster access.
-   **Automated tests** in the `tests/` and `scripts/` directories.

------------------------------------------------------------------------

## Architecture

### High-level application architecture

``` mermaid
flowchart TB
    USER([User])
    UI[Web Dashboard and Assistant]
    API[FastAPI Application]
    ROUTES[API Routers<br/>Main · Authentication · Admin · Remediation]
    GRAPH[LangGraph Workflow]

    LLM[LangChain ChatOpenAI]
    FOUNDRY[LLMFoundry OpenAI-Compatible Endpoint]
    GEMINI[Gemini 2.5 Flash]

    RETRIEVER[LangChain Retriever]
    SOP[(Kubernetes SOP Knowledge Base)]

    MCPCLIENT[MCP Client<br/>Streamable HTTP]
    SERVICE[Kubernetes MCP ClusterIP Service]
    MCP[MCP Server Deployment]
    K8SAPI[Kubernetes API Server]
    RESOURCES[Pods · Logs · Events · Deployments · Services]

    DB[(Application Database)]

    USER --> UI --> API
    API --> ROUTES
    ROUTES --> GRAPH
    API <--> DB

    GRAPH --> LLM
    LLM --> FOUNDRY --> GEMINI

    GRAPH --> RETRIEVER
    SOP --> RETRIEVER

    GRAPH --> MCPCLIENT
    MCPCLIENT <--> SERVICE
    SERVICE <--> MCP
    MCP <--> K8SAPI
    K8SAPI <--> RESOURCES
```

This is a component-level overview, not a literal trace of every
request. Individual workflows use only the components needed for the
request. The exact database engine and schema depend on the active
database configuration.

### Main LangGraph request flow

``` mermaid
flowchart TD
    START([User Question]) --> ANALYZE[Analyze Question with LLM]
    ANALYZE --> ROUTER{Intent Router}

    ROUTER -->|Kubernetes documentation| RETRIEVE[Retrieve SOP Context]
    RETRIEVE --> K8S[Generate Kubernetes Answer]
    K8S --> END1([End])

    ROUTER -->|Live cluster query or investigation| MCP[Query Kubernetes through MCP]
    MCP --> CHECK{Investigation Intent?}
    CHECK -->|Yes| RCA[Analyze Live Evidence and Recommend Actions]
    RCA --> END2([End])
    CHECK -->|No| END3([End])

    ROUTER -->|General question| GENERAL[Generate General Response]
    GENERAL --> END4([End])

    ROUTER -->|Remediation proposal| REM[Create Proposal Only]
    REM --> END5([End])
```

The router is intent-based and uses phrase/keyword checks in the current
implementation. It is not a general-purpose classifier model. The
graph's MCP branch proceeds to RCA when `investigation_intent` is true;
ordinary MCP requests can end after the MCP workflow.

------------------------------------------------------------------------

## Request Workflow

1.  **Receive a request:** The user interacts with the web frontend,
    which sends requests to the FastAPI backend.
2.  **Analyze the question:** The main graph invokes the configured chat
    model to create a short analysis of the question.
3.  **Route by intent:** The router selects the Kubernetes
    documentation, MCP, general-response, or remediation-proposal path.
4.  **Retrieve information:** Documentation requests retrieve relevant
    SOP content; live requests call MCP tools to query Kubernetes.
5.  **Generate a response:** The relevant response node uses the
    configured LLM and available context.
6.  **Return the answer:** The API returns the workflow result to the
    frontend.

For investigation requests, the RCA prompt instructs the model to avoid
inventing cluster facts, distinguish confirmed evidence from hypotheses,
state confidence, recommend prioritized actions, and provide manual
verification steps.

------------------------------------------------------------------------

## Technology Stack

  ---------------------------------------------------------------------------
  Area                                Technology / implementation
  ----------------------------------- ---------------------------------------
  Frontend                            HTML, CSS, JavaScript

  Backend API                         FastAPI

  Workflow orchestration              LangGraph

  LLM integration                     LangChain `ChatOpenAI`

  Configured model                    Gemini 2.5 Flash through LLMFoundry

  Retrieval                           LangChain retriever imported by the
                                      main graph

  Separate RAG implementation         Custom Python pipeline with ChromaDB
                                      under
                                      `retrieval-augmented-generation/rag/`

  Tool integration                    Model Context Protocol (MCP),
                                      Streamable HTTP client

  Cluster integration                 Kubernetes Python client in the MCP
                                      server

  Database                            Initialized through `app/database.py`;
                                      verify the active configuration for the
                                      selected database engine

  Containerization                    Docker

  Orchestration                       Kubernetes

  CI/CD                               Jenkins pipeline (`Jenkinsfile`)

  Testing                             pytest and API/security test scripts
  ---------------------------------------------------------------------------

------------------------------------------------------------------------

## Repository Structure

The following is a curated view of the main repository areas. It omits
generated databases, local vector-store contents, and experimental files
to keep the overview readable.

``` text
Kube-InsightAI-Agentv2.0/
├── app/
│   ├── agent/
│   │   ├── graph.py
│   │   └── state.py
│   ├── api/
│   │   ├── admin_routes.py
│   │   ├── auth_routes.py
│   │   ├── remediation_routes.py
│   │   └── routes.py
│   ├── langgraph/
│   │   ├── graph.py
│   │   └── state.py
│   ├── llm/
│   │   └── llm.py
│   ├── mcp/
│   │   ├── remediation.py
│   │   ├── client.py
│   │   └── server.py
│   ├── main.py
│   ├── mcp_client.py
│   ├── auth.py
│   ├── database.py
│   └── recommendations.py
├── frontend/
│   ├── assistant/
│   │   ├── assistant.html
│   │   ├── assistant.css
│   │   └── assistant.js
│   ├── dashboard/
│   │   ├── dashboard.html
│   │   ├── dashboard.css
│   │   └── auth.js
│   └── nginx.conf
├── kubernetes-manifests/
│   ├── agent.yaml
│   ├── frontend.yaml
│   ├── mcp.yaml
│   ├── namespace.yaml
│   ├── kube-insightai-pv.yaml
│   ├── kube-insightai-rbac.yaml
│   ├── app-admin-rbac.yaml
│   ├── approval-rbac.yaml
│   └── testing-files/
├── retrieval-augmented-generation/
│   ├── knowledge_base/
│   │   └── kubernetes/
│   ├── rag/
│   │   ├── document_loader.py
│   │   ├── text_splitter.py
│   │   ├── embeddings.py
│   │   ├── vector_store.py
│   │   ├── retriever.py
│   │   ├── generator.py
│   │   └── pipeline.py
│   ├── experiments/
│   └── Info.md
├── lc_demos/
│   ├── langchain_retriever_demo.py
│   ├── langchain_rag_chain.py
│   └── other LangChain learning/demo scripts
├── scripts/
│   ├── create_admin.py
│   ├── switch-to-gemini.sh
│   ├── switch-to-llmfoundry.sh
│   └── API and integration test scripts
├── tests/
├── Dockerfile
├── Dockerfile.frontend
├── Dockerfile.mcp
├── Jenkinsfile
├── requirements.txt
├── requirements-mcp.txt
├── pytest.ini
├── .env.example
└── README.md
```

### Important implementation distinction

The main application graph imports its retriever from
`lc_demos/langchain_retriever_demo.py` and document formatting from
`lc_demos/langchain_rag_chain.py`.

The custom pipeline in `retrieval-augmented-generation/rag/` has its own
document loading, splitting, embedding, ChromaDB, retrieval, and
generation modules. Treat it as a separate RAG implementation unless it
is explicitly wired into the main graph.

The repository also contains `app/agent/graph.py`, which is a separate
graph from the primary workflow in `app/langgraph/graph.py`. Do not
assume the two graphs are connected without checking the relevant call
sites.

------------------------------------------------------------------------

## LLM Configuration

The active LLM helper in `app/llm/llm.py` uses LangChain's `ChatOpenAI`
interface with an OpenAI-compatible LLMFoundry endpoint.

  Setting                 Current configuration
  ----------------------- -------------------------------------------------------
  LangChain class         `ChatOpenAI`
  Configured model        `models/gemini-2.5-flash`
  Endpoint                `https://llmfoundry.straive.com/gemini/v1beta/openai`
  Temperature             `0`
  Environment variables   `LLMFOUNDRY_TOKEN`, `PROJECT_NAME`

Create a local `.env` file using the example below, then fill in your
own values:

``` dotenv
LLMFOUNDRY_TOKEN=your_token_here
PROJECT_NAME=your_project_name
```

Do not commit `.env` or real credentials to source control.

The helper constructs the API key as `TOKEN:PROJECT`, as required by the
current configuration. It raises an error when either environment
variable is missing.

### Provider switching

The repository includes:

-   `scripts/switch-to-llmfoundry.sh`
-   `scripts/switch-to-gemini.sh`

Review these scripts and the deployment configuration before relying on
a provider switch. In the currently shared `app/llm/llm.py`, the base
URL points to LLMFoundry; changing Kubernetes Secret values alone does
not prove that the application switches to Google's direct Gemini
endpoint.

------------------------------------------------------------------------

## RAG and Knowledge Retrieval

The main graph's documentation workflow uses a LangChain retriever to
find relevant Kubernetes SOP content.

### Main application path

``` mermaid
flowchart LR
    Q[User Kubernetes Question]
    R[LangChain Retriever]
    DOCS[Retrieved SOP Documents]
    FORMAT[Format Document Context]
    PROMPT[Question + Analysis + Context]
    LLM[Configured Chat Model]
    A[Markdown Answer]

    Q --> R --> DOCS --> FORMAT --> PROMPT --> LLM --> A
```

The `retrieve_context()` node:

1.  Extracts the user's question.
2.  Invokes the configured retriever.
3.  Formats the returned documents.
4.  Stores the context and source metadata in graph state.
5.  Handles retrieval errors by returning empty context and an error
    message.

The `kubernetes_response()` node uses the retrieved context as its
primary information source and instructs the model not to invent
live-cluster details.

### Separate custom RAG pipeline

The `retrieval-augmented-generation/rag/` directory contains a separate
implementation with modules for:

-   Loading Kubernetes knowledge-base documents.
-   Splitting Markdown content into chunks.
-   Creating embeddings.
-   Persisting vectors in ChromaDB.
-   Retrieving relevant documents.
-   Generating an answer from retrieved content.
-   Running the pipeline through `pipeline.py`.

The directory also includes retrieval experiments such as basic
retrieval, structure-aware retrieval, hybrid retrieval, MMR, and LLM
reranking. These are repository experiments; do not assume every
experiment is enabled in the production request path.

------------------------------------------------------------------------

## MCP and Live Kubernetes Investigation

The main application's MCP client is `app/mcp_client.py`. It uses the
MCP Python client with **Streamable HTTP** and connects to the
configured Kubernetes MCP endpoint.

The Kubernetes manifest `kubernetes-manifests/mcp.yaml` defines a
Kubernetes MCP server Deployment and a ClusterIP Service on port `8001`
in the `kube-insightaiv2` namespace.

### Live investigation path

``` mermaid
flowchart LR
    GRAPH[LangGraph MCP Workflow]
    CLIENT[app/mcp_client.py]
    SVC[ClusterIP Service<br/>Port 8001]
    SERVER[MCP Server]
    PYCLIENT[Kubernetes Python Client]
    API[Kubernetes API Server]
    OBJECTS[Cluster Resources]

    GRAPH <--> CLIENT
    CLIENT <--> SVC
    SVC <--> SERVER
    SERVER <--> PYCLIENT
    PYCLIENT <--> API
    API <--> OBJECTS
```

The MCP server exposes tools for retrieving Kubernetes information. The
exact set of available operations and access scope depend on
`app/mcp/server.py`, the Kubernetes Python client configuration, and the
applicable RBAC manifests.

### Namespace behavior

The shared `mcp_response()` implementation attempts to extract a
namespace from the question. When none is specified, it defaults to:

``` text
kube-insightaiv2
```

For requests involving logs, health checks, ownership, or investigation,
the workflow first retrieves pods from the selected namespace and uses
that information to resolve the requested pod or component.

------------------------------------------------------------------------

## Remediation Safety

Kube-InsightAI currently has two distinct remediation-related behaviors:

1.  **Standalone proposal workflow:** Builds a remediation proposal from
    the request and returns the action, resource kind, resource name,
    namespace, and reason. It explicitly states that no Kubernetes
    operation was executed.
2.  **Evidence-based remediation request:** When the request explicitly
    asks for a remediation based on live evidence, the router sends it
    through MCP investigation and RCA so recommendations can be based on
    collected evidence.

The RCA prompt directs the model to: - Avoid inventing resource state,
events, logs, timestamps, or configuration. - Distinguish confirmed
evidence from likely causes and possible contributing factors. - State a
confidence level and explain uncertainty. - Prioritize targeted
diagnostics and low-risk checks before disruptive changes. - Flag risky
operations and provide manual verification steps.

**No automatic remediation execution is established by the reviewed
graph code.** Any future execution feature should include explicit
authorization, least-privilege RBAC, approval gates where appropriate,
audit logging, and post-action verification.

------------------------------------------------------------------------

## Running Locally

The exact dependency set and startup command should match your current
environment and `requirements.txt`. The following is a general local
setup for the FastAPI application.

### 1. Clone the repository

``` bash
git clone <your-repository-url>
cd <your-repository-directory>
```

Replace the placeholders with your repository URL and directory name.

### 2. Create and activate a virtual environment

Linux/macOS:

``` bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

``` powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

``` bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If you are developing or running the MCP server separately, review
`requirements-mcp.txt` and install the dependencies required for that
component.

### 4. Configure environment variables

Create `.env` from `.env.example` if it contains the settings for your
current environment. Ensure at least the required LLM variables are
configured:

``` dotenv
LLMFOUNDRY_TOKEN=your_token_here
PROJECT_NAME=your_project_name
```

Also configure any database, MCP endpoint, authentication, and
application settings required by your local environment. Use the actual
variable names expected by the code; do not assume this example lists
every required setting.

### 5. Start the API

From the repository root:

``` bash
uvicorn app.main:app --reload
```

The FastAPI application defines a root health endpoint at `/` that
returns a simple service status. With the default Uvicorn port, it is
available at:

``` text
http://127.0.0.1:8000/
```

FastAPI's interactive API documentation is normally available at `/docs`
when enabled by the application configuration.

> The API process alone does not guarantee that the frontend, database,
> LLM provider, or MCP server is configured and reachable. Configure and
> start each required dependency for the workflows you want to test.

------------------------------------------------------------------------

## Kubernetes Deployment

Kubernetes manifests are stored in `kubernetes-manifests/`.

Relevant files include:

  -----------------------------------------------------------------------
  Manifest                            Purpose indicated by the filename
  ----------------------------------- -----------------------------------
  `namespace.yaml`                    Application namespace

  `agent.yaml`                        Agent/backend deployment resources

  `frontend.yaml`                     Frontend deployment/service
                                      resources

  `mcp.yaml`                          Kubernetes MCP server Deployment
                                      and ClusterIP Service

  `kube-insightai-rbac.yaml`          Kubernetes access permissions for
                                      the application

  `app-admin-rbac.yaml`               Application administration-related
                                      RBAC resources

  `approval-rbac.yaml`                Approval-related RBAC resources

  `kube-insightai-pv.yaml`            Persistent volume resources
  -----------------------------------------------------------------------

Before deploying:

1.  Review image names and tags in the manifests.
2.  Confirm the namespace and Service names match the application
    configuration.
3.  Create or update Kubernetes Secrets for LLM credentials and other
    sensitive configuration.
4.  Verify ServiceAccount bindings and RBAC permissions grant only the
    required access.
5.  Confirm storage configuration matches your cluster's available
    storage.
6.  Apply manifests in the order required by their dependencies.
7.  Verify pod readiness, Services, and logs after deployment.

Example inspection commands:

``` bash
kubectl get namespaces
kubectl get pods -n kube-insightaiv2
kubectl get services -n kube-insightaiv2
kubectl get deployments -n kube-insightaiv2
kubectl logs deployment/kube-insightaiv2-mcp -n kube-insightaiv2
```

The final command assumes the MCP Deployment is named
`kube-insightaiv2-mcp`, as shown in the supplied manifest. Confirm
actual resource names before running commands in a different
environment.

The repository includes a `Jenkinsfile` and Dockerfiles for the
application, frontend, and MCP server. Review those files for the
current build, image-tagging, and deployment pipeline details.

------------------------------------------------------------------------

## Testing

The repository contains tests under `tests/` and additional
API/integration scripts under `scripts/`.

Run the configured pytest suite from the repository root:

``` bash
pytest
```

You can also run an individual test file, for example:

``` bash
pytest tests/test_remediation.py
pytest tests/test_remediation_api.py
pytest tests/test_remediation_persistence.py
pytest tests/test_database_migration.py
```

Additional scripts cover areas such as authentication,
authorization/RBAC, administration APIs, audit APIs, MCP clients,
LangGraph, and remediation. Inspect each script before running it
because some may require a live API, a Kubernetes cluster, configured
credentials, or other services.

For CI/CD, configure the pipeline to fail when the required automated
tests fail. Run tests before building and publishing deployment images.

------------------------------------------------------------------------

## Security Notes

-   Keep `.env`, API tokens, passwords, and Kubernetes Secret values out
    of Git.
-   Use `.env.example` for placeholder values only.
-   Restrict Kubernetes access through least-privilege RBAC and a
    dedicated ServiceAccount.
-   Review the exact permissions granted to the agent and MCP server
    before exposing them to a cluster.
-   Protect authentication and administrative endpoints.
-   Avoid logging credentials or sensitive application data.
-   Treat live-cluster output and logs as operationally sensitive.
-   Validate remediation targets and require appropriate authorization
    before any future execution capability.
-   Do not grant broad permissions or remove control-plane taints just
    to make a workload schedule.
-   Use image tags that can be traced to a specific build and follow
    your organization's image-scanning and deployment practices.

------------------------------------------------------------------------

## Troubleshooting

### LLM provider configuration error

If the application reports that `LLMFOUNDRY_TOKEN` or `PROJECT_NAME` is
not configured:

1.  Check that the variables exist in the environment loaded by the
    running process.
2.  Verify `.env` is located where `load_dotenv()` can find it, or
    inject the variables through your deployment configuration.
3.  Confirm the Kubernetes Secret keys match the environment variable
    names expected by the application.
4.  Restart or roll out the application after changing environment
    variables or Secret references, as appropriate.

Do not paste tokens into logs, issue trackers, or public repositories.

### MCP connection failure

1.  Confirm the MCP Deployment is ready.
2.  Check the ClusterIP Service name and port.
3.  Confirm the configured `KUBERNETES_MCP_URL` matches the in-cluster
    Service and MCP endpoint path.
4.  Inspect MCP server logs.
5.  Verify the ServiceAccount and RBAC permissions allow the requested
    operation.

### RAG returns no useful context

1.  Confirm the configured main retriever is available.
2.  Verify the Kubernetes SOP documents are present and indexed as
    expected.
3.  Inspect retrieval logs and document metadata.
4.  Remember that the main graph uses the retriever from `lc_demos/`;
    the separate custom pipeline under
    `retrieval-augmented-generation/rag/` is not automatically the
    active main-graph retriever.

### Live investigation lacks enough evidence

The RCA workflow is designed to acknowledge insufficient evidence
instead of inventing a cause. Check that the MCP tool call succeeded and
that the returned context includes relevant pod state, owner
information, events, and logs.

### Kubernetes resource not found

1.  Confirm the requested namespace.
2.  Remember that the MCP workflow defaults to `kube-insightaiv2` if no
    namespace is detected.
3.  Verify the resource name against the actual cluster.
4.  Check that the MCP server's Kubernetes identity has permission to
    list or inspect the resource.

------------------------------ END -------------------------------------