FROM python:3.14-alpine AS builder

ENV PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build toolchain & headers for native extensions
RUN apk add --no-cache \
    build-base \
    cargo \
    curl \
    git \
    libffi-dev \
    openssl-dev \
    pkgconf \
    postgresql-dev \
    rust \
    zlib-dev

WORKDIR /tmp/build
COPY requirements.txt ./

# Install Python dependencies into a reusable prefix
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install --no-compile --root /install -r requirements.txt && \
    native_dir=/install/usr/local/lib/python3.14/site-packages/osu_native_py/native/bin && \
    test -f "$native_dir/linux-x64/osu.Native.so" && \
    rm -rf "$native_dir/osx-arm64" "$native_dir/win-x64"

FROM python:3.14-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Minimal runtime libs for compiled wheels
RUN apk add --no-cache \
    ca-certificates \
    gcompat \
    icu-libs \
    libffi \
    libstdc++ \
    openssl \
    postgresql-libs \
    zlib

# Reuse site-packages & console entry points from builder
COPY --from=builder /install/usr/local /usr/local

WORKDIR /bot
COPY . .

# Byte-compile for faster cold start and verify native loading
RUN test -r /usr/local/lib/python3.14/site-packages/osu_native_py/native/bin/linux-x64/osu.Native.so && \
    python -c 'from osu_native_py.native import LIB_PATH; assert LIB_PATH.is_file(), LIB_PATH' && \
    python -m compileall -q /usr/local/lib/python3.14/site-packages app main.py

STOPSIGNAL SIGINT
CMD ["python", "main.py"]
