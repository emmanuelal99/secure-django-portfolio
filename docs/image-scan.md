# Container image scan: portfolio:1.0

The image is scanned twice: with Trivy on the build machine before it is pushed, and by Amazon ECR when it arrives (scan on push).

## Results

| Scanner | Critical | High | Medium | Low |
|---|---|---|---|---|
| Trivy (before push) | 0 | 45 | – | – |
| Amazon ECR basic scan (on push) | 0 | 3 | 9 | 3 |

Only HIGH and CRITICAL findings were recorded from the Trivy run. The two scanners use different vulnerability databases and count repeated findings differently, so the numbers do not match.

## Trivy findings

- 0 CRITICAL, 45 HIGH, all in Debian base packages with no fix released yet.
- The 45 findings come from 9 distinct CVEs repeated across packages that share the same library.
- Python dependencies: 0 HIGH or CRITICAL.

## Why the remaining findings are accepted for now

- None are reachable in practice: the container runs as a non-root user, with all Linux capabilities dropped, `no-new-privileges`, and a read-only file system.
- systemd, Perl, terminal tools and SQLite are in the base image but are not used by the running app.

## Actions

- Rebuild with `--pull --no-cache` when Debian releases fixes, and push it as a new version tag (tags are immutable).
- Future improvement: a smaller base image (for example distroless or a minimal image) would remove most of these packages entirely.

**Evidence:** [ECR settings and scan results](evidence/README.md#container-image)
