# Kubernetes Ingress Troubleshooting SOP

## 1. Purpose

This SOP provides a systematic procedure for diagnosing and troubleshooting Kubernetes Ingress issues.

It is intended to help identify problems with:

* External HTTP/HTTPS access
* Host-based routing
* Path-based routing
* Ingress rules
* Backend Services
* TLS configuration
* DNS configuration
* Ingress Controllers
* Load balancers
* HTTP 404 errors
* HTTP 502/503 errors
* Certificate-related problems

---

# 2. What Is Kubernetes Ingress?

Ingress is an API object that defines rules for routing external HTTP and HTTPS traffic to Services inside a Kubernetes cluster.

A typical request flow is:

```text
Client
  ↓
DNS
  ↓
Load Balancer / External IP
  ↓
Ingress Controller
  ↓
Ingress Rules
  ↓
Service
  ↓
Pod
  ↓
Application
```

An Ingress resource defines the routing rules.

An **Ingress Controller** is responsible for implementing those rules and handling the actual network traffic.

---

# 3. Ingress vs Ingress Controller

These concepts should not be confused.

### Ingress

Defines routing configuration.

Example:

```text
example.com/api
       ↓
payment-service
```

### Ingress Controller

Processes the Ingress configuration and handles incoming traffic.

Examples include controllers based on:

* NGINX
* HAProxy
* Traefik
* Cloud-provider implementations

The exact behavior and configuration depend on the controller being used.

---

# 4. General Ingress Troubleshooting Workflow

When external access through an Ingress fails:

```text id="4o3u1k"
1. Check Ingress resource
        ↓
2. Check Ingress Controller
        ↓
3. Check Ingress rules
        ↓
4. Check DNS
        ↓
5. Check external address
        ↓
6. Check backend Service
        ↓
7. Check Service endpoints
        ↓
8. Check Pods
        ↓
9. Check TLS if HTTPS is used
        ↓
10. Check controller logs
        ↓
11. Identify root cause
        ↓
12. Remediate
        ↓
13. Verify external access
```

---

# 5. Step 1 — Check the Ingress Resource

List Ingress resources:

```bash
kubectl get ingress
```

Or:

```bash
kubectl get ing
```

Check a specific Ingress:

```bash
kubectl get ingress <ingress-name>
```

Example:

```text
NAME            CLASS   HOSTS           ADDRESS        PORTS
app-ingress     nginx   example.com     203.0.113.10  80,443
```

Inspect:

* Ingress name
* Ingress class
* Host
* Address
* Ports
* Age

---

# 6. Step 2 — Describe the Ingress

Use:

```bash
kubectl describe ingress <ingress-name>
```

Inspect:

* Rules
* Hosts
* Paths
* Backend Services
* Ports
* TLS configuration
* Events

The `Rules` and `Events` sections are particularly useful during troubleshooting.

---

# 7. Step 3 — Check the Ingress Class

Ingress resources can specify an Ingress class.

Check:

```bash
kubectl get ingress <ingress-name> -o yaml
```

Look for:

```yaml
spec:
  ingressClassName: nginx
```

List available IngressClasses:

```bash
kubectl get ingressclass
```

If the Ingress references an incorrect or unavailable class, the expected controller may not process the resource.

---

# 8. Ingress Has No Address

## Symptom

The Ingress resource exists, but the `ADDRESS` field is empty or not populated as expected.

Example:

```text
NAME          CLASS   HOSTS          ADDRESS
app-ingress   nginx   example.com
```

## Common Causes

* Ingress Controller is not running
* Ingress Controller is not watching the Ingress class
* Load balancer provisioning problem
* Cloud-provider integration problem
* Incorrect Ingress configuration

## Investigation

Check the Ingress:

```bash
kubectl describe ingress <ingress-name>
```

Check IngressClasses:

```bash
kubectl get ingressclass
```

Check the Ingress Controller Pods:

```bash
kubectl get pods -A
```

Identify the namespace and controller being used, then inspect its resources and logs.

---

# 9. Check the Ingress Controller

The Ingress Controller is responsible for processing Ingress resources and handling traffic.

First identify the controller:

```bash
kubectl get pods -A
```

Then inspect its Pods:

```bash
kubectl get pods -n <controller-namespace>
```

Describe a controller Pod:

```bash
kubectl describe pod <controller-pod> -n <controller-namespace>
```

Check controller logs:

```bash
kubectl logs <controller-pod> -n <controller-namespace>
```

Controller logs can reveal:

* Invalid configuration
* Backend connection problems
* TLS configuration errors
* Failed reloads
* Routing problems

---

# 10. Host-Based Routing

An Ingress can route traffic based on the requested hostname.

Example:

```yaml
rules:
  - host: app.example.com
```

Traffic:

```text
app.example.com
       ↓
   Ingress
       ↓
 app-service
```

If the request uses the wrong hostname, the expected rule may not match.

Check:

```bash
kubectl describe ingress <ingress-name>
```

Verify:

* Hostname
* DNS record
* Client request hostname

---

# 11. Path-Based Routing

An Ingress can route traffic based on URL paths.

Example:

```text
example.com/api
       ↓
api-service

example.com/web
       ↓
web-service
```

Inspect:

```bash
kubectl describe ingress <ingress-name>
```

Verify:

* Path
* Path type
* Backend Service
* Backend port

Incorrect path configuration can result in unexpected routing or HTTP errors.

---

# 12. Ingress Returns HTTP 404

## Symptom

The client reaches the Ingress endpoint but receives:

```text
HTTP 404 Not Found
```

## Possible Causes

* Host does not match an Ingress rule
* Path does not match an Ingress rule
* Incorrect Ingress class
* Controller-specific routing configuration
* Application itself returns 404

## Investigation

Check the Ingress:

```bash
kubectl describe ingress <ingress-name>
```

Verify:

* Host
* Path
* Ingress class
* Backend Service

Test using the expected hostname.

If necessary, determine whether the 404 is generated by the Ingress Controller or the backend application.

---

# 13. Ingress Returns HTTP 502

## Symptom

The client receives:

```text
HTTP 502 Bad Gateway
```

## Common Causes

* Backend Service cannot be reached
* Service has no valid endpoints
* Incorrect Service port
* Incorrect targetPort
* Backend application is unavailable
* Network connectivity problem

## Investigation

Check the Ingress:

```bash
kubectl describe ingress <ingress-name>
```

Check the backend Service:

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

Check application logs:

```bash
kubectl logs <pod-name>
```

Check Ingress Controller logs:

```bash
kubectl logs <controller-pod> -n <controller-namespace>
```

Follow the request path:

```text
Ingress
  ↓
Service
  ↓
Endpoints
  ↓
Pod
  ↓
Application
```

---

# 14. Ingress Returns HTTP 503

## Symptom

The client receives:

```text
HTTP 503 Service Unavailable
```

## Common Causes

* No healthy backend endpoints
* Backend Pods are not Ready
* Service has no endpoints
* Ingress Controller cannot reach the backend
* Application is unavailable

## Investigation

Check:

```bash
kubectl get svc <service-name>
```

Then:

```bash
kubectl get endpoints <service-name>
```

Then:

```bash
kubectl get pods
```

Check readiness:

```bash
kubectl get pods
```

Inspect failing Pods:

```bash
kubectl describe pod <pod-name>
```

Check Ingress Controller logs.

---

# 15. Check Backend Service

Every Ingress backend must ultimately route traffic to a Service or another supported backend configuration.

Inspect the Ingress:

```bash
kubectl describe ingress <ingress-name>
```

Identify the backend Service.

Then:

```bash
kubectl get svc <service-name>
```

Describe it:

```bash
kubectl describe svc <service-name>
```

Verify:

* Service exists
* Correct namespace
* Correct port
* Correct targetPort
* Correct selector
* Endpoints exist

---

# 16. Check Backend Endpoints

A Service can exist without having usable endpoints.

Check:

```bash
kubectl get endpoints <service-name>
```

Also inspect EndpointSlices:

```bash
kubectl get endpointslice
```

If there are no appropriate endpoints, investigate:

```text
Service Selector
       ↓
Pod Labels
       ↓
Pod Readiness
       ↓
Endpoints
```

Ingress cannot successfully route to a backend that has no usable endpoints.

---

# 17. TLS Troubleshooting

For HTTPS traffic, inspect the Ingress TLS configuration.

Example:

```yaml
tls:
  - hosts:
      - app.example.com
    secretName: app-tls
```

Check the Secret:

```bash
kubectl get secret <secret-name>
```

Describe it:

```bash
kubectl describe secret <secret-name>
```

Verify:

* Secret exists
* Secret is in the correct namespace
* Correct hostname is covered by the certificate
* Certificate is valid
* Ingress references the correct Secret

---

# 18. TLS Secret Missing

## Symptom

HTTPS configuration does not work because the referenced TLS Secret cannot be found.

Check:

```bash
kubectl get secret <secret-name>
```

If the Secret is missing:

```text
Ingress
  ↓
TLS configuration
  ↓
Secret
  ↓
Missing
```

Investigate:

* Secret name
* Namespace
* Ingress configuration
* Certificate management system, if applicable

---

# 19. Certificate Problems

Possible certificate problems include:

* Certificate expired
* Certificate hostname mismatch
* Incorrect certificate
* Incorrect TLS Secret
* Certificate not trusted by the client
* Certificate provisioning failure

Check the Secret:

```bash
kubectl get secret <secret-name> -o yaml
```

If a certificate management system is used, also inspect the relevant certificate resources and controller logs.

---

# 20. DNS Troubleshooting

The hostname in the Ingress rule must resolve to the appropriate external endpoint.

Example:

```text
app.example.com
       ↓
DNS
       ↓
Ingress external address
```

Check the Ingress address:

```bash
kubectl get ingress <ingress-name>
```

Then verify DNS resolution using an appropriate DNS utility:

```bash
nslookup app.example.com
```

or:

```bash
dig app.example.com
```

Verify that the DNS record points to the expected endpoint.

---

# 21. Ingress Controller Logs

When the Ingress configuration appears correct but traffic still fails, inspect controller logs.

```bash
kubectl logs <controller-pod> -n <controller-namespace>
```

Look for:

* Configuration errors
* Failed backend connections
* TLS errors
* Invalid routing configuration
* Upstream failures
* Reload failures

Controller logs should be interpreted together with the Ingress, Service, Endpoint, and Pod state.

---

# 22. NetworkPolicy and Ingress

A NetworkPolicy can restrict communication between the Ingress Controller and backend Pods.

If:

```text
Ingress
   ↓
Service
   ↓
Endpoints
```

appears correct, but traffic still cannot reach the application, investigate NetworkPolicies.

List policies:

```bash
kubectl get networkpolicy
```

Inspect:

```bash
kubectl describe networkpolicy <policy-name>
```

Determine whether traffic from the Ingress Controller to the backend Pods is allowed.

---

# 23. Ingress Backend Port Mismatch

An Ingress backend references a Service port.

Example:

```yaml
backend:
  service:
    name: payment-service
    port:
      number: 80
```

The Service must expose the expected port.

Check:

```bash
kubectl get svc payment-service
```

Verify:

```text
Ingress backend port
        ↓
Service port
        ↓
Service targetPort
        ↓
Pod/application port
```

A mismatch can result in failed backend connections.

---

# 24. Application Works Through Service but Not Through Ingress

## Symptom

The application is reachable directly through the Service but not through the Ingress.

Example:

```text
Service access:
Working

Ingress access:
Failing
```

## Investigation

Check in this order:

```text
DNS
 ↓
Ingress external address
 ↓
Ingress rule
 ↓
Ingress Controller
 ↓
Backend Service
 ↓
Endpoints
 ↓
Pods
```

If direct Service access works, focus the investigation on:

* DNS
* Ingress rules
* Ingress class
* Controller configuration
* TLS
* External load balancer
* Controller-to-backend connectivity

---

# 25. Useful Ingress Commands

### List Ingress resources

```bash
kubectl get ingress
```

### Describe Ingress

```bash
kubectl describe ingress <ingress-name>
```

### Get Ingress YAML

```bash
kubectl get ingress <ingress-name> -o yaml
```

### List IngressClasses

```bash
kubectl get ingressclass
```

### Check Services

```bash
kubectl get svc
```

### Check Endpoints

```bash
kubectl get endpoints
```

### Check EndpointSlices

```bash
kubectl get endpointslice
```

### Check Pods

```bash
kubectl get pods -A
```

### Check controller logs

```bash
kubectl logs <controller-pod> -n <controller-namespace>
```

### Check DNS

```bash
nslookup <hostname>
```

or:

```bash
dig <hostname>
```

### Check TLS Secret

```bash
kubectl get secret <secret-name>
```

---

# 26. Ingress Troubleshooting Decision Flow

```text
                    Ingress Problem
                           │
                           ↓
                  Check Ingress Resource
                           │
                           ↓
                  Ingress exists?
                    /          \
                  No            Yes
                  ↓              ↓
             Fix resource   Check IngressClass
                                  │
                                  ↓
                         Controller processing it?
                            /             \
                          No               Yes
                          ↓                 ↓
                  Check controller      Check DNS
                  and class             │
                                        ↓
                                  DNS resolves?
                                   /       \
                                 No         Yes
                                 ↓           ↓
                           Fix DNS      Check backend
                                            │
                                            ↓
                                     Service exists?
                                      /          \
                                    No            Yes
                                    ↓              ↓
                               Fix Service    Check endpoints
                                                   │
                                                   ↓
                                            Endpoints exist?
                                             /          \
                                           No            Yes
                                           ↓              ↓
                                    Check selector/   Check ports
                                    readiness             │
                                                         ↓
                                                   Backend works?
                                                    /        \
                                                  No          Yes
                                                  ↓            ↓
                                            Check Pods,    Check TLS/
                                            logs, network  controller
                                                              │
                                                              ↓
                                                           Verify
                                                          external
                                                          access
```

---

# 27. Ingress Troubleshooting Checklist

```text
☐ Ingress exists
☐ Correct namespace
☐ Correct IngressClass
☐ Ingress Controller is running
☐ Controller is processing the Ingress
☐ External address is available
☐ DNS points to the expected endpoint
☐ Host rule is correct
☐ Path rule is correct
☐ Backend Service exists
☐ Backend Service port is correct
☐ Service targetPort is correct
☐ Service has endpoints
☐ Backend Pods are Ready
☐ Backend application is healthy
☐ NetworkPolicy allows required traffic
☐ TLS Secret exists
☐ TLS hostname is correct
☐ Certificate is valid
☐ Controller logs show no relevant errors
```

---

# 28. Verification After Remediation

After making a change:

### Check Ingress

```bash
kubectl get ingress <ingress-name>
```

### Check Service

```bash
kubectl get svc <service-name>
```

### Check endpoints

```bash
kubectl get endpoints <service-name>
```

### Check Pods

```bash
kubectl get pods
```

### Test DNS

```bash
nslookup <hostname>
```

### Test HTTP/HTTPS access

Use an appropriate client:

```bash
curl -I https://<hostname>
```

Verify:

* DNS resolves correctly
* External endpoint is reachable
* Correct Ingress rule is selected
* Backend Service is reachable
* Backend Pods are healthy
* HTTPS certificate is valid when TLS is configured
* Expected HTTP response is returned

---

# 29. Important Troubleshooting Principle

Ingress troubleshooting should follow the complete request path:

```text
Client
  ↓
DNS
  ↓
External IP / Load Balancer
  ↓
Ingress Controller
  ↓
Ingress Rule
  ↓
Service
  ↓
Endpoints
  ↓
Pod
  ↓
Application
```

Do not immediately assume the Ingress resource is the problem.

A failure further downstream—for example, a Service with no endpoints—can appear to the user as an Ingress failure.

---

# 30. Kube-InsightAI Diagnostic Principle

When Kube-InsightAI receives an Ingress-related question, it should correlate:

```text
Ingress
   +
IngressClass
   +
Ingress Controller
   +
DNS
   +
External Address
   +
Routing Rules
   +
Backend Service
   +
Endpoints
   +
Pods
   +
TLS
   +
NetworkPolicy
   +
Controller Logs
   ↓
Root Cause
```

The RAG knowledge base provides the documented troubleshooting procedure.

Later, MCP can retrieve the actual Ingress, IngressClass, Service, Endpoint, Pod, DNS-related configuration, and controller information from the environment.

The agent can combine the documented procedure with live cluster state to determine the likely cause and provide recommended next steps.
