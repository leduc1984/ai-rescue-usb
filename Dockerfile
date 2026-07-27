FROM alpine:3.19

LABEL maintainer="AI Rescue USB Team"
LABEL description="Build environment for AI Rescue USB"

# Install build dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    gcc \
    musl-dev \
    linux-headers \
    bash \
    wget \
    curl \
    git \
    build-base \
    qemu-img \
    dosfstools \
    mtools \
    syslinux \
    xorriso \
    squashfs-tools \
    && rm -rf /var/cache/apk/*

# Install Python dependencies
COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# Create working directory
WORKDIR /build

# Copy project files (this includes build/build.sh, which computes its own
# location via BASH_SOURCE to find the project root — it must stay inside
# the copied tree, not be relocated to /usr/local/bin, or every relative
# path it builds (ai_core/, requirements.txt, system/...) resolves wrong).
COPY . /build/
RUN chmod +x /build/build/build.sh

# Default command
CMD ["/build/build/build.sh"]
