# Kubernetes Pod Scenarios for Testing & Troubleshooting

This repository contains Kubernetes manifest definitions for testing and simulating common pod lifecycle states and failure scenarios using a minimal `busybox` base image. All resources are deployed isolated within the `testing-files` namespace.

---

## 📋 Overview of Scenarios

| Scenario | Pod Name | Expected Status | Description / Cause |
| :--- | :--- | :--- | :--- |
| **1. Healthy Baseline** | `scenario-1-healthy` | `Running` (`1/1 READY`) | Normal operating pod used as a comparison baseline. |
| **2. Image Failure** | `scenario-2-imagepullbackoff` | `ImagePullBackOff` | Deliberately uses a non-existent image tag (`busybox:nonexistent-tag-12345`). |
| **3. Process Crash** | `scenario-3-crashloopbackoff` | `CrashLoopBackOff` | Container process exits immediately with code `1`. |
| **4. Probe Failure** | `scenario-4-readiness-failure` | `Running` (`0/1 READY`) | Container runs `httpd`, but readiness probe queries a missing route (`/nonexistent-endpoint`), returning `404`. |
| **5. Scheduling Failure** | `scenario-5-unschedulable` | `Pending` | Pod defines a `nodeSelector` key/value that matches no nodes in the cluster. |

---

## 🚀 Deployment

Apply all scenarios to your cluster using `kubectl`:

```bash
kubectl apply -f manifests.yaml
```

To watch the status of the pods in real-time:

```bash
kubectl get pods -n testing-files -w
```

### Expected Output

```text
NAME                           READY   STATUS             RESTARTS   AGE
scenario-1-healthy             1/1     Running            0          30s
scenario-2-imagepullbackoff    0/1     ImagePullBackOff   0          30s
scenario-3-crashloopbackoff    0/1     CrashLoopBackOff   1 (10s ago) 30s
scenario-4-readiness-failure   0/1     Running            0          30s
scenario-5-unschedulable       0/1     Pending            0          30s
```

---

## 🔍 Diagnostic & Troubleshooting Commands

Use these standard `kubectl` commands to inspect and diagnose each simulated issue:

### 1. Inspect Scheduling & Event Errors
To see why `scenario-2` failed to pull the image or why `scenario-5` cannot be scheduled:

```bash
# Check image pull failure details
kubectl describe pod scenario-2-imagepullbackoff -n testing-files

# Check unschedulable node selector events
kubectl describe pod scenario-5-unschedulable -n testing-files
```

### 2. Inspect Probe Failures
To view readiness probe health check warnings:

```bash
kubectl describe pod scenario-4-readiness-failure -n testing-files
```
*Look under the **Events** section for `Readiness probe failed: HTTP probe failed with statuscode: 404`.*

### 3. Check Application Logs & Exit Codes
To diagnose why `scenario-3` keeps crashing:

```bash
kubectl logs scenario-3-crashloopbackoff -n testing-files
```

---

## 🧹 Cleanup

To delete all test pods and the surrounding namespace:

```bash
kubectl delete namespace testing-files
```