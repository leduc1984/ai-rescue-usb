#!/bin/bash
# Création de l'ISO bootable AI Rescue USB

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$PROJECT_DIR/build"
ROOTFS_DIR="$BUILD_DIR/rootfs"
ISO_DIR="$BUILD_DIR/iso"
ISO_OUTPUT="$PROJECT_DIR/ai-rescue-usb.iso"

echo "=== Création ISO AI Rescue USB ==="

# Vérifier que le rootfs existe
if [ ! -d "$ROOTFS_DIR" ]; then
    echo "ERREUR: Rootfs non trouvé. Exécutez d'abord build-base.sh"
    exit 1
fi

# Préparer la structure ISO
mkdir -p "$ISO_DIR/boot"
mkdir -p "$ISO_DIR/EFI"
mkdir -p "$ISO_DIR/syslinux"

# Copier le rootfs
echo "=== Copie rootfs vers ISO ==="
cp -r "$ROOTFS_DIR" "$ISO_DIR/boot/rootfs"

# Créer l'initramfs
echo "=== Création initramfs ==="
cd "$ISO_DIR/boot/rootfs"
find . | cpio -o -H newc | gzip > "$ISO_DIR/boot/initramfs.gz"
cd "$PROJECT_DIR"

# Copier le kernel Alpine (si présent)
if [ -f "$ROOTFS_DIR/boot/vmlinuz-lts" ]; then
    cp "$ROOTFS_DIR/boot/vmlinuz-lts" "$ISO_DIR/boot/vmlinuz"
else
    # Télécharger un kernel minimal
    echo "=== Téléchargement kernel ==="
    wget -O "$ISO_DIR/boot/vmlinuz" "https://dl-cdn.alpinelinux.org/alpine/v3.19/releases/x86_64/netboot/vmlinuz-lts"
fi

# Configuration GRUB pour UEFI et Legacy
echo "=== Configuration bootloader ==="
mkdir -p "$ISO_DIR/boot/grub"
cat > "$ISO_DIR/boot/grub/grub.cfg" <<EOF
set timeout=3
set default=0

menuentry "AI Rescue USB" {
    linux /boot/vmlinuz quiet
    initrd /boot/initramfs.gz
}

menuentry "AI Rescue USB (Mode sans échec)" {
    linux /boot/vmlinuz nomodeset
    initrd /boot/initramfs.gz
}

menuentry "Redémarrage" {
    reboot
}
EOF

# Copier GRUB EFI
if command -v grub-mkimage >/dev/null 2>&1; then
    echo "=== Création bootloader EFI ==="
    grub-mkimage -o "$ISO_DIR/EFI/bootx64.efi" -O x86_64-efi \
        part_gpt part_msdos fat iso9660 normal chain multiboot \
        linux initrd ext2 btrfs xfs
fi

# Créer l'ISO avec xorriso
echo "=== Création ISO finale ==="
if command -v xorriso >/dev/null 2>&1; then
    xorriso -as mkisofs \
        -o "$ISO_OUTPUT" \
        -isohybrid-mbr /usr/share/syslinux/isohdpfx.bin \
        -c boot/boot.cat \
        -b boot/isolinux/isolinux.bin \
        -no-emul-boot \
        -boot-load-size 4 \
        -boot-info-table \
        -eltorito-alt-boot \
        -e boot/grub/efi.img \
        -no-emul-boot \
        -isohybrid-gpt-basdat \
        "$ISO_DIR"
else
    echo "xorriso non installé, création ISO basique"
    genisoimage -o "$ISO_OUTPUT" \
        -b boot/grub/grub.cfg \
        -no-emul-boot \
        "$ISO_DIR"
fi

echo "=== ISO créée ==="
echo "Fichier: $ISO_OUTPUT"
echo "Taille: $(du -h "$ISO_OUTPUT" | cut -f1)"
echo ""
echo "Pour tester: ./test-qemu.sh"
echo "Pour installer sur USB: ./install-to-usb.sh"
