# Kubernetes Storage Troubleshooting SOP

## 1. Purpose

This document provides a systematic procedure for troubleshooting Kubernetes storage problems involving:

* PersistentVolumes (PV)
* PersistentVolumeClaims (PVC)
* StorageClasses
* Dynamic volume provisioning
* Volume mounts
* Persistent storage used by Pods
* CSI drivers
* Common storage-related Pod failures

The goal is to identify the root cause of storage failures and restore reliable access to application data.

---

# 2. Kubernetes Storage Overview

Kubernetes separates storage consumption from storage implementation.

The common relationship is:

```text
Pod
 ↓
PersistentVolumeClaim (PVC)
 ↓
PersistentVolume (PV)
 ↓
Storage Backend
```

For dynamically provisioned storage:

```text
Pod
 ↓
PVC
 ↓
StorageClass
 ↓
CSI Driver
 ↓
Storage Backend
 ↓
PV
```

A Pod normally requests storage through a PVC rather than directly managing the underlying storage system.

---

# 3. Important Storage Resources

## 3.1 PersistentVolume (PV)

A PersistentVolume is a cluster-level storage resource.

It represents storage that can be consumed by workloads.

Example:

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: app-pv
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
```

---

## 3.2 PersistentVolumeClaim (PVC)

A PersistentVolumeClaim is a request for storage made by a workload.

Example:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

A Pod can mount the PVC:

```yaml
volumes:
  - name: data
    persistentVolumeClaim:
      claimName: app-data
```

---

## 3.3 StorageClass

A StorageClass defines how storage should be dynamically provisioned.

Example:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-storage
provisioner: example.com/csi
```

When a PVC references a StorageClass, Kubernetes can request storage dynamically through the configured provisioner.

---

## 3.4 CSI Driver

CSI stands for Container Storage Interface.

CSI drivers allow Kubernetes to communicate with external storage systems.

Examples include storage systems provided by:

* Cloud providers
* SAN/NAS systems
* Distributed storage platforms
* Local storage implementations

A CSI failure can prevent volumes from being provisioned, attached, mounted, or used.

---

# 4. General Storage Troubleshooting Workflow

When a Pod cannot use its storage, follow this order:

```text
Pod
 ↓
Check Pod Events
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

Do not immediately assume that the application is responsible for the failure.

---

# 5. Check the Pod

Start with the affected Pod.

```bash
kubectl get pod <pod-name> -n <namespace>
```

Then inspect it:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Look at:

```text
Volumes
Mounts
Events
```

Storage-related errors often appear in Pod events.

Useful command:

```bash
kubectl get events -n <namespace> --sort-by=.lastTimestamp
```

---

# 6. Check the PersistentVolumeClaim

List PVCs:

```bash
kubectl get pvc -n <namespace>
```

Example:

```text
NAME       STATUS   VOLUME      CAPACITY   ACCESS MODES
app-data   Bound    pvc-1234    10Gi       RWO
```

A healthy PVC normally has:

```text
STATUS: Bound
```

Inspect the PVC:

```bash
kubectl describe pvc app-data -n <namespace>
```

Check:

* Status
* Requested storage
* Access mode
* StorageClass
* Bound PV
* Events

---

# 7. PVC Stuck in Pending

One of the most common storage problems is:

```text
PVC STATUS: Pending
```

A Pending PVC means Kubernetes has not successfully associated it with usable storage.

Possible causes include:

* No matching PV exists
* StorageClass is missing
* Incorrect StorageClass
* Dynamic provisioning failed
* CSI driver problem
* Requested capacity is unavailable
* Requested access mode is unsupported
* Volume topology constraints
* Storage backend failure

Check:

```bash
kubectl describe pvc <pvc-name> -n <namespace>
```

Look at the Events section.

---

# 8. Check the StorageClass

List StorageClasses:

```bash
kubectl get storageclass
```

Inspect a StorageClass:

```bash
kubectl describe storageclass <storage-class>
```

Check:

* Provisioner
* Reclaim policy
* Volume binding mode
* Allowed topology
* Parameters

Verify that the PVC references the expected StorageClass:

```bash
kubectl get pvc <pvc-name> -n <namespace> -o yaml
```

Look for:

```yaml
spec:
  storageClassName: fast-storage
```

A typo or incorrect StorageClass name can prevent dynamic provisioning.

---

# 9. Check the PersistentVolume

List PVs:

```bash
kubectl get pv
```

Inspect a PV:

```bash
kubectl describe pv <pv-name>
```

Check:

* Capacity
* Access modes
* StorageClass
* Status
* Claim
* Reclaim policy
* Node affinity
* Events

Common PV states include:

```text
Available
Bound
Released
Failed
```

---

# 10. PV and PVC Binding Problems

A PVC and PV must satisfy compatible requirements.

Important matching properties include:

* Storage capacity
* Access modes
* StorageClass
* Volume selectors
* Topology constraints

For example, a PVC requesting:

```text
20Gi
```

cannot normally bind to a PV offering only:

```text
10Gi
```

Check both resources:

```bash
kubectl get pvc <pvc-name> -n <namespace> -o yaml
```

```bash
kubectl get pv <pv-name> -o yaml
```

Compare their specifications.

---

# 11. PVC Bound but Pod Cannot Start

A PVC being `Bound` does not guarantee that a Pod can successfully use the volume.

The next stages are:

```text
PVC Bound
 ↓
Volume Attach
 ↓
Volume Mount
 ↓
Filesystem Access
 ↓
Application Access
```

If the Pod is stuck in:

```text
ContainerCreating
```

inspect:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Look for errors such as:

```text
FailedAttachVolume
FailedMount
MountVolume.SetUp failed
Unable to attach or mount volumes
```

---

# 12. FailedAttachVolume

Example:

```text
FailedAttachVolume
```

This generally indicates a problem attaching the storage volume to the node.

Possible causes:

* CSI controller problem
* Storage backend unavailable
* Volume already attached elsewhere
* Node problem
* Cloud-provider storage issue
* Access mode limitation
* Volume attachment timeout

Check Pod events:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Check volume attachments:

```bash
kubectl get volumeattachment
```

Inspect:

```bash
kubectl describe volumeattachment <name>
```

---

# 13. FailedMount

Example:

```text
FailedMount
```

This means Kubernetes was unable to mount the volume into the Pod.

Possible causes include:

* Volume attachment failure
* Incorrect filesystem
* Mount configuration problem
* CSI driver failure
* Permission issue
* Node problem
* Corrupted filesystem
* Storage backend unavailable

Start with:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Then inspect the CSI components if required.

---

# 14. CSI Driver Troubleshooting

If storage operations repeatedly fail, investigate the CSI driver.

List CSI drivers:

```bash
kubectl get csidrivers
```

Depending on the platform, CSI components may run in a dedicated namespace.

Check Pods belonging to the storage driver:

```bash
kubectl get pods -A
```

Then inspect relevant CSI controller or node Pods.

Check their logs:

```bash
kubectl logs <csi-pod> -n <namespace>
```

The CSI driver is especially important when:

```text
PVC → PV provisioning
PV → Volume attachment
Volume → Mount
```

fails.

---

# 15. Access Modes

Kubernetes storage can support different access modes depending on the storage implementation.

Common modes include:

```text
ReadWriteOnce (RWO)
ReadOnlyMany (ROX)
ReadWriteMany (RWX)
```

The actual capabilities depend on the storage provider.

For example:

```text
ReadWriteOnce
```

generally means the volume can be mounted read-write by a single node.

A workload expecting simultaneous read-write access from multiple nodes may require storage that supports:

```text
ReadWriteMany
```

Do not assume every storage backend supports every access mode.

---

# 16. ReadWriteOnce Problems

A common scenario:

```text
Pod A → Node 1 → Volume
Pod B → Node 2 → Same Volume
```

If the volume only supports a single-node read-write attachment, Pod B may fail to attach or mount it.

Investigate:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

and:

```bash
kubectl get volumeattachment
```

Verify that the requested access mode matches the storage backend capabilities.

---

# 17. Volume Mount Path Problems

A volume can exist and be mounted successfully but still be mounted at the wrong location.

Inspect the Pod:

```bash
kubectl get pod <pod-name> -n <namespace> -o yaml
```

Check:

```yaml
volumes:
```

and:

```yaml
volumeMounts:
```

Example:

```yaml
volumes:
  - name: data
    persistentVolumeClaim:
      claimName: app-data

containers:
  - name: app
    volumeMounts:
      - name: data
        mountPath: /var/lib/app
```

Verify:

```text
volume name
      ↓
PVC
      ↓
volumeMount name
      ↓
mountPath
```

The names must match correctly.

---

# 18. Storage Works but Application Cannot Write

Sometimes the volume mounts successfully but the application receives:

```text
Permission denied
```

Possible causes:

* Filesystem ownership
* File permissions
* Container user
* Security context
* Storage backend permissions
* Read-only filesystem

Inspect the Pod security context:

```bash
kubectl get pod <pod-name> -n <namespace> -o yaml
```

Look for:

```yaml
securityContext:
```

For example:

```yaml
securityContext:
  runAsUser: 1000
  runAsGroup: 1000
```

Check the mounted directory from inside the container when possible:

```bash
kubectl exec -it <pod-name> -n <namespace> -- ls -la /var/lib/app
```

Then test write access if appropriate.

---

# 19. Read-Only Filesystem

An application may fail because the mounted storage is read-only.

Check the Pod configuration:

```bash
kubectl get pod <pod-name> -n <namespace> -o yaml
```

Look for:

```yaml
readOnly: true
```

Also inspect application logs:

```bash
kubectl logs <pod-name> -n <namespace>
```

Typical application errors may include:

```text
Read-only file system
Permission denied
Cannot write file
```

Determine whether the read-only behavior comes from:

* Pod configuration
* Storage backend
* Filesystem
* Mount configuration

---

# 20. Storage Capacity Problems

Applications can fail when a filesystem becomes full.

Check from inside the container:

```bash
kubectl exec -it <pod-name> -n <namespace> -- df -h
```

Check filesystem usage:

```bash
kubectl exec -it <pod-name> -n <namespace> -- df -h /var/lib/app
```

If supported by the environment:

```bash
kubectl exec -it <pod-name> -n <namespace> -- du -sh /var/lib/app/*
```

A full filesystem can produce symptoms such as:

```text
No space left on device
```

The Kubernetes resource may still show as `Bound` even though the application has exhausted available filesystem capacity.

---

# 21. Volume Expansion

Some storage systems support expanding PVC capacity.

Check the PVC:

```bash
kubectl get pvc <pvc-name> -n <namespace>
```

Inspect the StorageClass:

```bash
kubectl describe storageclass <storage-class>
```

Look for expansion support:

```text
allowVolumeExpansion
```

Do not assume that changing the PVC size automatically means the application filesystem has already expanded. The storage provider and filesystem must support the required expansion process.

---

# 22. Storage and Node Scheduling

Storage can affect where a Pod is able to run.

Possible constraints include:

* Volume topology
* Node affinity
* Availability zones
* Storage backend location
* CSI topology requirements

If a Pod remains:

```text
Pending
```

and storage is involved, inspect:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Pay particular attention to:

```text
Events
```

and scheduling messages.

Also inspect the PV:

```bash
kubectl describe pv <pv-name>
```

Look for:

```text
Node Affinity
```

---

# 23. Stateful Applications

Stateful applications commonly depend on persistent storage.

Examples include:

* Databases
* Message queues
* Stateful services
* Persistent application data

For StatefulSets, inspect:

```bash
kubectl get statefulset -n <namespace>
```

and:

```bash
kubectl get pvc -n <namespace>
```

A StatefulSet may create individual PVCs for its Pods.

Example relationship:

```text
StatefulSet
    ↓
Pod
    ↓
PVC
    ↓
PV
    ↓
Storage Backend
```

A storage failure can therefore prevent a StatefulSet Pod from becoming Ready.

---

# 24. Reclaim Policies

PV reclaim policies determine what happens to storage after a PVC is deleted.

Common policies include:

```text
Retain
Delete
```

`Retain` generally preserves the underlying storage resource for manual recovery or cleanup.

`Delete` can allow the storage resource to be deleted when the associated claim is deleted, depending on the storage implementation.

Be extremely careful when deleting storage resources because data loss may be irreversible.

---

# 25. Data Loss Warning

Never delete a PV, PVC, or underlying storage resource simply because it is stuck.

Before destructive actions, determine:

```text
Is the data required?
Is there a backup?
What is the reclaim policy?
Where is the actual data stored?
Can the volume be recovered?
```

Storage troubleshooting must prioritize data preservation.

---

# 26. Useful Storage Commands

### List PVCs

```bash
kubectl get pvc -A
```

### Describe PVC

```bash
kubectl describe pvc <pvc-name> -n <namespace>
```

### List PVs

```bash
kubectl get pv
```

### Describe PV

```bash
kubectl describe pv <pv-name>
```

### List StorageClasses

```bash
kubectl get storageclass
```

### Describe StorageClass

```bash
kubectl describe storageclass <storage-class>
```

### List CSI drivers

```bash
kubectl get csidrivers
```

### List VolumeAttachments

```bash
kubectl get volumeattachment
```

### Describe VolumeAttachment

```bash
kubectl describe volumeattachment <name>
```

### Check Pod events

```bash
kubectl describe pod <pod-name> -n <namespace>
```

### Check filesystem usage

```bash
kubectl exec -it <pod-name> -n <namespace> -- df -h
```

### Check mounted files

```bash
kubectl exec -it <pod-name> -n <namespace> -- mount
```

---

# 27. Storage Troubleshooting Decision Flow

```text
Pod has storage problem
        ↓
Is PVC Bound?
   ┌────┴────┐
   NO        YES
   ↓          ↓
Check PVC   Can Pod attach volume?
events       ↓
   ↓      ┌──┴──┐
Check     NO    YES
Storage   ↓      ↓
Class     Check   Can volume mount?
PV        CSI     ↓
          driver ┌┴──┐
                 NO  YES
                 ↓    ↓
              Check  Can application
              mount  read/write?
              errors   ↓
                    ┌──┴──┐
                   NO    YES
                   ↓      ↓
                Check   Storage likely
                perms   healthy
                /FS
```

---

# 28. Storage Troubleshooting Checklist

When investigating Kubernetes storage:

* [ ] Identify the affected Pod
* [ ] Check Pod status
* [ ] Check Pod events
* [ ] Identify the PVC
* [ ] Check PVC status
* [ ] Check PVC events
* [ ] Identify the bound PV
* [ ] Check PV status
* [ ] Verify StorageClass
* [ ] Verify requested capacity
* [ ] Verify access modes
* [ ] Check CSI driver
* [ ] Check VolumeAttachment when applicable
* [ ] Check volume mount errors
* [ ] Check mount paths
* [ ] Check filesystem permissions
* [ ] Check filesystem capacity
* [ ] Check node/topology constraints
* [ ] Check application logs
* [ ] Verify data safety before destructive operations

---

# 29. Verification

After resolving the issue, verify the complete storage path:

```text
PVC
 ↓
PV
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

```bash
kubectl get pv
```

```bash
kubectl get pod <pod-name> -n <namespace>
```

Then verify that the application can actually read and write the expected data.

A `Bound` PVC alone is not sufficient verification.

---

# 30. Important Troubleshooting Principle

For Kubernetes storage problems, do not stop at:

```text
PVC = Bound
```

A healthy storage path requires:

```text
PVC
 ↓
PV
 ↓
Attach
 ↓
Mount
 ↓
Filesystem
 ↓
Application
```

The failure can occur at any stage.

Always identify the **first failed stage** rather than focusing only on the final application error.

---

# 31. Kube-InsightAI Diagnostic Principle

Kube-InsightAI should reason about storage failures as a dependency chain:

```text
Application
     ↓
Filesystem
     ↓
Volume Mount
     ↓
Volume Attachment
     ↓
PV
     ↓
PVC
     ↓
StorageClass
     ↓
CSI Driver
     ↓
Storage Backend
```

When a user reports:

> "My application cannot write to its disk."

Kube-InsightAI should not immediately conclude that the application is broken.

It should determine:

1. Which Pod is affected?
2. Which PVC does the Pod use?
3. Is the PVC Bound?
4. Which PV is associated with it?
5. Is the volume attached?
6. Was the volume mounted successfully?
7. Is the filesystem writable?
8. Is there sufficient capacity?
9. Are permissions correct?
10. Is the CSI driver functioning?
11. Is the underlying storage healthy?

This allows Kube-InsightAI to combine **RAG knowledge about Kubernetes storage** with **live MCP infrastructure data** when the project is implemented.

---

# 32. Summary

Kubernetes storage troubleshooting should follow a layered approach:

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

The most important storage failures include:

* PVC Pending
* PV/PVC binding problems
* StorageClass misconfiguration
* Dynamic provisioning failures
* CSI driver failures
* FailedAttachVolume
* FailedMount
* Access mode conflicts
* Volume topology problems
* Permission errors
* Read-only filesystems
* Full filesystems
* Stateful application storage failures

The primary objective is to find the **first broken layer in the storage dependency chain** and fix that layer without unnecessarily modifying or deleting data.
