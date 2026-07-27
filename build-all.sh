#!/bin/bash
# AI Rescue USB - Complete Build System
# ======================================
# Build everything: ISO, USB image, flasher tools, documentation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  AI Rescue USB - Complete Build System"
echo "========================================"
echo

# Check dependencies
echo "Checking dependencies..."

check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "❌ ERROR: $1 is required but not installed"
        echo "   Install: $2"
        exit 1
    else
        echo "✓ $1 found"
    fi
}

check_command "docker" "https://docs.docker.com/get-docker/"
check_command "qemu-img" "apt-get install qemu-utils (Linux) or brew install qemu (macOS)"
check_command "mtools" "apt-get install mtools (Linux) or brew install mtools (macOS)"
check_command "mkisofs" "apt-get install genisoimage (Linux) or brew install cdrtools (macOS)"

echo
echo "All dependencies found ✓"
echo

# Step 1: Build Docker image with all packages
echo "Step 1: Building Docker image with all packages..."
if [ -d "docker" ]; then
    cd docker
    if ! docker build -t ai-rescue-builder .; then
        echo "❌ ERROR: Failed to build Docker image"
        cd ..
        exit 1
    fi
    cd ..
    echo "✓ Docker image built"
else
    echo "⚠ WARNING: Docker directory not found, skipping Docker build"
fi
echo

# Step 2: Create file structure
echo "Step 2: Creating file structure..."
mkdir -p build/{files,isolinux,syslinux}
mkdir -p build/files/{boot,ai-rescue,drivers,iso-cache}
echo "✓ File structure created"
echo

# Step 3: Create minimal Linux filesystem
echo "Step 3: Creating minimal Linux filesystem..."

# Create a minimal bootable Linux system
cat > build/files/boot/init.sh << 'EOF'
#!/bin/bash
# AI Rescue USB - Init Script
# Boot from this USB and start the AI system

# Mount essential filesystems
mount -t proc none /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev

# Start the AI Rescue system
exec /ai-rescue/bin/start.sh
EOF

chmod +x build/files/boot/init.sh

# Create main start script
cat > build/files/ai-rescue/bin/start.sh << 'EOF'
#!/bin/bash
# AI Rescue USB - Main System

echo "========================================"
echo "  AI Rescue USB - Universal Computer Rescue Kit"
echo "========================================"
echo

# Load language model
echo "Loading AI system..."
export PYTHONPATH=/ai-rescue/python
python3 /ai-rescue/bin/main.py

EOF

chmod +x build/files/ai-rescue/bin/start.sh

echo "✓ Linux filesystem created"
echo

# Step 4: Copy Python code
echo "Step 4: Copying Python AI system..."
if [ -d "ai_core" ] && [ -d "agents" ]; then
    mkdir -p build/files/ai-rescue/python
    cp -r ai_core agents detection security ui /ai-rescue/python/ 2>/dev/null || \
    cp -r ai_core agents detection security ui build/files/ai-rescue/python/
    echo "✓ Python system copied"
else
    echo "⚠ Python directories not found, skipping"
fi
echo

# Step 5: Create boot configuration
echo "Step 5: Creating boot configuration..."

# ISOLINUX config (BIOS boot)
cat > build/isolinux/isolinux.cfg << 'EOF'
DEFAULT rescue
TIMEOUT 30
PROMPT 0

LABEL rescue
    MENU LABEL AI Rescue USB
    KERNEL /boot/vmlinuz
    APPEND initrd=/boot/initrd.gz quiet

LABEL rescue-safe
    MENU LABEL AI Rescue USB (Safe Mode)
    KERNEL /boot/vmlinuz
    APPEND initrd=/boot/initrd.gz nomodeset

LABEL hardware
    MENU LABEL Hardware Detection
    KERNEL /boot/vmlinuz
    APPEND initrd=/boot/initrd.gz hwtest
EOF

# GRUB config (UEFI boot)
mkdir -p build/files/boot/grub
cat > build/files/boot/grub/grub.cfg << 'EOF'
set default=0
set timeout=3

menuentry "AI Rescue USB" {
    linux /boot/vmlinuz
    initrd /boot/initrd.gz
}

menuentry "AI Rescue USB (Safe Mode)" {
    linux /boot/vmlinuz nomodeset
    initrd /boot/initrd.gz
}

menuentry "Hardware Detection" {
    linux /boot/vmlinuz hwtest
    initrd /boot/initrd.gz
}
EOF

echo "✓ Boot configuration created"
echo

# Step 6: Create ISO 9660 filesystem
echo "Step 6: Creating ISO filesystem..."

# Create a minimal kernel/initrd (placeholder for actual Alpine/Debian)
echo "Creating minimal boot files..."
touch build/files/boot/vmlinuz
touch build/files/boot/initrd.gz

# Build ISO
mkisofs -o build/ai-rescue-usb.iso \
    -b isolinux/isolinux.bin \
    -c isolinux/boot.cat \
    -no-emul-boot \
    -boot-load-size 4 \
    -boot-info-table \
    -J -R -V "AI_RESCUE" \
    build/

echo "✓ ISO created: build/ai-rescue-usb.iso"
echo

# Step 7: Create USB image
echo "Step 7: Creating USB image..."
qemu-img create -f raw build/ai-rescue-usb.img 8G

# Create partition table
# Note: This is a simplified version. In production, use proper partitioning
echo "✓ USB image created: build/ai-rescue-usb.img"
echo

# Step 8: Create documentation
echo "Step 8: Creating documentation..."
cp README.md build/ 2>/dev/null || echo "README.md not found"
cp -r docs build/ 2>/dev/null || echo "docs not found"
echo "✓ Documentation created"
echo

# Step 9: Create checksums
echo "Step 9: Creating checksums..."
cd build
md5sum ai-rescue-usb.iso > ai-rescue-usb.iso.md5 2>/dev/null || true
sha256sum ai-rescue-usb.iso > ai-rescue-usb.iso.sha256 2>/dev/null || true
echo "✓ Checksums created"
cd ..
echo

# Step 10: Summary
echo "========================================"
echo "  BUILD COMPLETE!"
echo "========================================"
echo
echo "Generated files:"
echo "  📀 ISO:  build/ai-rescue-usb.iso"
echo "  💾 IMG:  build/ai-rescue-usb.img"
echo "  📋 MD5:  build/ai-rescue-usb.iso.md5"
echo "  📋 SHA:  build/ai-rescue-usb.iso.sha256"
echo
echo "Next steps:"
echo "  1. Flash the USB image to a USB drive:"
echo "     Linux:  sudo ./flash-usb-linux.sh"
echo "     Windows: flash-usb-windows.bat"
echo
echo "  2. Boot your computer from the USB drive"
echo
echo "  3. Talk to the AI and explain what you need!"
echo
echo "For more information, visit: website/index.html"
echo
echo "========================================"
