FROM python:3.13-slim-bookworm AS builder

# Installing build dependencies
RUN apt update -y && \
    apt install -y --no-install-recommends  \
    postgresql-client git curl \
    && rm -rf /var/lib/apt/lists/*

# Install rust toolchain
RUN curl -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /bot

# Install python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.13-slim-bookworm

# Copy installed Python packages from builder
COPY --from=builder /usr/local /usr/local

# Disable output buffering
ENV PYTHONUNBUFFERED=1

# Copy source code
COPY . .

# Generate __pycache__ directories
ENV PYTHONDONTWRITEBYTECODE=1
RUN python -m compileall -q app

STOPSIGNAL SIGINT
CMD ["python3", "main.py"]