# Kubernetes & EKS Deployment Guide

## 1. Connecting to the EKS Cluster

Once Terraform completes provisioning, generate your local `kubeconfig`:

```bash
aws eks update-kubeconfig \
  --region us-east-1 \
  --name dev-agentic-rag-eks
```

Verify connection:
```bash
kubectl get nodes -o wide
```

---

## 2. Installing Prerequisites on EKS

### 2.1 AWS Load Balancer Controller
The application uses AWS Load Balancer Controller to manage Application Load Balancers via Kubernetes Ingress:

```bash
# Add EKS Helm repository
helm repo add eks https://aws.github.io/eks-charts
helm repo update

# Install AWS Load Balancer Controller
helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=dev-agentic-rag-eks \
  --set serviceAccount.create=true \
  --set serviceAccount.name=aws-load-balancer-controller
```

---

## 3. Deploying the Application via Helm

### 3.1 Development Deployment
```bash
# Render templates locally to verify correctness
helm template agentic-rag deploy/helm/agentic-rag -f deploy/helm/agentic-rag/values-dev.yaml

# Install or upgrade release
helm upgrade --install agentic-rag deploy/helm/agentic-rag \
  --namespace agentic-rag \
  --create-namespace \
  -f deploy/helm/agentic-rag/values-dev.yaml
```

### 3.2 Production Deployment
```bash
helm upgrade --install agentic-rag deploy/helm/agentic-rag \
  --namespace agentic-rag \
  --create-namespace \
  -f deploy/helm/agentic-rag/values-prod.yaml
```

---

## 4. Rollout Verification

Verify all pods, services, and ingress resources:

```bash
# Check Pod status
kubectl get pods -n agentic-rag

# Check Services
kubectl get svc -n agentic-rag

# Check Ingress & ALB DNS Name
kubectl get ingress -n agentic-rag

# View backend logs with correlation IDs
kubectl logs -n agentic-rag -l app.kubernetes.io/component=backend -f

# View worker logs
kubectl logs -n agentic-rag -l app.kubernetes.io/component=worker -f
```

---

## 5. Rollback Procedure

If a release introduces regression:

```bash
# View release history
helm history agentic-rag -n agentic-rag

# Rollback to previous revision
helm rollback agentic-rag <REVISION_NUMBER> -n agentic-rag
```
