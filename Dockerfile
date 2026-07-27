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

# Copy build scripts
COPY docker/build.sh /usr/local/bin/build.sh
RUN chmod +x /usr/local/bin/build.sh

# Copy project files
COPY . /build/

# Default command
CMD ["/usr/local/bin/build.sh"]
