#!/bin/bash
# ============================================
# AI Rescue USB - Build System
# Builds the bootable ISO from scratch
# ============================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_ROOT/build"
ISO_ROOT="$BUILD_DIR/iso_root"
OUTPUT_DIR="$PROJECT_ROOT/output"
CACHE_DIR="$PROJECT_ROOT/cache"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ============================================
# Configuration
# ============================================
ALPINE_VERSION="3.21"
ALPINE_MIRROR="https://dl-cdn.alpinelinux.org/alpine"
KERNEL_FLAVOR="lts"
ARCH="x86_64"
ISO_NAME="ai-rescue-usb"
ISO_VERSION="1.0.0"

# ============================================
# Stage 1: Download Alpine base
# ============================================
stage1_download_base() {
    log_info "Stage 1: Downloading Alpine Linux base..."

    mkdir -p "$CACHE_DIR" "$ISO_ROOT"

    local ALPINE_URL="$ALPINE_MIRROR/v${ALPINE_VERSION}/releases/${ARCH}"
    local ALPINE_TARBALL="alpine-minirootfs-${ALPINE_VERSION}.0-${ARCH}.tar.gz"

    if [ ! -f "$CACHE_DIR/$ALPINE_TARBALL" ]; then
        log_info "Downloading Alpine minirootfs..."
        wget -q --show-progress "$ALPINE_URL/$ALPINE_TARBALL" -O "$CACHE_DIR/$ALPINE_TARBALL"
        wget -q --show-progress "$ALPINE_URL/$ALPINE_TARBALL.sha256" -O "$CACHE_DIR/$ALPINE_TARBALL.sha256"
    fi

    log_info "Verifying checksum..."
    (cd "$CACHE_DIR" && sha256sum -c "$ALPINE_TARBALL.sha256")

    log_info "Extracting rootfs..."
    tar xzf "$CACHE_DIR/$ALPINE_TARBALL" -C "$ISO_ROOT"

    log_ok "Stage 1 complete"
}

# ============================================
# Stage 2: Install packages
# ============================================
stage2_install_packages() {
    log_info "Stage 2: Installing packages..."

    # Setup chroot DNS
    cp /etc/resolv.conf "$ISO_ROOT/etc/resolv.conf"

    # Core packages
    local PACKAGES=(
        # Kernel & boot
        "linux-${KERNEL_FLAVOR}"
        "linux-firmware"
        "efibootmgr"
        "grub-efi"
        "grub-bios"
        "syslinux"

        # System
        "alpine-base"
        "openrc"
        "busybox-openrc"
        "eudev"

        # Filesystem tools
        "ntfs-3g" "ntfs-3g-progs"
        "dosfstools" "exfatprogs"
        "e2fsprogs" "xfsprogs"
        "btrfs-progs" "zfs"
        "parted" "gdisk"
        "lvm2" "mdadm"
        "cryptsetup"

        # Hardware detection
        "pciutils" "usbutils"
        "lshw" "dmidecode"
        "hwinfo"
        "smartmontools"
        "hdparm" "nvme-cli"

        # Network
        "iproute2" "iw" "wpa_supplicant"
        "networkmanager" "networkmanager-wifi"
        "dhcpcd" "curl" "wget"

        # Python AI Core
        "python3" "py3-pip"
        "python3-dev"
        "py3-numpy"

        # Audio (voice)
        "alsa-utils" "pulseaudio"
        "sox"

        # Display
        "xorg-server" "xinit"
        "openbox" "tint2"
        "chromium"

        # Utilities
        "bash" "sudo"
        "tmux" "screen"
        "rsync" "pv"
        "testdisk" "ddrescue"
        "partclone" "partimage"
        "fsarchiver"
        "grub" "os-prober"
        "sysbench"

        # Security
        "openssl" "gnupg"
        "tpm2-tools"

        # Development (gcc+g++ needed to build llama-cpp-python from source —
        # musl/Alpine has no prebuilt wheel, unlike glibc Linux/Windows/macOS)
        "git" "make" "gcc" "g++" "cmake"
    )

    # Mount pseudo filesystems for chroot
    mount -t proc proc "$ISO_ROOT/proc"
    mount -t sysfs sys "$ISO_ROOT/sys"
    mount -t devtmpfs dev "$ISO_ROOT/dev"

    # Setup APK repos
    cat > "$ISO_ROOT/etc/apk/repositories" << EOF
$ALPINE_MIRROR/v${ALPINE_VERSION}/main
$ALPINE_MIRROR/v${ALPINE_VERSION}/community
$ALPINE_MIRROR/v${ALPINE_VERSION}/testing
EOF

    # Install in chroot
    chroot "$ISO_ROOT" /sbin/apk update
    for pkg in "${PACKAGES[@]}"; do
        log_info "Installing: $pkg"
        chroot "$ISO_ROOT" /sbin/apk add --no-cache "$pkg" || log_warn "Failed to install $pkg (continuing)"
    done

    # Cleanup
    umount -l "$ISO_ROOT/proc" "$ISO_ROOT/sys" "$ISO_ROOT/dev" 2>/dev/null || true

    log_ok "Stage 2 complete"
}

# ============================================
# Stage 3: Install AI Rescue components
# ============================================
stage3_install_ai_rescue() {
    log_info "Stage 3: Installing AI Rescue components..."

    # Copy AI Core
    mkdir -p "$ISO_ROOT/opt/ai-rescue"
    cp -r "$PROJECT_ROOT/ai_core" "$ISO_ROOT/opt/ai-rescue/"
    cp -r "$PROJECT_ROOT/agents" "$ISO_ROOT/opt/ai-rescue/"
    cp -r "$PROJECT_ROOT/detection" "$ISO_ROOT/opt/ai-rescue/"
    cp -r "$PROJECT_ROOT/security" "$ISO_ROOT/opt/ai-rescue/"
    cp -r "$PROJECT_ROOT/utils" "$ISO_ROOT/opt/ai-rescue/"
    cp -r "$PROJECT_ROOT/ui" "$ISO_ROOT/opt/ai-rescue/"
    cp "$PROJECT_ROOT/requirements.txt" "$ISO_ROOT/opt/ai-rescue/"
    cp "$PROJECT_ROOT/requirements-llm.txt" "$ISO_ROOT/opt/ai-rescue/" 2>/dev/null || true

    # Local LLM model (opt-in: only if the builder pre-downloaded one into
    # models/ — see README. Without it, ai_core/engine.py runs rule-based.)
    mkdir -p "$ISO_ROOT/opt/ai-rescue/models"
    if compgen -G "$PROJECT_ROOT/models/*.gguf" > /dev/null; then
        cp "$PROJECT_ROOT"/models/*.gguf "$ISO_ROOT/opt/ai-rescue/models/"
        log_ok "Bundled LLM model(s) copied into the ISO"
    else
        log_warn "No .gguf model found in models/ — ISO will run in rule-based mode"
    fi

    # Install Python dependencies (llama-cpp-python compiles from source here —
    # gcc/g++/cmake were installed in stage2 for exactly this)
    chroot "$ISO_ROOT" /usr/bin/pip3 install -r /opt/ai-rescue/requirements.txt
    if [ -f "$ISO_ROOT/opt/ai-rescue/requirements-llm.txt" ]; then
        chroot "$ISO_ROOT" /usr/bin/pip3 install -r /opt/ai-rescue/requirements-llm.txt || \
            log_warn "llama-cpp-python failed to build — falling back to rule-based mode on this ISO"
    fi

    # Copy configuration
    mkdir -p "$ISO_ROOT/etc/ai-rescue"
    cp "$PROJECT_ROOT/project.toml" "$ISO_ROOT/etc/ai-rescue/config.toml"

    # Copy init scripts
    cp "$PROJECT_ROOT/system/initramfs/init" "$ISO_ROOT/opt/ai-rescue/init.sh"
    chmod +x "$ISO_ROOT/opt/ai-rescue/init.sh"

    # Setup services
    mkdir -p "$ISO_ROOT/etc/init.d"
    cp "$PROJECT_ROOT/system/configs/ai-rescue-service" "$ISO_ROOT/etc/init.d/ai-rescue"
    chmod +x "$ISO_ROOT/etc/init.d/ai-rescue"

    log_ok "Stage 3 complete"
}

# ============================================
# Stage 4: Configure system
# ============================================
stage4_configure_system() {
    log_info "Stage 4: Configuring system..."

    # Hostname
    echo "ai-rescue" > "$ISO_ROOT/etc/hostname"

    # FSTAB
    cat > "$ISO_ROOT/etc/fstab" << EOF
tmpfs /tmp tmpfs defaults,noatime 0 0
tmpfs /var/log tmpfs defaults,noatime 0 0
EOF

    # Network
    cat > "$ISO_ROOT/etc/network/interfaces" << EOF
auto lo
iface lo inet loopback
EOF

    # Auto-login
    mkdir -p "$ISO_ROOT/etc/conf.d"
    cat > "$ISO_ROOT/etc/conf.d/agetty" << EOF
# Auto login
agetty_options="--autologin root --noclear"
EOF

    # Motd
    cat > "$ISO_ROOT/etc/motd" << 'EOF'

    ╔══════════════════════════════════════════╗
    ║          🤖 AI RESCUE USB v1.0          ║
    ║   Le technicien informatique universel  ║
    ║              dans une clé USB           ║
    ╚══════════════════════════════════════════╝

    Branchez-vous sur http://localhost:8080
    ou dites "ai-rescue" pour parler à l'IA.

EOF

    # Enable services
    chroot "$ISO_ROOT" /sbin/rc-update add ai-rescue default
    chroot "$ISO_ROOT" /sbin/rc-update add networkmanager default
    chroot "$ISO_ROOT" /sbin/rc-update add udev sysinit
    chroot "$ISO_ROOT" /sbin/rc-update add alsa default

    log_ok "Stage 4 complete"
}

# ============================================
# Stage 5: Build bootloader
# ============================================
stage5_build_bootloader() {
    log_info "Stage 5: Building bootloader..."

    mkdir -p "$ISO_ROOT/boot/grub"

    # GRUB config
    cat > "$ISO_ROOT/boot/grub/grub.cfg" << 'EOF'
set timeout=5
set default=0

menuentry "AI Rescue USB - RAM Mode (Recommended)" {
    linux /boot/vmlinuz-lts root=/dev/ram0 ro quiet loglevel=3 \
        ai_rescue.ram_mode=1 ai_rescue.persistence=0
    initrd /boot/initramfs-lts
}

menuentry "AI Rescue USB - With Persistence" {
    linux /boot/vmlinuz-lts root=/dev/ram0 ro quiet loglevel=3 \
        ai_rescue.ram_mode=1 ai_rescue.persistence=1
    initrd /boot/initramfs-lts
}

menuentry "AI Rescue USB - Install to Disk" {
    linux /boot/vmlinuz-lts root=/dev/ram0 ro quiet loglevel=3 \
        ai_rescue.install_mode=1
    initrd /boot/initramfs-lts
}

menuentry "AI Rescue USB - Safe Mode (VESA)" {
    linux /boot/vmlinuz-lts root=/dev/ram0 ro nomodeset quiet loglevel=3 \
        ai_rescue.ram_mode=1 ai_rescue.safe_graphics=1
    initrd /boot/initramfs-lts
}

menuentry "AI Rescue USB - Terminal Only" {
    linux /boot/vmlinuz-lts root=/dev/ram0 ro quiet loglevel=3 \
        ai_rescue.ram_mode=1 ai_rescue.no_ui=1
    initrd /boot/initramfs-lts
}

menuentry "Memory Test (memtest86+)" {
    linux /boot/memtest86+/memtest.bin
}
EOF

    # SYSLINUX for BIOS
    mkdir -p "$ISO_ROOT/boot/syslinux"
    cat > "$ISO_ROOT/boot/syslinux/syslinux.cfg" << 'EOF'
DEFAULT ai-rescue
PROMPT 0
TIMEOUT 50

LABEL ai-rescue
    MENU LABEL AI Rescue USB - RAM Mode
    LINUX /boot/vmlinuz-lts
    INITRD /boot/initramfs-lts
    APPEND root=/dev/ram0 ro quiet ai_rescue.ram_mode=1

LABEL persistence
    MENU LABEL AI Rescue USB - Persistence Mode
    LINUX /boot/vmlinuz-lts
    INITRD /boot/initramfs-lts
    APPEND root=/dev/ram0 ro quiet ai_rescue.persistence=1

LABEL safe
    MENU LABEL AI Rescue USB - Safe Mode
    LINUX /boot/vmlinuz-lts
    INITRD /boot/initramfs-lts
    APPEND root=/dev/ram0 ro nomodeset ai_rescue.safe_graphics=1
EOF

    # The syslinux package (installed in stage2) provides the actual boot
    # binaries under /usr/share/syslinux in the chroot — the .cfg above is
    # useless without them, and xorriso's -eltorito-boot needs isolinux.bin
    # to exist at the path we point it to.
    local SYSLINUX_DIR="$ISO_ROOT/usr/share/syslinux"
    if [ -d "$SYSLINUX_DIR" ]; then
        cp "$SYSLINUX_DIR/isolinux.bin" "$ISO_ROOT/boot/syslinux/" 2>/dev/null || \
            log_warn "isolinux.bin not found in $SYSLINUX_DIR"
        for f in ldlinux.c32 libcom32.c32 libutil.c32 menu.c32; do
            cp "$SYSLINUX_DIR/$f" "$ISO_ROOT/boot/syslinux/" 2>/dev/null || true
        done
    else
        log_warn "syslinux package files not found — BIOS boot image will be incomplete"
    fi

    log_ok "Stage 5 complete"
}

# ============================================
# Stage 6: Build ISO
# ============================================
stage6_build_iso() {
    log_info "Stage 6: Building ISO..."

    mkdir -p "$OUTPUT_DIR"

    local ISO_FILE="$OUTPUT_DIR/${ISO_NAME}-${ISO_VERSION}-${ARCH}.iso"

    # Build EFI image
    log_info "Creating EFI boot image..."
    dd if=/dev/zero of="$BUILD_DIR/efi.img" bs=1M count=50
    mkfs.vfat "$BUILD_DIR/efi.img"
    mmd -i "$BUILD_DIR/efi.img" ::EFI ::EFI/BOOT
    mcopy -i "$BUILD_DIR/efi.img" \
        "$ISO_ROOT/boot/grub/x86_64-efi/core.efi" ::EFI/BOOT/BOOTX64.EFI 2>/dev/null || true

    # Create ISO
    log_info "Creating ISO..."
    xorriso -as mkisofs \
        -iso-level 3 \
        -full-iso9660-filenames \
        -volid "AI_RESCUE" \
        -appid "AI Rescue USB" \
        -publisher "AI Rescue Team" \
        -preparer "AI Rescue Build System" \
        -eltorito-boot boot/syslinux/isolinux.bin \
        -eltorito-catalog boot/syslinux/boot.cat \
        -no-emul-boot \
        -boot-load-size 4 \
        -boot-info-table \
        -eltorito-alt-boot \
        -e "$BUILD_DIR/efi.img" \
        -no-emul-boot \
        -isohybrid-gpt-basdat \
        -isohybrid-mbr /usr/lib/syslinux/bios/isohdpfx.bin \
        -output "$ISO_FILE" \
        "$ISO_ROOT" 2>/dev/null || {
            # Fallback: simpler ISO creation
            log_warn "xorriso not available, using genisoimage..."
            genisoimage -r -J -l \
                -V "AI_RESCUE" \
                -b boot/syslinux/isolinux.bin \
                -c boot/syslinux/boot.cat \
                -no-emul-boot \
                -boot-load-size 4 \
                -boot-info-table \
                -o "$ISO_FILE" \
                "$ISO_ROOT"
        }

    log_ok "ISO created: $ISO_FILE"
    ls -lh "$ISO_FILE"
}

# ============================================
# Stage 7: Write to USB
# ============================================
stage7_write_usb() {
    local USB_DEVICE="${1:-}"

    if [ -z "$USB_DEVICE" ]; then
        log_error "Usage: $0 write-usb /dev/sdX"
        exit 1
    fi

    local ISO_FILE="$OUTPUT_DIR/${ISO_NAME}-${ISO_VERSION}-${ARCH}.iso"

    if [ ! -f "$ISO_FILE" ]; then
        log_error "ISO not found. Run build first."
        exit 1
    fi

    log_warn "============================================"
    log_warn " WRITING TO: $USB_DEVICE"
    log_warn " ALL DATA WILL BE DESTROYED!"
    log_warn "============================================"
    echo -n "Type 'YES' to confirm: "
    read -r confirm

    if [ "$confirm" != "YES" ]; then
        log_info "Aborted."
        exit 0
    fi

    log_info "Writing ISO to USB..."
    dd if="$ISO_FILE" of="$USB_DEVICE" bs=4M status=progress conv=fsync

    log_ok "USB written successfully!"
    log_info "You can now boot from this USB drive."
}

# ============================================
# Main
# ============================================
main() {
    echo ""
    echo "╔══════════════════════════════════════════╗"
    echo "║     AI Rescue USB - Build System v1.0    ║"
    echo "╚══════════════════════════════════════════╝"
    echo ""

    local COMMAND="${1:-build}"

    case "$COMMAND" in
        build)
            stage1_download_base
            stage2_install_packages
            stage3_install_ai_rescue
            stage4_configure_system
            stage5_build_bootloader
            stage6_build_iso
            log_ok "Build complete! ISO ready."
            ;;
        quick-build)
            # Skip download if already cached
            stage1_download_base
            stage3_install_ai_rescue
            stage4_configure_system
            stage5_build_bootloader
            stage6_build_iso
            ;;
        write-usb)
            stage7_write_usb "$2"
            ;;
        clean)
            log_info "Cleaning build directory..."
            rm -rf "$BUILD_DIR" "$OUTPUT_DIR"
            log_ok "Cleaned."
            ;;
        *)
            echo "Usage: $0 {build|quick-build|write-usb|clean}"
            echo ""
            echo "  build       - Full build from scratch"
            echo "  quick-build - Skip package reinstall"
            echo "  write-usb   - Write ISO to USB (/dev/sdX)"
            echo "  clean       - Remove build artifacts"
            ;;
    esac
}

main "$@"
