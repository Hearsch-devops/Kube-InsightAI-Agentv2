# Kubernetes Networking Troubleshooting SOP

## 1. Purpose

This document provides a systematic procedure for troubleshooting Kubernetes networking problems involving:

* Pod-to-Pod communication
* Pod-to-Service communication
* Service-to-Service communication
* DNS resolution
* NetworkPolicies
* Ingress traffic
* Ports and protocols
* Kubernetes Services
* Cluster networking
* CNI plugins
* Network connectivity failures

The goal is to identify the first broken layer in the Kubernetes network path and determine the root cause.

---

# 2. Kubernetes Networking Overview

Kubernetes networking allows Pods, Services, and external clients to communicate.

A simplified application request path is:

```text
External Client
      ↓
DNS
      ↓
Load Balancer / Ingress
      ↓
Ingress Controller
      ↓
Service
      ↓
Service Selector
      ↓
Pod IP
      ↓
Container Port
      ↓
Application
```

For internal Pod communication:

```text
Pod A
 ↓
Pod B
```

For Service communication:

```text
Pod A
 ↓
Service
 ↓
Endpoint
 ↓
Pod B
```

When troubleshooting networking, identify which communication path is failing.

---

# 3. Kubernetes Networking Principles

Kubernetes networking is based on several important principles.

## 3.1 Every Pod Gets an IP Address

Pods normally receive their own IP address from the cluster network.

Check a Pod IP:

```bash
kubectl get pod <pod-name> -n <namespace> -o wide
```

Example:

```text
NAME       IP            NODE
web-pod    10.244.1.15   worker-1
```

---

## 3.2 Pods Can Communicate with Other Pods

Kubernetes networking is designed so that Pods can communicate across nodes without requiring application-level NAT in the normal cluster networking model.

If Pod-to-Pod communication fails, investigate:

* Pod network configuration
* CNI
* NetworkPolicy
* Routing
* Node networking
* Firewall rules
* Application listening address
* Ports

---

# 4. Identify the Communication Path

Before troubleshooting, define exactly what is failing.

Possible paths:

```text
Pod → Pod
Pod → Service
Service → Pod
Pod → DNS
Pod → External Service
External Client → Ingress
External Client → LoadBalancer
```

Do not treat all network failures as the same problem.

---

# 5. General Networking Troubleshooting Workflow

Use this sequence:

```text
Identify Source
      ↓
Identify Destination
      ↓
Check DNS
      ↓
Check IP Connectivity
      ↓
Check Port
      ↓
Check Service
      ↓
Check Endpoints
      ↓
Check NetworkPolicy
      ↓
Check CNI
      ↓
Check Node Networking
      ↓
Check Application
```

The correct troubleshooting path depends on where the failure occurs.

---

# 6. Check Pod IP Addresses

List Pods with their IPs:

```bash
kubectl get pods -A -o wide
```

Inspect a specific Pod:

```bash
kubectl get pod <pod-name> -n <namespace> -o wide
```

Check:

* Pod IP
* Node
* Pod status
* Readiness

A Pod without a usable IP may indicate a networking or Pod lifecycle problem.

---

# 7. Test Pod-to-Pod Connectivity

If two Pods are expected to communicate, identify their IP addresses:

```bash
kubectl get pods -o wide -n <namespace>
```

Then test connectivity from the source Pod.

For example:

```bash
kubectl exec -it <source-pod> -n <namespace> -- curl http://<destination-pod-ip>:8080
```

If `curl` is unavailable, use another appropriate network diagnostic tool available in the container.

Do not assume that ICMP/ping is supported or meaningful for every application.

Application-level connectivity tests are usually more useful.

---

# 8. Check the Application Listening Address

A common problem is that the application is listening only on localhost.

For example:

```text
127.0.0.1:8080
```

instead of:

```text
0.0.0.0:8080
```

If the application listens only on `127.0.0.1`, other Pods may not be able to reach it through the Pod IP.

Check listening ports inside the container when the required tools are available:

```bash
kubectl exec -it <pod-name> -n <namespace> -- ss -lntp
```

Verify:

```text
Application
   ↓
Listening Address
   ↓
Listening Port
```

---

# 9. Pod Port vs Service Port

A Kubernetes Service commonly contains:

```yaml
ports:
  - port: 80
    targetPort: 8080
```

This means:

```text
Client
 ↓
Service Port 80
 ↓
Pod Target Port 8080
 ↓
Application
```

`port` and `targetPort` do not necessarily have to be the same.

A mismatch can result in connection failures.

Check the Service:

```bash
kubectl get svc <service-name> -n <namespace> -o yaml
```

---

# 10. Service Selector Problems

A Service uses a selector to identify backend Pods.

Example:

```yaml
selector:
  app: web
```

The target Pod must have:

```yaml
labels:
  app: web
```

Check Service configuration:

```bash
kubectl get svc <service-name> -n <namespace> -o yaml
```

Check Pod labels:

```bash
kubectl get pods -n <namespace> --show-labels
```

If the selector does not match the Pod labels, the Service may have no usable endpoints.

---

# 11. Check Service Endpoints

Check the Service:

```bash
kubectl get svc -n <namespace>
```

Check EndpointSlices:

```bash
kubectl get endpointslice -n <namespace>
```

Inspect the relevant EndpointSlice:

```bash
kubectl describe endpointslice <name> -n <namespace>
```

The request path should be:

```text
Client
 ↓
Service
 ↓
EndpointSlice
 ↓
Ready Pod
```

If the Service has no endpoints, investigate:

* Selector mismatch
* Pod labels
* Pod readiness
* Pod status
* Namespace
* EndpointSlice configuration

---

# 12. Test Service Connectivity

From another Pod:

```bash
kubectl exec -it <source-pod> -n <namespace> -- curl http://<service-name>:<port>
```

You can also use the Service DNS name:

```text
<service-name>.<namespace>.svc.cluster.local
```

For example:

```bash
kubectl exec -it <source-pod> -n <namespace> -- curl http://web.default.svc.cluster.local:80
```

If Service connectivity fails, compare:

```text
Service
 ↓
Selector
 ↓
Endpoints
 ↓
Pod IP
 ↓
TargetPort
 ↓
Application
```

---

# 13. Kubernetes DNS

Kubernetes provides DNS-based service discovery.

A Service can normally be accessed using:

```text
service-name
```

within the same namespace.

Across namespaces:

```text
service-name.namespace
```

The full DNS form is:

```text
service-name.namespace.svc.cluster.local
```

Example:

```text
api.production.svc.cluster.local
```

---

# 14. DNS Troubleshooting

If a Service works using its ClusterIP but not its DNS name, investigate DNS.

From a Pod:

```bash
kubectl exec -it <pod-name> -n <namespace> -- cat /etc/resolv.conf
```

Test DNS resolution using available tools:

```bash
kubectl exec -it <pod-name> -n <namespace> -- nslookup <service-name>
```

or:

```bash
kubectl exec -it <pod-name> -n <namespace> -- getent hosts <service-name>
```

Possible causes:

* CoreDNS failure
* Incorrect DNS configuration
* NetworkPolicy blocking DNS
* CNI problems
* Namespace/name mistake
* Cluster networking issue

---

# 15. Check CoreDNS

Check CoreDNS Pods:

```bash
kubectl get pods -n kube-system -l k8s-app=kube-dns
```

Check CoreDNS Service:

```bash
kubectl get svc -n kube-system
```

Check logs:

```bash
kubectl logs -n kube-system -l k8s-app=kube-dns
```

Look for:

* DNS resolution errors
* Upstream resolution errors
* Plugin errors
* Timeouts
* Connection failures

Do not restart CoreDNS blindly. First identify whether DNS is actually the failing layer.

---

# 16. NetworkPolicy

NetworkPolicy controls network traffic between Pods and/or other endpoints when supported by the cluster network implementation.

A NetworkPolicy can restrict:

* Ingress traffic
* Egress traffic
* Namespace-to-namespace communication
* Pod-to-Pod communication
* External communication

List policies:

```bash
kubectl get networkpolicy -A
```

Inspect a policy:

```bash
kubectl describe networkpolicy <policy-name> -n <namespace>
```

---

# 17. NetworkPolicy Troubleshooting

A common scenario:

```text
Pod A
 ↓
Service
 ↓
Pod B
```

The Pods and Service may all appear healthy, but traffic is blocked by NetworkPolicy.

When connectivity fails, ask:

```text
Is there a NetworkPolicy?
        ↓
Does it select the source/destination Pod?
        ↓
Is ingress allowed?
        ↓
Is egress allowed?
        ↓
Is the required port allowed?
        ↓
Is DNS traffic allowed?
```

A NetworkPolicy problem can affect otherwise healthy workloads.

---

# 18. Namespace Isolation

NetworkPolicies can restrict traffic based on namespaces.

Example concept:

```text
frontend namespace
       ↓
       X
       ↓
backend namespace
```

If the frontend cannot reach the backend, inspect:

```bash
kubectl get networkpolicy -A
```

Check whether the policy permits traffic from the frontend namespace to the backend workload.

Verify namespace labels when policies use namespace selectors.

---

# 19. DNS Blocked by NetworkPolicy

A particularly confusing situation occurs when application traffic is allowed but DNS traffic is blocked.

Symptoms may include:

```text
curl http://10.x.x.x:8080
```

works, but:

```text
curl http://service-name:8080
```

fails.

In this case:

```text
Pod
 ↓
DNS
 ↓
CoreDNS
```

may be blocked.

Check NetworkPolicies and ensure the required DNS traffic is permitted.

---

# 20. Ingress Networking

For external HTTP/HTTPS traffic, the request path is commonly:

```text
Internet Client
 ↓
DNS
 ↓
Load Balancer
 ↓
Ingress Controller
 ↓
Ingress Rule
 ↓
Service
 ↓
Pod
 ↓
Application
```

If external access fails, test each layer separately.

---

# 21. Ingress 404

A 404 can indicate that the request reached the Ingress Controller but did not match an expected rule.

Check:

```bash
kubectl get ingress -A
```

Inspect:

```bash
kubectl describe ingress <ingress-name> -n <namespace>
```

Verify:

* Hostname
* Path
* Path type
* IngressClass
* Backend Service

Do not immediately assume that the backend application is down.

---

# 22. Ingress 502 or 503

Errors such as:

```text
502 Bad Gateway
503 Service Unavailable
```

may indicate problems between the Ingress Controller and backend Service.

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

Inspect:

```bash
kubectl get svc -n <namespace>
kubectl get endpointslice -n <namespace>
kubectl get pods -n <namespace>
```

Then test the Service directly from inside the cluster.

---

# 23. LoadBalancer Troubleshooting

Check Services:

```bash
kubectl get svc -A
```

Look for:

```text
TYPE: LoadBalancer
```

Check the external address:

```bash
kubectl get svc <service-name> -n <namespace>
```

If an external address is not assigned, possible causes include:

* Cloud provider integration
* Load balancer controller
* Cloud permissions
* Provider configuration
* Infrastructure availability

The exact troubleshooting process depends on the Kubernetes environment.

---

# 24. NodePort Troubleshooting

For NodePort Services:

```bash
kubectl get svc <service-name> -n <namespace>
```

Verify:

* NodePort
* Service port
* Target port
* Backend endpoints

The general path is:

```text
External Client
 ↓
Node IP
 ↓
NodePort
 ↓
Service
 ↓
Pod
```

A NodePort being configured does not guarantee that the application is reachable.

---

# 25. External Connectivity

Pods may need to communicate with external systems such as:

* APIs
* Databases
* Cloud services
* Package repositories
* External DNS services

Test from the affected Pod:

```bash
kubectl exec -it <pod-name> -n <namespace> -- curl -I https://example.com
```

If external connectivity fails, investigate:

```text
Pod
 ↓
DNS
 ↓
CNI
 ↓
Node Network
 ↓
Firewall / Egress Controls
 ↓
External Destination
```

Possible causes include:

* DNS failure
* Egress NetworkPolicy
* Proxy configuration
* Firewall
* Routing
* NAT
* Cloud networking
* CNI configuration

---

# 26. CNI Troubleshooting

CNI stands for Container Network Interface.

The CNI implementation is responsible for providing Pod networking.

If many Pods across the cluster experience networking failures, investigate the CNI.

Check cluster Pods:

```bash
kubectl get pods -A
```

Identify the CNI components and inspect their status.

Check relevant logs:

```bash
kubectl logs <cni-pod> -n <namespace>
```

Look for:

* Network interface creation errors
* IP allocation failures
* Routing errors
* Plugin failures
* Connectivity problems

A CNI problem can affect multiple workloads simultaneously.

---

# 27. Symptoms of Cluster-Wide Networking Problems

Suspect a broader networking problem when:

* Pods on multiple nodes cannot communicate
* New Pods cannot obtain network connectivity
* Multiple Services fail simultaneously
* DNS fails across many namespaces
* Pods cannot reach external systems
* Network-related errors appear across many nodes

Compare:

```text
Single Pod affected
        vs
Multiple Pods affected
        vs
Multiple Nodes affected
```

The scope of the failure is an important diagnostic signal.

---

# 28. Node-Level Networking

If networking problems are isolated to Pods on one node, investigate the node.

Check:

```bash
kubectl get nodes -o wide
```

Inspect:

```bash
kubectl describe node <node-name>
```

Look for:

* Node conditions
* Network-related events
* Resource pressure
* CNI issues
* Pod networking anomalies

A node-specific problem can make multiple Pods on that node appear unhealthy.

---

# 29. Port Connectivity Testing

When possible, test the exact destination port.

For example:

```bash
kubectl exec -it <source-pod> -n <namespace> -- curl http://<destination>:8080
```

For TCP connectivity testing, tools such as `nc` may be available:

```bash
kubectl exec -it <source-pod> -n <namespace> -- nc -vz <destination> 8080
```

A successful DNS lookup does not prove that the application port is reachable.

Similarly, a reachable port does not prove that the application is functioning correctly.

---

# 30. Connection Refused vs Timeout

These errors provide useful diagnostic information.

## Connection Refused

Example:

```text
Connection refused
```

This often indicates that the destination was reachable but nothing accepted the connection on that port.

Investigate:

* Application process
* Listening port
* TargetPort
* Pod readiness
* Service configuration

---

## Connection Timeout

Example:

```text
Connection timed out
```

This may indicate:

* NetworkPolicy
* Firewall
* Routing problem
* CNI problem
* Node networking problem
* Unreachable destination

Do not treat `connection refused` and `timeout` as identical failures.

---

# 31. Service DNS vs Pod IP

If this works:

```bash
curl http://10.244.1.15:8080
```

but this fails:

```bash
curl http://web-service:80
```

investigate:

```text
DNS
Service
Selector
Endpoints
TargetPort
```

If both fail, investigate deeper into:

```text
Pod
Application
CNI
NetworkPolicy
Node Networking
```

This comparison can quickly narrow down the failing layer.

---

# 32. Namespace Problems

Services and Pods are namespace-scoped.

For example:

```text
frontend/web-service
backend/web-service
```

are different Services.

Always specify the namespace when troubleshooting:

```bash
kubectl get svc <service-name> -n <namespace>
```

Check the source and destination namespaces.

Incorrect namespace assumptions can lead to apparently missing Services or failed DNS lookups.

---

# 33. Application-Level Networking

Kubernetes networking can be healthy while the application itself is broken.

For example:

```text
Pod IP reachable
       ↓
Port reachable
       ↓
Application returns HTTP 500
```

This is not primarily a Kubernetes network problem.

Check:

```bash
kubectl logs <pod-name> -n <namespace>
```

and verify application health.

Always distinguish:

```text
Network failure
        vs
Application failure
```

---

# 34. Useful Networking Commands

### List Pods with IPs

```bash
kubectl get pods -A -o wide
```

### Check Service

```bash
kubectl get svc -n <namespace>
```

### Describe Service

```bash
kubectl describe svc <service-name> -n <namespace>
```

### Check EndpointSlices

```bash
kubectl get endpointslice -n <namespace>
```

### Check Ingress

```bash
kubectl get ingress -A
```

### Describe Ingress

```bash
kubectl describe ingress <ingress-name> -n <namespace>
```

### List NetworkPolicies

```bash
kubectl get networkpolicy -A
```

### Describe NetworkPolicy

```bash
kubectl describe networkpolicy <policy-name> -n <namespace>
```

### Check Nodes

```bash
kubectl get nodes -o wide
```

### Check Node Details

```bash
kubectl describe node <node-name>
```

### Test DNS

```bash
kubectl exec -it <pod-name> -n <namespace> -- nslookup <service-name>
```

### Test HTTP

```bash
kubectl exec -it <pod-name> -n <namespace> -- curl http://<service-name>:<port>
```

### Test TCP Port

```bash
kubectl exec -it <pod-name> -n <namespace> -- nc -vz <destination> <port>
```

---

# 35. Networking Troubleshooting Decision Flow

```text
Network problem
      ↓
Identify source and destination
      ↓
Can source resolve destination?
      │
   ┌──┴──┐
  NO    YES
  ↓      ↓
Check   Can destination
DNS     port be reached?
         │
      ┌──┴──┐
     NO    YES
     ↓      ↓
 Check   Does application
 Service  respond correctly?
 NetworkPolicy
 CNI
 Routing
 Firewall
     ↓
If Service is involved
     ↓
Check selector
     ↓
Check EndpointSlices
     ↓
Check targetPort
     ↓
Check backend Pod
```

---

# 36. Networking Troubleshooting Checklist

When investigating a Kubernetes networking problem:

* [ ] Identify the source
* [ ] Identify the destination
* [ ] Identify the namespace
* [ ] Identify the communication path
* [ ] Check Pod status
* [ ] Check Pod IP
* [ ] Check application listening address
* [ ] Check application listening port
* [ ] Check DNS resolution
* [ ] Check Service
* [ ] Check Service selector
* [ ] Check EndpointSlices
* [ ] Check `port`
* [ ] Check `targetPort`
* [ ] Check NetworkPolicies
* [ ] Check Ingress when applicable
* [ ] Check LoadBalancer/NodePort when applicable
* [ ] Check CNI when appropriate
* [ ] Check node networking
* [ ] Check external connectivity
* [ ] Check application logs
* [ ] Compare connection refused vs timeout
* [ ] Determine whether the problem affects one Pod, one node, or the entire cluster

---

# 37. Verification

After fixing a networking problem, verify the complete request path.

For internal Service traffic:

```text
Source Pod
 ↓
DNS
 ↓
Service
 ↓
EndpointSlice
 ↓
Destination Pod
 ↓
Target Port
 ↓
Application
```

For external traffic:

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

Test the path from the same location where the original failure occurred.

A Service being `Running` or existing in the cluster is not sufficient proof that application traffic works.

---

# 38. Important Troubleshooting Principle

When troubleshooting Kubernetes networking, always locate the **first failed layer**.

For example:

```text
DNS works
 ↓
Service exists
 ↓
Service has endpoints
 ↓
Pod IP reachable
 ↓
Port reachable
 ↓
Application returns error
```

In this case, the Kubernetes network may be healthy and the application may be the actual problem.

Another example:

```text
DNS fails
 ↓
Service cannot be resolved
```

In this case, there is no reason to immediately investigate the application.

Start where the failure first appears.

---

# 39. Kube-InsightAI Diagnostic Principle

Kube-InsightAI should reason about networking as a dependency chain.

```text
Client
 ↓
DNS
 ↓
Ingress / LoadBalancer
 ↓
Service
 ↓
Selector
 ↓
EndpointSlice
 ↓
Pod IP
 ↓
NetworkPolicy
 ↓
Node / CNI
 ↓
Port
 ↓
Application
```

When a user reports:

> "My service is not reachable."

Kube-InsightAI should not immediately conclude that the Service is broken.

It should determine:

1. Who is the client?
2. What is the destination?
3. Is DNS resolving correctly?
4. Does the Service exist?
5. Does the Service selector match the intended Pods?
6. Does the Service have EndpointSlices?
7. Are the backend Pods Ready?
8. Is the target port correct?
9. Is NetworkPolicy blocking traffic?
10. Is the Pod network functioning?
11. Is the node healthy?
12. Is the application listening on the expected address and port?
13. Does the application itself return a valid response?

Kube-InsightAI can later combine this RAG knowledge with live MCP information such as:

```text
kubectl get pods
kubectl get svc
kubectl get endpointslice
kubectl get networkpolicy
kubectl get nodes
kubectl describe pod
kubectl describe svc
kubectl logs
```

This allows the agent to move from:

```text
"What could cause a networking problem?"
```

to:

```text
"What is actually happening in my cluster right now?"
```

---

# 40. Summary

Kubernetes networking troubleshooting should follow the actual communication path:

```text
Client
 ↓
DNS
 ↓
Ingress / LoadBalancer
 ↓
Service
 ↓
EndpointSlice
 ↓
Pod
 ↓
Port
 ↓
Application
```

For internal networking:

```text
Pod
 ↓
DNS
 ↓
Service
 ↓
EndpointSlice
 ↓
Pod
```

The most common areas to investigate include:

* DNS
* Service selectors
* EndpointSlices
* Ports and targetPorts
* NetworkPolicies
* Ingress
* LoadBalancers
* NodePorts
* CNI
* Node networking
* Application listening addresses
* Application-level failures

The most important diagnostic rule is:

> **Find the first broken layer in the network path instead of troubleshooting every layer at once.**
