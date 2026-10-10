# 1. EKS Cluster
resource "aws_eks_cluster" "main" {
  name     = "${var.environment}-agentic-rag-eks"
  role_arn = var.cluster_role_arn
  version  = var.cluster_version

  vpc_config {
    subnet_ids              = concat(var.public_subnet_ids, var.private_subnet_ids)
    security_group_ids      = [var.node_security_group_id]
    endpoint_private_access = true
    endpoint_public_access  = var.endpoint_public_access
    public_access_cidrs     = var.public_access_cidrs
  }

  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-eks-cluster"
    }
  )
}

# 2. Managed Node Group
resource "aws_eks_node_group" "workload" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.environment}-workload-nodes"
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_subnet_ids

  instance_types = var.instance_types
  capacity_type  = var.capacity_type

  scaling_config {
    desired_size = var.desired_nodes
    max_size     = var.max_nodes
    min_size     = var.min_nodes
  }

  update_config {
    max_unavailable = 1
  }

  labels = {
    role        = "workload"
    environment = var.environment
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-workload-node"
    }
  )

  depends_on = [
    aws_eks_cluster.main
  ]
}

# 3. Managed Cluster Add-ons
resource "aws_eks_addon" "vpc_cni" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "vpc-cni"
}

resource "aws_eks_addon" "coredns" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "coredns"
  depends_on   = [aws_eks_node_group.workload]
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "kube-proxy"
}

resource "aws_eks_addon" "pod_identity" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "eks-pod-identity-agent"
}

# 4. EKS Pod Identity Associations
resource "aws_eks_pod_identity_association" "backend" {
  cluster_name    = aws_eks_cluster.main.name
  namespace       = var.namespace
  service_account = "agentic-rag-backend-sa"
  role_arn        = var.backend_pod_role_arn

  depends_on = [aws_eks_addon.pod_identity]
}

resource "aws_eks_pod_identity_association" "worker" {
  cluster_name    = aws_eks_cluster.main.name
  namespace       = var.namespace
  service_account = "agentic-rag-worker-sa"
  role_arn        = var.worker_pod_role_arn

  depends_on = [aws_eks_addon.pod_identity]
}
