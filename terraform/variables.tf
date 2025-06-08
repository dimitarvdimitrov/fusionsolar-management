variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "eu-central-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small"
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for data storage"
  type        = string
  default     = "fusionsolar-management"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}
