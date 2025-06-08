terraform {
  backend "s3" {
    bucket  = "fusionsolar-management-terraform-state"
    key     = "infrastructure/terraform.tfstate"
    region  = "eu-central-1"
    encrypt = true
  }
}
