# Evidence

Screenshots of the portfolio's security controls working. Account IDs, bucket names, ARNs, the admin username and sign-in links are covered with solid boxes.

The architecture is shown in [architecture.png](../architecture.png). Problems found while deploying are in [findings.md](../findings.md). Platform screenshots (accounts, guardrails, GuardDuty, Prowler scans) are in the [landing zone evidence](https://github.com/emmanuelal99/aws-landing-zone/blob/main/docs/evidence/README.md).

| Section | Shows |
|---|---|
| [Live site: guest and admin](#live-site-guest-and-admin) | What a visitor can reach, and how the admin gets in |
| [Edge protection: CloudFront](#edge-protection-cloudfront) | HTTPS, security headers, the admin block and the private origin |
| [Server and network](#server-and-network) | No public IP, one inbound rule, hardened instance, no outbound internet |
| [Admin isolation on the server](#admin-isolation-on-the-server) | The admin listens on localhost only |
| [Secrets](#secrets) | Encrypted parameters and root-only files |
| [Media bucket](#media-bucket) | Private bucket, readable only through CloudFront |
| [Instance role and permissions](#instance-role-and-permissions) | Least-privilege role and a scoped `PassRole` |
| [Container image](#container-image) | Immutable tags and vulnerability scanning |
| [Application code](#application-code) | Static analysis, Django deploy checks and login lockout |
| [Infrastructure as code](#infrastructure-as-code) | Terraform matches the live environment |

---

## Live site: guest and admin

![Guest home page](live-site-guest-home.png)
**Public site in a private browser window: only Projects and About are shown**

![Guest project list](live-site-guest-projects.png)
**Project images loaded from the private S3 bucket through CloudFront**

![Guest requests](guest-blocked-from-admin.png)
**Guest requests: HTTP redirected to HTTPS (301), admin and dashboard blocked (403), home page allowed (200)**

![Admin tunnel](admin-tunnel-sign-in.png)
**Admin: single sign-on, then a port forwarding tunnel to the instance**

![Django admin](django-admin-through-tunnel.png)
**Django admin, reached only at `localhost:8001` through the tunnel**

![Dashboard](dashboard-through-tunnel.png)
**Site dashboard through the tunnel: the Dashboard and Logout links appear only here**

---

## Edge protection: CloudFront

![Cache behaviours](cloudfront-behaviours.png)
**Cache behaviours: every path redirects HTTP to HTTPS and adds the security headers**

![Edge function](edge-function-403.png)
**Edge function that returns 403 for `/admin*` and `/dashboard*`**

![Security headers policy](security-headers-policy.png)
**Response headers policy: HSTS, nosniff, frame DENY and referrer policy**

![VPC origin](cloudfront-vpc-origin.png)
**VPC origin: CloudFront reaches the private instance on port 8000**

![Distribution settings](cloudfront-distribution-settings.png)
**Distribution settings checked from the command line**

> This also shows the known gaps: the default `*.cloudfront.net` certificate, a `TLSv1` minimum and no WAF. They are listed under "Not yet in place" in the README and deferred in [prowler-triage.md](../prowler-triage.md#deferred).

---

## Server and network

![Security group](security-group-cloudfront-only.png)
**The only inbound rule: port 8000 from CloudFront's VPC origin security group**

> No IP ranges or prefix lists are allowed. The second command confirms that the allowed group is CloudFront's own service security group.

![Instance summary](instance-private-subnet.png)
**Instance in the private subnet with no public IP address**

![Instance hardening](instance-hardening.png)
**IMDSv2 required with hop limit 2, no key pair, no public IP, encrypted gp3 volume, termination protection on**

![No NAT, site still up](no-nat-site-still-up.png)
**No NAT gateway and no Elastic IP, and the site still answers 200**

> The first two commands print nothing: there is no NAT gateway and no public IP address in the account. The server has no route to the internet, yet CloudFront still reaches it through the private VPC origin.

![Session after reboot](ssm-session-after-reboot.png)
**P-001: Session Manager working after a reboot once the NAT was back**

> The covered address is the NAT gateway's public IP. It is shown only to prove that outbound traffic left through the NAT, and the NAT was removed afterwards.

---

## Admin isolation on the server

![Containers and ports](containers-and-ports.png)
**Containers: web on port 8000, admin on `127.0.0.1:8001` only, database with no published port**

![Admin isolation check](admin-isolated-on-server.png)
**Port 8001 listens on localhost only, and the public container has no admin page (404)**

> The home page returned 500 here only because the database tables had not been created yet. They were created in the next step.

---

## Secrets

![Parameter Store](parameter-store-securestring.png)
**Django secret key stored as a SecureString, value hidden**

![Root-only secret files](secrets-root-only-files.png)
**Secrets written at deploy time to files only root can read (`-rw-------`)**

---

## Media bucket

![Bucket settings](media-bucket-settings.png)
**Block Public Access fully on, ACLs disabled (BucketOwnerEnforced), versioning on**

![Bucket policy](media-bucket-policy.png)
**Bucket policy: requests without HTTPS are denied**

![Regional S3 origin](s3-origin-regional-endpoint.png)
**P-002: S3 origin using the regional endpoint, with Origin Access Control**

---

## Instance role and permissions

![Instance role](instance-role-policies.png)
**Instance role: Session Manager access plus one inline policy for its own parameters, bucket and image**

![PassRole policy](developer-passrole-only.png)
**Developer permission set can pass only `portfolio-ec2-role`, and only to EC2**

---

## Container image

![ECR settings](ecr-repository-settings.png)
**ECR repository: immutable tags, scan on push, encrypted, and the image's scan results**

![ECR scan](ecr-image-scan.png)
**ECR scan of the deployed image: no critical findings**

> The image was also scanned with Trivy before it was pushed. Both results are triaged in [image-scan.md](../image-scan.md).

---

## Application code

![Bandit before](bandit-before.png)
**Bandit before the fix: `mark_safe` could allow cross-site scripting**

![Bandit after](bandit-after.png)
**Bandit after the fix: `format_html_join` escapes each value, no issues left**

![Django deploy check](django-deploy-check.png)
**Django `check --deploy`: no issues**

> The one warning left, HSTS preload, is silenced on purpose. A `*.cloudfront.net` address cannot be added to the browser preload list.

![Login lockout](axes-lockout-page.png)
**Login lockout after repeated failed attempts (django-axes), tested locally**

![Lockout log](axes-lockout-log.png)
**Server log: failed logins recorded, then the login page answers 429 Too Many Requests**

---

## Infrastructure as code

![Terraform plan](terraform-portfolio-no-changes.png)
**Terraform plan with the read-only role: no changes, 26 entries in state (20 resources and 6 data sources)**
