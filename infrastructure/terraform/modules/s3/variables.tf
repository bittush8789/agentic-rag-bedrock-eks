variable "environment" {
  description = "Target deployment environment"
  type        = string
}

variable "account_id" {
  description = "AWS Account ID for globally unique bucket naming"
  type        = string
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}
