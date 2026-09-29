# Kubernetes Overview

## What is Kubernetes?

Kubernetes is an open-source container orchestration platform used to deploy, manage, scale, and maintain containerized applications across a cluster of machines.

Instead of manually managing individual containers, Kubernetes provides a declarative system where you define the desired state of your applications and Kubernetes works to maintain that state.

For example, you can define that an application should have three running replicas. Kubernetes continuously monitors the cluster and attempts to maintain those three replicas.

## Why is Kubernetes Used?

Kubernetes helps organizations manage containerized applications reliably at scale.

Common capabilities include:

* Deploying containerized applications
* Scaling applications up or down
* Restarting failed containers
* Performing rolling updates
* Providing service discovery and networking
* Managing application configuration and secrets
* Scheduling workloads across worker nodes
* Managing persistent storage
* Monitoring application and workload health

## Kubernetes Cluster

A Kubernetes cluster consists primarily of a control plane and worker nodes.

### Control Plane

The control plane manages the Kubernetes cluster and makes decisions about the desired state of workloads.

Important control-plane components include:

* API Server
* Scheduler
* Controller Manager
* etcd

### Worker Nodes

Worker nodes run the application workloads.

A worker node commonly contains:

* Kubelet
* Container runtime
* kube-proxy

Pods are scheduled onto worker nodes by the Kubernetes scheduler.

## Pods

A Pod is the smallest deployable unit in Kubernetes.

A Pod usually contains one container, although a Pod can contain multiple closely related containers that share networking and storage.

Example:

```text
Pod
└── Container
    └── Application
```

Kubernetes manages Pods rather than directly managing individual containers.

## Deployments

A Deployment manages replicated Pods and provides declarative application updates.

A Deployment can:

* Create and manage Pods
* Maintain the desired number of replicas
* Perform rolling updates
* Replace failed Pods
* Roll back to previous versions

Example:

```text
Deployment
├── Pod
├── Pod
└── Pod
```

If the desired replica count is three and one Pod fails, Kubernetes attempts to create another Pod to maintain the desired state.

## Services

A Kubernetes Service provides a stable network endpoint for accessing a group of Pods.

Pods are ephemeral and their IP addresses can change. A Service provides a stable abstraction that allows clients to communicate with the application without depending on individual Pod IP addresses.

Common Service types include:

* ClusterIP
* NodePort
* LoadBalancer

## Namespaces

A Namespace provides logical separation within a Kubernetes cluster.

Namespaces can be used to organize and isolate resources such as:

* Pods
* Deployments
* Services
* ConfigMaps
* Secrets

For example:

```text
Cluster
├── default
├── kube-system
└── kube-insightaiv2
```

Resources can be queried within a specific namespace using kubectl.

Example:

```bash
kubectl get pods -n kube-insightaiv2
```

## ConfigMaps

A ConfigMap stores non-sensitive configuration data separately from application container images.

Applications can consume ConfigMap values as:

* Environment variables
* Command-line arguments
* Mounted files

## Secrets

A Secret is used to store sensitive information such as:

* Passwords
* API keys
* Tokens
* Certificates

Secrets can be exposed to containers through environment variables or mounted files.

Sensitive values should be handled carefully and should not be unnecessarily exposed in logs or source code.

## Ingress

An Ingress provides HTTP and HTTPS routing to services inside a Kubernetes cluster.

It can route requests based on information such as:

* Hostname
* URL path

Example:

```text
Client
   |
   v
Ingress
   |
   +----> frontend Service
   |
   +----> backend Service
```

## Kubernetes Health

Kubernetes provides mechanisms for determining application health and readiness.

### Readiness Probe

A readiness probe determines whether a container is ready to receive traffic.

If the readiness probe fails, the Pod can remain running but is considered not ready to receive Service traffic.

### Liveness Probe

A liveness probe determines whether a container is still functioning correctly.

If a liveness probe repeatedly fails, Kubernetes can restart the container.

### Startup Probe

A startup probe can be used for applications that require additional time to start.

It prevents liveness and readiness checks from being applied too aggressively during application startup.

## Scheduling

The Kubernetes scheduler determines which worker node should run a Pod.

Scheduling decisions can consider factors such as:

* Available resources
* CPU and memory requirements
* Node constraints
* Taints and tolerations
* Node affinity
* Pod affinity and anti-affinity

## Kubernetes Desired State

One of the key concepts in Kubernetes is the desired state.

For example:

```yaml
spec:
  replicas: 3
```

This declares that the application should have three replicas.

Kubernetes continuously observes the actual cluster state and uses controllers to move the cluster toward the desired state.

```text
Desired State
     |
     v
Kubernetes Controllers
     |
     v
Actual Cluster State
     |
     └──> Continuously Reconciled
```

## kubectl

`kubectl` is the command-line tool used to interact with a Kubernetes cluster.

Common commands include:

```bash
kubectl get pods
kubectl get deployments
kubectl get services
kubectl get nodes
kubectl get namespaces
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

Namespace-specific example:

```bash
kubectl get pods -n kube-insightaiv2
```

## Kubernetes and Kube-InsightAI

Kube-InsightAI can use Kubernetes knowledge stored in its RAG knowledge base to answer conceptual questions about Kubernetes.

Examples include:

* What is Kubernetes?
* What is a Pod?
* What is a Deployment?
* What is a readiness probe?
* What is a Kubernetes Service?
* How does Kubernetes scheduling work?

For questions requiring current cluster information, Kube-InsightAI can use MCP to retrieve live Kubernetes information.

For example:

```text
"What is a readiness probe?"
        |
        v
       RAG
        |
        v
Kubernetes knowledge base
```

Whereas:

```text
"Is the kube-insightaiv2 agent ready?"
        |
        v
       MCP
        |
        v
Live Kubernetes cluster
```

This separation allows Kube-InsightAI to distinguish between Kubernetes knowledge questions and live cluster operational questions.
