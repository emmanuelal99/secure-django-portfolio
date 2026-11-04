#!/usr/bin/env bash
# Builds .env and .env.db on the EC2 instance from SSM Parameter Store,
# using the instance role - no secrets in Git, the image, or compose files.
#
# Create these parameters first (alphanumeric values avoid quoting issues):
#   /portfolio/prod/django_secret_key   SecureString
#   /portfolio/prod/db_password         SecureString
#   /portfolio/prod/cloudfront_domain   String  (e.g. d1234abcd.cloudfront.net)
#   /portfolio/prod/media_bucket        String  (the private S3 bucket for uploads)

set -euo pipefail
umask 077   # Files are created readable by the owner only (mode 600)

REGION="eu-west-2"
PREFIX="/portfolio/prod"

get() {
  aws ssm get-parameter --region "$REGION" --name "$PREFIX/$1" \
    --with-decryption --query Parameter.Value --output text
}

DB_PASSWORD="$(get db_password)"
CLOUDFRONT_DOMAIN="$(get cloudfront_domain)"

cat > .env <<EOF
SECRET_KEY=$(get django_secret_key)
DEBUG=False
ALLOWED_HOSTS=${CLOUDFRONT_DOMAIN}
CSRF_TRUSTED_ORIGINS=https://${CLOUDFRONT_DOMAIN}
ENABLE_ADMIN=False
TUNNEL_MODE=False
USE_POSTGRES=True
DB_NAME=portfolio_db
DB_USER=portfolio_app
DB_PASSWORD=${DB_PASSWORD}
DB_HOST=db
DB_PORT=5432
MEDIA_BUCKET=$(get media_bucket)
CLOUDFRONT_DOMAIN=${CLOUDFRONT_DOMAIN}
AWS_REGION=${REGION}
EOF

cat > .env.db <<EOF
POSTGRES_DB=portfolio_db
POSTGRES_USER=portfolio_app
POSTGRES_PASSWORD=${DB_PASSWORD}
EOF

echo "Wrote .env and .env.db (mode 600)"
