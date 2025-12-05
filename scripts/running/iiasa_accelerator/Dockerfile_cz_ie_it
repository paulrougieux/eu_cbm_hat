# ---- Base ----
FROM python:3.11-slim

# Avoid Python .pyc files & ensure unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ca-certificates \
    dos2unix \
 && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the project
COPY . .

# Ensure shell scripts are LF and executable
RUN if [ -d scripts ]; then \
      find scripts -type f -name "*.sh" -print0 | xargs -0 -r dos2unix; \
      find scripts -type f -name "*.sh" -print0 | xargs -0 -r chmod +x; \
    fi

# Default runtime environment hints (can be overridden by accli env)
ENV EU_CBM_DATA=/app/local_data/ \
    EU_CBM_AIDB=/app/local_data/eu_cbm_aidb/ \
    EU_CBM_OUT=/app/local_data/output

# Default command
CMD ["bash", "scripts/run_eucbm_hat.sh"]

