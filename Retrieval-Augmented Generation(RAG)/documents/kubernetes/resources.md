# Kubernetes Resource Troubleshooting SOP

## 1. Purpose

This document provides a systematic procedure for troubleshooting Kubernetes resource-related problems involving:

* CPU
* Memory
* Resource requests
* Resource limits
* Quality of Service (QoS)
* OOMKilled
* Container resource exhaustion
* Pod scheduling failures
* Node resource pressure
* Evictions
* Horizontal Pod Autoscaling (HPA)
* Vertical Pod Autoscaling (VPA)
* ResourceQuota
* LimitRange

The goal is to determine whether a workload is:

* requesting too many resources,
* receiving too few resources,
* exceeding its limits,
* competing for node capacity,
* being evicted,
* or incorrectly configured for its workload requirements.

---

# 2. Kubernetes Resource Model

Kubernetes schedules workloads based primarily on resource requests.

The most common resources are:

```text
CPU
Memory
```

A container can specify:

```yaml
resources:
  requests:
    cpu: "250m"
    memory: "256Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"
```

The simplified relationship is:

```text
Pod
 ↓
Container
 ↓
Requests + Limits
 ↓
Scheduler / Kubelet
 ↓
Node Resources
```

---

# 3. Resource Requests

A resource request represents the amount of a resource that Kubernetes uses when making scheduling decisions.

Example:

```yaml
resources:
  requests:
    cpu: "250m"
    memory: "256Mi"
```

This tells Kubernetes that the container requests:

```text
CPU:    250 millicores
Memory: 256 MiB
```

The scheduler uses these requests when determining whether a Pod can fit on a node.

---

# 4. CPU Requests

CPU is commonly expressed using:

```text
m = millicores
```

Examples:

```text
100m  = 0.1 CPU
250m  = 0.25 CPU
500m  = 0.5 CPU
1000m = 1 CPU
```

Example:

```yaml
requests:
  cpu: "500m"
```

means the container requests approximately half of one CPU core.

---

# 5. Memory Requests

Memory can be specified using units such as:

```text
Mi
Gi
```

Examples:

```text
128Mi
256Mi
512Mi
1Gi
2Gi
```

Memory requests influence scheduling.

If a node does not have enough allocatable memory to satisfy a Pod's request, the Pod may remain:

```text
Pending
```

---

# 6. Resource Limits

A resource limit defines an upper boundary for a container's resource consumption.

Example:

```yaml
resources:
  limits:
    cpu: "1"
    memory: "1Gi"
```

CPU and memory behave differently when a container approaches its limits.

### CPU

CPU is generally throttled when the container attempts to use more CPU than its configured limit.

### Memory

Memory cannot be throttled in the same way.

If a container exceeds its memory limit, it may be terminated by the kernel and reported by Kubernetes as:

```text
OOMKilled
```

---

# 7. Requests vs Limits

A useful distinction is:

```text
Request = scheduling expectation
Limit   = maximum allowed resource usage
```

For example:

```yaml
resources:
  requests:
    cpu: "250m"
    memory: "256Mi"

  limits:
    cpu: "1"
    memory: "512Mi"
```

This means:

```text
Scheduler considers:
    250m CPU
    256Mi Memory

Container limit:
    1 CPU
    512Mi Memory
```

Do not assume requests and limits must always be identical.

---

# 8. Check Pod Resource Configuration

Inspect the Pod:

```bash
kubectl get pod <pod-name> -n <namespace> -o yaml
```

Look for:

```yaml
resources:
  requests:
  limits:
```

For a Deployment:

```bash
kubectl get deployment <deployment-name> -n <namespace> -o yaml
```

Check the container specification.

---

# 9. Pod Pending Due to Insufficient Resources

A common resource problem is:

```text
Pod = Pending
```

Check:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Look at Events.

A scheduling message may indicate that nodes do not have sufficient:

```text
CPU
Memory
```

Example:

```text
0/3 nodes are available:
insufficient memory
```

Possible causes:

* Requests are too large
* Nodes are heavily utilized
* Cluster has insufficient capacity
* Node is unavailable
* ResourceQuota limits the workload
* Scheduling constraints reduce available nodes

---

# 10. Check Node Capacity

List nodes:

```bash
kubectl get nodes
```

Inspect a node:

```bash
kubectl describe node <node-name>
```

Important fields include:

```text
Capacity
Allocatable
Allocated resources
Conditions
```

The scheduler primarily considers the node's allocatable resources.

---

# 11. Capacity vs Allocatable

A node may have:

```text
Capacity:
    CPU: 8
    Memory: 32Gi
```

but:

```text
Allocatable:
    CPU: 7.8
    Memory: 30Gi
```

The difference can be consumed by Kubernetes system components and other reservations.

Do not assume that all physical node resources are available to application Pods.

---

# 12. Check Current Resource Usage

When metrics are available:

```bash
kubectl top nodes
```

For Pods:

```bash
kubectl top pods -A
```

For a specific namespace:

```bash
kubectl top pods -n <namespace>
```

For a specific Pod:

```bash
kubectl top pod <pod-name> -n <namespace>
```

Resource metrics help answer:

```text
What is being requested?
What is being consumed?
What capacity is available?
```

---

# 13. Requests vs Actual Usage

A Pod may request:

```text
CPU: 2
Memory: 4Gi
```

but actually consume:

```text
CPU: 100m
Memory: 200Mi
```

This can lead to poor cluster utilization because scheduling is based on requests rather than simply current usage.

Conversely, a Pod may request very little but regularly consume much more CPU or memory.

Therefore, compare:

```text
Requested resources
        vs
Actual usage
        vs
Configured limits
```

---

# 14. CPU Throttling

CPU limits can cause throttling.

For example:

```yaml
limits:
  cpu: "500m"
```

If the application needs more CPU than the configured limit, it may be throttled.

Symptoms may include:

* Increased latency
* Slow application response
* Increased request duration
* Lower throughput
* Timeouts during CPU-heavy workloads

Do not automatically conclude that the node lacks CPU.

The container itself may be constrained by its CPU limit.

---

# 15. CPU Troubleshooting

When an application appears CPU constrained:

```text
Check Pod usage
      ↓
Check CPU request
      ↓
Check CPU limit
      ↓
Check node CPU
      ↓
Check application behavior
```

Commands:

```bash
kubectl top pod <pod-name> -n <namespace>
```

```bash
kubectl describe pod <pod-name> -n <namespace>
```

```bash
kubectl describe node <node-name>
```

Determine whether the bottleneck is:

```text
Container limit
Node capacity
Application workload
```

---

# 16. Memory Pressure

Memory problems are different from CPU problems.

When a container needs more memory than its limit, it may be killed.

A common result is:

```text
OOMKilled
```

Check:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Look for:

```text
Last State:
  Reason: OOMKilled
```

Also inspect:

```bash
kubectl get pod <pod-name> -n <namespace> -o json
```

and application logs.

---

# 17. OOMKilled Troubleshooting

When a container is OOMKilled:

```text
Container
 ↓
Memory usage exceeded available boundary
 ↓
Container terminated
 ↓
Kubernetes restarts it
```

Possible causes:

* Memory limit too low
* Application memory leak
* Large workload
* Unexpected traffic
* Large cache
* Excessive concurrency
* Incorrect application configuration

Do not automatically solve every OOMKilled problem by increasing the memory limit.

First determine why memory usage increased.

---

# 18. OOMKilled Decision Process

```text
OOMKilled
   ↓
Check memory limit
   ↓
Check historical/current usage
   ↓
Check application logs
   ↓
Check workload pattern
   ↓
Determine cause
   ↓
Adjust configuration or application
```

Potential solutions may include:

* Increase memory limit
* Increase memory request
* Reduce application memory consumption
* Fix memory leak
* Reduce concurrency
* Adjust caching
* Scale horizontally
* Tune application configuration

---

# 19. Node Memory Pressure

A node can experience memory pressure even when an individual Pod has not exceeded its own memory limit.

Check:

```bash
kubectl describe node <node-name>
```

Look at:

```text
Conditions
```

A node may report:

```text
MemoryPressure
```

When node resources become constrained, Kubernetes may evict Pods.

---

# 20. Pod Eviction

Pods may be evicted when nodes experience resource pressure.

Common causes include:

```text
Memory pressure
Disk pressure
PID pressure
```

Check:

```bash
kubectl get pods -A
```

and:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Also inspect the node:

```bash
kubectl describe node <node-name>
```

Look at:

```text
Conditions
Events
```

An eviction is different from an application voluntarily terminating itself.

---

# 21. Disk Pressure

Although disk is not normally specified in the same way as CPU and memory requests/limits, disk exhaustion can affect workload stability.

Check node conditions:

```bash
kubectl describe node <node-name>
```

Look for:

```text
DiskPressure
```

Possible causes include:

* Container image storage
* Container logs
* Temporary files
* Ephemeral storage consumption

---

# 22. Ephemeral Storage

Containers can consume local ephemeral storage for:

* Writable container layers
* Logs
* Temporary files
* `emptyDir` volumes

Resource configuration can include:

```yaml
resources:
  requests:
    ephemeral-storage: "1Gi"
  limits:
    ephemeral-storage: "2Gi"
```

If a workload consumes excessive ephemeral storage, it may contribute to node disk pressure or be evicted depending on the situation.

---

# 23. ResourceQuota

A namespace may have a ResourceQuota.

List quotas:

```bash
kubectl get resourcequota -n <namespace>
```

Describe:

```bash
kubectl describe resourcequota <quota-name> -n <namespace>
```

A ResourceQuota can limit aggregate resource consumption in a namespace.

Examples include:

```text
CPU requests
CPU limits
Memory requests
Memory limits
Number of Pods
```

A workload may therefore fail even when the cluster has available capacity.

---

# 24. ResourceQuota Troubleshooting

If a Pod cannot be created or updated:

```text
Check namespace
      ↓
Check ResourceQuota
      ↓
Check current quota usage
      ↓
Check requested resources
```

Useful command:

```bash
kubectl describe resourcequota -n <namespace>
```

Compare:

```text
Used
vs
Hard
```

For example:

```text
requests.cpu:
    Used: 8
    Hard: 8
```

A new workload requesting additional CPU may be rejected because the namespace quota has been reached.

---

# 25. LimitRange

A namespace can have a LimitRange that defines default or maximum/minimum resource values.

Check:

```bash
kubectl get limitrange -n <namespace>
```

Inspect:

```bash
kubectl describe limitrange <name> -n <namespace>
```

LimitRange can:

* Set default CPU requests
* Set default memory requests
* Set default limits
* Enforce minimum resources
* Enforce maximum resources

Therefore, a Pod's effective resources may not come entirely from the Pod YAML explicitly written by the developer.

---

# 26. Quality of Service Classes

Kubernetes assigns Pods a QoS class based on their resource configuration.

Common QoS classes are:

```text
Guaranteed
Burstable
BestEffort
```

Check:

```bash
kubectl get pod <pod-name> -n <namespace> -o jsonpath='{.status.qosClass}'
```

---

# 27. Guaranteed QoS

A Pod is generally Guaranteed when every container has CPU and memory requests and limits configured, with the required equality between requests and limits for those resources.

Example:

```yaml
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"
```

Guaranteed workloads receive stronger protection during resource pressure than lower-priority QoS classes.

---

# 28. Burstable QoS

A Pod is generally Burstable when it has resource requests or limits configured but does not satisfy the requirements for Guaranteed QoS.

Example:

```yaml
resources:
  requests:
    cpu: "250m"
    memory: "256Mi"
  limits:
    cpu: "1"
    memory: "1Gi"
```

Burstable workloads can use more resources than their requests when capacity allows, subject to limits and cluster conditions.

---

# 29. BestEffort QoS

A Pod is generally BestEffort when none of its containers specify CPU or memory requests or limits.

Example:

```yaml
containers:
  - name: app
    image: example/app
```

BestEffort workloads have fewer resource guarantees and are more vulnerable during resource pressure.

---

# 30. QoS Troubleshooting

When a Pod is evicted or affected by node pressure, check:

```bash
kubectl get pod <pod-name> -n <namespace> -o jsonpath='{.status.qosClass}'
```

Then investigate:

```text
QoS class
↓
Pod priority
↓
Node pressure
↓
Resource requests
↓
Actual usage
```

QoS is one factor in eviction behavior; it should not be treated as the only factor.

---

# 31. Resource Optimization

Resource optimization requires comparing:

```text
Requested
   ↓
Limited
   ↓
Actual usage
   ↓
Workload behavior
```

If requests are too high:

```text
Poor scheduling efficiency
```

If requests are too low:

```text
Scheduling may appear efficient
but workloads may compete for resources
```

If limits are too low:

```text
CPU throttling
OOMKilled
```

If limits are excessively high:

```text
Reduced ability to constrain workloads
Potentially inefficient resource planning
```

Resource values should be based on observed workload behavior.

---

# 32. Horizontal Pod Autoscaler

HPA automatically adjusts the number of Pod replicas based on configured metrics.

A common CPU-based model is:

```text
High CPU
   ↓
HPA detects target exceeded
   ↓
Increase replicas
   ↓
Distribute workload
```

Check HPAs:

```bash
kubectl get hpa -A
```

Inspect:

```bash
kubectl describe hpa <hpa-name> -n <namespace>
```

Check:

* Current replicas
* Desired replicas
* Current metrics
* Target metrics
* Minimum replicas
* Maximum replicas
* Events

---

# 33. HPA Troubleshooting

If HPA is not scaling:

```text
Check HPA
 ↓
Check metrics
 ↓
Check target
 ↓
Check current replicas
 ↓
Check min/max replicas
 ↓
Check workload resources
```

A common issue is that CPU-based HPA behavior depends on CPU requests.

If CPU utilization is expressed relative to requests, incorrect or missing CPU requests can affect scaling behavior.

Do not assume that installing HPA automatically means Pods will scale correctly.

---

# 34. Vertical Pod Autoscaler

VPA can recommend or adjust resource requests for workloads depending on its configuration and operating mode.

Conceptually:

```text
Historical usage
      ↓
VPA
      ↓
Resource recommendation
      ↓
CPU / Memory requests
```

VPA can help identify workloads whose configured resources do not match observed behavior.

Before relying on VPA recommendations, understand the configured update mode and operational impact.

---

# 35. Resource Troubleshooting for Deployments

For a Deployment:

```bash
kubectl get deployment <deployment-name> -n <namespace>
```

Inspect:

```bash
kubectl describe deployment <deployment-name> -n <namespace>
```

Then inspect its Pods:

```bash
kubectl get pods -n <namespace>
```

A Deployment may fail to achieve the desired replica count because:

```text
Deployment
 ↓
ReplicaSet
 ↓
Pod
 ↓
Scheduler
 ↓
Node capacity
```

The Deployment itself may be healthy while its Pods cannot be scheduled.

---

# 36. Resource Troubleshooting for StatefulSets

For StatefulSets:

```bash
kubectl get statefulset -n <namespace>
```

Inspect:

```bash
kubectl describe statefulset <name> -n <namespace>
```

Then inspect its Pods and resources.

Stateful applications may have:

* High memory requirements
* Storage requirements
* CPU-intensive workloads
* Strict scheduling requirements

Resource problems can therefore interact with storage and scheduling problems.

---

# 37. Resource Problems and Scheduling

Resource-related scheduling can be represented as:

```text
Pod Resource Request
        ↓
Scheduler
        ↓
Node Allocatable Resources
        ↓
Can Pod Fit?
   ┌────┴────┐
  YES       NO
   ↓         ↓
Schedule   Pending
             ↓
       Check Events
```

If a Pod is Pending due to resources, increasing replicas may make the problem worse if no additional capacity exists.

---

# 38. Resource Problems and Application Performance

An application can be technically healthy but resource constrained.

Example:

```text
Pod = Running
Ready = True
CPU = throttled
Application = slow
```

Therefore:

```text
Running ≠ Performing Well
```

Likewise:

```text
Pod = Running
Memory usage = increasing
```

may indicate an upcoming memory failure even before an OOMKilled event occurs.

---

# 39. Useful Resource Commands

### Check Pod resources

```bash
kubectl describe pod <pod-name> -n <namespace>
```

### Inspect Pod YAML

```bash
kubectl get pod <pod-name> -n <namespace> -o yaml
```

### Check Pod resource usage

```bash
kubectl top pod <pod-name> -n <namespace>
```

### Check all Pod usage

```bash
kubectl top pods -A
```

### Check node usage

```bash
kubectl top nodes
```

### Check node resources

```bash
kubectl describe node <node-name>
```

### Check ResourceQuota

```bash
kubectl get resourcequota -n <namespace>
```

### Describe ResourceQuota

```bash
kubectl describe resourcequota -n <namespace>
```

### Check LimitRange

```bash
kubectl get limitrange -n <namespace>
```

### Describe LimitRange

```bash
kubectl describe limitrange <name> -n <namespace>
```

### Check HPA

```bash
kubectl get hpa -A
```

### Describe HPA

```bash
kubectl describe hpa <hpa-name> -n <namespace>
```

### Check QoS

```bash
kubectl get pod <pod-name> -n <namespace> -o jsonpath='{.status.qosClass}'
```

---

# 40. Resource Troubleshooting Decision Flow

```text
Resource Problem
      ↓
Is Pod Pending?
   ┌──┴──┐
  YES    NO
   ↓      ↓
Check   Is Pod
scheduler Running?
events     ↓
   ↓     ┌─┴───────┐
Check   YES       NO
requests ↓          ↓
limits   Is app    Check
quota    slow?     Pod events
nodes      ↓
         Check
         CPU/memory
         usage
            ↓
       ┌────┴─────┐
      CPU        Memory
       ↓            ↓
Check limit     Check limit
usage           usage
throttling      OOMKilled
       ↓            ↓
Check node      Check app
capacity        behavior
```

---

# 41. Resource Troubleshooting Checklist

When investigating a Kubernetes resource problem:

* [ ] Identify affected Pod
* [ ] Check Pod status
* [ ] Check Pod events
* [ ] Check CPU requests
* [ ] Check memory requests
* [ ] Check CPU limits
* [ ] Check memory limits
* [ ] Check actual CPU usage
* [ ] Check actual memory usage
* [ ] Check node allocatable resources
* [ ] Check node conditions
* [ ] Check MemoryPressure
* [ ] Check DiskPressure
* [ ] Check Pod QoS class
* [ ] Check ResourceQuota
* [ ] Check LimitRange
* [ ] Check HPA
* [ ] Check VPA when applicable
* [ ] Check application logs
* [ ] Check for OOMKilled
* [ ] Check for CPU throttling
* [ ] Check whether the issue affects one Pod or many Pods
* [ ] Check whether multiple workloads are competing for node capacity

---

# 42. Verification

After resolving a resource problem, verify:

```text
Pod
 ↓
Resource Configuration
 ↓
Scheduler
 ↓
Node Capacity
 ↓
Actual Usage
 ↓
Application Performance
```

Check:

```bash
kubectl get pods -n <namespace>
```

Then:

```bash
kubectl top pods -n <namespace>
```

And:

```bash
kubectl top nodes
```

Verify that:

* Pods are scheduled
* Pods remain Ready
* Memory is stable
* CPU usage is reasonable
* No repeated OOMKilled events occur
* Nodes are not under unexpected pressure
* HPA behaves as expected when applicable

A Pod being `Running` is not enough. Verify actual workload behavior.

---

# 43. Important Troubleshooting Principle

Always distinguish between:

```text
Requested Resources
        vs
Configured Limits
        vs
Actual Usage
        vs
Node Capacity
```

These are four different concepts.

For example:

```text
Request:
    500Mi memory

Limit:
    1Gi memory

Actual usage:
    900Mi memory

Node:
    Plenty of free memory
```

The Pod may still be healthy because it is below its limit.

Another scenario:

```text
Request:
    500Mi

Limit:
    512Mi

Actual usage:
    700Mi
```

The container may experience:

```text
OOMKilled
```

even if the node has plenty of unused memory.

The container's configured limit matters.

---

# 44. Kube-InsightAI Diagnostic Principle

Kube-InsightAI should reason about resource problems using multiple layers:

```text
Application
     ↓
Container
     ↓
Requests / Limits
     ↓
Pod QoS
     ↓
Scheduler
     ↓
Node Allocatable Resources
     ↓
Node Pressure
     ↓
Cluster Capacity
```

When a user reports:

> "My Pod is slow."

Kube-InsightAI should not immediately recommend increasing CPU.

It should determine:

1. What Pod is affected?
2. What containers does it contain?
3. What CPU and memory requests are configured?
4. What CPU and memory limits are configured?
5. What is the current resource usage?
6. Is CPU throttling occurring?
7. Is memory usage approaching the limit?
8. Has the container been OOMKilled?
9. What is the node's allocatable capacity?
10. Is the node under resource pressure?
11. Is a ResourceQuota limiting the workload?
12. Is an HPA configured?
13. Is the application itself experiencing abnormal workload behavior?

Kube-InsightAI can later combine this RAG knowledge with live MCP data such as:

```text
kubectl top pods
kubectl top nodes
kubectl describe pod
kubectl describe node
kubectl get hpa
kubectl get resourcequota
kubectl get limitrange
```

This allows the agent to distinguish:

```text
"Your Pod has a 512Mi memory limit."
```

from:

```text
"Your Pod is currently using 490Mi of its 512Mi limit and has been OOMKilled repeatedly."
```

The second answer requires live cluster information.

---

# 45. Summary

Kubernetes resource troubleshooting should follow:

```text
Pod
 ↓
Requests / Limits
 ↓
Actual Usage
 ↓
QoS
 ↓
Scheduler
 ↓
Node Allocatable
 ↓
Node Pressure
 ↓
Cluster Capacity
 ↓
Application Behavior
```

The major resource-related problems include:

* Pods stuck Pending because of insufficient resources
* CPU throttling
* Memory exhaustion
* OOMKilled containers
* Node MemoryPressure
* Node DiskPressure
* Pod eviction
* Excessive resource requests
* Insufficient resource requests
* Incorrect resource limits
* ResourceQuota exhaustion
* LimitRange constraints
* HPA configuration problems
* VPA recommendations
* Poor resource sizing

The most important diagnostic rule is:

> **Compare requested resources, configured limits, actual usage, and available node capacity before changing resource values.**
