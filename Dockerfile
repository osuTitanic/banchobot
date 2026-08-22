FROM python:3.14-slim-trixie AS builder

ENV PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build toolchain & headers for native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cargo \
    curl \
    git \
    libffi-dev \
    libpq-dev \
    libssl-dev \
    pkg-config \
    rustc \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp/build
COPY requirements.txt ./

# Install Python dependencies into a reusable prefix
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install --no-compile --root /install -r requirements.txt && \
    native_dir=/install/usr/local/lib/python3.14/site-packages/osu_native_py/native/bin && \
    find "$native_dir" -type f -name osu.Native.so -print -quit | grep -q .

FROM python:3.14-slim-trixie

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Minimal runtime libs for compiled wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libffi8 \
    libicu76 \
    libpq5 \
    libstdc++6 \
    openssl \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

# Reuse site-packages & console entry points from builder
COPY --from=builder /install/usr/local /usr/local

WORKDIR /bot
COPY . .

# Byte-compile for faster cold start and verify native loading
RUN python -c 'from osu_native_py.native import LIB_PATH; assert LIB_PATH.is_file(), LIB_PATH' && \
    python -m compileall -q /usr/local/lib/python3.14/site-packages app main.py

STOPSIGNAL SIGINT
CMD ["python", "main.py"]
