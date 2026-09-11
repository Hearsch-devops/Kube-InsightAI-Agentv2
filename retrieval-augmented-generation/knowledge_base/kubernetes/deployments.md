# Kubernetes Deployment Troubleshooting SOP

## 1. Purpose

This SOP provides a systematic procedure for diagnosing and troubleshooting Kubernetes Deployment issues.

It is intended to help identify problems with:

* Deployment availability
* Replica counts
* Rolling updates
* Failed rollouts
* Stuck rollouts
* Rollbacks
* ReplicaSets
* Pod creation
* Application version changes

---

# 2. What Is a Kubernetes Deployment?

A Deployment manages a set of replicated Pods and provides declarative updates for applications.

A Deployment typically manages a ReplicaSet, which in turn manages the Pods.

The relationship is:

```text
Deployment
     ↓
ReplicaSet
     ↓
Pods
     ↓
Containers
```

A Deployment can be used to:

* Maintain a desired number of Pods
* Perform rolling updates
* Roll back to a previous revision
* Scale an application
* Manage application versions

---

# 3. Important Deployment Concepts

## Desired Replicas

The number of Pods the Deployment is configured to maintain.

Example:

```yaml
replicas: 3
```

The Deployment attempts to maintain three Pods.

## Available Replicas

The number of Pods currently available to serve the application.

## Ready Replicas

The number of Pods that have passed their readiness requirements.

## Updated Replicas

The number of replicas running the current Deployment revision.

---

# 4. General Deployment Troubleshooting Workflow

When a Deployment is unhealthy, follow this sequence:

```text
1. Check Deployment status
        ↓
2. Describe Deployment
        ↓
3. Check rollout status
        ↓
4. Check ReplicaSets
        ↓
5. Check Pods
        ↓
6. Check Pod logs
        ↓
7. Check events
        ↓
8. Identify root cause
        ↓
9. Remediate
        ↓
10. Verify rollout
```

---

# 5. Step 1 — Check Deployment Status

List Deployments:

```bash
kubectl get deployments
```

Check a specific Deployment:

```bash
kubectl get deployment <deployment-name>
```

Example:

```text
NAME          READY   UP-TO-DATE   AVAILABLE   AGE
payment-api   2/3     3            2           10m
```

Important fields:

* `READY` — Ready replicas / desired replicas
* `UP-TO-DATE` — Replicas using the current Deployment revision
* `AVAILABLE` — Available replicas
* `AGE` — Deployment age

---

# 6. Step 2 — Describe the Deployment

Use:

```bash
kubectl describe deployment <deployment-name>
```

Inspect:

* Desired replicas
* Current replicas
* Updated replicas
* Available replicas
* Conditions
* Strategy
* Selector
* Pod template
* Events

The Events section can provide useful information about Deployment and ReplicaSet activity.

---

# 7. Step 3 — Check Rollout Status

Check whether a rollout is progressing:

```bash
kubectl rollout status deployment/<deployment-name>
```

A successful rollout should eventually report that the Deployment has successfully rolled out.

If the command does not complete or reports a failure, investigate the underlying Pods, ReplicaSet, and events.

---

# 8. Step 4 — Check ReplicaSets

A Deployment manages ReplicaSets.

List ReplicaSets:

```bash
kubectl get replicasets
```

For a specific application:

```bash
kubectl get rs
```

ReplicaSets help determine which Deployment revision is currently creating Pods.

A useful investigation pattern is:

```text
Deployment
     ↓
ReplicaSet
     ↓
Pods
```

If the Deployment looks correct but the expected Pods are not available, inspect the associated ReplicaSet.

---

# 9. Step 5 — Check Pods Managed by the Deployment

List Pods:

```bash
kubectl get pods
```

Check Pods with labels:

```bash
kubectl get pods -l app=<application-label>
```

Inspect an individual Pod:

```bash
kubectl describe pod <pod-name>
```

Check logs:

```bash
kubectl logs <pod-name>
```

If the Pod is restarting:

```bash
kubectl logs <pod-name> --previous
```

Deployment problems frequently originate from the Pods themselves.

---

# 10. Deployment Has Fewer Available Replicas

## Symptom

Example:

```text
READY   UP-TO-DATE   AVAILABLE
2/3     3            2
```

The Deployment expects three replicas but only two are available.

## Common Causes

* One or more Pods are failing
* Readiness probe failures
* Container startup failures
* Insufficient cluster resources
* Scheduling problems
* Image pull failures
* Configuration errors
* Application crashes

## Investigation

Check:

```bash
kubectl get deployment <deployment-name>
```

Then:

```bash
kubectl get pods
```

Describe unhealthy Pods:

```bash
kubectl describe pod <pod-name>
```

Check logs:

```bash
kubectl logs <pod-name>
```

Check Deployment events:

```bash
kubectl describe deployment <deployment-name>
```

---

# 11. Deployment Rollout Is Stuck

## Symptom

A Deployment update does not complete.

Check:

```bash
kubectl rollout status deployment/<deployment-name>
```

## Common Causes

* New Pods fail to start
* Readiness probe failures
* ImagePullBackOff
* CrashLoopBackOff
* Insufficient resources
* Scheduling constraints
* Incorrect application configuration
* Deployment strategy constraints

## Investigation

Check:

```bash
kubectl get deployment <deployment-name>
```

Then:

```bash
kubectl get rs
```

Then:

```bash
kubectl get pods
```

Inspect unhealthy Pods:

```bash
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

Review events:

```bash
kubectl describe deployment <deployment-name>
```

---

# 12. Deployment Update Created Unhealthy Pods

## Symptom

A new application version is deployed, but the new Pods are failing.

Example:

```text
Old Pods:
3 Running

New Pods:
0 Running
3 CrashLoopBackOff
```

## Common Causes

* Application bug
* Incorrect container image
* Incorrect image tag
* Configuration change
* Missing Secret or ConfigMap
* Environment variable problem
* Failed dependency
* Incorrect startup command

## Investigation

Check the Deployment image:

```bash
kubectl get deployment <deployment-name> -o yaml
```

Check the new Pods:

```bash
kubectl get pods
```

Check logs:

```bash
kubectl logs <pod-name>
```

Check previous logs if necessary:

```bash
kubectl logs <pod-name> --previous
```

---

# 13. Image Update Troubleshooting

A Deployment can be updated to use a new container image.

Example:

```bash
kubectl set image deployment/<deployment-name> \
  <container-name>=<image>:<tag>
```

Check rollout:

```bash
kubectl rollout status deployment/<deployment-name>
```

Check the Deployment:

```bash
kubectl get deployment <deployment-name>
```

If the rollout fails, inspect the resulting Pods and events.

Common image-related problems include:

* Incorrect image name
* Incorrect tag
* Image does not exist
* Private registry authentication failure
* Registry connectivity problems

---

# 14. Rolling Update

Deployments commonly use the `RollingUpdate` strategy.

A rolling update gradually replaces old Pods with new Pods.

Conceptually:

```text
Before:

Old Old Old
 ↓
3 running Pods


During rollout:

Old Old New
 ↓
Old New New
 ↓
New New New


After:

New New New
```

This allows an application to be updated without immediately terminating all existing Pods.

---

# 15. Check Deployment Strategy

Inspect the Deployment:

```bash
kubectl get deployment <deployment-name> -o yaml
```

Look for:

```yaml
strategy:
  type: RollingUpdate
```

Rolling update behavior can also be influenced by:

* `maxUnavailable`
* `maxSurge`

These settings control how many Pods can be unavailable and how many additional Pods can temporarily be created during an update.

---

# 16. Rollback a Deployment

If a rollout introduces a problem, inspect rollout history:

```bash
kubectl rollout history deployment/<deployment-name>
```

View a specific revision:

```bash
kubectl rollout history deployment/<deployment-name> --revision=<revision>
```

Rollback to the previous revision:

```bash
kubectl rollout undo deployment/<deployment-name>
```

Then verify:

```bash
kubectl rollout status deployment/<deployment-name>
```

And:

```bash
kubectl get pods
```

A rollback should be followed by verification that the application is healthy.

---

# 17. Check Deployment Rollout History

Use:

```bash
kubectl rollout history deployment/<deployment-name>
```

This can help identify:

* Previous revisions
* Recent application changes
* Deployment updates

For detailed investigation:

```bash
kubectl rollout history deployment/<deployment-name> \
  --revision=<revision>
```

---

# 18. Scaling a Deployment

Check current configuration:

```bash
kubectl get deployment <deployment-name>
```

Scale the Deployment:

```bash
kubectl scale deployment <deployment-name> --replicas=<number>
```

Example:

```bash
kubectl scale deployment payment-api --replicas=5
```

Verify:

```bash
kubectl get deployment payment-api
kubectl get pods
```

Scaling problems can occur if the cluster does not have sufficient resources or if Pods cannot be scheduled.

---

# 19. Deployment Selector Problems

A Deployment uses a selector to identify the Pods it manages.

Example:

```yaml
selector:
  matchLabels:
    app: payment-api
```

The Pod template should contain matching labels:

```yaml
template:
  metadata:
    labels:
      app: payment-api
```

The selector and Pod labels must be configured consistently.

When troubleshooting unexpected Deployment behavior, inspect:

```bash
kubectl get deployment <deployment-name> -o yaml
```

Pay particular attention to:

* `spec.selector`
* `spec.template.metadata.labels`

---

# 20. Deployment Paused

A Deployment can be paused.

Check Deployment state:

```bash
kubectl get deployment <deployment-name>
```

Resume a paused Deployment:

```bash
kubectl rollout resume deployment/<deployment-name>
```

After resuming, verify rollout progress:

```bash
kubectl rollout status deployment/<deployment-name>
```

---

# 21. Deployment Revision Does Not Become Available

## Symptom

The Deployment has updated replicas, but the new revision does not become available.

## Common Causes

* Readiness probe failure
* Application startup failure
* Container crash
* Configuration error
* Insufficient resources
* Scheduling problems

## Investigation

Start with:

```bash
kubectl get deployment <deployment-name>
```

Then:

```bash
kubectl rollout status deployment/<deployment-name>
```

Inspect Pods:

```bash
kubectl get pods
```

Describe failing Pods:

```bash
kubectl describe pod <pod-name>
```

Check logs:

```bash
kubectl logs <pod-name>
```

---

# 22. Useful Deployment Commands

### List Deployments

```bash
kubectl get deployments
```

### Describe Deployment

```bash
kubectl describe deployment <deployment-name>
```

### Get Deployment YAML

```bash
kubectl get deployment <deployment-name> -o yaml
```

### Check rollout status

```bash
kubectl rollout status deployment/<deployment-name>
```

### View rollout history

```bash
kubectl rollout history deployment/<deployment-name>
```

### Roll back

```bash
kubectl rollout undo deployment/<deployment-name>
```

### Pause rollout

```bash
kubectl rollout pause deployment/<deployment-name>
```

### Resume rollout

```bash
kubectl rollout resume deployment/<deployment-name>
```

### List ReplicaSets

```bash
kubectl get rs
```

### List Pods

```bash
kubectl get pods
```

### Scale Deployment

```bash
kubectl scale deployment <deployment-name> --replicas=<number>
```

### Update container image

```bash
kubectl set image deployment/<deployment-name> \
  <container-name>=<image>:<tag>
```

---

# 23. Deployment Troubleshooting Decision Flow

```text
                  Deployment Problem
                          │
                          ↓
                kubectl get deployment
                          │
             ┌────────────┴────────────┐
             ↓                         ↓
       Rollout healthy?            Rollout stuck?
             │                         │
             │                         ↓
             │                 Check ReplicaSet
             │                         ↓
             │                    Check Pods
             │                         ↓
             │               ┌─────────┴─────────┐
             │               ↓                   ↓
             │          Pods failing?        Pods Pending?
             │               │                   │
             │               ↓                   ↓
             │          Check logs          Check scheduling
             │          Check events        Check resources
             │               │
             │               ↓
             │         Identify cause
             │               │
             └───────────────┤
                             ↓
                         Remediate
                             ↓
                    Check rollout status
                             ↓
                       Verify replicas
```

---

# 24. Deployment Troubleshooting Checklist

When troubleshooting a Deployment, check:

```text
☐ Deployment status
☐ Desired replicas
☐ Updated replicas
☐ Available replicas
☐ Deployment conditions
☐ Rollout status
☐ ReplicaSets
☐ Pod status
☐ Pod events
☐ Container logs
☐ Previous container logs
☐ Image configuration
☐ Environment variables
☐ ConfigMaps
☐ Secrets
☐ Readiness probes
☐ Liveness probes
☐ Resource requests/limits
☐ Scheduling constraints
☐ Deployment strategy
☐ Rollout history
```

---

# 25. Verification After Remediation

After fixing the Deployment:

```bash
kubectl rollout status deployment/<deployment-name>
```

Then:

```bash
kubectl get deployment <deployment-name>
```

Verify:

* Desired replicas are available
* Updated replicas match the expected revision
* Available replicas are healthy
* Pods are Ready
* Pod restart counts are stable
* Application logs are healthy
* Readiness probes succeed

If the Deployment was rolled back, verify that the previous revision is healthy.

---

# 26. Important Troubleshooting Principle

A Deployment is a higher-level controller.

When a Deployment is unhealthy, do not investigate only the Deployment object.

Follow the controller hierarchy:

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

A Deployment may report fewer available replicas because a Pod is failing.

A Pod may be failing because a container is crashing.

A container may be crashing because the application has a configuration or runtime error.

Therefore, troubleshoot from the Deployment down to the actual failure.

---

# 27. Kube-InsightAI Diagnostic Principle

When Kube-InsightAI receives a Deployment-related question, it should correlate information from multiple levels:

```text
Deployment
     +
ReplicaSet
     +
Pod
     +
Container
     +
Logs
     +
Events
     +
Configuration
     ↓
Root Cause
```

The RAG knowledge base provides the documented troubleshooting procedures.

Live Kubernetes information can later be retrieved through MCP.

The agent can then combine the documented procedure with the current cluster state to produce a diagnosis and recommended next steps.
