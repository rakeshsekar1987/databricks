# AKS Cluster Upgrade Guide: Version 1.30.0 to 1.35.0

## Overview

Upgrading an Azure Kubernetes Service (AKS) cluster from version 1.30.0 to 1.35.0 is a **major upgrade** spanning 5 minor versions. AKS only supports upgrading one minor version at a time, so you'll need to perform sequential upgrades:

```
1.30.0 → 1.31.x → 1.32.x → 1.33.x → 1.34.x → 1.35.0
```

This guide covers all precautions and steps to ensure a successful upgrade.

---

## Table of Contents

1. [Pre-Upgrade Assessment](#1-pre-upgrade-assessment)
2. [Backup and Disaster Recovery](#2-backup-and-disaster-recovery)
3. [Review Breaking Changes](#3-review-breaking-changes)
4. [Application Compatibility Testing](#4-application-compatibility-testing)
5. [Infrastructure Preparation](#5-infrastructure-preparation)
6. [Upgrade Execution](#6-upgrade-execution)
7. [Post-Upgrade Validation](#7-post-upgrade-validation)
8. [Rollback Strategy](#8-rollback-strategy)

---

## 1. Pre-Upgrade Assessment

### 1.1 Check Current Cluster Health

Before upgrading, ensure your cluster is healthy:

```bash
# Check cluster health
az aks show --resource-group <resource-group> --name <cluster-name> --query "provisioningState"

# Check node health
kubectl get nodes -o wide

# Check all pods are running
kubectl get pods --all-namespaces | grep -v Running | grep -v Completed

# Check for any pending PVCs
kubectl get pvc --all-namespaces | grep -v Bound

# Check cluster events for issues
kubectl get events --all-namespaces --sort-by='.lastTimestamp' | tail -50
```

### 1.2 Verify Available Upgrades

```bash
# Check available upgrade versions
az aks get-upgrades --resource-group <resource-group> --name <cluster-name> --output table

# Check current version
az aks show --resource-group <resource-group> --name <cluster-name> --query "kubernetesVersion"
```

### 1.3 Review Resource Quotas and Limits

```bash
# Check if you have sufficient quota for upgrade
az vm list-usage --location <region> --output table

# Ensure you have headroom for surge nodes during upgrade
az aks show --resource-group <resource-group> --name <cluster-name> --query "agentPoolProfiles[].{Name:name, Count:count, MaxCount:maxCount}"
```

### 1.4 Document Current Configuration

```bash
# Export current cluster configuration
az aks show --resource-group <resource-group> --name <cluster-name> > cluster-config-backup.json

# Export all Kubernetes resources
kubectl get all --all-namespaces -o yaml > all-resources-backup.yaml

# Export ConfigMaps and Secrets (be careful with secrets!)
kubectl get configmaps --all-namespaces -o yaml > configmaps-backup.yaml
kubectl get secrets --all-namespaces -o yaml > secrets-backup.yaml

# Export Custom Resource Definitions
kubectl get crd -o yaml > crds-backup.yaml
```

---

## 2. Backup and Disaster Recovery

### 2.1 Backup Persistent Volumes

```bash
# List all PVs and PVCs
kubectl get pv
kubectl get pvc --all-namespaces

# Create Azure Disk snapshots for each PV
az snapshot create \
  --resource-group <resource-group> \
  --source <disk-id> \
  --name <snapshot-name>
```

### 2.2 Backup Application Data

- Export databases to external storage
- Backup any stateful application data
- Verify backup integrity

### 2.3 Use Velero for Cluster Backup (Recommended)

```bash
# Install Velero if not already installed
velero install \
  --provider azure \
  --plugins velero/velero-plugin-for-microsoft-azure:v1.5.0 \
  --bucket <blob-container> \
  --secret-file ./credentials-velero \
  --backup-location-config resourceGroup=<resource-group>,storageAccount=<storage-account>

# Create full cluster backup
velero backup create pre-upgrade-backup --include-namespaces '*' --wait

# Verify backup completed
velero backup describe pre-upgrade-backup
```

### 2.4 Backup etcd (for self-managed control plane components)

AKS manages etcd, but ensure any custom resources are backed up:

```bash
# Export all custom resources
for crd in $(kubectl get crd -o name); do
  kubectl get ${crd} --all-namespaces -o yaml > "backup-${crd##*/}.yaml"
done
```

---

## 3. Review Breaking Changes

### 3.1 Kubernetes API Deprecations

Each Kubernetes version deprecates and removes APIs. Review these for each version:

| Version | Key Deprecations/Removals |
|---------|--------------------------|
| **1.31** | - `flowcontrol.apiserver.k8s.io/v1beta2` removed<br>- PodSecurityPolicy completely removed |
| **1.32** | - `autoscaling/v2beta2` removed (use `autoscaling/v2`)<br>- Legacy ServiceAccount token secrets deprecated |
| **1.33** | - `batch/v1beta1` CronJob removed<br>- `policy/v1beta1` PodDisruptionBudget removed |
| **1.34** | - `networking.k8s.io/v1beta1` Ingress removed<br>- In-tree cloud provider code deprecated |
| **1.35** | - Various alpha features may change<br>- Check official release notes |

### 3.2 Identify Deprecated APIs in Your Cluster

```bash
# Install pluto to detect deprecated APIs
# https://github.com/FairwindsOps/pluto
curl -L -o pluto.tar.gz https://github.com/FairwindsOps/pluto/releases/download/v5.16.1/pluto_5.16.1_linux_amd64.tar.gz
tar -xzf pluto.tar.gz
chmod +x pluto

# Scan cluster for deprecated APIs
./pluto detect-helm -o wide
./pluto detect-files -d . -o wide

# Check all deployments for deprecated APIs
kubectl get deployments.apps --all-namespaces -o yaml | ./pluto detect -
```

### 3.3 Update Deprecated Resources

Before upgrading, update all resources using deprecated APIs:

```bash
# Example: Update HorizontalPodAutoscaler from v2beta2 to v2
kubectl get hpa --all-namespaces -o yaml > hpa-backup.yaml

# Update the apiVersion in your manifests and reapply
# FROM: apiVersion: autoscaling/v2beta2
# TO:   apiVersion: autoscaling/v2
```

---

## 4. Application Compatibility Testing

### 4.1 Test in Non-Production Environment First

**CRITICAL**: Always test upgrades in a development/staging environment before production.

```bash
# Create a test cluster with the target version
az aks create \
  --resource-group <test-resource-group> \
  --name <test-cluster-name> \
  --kubernetes-version 1.35.0 \
  --node-count 3

# Deploy your applications and test thoroughly
```

### 4.2 Verify Helm Charts Compatibility

```bash
# List all Helm releases
helm list --all-namespaces

# Check each chart's compatibility with newer Kubernetes versions
helm show chart <chart-name> --version <version>

# Update Helm charts to compatible versions
helm repo update
helm upgrade <release-name> <chart> --version <new-version>
```

### 4.3 Check Operator Compatibility

For each operator in your cluster:
- Cert-Manager
- Ingress Controllers (NGINX, Traefik, etc.)
- Service Mesh (Istio, Linkerd)
- Monitoring (Prometheus, Grafana)
- External DNS
- External Secrets

```bash
# Example: Check cert-manager compatibility
kubectl get deployment cert-manager -n cert-manager -o jsonpath='{.spec.template.spec.containers[0].image}'

# Upgrade operators if needed BEFORE cluster upgrade
```

### 4.4 Test Pod Disruption Budgets

```bash
# List all PDBs
kubectl get pdb --all-namespaces

# Ensure PDBs allow at least one pod to be unavailable during node drains
kubectl describe pdb <pdb-name> -n <namespace>
```

---

## 5. Infrastructure Preparation

### 5.1 Configure Upgrade Settings

```bash
# Set max surge for node pools (recommended: 33% or 1 for small pools)
az aks nodepool update \
  --resource-group <resource-group> \
  --cluster-name <cluster-name> \
  --name <nodepool-name> \
  --max-surge 33%
```

### 5.2 Ensure Sufficient IP Address Space

```bash
# Check current IP usage
az network vnet subnet show \
  --resource-group <vnet-resource-group> \
  --vnet-name <vnet-name> \
  --name <subnet-name> \
  --query "addressPrefix"

# Ensure you have IPs for surge nodes
```

### 5.3 Schedule Maintenance Window

```bash
# Configure maintenance window (recommended for production)
az aks maintenanceconfiguration add \
  --resource-group <resource-group> \
  --cluster-name <cluster-name> \
  --name default \
  --weekday Saturday \
  --start-hour 22 \
  --duration 4
```

### 5.4 Notify Stakeholders

- Inform application teams
- Schedule maintenance window
- Prepare rollback team
- Set up monitoring dashboards

---

## 6. Upgrade Execution

### 6.1 Upgrade Path (Sequential Minor Versions)

You MUST upgrade one minor version at a time:

```bash
# Step 1: 1.30.0 → 1.31.x
az aks upgrade \
  --resource-group <resource-group> \
  --name <cluster-name> \
  --kubernetes-version 1.31.0 \
  --yes

# Wait for completion and validate before proceeding
kubectl get nodes
kubectl get pods --all-namespaces | grep -v Running | grep -v Completed

# Step 2: 1.31.x → 1.32.x
az aks upgrade \
  --resource-group <resource-group> \
  --name <cluster-name> \
  --kubernetes-version 1.32.0 \
  --yes

# Step 3: 1.32.x → 1.33.x
az aks upgrade \
  --resource-group <resource-group> \
  --name <cluster-name> \
  --kubernetes-version 1.33.0 \
  --yes

# Step 4: 1.33.x → 1.34.x
az aks upgrade \
  --resource-group <resource-group> \
  --name <cluster-name> \
  --kubernetes-version 1.34.0 \
  --yes

# Step 5: 1.34.x → 1.35.0
az aks upgrade \
  --resource-group <resource-group> \
  --name <cluster-name> \
  --kubernetes-version 1.35.0 \
  --yes
```

### 6.2 Upgrade Control Plane Only First (Optional but Recommended)

```bash
# Upgrade control plane first, then node pools separately
az aks upgrade \
  --resource-group <resource-group> \
  --name <cluster-name> \
  --kubernetes-version <version> \
  --control-plane-only \
  --yes

# Then upgrade each node pool
az aks nodepool upgrade \
  --resource-group <resource-group> \
  --cluster-name <cluster-name> \
  --name <nodepool-name> \
  --kubernetes-version <version>
```

### 6.3 Monitor Upgrade Progress

```bash
# Watch upgrade progress
az aks show --resource-group <resource-group> --name <cluster-name> --query "provisioningState"

# Monitor node status
kubectl get nodes -w

# Watch for pod disruptions
kubectl get pods --all-namespaces -w

# Check events
kubectl get events --all-namespaces --sort-by='.lastTimestamp' -w
```

---

## 7. Post-Upgrade Validation

### 7.1 Verify Cluster Health

```bash
# Check cluster version
az aks show --resource-group <resource-group> --name <cluster-name> --query "kubernetesVersion"

# Check all nodes are ready
kubectl get nodes

# Verify node versions
kubectl get nodes -o custom-columns=NAME:.metadata.name,VERSION:.status.nodeInfo.kubeletVersion

# Check system pods
kubectl get pods -n kube-system

# Check all pods across namespaces
kubectl get pods --all-namespaces | grep -v Running | grep -v Completed
```

### 7.2 Validate Application Functionality

```bash
# Run smoke tests
# Check endpoints
kubectl get svc --all-namespaces

# Test ingress/load balancer endpoints
curl -I https://<your-app-endpoint>

# Check application logs
kubectl logs -l app=<your-app> -n <namespace> --tail=100
```

### 7.3 Verify Monitoring and Logging

```bash
# Check Prometheus/Grafana
kubectl get pods -n monitoring

# Verify metrics collection
kubectl top nodes
kubectl top pods --all-namespaces

# Check log collection
kubectl logs -l app=fluentd -n logging --tail=50
```

### 7.4 Update kubectl and Tools

```bash
# Update kubectl to match cluster version
az aks install-cli

# Verify kubectl version
kubectl version --client
```

---

## 8. Rollback Strategy

### 8.1 Important: AKS Does NOT Support Downgrade

**CRITICAL**: Azure AKS does not support downgrading Kubernetes versions. If an upgrade fails:

1. **Option 1**: Fix forward - resolve issues and continue
2. **Option 2**: Restore from backup to a new cluster

### 8.2 Restore from Velero Backup

```bash
# Create new cluster with original version
az aks create \
  --resource-group <resource-group> \
  --name <new-cluster-name> \
  --kubernetes-version 1.30.0 \
  --node-count 3

# Restore from Velero backup
velero restore create --from-backup pre-upgrade-backup

# Verify restoration
kubectl get all --all-namespaces
```

### 8.3 Blue-Green Deployment Strategy (Safest)

For mission-critical workloads, consider a blue-green approach:

```bash
# Keep old cluster running (Blue)
# Create new cluster with target version (Green)
az aks create \
  --resource-group <resource-group> \
  --name <cluster-name>-green \
  --kubernetes-version 1.35.0

# Deploy applications to Green cluster
# Test thoroughly
# Switch traffic using Azure Traffic Manager or DNS
# Decommission Blue cluster after validation
```

---

## Pre-Upgrade Checklist

Use this checklist before each minor version upgrade:

- [ ] Cluster health verified
- [ ] All nodes in Ready state
- [ ] No pods in CrashLoopBackOff or Error state
- [ ] Backups completed and verified
- [ ] Deprecated APIs identified and updated
- [ ] Helm charts compatibility verified
- [ ] Operators updated to compatible versions
- [ ] Test upgrade completed in non-production
- [ ] PodDisruptionBudgets configured correctly
- [ ] Sufficient IP address space available
- [ ] Sufficient VM quota available
- [ ] Stakeholders notified
- [ ] Monitoring dashboards ready
- [ ] Rollback plan documented and tested

---

## Troubleshooting Common Issues

### Issue 1: Upgrade Stuck or Failing

```bash
# Check upgrade status
az aks show --resource-group <resource-group> --name <cluster-name> --query "provisioningState"

# Check node pool status
az aks nodepool show --resource-group <resource-group> --cluster-name <cluster-name> --name <nodepool-name>

# Check for stuck pods preventing node drain
kubectl get pods --all-namespaces -o wide | grep <draining-node>

# Force delete stuck pods (use with caution)
kubectl delete pod <pod-name> -n <namespace> --force --grace-period=0
```

### Issue 2: Pods Not Scheduling After Upgrade

```bash
# Check node taints
kubectl describe nodes | grep -A5 Taints

# Check pod events
kubectl describe pod <pod-name> -n <namespace>

# Check resource requests vs available
kubectl describe nodes | grep -A10 "Allocated resources"
```

### Issue 3: Network Issues After Upgrade

```bash
# Check CNI pods
kubectl get pods -n kube-system -l k8s-app=azure-cni

# Restart network pods if needed
kubectl rollout restart daemonset azure-cni -n kube-system
```

---

## Recommended Timeline

| Phase | Duration | Activities |
|-------|----------|------------|
| Planning | 1-2 weeks | Review breaking changes, update deprecated APIs |
| Testing | 1-2 weeks | Test in non-production environment |
| Preparation | 1 day | Backups, stakeholder notification |
| Upgrade Execution | 4-8 hours per version | Sequential upgrades with validation |
| Post-Validation | 1 day | Monitor and validate |

**Total estimated time for 5 minor version upgrades: 2-4 weeks (following best practices)**

---

## Additional Resources

- [AKS Kubernetes Version Support Policy](https://docs.microsoft.com/en-us/azure/aks/supported-kubernetes-versions)
- [Kubernetes Deprecation Guide](https://kubernetes.io/docs/reference/using-api/deprecation-guide/)
- [AKS Upgrade Documentation](https://docs.microsoft.com/en-us/azure/aks/upgrade-cluster)
- [Kubernetes Release Notes](https://kubernetes.io/releases/)

---

## Important Notes

1. **Always upgrade sequentially** - Skip versions are not supported
2. **No rollback possible** - Plan and test thoroughly
3. **Production upgrades during low-traffic windows** - Minimize impact
4. **Keep clusters within support window** - AKS supports N-2 versions
5. **Update client tools** - kubectl, Helm, etc. should match cluster version

---

*Last Updated: January 2026*
