generate "versions.tf" {
  path      = "versions.tf"
  if_exists = "skip"
  contents  = <<EOF
terraform {
  required_providers {
  aws = {
  source  = "hashicorp/aws"
  version = "~> 5.33.0"
}
}
}
EOF
}

generate "backend.tf" {
  path      = "backend.tf"
  if_exists = "skip"
  contents  = <<EOF
terraform {
  backend "s3" {}
}
EOF
}

remote_state {
  backend = "s3"
  config = {
    bucket         = "ft-<AWS_ACCOUNT_ID>-<AWS_REGION>-tfstate"
    key            = "finisterra/generated/aws/<AWS_ACCOUNT_ID>/<AWS_REGION>/${path_relative_to_include()}/terraform.${run_cmd("--terragrunt-quiet", "sh", "-c", "touch ${get_original_terragrunt_dir()}/state_hash && cat ${get_original_terragrunt_dir()}/state_hash")}.tfstate"
    region         = "<AWS_REGION>"
    encrypt        = true
    dynamodb_table = "ft-<AWS_ACCOUNT_ID>-<AWS_REGION>-tfstate-lock"
  }
}

generate "data.tf" {
  path      = "data.tf"
  if_exists = "skip"
  contents  = <<EOF
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
EOF
}

generate "locals.tf" {
  path      = "locals.tf"
  if_exists = "skip"
  contents  = <<EOF
locals {
  aws_region = data.aws_region.current.name
  aws_account_id = data.aws_caller_identity.current.account_id
  aws_partition = can(regex("gov", local.aws_region)) ? "aws-us-gov" : "aws"
}
EOF
}

