# Dev account. The default profile is read-only (dev-audit), so a normal
# "terraform plan" can never change anything. A write role is chosen on
# purpose, only when applying a change:
#   terraform plan -var dev_profile=dev-admin -out=change.tfplan
provider "aws" {
  region  = "eu-west-2"
  profile = var.dev_profile
}