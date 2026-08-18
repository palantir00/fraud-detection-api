# Base image: Python 3.12, "slim" variant (no extra system tooling).
FROM python:3.12-slim

# PYTHONDONTWRITEBYTECODE: skip .pyc files inside the container
# PYTHONUNBUFFERED: logs go straight to stdout instead of sitting in a buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Copy the dependency list first, install, and only then copy the code.
# This way a code change does not invalidate the layer with installed
# packages, so rebuilds take seconds instead of minutes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Do not run as root: a compromised app then has fewer privileges.
RUN useradd --create-home appuser && chown -R appuser:appuser /code
USER appuser

EXPOSE 8000

# 0.0.0.0 rather than 127.0.0.1: the container must listen on all
# interfaces, otherwise traffic from the host never reaches it.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
