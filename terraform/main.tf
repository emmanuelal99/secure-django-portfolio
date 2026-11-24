# Portfolio workload (Dev account)
#
# This project manages only the resources that exist for the portfolio app.
# The network (VPC, subnets, route tables, S3 endpoint) belongs to the landing
# zone and is only read here through data sources, never managed.
#
# Parameter Store values are deliberately not managed here: importing
# SecureString parameters would store the secrets in plain text in the state.

# ---------------------------------------------------------------------------
# Inputs read from AWS and from the landing zone
# ---------------------------------------------------------------------------

data "aws_caller_identity" "current" {}

# Owned by the landing zone. Found by tag, never managed here.
data "aws_vpc" "platform" {
  tags = { Name = "portfolio-vpc" }
}

data "aws_subnet" "private_a" {
  vpc_id = data.aws_vpc.platform.id
  tags   = { Name = "portfolio-private-a" }
}

# Created and managed by CloudFront for VPC origins in this VPC.
data "aws_security_group" "cloudfront_vpc_origins" {
  vpc_id = data.aws_vpc.platform.id
  name   = "CloudFront-VPCOrigins-Service-SG"
}

# AWS managed cache policies.
data "aws_cloudfront_cache_policy" "caching_disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_cache_policy" "caching_optimized" {
  name = "Managed-CachingOptimized"
}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = "eu-west-2"

  # Account regional namespace bucket name. Built from the account ID so the
  # number is not written in the code.
  media_bucket_name = "portfolio-media-${local.account_id}-${local.region}-an"

  # Origin ID created by the console when the distribution was built.
  # Kept as it is: changing an origin ID changes every behaviour that uses it.
  vpc_origin_id = "origin-ip-10-0-1-55.eu-west-2.compute.internal-mwtd8sc02oi"

  common_tags = {
    Project = "Portfolio"
    Env     = "Dev"
    Owner   = "Emmy"
  }
}

# ---------------------------------------------------------------------------
# Compute
# ---------------------------------------------------------------------------

resource "aws_security_group" "app" {
  name        = "portfolio-app-sg"
  description = "Portfolio Django app server. Inbound TCP on port 8000 from CloudFront only. No SSH. Outbound HTTPS only."
  vpc_id      = data.aws_vpc.platform.id

  ingress {
    description     = "Gunicorn from CloudFront only"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [data.aws_security_group.cloudfront_vpc_origins.id]
  }

  egress {
    description = "HTTPS to AWS services, ECR, OS updates"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "portfolio-app-sg" })
}

resource "aws_instance" "portfolio" {
  # Fixed AMI on purpose: a "latest AMI" lookup would replace the instance
  # every time Amazon publishes a new image.
  ami           = "ami-0d623184a69654e22"
  instance_type = "t4g.small"

  subnet_id                   = data.aws_subnet.private_a.id
  vpc_security_group_ids      = [aws_security_group.app.id]
  associate_public_ip_address = false
  iam_instance_profile        = aws_iam_instance_profile.ec2.name

  disable_api_termination = true
  ebs_optimized           = true
  monitoring              = false

  # IMDSv2 only. Hop limit 2 lets the containers reach the instance role.
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
    instance_metadata_tags      = "disabled"
  }

  credit_specification {
    cpu_credits = "standard"
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    iops                  = 3000
    throughput            = 125
    encrypted             = true
    delete_on_termination = true

    tags = merge(local.common_tags, { Name = "portfolio" })
  }

  tags = merge(local.common_tags, { Name = "portfolio" })
}

# ---------------------------------------------------------------------------
# Instance role
# ---------------------------------------------------------------------------

resource "aws_iam_role" "ec2" {
  name        = "portfolio-ec2-role"
  description = "Portfolio app server: SSM access, app parameters, media bucket, ECR pull"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_instance_profile" "ec2" {
  name = "portfolio-ec2-role"
  role = aws_iam_role.ec2.name
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "app_access" {
  name = "portfolio-app-access"
  role = aws_iam_role.ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadAppParameters"
        Effect   = "Allow"
        Action   = "ssm:GetParameter"
        Resource = "arn:aws:ssm:${local.region}:${local.account_id}:parameter/portfolio/prod/*"
      },
      {
        Sid      = "MediaBucketObjects"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = "${aws_s3_bucket.media.arn}/*"
      },
      {
        Sid      = "MediaBucketList"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.media.arn
      },
      {
        Sid      = "EcrLogin"
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        Sid      = "EcrPullPortfolioOnly"
        Effect   = "Allow"
        Action   = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:BatchCheckLayerAvailability"]
        Resource = aws_ecr_repository.portfolio.arn
      }
    ]
  })
}

# ---------------------------------------------------------------------------
# Container registry
# ---------------------------------------------------------------------------

resource "aws_ecr_repository" "portfolio" {
  name                 = "portfolio"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(local.common_tags, { Name = "portfolio" })
}

resource "aws_ecr_lifecycle_policy" "portfolio" {
  repository = aws_ecr_repository.portfolio.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Keep the 10 most recent images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = { type = "expire" }
      }
    ]
  })
}

# ---------------------------------------------------------------------------
# Media bucket (private, read through CloudFront OAC only)
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "media" {
  bucket           = local.media_bucket_name
  bucket_namespace = "account-regional"

  tags = merge(local.common_tags, { Name = "portfolio-media" })
}

resource "aws_s3_bucket_public_access_block" "media" {
  bucket = aws_s3_bucket.media.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "media" {
  bucket = aws_s3_bucket.media.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  rule {
    bucket_key_enabled       = true
    blocked_encryption_types = ["SSE-C"]

    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "media" {
  bucket = aws_s3_bucket.media.id

  versioning_configuration {
    status     = "Enabled"
    mfa_delete = "Disabled"
  }
}

resource "aws_s3_bucket_policy" "media" {
  bucket = aws_s3_bucket.media.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource  = [aws_s3_bucket.media.arn, "${aws_s3_bucket.media.arn}/*"]
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      },
      {
        Sid       = "AllowCloudFrontServicePrincipalReadOnly"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.media.arn}/*"
        # Built from the distribution, never typed by hand (finding P-002).
        Condition = { StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.portfolio.arn } }
      }
    ]
  })
}

# ---------------------------------------------------------------------------
# CloudFront
# ---------------------------------------------------------------------------

resource "aws_cloudfront_function" "block_admin" {
  name    = "portfolio-block-admin"
  runtime = "cloudfront-js-2.0"
  comment = "Returns 403 for /admin and /dashboard at the edge"

  code = chomp(<<-EOT
    function handler(event) {
      return {
        statusCode: 403,
        statusDescription: 'Forbidden',
        headers: { 'cache-control': { value: 'no-store' } }
      };
    }
  EOT
  )

  tags = local.common_tags

  # "publish" is not read back from AWS on import, so it would always show a
  # change. The function is already published (LIVE).
  lifecycle {
    ignore_changes = [publish]
  }
}

resource "aws_cloudfront_origin_access_control" "media" {
  name                              = "portfolio-media-oac"
  description                       = "Lets only the portfolio-site distribution read the private media bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_origin_request_policy" "django" {
  name    = "portfolio-django-origin"
  comment = "Forward Host and CloudFront-Forwarded-Proto to Django; all query strings; no cookies"

  cookies_config {
    cookie_behavior = "none"
  }

  headers_config {
    header_behavior = "whitelist"
    headers {
      items = ["CloudFront-Forwarded-Proto", "Host"]
    }
  }

  query_strings_config {
    query_string_behavior = "all"
  }
}

resource "aws_cloudfront_response_headers_policy" "security" {
  name    = "portfolio-security-headers"
  comment = "HSTS, nosniff, frame DENY, referrer policy"

  security_headers_config {
    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = true
      preload                    = false
      override                   = true
    }

    content_type_options {
      override = true
    }

    frame_options {
      frame_option = "DENY"
      override     = true
    }

    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }
  }
}

resource "aws_cloudfront_vpc_origin" "portfolio" {
  vpc_origin_endpoint_config {
    name                   = "portfolio-vpc-origin"
    arn                    = aws_instance.portfolio.arn
    http_port              = 8000
    https_port             = 443
    origin_protocol_policy = "http-only"

    # Not used with http-only. Kept as AWS set it, so the import makes no change.
    origin_ssl_protocols {
      items    = ["SSLv3", "TLSv1", "TLSv1.1", "TLSv1.2"]
      quantity = 4
    }
  }
}

resource "aws_cloudfront_distribution" "portfolio" {
  enabled         = true
  comment         = "Portfolio site: VPC origin (EC2) + S3 media via OAC"
  is_ipv6_enabled = true
  http_version    = "http2"
  price_class     = "PriceClass_All"

  # Django app on the private instance, reached through the VPC origin.
  origin {
    origin_id   = local.vpc_origin_id
    domain_name = aws_instance.portfolio.private_dns

    vpc_origin_config {
      vpc_origin_id            = aws_cloudfront_vpc_origin.portfolio.id
      origin_keepalive_timeout = 5
      origin_read_timeout      = 30
    }
  }

  # Private media bucket, read through OAC. Uses the regional S3 endpoint
  # (finding P-002: the global endpoint caused a 307 and a region error).
  origin {
    origin_id                = "portfolio-media"
    domain_name              = aws_s3_bucket.media.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.media.id
  }

  # Everything else goes to Django. GET and HEAD only, nothing cached.
  default_cache_behavior {
    target_origin_id           = local.vpc_origin_id
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.caching_disabled.id
    origin_request_policy_id   = aws_cloudfront_origin_request_policy.django.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
  }

  # Behaviours are matched in this order. The admin blocks must stay first.
  ordered_cache_behavior {
    path_pattern               = "/admin*"
    target_origin_id           = local.vpc_origin_id
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.caching_disabled.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.block_admin.arn
    }
  }

  ordered_cache_behavior {
    path_pattern               = "/dashboard*"
    target_origin_id           = local.vpc_origin_id
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.caching_disabled.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.block_admin.arn
    }
  }

  ordered_cache_behavior {
    path_pattern               = "/media/*"
    target_origin_id           = "portfolio-media"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.caching_optimized.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
  }

  ordered_cache_behavior {
    path_pattern               = "/static/*"
    target_origin_id           = local.vpc_origin_id
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.caching_optimized.id
    origin_request_policy_id   = aws_cloudfront_origin_request_policy.django.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # Default *.cloudfront.net certificate. A custom domain with an ACM
  # certificate is a deferred finding.
  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = merge(local.common_tags, { Name = "portfolio-site" })
}
