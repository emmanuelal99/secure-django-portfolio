#!/usr/bin/env bash
# Opens an SSM tunnel to the admin container on the current portfolio instance.
# Usage: ./admin-tunnel.sh   then browse to http://localhost:8001/dashboard/login/
set -euo pipefail

PROFILE="dev"

aws sso login --profile "$PROFILE"

ID=$(aws ec2 describe-instances --profile "$PROFILE" \
  --filters "Name=tag:Name,Values=portfolio" "Name=instance-state-name,Values=running" \
  --query "Reservations[].Instances[].InstanceId" --output text)

if [ -z "$ID" ]; then
  echo "No running instance tagged Name=portfolio found." >&2
  exit 1
fi

echo "Tunnel to $ID open. Browse to http://localhost:8001/dashboard/login/ (Ctrl+C to close)"

aws ssm start-session --profile "$PROFILE" --target "$ID" \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["8001"],"localPortNumber":["8001"]}'