# Kubernetes ConfigMaps and Secrets Troubleshooting SOP

## 1. Purpose

This SOP provides a systematic procedure for diagnosing and troubleshooting Kubernetes ConfigMap and Secret issues.

It is intended to help identify problems involving:

* Missing ConfigMaps
* Missing Secrets
* Incorrect configuration values
* Incorrect environment variables
* Environment variable references
* Volume-mounted configuration
* Secret references
* Configuration changes
* Application startup failures
* `CreateContainerConfigError`
* `CreateContainerError`
* Configuration-related Pod failures

---

# 2. What Is a ConfigMap?

A ConfigMap stores non-sensitive configuration data separately from application container images.

Examples include:

* Application configuration
* Environment settings
* Configuration files
* URLs
* Feature flags
* Non-sensitive application parameters

Example:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: payment-config
data:
  APP_MODE: production
  LOG_LEVEL: info
```

A Pod can consume ConfigMap values through:

* Environment variables
* Environment variable references
* Volume mounts

Conceptually:

```text
ConfigMap
    ↓
Pod
    ↓
Container
    ↓
Application
```

---

# 3. What Is a Secret?

A Kubernetes Secret stores data intended to be sensitive, such as:

* Passwords
* API tokens
* Authentication credentials
* TLS certificates
* Registry credentials

Example:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: payment-secret
type: Opaque
data:
  DATABASE_PASSWORD: <encoded-value>
```

A Secret can be consumed through:

* Environment variables
* Volume mounts
* Image pull credentials
* Other Kubernetes resources

Conceptually:

```text
Secret
   ↓
Pod
   ↓
Container
   ↓
Application
```

---

# 4. Important Security Principle

A Kubernetes Secret is intended for sensitive data, but storing a value in a Secret does not automatically make the value fully secure.

Kubernetes Secret data is commonly represented as Base64-encoded data.

Base64 is **encoding, not encryption**.

Do not treat Base64 encoding as a security mechanism.

Production environments should also consider:

* Encryption at rest
* RBAC
* Least-privilege access
* External secret-management systems
* Secret rotation
* Audit logging

---

# 5. ConfigMap vs Secret

| ConfigMap                   | Secret                     |
| --------------------------- | -------------------------- |
| Non-sensitive configuration | Sensitive configuration    |
| Application settings        | Passwords                  |
| Feature flags               | API tokens                 |
| URLs                        | Certificates               |
| Log levels                  | Authentication credentials |
| Configuration files         | Registry credentials       |

Simple rule:

```text
Non-sensitive → ConfigMap
Sensitive     → Secret
```

---

# 6. General Troubleshooting Workflow

When an application has a configuration-related problem:

```text
1. Check Pod status
        ↓
2. Check Pod events
        ↓
3. Check container logs
        ↓
4. Inspect Deployment
        ↓
5. Identify ConfigMap/Secret references
        ↓
6. Verify ConfigMap/Secret exists
        ↓
7. Verify namespace
        ↓
8. Verify key names
        ↓
9. Verify configuration values
        ↓
10. Check volume/environment configuration
        ↓
11. Restart/redeploy when required
        ↓
12. Verify application health
```

---

# 7. List ConfigMaps

List ConfigMaps in the current namespace:

```bash
kubectl get configmaps
```

Or:

```bash
kubectl get cm
```

List ConfigMaps in a specific namespace:

```bash
kubectl get configmaps -n <namespace>
```

Inspect a ConfigMap:

```bash
kubectl describe configmap <configmap-name>
```

Get its YAML:

```bash
kubectl get configmap <configmap-name> -o yaml
```

---

# 8. List Secrets

List Secrets:

```bash
kubectl get secrets
```

List Secrets in a specific namespace:

```bash
kubectl get secrets -n <namespace>
```

Describe a Secret:

```bash
kubectl describe secret <secret-name>
```

Get Secret metadata and encoded values:

```bash
kubectl get secret <secret-name> -o yaml
```

Avoid exposing sensitive Secret values unnecessarily.

Use appropriate access controls when investigating Secrets.

---

# 9. ConfigMap Does Not Exist

## Symptom

A Pod references a ConfigMap that does not exist.

This can result in a Pod failing to start or configuration not being available.

## Common Causes

* ConfigMap was never created
* ConfigMap was deleted
* Incorrect ConfigMap name
* Wrong namespace
* Deployment references an old ConfigMap name

## Investigation

Check ConfigMaps:

```bash
kubectl get configmaps
```

Check the Pod:

```bash
kubectl describe pod <pod-name>
```

Inspect the Deployment:

```bash
kubectl get deployment <deployment-name> -o yaml
```

Look for:

```yaml
configMap:
  name: <configmap-name>
```

Verify that the referenced ConfigMap exists in the same namespace as the consuming workload.

---

# 10. Secret Does Not Exist

## Symptom

A Pod references a Secret that does not exist.

The container may fail to start.

## Common Causes

* Secret was never created
* Secret was deleted
* Incorrect Secret name
* Wrong namespace
* Deployment references an outdated Secret

## Investigation

Check:

```bash
kubectl get secrets
```

Inspect the Pod:

```bash
kubectl describe pod <pod-name>
```

Inspect the Deployment:

```bash
kubectl get deployment <deployment-name> -o yaml
```

Identify the referenced Secret and verify that it exists in the expected namespace.

---

# 11. Namespace Mismatch

ConfigMaps and Secrets are namespaced resources.

For example:

```text
production
├── payment-api
└── payment-config

development
├── payment-api
└── payment-config
```

A Pod in `production` cannot directly consume a ConfigMap or Secret with the same name from `development`.

Always check the namespace:

```bash
kubectl get configmap <configmap-name> -n <namespace>
```

```bash
kubectl get secret <secret-name> -n <namespace>
```

Also check the Pod namespace:

```bash
kubectl get pod <pod-name> -o jsonpath='{.metadata.namespace}'
```

---

# 12. ConfigMap Used as Environment Variables

Example:

```yaml
env:
  - name: APP_MODE
    valueFrom:
      configMapKeyRef:
        name: payment-config
        key: APP_MODE
```

The referenced key must exist.

Inspect:

```bash
kubectl get configmap payment-config -o yaml
```

Verify:

```text
ConfigMap name
      ↓
Key name
      ↓
Environment variable
```

An incorrect key reference can prevent the expected configuration from being available.

---

# 13. Secret Used as Environment Variables

Example:

```yaml
env:
  - name: DATABASE_PASSWORD
    valueFrom:
      secretKeyRef:
        name: payment-secret
        key: DATABASE_PASSWORD
```

Verify:

* Secret exists
* Secret is in the correct namespace
* Key exists
* Pod has permission to access the Secret

Inspect metadata and keys carefully without unnecessarily exposing sensitive values.

---

# 14. ConfigMap Mounted as a Volume

A ConfigMap can be mounted into a container as files.

Example:

```yaml
volumes:
  - name: app-config
    configMap:
      name: payment-config
```

The volume can then be mounted into the container.

Conceptually:

```text
ConfigMap
    ↓
Volume
    ↓
Container filesystem
    ↓
Application
```

If configuration files are missing:

Check:

```bash
kubectl describe pod <pod-name>
```

Inspect the volume configuration:

```bash
kubectl get pod <pod-name> -o yaml
```

Verify:

* ConfigMap exists
* Correct ConfigMap name
* Volume is configured
* VolumeMount is configured
* Mount path is correct

---

# 15. Secret Mounted as a Volume

Secrets can also be mounted as files.

Conceptually:

```text
Secret
  ↓
Volume
  ↓
Container filesystem
  ↓
Application
```

Inspect:

```bash
kubectl describe pod <pod-name>
```

Check the Pod specification:

```bash
kubectl get pod <pod-name> -o yaml
```

Verify:

* Secret exists
* Correct Secret name
* Volume configuration
* VolumeMount configuration
* Mount path
* File/key configuration

---

# 16. `CreateContainerConfigError`

## Symptom

A Pod displays:

```text
CreateContainerConfigError
```

This can indicate that Kubernetes cannot create the container because required configuration is invalid or unavailable.

## Possible Causes

* Missing ConfigMap
* Missing Secret
* Incorrect key reference
* Invalid environment configuration
* Missing referenced resource
* Incorrect volume configuration

## Investigation

Start with:

```bash
kubectl describe pod <pod-name>
```

Pay particular attention to the Events section.

Then inspect:

```bash
kubectl get deployment <deployment-name> -o yaml
```

Check ConfigMaps:

```bash
kubectl get configmaps
```

Check Secrets:

```bash
kubectl get secrets
```

---

# 17. `CreateContainerError`

## Symptom

The Pod displays:

```text
CreateContainerError
```

This indicates a problem occurred while creating the container.

## Possible Causes

Depending on the situation:

* Invalid container configuration
* Volume problems
* Mount configuration problems
* Runtime configuration problems
* Missing required resources

## Investigation

Use:

```bash
kubectl describe pod <pod-name>
```

Then inspect:

```bash
kubectl get pod <pod-name> -o yaml
```

Review events and container configuration.

---

# 18. Configuration Value Is Incorrect

## Symptom

The application starts but behaves incorrectly.

Examples:

```text
Wrong database host
Wrong API endpoint
Wrong application mode
Wrong feature flag
Wrong environment
```

## Investigation

Identify how the application receives its configuration.

Check the Deployment:

```bash
kubectl get deployment <deployment-name> -o yaml
```

Determine whether configuration comes from:

* ConfigMap
* Secret
* Environment variable
* Volume-mounted file
* Container argument
* Container command

Then inspect the relevant configuration source.

---

# 19. ConfigMap Updated but Application Still Uses Old Value

Updating a ConfigMap does not necessarily cause an application using environment variables to automatically restart.

For workloads consuming ConfigMap values through environment variables, a new Pod may be required for the updated environment to take effect.

A common approach is to restart the Deployment:

```bash
kubectl rollout restart deployment/<deployment-name>
```

Then verify:

```bash
kubectl rollout status deployment/<deployment-name>
```

And:

```bash
kubectl get pods
```

For volume-mounted ConfigMaps, Kubernetes can update the mounted content asynchronously, subject to the mechanism being used and application behavior.

Applications may still need to reload the configuration to recognize the change.

---

# 20. Secret Updated but Application Still Uses Old Value

The same principle applies to Secrets.

If a Secret is consumed through environment variables, existing containers generally continue using the value that was present when the container started.

A rollout may therefore be required:

```bash
kubectl rollout restart deployment/<deployment-name>
```

Then verify:

```bash
kubectl rollout status deployment/<deployment-name>
```

Do not expose Secret values during troubleshooting.

---

# 21. Check Environment Configuration

Inspect the Deployment specification:

```bash
kubectl get deployment <deployment-name> -o yaml
```

Look for:

```yaml
env:
envFrom:
```

Determine whether values come from:

```text
ConfigMap
Secret
Direct value
```

For troubleshooting, inspect configuration references rather than unnecessarily printing sensitive values.

---

# 22. `envFrom` Troubleshooting

A container can import multiple configuration values using `envFrom`.

Example:

```yaml
envFrom:
  - configMapRef:
      name: payment-config
  - secretRef:
      name: payment-secret
```

Verify:

```text
ConfigMap exists
       +
Secret exists
       +
Correct namespace
       +
Expected keys
```

Inspect the Pod:

```bash
kubectl describe pod <pod-name>
```

---

# 23. Configuration Key Mismatch

Example:

ConfigMap:

```yaml
data:
  DATABASE_HOST: database
```

Application expects:

```text
DB_HOST
```

The ConfigMap exists, but the application may still fail because the expected key is different.

Investigation:

```text
Application expected key
          ↓
Deployment reference
          ↓
ConfigMap/Secret key
```

Verify all names match.

---

# 24. ConfigMap or Secret Deleted During Deployment

A Deployment may reference configuration resources that are later deleted.

This can cause newly created Pods to fail while older Pods may continue running.

Example:

```text
Old Pods
   ↓
Started successfully

ConfigMap deleted

New Pods
   ↓
Cannot obtain required configuration
```

When a Deployment rollout starts failing unexpectedly, check whether referenced ConfigMaps or Secrets still exist.

---

# 25. RBAC and Secret Access

Access to Secrets can be restricted through Kubernetes authorization mechanisms.

If a workload or controller requires access to a Secret, verify the relevant permissions when appropriate.

Investigate:

* ServiceAccount
* Role
* ClusterRole
* RoleBinding
* ClusterRoleBinding

Useful commands:

```bash
kubectl get serviceaccount
```

```bash
kubectl get role
```

```bash
kubectl get rolebinding
```

For cluster-scoped resources:

```bash
kubectl get clusterrole
```

```bash
kubectl get clusterrolebinding
```

Do not grant broader permissions than necessary.

---

# 26. Useful ConfigMap Commands

### List ConfigMaps

```bash
kubectl get configmaps
```

### Describe ConfigMap

```bash
kubectl describe configmap <configmap-name>
```

### Get ConfigMap YAML

```bash
kubectl get configmap <configmap-name> -o yaml
```

### Get ConfigMap from namespace

```bash
kubectl get configmap <configmap-name> -n <namespace>
```

---

# 27. Useful Secret Commands

### List Secrets

```bash
kubectl get secrets
```

### Describe Secret

```bash
kubectl describe secret <secret-name>
```

### Get Secret metadata/YAML

```bash
kubectl get secret <secret-name> -o yaml
```

### Get Secret from namespace

```bash
kubectl get secret <secret-name> -n <namespace>
```

Handle Secret values carefully and avoid exposing credentials in logs, terminals, tickets, or chat.

---

# 28. Useful Pod and Deployment Commands

### Check Pod

```bash
kubectl get pod <pod-name>
```

### Describe Pod

```bash
kubectl describe pod <pod-name>
```

### Get Pod YAML

```bash
kubectl get pod <pod-name> -o yaml
```

### Check Deployment

```bash
kubectl get deployment <deployment-name>
```

### Get Deployment YAML

```bash
kubectl get deployment <deployment-name> -o yaml
```

### Restart Deployment

```bash
kubectl rollout restart deployment/<deployment-name>
```

### Check rollout

```bash
kubectl rollout status deployment/<deployment-name>
```

---

# 29. Configuration Troubleshooting Decision Flow

```text
                 Application Problem
                         │
                         ↓
                  Check Pod Status
                         │
                         ↓
               Configuration-related?
                  /             \
                No               Yes
                ↓                 ↓
          Other SOPs       Check Deployment
                                  │
                                  ↓
                         Find Config References
                                  │
                     ┌────────────┴────────────┐
                     ↓                         ↓
                 ConfigMap                  Secret
                     │                         │
                     ↓                         ↓
                  Exists?                   Exists?
                  /     \                   /     \
                No       Yes              No       Yes
                ↓         ↓               ↓         ↓
             Create    Check keys      Create    Check keys
                       and values                 and refs
                     │                         │
                     └────────────┬────────────┘
                                  ↓
                         Check namespace
                                  ↓
                       Check Pod references
                                  ↓
                         Check volume/env
                                  ↓
                         Check application
                                  ↓
                              Remediate
                                  ↓
                         Restart/redeploy
                           if required
                                  ↓
                             Verify
```

---

# 30. Configuration Troubleshooting Checklist

```text
☐ Pod namespace identified
☐ ConfigMap exists
☐ Secret exists
☐ Correct namespace
☐ Correct ConfigMap name
☐ Correct Secret name
☐ Required keys exist
☐ Environment references are correct
☐ envFrom references are correct
☐ Volume configuration is correct
☐ VolumeMount configuration is correct
☐ Mount path is correct
☐ Application expects the same key names
☐ Configuration values are valid
☐ Deployment references current configuration
☐ ServiceAccount permissions checked when relevant
☐ Application restarted/redeployed when required
☐ Application logs checked
☐ Pod status verified
☐ Configuration values handled securely
```

---

# 31. Verification After Remediation

After fixing the configuration:

Check the Deployment:

```bash
kubectl get deployment <deployment-name>
```

Check rollout:

```bash
kubectl rollout status deployment/<deployment-name>
```

Check Pods:

```bash
kubectl get pods
```

Check logs:

```bash
kubectl logs <pod-name>
```

Verify:

* Pods are Running
* Pods are Ready
* Restart count is stable
* Application starts successfully
* Expected configuration is being used
* No configuration-related errors appear in logs

Do not expose sensitive Secret values during verification.

---

# 32. Important Troubleshooting Principle

When an application has a configuration problem, do not immediately assume the ConfigMap or Secret itself is broken.

Follow the complete configuration path:

```text
Application
     ↓
Environment / File
     ↓
Pod Specification
     ↓
ConfigMap / Secret Reference
     ↓
ConfigMap / Secret
     ↓
Key
     ↓
Value
```

A failure anywhere in this chain can cause application problems.

---

# 33. Kube-InsightAI Diagnostic Principle

When Kube-InsightAI receives a ConfigMap or Secret-related question, it should correlate:

```text
Pod
 +
Deployment
 +
Environment Variables
 +
ConfigMap
 +
Secret
 +
Keys
 +
Volumes
 +
VolumeMounts
 +
ServiceAccount / RBAC
 +
Application Logs
 +
Pod Events
 ↓
Root Cause
```

The RAG knowledge base provides the documented troubleshooting procedure.

Later, MCP can retrieve the live Deployment, Pod, ConfigMap, Secret metadata, ServiceAccount, RBAC configuration, events, and logs from the Kubernetes environment.

Kube-InsightAI can then combine the SOP guidance with live cluster information to determine the likely cause and recommend the next troubleshooting step.
