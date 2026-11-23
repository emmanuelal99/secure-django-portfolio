# Findings

Problems found while deploying the portfolio workload, with the cause, the fix and the lesson for each. Account IDs and resource IDs are replaced with placeholders.

## P-001: Session Manager not ready straight after the NAT is turned on

**What happened:** After `nat-on.sh` finished, `aws ssm start-session` failed with `TargetNotConnected`. At the same time, `aws ssm describe-instance-information` showed the instance as `Online`.

**Cause:** The SSM agent uses two separate connections:

| Connection | Used for |
|---|---|
| SSM (status pings) | The `Online` status |
| SSM Messages (session channel) | `start-session` and port forwarding |

When the NAT is removed, both connections drop. When it comes back, each one reconnects on its own retry timer, and the timer gets longer after each failed attempt. The status connection came back first, so the instance showed `Online` while sessions were still refused.

**Fix:** Rebooting the instance reset both connections. Sessions worked as soon as the agent was back.

**Evidence:**

```
$ aws ssm describe-instance-information ...
| <INSTANCE_ID> | Online | 2026-11-23T16:20:31 |

$ aws ssm start-session --target <INSTANCE_ID> ...
An error occurred (TargetNotConnected) when calling the StartSession operation: <INSTANCE_ID> is not connected.
```

**Lessons:**

- `Online` does not mean a session will work.
- After turning the NAT on, reboot the instance or wait a few minutes before starting a session.
- This cost comes with the on-demand NAT design. It is a few minutes of waiting in exchange for no NAT charge while the NAT is not needed.

## P-002: Media images did not load through CloudFront

**What happened:** Images uploaded through the admin page were saved to S3, but showed as broken on the public site. Two separate problems caused this, and they were found one after the other.

### Cause 1: the S3 origin used the global S3 endpoint

The CloudFront S3 origin was set to `<BUCKET>.s3.amazonaws.com`, the global endpoint. CloudFront signed its requests (through OAC) for `eu-west-2`, but the global endpoint answered from `us-east-1`:

```
HTTP/2 307
server: AmazonS3

<Error><Code>AuthorizationHeaderMalformed</Code><Message>The authorization header is malformed; the region 'eu-west-2' is wrong; expecting 'us-east-1'</Message></Error>
```

CloudFront does not follow redirects from an origin, so the image never loaded.

**Fix:** The origin domain was changed to the regional endpoint, `<BUCKET>.s3.eu-west-2.amazonaws.com`. The OAC and the origin name stayed the same.

### Cause 2: one wrong character in the bucket policy

After the first fix, the response changed to `403 AccessDenied` from S3. The other possible causes were ruled out first:

| Check | Result | Ruled out |
|---|---|---|
| `aws s3 ls` on the object path | The file existed at the expected key | Wrong path |
| `aws s3api get-bucket-encryption` | `AES256` (SSE-S3) | KMS blocking CloudFront |
| The bucket policy's `AWS:SourceArn` | The distribution ID was typed with a zero (`0`) where the real ID has the letter `O` | **This was the cause** |

**Fix:** The policy was corrected using the ID returned by `aws cloudfront list-distributions`, rather than the ID typed by hand.

### Final state

```
$ curl -sI "https://<CLOUDFRONT_DOMAIN>/media/projects/..." | head -1
HTTP/2 200

$ curl -sI "https://<BUCKET>.s3.eu-west-2.amazonaws.com/media/projects/..." | head -1
HTTP/1.1 403 Forbidden
```

Images are served through CloudFront, and the bucket cannot be read directly.

**Lessons:**

- **Use the regional S3 endpoint for CloudFront origins.** In Terraform, use `bucket_regional_domain_name`, not `bucket_domain_name`.
- **Never type resource IDs by hand.** Copy them from the CLI or the console. In Terraform, reference the distribution's `.arn` so the ID cannot be mistyped.
- **Read the response, not just the status code.** The `server` header showed who answered (S3, not Django or CloudFront), and the XML error code named the cause each time.
- **The policy failed closed.** While the ARN was wrong, nobody could read the files, including the distribution itself. The mistake made access stricter, not more open.
