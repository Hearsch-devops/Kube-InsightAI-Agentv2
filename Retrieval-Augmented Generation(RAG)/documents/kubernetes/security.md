# Kubernetes Security Troubleshooting Guide

## 1. Kubernetes Security Overview

Kubernetes security protects:

* Cluster resources
* Workloads
* APIs
* Secrets and configuration
* Network communication
* Container processes
* Nodes
* Supply chain and container images
* Access between users, services, and workloads

A useful Kubernetes security model is:

```text
User / Workload
      ↓
Authentication
      ↓
Authorization (RBAC)
      ↓
Admission / Policy
      ↓
Kubernetes API
      ↓
Resource
      ↓
Pod Security
      ↓
Network Security
      ↓
Container / Image Security
      ↓
Node Security
```

Security problems can occur at any layer.

---

# 2. Kubernetes Security Principles

The most important principles are:

### Least Privilege

Give users and workloads only the permissions they actually need.

### Defense in Depth

Do not depend on a single security mechanism.

Use multiple layers:

```text
RBAC
 +
Pod Security
 +
NetworkPolicy
 +
Container Security
 +
Image Security
 +
Node Security
```

### Explicit Access

Access should be granted intentionally rather than accidentally.

### Secure Defaults

Applications should not require unnecessary privileges.

### Continuous Verification

A configuration that is secure today can become insecure after a deployment or configuration change.

---

# 3. Authentication vs Authorization

These concepts are different.

### Authentication

Answers:

> Who are you?

Examples:

* User identity
* ServiceAccount
* External identity provider
* Client certificate

### Authorization

Answers:

> What are you allowed to do?

Kubernetes commonly uses **RBAC** for authorization.

```text
Identity
   ↓
Authentication
   ↓
RBAC
   ↓
Allowed / Denied
```

---

# 4. RBAC

RBAC stands for:

**Role-Based Access Control**

RBAC controls access to Kubernetes API resources.

The main RBAC objects are:

* Role
* ClusterRole
* RoleBinding
* ClusterRoleBinding

Relationship:

```text
Role
 ↓
Permissions

RoleBinding
 ↓
Connects Identity → Role
```

---

# 5. Role

A `Role` grants permissions inside a specific namespace.

Example:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: production
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]
```

This allows the associated identity to read Pods in the `production` namespace.

It does not automatically provide access to Pods in other namespaces.

---

# 6. ClusterRole

A `ClusterRole` is cluster-scoped.

It can grant permissions for:

* Cluster-scoped resources
* Resources across namespaces when bound appropriately

Example:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: pod-reader
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]
```

A ClusterRole can be connected to an identity through a `ClusterRoleBinding`.

---

# 7. RoleBinding

A `RoleBinding` connects a user, group, or ServiceAccount to a Role.

Example relationship:

```text
ServiceAccount
      ↓
RoleBinding
      ↓
Role
      ↓
Permissions
```

A common troubleshooting mistake is checking the Role but forgetting the RoleBinding.

---

# 8. ClusterRoleBinding

A `ClusterRoleBinding` grants a ClusterRole to an identity at cluster scope.

Example:

```text
ServiceAccount
      ↓
ClusterRoleBinding
      ↓
ClusterRole
      ↓
Cluster-wide permissions
```

Because ClusterRoleBindings can grant broad access, they should be reviewed carefully.

---

# 9. RBAC Troubleshooting

If a user or workload receives:

```text
Forbidden
```

check:

1. Who is making the request?
2. Which ServiceAccount or user is being used?
3. Which namespace is involved?
4. Which resource is being accessed?
5. Which API group is involved?
6. Which verb is required?
7. Does an appropriate Role/ClusterRole exist?
8. Does a RoleBinding/ClusterRoleBinding connect the identity?
9. Is the binding in the correct namespace?
10. Are additional admission or policy controls involved?

Useful commands:

```bash
kubectl auth can-i get pods -n production
```

```bash
kubectl auth can-i create deployments -n production
```

For a ServiceAccount:

```bash
kubectl auth can-i get pods \
  --as=system:serviceaccount:production:payment-api \
  -n production
```

---

# 10. ServiceAccounts

Pods can use a Kubernetes `ServiceAccount` as their workload identity.

Relationship:

```text
Pod
 ↓
ServiceAccount
 ↓
RBAC Permissions
 ↓
Kubernetes API
```

Check the ServiceAccount:

```bash
kubectl get serviceaccount -n production
```

Inspect it:

```bash
kubectl describe serviceaccount payment-api -n production
```

Check which ServiceAccount a Pod uses:

```bash
kubectl get pod payment-api -n production \
  -o jsonpath='{.spec.serviceAccountName}'
```

---

# 11. ServiceAccount Security

Avoid giving every workload broad permissions.

Bad pattern:

```text
Every Pod
   ↓
Highly privileged ServiceAccount
```

Better:

```text
Application A
   ↓
Dedicated ServiceAccount
   ↓
Minimum required permissions
```

A workload that does not need Kubernetes API access should not receive unnecessary permissions.

---

# 12. Secrets Security

Kubernetes Secrets commonly contain sensitive information such as:

* Passwords
* API keys
* Tokens
* Certificates
* Credentials

Check Secrets:

```bash
kubectl get secrets -n production
```

Describe a Secret:

```bash
kubectl describe secret payment-api -n production
```

Important principle:

> Base64 encoding is not encryption.

For example:

```text
Base64
  ≠
Encryption
```

Secret security depends on cluster configuration, access controls, storage encryption, and operational practices.

---

# 13. Secret Troubleshooting

If an application cannot access a Secret, check:

```text
Pod
 ↓
Secret Reference
 ↓
Secret
 ↓
Correct Namespace
 ↓
Correct Key
 ↓
RBAC / Access
 ↓
Application
```

Common causes:

* Secret does not exist
* Wrong namespace
* Wrong Secret name
* Wrong key
* Incorrect volume reference
* Incorrect environment variable reference
* ServiceAccount permissions
* Application expects a different value
* Secret was changed but application was not restarted when required

---

# 14. NetworkPolicy

`NetworkPolicy` controls network traffic to and/or from Pods.

Conceptually:

```text
Pod A
  │
  │ Network traffic
  ↓
NetworkPolicy
  │
  ├── Allowed
  └── Denied
```

Policies may control:

* Ingress traffic
* Egress traffic
* Source Pods
* Destination Pods
* Namespaces
* IP ranges
* Ports

---

# 15. NetworkPolicy Troubleshooting

If an application suddenly cannot communicate with another service:

Check:

```bash
kubectl get networkpolicy -A
```

Inspect policies:

```bash
kubectl describe networkpolicy <policy-name> -n production
```

Determine:

1. Source Pod
2. Destination Pod
3. Destination port
4. Namespace
5. Applicable NetworkPolicies
6. Whether ingress is allowed
7. Whether egress is allowed
8. Whether the CNI supports/enforces NetworkPolicy

A NetworkPolicy problem may appear as:

```text
Connection timeout
```

rather than an application error.

---

# 16. NetworkPolicy and DNS

DNS is easy to overlook.

An application may be unable to resolve:

```text
payment-api.production.svc.cluster.local
```

because DNS traffic is blocked by an egress policy.

Troubleshooting should therefore include:

```text
Application
 ↓
DNS Resolution
 ↓
Network Connection
 ↓
Service
 ↓
Pod
```

Do not assume that a network failure is always a Service problem.

---

# 17. Pod Security

Kubernetes provides mechanisms to restrict potentially dangerous Pod configurations.

The **Pod Security Standards** define security profiles such as:

* Privileged
* Baseline
* Restricted

Exact enforcement depends on cluster configuration and policy setup.

---

# 18. SecurityContext

A Pod or container can define security settings through `securityContext`.

Common settings include:

* `runAsUser`
* `runAsGroup`
* `runAsNonRoot`
* Linux capabilities
* Privilege escalation
* Seccomp profile
* Read-only root filesystem

Example:

```yaml
securityContext:
  runAsNonRoot: true
  allowPrivilegeEscalation: false
```

Container-level settings can also be defined:

```yaml
containers:
  - name: app
    image: example/app:1.0
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
```

---

# 19. Privileged Containers

Privileged containers have significantly greater access to the underlying host.

They should only be used when genuinely required.

If a workload unexpectedly requires privileged access, investigate why.

Check:

```bash
kubectl get pod <pod-name> -n production -o yaml
```

Look for:

```yaml
securityContext:
  privileged: true
```

Also inspect:

* Capabilities
* Host namespaces
* HostPath mounts
* Host networking
* Host PID
* Host IPC

---

# 20. Linux Capabilities

Linux capabilities provide granular privileges.

Instead of giving a container broad privileges, capabilities can be selectively added or removed.

Example:

```yaml
securityContext:
  capabilities:
    drop:
      - ALL
```

Only required capabilities should be added.

---

# 21. Seccomp

Seccomp can restrict system calls available to a container.

A restricted workload may use a runtime/default or more restrictive profile depending on the cluster configuration.

Security troubleshooting should check whether a workload is being blocked because of its security profile.

---

# 22. Read-Only Root Filesystem

A container can use:

```yaml
readOnlyRootFilesystem: true
```

This prevents writes to the container's root filesystem.

If an application fails after enabling this setting, determine where it expects to write.

Common writable locations may need explicit volumes.

Example:

```text
Container
 ├── Root filesystem → Read-only
 │
 └── /tmp → Writable volume
```

---

# 23. Container Image Security

Container images are part of the Kubernetes security boundary.

Common concerns:

* Untrusted images
* Vulnerable packages
* Outdated base images
* Malicious images
* Mutable tags
* Compromised registries

Prefer trusted registries and controlled image sources.

Use image scanning and supply-chain controls where available.

---

# 24. ImagePullSecrets

Private registries may require credentials.

Example:

```yaml
imagePullSecrets:
  - name: registry-credentials
```

If image pulls fail, check:

```bash
kubectl describe pod <pod-name> -n production
```

Look for:

```text
ErrImagePull
ImagePullBackOff
```

Then verify:

```text
Registry
 ↓
Credentials
 ↓
ImagePullSecret
 ↓
ServiceAccount / Pod
 ↓
Image Pull
```

---

# 25. Image Security Troubleshooting

Check:

1. Image name
2. Image tag or digest
3. Registry accessibility
4. Registry credentials
5. ImagePullSecret
6. ServiceAccount configuration
7. Node network connectivity
8. Image availability
9. Image architecture compatibility
10. Registry certificate/TLS issues

Do not immediately assume an `ImagePullBackOff` is an RBAC issue.

---

# 26. Namespace Isolation

Namespaces provide logical separation of Kubernetes resources.

Example:

```text
production
 ├── payment-api
 ├── payment-db
 └── payment-service

development
 ├── payment-api
 ├── payment-db
 └── payment-service
```

Namespaces can help organize:

* RBAC
* NetworkPolicies
* ResourceQuotas
* Secrets
* Workloads

However, namespaces alone should not be treated as a complete security boundary.

---

# 27. ResourceQuota and Security

ResourceQuota is primarily a resource-management mechanism, but it can also support workload governance.

For example, it can limit:

* CPU
* Memory
* Number of Pods
* Number of Services
* Number of Secrets

Check:

```bash
kubectl get resourcequota -A
```

An unexpected deployment failure may be caused by quota restrictions.

---

# 28. Encryption

Sensitive data should be protected both:

### In Transit

Use secure communication such as TLS where appropriate.

### At Rest

Kubernetes Secrets and other sensitive information can be protected using encryption mechanisms supported by the cluster.

Security troubleshooting should distinguish:

```text
Data in transit
        vs
Data at rest
```

Do not assume that simply creating a Kubernetes Secret automatically provides complete end-to-end secret security.

---

# 29. Kubernetes API Security

The Kubernetes API server is a critical security boundary.

Security concerns include:

* Authentication
* Authorization
* Admission control
* TLS
* API exposure
* Audit logging
* Credential management

A compromised Kubernetes API credential can potentially provide significant cluster access depending on its permissions.

---

# 30. Admission and Policy Controls

Authentication and RBAC are not necessarily the final security decision.

Admission mechanisms can validate or modify requests before resources are persisted.

Conceptually:

```text
Request
 ↓
Authentication
 ↓
Authorization
 ↓
Admission
 ↓
Resource Creation
```

A request may therefore fail even when the identity has sufficient RBAC permissions.

When troubleshooting denied resource creation, check whether policy or admission controls are involved.

---

# 31. Audit Logging

Kubernetes audit logs can help answer:

* Who performed an action?
* What resource was accessed?
* What operation was attempted?
* When did it happen?
* Was the request successful?

Audit configuration varies by cluster.

For security investigations:

```text
User / Workload
      ↓
API Request
      ↓
Authentication
      ↓
Authorization
      ↓
Admission
      ↓
Resource Change
      ↓
Audit Evidence
```

---

# 32. Node Security

Kubernetes security also depends on the underlying nodes.

Important areas include:

* Operating system security
* Kernel security
* Container runtime
* SSH access
* Node credentials
* Host filesystem access
* Host networking
* HostPath mounts
* Node updates and patching

A Pod may be configured securely while the underlying node remains vulnerable.

---

# 33. HostPath Security

`hostPath` mounts expose directories from the node filesystem to Pods.

Example:

```yaml
volumes:
  - name: host-data
    hostPath:
      path: /var/lib/example
```

HostPath should be used cautiously.

Ask:

> Does this workload actually need direct access to the node filesystem?

If not, use a more isolated storage mechanism.

---

# 34. Common Security Symptoms

| Symptom                             | Possible Cause                           |
| ----------------------------------- | ---------------------------------------- |
| `Forbidden`                         | RBAC / authorization                     |
| Pod cannot access API               | ServiceAccount / RBAC                    |
| Secret inaccessible                 | Secret reference / RBAC / namespace      |
| Connection timeout                  | NetworkPolicy / networking               |
| ImagePullBackOff                    | Registry / credentials / image           |
| Pod rejected                        | Admission / Pod Security                 |
| Permission denied                   | securityContext / filesystem permissions |
| Container cannot write              | read-only filesystem                     |
| Unexpected privileged access        | securityContext                          |
| Resource creation denied            | RBAC / admission / quota                 |
| ServiceAccount has excessive access | Overly broad RBAC                        |
| Application cannot resolve DNS      | NetworkPolicy / DNS configuration        |

---

# 35. Security Troubleshooting Workflow

Use this workflow:

```text
Security Symptom
      ↓
Identify Identity / Workload
      ↓
Identify Resource
      ↓
Check Namespace
      ↓
Check Authentication
      ↓
Check RBAC
      ↓
Check Admission / Policy
      ↓
Check Pod Security
      ↓
Check NetworkPolicy
      ↓
Check Secret / Credential Access
      ↓
Check Image Security
      ↓
Check Node / Runtime
      ↓
Validate With Evidence
      ↓
Apply Minimal Corrective Action
      ↓
Verify
```

---

# 36. Security Decision Tree

```text
Security Problem
      │
      ├── Forbidden?
      │      ↓
      │    Check identity
      │      ↓
      │    Check RBAC
      │      ↓
      │    Check admission/policy
      │
      ├── Network blocked?
      │      ↓
      │    Check NetworkPolicy
      │      ↓
      │    Check DNS
      │      ↓
      │    Check Service/network path
      │
      ├── Pod rejected?
      │      ↓
      │    Check Pod Security
      │      ↓
      │    Check admission policy
      │
      ├── Secret problem?
      │      ↓
      │    Check Secret
      │      ↓
      │    Check namespace/key
      │      ↓
      │    Check ServiceAccount/RBAC
      │
      ├── Image problem?
      │      ↓
      │    Check registry
      │      ↓
      │    Check credentials
      │      ↓
      │    Check ImagePullSecret
      │
      └── Container permission problem?
             ↓
           Check securityContext
             ↓
           Check filesystem
             ↓
           Check capabilities
```

---

# 37. Evidence Collection

For a security incident or troubleshooting investigation, collect evidence before making changes.

Useful commands:

```bash
kubectl get pods -A
```

```bash
kubectl get serviceaccounts -A
```

```bash
kubectl get roles,rolebindings -A
```

```bash
kubectl get clusterroles,clusterrolebindings
```

```bash
kubectl get networkpolicies -A
```

```bash
kubectl get secrets -A
```

```bash
kubectl get pod <pod-name> -n <namespace> -o yaml
```

```bash
kubectl auth can-i <verb> <resource> -n <namespace>
```

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Check events:

```bash
kubectl get events -n <namespace> --sort-by=.lastTimestamp
```

---

# 38. Security Investigation Checklist

### Identity

* [ ] Who is making the request?
* [ ] Which ServiceAccount is being used?
* [ ] Is authentication successful?

### RBAC

* [ ] Is the required Role/ClusterRole present?
* [ ] Is the correct binding present?
* [ ] Is the namespace correct?
* [ ] Does `kubectl auth can-i` confirm the permission?

### Secrets

* [ ] Does the Secret exist?
* [ ] Is it in the correct namespace?
* [ ] Is the correct key referenced?
* [ ] Is access appropriately restricted?

### Network

* [ ] Is NetworkPolicy applied?
* [ ] Is ingress allowed?
* [ ] Is egress allowed?
* [ ] Is DNS reachable?

### Pod Security

* [ ] Is the Pod allowed by configured security policy?
* [ ] Is it running as non-root where appropriate?
* [ ] Are unnecessary capabilities removed?
* [ ] Is privilege escalation disabled where appropriate?

### Images

* [ ] Is the image trusted?
* [ ] Is the registry trusted?
* [ ] Are credentials configured correctly?
* [ ] Is the image version controlled?

### Nodes

* [ ] Is the node healthy?
* [ ] Is the container runtime healthy?
* [ ] Are host-level permissions appropriate?
* [ ] Are sensitive host mounts being used?

---

# 39. Safe Remediation Principles

Security changes should be conservative.

Prefer:

```text
Observe
 ↓
Understand
 ↓
Validate
 ↓
Make Small Change
 ↓
Verify
```

Avoid immediately:

* Granting `cluster-admin`
* Making Pods privileged
* Disabling NetworkPolicies
* Disabling security policies
* Exposing sensitive services
* Sharing credentials
* Removing security controls without understanding their purpose

For example, if an application receives:

```text
Forbidden
```

do not immediately grant:

```text
cluster-admin
```

Instead determine exactly which permission is missing.

---

# 40. Least-Privilege Remediation Example

Instead of:

```text
Application
    ↓
cluster-admin
```

use:

```text
Application
    ↓
ServiceAccount
    ↓
Role
    ↓
get/list/watch
    ↓
Required resource
```

This reduces the potential impact of a compromised workload.

---

# 41. Security Verification

After changing a security configuration, verify:

### Access

```bash
kubectl auth can-i ...
```

### Workload

```bash
kubectl get pods -n production
```

### Network

Test the required application path.

### Secrets

Confirm the application can access only the required Secret.

### Pod Security

Confirm the workload still satisfies the intended security requirements.

### Logs

Check application and Kubernetes events for unexpected failures.

---

# 42. Kube-InsightAI Security Diagnostic Principle

Kube-InsightAI should not treat security failures as isolated errors.

It should trace the complete security path:

```text
Identity
   ↓
Authentication
   ↓
Authorization
   ↓
Admission / Policy
   ↓
Namespace
   ↓
Resource
   ↓
Pod Security
   ↓
Network Policy
   ↓
Secret / Credential
   ↓
Container
   ↓
Node
```

The agent should identify the **first broken security boundary**.

---

# 43. Kube-InsightAI Example

User:

> Why can't my payment-api access the Kubernetes API?

Kube-InsightAI should investigate:

```text
payment-api Pod
      ↓
ServiceAccount
      ↓
Authentication
      ↓
Role / ClusterRole
      ↓
RoleBinding / ClusterRoleBinding
      ↓
Requested API resource
      ↓
Required verb
      ↓
Admission / Policy
```

Suppose the application uses:

```text
ServiceAccount: payment-api
```

and attempts:

```text
list pods
```

but receives:

```text
403 Forbidden
```

The agent should check whether:

```text
payment-api
   ↓
RoleBinding
   ↓
Role
   ↓
pods
   ↓
list
```

is present.

If the Role only permits:

```text
get pods
```

then the missing `list` permission is a likely root cause.

The agent should report the evidence rather than simply saying:

> RBAC is broken.

---

# 44. RAG + MCP Security Investigation

This document provides the **knowledge** required to understand Kubernetes security.

MCP can provide **live evidence**.

For example:

```text
User
 ↓
Kube-InsightAI
 ↓
RAG
 ↓
RBAC Troubleshooting Knowledge
 ↓
MCP
 ↓
Live Cluster
 ↓
ServiceAccount
 ↓
RoleBindings
 ↓
Roles
 ↓
kubectl auth can-i
 ↓
Events / Logs
 ↓
LLM
 ↓
Diagnosis
```

Example:

```text
RAG:
"403 Forbidden commonly requires checking
identity, RBAC permissions, and bindings."

MCP:
"payment-api ServiceAccount cannot list Pods."

LLM:
"The payment-api workload is missing the
list permission for Pods."
```

This demonstrates the separation:

```text
RAG = Security Knowledge
MCP = Live Security Evidence
LLM = Reasoning
LangGraph = Decision / Orchestration
```

---

# 45. Important Security Principle

A security symptom is not automatically a security root cause.

For example:

```text
Application failure
       ↓
403 Forbidden
       ↓
Could be RBAC
       ↓
Could be Admission Policy
       ↓
Could be another authorization layer
```

Similarly:

```text
Connection timeout
       ↓
Could be NetworkPolicy
       ↓
Could be DNS
       ↓
Could be Service
       ↓
Could be routing
       ↓
Could be application
```

Always validate with evidence.

---

# 46. Final Kubernetes Security Checklist

Before declaring a Kubernetes security issue resolved:

```text
[ ] Identity identified
[ ] Authentication verified
[ ] RBAC permissions checked
[ ] Role / ClusterRole checked
[ ] RoleBinding / ClusterRoleBinding checked
[ ] ServiceAccount checked
[ ] Secrets checked
[ ] NetworkPolicies checked
[ ] Pod security configuration checked
[ ] Admission / policy controls considered
[ ] Container image checked
[ ] Registry credentials checked
[ ] Node security considered
[ ] Evidence collected
[ ] Minimal remediation applied
[ ] Access verified
[ ] Workload verified
[ ] Network verified
[ ] No unnecessary privileges introduced
[ ] Security posture verified after remediation
```

---

# 47. Core Principle

> **Kubernetes security troubleshooting means identifying which security boundary is rejecting or exposing the workload, validating that boundary with evidence, and applying the smallest change necessary.**

For Kube-InsightAI:

```text
Security Knowledge
        +
Live Cluster Evidence
        +
LLM Reasoning
        ↓
Evidence-Based Security Diagnosis
```

The goal is not simply to make the error disappear.

The goal is to determine:

```text
WHO
 ↓
is trying to access
 ↓
WHAT
 ↓
through WHICH security boundary
 ↓
and WHY
 ↓
the request was allowed or denied.
```
