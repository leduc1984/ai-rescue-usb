"""
AI Rescue USB - OS Detection
=============================
Détecte automatiquement tous les systèmes d'exploitation
présents sur les disques : Windows, Linux, BSD, macOS.
"""

import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

log = logging.getLogger("os-detection")


@dataclass
class PartitionInfo:
    device: str = ""
    size: str = ""
    filesystem: str = ""
    label: str = ""
    mountpoint: str = ""
    flags: list = field(default_factory=list)
    os_type: str = "unknown"  # windows/linux/bsd/macos/data/swap/efi/recovery


@dataclass
class OSInstall:
    name: str = "unknown"
    type: str = "unknown"  # windows/linux/bsd/macos
    version: str = "unknown"
    architecture: str = "x86_64"
    partition: str = ""
    boot_loader: str = "unknown"
    boot_status: str = "unknown"  # ok/broken/missing
    language: str = "unknown"
    users: list = field(default_factory=list)
    last_boot: str = "unknown"


@dataclass
class FullOSInfo:
    detected_os: list = field(default_factory=list)
    partitions: list = field(default_factory=list)
    boot_mode: str = "unknown"  # uefi/legacy
    efi_partition: str = ""
    disk_layout: str = "mbr"  # mbr/gpt/hybrid
    overall_status: str = "healthy"  # healthy/broken/missing_boot


class OSDetector:
    """Détecteur de systèmes d'exploitation."""

    def detect_all(self) -> FullOSInfo:
        """Détecte tous les OS sur tous les disques."""
        log.info("Starting OS detection...")

        info = FullOSInfo()

        # Étape 1: Trouver tous les disques
        disks = self._find_disks()

        # Étape 2: Analyser chaque disque
        for disk in disks:
            self._analyze_disk(disk, info)

        # Étape 3: Déterminer le statut global
        info.overall_status = self._assess_overall_status(info)

        # Étape 4: Résumé
        os_names = [f"{o.name} ({o.type})" for o in info.detected_os]
        log.info(f"OS detection complete: {os_names or 'none found'}")

        return info

    def _find_disks(self) -> list[str]:
        """Trouve tous les disques disponibles."""
        disks = []

        try:
            output = subprocess.check_output(
                ["lsblk", "-d", "-n", "-o", "NAME,TYPE"],
                timeout=10, stderr=subprocess.DEVNULL,
            ).decode()

            for line in output.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "disk":
                    disks.append(f"/dev/{parts[0]}")

        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback
            for dev in Path("/dev").glob("sd?"):
                disks.append(str(dev))
            for dev in Path("/dev").glob("nvme?n?"):
                disks.append(str(dev))

        return disks

    def _analyze_disk(self, disk: str, info: FullOSInfo):
        """Analyse un disque complet."""
        log.info(f"Analyzing disk: {disk}")

        # Détecter le type de table de partition
        try:
            output = subprocess.check_output(
                ["fdisk", "-l", disk], timeout=10, stderr=subprocess.DEVNULL
            ).decode()

            if "Disklabel type: gpt" in output:
                info.disk_layout = "gpt"
            elif "Disklabel type: dos" in output:
                info.disk_layout = "mbr"
        except subprocess.CalledProcessError:
            pass

        # Détecter les partitions
        partitions = self._get_partitions(disk)
        info.partitions.extend(partitions)

        # Chercher EFI
        for p in partitions:
            if "esp" in [f.lower() for f in p.flags] or "boot" in [f.lower() for f in p.flags]:
                if p.filesystem == "vfat":
                    info.efi_partition = p.device

        # Déterminer le mode de boot
        if os.path.exists("/sys/firmware/efi"):
            info.boot_mode = "uefi"
        else:
            info.boot_mode = "legacy"

        # Monter temporairement pour analyser
        os_installs = self._detect_os_on_partitions(partitions)
        info.detected_os.extend(os_installs)

    def _get_partitions(self, disk: str) -> list[PartitionInfo]:
        """Liste les partitions d'un disque."""
        partitions = []

        try:
            output = subprocess.check_output(
                ["lsblk", "-n", "-o", "NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT,PARTFLAGS", disk],
                timeout=10, stderr=subprocess.DEVNULL,
            ).decode()

            for line in output.strip().split("\n")[1:]:  # Skip disk entry
                if not line.strip():
                    continue
                parts = line.split(None, 5)

                if len(parts) >= 1:
                    name = parts[0]
                    # Construire le chemin complet
                    if name.startswith(disk.split("/")[-1]):
                        device = f"/dev/{name}"
                    else:
                        device = f"/dev/{name}"

                    p = PartitionInfo(
                        device=device,
                        size=parts[1] if len(parts) > 1 else "",
                        filesystem=parts[2] if len(parts) > 2 else "",
                        label=parts[3] if len(parts) > 3 else "",
                        mountpoint=parts[4] if len(parts) > 4 else "",
                    )
                    partitions.append(p)

        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        return partitions

    def _detect_os_on_partitions(self, partitions: list[PartitionInfo]) -> list[OSInstall]:
        """Détecte les OS sur les partitions."""
        os_list = []
        mount_base = "/mnt/ai_rescue_os_scan"

        for part in partitions:
            if not part.filesystem or part.filesystem in ("swap", "vfat"):
                continue

            mountpoint = f"{mount_base}_{part.device.replace('/', '_')}"
            os.makedirs(mountpoint, exist_ok=True)

            try:
                # Tenter de monter
                mount_cmd = ["mount", "-o", "ro"]
                if part.filesystem == "ntfs":
                    mount_cmd = ["ntfs-3g", "-o", "ro"]

                subprocess.run(
                    mount_cmd + [part.device, mountpoint],
                    timeout=10, check=False,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )

                # Vérifier si le montage a réussi
                if not os.path.ismount(mountpoint):
                    continue

                # Détection Windows
                if os.path.exists(f"{mountpoint}/Windows/System32"):
                    os_install = self._detect_windows(mountpoint, part.device)
                    if os_install:
                        os_list.append(os_install)

                # Détection Linux
                elif os.path.exists(f"{mountpoint}/etc/os-release"):
                    os_install = self._detect_linux(mountpoint, part.device)
                    if os_install:
                        os_list.append(os_install)

                # Détection BSD
                elif os.path.exists(f"{mountpoint}/etc/rc.conf") or \
                     os.path.exists(f"{mountpoint}/etc/freebsd-update.conf"):
                    os_install = self._detect_bsd(mountpoint, part.device)
                    if os_install:
                        os_list.append(os_install)

                # Détection macOS
                elif os.path.exists(f"{mountpoint}/System/Library/CoreServices"):
                    os_install = self._detect_macos(mountpoint, part.device)
                    if os_install:
                        os_list.append(os_install)

            except Exception as e:
                log.debug(f"Cannot mount {part.device}: {e}")
            finally:
                subprocess.run(
                    ["umount", mountpoint], timeout=5,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    check=False,
                )
                try:
                    os.rmdir(mountpoint)
                except OSError:
                    pass

        return os_list

    def _detect_windows(self, mountpoint: str, partition: str) -> Optional[OSInstall]:
        """Détecte une installation Windows."""
        os_info = OSInstall(
            name="Windows",
            type="windows",
            partition=partition,
        )

        # Version via le registre ou les fichiers
        # Chercher le fichier de version
        system32 = Path(mountpoint) / "Windows" / "System32"
        if system32.exists():
            # Chercher la version dans divers fichiers
            version = "unknown"
            for ver_file in ["ntoskrnl.exe", "kernel32.dll", "License.rtf"]:
                fpath = system32 / ver_file
                if fpath.exists():
                    # Version approximative par taille de fichier
                    size = fpath.stat().st_size
                    if size > 10_000_000:
                        version = "11"
                    elif size > 8_000_000:
                        version = "10"
                    elif size > 5_000_000:
                        version = "8/8.1"
                    elif size > 3_000_000:
                        version = "7"
                    else:
                        version = "XP/Vista"
                    break
            os_info.version = version

        # Boot loader
        efi_path = Path(mountpoint) / "EFI" / "Microsoft" / "Boot"
        if efi_path.exists():
            os_info.boot_loader = "Windows Boot Manager (EFI)"
        else:
            os_info.boot_loader = "NTLDR/BOOTMGR (Legacy)"

        # Vérifier statut boot
        if efi_path.exists() or (Path(mountpoint) / "bootmgr").exists():
            os_info.boot_status = "ok"
        elif (Path(mountpoint) / "Boot" / "BCD").exists():
            os_info.boot_status = "ok"
        else:
            os_info.boot_status = "broken"

        return os_info

    def _detect_linux(self, mountpoint: str, partition: str) -> Optional[OSInstall]:
        """Détecte une installation Linux."""
        os_info = OSInstall(
            name="Linux",
            type="linux",
            partition=partition,
        )

        # Lire /etc/os-release
        os_release = Path(mountpoint) / "etc" / "os-release"
        if os_release.exists():
            try:
                with open(os_release) as f:
                    content = f.read()
                    for line in content.split("\n"):
                        if line.startswith("NAME="):
                            os_info.name = line.split("=")[1].strip('"')
                        elif line.startswith("VERSION_ID="):
                            os_info.version = line.split("=")[1].strip('"')
                        elif line.startswith("ID="):
                            distro_id = line.split("=")[1].strip('"')
                            if not os_info.name or os_info.name == "Linux":
                                os_info.name = distro_id.capitalize()
            except Exception:
                pass

        # Alternative: /etc/lsb-release (Ubuntu)
        lsb_release = Path(mountpoint) / "etc" / "lsb-release"
        if lsb_release.exists() and os_info.version == "unknown":
            try:
                with open(lsb_release) as f:
                    content = f.read()
                    for line in content.split("\n"):
                        if line.startswith("DISTRIB_RELEASE="):
                            os_info.version = line.split("=")[1].strip('"')
            except Exception:
                pass

        # Boot loader
        if Path(mountpoint, "boot/grub/grub.cfg").exists():
            os_info.boot_loader = "GRUB2"
        elif Path(mountpoint, "boot/grub/menu.lst").exists():
            os_info.boot_loader = "GRUB Legacy"
        elif Path(mountpoint, "boot/loader/loader.conf").exists():
            os_info.boot_loader = "systemd-boot"

        # Vérifier statut boot
        if os_info.boot_loader != "unknown":
            os_info.boot_status = "ok"
        elif Path(mountpoint, "boot/vmlinuz*").exists():
            os_info.boot_status = "broken"  # Kernel exists but no bootloader found
        else:
            os_info.boot_status = "broken"

        # Utilisateurs
        home = Path(mountpoint) / "home"
        if home.exists():
            os_info.users = [d.name for d in home.iterdir() if d.is_dir()]

        return os_info

    def _detect_bsd(self, mountpoint: str, partition: str) -> Optional[OSInstall]:
        """Détecte une installation BSD."""
        os_info = OSInstall(
            name="BSD",
            type="bsd",
            partition=partition,
        )

        # Déterminer quelle variante BSD
        if Path(mountpoint, "etc/freebsd-update.conf").exists():
            os_info.name = "FreeBSD"
        elif Path(mountpoint, "etc/netbsd-release").exists() or \
             Path(mountpoint, "etc/release").exists():
            os_info.name = "NetBSD"
        elif Path(mountpoint, "etc/openbsd-release").exists():
            os_info.name = "OpenBSD"

        # Version FreeBSD
        if os_info.name == "FreeBSD":
            freebsd_version = Path(mountpoint) / "bin" / "freebsd-version"
            if freebsd_version.exists():
                os_info.version = "FreeBSD (version inconnue)"
            motd = Path(mountpoint) / "etc" / "motd"
            if motd.exists():
                try:
                    with open(motd) as f:
                        content = f.read()
                        match = re.search(r"FreeBSD\s+(\d+\.\d+)", content)
                        if match:
                            os_info.version = match.group(1)
                except Exception:
                    pass

        # Boot loader FreeBSD
        if os_info.name == "FreeBSD":
            if Path(mountpoint, "boot/loader.efi").exists():
                os_info.boot_loader = "FreeBSD Loader (EFI)"
            elif Path(mountpoint, "boot/boot1.efifat").exists():
                os_info.boot_loader = "FreeBSD Loader"
            os_info.boot_status = "ok" if os_info.boot_loader != "unknown" else "broken"

        return os_info

    def _detect_macos(self, mountpoint: str, partition: str) -> Optional[OSInstall]:
        """Détecte macOS."""
        os_info = OSInstall(
            name="macOS",
            type="macos",
            partition=partition,
        )

        # Version via SystemVersion.plist
        plist = Path(mountpoint) / "System" / "Library" / "CoreServices" / "SystemVersion.plist"
        if plist.exists():
            try:
                import plistlib
                with open(plist, "rb") as f:
                    data = plistlib.load(f)
                    os_info.version = data.get("ProductVersion", "unknown")
                    os_info.name = data.get("ProductName", "macOS")
            except Exception:
                pass

        # Boot loader
        if Path(mountpoint, "System/Library/CoreServices/boot.efi").exists():
            os_info.boot_loader = "Apple Boot (EFI)"
            os_info.boot_status = "ok"
        else:
            os_info.boot_status = "broken"

        return os_info

    def _assess_overall_status(self, info: FullOSInfo) -> str:
        """Évalue l'état global du système."""
        if not info.detected_os:
            return "no_os_found"

        broken_count = sum(1 for o in info.detected_os if o.boot_status == "broken")
        ok_count = sum(1 for o in info.detected_os if o.boot_status == "ok")

        if broken_count == 0 and ok_count > 0:
            return "healthy"
        elif broken_count > 0 and ok_count > 0:
            return "partial"
        elif broken_count > 0:
            return "broken"
        return "unknown"

    def summary(self, info: FullOSInfo) -> str:
        """Génère un résumé lisible."""
        lines = [
            "=" * 50,
            "  SYSTÈMES D'EXPLOITATION DÉTECTÉS",
            "=" * 50,
            "",
            f"Mode boot : {info.boot_mode.upper()}",
            f"Table partition : {info.disk_layout.upper()}",
            f"Partition EFI : {info.efi_partition or 'aucune'}",
            f"État global : {info.overall_status}",
            "",
            "OS trouvés :",
        ]

        if not info.detected_os:
            lines.append("  Aucun OS détecté")
        else:
            for os_install in info.detected_os:
                status_icon = "✓" if os_install.boot_status == "ok" else "⚠" if os_install.boot_status == "broken" else "✗"
                lines.append(
                    f"  {status_icon} {os_install.name} {os_install.version} "
                    f"({os_install.partition}) - Boot: {os_install.boot_status}"
                )
                if os_install.users:
                    lines.append(f"     Utilisateurs: {', '.join(os_install.users)}")

        lines.extend([
            "",
            "Partitions :",
        ])
        for p in info.partitions:
            fs = p.filesystem or "inconnu"
            label = f" [{p.label}]" if p.label else ""
            lines.append(f"  {p.device} - {p.size} - {fs}{label}")

        lines.extend(["", "=" * 50])
        return "\n".join(lines)


# ============================================================
# CLI Test
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    detector = OSDetector()
    info = detector.detect_all()
    print(detector.summary(info))
