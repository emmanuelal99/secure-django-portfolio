# Platform dependencies

The portfolio runs on the [AWS landing zone](https://github.com/emmanuelal99/aws-landing-zone). This document lists what the portfolio expects the landing zone to provide, how the portfolio finds it, and what happens if it is missing.

The two projects are separate: each has its own repository and its own Terraform state. The portfolio reads platform resources and never manages them.

## Who owns what

| Resource | Owner | Managed in |
|---|---|---|
| Organisation, accounts, SCPs, tag policy | Landing zone | `aws-landing-zone/terraform` |
| IAM Identity Center (permission sets, groups, assignments) | Landing zone | `aws-landing-zone/terraform` |
| VPC, subnets, route tables, internet gateway, S3 endpoint | Landing zone | `aws-landing-zone/terraform` |
| NAT gateway (on demand) | Landing zone | `aws-landing-zone/scripts/` |
| GuardDuty, CloudTrail, account security settings | Landing zone | `aws-landing-zone/terraform` |
| EC2 instance, security group, instance role | Portfolio | `terraform/main.tf` |
| ECR repository, media bucket, CloudFront | Portfolio | `terraform/main.tf` |
| Parameter Store values | Portfolio | Console (not in Terraform, see below) |

## What the portfolio depends on

### Network

| Dependency | How the portfolio finds it | Used for |
|---|---|---|
| VPC tagged `Name=portfolio-vpc` | `data "aws_vpc" "platform"` | The security group and the instance |
| Private subnet tagged `Name=portfolio-private-a` | `data "aws_subnet" "private_a"` | Where the instance runs, with no public IP |
| Private route table, attached to that subnet | Not referenced directly | Without the attachment, the subnet falls back to the main route table and SSM cannot connect |
| S3 gateway endpoint on the private route table | Not referenced directly | Media uploads to S3 and ECR image layers, without the NAT |
| NAT gateway, switched on with `nat-on.sh` | Not referenced | Deployments, server sessions and the admin tunnel |

### Identity

| Dependency | Used for |
|---|---|
| Developer permission set with `iam:PassRole` for `portfolio-ec2-role` only | Launching the instance with its role |
| PortfolioAdmin permission set (port forwarding only) | The Django admin tunnel |
| Developers group assigned to both, in the Dev account | Access for the people who run the portfolio |

### Guardrails the portfolio must respect

| Guardrail | Effect |
|---|---|
| Region lock | Everything is in `eu-west-2`. CloudFront is global and exempt. |
| Tag policy | Resources use `Project=Portfolio`, `Env=Dev`, `Owner=Emmy` |
| Baseline deny | No IAM users or access keys. The instance carries `Project` at launch. |

### Security services that cover the portfolio automatically

- GuardDuty (foundational detection and S3 Protection, including the media bucket)
- The organisation CloudTrail trail
- Account defaults: EBS encryption and IMDSv2 for new instances

## What happens if a dependency is missing

The data sources only read. If the VPC or subnet cannot be found, `terraform plan` stops with an error such as `no matching EC2 VPC found`. Nothing is created in the wrong place and nothing is changed.

## Known limitation: rebuilding from nothing

The CloudFront service security group (`CloudFront-VPCOrigins-Service-SG`) is created by AWS the first time a VPC origin is created in the VPC. The portfolio reads it with a data source, so on a completely new build:

1. The first apply would fail, because the group does not exist yet.
2. The fix is a two-step build: create the VPC origin first (with the security group allowing the CloudFront managed prefix list), then switch the rule to the service security group.

This does not affect the current environment, which was imported rather than built.

## Not managed by Terraform

Parameter Store values (`/portfolio/prod/*`) are created in the console. Importing SecureString parameters would store the secrets in plain text in the Terraform state.

## Order of operations

- **Build:** landing zone first, then the portfolio.
- **Change:** network or identity changes go to the landing zone repository; application changes go to this repository.
- **Destroy:** the portfolio first, then the landing zone. The portfolio's instance and security group sit inside the landing zone VPC, so the network cannot be removed while they exist.
