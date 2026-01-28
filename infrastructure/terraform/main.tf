# Terraform configuration for Creseada RFQ Automation on GCP
# This creates the infrastructure needed for the MVP deployment

terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Configure backend for state storage
  # Uncomment and configure for production use
  # backend "gcs" {
  #   bucket = "your-terraform-state-bucket"
  #   prefix = "creseada-rfq"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "aiplatform.googleapis.com",
    "storage.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# Cloud SQL PostgreSQL instance
resource "google_sql_database_instance" "main" {
  name             = "${var.project_prefix}-db"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = "db-f1-micro"  # Smallest tier for MVP
    availability_type = "ZONAL"

    ip_configuration {
      ipv4_enabled = true
      # IMPORTANT:
      # Do NOT use 0.0.0.0/0 authorized networks.
      # Connect from Cloud Run using the Cloud SQL connector instead.
    }

    backup_configuration {
      enabled    = true
      start_time = "03:00"
    }
  }

  deletion_protection = false  # Set to true for production

  depends_on = [google_project_service.apis["sqladmin.googleapis.com"]]
}

# Database
resource "google_sql_database" "rfq" {
  name     = "rfq_automation"
  instance = google_sql_database_instance.main.name
}

# Database user
resource "google_sql_user" "rfq" {
  name     = "rfq_user"
  instance = google_sql_database_instance.main.name
  password = random_password.db_password.result
}

resource "random_password" "db_password" {
  length  = 24
  special = false
}

# Secret for database URL
resource "google_secret_manager_secret" "database_url" {
  secret_id = "DATABASE_URL"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis["secretmanager.googleapis.com"]]
}

resource "google_secret_manager_secret_version" "database_url" {
  secret = google_secret_manager_secret.database_url.id
  # Cloud Run + Cloud SQL connector Unix socket connection string
  # Requires Cloud Run deployment flag: --add-cloudsql-instances=<connection_name>
  secret_data = "postgresql://${google_sql_user.rfq.name}:${random_password.db_password.result}@/${google_sql_database.rfq.name}?host=/cloudsql/${google_sql_database_instance.main.connection_name}"
}

# Cloud Storage bucket for email uploads
resource "google_storage_bucket" "rfq_uploads" {
  name          = "${var.project_id}-rfq-uploads"
  location      = var.region
  force_destroy = true  # Set to false for production

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 90  # Delete files older than 90 days
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.apis["storage.googleapis.com"]]
}

# Cloud Run service account
resource "google_service_account" "cloud_run" {
  account_id   = "${var.project_prefix}-run-sa"
  display_name = "Creseada RFQ Cloud Run Service Account"
}

# Grant necessary permissions to service account
resource "google_project_iam_member" "cloud_run_roles" {
  for_each = toset([
    "roles/secretmanager.secretAccessor",
    "roles/cloudsql.client",
    "roles/storage.objectAdmin",
    "roles/aiplatform.user",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Grant Secret Manager access to Cloud Build
resource "google_secret_manager_secret_iam_member" "cloud_build_access" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_project.current.number}@cloudbuild.gserviceaccount.com"
}

data "google_project" "current" {
  project_id = var.project_id
}

# Outputs
output "database_instance" {
  value = google_sql_database_instance.main.name
}

output "database_ip" {
  value = google_sql_database_instance.main.public_ip_address
}

output "storage_bucket" {
  value = google_storage_bucket.rfq_uploads.name
}

output "service_account" {
  value = google_service_account.cloud_run.email
}

output "database_connection_name" {
  value = google_sql_database_instance.main.connection_name
}
