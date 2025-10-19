FROM python:3.14-slim AS builder

# Installing build dependencies
RUN apt update -y && \
    apt install -y --no-install-recommends  \
    postgresql-client git curl build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install rust toolchain
RUN curl -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
ENV PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

WORKDIR /bot

# Install python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.14-slim

# Copy installed Python packages from builder
COPY --from=builder /usr/local /usr/local

# Disable output buffering
ENV PYTHONUNBUFFERED=1

# Copy source code
WORKDIR /bot
COPY . .

# Generate __pycache__ directories
ENV PYTHONDONTWRITEBYTECODE=1
RUN python -m compileall -q app

STOPSIGNAL SIGINT
CMD ["python3", "main.py"]