# Kubernetes Service Troubleshooting SOP

## 1. Purpose

This SOP provides a systematic procedure for diagnosing and troubleshooting Kubernetes Service issues.

It is intended to help identify problems with:

* Service connectivity
* Service discovery
* Service endpoints
* Pod-to-Service communication
* Service selectors
* Service ports
* Target ports
* ClusterIP
* NodePort
* LoadBalancer
* DNS-based Service access

---

# 2. What Is a Kubernetes Service?

A Kubernetes Service provides a stable network endpoint for accessing a group of Pods.

Pods are ephemeral and their IP addresses can change.

A Service provides a stable abstraction that routes network traffic to the appropriate Pods.

The basic relationship is:

```text
             Service
                │
        ┌───────┼───────┐
        ↓       ↓       ↓
      Pod     Pod     Pod
```

The Service uses a **selector** to identify the Pods that should receive traffic.

---

# 3. Why Do We Need Services?

Pod IP addresses are not stable.

For example:

```text
Pod A → 10.0.1.10
Pod B → 10.0.1.11
Pod C → 10.0.1.12
```

If Pod A is deleted and recreated, its IP may change:

```text
Pod A → 10.0.1.25
```

Applications should not need to track these changing IP addresses.

A Service provides a stable endpoint:

```text
Application
     ↓
Service
     ↓
Pods
```

---

# 4. Common Service Types

Kubernetes provides several Service types.

| Type         | Purpose                                                        |
| ------------ | -------------------------------------------------------------- |
| ClusterIP    | Internal cluster access                                        |
| NodePort     | Exposes Service through a port on each node                    |
| LoadBalancer | Exposes Service using an external load balancer when supported |
| ExternalName | Maps a Service to an external DNS name                         |

The default Service type is:

```text
ClusterIP
```

---

# 5. General Service Troubleshooting Workflow

When an application cannot be reached through a Service:

```text
1. Check Service
        ↓
2. Check Service type
        ↓
3. Check Service selector
        ↓
4. Check Service endpoints
        ↓
5. Check target Pods
        ↓
6. Check Pod readiness
        ↓
7. Check Service ports
        ↓
8. Test connectivity
        ↓
9. Check DNS if applicable
        ↓
10. Identify root cause
        ↓
11. Remediate
        ↓
12. Verify connectivity
```

---

# 6. Step 1 — Check the Service

List Services:

```bash
kubectl get services
```

Or:

```bash
kubectl get svc
```

Check a specific Service:

```bash
kubectl get svc <service-name>
```

Example:

```text
NAME          TYPE        CLUSTER-IP     PORT(S)
payment-api   ClusterIP   10.96.45.100   80/TCP
```

Check:

* Service name
* Service type
* ClusterIP
* Service port
* Target port

---

# 7. Step 2 — Describe the Service

Use:

```bash
kubectl describe service <service-name>
```

Inspect:

* Type
* IP
* Ports
* TargetPort
* Selector
* Endpoints
* Events

The **Selector** and **Endpoints** are particularly important when troubleshooting connectivity.

---

# 8. Step 3 — Check the Service Selector

A Service uses labels to select the Pods that receive traffic.

Example Service:

```yaml
selector:
  app: payment-api
```

The target Pod should have the corresponding label:

```yaml
labels:
  app: payment-api
```

Check the Service:

```bash
kubectl get service <service-name> -o yaml
```

Check Pod labels:

```bash
kubectl get pods --show-labels
```

You can also query Pods using the expected selector:

```bash
kubectl get pods -l app=payment-api
```

---

# 9. Service Has No Endpoints

## Symptom

The Service exists, but it has no endpoints.

Check:

```bash
kubectl get endpoints <service-name>
```

Depending on the Kubernetes version and configuration, EndpointSlices may also be used:

```bash
kubectl get endpointslice
```

## Common Causes

* Service selector does not match Pod labels
* No matching Pods exist
* Matching Pods are not Ready
* Pods are in a failed state
* Incorrect namespace

## Investigation

Check Service selector:

```bash
kubectl describe service <service-name>
```

Check Pods:

```bash
kubectl get pods --show-labels
```

Check matching Pods:

```bash
kubectl get pods -l <selector>
```

Check Pod readiness:

```bash
kubectl get pods
```

---

# 10. Service Selector Mismatch

## Symptom

The application Pods are running, but the Service does not route traffic to them.

Example:

Service:

```yaml
selector:
  app: payment-api
```

Pod:

```yaml
labels:
  app: payments-api
```

The labels do not match.

Therefore:

```text
Service Selector
       ≠
Pod Labels
       ↓
No matching endpoints
```

## Investigation

Check Service:

```bash
kubectl get service <service-name> -o yaml
```

Check Pods:

```bash
kubectl get pods --show-labels
```

Compare the selector and labels.

---

# 11. Service Port vs TargetPort

A common Service configuration is:

```yaml
ports:
  - port: 80
    targetPort: 8080
```

These represent different things.

### `port`

The port exposed by the Service.

```text
Service → port 80
```

### `targetPort`

The port on the selected Pod/container that receives traffic.

```text
Service port 80
       ↓
Pod port 8080
```

Conceptually:

```text
Client
  ↓
Service :80
  ↓
Pod :8080
```

An incorrect `targetPort` can prevent traffic from reaching the application.

---

# 12. Troubleshooting Port Configuration

Inspect the Service:

```bash
kubectl get service <service-name> -o yaml
```

Check:

```yaml
ports:
  - port: 80
    targetPort: 8080
```

Inspect the Pod configuration:

```bash
kubectl get pod <pod-name> -o yaml
```

Verify that the application is actually listening on the expected port.

Check container logs:

```bash
kubectl logs <pod-name>
```

---

# 13. Service Exists but Application Is Not Reachable

## Symptom

The Service exists and has an IP, but the application cannot be reached.

## Possible Causes

* No endpoints
* Selector mismatch
* Incorrect targetPort
* Pod not Ready
* Application not listening
* NetworkPolicy blocking traffic
* DNS resolution problem
* Service type does not provide the expected external access

## Investigation

Start with:

```bash
kubectl get svc <service-name>
```

Then:

```bash
kubectl describe svc <service-name>
```

Check endpoints:

```bash
kubectl get endpoints <service-name>
```

Check Pods:

```bash
kubectl get pods
```

Check Pod readiness:

```bash
kubectl get pods
```

Check application logs:

```bash
kubectl logs <pod-name>
```

---

# 14. Test Service Connectivity From Inside the Cluster

For an internal Service, test connectivity from another Pod.

For example:

```bash
kubectl exec -it <test-pod> -- curl http://<service-name>:<port>
```

If DNS is being tested:

```bash
kubectl exec -it <test-pod> -- nslookup <service-name>
```

The exact testing command depends on which utilities are available inside the test container.

---

# 15. Service DNS

Kubernetes provides DNS-based Service discovery.

Within the same namespace, a Service can commonly be accessed using:

```text
<service-name>
```

A fully qualified Service DNS name follows the pattern:

```text
<service-name>.<namespace>.svc.cluster.local
```

Example:

```text
payment-api.production.svc.cluster.local
```

If Service DNS does not work, investigate:

* Service existence
* Service namespace
* DNS configuration
* CoreDNS health
* Network connectivity

---

# 16. DNS Troubleshooting

Check the Service:

```bash
kubectl get svc <service-name>
```

Test DNS from a Pod:

```bash
kubectl exec -it <pod-name> -- nslookup <service-name>
```

Check CoreDNS Pods:

```bash
kubectl get pods -n kube-system
```

If CoreDNS Pods are unhealthy, investigate their status and logs.

---

# 17. ClusterIP Troubleshooting

A `ClusterIP` Service is normally accessible from within the cluster.

Check:

```bash
kubectl get svc <service-name>
```

Example:

```text
NAME          TYPE        CLUSTER-IP
payment-api   ClusterIP   10.96.45.100
```

Test from another Pod:

```bash
kubectl exec -it <test-pod> -- curl http://10.96.45.100:<port>
```

If the ClusterIP is unreachable, investigate:

* Endpoints
* Pod readiness
* Service ports
* NetworkPolicy
* Cluster networking

---

# 18. NodePort Troubleshooting

A `NodePort` Service exposes the Service on a port on each node.

Example:

```yaml
type: NodePort
```

Check:

```bash
kubectl get svc <service-name>
```

Example:

```text
PORT(S)
80:30080/TCP
```

The Service port is:

```text
80
```

The NodePort is:

```text
30080
```

Troubleshoot:

1. Confirm the Service exists.
2. Confirm the NodePort.
3. Confirm endpoints exist.
4. Confirm Pods are Ready.
5. Confirm node accessibility.
6. Check network/firewall rules if traffic originates outside the cluster.

---

# 19. LoadBalancer Troubleshooting

A `LoadBalancer` Service requests an external load balancer when supported by the Kubernetes environment.

Check:

```bash
kubectl get svc <service-name>
```

Look at:

```text
EXTERNAL-IP
```

If the external address remains pending or traffic does not work:

Check:

```bash
kubectl describe service <service-name>
```

Investigate:

* Cloud provider integration
* Load balancer provisioning
* Service configuration
* Endpoints
* Pod readiness
* External networking
* Firewall/security rules

---

# 20. Pods Are Running but Service Has No Endpoints

This is a common troubleshooting scenario.

Example:

```text
Pods:
payment-api-1    Running
payment-api-2    Running
payment-api-3    Running

Service:
payment-api

Endpoints:
<none>
```

Do not assume that because the Pods are `Running`, the Service will automatically route traffic.

Check:

```text
Service Selector
        ↓
Pod Labels
        ↓
Pod Readiness
        ↓
Endpoints
```

All of these should be investigated.

---

# 21. Service and Readiness

A Pod can be running but not Ready.

A Service normally routes traffic only to eligible Ready endpoints.

Example:

```text
Pod:
Running
Not Ready
```

The Pod may therefore not receive Service traffic.

Check:

```bash
kubectl get pods
```

Then inspect the Pod:

```bash
kubectl describe pod <pod-name>
```

Investigate readiness probe failures.

---

# 22. NetworkPolicy and Service Connectivity

A NetworkPolicy can restrict traffic between Pods.

If:

* Service exists
* Endpoints exist
* Pods are Ready
* Ports are correct

but traffic is still blocked, investigate NetworkPolicies.

List NetworkPolicies:

```bash
kubectl get networkpolicy
```

Or:

```bash
kubectl get netpol
```

Inspect a NetworkPolicy:

```bash
kubectl describe networkpolicy <policy-name>
```

Determine whether the source Pod is allowed to communicate with the destination Pod on the required port.

---

# 23. Useful Service Commands

### List Services

```bash
kubectl get svc
```

### Describe Service

```bash
kubectl describe svc <service-name>
```

### Get Service YAML

```bash
kubectl get svc <service-name> -o yaml
```

### Check Endpoints

```bash
kubectl get endpoints <service-name>
```

### Check EndpointSlices

```bash
kubectl get endpointslice
```

### Check Pods and labels

```bash
kubectl get pods --show-labels
```

### Find Pods using a selector

```bash
kubectl get pods -l <selector>
```

### Check NetworkPolicies

```bash
kubectl get networkpolicy
```

### Test DNS

```bash
kubectl exec -it <pod-name> -- nslookup <service-name>
```

### Test HTTP connectivity

```bash
kubectl exec -it <pod-name> -- curl http://<service-name>:<port>
```

---

# 24. Service Troubleshooting Decision Flow

```text
                  Service Problem
                         │
                         ↓
                  Check Service
                         │
                         ↓
                Does Service exist?
                    /          \
                  No            Yes
                  ↓              ↓
             Investigate     Check selector
                                  │
                                  ↓
                         Matching Pods exist?
                           /           \
                         No             Yes
                         ↓                ↓
                   Check labels      Check readiness
                                          │
                                          ↓
                                   Pods Ready?
                                    /      \
                                  No        Yes
                                  ↓          ↓
                           Check probes   Check endpoints
                                             │
                                             ↓
                                      Endpoints exist?
                                       /          \
                                     No            Yes
                                     ↓              ↓
                              Selector/labels    Check ports
                              readiness          │
                                                     ↓
                                               Correct port?
                                                /       \
                                              No         Yes
                                              ↓           ↓
                                        Fix Service   Test network
                                        configuration     │
                                                         ↓
                                                   Check DNS/
                                                  NetworkPolicy
                                                         │
                                                         ↓
                                                    Verify
                                                    connectivity
```

---

# 25. Service Troubleshooting Checklist

```text
☐ Service exists
☐ Correct namespace
☐ Correct Service type
☐ Correct selector
☐ Pod labels match selector
☐ Matching Pods exist
☐ Pods are Ready
☐ Endpoints exist
☐ EndpointSlices are correct
☐ Service port is correct
☐ TargetPort is correct
☐ Application is listening on target port
☐ DNS resolves correctly
☐ NetworkPolicy allows traffic
☐ NodePort configuration is correct
☐ LoadBalancer is provisioned when applicable
☐ External network/firewall rules are correct
```

---

# 26. Verification After Remediation

After making a change, verify the Service:

```bash
kubectl get svc <service-name>
```

Check endpoints:

```bash
kubectl get endpoints <service-name>
```

Check Pods:

```bash
kubectl get pods
```

Test connectivity from an appropriate client or test Pod:

```bash
kubectl exec -it <test-pod> -- curl http://<service-name>:<port>
```

For externally exposed Services, verify access through the appropriate external address or NodePort.

---

# 27. Important Troubleshooting Principle

A Service being `Running` or existing successfully does **not** mean that application traffic will work.

When troubleshooting Service connectivity, follow the complete path:

```text
Client
  ↓
Service
  ↓
Selector
  ↓
Endpoints
  ↓
Ready Pod
  ↓
Target Port
  ↓
Application
```

A failure anywhere in this path can result in connectivity problems.

---

# 28. Kube-InsightAI Diagnostic Principle

When Kube-InsightAI receives a Service-related question, it should correlate:

```text
Service
   +
Selector
   +
Pod Labels
   +
Pod Readiness
   +
Endpoints
   +
Service Port
   +
TargetPort
   +
DNS
   +
NetworkPolicy
   ↓
Root Cause
```

The RAG knowledge base provides the documented troubleshooting procedure.

Later, MCP can retrieve the actual Service, Endpoint, Pod, NetworkPolicy, and cluster information.

The agent can combine the documented procedure with live cluster state to determine the likely cause and provide recommended next steps.
