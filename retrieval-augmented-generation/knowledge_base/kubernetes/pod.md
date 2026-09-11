# Kubernetes Pod Troubleshooting SOP

## 1. Purpose

This SOP provides a systematic procedure for diagnosing and troubleshooting Kubernetes Pod issues.

It is intended to help identify the cause of common Pod failures and determine the appropriate troubleshooting steps.

---

## 2. What Is a Kubernetes Pod?

A Pod is the smallest deployable unit in Kubernetes.

A Pod can contain one or more containers that share:

* Network namespace
* IP address
* Storage volumes

In most applications, a Pod contains a single application container.

---

## 3. Common Pod States

Kubernetes commonly reports the following Pod phases:

| Phase     | Meaning                                                      |
| --------- | ------------------------------------------------------------ |
| Pending   | Pod has been accepted but has not started running            |
| Running   | Pod has been scheduled and at least one container is running |
| Succeeded | All containers completed successfully                        |
| Failed    | All containers terminated and at least one failed            |
| Unknown   | Pod state could not be determined                            |

> Note: `CrashLoopBackOff`, `ImagePullBackOff`, and `OOMKilled` are not Pod phases. They are commonly observed container status/reason indicators.

---

# 4. General Pod Troubleshooting Workflow

When a Pod is unhealthy, follow this sequence:

```text
1. Check Pod status
        ↓
2. Describe the Pod
        ↓
3. Check container logs
        ↓
4. Check previous container logs
        ↓
5. Check Pod events
        ↓
6. Inspect configuration
        ↓
7. Check node resources
        ↓
8. Identify root cause
        ↓
9. Apply remediation
        ↓
10. Verify Pod health
```

---

# 5. Step 1 — Check Pod Status

First determine the current state of the Pod.

```bash
kubectl get pod <pod-name>
```

For all Pods in the current namespace:

```bash
kubectl get pods
```

For Pods across all namespaces:

```bash
kubectl get pods -A
```

Example:

```text
NAME           READY   STATUS             RESTARTS   AGE
payment-api    0/1     CrashLoopBackOff   5          3m
```

Important fields:

* `READY` — Number of ready containers
* `STATUS` — Current displayed Pod/container status
* `RESTARTS` — Number of container restarts
* `AGE` — Pod age

---

# 6. Step 2 — Describe the Pod

Use `kubectl describe` to inspect detailed Pod information.

```bash
kubectl describe pod <pod-name>
```

Pay particular attention to:

* Conditions
* Container state
* Container last state
* Restart count
* Image
* Environment configuration
* Volume mounts
* Node assignment
* Events

The `Events` section is especially useful for identifying scheduling, image, mount, and other runtime problems.

---

# 7. Step 3 — Check Container Logs

Check the current container logs:

```bash
kubectl logs <pod-name>
```

For a Pod containing multiple containers:

```bash
kubectl logs <pod-name> -c <container-name>
```

Logs can reveal:

* Application startup failures
* Configuration errors
* Connection failures
* Authentication failures
* Application crashes
* Invalid arguments
* Dependency failures

---

# 8. Step 4 — Check Previous Container Logs

If the container has restarted, inspect logs from the previous container instance:

```bash
kubectl logs <pod-name> --previous
```

For a specific container:

```bash
kubectl logs <pod-name> -c <container-name> --previous
```

This is particularly useful for `CrashLoopBackOff` situations where the current container may have little or no useful output.

---

# 9. Step 5 — Check Pod Events

Pod events can provide information about what Kubernetes is doing with the Pod.

```bash
kubectl describe pod <pod-name>
```

Look at the `Events` section.

You can also query events directly:

```bash
kubectl get events --sort-by=.lastTimestamp
```

Events can help identify problems such as:

* Failed scheduling
* Image pull failures
* Volume mount failures
* Failed probes
* Container creation failures
* Permission-related issues

---

# 10. CrashLoopBackOff

## Symptom

The Pod repeatedly starts a container and the container repeatedly exits.

Example:

```text
NAME          READY   STATUS             RESTARTS
payment-api   0/1     CrashLoopBackOff   7
```

## Common Causes

* Application startup failure
* Incorrect command or arguments
* Missing environment variables
* Invalid configuration
* Dependency unavailable
* Application exits immediately
* Permission problems
* Failed startup configuration

## Investigation

Check the Pod:

```bash
kubectl describe pod <pod-name>
```

Check current logs:

```bash
kubectl logs <pod-name>
```

Check logs from the previous container:

```bash
kubectl logs <pod-name> --previous
```

Check events:

```bash
kubectl describe pod <pod-name>
```

## Remediation

The remediation depends on the actual error.

Do not automatically restart the Pod without identifying the underlying cause.

---

# 11. ImagePullBackOff / ErrImagePull

## Symptom

Kubernetes cannot obtain the specified container image.

Example:

```text
STATUS
ImagePullBackOff
```

## Common Causes

* Incorrect image name
* Incorrect image tag
* Image does not exist
* Private registry authentication failure
* Registry connectivity problem
* Registry rate limiting

## Investigation

Check the Pod events:

```bash
kubectl describe pod <pod-name>
```

Inspect the image configuration:

```bash
kubectl get pod <pod-name> -o yaml
```

Verify:

* Image name
* Image tag
* Registry
* Image pull credentials

## Remediation

Correct the image reference or registry authentication configuration.

---

# 12. Pending

## Symptom

The Pod remains in:

```text
Pending
```

## Common Causes

* Insufficient CPU
* Insufficient memory
* Node selector mismatch
* Node affinity rules
* Taints without matching tolerations
* PersistentVolume/PersistentVolumeClaim constraints
* No suitable node available

## Investigation

Describe the Pod:

```bash
kubectl describe pod <pod-name>
```

Check nodes:

```bash
kubectl get nodes
```

Check node details:

```bash
kubectl describe nodes
```

Pay particular attention to scheduler-related events.

---

# 13. OOMKilled

## Symptom

A container terminates because it exceeded its memory limit.

Check the container's previous state:

```bash
kubectl describe pod <pod-name>
```

Look for:

```text
Reason: OOMKilled
```

## Common Causes

* Application uses more memory than its configured limit
* Memory leak
* Incorrect memory limit
* Unexpected workload increase

## Investigation

Check configured resources:

```bash
kubectl get pod <pod-name> -o yaml
```

Look for:

```yaml
resources:
  requests:
    memory: ...
  limits:
    memory: ...
```

If metrics are available, inspect current resource consumption:

```bash
kubectl top pod <pod-name>
```

## Remediation

Depending on the root cause:

* Fix the application memory issue
* Adjust the memory limit
* Review workload behavior
* Investigate memory leaks

---

# 14. ContainerCreating

## Symptom

The Pod remains in:

```text
ContainerCreating
```

for an unexpectedly long period.

## Common Causes

* Volume mounting problems
* Image pulling
* CNI/network setup problems
* Secret or ConfigMap issues
* Container runtime problems

## Investigation

Start with:

```bash
kubectl describe pod <pod-name>
```

Review the `Events` section.

Check:

* Volumes
* Secrets
* ConfigMaps
* Image
* Node
* Network-related events

---

# 15. CreateContainerConfigError

## Symptom

The container cannot be created because its configuration is invalid or required configuration is unavailable.

## Common Causes

* Missing ConfigMap
* Missing Secret
* Incorrect environment variable reference
* Incorrect volume configuration

## Investigation

Describe the Pod:

```bash
kubectl describe pod <pod-name>
```

Check referenced resources:

```bash
kubectl get configmap
kubectl get secrets
```

Inspect the Pod specification:

```bash
kubectl get pod <pod-name> -o yaml
```

---

# 16. Failed Readiness Probe

## Symptom

The container is running but is not considered ready to receive traffic.

## Common Causes

* Application is not listening on the expected port
* Incorrect probe path
* Incorrect probe port
* Application startup takes longer than expected
* Application is unhealthy

## Investigation

Inspect the Pod:

```bash
kubectl describe pod <pod-name>
```

Review the configured readiness probe.

Check application logs:

```bash
kubectl logs <pod-name>
```

Verify the application is listening on the expected port and serving the expected endpoint.

---

# 17. Failed Liveness Probe

## Symptom

The container repeatedly restarts because its liveness probe fails.

## Common Causes

* Application is unhealthy
* Incorrect probe configuration
* Incorrect port
* Incorrect HTTP path
* Probe timeout too short
* Application startup takes longer than the configured initial delay

## Investigation

```bash
kubectl describe pod <pod-name>
```

Check:

* Probe configuration
* Probe failures in events
* Application logs
* Application health endpoint

---

# 18. Useful Pod Commands

### List Pods

```bash
kubectl get pods
```

### Get detailed Pod information

```bash
kubectl describe pod <pod-name>
```

### Get Pod YAML

```bash
kubectl get pod <pod-name> -o yaml
```

### View logs

```bash
kubectl logs <pod-name>
```

### View previous container logs

```bash
kubectl logs <pod-name> --previous
```

### View logs for a specific container

```bash
kubectl logs <pod-name> -c <container-name>
```

### View Pod events

```bash
kubectl get events --sort-by=.lastTimestamp
```

### Check resource usage

```bash
kubectl top pod <pod-name>
```

---

# 19. Troubleshooting Decision Flow

Use the following decision process:

```text
                 Pod Problem
                      │
                      ↓
              kubectl get pod
                      │
             ┌────────┴────────┐
             ↓                 ↓
          Pending?           Running?
             │                 │
             ↓                 ↓
      Check scheduling     Check readiness
      and resources             │
             │             ┌────┴─────┐
             │             ↓          ↓
             │          Ready?    Not Ready?
             │                        │
             │                        ↓
             │                  Check probes
             │
             └──────────┬─────────────┘
                        ↓
                Container failure?
                        │
                 ┌──────┴──────┐
                 ↓             ↓
              Yes             No
                 ↓             ↓
             Check logs     Check events
                 ↓
          Check --previous
                 ↓
          Identify root cause
                 ↓
              Remediate
                 ↓
             Verify health
```

---

# 20. Verification After Remediation

After applying a fix, verify the Pod.

```bash
kubectl get pod <pod-name>
```

Confirm:

* Pod reaches the expected state
* Containers are ready
* Restart count is no longer increasing
* Application logs are healthy
* Readiness probe succeeds
* Application is reachable

If appropriate, also verify the related Service or application functionality.

---

# 21. General Troubleshooting Principle

Do not assume the displayed Pod status is the root cause.

For example:

```text
CrashLoopBackOff
```

is an indication that a container is repeatedly restarting. It is not, by itself, the underlying application error.

Always investigate using:

```text
Pod Status
     +
Pod Description
     +
Container Logs
     +
Previous Logs
     +
Events
     +
Configuration
     +
Node/Resource Information
```

Then determine the root cause before applying remediation.
