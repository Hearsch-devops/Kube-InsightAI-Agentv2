# Kubernetes Scheduling Troubleshooting SOP

## 1. Purpose

This document provides a systematic procedure for troubleshooting Kubernetes scheduling problems involving:

* Pending Pods
* Kubernetes Scheduler
* Node selection
* Node labels
* Node selectors
* Node affinity
* Pod affinity
* Pod anti-affinity
* Taints
* Tolerations
* Topology constraints
* Resource availability
* Unschedulable nodes
* Scheduling failures
* Priority and preemption

The goal is to identify why a Pod cannot be scheduled and determine the first scheduling constraint preventing placement.

---

# 2. Kubernetes Scheduling Overview

The Kubernetes Scheduler determines which node should run a newly created Pod.

The simplified process is:

```text
Pod Created
    ↓
Scheduler
    ↓
Evaluate Nodes
    ↓
Filter Nodes
    ↓
Score Suitable Nodes
    ↓
Select Node
    ↓
Bind Pod to Node
    ↓
Kubelet Starts Pod
```

If no node satisfies the Pod's requirements, the Pod remains:

```text
Pending
```

---

# 3. Basic Scheduling Flow

A simplified scheduling decision looks like:

```text
New Pod
   ↓
Does node have enough resources?
   ↓
Does node satisfy scheduling constraints?
   ↓
Are node taints tolerated?
   ↓
Does node satisfy affinity rules?
   ↓
Does topology requirement work?
   ↓
Is node schedulable?
   ↓
Schedule Pod
```

A Pod may fail scheduling because of any one of these conditions.

---

# 4. Check Pod Status

Start by checking the Pod:

```bash
kubectl get pod <pod-name> -n <namespace>
```

If it shows:

```text
STATUS: Pending
```

inspect the Pod:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

The most important section is:

```text
Events
```

Scheduling failures are often explained in the Pod events.

---

# 5. Check Scheduler Events

Example:

```text
0/3 nodes are available:
2 Insufficient memory,
1 node had untolerated taint.
```

This is extremely useful because it tells you why nodes were rejected.

Possible scheduling messages may involve:

* Insufficient CPU
* Insufficient memory
* Untolerated taint
* Node selector mismatch
* Node affinity mismatch
* Pod affinity rules
* Pod anti-affinity rules
* Volume topology
* Node unschedulable
* Resource constraints

Do not immediately change the Pod specification.

First understand why the scheduler rejected the available nodes.

---

# 6. Resource-Based Scheduling

Resource requests are a major scheduling input.

Example:

```yaml
resources:
  requests:
    cpu: "2"
    memory: "4Gi"
```

The scheduler checks whether a node has sufficient allocatable resources for the request.

Conceptually:

```text
Pod Request
     ↓
Node Allocatable Capacity
     ↓
Can Pod Fit?
   ┌───┴───┐
  YES     NO
   ↓       ↓
Schedule Pending
```

---

# 7. Insufficient CPU

A Pod may remain Pending because nodes do not have enough CPU capacity.

Check:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Look at Events.

Then inspect nodes:

```bash
kubectl get nodes
```

and:

```bash
kubectl describe node <node-name>
```

Check:

```text
Allocatable
Allocated resources
```

If the Pod requests more CPU than any suitable node can provide, it cannot be scheduled.

---

# 8. Insufficient Memory

The same principle applies to memory.

Example:

```yaml
resources:
  requests:
    memory: "8Gi"
```

If no eligible node can satisfy the request, the Pod remains Pending.

Check:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

and:

```bash
kubectl describe node <node-name>
```

Do not confuse:

```text
Current memory usage
```

with:

```text
Memory available for scheduling
```

Scheduling primarily considers resource requests and allocatable capacity.

---

# 9. Node Selector

A `nodeSelector` restricts a Pod to nodes with specific labels.

Example:

```yaml
spec:
  nodeSelector:
    disktype: ssd
```

The Pod can only be scheduled onto nodes labeled:

```text
disktype=ssd
```

Check node labels:

```bash
kubectl get nodes --show-labels
```

Or:

```bash
kubectl get node <node-name> --show-labels
```

If no node has the required label, the Pod remains Pending.

---

# 10. Node Selector Troubleshooting

When a Pod uses `nodeSelector`:

```text
Pod
 ↓
nodeSelector
 ↓
Node Labels
 ↓
Matching Node?
```

Check the Pod:

```bash
kubectl get pod <pod-name> -n <namespace> -o yaml
```

Look for:

```yaml
nodeSelector:
```

Then check nodes:

```bash
kubectl get nodes --show-labels
```

Common problems include:

* Typo in label key
* Typo in label value
* Label removed from node
* Wrong node selected
* No nodes have the required label

---

# 11. Node Affinity

Node affinity provides more expressive node-selection rules than `nodeSelector`.

Example:

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: disktype
              operator: In
              values:
                - ssd
```

This requires the Pod to be scheduled on a node satisfying the rule.

---

# 12. Required vs Preferred Node Affinity

Node affinity commonly uses two approaches.

### Required

```text
requiredDuringSchedulingIgnoredDuringExecution
```

The requirement must be satisfied.

If no node satisfies it:

```text
Pod = Pending
```

### Preferred

```text
preferredDuringSchedulingIgnoredDuringExecution
```

The scheduler prefers matching nodes but can schedule elsewhere if necessary.

Conceptually:

```text
Required = Must match
Preferred = Prefer match
```

This distinction is important when diagnosing scheduling behavior.

---

# 13. Node Affinity Troubleshooting

Check the Pod:

```bash
kubectl get pod <pod-name> -n <namespace> -o yaml
```

Inspect:

```yaml
affinity:
  nodeAffinity:
```

Then compare the rules against node labels:

```bash
kubectl get nodes --show-labels
```

If the rule is required and no node satisfies it, the Pod cannot be scheduled.

---

# 14. Taints

A taint marks a node so that Pods without a matching toleration are prevented from scheduling there.

Example:

```bash
kubectl taint nodes <node-name> dedicated=database:NoSchedule
```

Conceptually:

```text
Node
 ↓
Taint
 ↓
Does Pod tolerate it?
 ┌────┴────┐
YES       NO
 ↓         ↓
Allowed   Rejected
```

---

# 15. Taint Effects

Common taint effects include:

```text
NoSchedule
PreferNoSchedule
NoExecute
```

### NoSchedule

New Pods that do not tolerate the taint are not scheduled onto the node.

### PreferNoSchedule

The scheduler tries to avoid placing Pods that do not tolerate the taint on the node.

### NoExecute

Affects scheduling and can also cause existing Pods that do not tolerate the taint to be evicted.

---

# 16. Tolerations

A toleration allows a Pod to tolerate a matching node taint.

Example:

```yaml
tolerations:
  - key: dedicated
    operator: Equal
    value: database
    effect: NoSchedule
```

This does not force the Pod onto the node.

It only means:

```text
Pod is allowed to run there.
```

This distinction is important.

```text
Toleration ≠ Node Selection
```

A toleration permits placement; it does not necessarily choose the node.

---

# 17. Taint and Toleration Troubleshooting

Check node taints:

```bash
kubectl describe node <node-name>
```

Look for:

```text
Taints:
```

Check Pod tolerations:

```bash
kubectl get pod <pod-name> -n <namespace> -o yaml
```

Look for:

```yaml
tolerations:
```

Compare:

```text
Node Taint
     ↓
Pod Toleration
     ↓
Do they match?
```

A mismatch can cause:

```text
Pod Pending
```

---

# 18. Unschedulable Nodes

A node can be marked unschedulable.

Check:

```bash
kubectl get nodes
```

A node may show:

```text
SchedulingDisabled
```

Inspect:

```bash
kubectl describe node <node-name>
```

If a node has been cordoned:

```bash
kubectl cordon <node-name>
```

new Pods are not scheduled there.

Existing Pods are not automatically removed merely because the node was cordoned.

---

# 19. Uncordoning a Node

To allow scheduling again:

```bash
kubectl uncordon <node-name>
```

Before doing this, determine why the node was cordoned.

Possible reasons include:

* Maintenance
* Hardware problems
* Planned upgrades
* Incident response
* Node replacement

Do not automatically uncordon a node without understanding the operational reason.

---

# 20. Pod Affinity

Pod affinity allows a Pod to prefer or require placement near other Pods based on labels and topology.

Example concept:

```text
Frontend Pod
     ↓
Prefer
     ↓
Backend Pod
     ↓
Same topology domain
```

Pod affinity can be used when workloads benefit from being located close to each other.

---

# 21. Pod Anti-Affinity

Pod anti-affinity helps spread workloads apart.

Example:

```text
web-1 → Node 1
web-2 → Node 2
web-3 → Node 3
```

This can improve availability by avoiding placing replicas on the same failure domain.

A required anti-affinity rule can prevent scheduling if there is not enough space to satisfy it.

---

# 22. Affinity Troubleshooting

When affinity or anti-affinity causes Pending Pods, inspect:

```bash
kubectl get pod <pod-name> -n <namespace> -o yaml
```

Look for:

```yaml
affinity:
```

Then inspect:

* Match labels
* Topology key
* Required/preferred behavior
* Existing Pods
* Node labels

The scheduler evaluates the complete set of constraints.

---

# 23. Topology Constraints

Topology constraints control how Pods are distributed across failure domains.

Examples include:

```text
Node
Zone
Region
```

A topology rule can require Pods to be distributed across zones or nodes.

Example concept:

```text
Zone A       Zone B       Zone C

Pod 1        Pod 2        Pod 3
```

This can improve resilience.

However, overly strict topology constraints can prevent scheduling when insufficient suitable nodes exist.

---

# 24. Topology Spread Constraints

A Pod can specify:

```yaml
topologySpreadConstraints:
```

These constraints influence how replicas are distributed across topology domains.

Check:

```bash
kubectl get pod <pod-name> -n <namespace> -o yaml
```

Look for:

```yaml
topologySpreadConstraints:
```

Investigate:

* `topologyKey`
* `maxSkew`
* `whenUnsatisfiable`
* Pod selector
* Available topology domains

---

# 25. Volumes and Scheduling

Storage can affect scheduling.

For example:

```text
Pod
 ↓
PVC
 ↓
PV
 ↓
Topology
 ↓
Eligible Nodes
```

A volume may only be available in certain zones or nodes depending on the storage implementation.

When a Pod uses persistent storage and remains Pending, investigate both:

```text
Scheduling
```

and:

```text
Storage
```

Useful commands:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

```bash
kubectl describe pv <pv-name>
```

---

# 26. ResourceQuota and Scheduling

ResourceQuota can prevent workload creation or updates at the namespace level.

Check:

```bash
kubectl get resourcequota -n <namespace>
```

Then:

```bash
kubectl describe resourcequota -n <namespace>
```

A quota issue is different from a node capacity issue.

Distinguish:

```text
Namespace quota
        vs
Node capacity
```

---

# 27. Priority Classes

Kubernetes supports Pod priorities.

Check PriorityClasses:

```bash
kubectl get priorityclass
```

A Pod can specify:

```yaml
priorityClassName: high-priority
```

Higher-priority Pods can receive scheduling preference over lower-priority Pods.

Priority can become important when the cluster is under resource pressure.

---

# 28. Preemption

Preemption allows a higher-priority Pod to make room for itself by causing lower-priority Pods to be removed when appropriate.

Conceptually:

```text
High Priority Pod
       ↓
No suitable capacity
       ↓
Can lower-priority Pods be preempted?
       ↓
YES
       ↓
Victim Pods removed
       ↓
High Priority Pod scheduled
```

Preemption should not be treated as the first solution to a capacity problem.

Investigate the scheduling constraints and cluster capacity first.

---

# 29. Pod Priority Troubleshooting

Check the Pod:

```bash
kubectl get pod <pod-name> -n <namespace> -o yaml
```

Look for:

```yaml
priorityClassName:
```

Check:

```bash
kubectl get priorityclass
```

Inspect Pod events:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Scheduling events may indicate whether preemption was considered.

---

# 30. Multiple Scheduling Constraints

A Pod may have several constraints simultaneously:

```text
Resources
+
Node Selector
+
Node Affinity
+
Tolerations
+
Pod Affinity
+
Pod Anti-Affinity
+
Topology Constraints
+
Volume Topology
```

For example:

```text
Pod
 ↓
Needs 4 CPU
 ↓
Requires SSD node
 ↓
Requires zone=us-east-1a
 ↓
Does not tolerate database taint
 ↓
Requires anti-affinity
 ↓
Only one node remains
 ↓
Node has insufficient CPU
 ↓
Pod Pending
```

The scheduler evaluates the complete set of constraints.

---

# 31. Scheduling Troubleshooting Strategy

When a Pod is Pending, follow:

```text
Pod Pending
     ↓
Check Events
     ↓
Identify rejected nodes
     ↓
Check resource requirements
     ↓
Check nodeSelector
     ↓
Check nodeAffinity
     ↓
Check taints/tolerations
     ↓
Check pod affinity/anti-affinity
     ↓
Check topology constraints
     ↓
Check storage topology
     ↓
Check node schedulability
     ↓
Check Priority / Preemption
```

Start with the scheduler event message because it often identifies the failing constraint.

---

# 32. Scheduling vs Resource Usage

A critical distinction:

```text
Scheduling
```

primarily evaluates resource requests and node allocatable capacity.

It does not simply ask:

```text
"How much CPU is the node using right now?"
```

For example:

```text
Node:
    8 CPU capacity

Existing requests:
    7 CPU

Actual usage:
    3 CPU
```

A new Pod requesting:

```text
2 CPU
```

may still be unschedulable because scheduling considers the existing resource reservations/requests.

---

# 33. Node Conditions

Check node conditions:

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

A node that is not Ready or has relevant unhealthy conditions may not be suitable for scheduling.

---

# 34. Node Labels

List labels:

```bash
kubectl get nodes --show-labels
```

Inspect a specific node:

```bash
kubectl get node <node-name> --show-labels
```

Labels are used by:

* nodeSelector
* node affinity
* pod affinity
* pod anti-affinity
* topology rules

Incorrect labels can therefore cause scheduling failures.

---

# 35. Scheduling Failures Across Many Pods

If many unrelated Pods suddenly become Pending:

```text
Pod A → Pending
Pod B → Pending
Pod C → Pending
```

do not immediately investigate each Pod separately.

Look for a shared cause:

```text
Cluster capacity
Node availability
Taints
Scheduler
ResourceQuota
Storage
Cluster-wide constraints
```

The scope of the failure is an important diagnostic signal.

---

# 36. Scheduling Failures on One Node

If workloads fail only on one node:

```text
Node 1 → Healthy
Node 2 → Healthy
Node 3 → Problems
```

investigate Node 3.

Check:

```bash
kubectl describe node <node-name>
```

Look for:

* Taints
* Conditions
* Allocatable resources
* SchedulingDisabled
* Labels
* Events

A node-specific issue may explain why Pods are not being placed there.

---

# 37. Useful Scheduling Commands

### Check Pod

```bash
kubectl get pod <pod-name> -n <namespace>
```

### Describe Pod

```bash
kubectl describe pod <pod-name> -n <namespace>
```

### Inspect Pod YAML

```bash
kubectl get pod <pod-name> -n <namespace> -o yaml
```

### List Nodes

```bash
kubectl get nodes
```

### List Nodes with Labels

```bash
kubectl get nodes --show-labels
```

### Describe Node

```bash
kubectl describe node <node-name>
```

### List PriorityClasses

```bash
kubectl get priorityclass
```

### List ResourceQuotas

```bash
kubectl get resourcequota -A
```

### List Pods by Node

```bash
kubectl get pods -A -o wide
```

### Check Events

```bash
kubectl get events -A --sort-by=.lastTimestamp
```

### Check Taints

```bash
kubectl describe node <node-name>
```

---

# 38. Scheduling Troubleshooting Decision Flow

```text
Pod Pending
    ↓
Check Pod Events
    ↓
Why were nodes rejected?
    │
    ├── Insufficient CPU
    │       ↓
    │   Check requests
    │   Check node capacity
    │
    ├── Insufficient Memory
    │       ↓
    │   Check requests
    │   Check node capacity
    │
    ├── Untolerated Taint
    │       ↓
    │   Check node taints
    │   Check Pod tolerations
    │
    ├── Node Selector/Affinity
    │       ↓
    │   Check Pod rules
    │   Check node labels
    │
    ├── Pod Affinity/Anti-Affinity
    │       ↓
    │   Check existing Pods
    │   Check topology
    │
    ├── Volume/Topology
    │       ↓
    │   Check PV/PVC
    │   Check storage topology
    │
    └── Node Unschedulable
            ↓
        Check node state
```

---

# 39. Scheduling Troubleshooting Checklist

When investigating a Pending Pod:

* [ ] Check Pod status
* [ ] Check Pod events
* [ ] Identify scheduler rejection reason
* [ ] Check CPU requests
* [ ] Check memory requests
* [ ] Check node allocatable resources
* [ ] Check node availability
* [ ] Check node labels
* [ ] Check nodeSelector
* [ ] Check node affinity
* [ ] Check Pod affinity
* [ ] Check Pod anti-affinity
* [ ] Check node taints
* [ ] Check Pod tolerations
* [ ] Check topology spread constraints
* [ ] Check volume topology
* [ ] Check ResourceQuota
* [ ] Check PriorityClass
* [ ] Check preemption events
* [ ] Check whether nodes are cordoned
* [ ] Check node conditions
* [ ] Determine whether the problem affects one Pod or many Pods

---

# 40. Verification

After resolving a scheduling problem:

```text
Pod
 ↓
Scheduler
 ↓
Node Selected
 ↓
Pod Assigned
 ↓
Kubelet
 ↓
Container Created
 ↓
Pod Running
 ↓
Pod Ready
```

Check:

```bash
kubectl get pod <pod-name> -n <namespace> -o wide
```

Verify:

* Pod is no longer Pending
* Pod has been assigned to an expected node
* Containers start successfully
* Pod becomes Ready
* No repeated scheduling failures occur
* Resource usage remains reasonable

A Pod becoming `Running` is not the end of troubleshooting. Confirm that it becomes `Ready` and the application functions correctly.

---

# 41. Important Troubleshooting Principle

When a Pod is Pending, do not immediately increase cluster capacity.

First determine:

```text
Why was the Pod rejected?
```

The cause may be:

```text
Resource constraint
Taint
Affinity
Node selector
Topology
Storage
Quota
Unschedulable node
```

Increasing cluster capacity will not fix a Pod whose required node label is incorrect or whose affinity rule cannot be satisfied.

---

# 42. Kube-InsightAI Diagnostic Principle

Kube-InsightAI should reason about scheduling as a constraint-solving problem.

```text
                Pod
                 │
       ┌─────────┼──────────┐
       ↓         ↓          ↓
   Resources   Placement   Storage
       │         │          │
       ↓         ↓          ↓
    CPU/RAM   Labels      Topology
              Affinity
              Taints
              Tolerations
                 │
                 ↓
              Scheduler
                 │
        ┌────────┴────────┐
        ↓                 ↓
   Suitable Node      No Suitable Node
        ↓                 ↓
     Schedule            Pending
```

When a user reports:

> "My Pod is stuck in Pending."

Kube-InsightAI should determine:

1. What scheduling event occurred?
2. Which nodes were considered?
3. Why were nodes rejected?
4. Does the Pod have sufficient resource requests?
5. Do eligible nodes have enough allocatable resources?
6. Does the Pod use a nodeSelector?
7. Does it have node affinity?
8. Are there node taints?
9. Does the Pod have matching tolerations?
10. Does Pod affinity or anti-affinity restrict placement?
11. Are topology constraints involved?
12. Is storage topology involved?
13. Is the node cordoned or otherwise unschedulable?
14. Is ResourceQuota involved?
15. Is Pod priority or preemption relevant?

Kube-InsightAI can later combine this RAG knowledge with live MCP information such as:

```text
kubectl describe pod
kubectl get nodes
kubectl describe node
kubectl get pods -A -o wide
kubectl get resourcequota
kubectl get priorityclass
kubectl get pv
kubectl get pvc
```

This allows the agent to move from:

```text
"Why can Kubernetes Pods remain Pending?"
```

to:

```text
"Why is this specific Pod Pending in my cluster?"
```

For example:

```text
User:
Why is payment-api-7d8f9c Pending?

Kube-InsightAI:
The Pod requests 8Gi memory, but the only nodes
matching its required zone and node affinity have
less than 8Gi allocatable memory.

Therefore the scheduler cannot find a suitable node.
```

That diagnosis requires both:

```text
RAG
+
Live MCP data
```

---

# 43. Summary

Kubernetes scheduling can be viewed as:

```text
Pod Requirements
      ↓
Scheduler
      ↓
Filter Nodes
      ↓
Score Nodes
      ↓
Select Node
      ↓
Bind Pod
```

The major causes of Pending Pods include:

* Insufficient CPU
* Insufficient memory
* Node selector mismatch
* Node affinity mismatch
* Pod affinity constraints
* Pod anti-affinity constraints
* Untolerated taints
* Unschedulable nodes
* Topology constraints
* Storage topology
* ResourceQuota
* Node conditions
* Priority and preemption

The most important diagnostic rule is:

> **When a Pod is Pending, start with the scheduler events and identify why nodes were rejected before changing the workload or cluster.**
