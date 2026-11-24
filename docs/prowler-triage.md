# Prowler triage: portfolio workload

This document covers the findings about the portfolio workload in the Dev account: CloudFront, the media bucket, the instance, the instance role and the container image. Account-wide findings (identity, password policy, GuardDuty, the shared network) are triaged in the landing zone repository, because the platform owns them.

## How the scan was run

```bash
prowler aws --profile dev-audit --region eu-west-2 \
  --services ec2 vpc s3 cloudfront ecr ssm iam guardduty \
  --config-file ~/prowler-reports/prowler-config.yaml \
  --output-directory ~/prowler-reports/dev-phase9
```

The scan used a read-only profile and one region. Raw reports are kept outside the repository because they contain account IDs and resource names.

## Results

| Scan | Failed (workload) |
|---|---|
| Before | 22 |
| After | 21 |

Every remaining finding is accepted or deferred below, with a reason.

## Fixed

| Finding | Fix | Why |
|---|---|---|
| `ecr_repositories_lifecycle_policy_enabled` | Untagged images expire after 7 days; the 10 newest images are kept | Old images build up, cost storage and still contain old vulnerabilities |

## Accepted

| Finding | Reason |
|---|---|
| `iam_inline_policy_allows_privilege_escalation` (PortfolioAdmin) | **False positive.** The permission set only allows `ssm:StartSession` with the `AWS-StartPortForwardingSession` document, on instances tagged `Project=Portfolio`. No shell can be opened, so the instance role's credentials cannot be reached. |
| `iam_role_cross_service_confused_deputy_prevention` (`portfolio-ec2-role`) | The role can only be used through an instance profile in this account, and `iam:PassRole` is limited to EC2. Adding conditions to an EC2 trust policy risks breaking the instance's credentials. |
| `cloudfront_distributions_default_root_object` | Meant for S3 static websites. Django serves `/` itself, so this does not apply. |
| `cloudfront_distributions_logging_enabled` | CloudTrail records configuration changes. Access logs add storage cost. |
| `cloudfront_distributions_field_level_encryption_enabled` | The public site only allows GET and HEAD, so no form data passes through CloudFront |
| `cloudfront_distributions_geo_restrictions_enabled` | A public portfolio for recruiters in any country |
| `ec2_instance_detailed_monitoring_enabled` | Standard 5-minute metrics are enough for a portfolio |
| `ecr_repositories_scan_vulnerabilities_in_latest_image` | Already triaged at build time (Trivy and ECR basic scanning). The image is rebuilt when upstream fixes are available. |
| `s3_bucket_kms_encryption` | SSE-S3 is enough for public media. KMS adds a cost per request and key policy work for OAC. |
| `s3_bucket_no_mfa_delete` | Only the root user can enable MFA Delete, and root is used for break-glass only |
| `s3_bucket_server_access_logging_enabled` | GuardDuty S3 Protection watches data access. Access logs add storage cost. |
| `s3_bucket_cross_region_replication` | The region lock SCP blocks every region except eu-west-2 |
| `s3_bucket_event_notifications_enabled`, `s3_bucket_lifecycle_enabled`, `s3_bucket_object_lock` | Not needed for replaceable portfolio media |

## Deferred

| Finding | Reason | When |
|---|---|---|
| `ec2_ebs_volume_snapshots_exists`, `ec2_ebs_volume_protected_by_backup_plan` | The Postgres data lives only on the instance's volume. Daily snapshots kept for 7 days cost very little. | Terraform phase |
| `cloudfront_distributions_custom_ssl_certificate`, `cloudfront_distributions_pqc_tls_enabled` | Not possible with the default `*.cloudfront.net` certificate, which also fixes the minimum TLS version | When a custom domain is added |
| `cloudfront_distributions_origin_traffic_encrypted` | Traffic from CloudFront to the VPC origin stays inside AWS and reaches a private subnet, never the internet. Encrypting it needs a certificate on the instance. | When a custom domain is added |
| `cloudfront_distributions_using_waf` | A pay-as-you-go web ACL is planned. The CloudFront free flat-rate plan cannot be used because it does not support VPC origins or custom policies. | Phase 9.8 (optional) |

## Lessons

- **A scanner flags patterns, not intent.** The PortfolioAdmin finding matched a known escalation pattern (`ssm:StartSession`), but the policy blocks the risky part. Reading the policy, not just the finding, is what decides it.
- **Some findings only make sense with a custom domain.** Three CloudFront findings share one cause: the default certificate. They are grouped so they can be closed together.
