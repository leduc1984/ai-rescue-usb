#!/bin/bash
# AI Rescue USB - Test Script
# ===========================
# Test the AI Rescue USB system in QEMU without burning to USB

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  AI Rescue USB - Test Script"
echo "========================================"
echo

# Check if ISO exists
if [ ! -f "build/ai-rescue-usb.iso" ]; then
    echo "❌ ERROR: ISO not found at build/ai-rescue-usb.iso"
    echo "Please run ./build-all.sh first to create the ISO."
    exit 1
fi

echo "✓ Found ISO: build/ai-rescue-usb.iso"
echo

# Check if QEMU is installed
if ! command -v qemu-system-x86_64 &> /dev/null; then
    echo "❌ ERROR: QEMU not found"
    echo "Install QEMU:"
    echo "  Ubuntu/Debian: sudo apt-get install qemu-system-x86"
    echo "  macOS: brew install qemu"
    echo "  Windows: https://www.qemu.org/download/#windows"
    exit 1
fi

echo "✓ QEMU found"
echo

# Create a temporary disk image for testing
echo "Creating temporary test disk (10GB)..."
qemu-img create -f qcow2 /tmp/ai-rescue-test-disk.qcow2 10G
echo "✓ Test disk created"
echo

# Launch QEMU
echo "========================================"
echo "  Starting QEMU Test Environment"
echo "========================================"
echo
echo "You are now booting AI Rescue USB in QEMU!"
echo
echo "Instructions:"
echo "  1. The AI should greet you automatically"
echo "  2. Try these commands:"
echo "     - 'My computer won't boot'"
echo "     - 'Install Ubuntu'"
echo "     - 'Diagnose my computer'"
echo "     - 'Recover my deleted files'"
echo
echo "  3. Press Ctrl+Alt+Delete to exit QEMU"
echo
echo "========================================"
echo

# Launch QEMU with the ISO
qemu-system-x86_64 \
    -enable-kvm \
    -m 4G \
    -smp 2 \
    -cdrom build/ai-rescue-usb.iso \
    -drive file=/tmp/ai-rescue-test-disk.qcow2,format=qcow2 \
    -boot d \
    -net nic \
    -net user \
    -usb \
    -device usb-ehci,id=ehci \
    -vga std \
    -name "AI Rescue USB Test"

# Cleanup
echo
echo "QEMU closed. Cleaning up..."
rm -f /tmp/ai-rescue-test-disk.qcow2
echo "✓ Test disk removed"
echo
echo "Test completed!"
