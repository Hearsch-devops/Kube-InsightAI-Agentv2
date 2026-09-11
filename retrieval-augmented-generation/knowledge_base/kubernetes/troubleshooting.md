# Kubernetes Troubleshooting Guide

## 1. Purpose

This document provides a general troubleshooting methodology for Kubernetes incidents.

It combines the troubleshooting principles from:

* Pods
* Deployments
* Services
* Ingress
* ConfigMaps
* Secrets
* Storage
* Networking
* Resources
* Scheduling

The goal is to identify the **first failed component**, determine the root cause, and verify that the problem has been resolved.

---

# 2. Kubernetes Troubleshooting Philosophy

Kubernetes applications are composed of multiple dependent layers.

A typical application may look like:

```text
User
 ↓
DNS
 ↓
LoadBalancer / Ingress
 ↓
Service
 ↓
Pod
 ↓
Container
 ↓
Application
 ↓
Config / Secret
 ↓
Storage
 ↓
External Dependencies
```

A failure at one layer can cause symptoms at another layer.

For example:

```text
Application cannot connect to database
```

does not necessarily mean the application is broken.

Possible causes include:

```text
DNS
NetworkPolicy
Service
Network
Database Pod
Credentials
Secret
Storage
Database resource exhaustion
```

The objective is to trace the dependency chain rather than guessing.

---

# 3. The First-Failure Principle

The most important Kubernetes troubleshooting principle is:

> **Find the first failed layer in the dependency chain.**

For example:

```text
Ingress
   ↓
Service
   ↓
Endpoint
   ↓
Pod
   ↓
Application
```

Suppose:

```text
Ingress = healthy
Service = healthy
Endpoint = healthy
Pod = Ready
Application = HTTP 500
```

The Kubernetes infrastructure may be functioning correctly.

The application is the first failing layer.

---

# 4. Start With the Symptom

First identify exactly what the user is reporting.

Examples:

```text
Pod is Pending
Pod is CrashLoopBackOff
Application is slow
Service is unreachable
Ingress returns 404
Ingress returns 502
Ingress returns 503
Container is OOMKilled
PVC is Pending
Pod cannot mount volume
DNS resolution fails
Deployment rollout is stuck
Application cannot connect to another Service
```

Do not begin by changing configuration.

First classify the symptom.

---

# 5. General Troubleshooting Workflow

Use the following process:

```text
Incident
 ↓
Identify Symptom
 ↓
Identify Affected Resource
 ↓
Check Status
 ↓
Check Events
 ↓
Check Logs
 ↓
Trace Dependencies
 ↓
Identify First Failure
 ↓
Form Hypothesis
 ↓
Validate Hypothesis
 ↓
Apply Corrective Action
 ↓
Verify
 ↓
Monitor
```

This workflow should be followed before making destructive or high-impact changes.

---

# 6. Step 1 — Identify the Affected Resource

Determine:

* Namespace
* Pod
* Deployment
* StatefulSet
* Service
* Ingress
* PVC
* Node
* ConfigMap
* Secret

Useful commands:

```bash
kubectl get pods -A
```

```bash
kubectl get deployments -A
```

```bash
kubectl get services -A
```

```bash
kubectl get ingress -A
```

```bash
kubectl get pvc -A
```

---

# 7. Step 2 — Check Resource Status

Start with a high-level status check.

For Pods:

```bash
kubectl get pods -n <namespace>
```

For Deployments:

```bash
kubectl get deployments -n <namespace>
```

For Services:

```bash
kubectl get svc -n <namespace>
```

For Nodes:

```bash
kubectl get nodes
```

For PVCs:

```bash
kubectl get pvc -n <namespace>
```

The status gives an initial signal but does not necessarily identify the root cause.

---

# 8. Status Is Not Root Cause

A Kubernetes status such as:

```text
CrashLoopBackOff
```

is a symptom.

It does not explain why the container is repeatedly restarting.

Possible root causes include:

* Application crash
* Configuration error
* Missing Secret
* Missing ConfigMap
* Dependency failure
* Permission issue
* OOMKilled
* Failed health probe

Always investigate deeper.

---

# 9. Step 3 — Describe the Resource

Use `kubectl describe` to obtain detailed information.

For a Pod:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

For a Deployment:

```bash
kubectl describe deployment <deployment-name> -n <namespace>
```

For a Service:

```bash
kubectl describe svc <service-name> -n <namespace>
```

For a Node:

```bash
kubectl describe node <node-name>
```

For a PVC:

```bash
kubectl describe pvc <pvc-name> -n <namespace>
```

Pay special attention to:

```text
Events
Conditions
Configuration
References
```

---

# 10. Step 4 — Check Events

Events are one of the most valuable troubleshooting signals in Kubernetes.

Check:

```bash
kubectl get events -A --sort-by=.lastTimestamp
```

Or:

```bash
kubectl get events -n <namespace> --sort-by=.lastTimestamp
```

Events can reveal:

* Scheduling failures
* Image pull failures
* Mount failures
* Probe failures
* Container creation errors
* Evictions
* Failed attachments
* Scaling activity

Use events to determine what Kubernetes observed.

---

# 11. Events vs Logs

Events and logs provide different information.

```text
Events
 ↓
Kubernetes-level activity
```

```text
Logs
 ↓
Application/container-level activity
```

Use both.

For example:

```text
Event:
Container restarted
```

Then:

```bash
kubectl logs <pod-name> -n <namespace>
```

may reveal:

```text
Application failed to connect to database
```

Events tell you **what Kubernetes observed**.

Logs often tell you **what the application experienced**.

---

# 12. Step 5 — Check Container Logs

Current container logs:

```bash
kubectl logs <pod-name> -n <namespace>
```

For a specific container:

```bash
kubectl logs <pod-name> -n <namespace> -c <container-name>
```

Previous container instance:

```bash
kubectl logs <pod-name> -n <namespace> --previous
```

This is especially useful for:

```text
CrashLoopBackOff
OOMKilled
Startup failures
Application crashes
```

---

# 13. Step 6 — Check Previous Container State

Inspect the Pod:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Look for:

```text
Last State
Reason
Exit Code
Started
Finished
```

Common reasons include:

```text
OOMKilled
Error
Completed
```

The exit code can provide additional evidence about why a container terminated.

---

# 14. Step 7 — Check Health Probes

Applications may be restarted or removed from Service traffic because of health probes.

Common probes:

```text
Liveness Probe
Readiness Probe
Startup Probe
```

Inspect:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Look for probe failures in Events.

---

# 15. Liveness Probe Failure

A liveness probe determines whether a container should be restarted.

If it repeatedly fails:

```text
Container
 ↓
Liveness Probe
 ↓
Failure
 ↓
Container Restart
```

Possible causes:

* Application deadlock
* Incorrect probe path
* Incorrect port
* Application startup too slow
* Probe timeout too short
* Temporary dependency issue

Do not automatically increase probe thresholds.

First determine whether the probe correctly represents application health.

---

# 16. Readiness Probe Failure

A readiness probe determines whether a Pod should receive traffic.

If readiness fails:

```text
Pod
 ↓
Not Ready
 ↓
Removed from Service endpoints
```

The container can remain:

```text
Running
```

while not receiving traffic.

This distinction is important:

```text
Running ≠ Ready
```

---

# 17. Startup Probe Failure

Startup probes can protect slow-starting applications from premature liveness failures.

If startup takes longer than expected, investigate:

* Application startup time
* Startup probe configuration
* Image initialization
* Dependency availability
* Resource constraints

Do not treat every slow startup as a liveness problem.

---

# 18. Deployment Troubleshooting

For a Deployment:

```bash
kubectl get deployment <deployment-name> -n <namespace>
```

Check rollout:

```bash
kubectl rollout status deployment/<deployment-name> -n <namespace>
```

Check history:

```bash
kubectl rollout history deployment/<deployment-name> -n <namespace>
```

Inspect:

```bash
kubectl describe deployment <deployment-name> -n <namespace>
```

Then trace:

```text
Deployment
 ↓
ReplicaSet
 ↓
Pod
 ↓
Container
 ↓
Application
```

A Deployment problem often originates in the Pod or container.

---

# 19. Stuck Deployment Rollout

Symptoms:

```text
Deployment does not reach desired replicas
```

Investigate:

```text
Deployment
 ↓
ReplicaSet
 ↓
New Pods
 ↓
Pod status
 ↓
Pod events
 ↓
Container logs
```

Possible causes:

* ImagePullBackOff
* CrashLoopBackOff
* Failed probes
* Pending Pods
* Insufficient resources
* Scheduling constraints
* Config errors
* Secret errors
* Storage problems

---

# 20. Service Troubleshooting

For a Service:

```bash
kubectl get svc <service-name> -n <namespace>
```

Inspect:

```bash
kubectl describe svc <service-name> -n <namespace>
```

Then check EndpointSlices:

```bash
kubectl get endpointslice -n <namespace>
```

Trace:

```text
Service
 ↓
Selector
 ↓
EndpointSlice
 ↓
Ready Pod
 ↓
TargetPort
 ↓
Application
```

If the Service has no endpoints, investigate selectors and Pod readiness.

---

# 21. Service Has No Endpoints

Possible causes:

* Selector mismatch
* Incorrect labels
* Pods not Ready
* Wrong namespace
* No matching Pods

Compare:

```bash
kubectl get svc <service-name> -n <namespace> -o yaml
```

with:

```bash
kubectl get pods -n <namespace> --show-labels
```

Then inspect:

```bash
kubectl get endpointslice -n <namespace>
```

---

# 22. Ingress Troubleshooting

For external HTTP/HTTPS problems:

```text
Client
 ↓
DNS
 ↓
LoadBalancer
 ↓
Ingress Controller
 ↓
Ingress Rule
 ↓
Service
 ↓
EndpointSlice
 ↓
Pod
 ↓
Application
```

A failure can occur at any layer.

Check:

```bash
kubectl get ingress -A
```

Then:

```bash
kubectl describe ingress <ingress-name> -n <namespace>
```

---

# 23. Ingress Error Interpretation

### 404

Often indicates that the request reached the Ingress Controller but no expected route matched.

Check:

* Host
* Path
* IngressClass
* Rules

### 502

May indicate that the Ingress Controller cannot successfully communicate with the backend.

Check:

```text
Ingress
 ↓
Service
 ↓
Endpoints
 ↓
Pod
```

### 503

May indicate that no healthy backend is available.

Check:

* Service
* EndpointSlices
* Pod readiness
* Backend health

Do not treat these interpretations as absolute. Confirm using cluster evidence.

---

# 24. ConfigMap and Secret Troubleshooting

If a Pod fails during startup, check whether it references:

```text
ConfigMap
Secret
```

Inspect:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Then:

```bash
kubectl get configmap -n <namespace>
```

```bash
kubectl get secret -n <namespace>
```

Check:

* Resource exists
* Correct namespace
* Correct name
* Correct key
* Correct reference
* Required permissions

---

# 25. Configuration Failure Pattern

A common dependency chain is:

```text
Application
 ↓
Environment Variable / Mounted File
 ↓
Pod Specification
 ↓
ConfigMap / Secret
 ↓
Key
 ↓
Value
```

A failure at any point can prevent the application from starting correctly.

For example:

```text
Application expects:
DATABASE_HOST

Pod provides:
DB_HOST
```

The ConfigMap or Secret may exist, but the application can still fail.

---

# 26. Storage Troubleshooting

For storage failures:

```text
Pod
 ↓
PVC
 ↓
PV
 ↓
StorageClass
 ↓
CSI Driver
 ↓
Volume Attachment
 ↓
Volume Mount
 ↓
Filesystem
 ↓
Application
```

Check:

```bash
kubectl get pvc -n <namespace>
```

Then:

```bash
kubectl describe pvc <pvc-name> -n <namespace>
```

Check:

```bash
kubectl get pv
```

For Pod mount errors:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Look for:

```text
FailedAttachVolume
FailedMount
```

---

# 27. Networking Troubleshooting

For networking:

```text
Source
 ↓
DNS
 ↓
Service
 ↓
EndpointSlice
 ↓
Pod IP
 ↓
Port
 ↓
Application
```

Check:

```bash
kubectl get svc -n <namespace>
```

```bash
kubectl get endpointslice -n <namespace>
```

```bash
kubectl get pods -o wide -n <namespace>
```

Then test connectivity from the source Pod when possible.

---

# 28. NetworkPolicy Troubleshooting

If Pods are healthy but communication fails, check:

```bash
kubectl get networkpolicy -A
```

Inspect:

```bash
kubectl describe networkpolicy <policy-name> -n <namespace>
```

Determine:

```text
Is traffic allowed?
Is ingress allowed?
Is egress allowed?
Is DNS allowed?
Is the correct port allowed?
```

Do not assume that healthy Pods can communicate with each other when NetworkPolicies are present.

---

# 29. DNS Troubleshooting

Test DNS from the affected Pod:

```bash
kubectl exec -it <pod-name> -n <namespace> -- nslookup <service-name>
```

or:

```bash
kubectl exec -it <pod-name> -n <namespace> -- getent hosts <service-name>
```

Check CoreDNS:

```bash
kubectl get pods -n kube-system -l k8s-app=kube-dns
```

Then inspect logs if required.

A DNS problem can affect:

```text
Service discovery
External API access
Database connections
Ingress dependencies
```

---

# 30. Resource Troubleshooting

When applications are slow or containers restart:

```text
Pod
 ↓
Resource Requests
 ↓
Resource Limits
 ↓
Actual Usage
 ↓
Node Capacity
 ↓
Node Pressure
```

Check usage:

```bash
kubectl top pods -A
```

Check nodes:

```bash
kubectl top nodes
```

Inspect Pod:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Look for:

```text
OOMKilled
Evicted
Pending
```

---

# 31. OOMKilled

If a container is repeatedly OOMKilled:

```text
Container
 ↓
Memory consumption
 ↓
Memory limit exceeded
 ↓
Container terminated
 ↓
Restart
```

Check:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Look for:

```text
Reason: OOMKilled
```

Then investigate:

* Memory limit
* Memory usage
* Application behavior
* Traffic pattern
* Memory leaks
* Concurrency
* Caching

Do not automatically increase memory without understanding the cause.

---

# 32. Scheduling Troubleshooting

If a Pod is Pending:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Start with scheduler Events.

Possible causes:

```text
Insufficient CPU
Insufficient Memory
Untolerated Taint
Node Selector
Node Affinity
Pod Affinity
Pod Anti-Affinity
Topology Constraints
Volume Topology
Unschedulable Node
ResourceQuota
```

The first step is to identify why nodes were rejected.

---

# 33. Node Troubleshooting

Check nodes:

```bash
kubectl get nodes
```

Inspect:

```bash
kubectl describe node <node-name>
```

Important conditions include:

```text
Ready
MemoryPressure
DiskPressure
PIDPressure
NetworkUnavailable
```

Check:

```text
Taints
Labels
Allocatable Resources
Allocated Resources
Events
```

---

# 34. Single-Workload vs Cluster-Wide Failure

Determine the scope of the incident.

### Single Pod

```text
One Pod affected
```

Investigate:

* Pod
* Container
* Configuration
* Application

### Multiple Pods on One Node

```text
Node-specific pattern
```

Investigate:

* Node
* CNI
* Resources
* Disk
* Network

### Multiple Pods Across Nodes

```text
Cluster-wide pattern
```

Investigate:

* Control-plane behavior
* Cluster networking
* Storage systems
* Shared dependencies
* Resource capacity
* DNS
* Cluster configuration

Scope is a powerful diagnostic signal.

---

# 35. Compare Healthy vs Unhealthy Workloads

When possible, compare:

```text
Healthy Pod
vs
Unhealthy Pod
```

Compare:

* Image
* Environment variables
* ConfigMaps
* Secrets
* Resource requests
* Resource limits
* Node placement
* Labels
* Service membership
* Volumes
* Probes

This can reveal configuration differences that would otherwise be difficult to identify.

---

# 36. Use a Dependency Graph

Complex Kubernetes applications should be investigated as dependency graphs.

Example:

```text
Frontend
   ↓
Frontend Service
   ↓
Backend Service
   ↓
Backend Pod
   ↓
Database Service
   ↓
Database Pod
   ↓
PVC
   ↓
PV
```

If the frontend cannot load data, trace the dependency chain rather than investigating only the frontend.

---

# 37. Form a Hypothesis

After collecting evidence, create a specific hypothesis.

Weak hypothesis:

```text
"The cluster has a networking problem."
```

Better hypothesis:

```text
"The backend Service has no EndpointSlices because its
selector does not match the backend Pod labels."
```

Strong troubleshooting requires a testable hypothesis.

---

# 38. Validate the Hypothesis

Use Kubernetes data to confirm or reject the hypothesis.

Example:

Hypothesis:

```text
Service selector is incorrect.
```

Check:

```bash
kubectl get svc backend -n <namespace> -o yaml
```

Then:

```bash
kubectl get pods -n <namespace> --show-labels
```

Then:

```bash
kubectl get endpointslice -n <namespace>
```

If the selector does not match the intended Pods and the Service has no endpoints, the hypothesis is supported.

---

# 39. Avoid Random Changes

Do not blindly perform actions such as:

```text
Restart everything
Delete the Pod
Delete the PVC
Increase memory
Increase replicas
Restart CoreDNS
Restart nodes
Delete resources
```

without first identifying the likely cause.

Random changes can:

* Hide the original problem
* Cause downtime
* Destroy data
* Create additional failures
* Make incident analysis harder

Troubleshooting should be evidence-driven.

---

# 40. Safe vs Destructive Actions

Prefer low-risk diagnostic actions first.

Examples:

```text
kubectl get
kubectl describe
kubectl logs
kubectl top
kubectl exec
```

Potentially higher-impact actions include:

```text
kubectl delete
kubectl rollout restart
kubectl scale
kubectl cordon
kubectl drain
```

Destructive operations involving storage require additional caution.

Before deleting storage resources, verify:

```text
Backup
Data importance
Reclaim policy
Recovery path
```

---

# 41. Incident Severity

Not every Kubernetes issue has the same impact.

Consider:

```text
Number of affected workloads
Number of affected users
Availability impact
Data integrity risk
Duration
Production vs non-production
Recovery complexity
```

A single non-production Pod failure is different from a cluster-wide production outage.

---

# 42. Troubleshooting Evidence Collection

Useful evidence includes:

```text
Pod status
Pod events
Container logs
Previous container logs
Deployment status
ReplicaSet status
Service configuration
EndpointSlices
Ingress configuration
NetworkPolicies
PVC/PV status
StorageClass
Node conditions
Resource usage
HPA status
Scheduler events
```

Collect evidence before making major changes whenever possible.

---

# 43. Verification After Fix

A fix is not complete when the error disappears once.

Verify:

```text
Resource status
 ↓
Pod health
 ↓
Service connectivity
 ↓
Application behavior
 ↓
Logs
 ↓
Metrics
```

For example:

```bash
kubectl get pods -n <namespace>
```

Then:

```bash
kubectl get svc -n <namespace>
```

Then test the application.

Look for:

* Pods Ready
* No repeated restarts
* No new critical events
* Service endpoints available
* Expected application response
* Stable resource usage

---

# 44. Monitor After Recovery

After fixing the immediate problem, continue observing the workload.

Check:

```bash
kubectl get pods -n <namespace>
```

and:

```bash
kubectl top pods -n <namespace>
```

Review:

* Restart count
* Resource usage
* Application errors
* Latency
* Availability
* New events

A temporary recovery does not necessarily mean the root cause has been permanently resolved.

---

# 45. Kubernetes Troubleshooting Decision Tree

```text
Incident
   ↓
What is the symptom?
   │
   ├── Pod Pending
   │      ↓
   │   Scheduler Events
   │      ↓
   │   Resources / Taints / Affinity / Topology
   │
   ├── Pod CrashLoopBackOff
   │      ↓
   │   Logs + Previous Logs
   │      ↓
   │   Exit Code / OOMKilled / Probes / Config
   │
   ├── Service unreachable
   │      ↓
   │   Service → Selector → EndpointSlice → Pod
   │      ↓
   │   DNS / NetworkPolicy / Port / Application
   │
   ├── Ingress failure
   │      ↓
   │   DNS → Ingress → Service → Endpoint → Pod
   │
   ├── Storage failure
   │      ↓
   │   PVC → PV → CSI → Attach → Mount → Filesystem
   │
   ├── Application slow
   │      ↓
   │   CPU / Memory / Throttling / Node Capacity
   │
   └── Configuration failure
          ↓
       ConfigMap / Secret
          ↓
       Pod Environment / Files
          ↓
       Application
```

---

# 46. Universal Kubernetes Troubleshooting Flow

The following workflow can be applied to most Kubernetes incidents:

```text
User Reports Problem
        ↓
Identify Resource
        ↓
Check Status
        ↓
Check Events
        ↓
Check Logs
        ↓
Trace Dependencies
        ↓
Find First Failure
        ↓
Form Hypothesis
        ↓
Validate With Evidence
        ↓
Apply Minimal Corrective Action
        ↓
Verify
        ↓
Monitor
```

The key principle is:

> **Observe → Hypothesize → Validate → Act → Verify**

---

# 47. Kube-InsightAI Diagnostic Principle

Kube-InsightAI should use this document as its general troubleshooting framework.

When a user reports:

> "Something is wrong with my Kubernetes application."

The agent should not immediately execute commands or recommend changes.

It should first determine:

1. What application is affected?
2. Which namespace contains it?
3. Which Kubernetes resources are involved?
4. What is the observed symptom?
5. What is the current status?
6. What do Kubernetes events show?
7. What do container logs show?
8. What dependencies does the workload have?
9. Where is the first failure?
10. What evidence supports the suspected root cause?
11. What is the safest corrective action?
12. How can the fix be verified?

The agent should reason using the following pattern:

```text
Symptom
   ↓
Evidence
   ↓
Dependency Graph
   ↓
First Failure
   ↓
Root Cause Hypothesis
   ↓
Validation
   ↓
Recommendation
   ↓
Verification
```

When MCP is integrated, Kube-InsightAI can obtain live evidence such as:

```text
kubectl get pods
kubectl describe pod
kubectl logs
kubectl get deployments
kubectl get svc
kubectl get endpointslice
kubectl get ingress
kubectl get networkpolicy
kubectl get pvc
kubectl get pv
kubectl get nodes
kubectl top pods
kubectl top nodes
kubectl get events
```

RAG provides the Kubernetes troubleshooting knowledge.

MCP provides the live cluster state.

The LLM combines both to produce the diagnosis.

---

# 48. RAG + MCP Troubleshooting Example

User:

> "My payment API is not working."

Kube-InsightAI should reason:

```text
User Complaint
      ↓
Identify payment-api
      ↓
Check Deployment
      ↓
Check Pods
      ↓
Check Service
      ↓
Check EndpointSlices
      ↓
Check Logs
      ↓
Check Events
      ↓
Trace Dependencies
```

Suppose MCP returns:

```text
payment-api Pod:
CrashLoopBackOff

Previous container:
OOMKilled

Memory limit:
512Mi

Current memory usage:
near limit
```

RAG provides the knowledge:

```text
OOMKilled indicates memory exhaustion.
Investigate memory limits and application behavior.
```

The agent can then produce:

```text
Diagnosis:
The payment-api container is repeatedly being
terminated because it exceeds its 512Mi memory limit.

Evidence:
- Pod is in CrashLoopBackOff.
- Previous container state is OOMKilled.
- Memory usage is near the configured limit.

Recommended next step:
Investigate application memory consumption and determine
whether the 512Mi limit is appropriate before increasing it.
```

This is the intended Kube-InsightAI architecture:

```text
             User
               ↓
        Kube-InsightAI
               ↓
          LangGraph
               ↓
        ┌──────┴──────┐
        ↓             ↓
       RAG           MCP
        ↓             ↓
Kubernetes SOPs   Live Cluster
        │             │
        └──────┬──────┘
               ↓
              LLM
               ↓
        Diagnosis + Evidence
        + Recommendation
        + Verification
```

---

# 49. Important Safety Principle

Kube-InsightAI should distinguish between:

```text
Read-only diagnostic action
```

and:

```text
Mutating action
```

Examples of diagnostic actions:

```text
get
describe
logs
top
exec
```

Examples of potentially mutating actions:

```text
delete
scale
restart
rollout
cordon
drain
patch
apply
```

The agent should gather evidence before recommending or executing mutating actions.

For destructive operations, especially storage-related operations, the agent should require additional confirmation and consider data-loss risk.

---

# 50. Final Troubleshooting Checklist

Before concluding a Kubernetes incident:

* [ ] Identify the symptom
* [ ] Identify the affected resource
* [ ] Identify namespace
* [ ] Check resource status
* [ ] Check events
* [ ] Check container logs
* [ ] Check previous container logs
* [ ] Check health probes
* [ ] Check resource requests and limits
* [ ] Check node capacity
* [ ] Check scheduling constraints
* [ ] Check Services
* [ ] Check EndpointSlices
* [ ] Check DNS
* [ ] Check NetworkPolicies
* [ ] Check Ingress
* [ ] Check ConfigMaps
* [ ] Check Secrets
* [ ] Check PVCs and PVs
* [ ] Check CSI/storage when applicable
* [ ] Trace application dependencies
* [ ] Identify first failed layer
* [ ] Form a root-cause hypothesis
* [ ] Validate the hypothesis
* [ ] Apply the minimal corrective action
* [ ] Verify the fix
* [ ] Monitor for recurrence
* [ ] Document the root cause and resolution

---

# 51. Summary

Kubernetes troubleshooting should not be based on guessing.

The recommended process is:

```text
Observe
  ↓
Collect Evidence
  ↓
Trace Dependencies
  ↓
Find First Failure
  ↓
Form Hypothesis
  ↓
Validate
  ↓
Act
  ↓
Verify
  ↓
Monitor
```

The most important principle is:

> **Do not troubleshoot the symptom alone. Trace the dependency chain until you find the first failed layer.**

For Kube-InsightAI:

```text
RAG = Kubernetes knowledge
MCP = Live cluster evidence
LLM = Reasoning and explanation
LangGraph = Decision/workflow orchestration
LangChain = Reusable components
```

Together, these components allow Kube-InsightAI to transform:

```text
"What could be wrong?"
```

into:

```text
"What is wrong,
why is it happening,
what evidence proves it,
what should I do next,
and how do I verify the fix?"
```
