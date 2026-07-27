#!/bin/bash
# AI Rescue USB - Linux Flash Tool
# =================================
# Flash the AI Rescue USB image to a USB drive on Linux

set -e

IMAGE_FILE="build/ai-rescue-usb.img"

echo
echo "========================================"
echo "   AI Rescue USB - Linux Flash Tool"
echo "========================================"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "[ERROR] This tool requires root privileges."
    echo "Please run: sudo $0"
    exit 1
fi

# Check if image exists
if [ ! -f "$IMAGE_FILE" ]; then
    echo "[ERROR] USB image not found: $IMAGE_FILE"
    echo "Please run ./build-all.sh first to create the image."
    exit 1
fi

echo "Found USB image: $IMAGE_FILE"
echo

# List available USB drives
echo "Available USB drives:"
echo

lsblk -d -o NAME,SIZE,MODEL,TRAN | grep usb | nl -v 1

# Count USB drives
usb_count=$(lsblk -d -o NAME,SIZE,MODEL,TRAN | grep -c usb)

if [ "$usb_count" -eq 0 ]; then
    echo "[ERROR] No USB drives detected."
    echo "Please insert a USB drive and try again."
    exit 1
fi

echo
read -p "Select USB drive number (1-$usb_count): " selection

# Validate selection
if ! [[ "$selection" =~ ^[0-9]+$ ]] || [ "$selection" -lt 1 ] || [ "$selection" -gt "$usb_count" ]; then
    echo "[ERROR] Invalid selection."
    exit 1
fi

# Get selected device
selected_device=$(lsblk -d -o NAME,SIZE,MODEL,TRAN | grep usb | sed -n "${selection}p" | awk '{print $1}')
selected_device="/dev/$selected_device"
selected_model=$(lsblk -d -o NAME,SIZE,MODEL,TRAN | grep usb | sed -n "${selection}p" | awk '{for(i=2;i<=NF-1;i++) printf $i" "; print ""}')

echo
echo "========================================"
echo "WARNING: This will erase ALL data on:"
echo "  Device: $selected_device"
echo "  Model: $selected_model"
echo "========================================"
echo

read -p "Type 'YES' to confirm: " confirm
if [ "$confirm" != "YES" ]; then
    echo "Operation cancelled."
    exit 0
fi

echo
echo "Flashing USB image..."
echo "This may take several minutes."
echo

# Flash with dd
dd if="$IMAGE_FILE" of="$selected_device" bs=4M status=progress conv=fsync

if [ $? -eq 0 ]; then
    echo
    echo "[SUCCESS] USB drive flashed successfully!"
    echo "You can now boot from this USB drive."
    echo
    sync
else
    echo
    echo "[ERROR] Failed to flash USB drive."
    exit 1
fi
