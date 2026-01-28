# Variables for Creseada RFQ Automation infrastructure

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region for resources"
  type        = string
  default     = "us-central1"
}

variable "project_prefix" {
  description = "Prefix for resource names"
  type        = string
  default     = "creseada-rfq"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}
