# GitOps & Argo CD Guide

## 1. GitOps Workflow Overview

The platform uses **Argo CD** to manage application delivery through GitOps principles:
1. Git is the single source of truth for all Kubernetes configurations.
2. Changes to container images and Helm values are committed to the repository.
3. Argo CD detects configuration drift and applies the approved desired state to EKS.

---

## 2. Installing Argo CD on EKS

```bash
# 1. Create Argo CD namespace
kubectl create namespace argocd

# 2. Install Argo CD manifests
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 3. Retrieve initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
echo

# 4. Port forward Argo CD UI
kubectl port-forward svc/argocd-server -n argocd 8081:443
```

---

## 3. Registering Applications in Argo CD

### 3.1 Development Application
Apply the dev application manifest:
```bash
kubectl apply -f deploy/argocd/application-dev.yaml
```
- **Sync Policy**: Automated with `selfHeal: true` and `prune: true`.
- Automatically deploys on every commit to `main`.

### 3.2 Production Application
Apply the production application manifest:
```bash
kubectl apply -f deploy/argocd/application-prod.yaml
```
- **Sync Policy**: Manual synchronization.
- Requires operator approval through the Argo CD Web UI or CLI.

---

## 4. Promotion Workflow (Dev to Prod)

1. **Pull Request**: Developer merges a feature branch to `main`.
2. **CI Pipeline**: GitHub Actions validates tests, scans images with Trivy, and pushes versioned images (`sha-<commit>`) to ECR.
3. **CD Pipeline**: GitHub Actions updates `values.yaml` in the GitOps repository.
4. **Dev Sync**: Argo CD auto-syncs the new image to the `agentic-rag-dev` namespace.
5. **Production Promotion**:
   - The platform team reviews the dev deployment and metrics.
   - The team creates a pull request updating `deploy/helm/agentic-rag/values-prod.yaml`.
   - Once approved, the operator triggers manual sync in Argo CD for `agentic-rag-prod`.
