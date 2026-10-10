variable "aws_region" {
  description = "AWS deployment region"
  type        = string
  default     = "us-east-1"
}

variable "admin_cidr_blocks" {
  description = "Allowed CIDR blocks for accessing EKS control plane API endpoint"
  type        = list(string)
  default     = ["10.0.0.0/8"]
}
