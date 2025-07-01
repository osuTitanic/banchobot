FROM python:3.13-slim-bookworm

# Installing/Updating system dependencies
RUN apt update -y && \
    apt install -y --no-install-recommends  \
    postgresql git curl \
    && rm -rf /var/lib/apt/lists/*

# Install rust toolchain
RUN curl -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /bot

# Install python dependencies
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Disable output buffering
ENV PYTHONUNBUFFERED=1

# Copy source code
COPY . .

CMD ["python3", "main.py"]