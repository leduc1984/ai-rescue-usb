#!/bin/bash
# Construction de l'ISO de base AI Rescue USB
# Basé sur Alpine Linux minimal

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$PROJECT_DIR/build"
ISO_DIR="$BUILD_DIR/iso"
ROOTFS_DIR="$BUILD_DIR/rootfs"

echo "=== AI Rescue USB - Build System ==="
echo "Projet: $PROJECT_DIR"
echo "Build: $BUILD_DIR"

# Nettoyer l'ancien build
rm -rf "$BUILD_DIR"
mkdir -p "$ISO_DIR" "$ROOTFS_DIR"

# Télécharger Alpine Linux miniroot
ALPINE_VERSION="3.19.1"
ALPINE_ARCH="x86_64"
ALPINE_URL="https://dl-cdn.alpinelinux.org/alpine/v${ALPINE_VERSION%.*}/releases/${ALPINE_ARCH}/alpine-minirootfs-${ALPINE_VERSION}-${ALPINE_ARCH}.tar.gz"

echo "=== Téléchargement Alpine Linux miniroot ==="
wget -O "$BUILD_DIR/alpine-minirootfs.tar.gz" "$ALPINE_URL"

# Extraire dans rootfs
echo "=== Extraction rootfs ==="
cd "$ROOTFS_DIR"
tar xzf "$BUILD_DIR/alpine-minirootfs.tar.gz"
rm "$BUILD_DIR/alpine-minirootfs.tar.gz"

# Copier les composants AI Rescue
echo "=== Installation AI Rescue ==="
cp -r "$PROJECT_DIR/core" "$ROOTFS_DIR/opt/ai-rescue/"
cp -r "$PROJECT_DIR/agents" "$ROOTFS_DIR/opt/ai-rescue/"
cp -r "$PROJECT_DIR/skills" "$ROOTFS_DIR/opt/ai-rescue/"
cp -r "$PROJECT_DIR/tools" "$ROOTFS_DIR/opt/ai-rescue/"
cp -r "$PROJECT_DIR/ui" "$ROOTFS_DIR/opt/ai-rescue/"
cp -r "$PROJECT_DIR/config" "$ROOTFS_DIR/opt/ai-rescue/"

# Rendre les scripts exécutables
chmod +x "$ROOTFS_DIR/opt/ai-rescue/core/"*.py
chmod +x "$ROOTFS_DIR/opt/ai-rescue/agents/"*.py

# Installer les dépendances Python
echo "=== Installation Python ==="
cat > "$ROOTFS_DIR/etc/apk/repositories" <<EOF
https://dl-cdn.alpinelinux.org/alpine/v${ALPINE_VERSION%.*}/main
https://dl-cdn.alpinelinux.org/alpine/v${ALPINE_VERSION%.*}/community
EOF

# Script chroot pour installer les paquets
cat > "$ROOTFS_DIR/tmp/install-deps.sh" <<'EOF'
#!/bin/sh
apk update
apk add python3 py3-pip bash curl wget
apk add ntfs-3g dosfstools mtools
apk add testdisk photorec
apk add fdisk gdisk parted
apk add grub grub-efi
apk add linux-firmware
apk add usbutils pciutils
apk add networkmanager wpa_supplicant
apk add xorg-server xf86-input-libinput
apk add firefox-esr
pip3 install --break-system-packages llama-cpp-python fastapi uvicorn websockets
EOF

chmod +x "$ROOTFS_DIR/tmp/install-deps.sh"

# Configurer le démarrage automatique
echo "=== Configuration démarrage ==="
cat > "$ROOTFS_DIR/etc/inittab" <<EOF
::sysinit:/sbin/openrc sysinit
::sysinit:/sbin/openrc boot
::wait:/sbin/openrc default
tty1::respawn:/sbin/getty 38400 tty1
tty2::respawn:/sbin/getty 38400 tty2
tty3::respawn:/sbin/getty 38400 tty3
tty4::respawn:/sbin/getty 38400 tty4
tty5::respawn:/sbin/getty 38400 tty5
tty6::respawn:/sbin/getty 38400 tty6
::ctrlaltdel:/sbin/reboot
::shutdown:/sbin/openrc shutdown
EOF

# Script de démarrage AI Rescue
cat > "$ROOTFS_DIR/etc/local.d/ai-rescue.start" <<'EOF'
#!/bin/sh
echo "=== AI Rescue USB ==="
echo "Démarrage du système de récupération..."
/opt/ai-rescue/core/startup.sh
EOF

chmod +x "$ROOTFS_DIR/etc/local.d/ai-rescue.start"

echo "=== Build terminé ==="
echo "Rootfs disponible: $ROOTFS_DIR"
echo "Prochaine étape: ./create-iso.sh"
