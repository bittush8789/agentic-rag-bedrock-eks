variable "environment" {
  description = "Target deployment environment"
  type        = string
}

variable "db_name" {
  description = "PostgreSQL initial database name"
  type        = string
  default     = "agentic_rag"
}

variable "db_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "rag_admin"
}

variable "instance_class" {
  description = "RDS instance class (e.g. db.t4g.micro for dev, db.r6g.xlarge for prod)"
  type        = string
  default     = "db.t4g.micro"
}

variable "allocated_storage" {
  description = "Initial storage in GB"
  type        = number
  default     = 20
}

variable "max_allocated_storage" {
  description = "Storage autoscaling upper limit in GB"
  type        = number
  default     = 100
}

variable "db_subnet_group_name" {
  description = "Subnet group name in private database subnets"
  type        = string
}

variable "security_group_id" {
  description = "Security group ID restricting access from EKS nodes"
  type        = string
}

variable "multi_az" {
  description = "Enable Multi-AZ deployment"
  type        = bool
  default     = false
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = false
}

variable "skip_final_snapshot" {
  description = "Skip final snapshot upon destruction"
  type        = bool
  default     = true
}

variable "backup_retention_period" {
  description = "Days of automated backups"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}
