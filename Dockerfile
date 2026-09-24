# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# libpq-dev removed: psycopg2-binary / psycopg[binary] bundle libpq.
# If the build fails with a "pg_config" error, switch requirements.txt to psycopg2-binary.

# Apply any Debian security fixes released since the base image was published
RUN apt-get update && \
    apt-get upgrade -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Non-root runtime user with no login shell
RUN groupadd --system app && \
    useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app

# Dependencies first so this layer is cached between code changes
COPY requirements.txt .
RUN pip install -r requirements.txt

# Code stays owned by root, so the app user can read it but not modify it
COPY . .

# Static files are baked into the image and served by WhiteNoise.
# The dummy key only lets settings.py load during the build; it is never used at runtime.
# Media uploads go to S3, so nothing in the image needs to be writable.
RUN SECRET_KEY=collectstatic-build-only python manage.py collectstatic --noinput

# Writable media folder for local development uploads.
# In production uploads go to S3 and the container filesystem is read-only.
RUN mkdir -p /app/media && chown app:app /app/media

# Remove the package tooling from the runtime image: the app never installs anything
# at runtime, and pip bundles its own copies of libraries (such as msgpack) that
# scanners flag. No package manager also means less for an attacker to use.
RUN python -m pip uninstall -y pip setuptools

USER app

EXPOSE 8000

# 30s timeout matches CloudFront's default origin response timeout.
# /dev/shm for worker heartbeats so the container can run with a read-only filesystem.
CMD ["gunicorn", "portfolio_site.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--timeout", "30", \
     "--worker-tmp-dir", "/dev/shm", \
     "--no-control-socket", \
     "--access-logfile", "-"]