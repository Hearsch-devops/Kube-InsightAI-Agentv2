# Kube-InsightAI-Agentv2.0

An AI-powered Kubernetes troubleshooting assistant that combines a web
dashboard, FastAPI, LangGraph-based reasoning, a Kubernetes Model
Context Protocol (MCP) server, and live cluster data to help engineers
investigate Kubernetes resources and operational issues.

> **Project focus:** evidence-based Kubernetes investigations, pod
> ownership resolution, namespace-aware routing, live log retrieval, and
> a dashboard for cluster visibility and investigation history.

------------------------------------------------------------------------

## Table of Contents

-   [Overview](#overview)
-   [Key Capabilities](#key-capabilities)
-   [Architecture](#architecture)
-   [Core Workflows](#core-workflows)
    -   [AI Investigation](#1-ai-investigation)
    -   [Pod Ownership Investigation](#2-pod-ownership-investigation)
    -   [Refresh Logs API](#3-refresh-logs-api)
    -   [Namespace and Pod Routing](#4-namespace-and-pod-routing)
    -   [Investigation History](#5-investigation-history)
-   [Repository Structure](#repository-structure)
-   [Technology Stack](#technology-stack)
-   [API Reference](#api-reference)
-   [Configuration](#configuration)
-   [Run Locally](#run-locally)
-   [Kubernetes Deployment](#kubernetes-deployment)
-   [Troubleshooting and Validation](#troubleshooting-and-validation)
-   [Security Notes](#security-notes)
-   [Roadmap](#roadmap)

------------------------------------------------------------------------

## Overview

Kube-InsightAI-Agentv2.0 is designed to help engineers ask operational
questions in natural language and receive answers grounded in Kubernetes
data and project knowledge.

Examples include:

-   "What pods are currently running in namespace `kube-insightaiv2`?"
-   "Why is `demo-pod1` failing in namespace `testing-files`?"
-   "Who owns this pod, and which Deployment manages it?"
-   "Show the logs for a specific pod over a selected time range."
-   "Investigate why a pod is unschedulable. Use the pod specification,
    node labels and taints, and scheduling events as evidence."

The system should distinguish **retrieved cluster evidence** from
**reasoned conclusions**. It should not claim to have inspected a
resource unless the relevant data was returned by the Kubernetes MCP
tools.

## Key Capabilities

-   **AI-assisted troubleshooting:** route user questions to the
    appropriate knowledge or live-cluster workflow.
-   **RAG and LangGraph:** combine Kubernetes reference material with
    structured investigation steps.
-   **MCP integration:** retrieve Kubernetes resources and logs through
    a dedicated MCP server.
-   **Pod ownership resolution:** follow ownership relationships such as
    `Pod → ReplicaSet → Deployment`; identify standalone pods.
-   **Namespace-aware investigations:** keep the requested namespace and
    pod identity consistent through the request path.
-   **Logs Explorer:** select a pod and time range, apply filters or
    refresh, and inspect retrieved logs. The frontend uses the shared
    authenticated request helper (`window.KubeAuth.apiFetch`).
-   **Cluster dashboard:** namespace selection, recent activity, system
    events, ingress data, and cluster metrics.
-   **Investigation History:** store and retrieve previous
    investigations through the API and PostgreSQL.
-   **Authentication and administration:** dedicated authentication and
    admin route modules.
-   **Kubernetes delivery:** containerized services deployed with
    Kubernetes manifests and a Jenkins pipeline.

The dashboard keeps the **Cluster**, **Logs**, **Recommendations**, and
**History** experiences. Monitoring was removed as a separate section
because cluster health and metrics are already represented in Cluster.

------------------------------------------------------------------------

## Architecture

``` mermaid
flowchart TB
    U[Engineer / User] --> UI[Web Dashboard]
    UI --> AUTH[Authenticated API Requests]
    AUTH --> API[FastAPI Application<br/>app/main.py]
    API --> ROUTES[API Routers<br/>app/api/]
    ROUTES --> GRAPH[LangGraph Workflow<br/>app/langgraph/graph.py]
    ROUTES --> CLIENT[MCP Client<br/>app/mcp_client.py]
    GRAPH --> CLIENT
    CLIENT --> MCP[Kubernetes MCP Server<br/>app/mcp/server.py]
    MCP --> K8S[Kubernetes API]
    GRAPH --> RAG[Kubernetes Knowledge / RAG]
    API --> DB[(PostgreSQL<br/>Investigation History)]
    MCP --> RESULTS[Live Resource Data<br/>Pods, Events, Ownership, Logs]
    RESULTS --> GRAPH
    GRAPH --> ANSWER[Evidence-based Response]
    ANSWER --> UI
    DB --> UI
```

### Main components

  -----------------------------------------------------------------------
  Component                           Responsibility
  ----------------------------------- -----------------------------------
  Web dashboard                       User interface for Cluster, Logs,
                                      Recommendations, History, and
                                      administrative screens

  `app/main.py`                       Creates the FastAPI application,
                                      initializes the database, and
                                      registers routers

  `app/api/routes.py`                 Main Kubernetes and agent API
                                      routes; calls MCP tools and
                                      normalizes MCP results

  `app/api/auth_routes.py`            Authentication endpoints

  `app/api/admin_routes.py`           Administrative endpoints

  `app/api/remediation_routes.py`     Remediation-related endpoints

  `app/mcp_client.py`                 Creates MCP sessions and calls
                                      tools on an MCP server

  `app/mcp/server.py`                 Exposes Kubernetes operations as
                                      MCP tools

  `app/langgraph/graph.py`            Question routing, investigation
                                      intent, ownership intent, MCP
                                      context construction, and response
                                      reasoning

  PostgreSQL                          Persists investigation history and
                                      related application data

  Kubernetes cluster                  Source of live pod, workload,
                                      event, node, and log information
  -----------------------------------------------------------------------

The Kubernetes MCP endpoint used inside the cluster is configured as:

``` text
http://kube-insightaiv2-mcp:8001/mcp
```

The value can be overridden through `KUBERNETES_MCP_URL`.

------------------------------------------------------------------------

## Core Workflows

### 1. AI Investigation

``` mermaid
flowchart TD
    A[User submits a question] --> B[Authenticated API]
    B --> C[LangGraph workflow]
    C --> D{Determine intent and route}
    D -->|Kubernetes knowledge| E[RAG / Kubernetes reference material]
    D -->|Live cluster question| F[Kubernetes MCP tools]
    D -->|Ownership question| G[Resolve pod owner]
    F --> H[Collect relevant resources and events]
    G --> H
    E --> I[Build response context]
    H --> I
    I --> J[LLM reasons over supplied evidence]
    J --> K[Return response and source/context metadata]
    K --> L[Display in dashboard]
    L --> M[Persist investigation history, where enabled]
```

The workflow is expected to use actual MCP results for live cluster
claims. If required data is missing, the response should communicate
that limitation rather than inventing pod names, events, or status
values.

### 2. Pod Ownership Investigation

Kubernetes commonly represents Deployment-managed ownership through an
intermediate ReplicaSet. The workflow resolves this chain instead of
assuming that the pod's immediate owner is the Deployment.

``` mermaid
flowchart TD
    A[Ownership question] --> B[Identify requested pod and namespace]
    B --> C[MCP: get pod owner]
    C --> D{Owner found?}
    D -->|No| E[Report standalone pod / no owner]
    D -->|Yes| F{Owner kind}
    F -->|ReplicaSet| G[Read ReplicaSet owner references]
    G --> H{Managed by Deployment?}
    H -->|Yes| I[Report ReplicaSet and Deployment]
    H -->|No| J[Report actual owner]
    F -->|Other| J
    E --> K[Compose evidence-based answer]
    I --> K
    J --> K
```

Example ownership chain:

``` text
Pod
 └── ReplicaSet
      └── Deployment
```

The ownership implementation is in `get_pod_owner()` in
`app/mcp/server.py`. Standalone pods should return no Deployment owner.
Ownership-intent detection must not depend exclusively on the literal
word `pod`; a request containing a real pod name and ownership wording
should still be recognized.

### 3. Refresh Logs API

The Logs Explorer uses an authenticated backend API to retrieve logs
from the Kubernetes MCP server.

``` mermaid
sequenceDiagram
    actor User
    participant UI as Logs Explorer
    participant Auth as window.KubeAuth.apiFetch
    participant API as FastAPI routes
    participant Client as app/mcp_client.py
    participant MCP as Kubernetes MCP
    participant K8s as Kubernetes API

    User->>UI: Select namespace, pod, and time range
    User->>UI: Click Apply or Refresh
    UI->>Auth: GET /api/cluster/logs with query parameters
    Auth->>API: Authenticated HTTP request
    API->>API: Validate request and user
    API->>Client: call_mcp_tool(...)
    Client->>MCP: get_pod_logs_by_time(...)
    MCP->>K8s: Retrieve logs for selected pod/container
    K8s-->>MCP: Log records
    MCP-->>Client: MCP tool result
    Client-->>API: Tool response
    API->>API: Normalize MCP result
    API-->>UI: JSON response with logs
    UI-->>User: Render logs and request status
```

#### Endpoint

`GET /api/cluster/logs`

Expected query parameters:

  -----------------------------------------------------------------------
  Parameter                           Purpose
  ----------------------------------- -----------------------------------
  `pod_name`                          Required pod name

  `namespace`                         Namespace containing the pod; use
                                      the selected/requested namespace

  `start_time`                        Optional beginning of the requested
                                      time range

  `end_time`                          Optional end of the requested time
                                      range

  `container`                         Optional container name for
                                      multi-container pods
  -----------------------------------------------------------------------

The backend uses the MCP tool `get_pod_logs_by_time` with the pod,
namespace, time range, and optional container. MCP failures should be
handled as upstream/tool errors (the implementation plan uses HTTP `502`
for MCP failures), not silently converted into successful empty log
results.

#### Logs UI behaviour

-   Preserve the project's purple visual theme.
-   Keep namespace and pod selection, time-range controls, quick ranges,
    Apply, manual refresh, and auto-refresh.
-   Validate the time range before making a request; the end time must
    not precede the start time.
-   Use `window.KubeAuth.apiFetch` for authenticated requests rather
    than bypassing the shared authentication flow.
-   Show loading, empty, and error states distinctly.
-   Historical log availability depends on the logging source and
    retention. Kubernetes container logs are not guaranteed to support
    arbitrary historical ranges unless an appropriate logging backend
    retains them.

### 4. Namespace and Pod Routing

The routing investigation focused on a critical correctness requirement:
when a user explicitly asks about a pod in `testing-files`, the backend
must not accidentally query the application namespace
`kube-insightaiv2`.

``` mermaid
flowchart TD
    A[Question from dashboard] --> B[Extract explicit namespace]
    B --> C[Extract requested pod / resource]
    C --> D[Detect intent]
    D --> E[Select workflow and MCP tool]
    E --> F[Build MCP arguments]
    F --> G{Namespace preserved?}
    G -->|No| H[Stop: routing/argument bug]
    G -->|Yes| I[Call Kubernetes MCP]
    I --> J[Verify returned namespace and resource name]
    J --> K[Build evidence context]
    K --> L[Generate answer]
    L --> M[Compare answer with actual MCP result]
```

#### Routing invariants

1.  **Explicit namespace wins.** If the question says
    `namespace testing-files`, carry that value through the graph and
    tool arguments.
2.  **Do not substitute the application namespace.** `kube-insightaiv2`
    is the namespace hosting the agent and MCP service; it is not the
    default target for every investigation.
3.  **Preserve the requested pod name.** Do not replace it with a
    similarly named pod or a pod selected from another namespace.
4.  **Validate MCP results.** Check the returned namespace and resource
    name before using the result as evidence.
5.  **Handle namespace-wide questions separately.** A question asking
    for all pods in a namespace should use namespace-wide discovery
    rather than requiring a single requested pod.
6.  **Keep ownership and general investigation intents distinct.** An
    ownership question should take the ownership path, while a request
    to investigate a failure may require owner, events, logs, and other
    evidence.
7.  **Log routing decisions.** Use the route and resolved-resource logs
    to correlate the user's question with the backend's actions.

Useful backend log message:

``` text
INFO:app.langgraph.graph:Question routed to: <route>
```

Useful regression check:

``` bash
kubectl logs -n kube-insightaiv2 \
  deployment/kube-insightaiv2-agent --since=30s \
  | grep "Question routed"
```

Use `--since=30s` immediately after a test so that old requests do not
get mistaken for the current request.

### 5. Investigation History

``` mermaid
flowchart LR
    A[User submits investigation] --> B[Agent processes question]
    B --> C[Response and metadata]
    C --> D[History API]
    D --> E[(PostgreSQL)]
    E --> F[History tab]
    F --> G[Review previous investigation]
```

The History experience uses the existing tab and PostgreSQL-backed API,
rather than introducing a separate duplicate page.

Known history API routes:

-   `GET /api/history` --- retrieve saved history.
-   `POST /api/history` --- save an investigation record.

The history record has included fields such as `id`, `question`,
`response`, `timestamp`, `route`, `namespace`, and `sources`. Confirm
the live schema and validation in the current code before changing these
fields.

------------------------------------------------------------------------

## Repository Structure

The following is the **documented core structure** based on the project
files and discussions. Optional files and frontend locations may differ
in the checked-out branch; verify the repository before treating this as
an exhaustive tree.

``` text
Kube-InsightAI-Agentv2.0/
├── app/
│   ├── main.py                  # FastAPI app, startup initialization, router registration
│   ├── mcp_client.py            # MCP session and tool-call helpers
│   ├── auth.py                  # Authentication dependencies/helpers (if present in this branch)
│   ├── api/
│   │   ├── routes.py            # Main Kubernetes / agent API routes
│   │   ├── auth_routes.py       # Authentication endpoints
│   │   ├── admin_routes.py      # User/admin management endpoints
│   │   └── remediation_routes.py# Remediation-related endpoints
│   ├── langgraph/
│   │   └── graph.py             # Intent detection, routing, investigation and reasoning
│   ├── mcp/
│   │   ├── server.py            # Kubernetes MCP tools, including pod ownership and logs
│   │   └── client.py            # MCP client/test helper, if retained
│   └── database.py              # Database initialization and access (if present)
├── kubernetes-manifests/
│   ├── mcp.yaml                 # MCP Deployment and Service
│   └── ...                      # Agent, frontend, config and service manifests
├── Dockerfile                   # Agent/backend image build
├── Jenkinsfile                  # CI/CD pipeline
├── requirements.txt             # Python dependencies
├── .env.example                 # Safe configuration template (recommended)
└── README.md
```

### File naming guidance

Use consistent, descriptive names:

-   `README.md` --- project overview, setup, architecture, API, and
    operational notes.
-   `app/main.py` --- FastAPI entry point. This project does **not** use
    a root `app.py` as its main entry point.
-   `app/api/routes.py` --- main API routes; keep the Logs endpoint with
    the existing router if that is where the current API is implemented.
-   `app/mcp_client.py` --- shared MCP client helper. Avoid self-imports
    in this module.
-   `app/mcp/server.py` --- Kubernetes MCP tool definitions and
    implementations.
-   `app/langgraph/graph.py` --- intent detection, routing, and agent
    workflow.
-   `kubernetes-manifests/mcp.yaml` --- MCP Kubernetes resources.
-   `Jenkinsfile` --- build, publish, and deployment pipeline.

Before adding a file shown as optional above, inspect the actual branch
and reuse existing modules when possible instead of creating duplicate
implementations.

------------------------------------------------------------------------

## Technology Stack

  -----------------------------------------------------------------------
  Area                                Technology
  ----------------------------------- -----------------------------------
  API backend                         Python, FastAPI

  Agent workflow                      LangGraph

  Knowledge retrieval                 RAG / Kubernetes operational
                                      documents

  Tool integration                    Model Context Protocol (MCP)

  Cluster orchestration               Kubernetes

  Data persistence                    PostgreSQL

  Frontend                            Web dashboard (HTML, CSS,
                                      JavaScript, as used by the current
                                      UI)

  Containerization                    Docker

  CI/CD                               Jenkins

  API authentication                  Existing application authentication
                                      and `window.KubeAuth.apiFetch` in
                                      the frontend
  -----------------------------------------------------------------------

LLM provider/model configuration is environment-specific. Configure the
provider and model using the application's supported settings; do not
commit credentials or assume a single provider is mandatory.

------------------------------------------------------------------------

## API Reference

The routes below include endpoints known from project discussions. Check
the running API or current route modules for the complete list and exact
response schemas.

  Method   Endpoint              Purpose
  -------- --------------------- ----------------------------------------
  `GET`    `/`                   Basic application health response
  `GET`    `/api/cluster/logs`   Retrieve logs for a pod and time range
  `GET`    `/api/history`        Retrieve investigation history
  `POST`   `/api/history`        Save an investigation record

The application registers the main, authentication, admin, and
remediation routers under `/api` in `app/main.py`.

### Example: request logs

``` bash
curl -G "http://localhost:8000/api/cluster/logs" \
  --data-urlencode "pod_name=demo-pod1" \
  --data-urlencode "namespace=testing-files" \
  --data-urlencode "start_time=<ISO-8601-start-time>" \
  --data-urlencode "end_time=<ISO-8601-end-time>" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Replace the placeholders with valid values. Authentication requirements
and accepted timestamp formats must match the current implementation. Do
not put real access tokens in shell history or documentation.

------------------------------------------------------------------------

## Configuration

Use environment variables or your deployment's secret/configuration
mechanism for environment-specific values. Do not commit `.env` files
containing secrets.

Common configuration areas:

  ----------------------------------------------------------------------------
  Setting                             Purpose
  ----------------------------------- ----------------------------------------
  `KUBERNETES_MCP_URL`                Kubernetes MCP endpoint; in-cluster
                                      default is
                                      `http://kube-insightaiv2-mcp:8001/mcp`

  Database configuration              PostgreSQL connection settings used by
                                      the application

  LLM provider settings               Provider endpoint, model name, and
                                      credentials supported by the
                                      implementation

  Authentication settings             Secret keys, token configuration, and
                                      other auth settings required by the
                                      current application
  ----------------------------------------------------------------------------

Create a local `.env` or Kubernetes Secret based on the actual
environment-variable names referenced in the code. The list above
describes configuration categories and is not a claim that every
variable has that exact name.

------------------------------------------------------------------------

## Run Locally

These steps are a general development outline; install dependencies and
configure variables according to the repository's actual
`requirements.txt` and environment.

``` bash
git clone <YOUR_REPOSITORY_URL>
cd <YOUR_REPOSITORY_DIRECTORY>

python -m venv .venv
```

Activate the virtual environment:

**Linux/macOS**

``` bash
source .venv/bin/activate
```

**Windows PowerShell**

``` powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies and start the API:

``` bash
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The root health endpoint should respond at `http://localhost:8000/`. API
documentation is typically available at `http://localhost:8000/docs`
when enabled by the FastAPI configuration.

A local run also needs valid database configuration and access to the
configured Kubernetes MCP server. Starting FastAPI alone does not
guarantee that live cluster investigation will work.

------------------------------------------------------------------------

## Kubernetes Deployment

The project has Kubernetes manifests under `kubernetes-manifests/` and a
Jenkins pipeline in `Jenkinsfile`. The deployed application namespace
used in the project is `kube-insightaiv2`.

Inspect resources before applying changes:

``` bash
kubectl get deployments,pods,services -n kube-insightaiv2
kubectl get endpoints -n kube-insightaiv2
kubectl describe deployment kube-insightaiv2-agent -n kube-insightaiv2
kubectl logs -n kube-insightaiv2 deployment/kube-insightaiv2-agent --since=10m
```

Check MCP service resolution from the agent's namespace:

``` bash
kubectl get svc kube-insightaiv2-mcp -n kube-insightaiv2
kubectl get pods -n kube-insightaiv2 -o wide
```

Use the actual manifest names, image tags, and namespace from the
checked-out branch. Avoid applying sample commands blindly to a
production cluster.

------------------------------------------------------------------------

## Troubleshooting and Validation

### Logs endpoint returns an error

1.  Confirm the user is authenticated and the frontend uses
    `window.KubeAuth.apiFetch`.
2.  Check the browser Network panel for the request URL, query
    parameters, and status code.
3.  Check the agent logs for the request and MCP failure details.
4.  Confirm `KUBERNETES_MCP_URL` points to the correct service.
5.  Verify that the MCP server exposes `get_pod_logs_by_time` and
    accepts the arguments being sent.
6.  Confirm the requested pod, namespace, container, and time range are
    valid.

### Investigation queries the wrong namespace

1.  Reproduce with an explicit namespace and pod name.
2.  Inspect the route selected by LangGraph.
3.  Inspect the final MCP context and tool arguments.
4.  Verify that the namespace has not been replaced by
    `kube-insightaiv2`.
5.  Compare the returned namespace and resource name with the original
    request.
6.  Re-test both a single-pod investigation and a namespace-wide query.

### Inspect routing logs

``` bash
kubectl logs -n kube-insightaiv2 \
  deployment/kube-insightaiv2-agent --since=30s \
  | grep -E "Question routed|Resolved pod|namespace|MCP"
```

Use a short time window immediately after each test to avoid correlating
stale log lines with the wrong request.

### Validate pod ownership

Test at least these cases:

-   Standalone pod: the answer should report no owner when the live
    resource has no owner reference.
-   Deployment-managed pod: resolve `Pod → ReplicaSet → Deployment`.
-   Namespace mismatch: the same pod name in a different namespace must
    not be treated as the requested resource.
-   Missing pod: report that the MCP lookup did not find the requested
    pod; do not infer an owner.

### Validate logs time-range behaviour

-   Valid range: start time is earlier than or equal to end time.
-   Invalid range: end time is earlier than start time; reject it before
    calling MCP.
-   Container selection: pass the selected container when provided.
-   Empty logs: render an explicit empty state.
-   MCP failure: display an error state and preserve useful diagnostics.
-   Refresh: confirm the request includes the current namespace, pod,
    and time controls.

### Example regression question

``` text
In namespace testing-files, investigate demo-pod1.
Retrieve its actual status and relevant Kubernetes events through MCP.
Explain the likely cause using the returned evidence. Do not invent results.
```

For a pod with an invalid image reference, the investigation may report
`ErrImagePull` or `ImagePullBackOff` if those states are actually
present in the live cluster data.

------------------------------------------------------------------------

## Security Notes

-   Never commit API tokens, passwords, database credentials, private
    keys, or populated `.env` files.
-   Protect investigation, user-management, and remediation endpoints
    with the existing authentication and authorization controls.
-   Follow least-privilege Kubernetes RBAC for the agent and MCP server.
-   Treat cluster data and log output as potentially sensitive.
-   Keep read-only investigation separate from remediation actions;
    require explicit authorization and confirmation for any operation
    that changes cluster resources.
-   Sanitize errors returned to the browser while retaining useful
    server-side diagnostics.
-   Do not expose internal service endpoints publicly unless required
    and protected.

------------------------------------------------------------------------

## Roadmap

Potential follow-up improvements, subject to the current implementation
and priorities:

-   Add automated tests for namespace/pod routing and ownership-intent
    detection.
-   Add API tests for `GET /api/cluster/logs`, including authentication,
    validation, empty results, and MCP failures.
-   Add frontend tests for time-range validation and loading/error/empty
    states.
-   Ensure CI fails when API tests fail.
-   Expand regression coverage for RAG, live pod queries, namespace-wide
    investigations, ownership, events, and logs.
-   Improve observability with request correlation IDs across frontend,
    API, graph, and MCP calls.
-   Document the exact environment variables and deployment manifests
    from the production branch.
