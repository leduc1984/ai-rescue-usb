"""
AI Rescue USB - Hardware Detection
====================================
Détecte automatiquement tout le matériel de l'ordinateur.
Fonctionne sur PC anciens et récents, UEFI et BIOS Legacy.
"""

import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

log = logging.getLogger("hardware-detection")


@dataclass
class CPUInfo:
    model: str = "unknown"
    vendor: str = "unknown"
    cores: int = 0
    threads: int = 0
    architecture: str = "x86_64"
    max_frequency_mhz: int = 0
    features: list = field(default_factory=list)


@dataclass
class RAMInfo:
    total_mb: int = 0
    available_mb: int = 0
    type: str = "unknown"  # DDR3/DDR4/DDR5
    speed_mhz: int = 0
    slots_used: int = 0
    slots_total: int = 0


@dataclass
class GPUInfo:
    model: str = "unknown"
    vendor: str = "unknown"
    driver: str = "unknown"
    memory_mb: int = 0
    type: str = "unknown"  # integrated/dedicated


@dataclass
class DiskInfo:
    device: str = ""
    model: str = "unknown"
    size_gb: float = 0.0
    type: str = "unknown"  # ssd/hdd/nvme/usb
    interface: str = "unknown"  # sata/nvme/usb/ide
    partitions: list = field(default_factory=list)
    smart_status: str = "unknown"
    health: str = "unknown"


@dataclass
class NetworkInfo:
    interface: str = ""
    type: str = "unknown"  # ethernet/wifi/bluetooth
    model: str = "unknown"
    driver: str = "unknown"
    mac_address: str = ""
    status: str = "unknown"  # up/down


@dataclass
class FullHardwareInfo:
    cpu: CPUInfo = field(default_factory=CPUInfo)
    ram: RAMInfo = field(default_factory=RAMInfo)
    gpus: list = field(default_factory=list)
    disks: list = field(default_factory=list)
    network: list = field(default_factory=list)
    usb_devices: list = field(default_factory=list)
    audio: list = field(default_factory=list)
    bios_type: str = "unknown"  # uefi / legacy
    secure_boot: bool = False
    motherboard: str = "unknown"
    tpm: bool = False
    virtualization: bool = False


class HardwareDetector:
    """Détecteur matériel universel."""

    def detect_all(self) -> FullHardwareInfo:
        """Détecte tout le matériel en une seule passe."""
        log.info("Starting full hardware detection...")

        hw = FullHardwareInfo()

        # Détections de base (toujours disponibles)
        hw.cpu = self._detect_cpu()
        hw.ram = self._detect_ram()
        hw.bios_type = self._detect_bios_type()
        hw.secure_boot = self._detect_secure_boot()
        hw.motherboard = self._detect_motherboard()
        hw.tpm = self._detect_tpm()
        hw.virtualization = self._detect_virtualization()

        # Détections avancées (selon outils disponibles)
        hw.gpus = self._detect_gpus()
        hw.disks = self._detect_disks()
        hw.network = self._detect_network()
        hw.usb_devices = self._detect_usb()
        hw.audio = self._detect_audio()

        log.info(f"Hardware detection complete: CPU={hw.cpu.model}, RAM={hw.ram.total_mb}MB, Disks={len(hw.disks)}")
        return hw

    def _detect_cpu(self) -> CPUInfo:
        """Détecte le CPU via /proc/cpuinfo."""
        cpu = CPUInfo()

        try:
            with open("/proc/cpuinfo") as f:
                content = f.read()

            # Compter les processeurs physiques
            physical_ids = set()
            for line in content.split("\n"):
                if line.startswith("model name"):
                    cpu.model = line.split(":")[1].strip()
                elif line.startswith("vendor_id"):
                    cpu.vendor = line.split(":")[1].strip()
                elif line.startswith("cpu cores"):
                    cpu.cores = int(line.split(":")[1].strip())
                elif line.startswith("physical id"):
                    physical_ids.add(line.split(":")[1].strip())
                elif line.startswith("flags"):
                    cpu.features = line.split(":")[1].strip().split()

            cpu.threads = content.count("processor\t:")
            if cpu.cores == 0:
                cpu.cores = cpu.threads

            # Fréquence max
            try:
                with open("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq") as f:
                    cpu.max_frequency_mhz = int(f.read().strip()) // 1000
            except (FileNotFoundError, ValueError):
                # Essayer dmidecode
                try:
                    output = subprocess.check_output(
                        ["dmidecode", "-t", "processor"], timeout=5,
                        stderr=subprocess.DEVNULL
                    ).decode()
                    match = re.search(r"Max Speed:\s*(\d+)\s*MHz", output)
                    if match:
                        cpu.max_frequency_mhz = int(match.group(1))
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass

        except FileNotFoundError:
            log.warning("/proc/cpuinfo not found")
            cpu.model = "unknown (no /proc)"

        return cpu

    def _detect_ram(self) -> RAMInfo:
        """Détecte la RAM totale et disponible."""
        ram = RAMInfo()

        try:
            with open("/proc/meminfo") as f:
                content = f.read()

            for line in content.split("\n"):
                if line.startswith("MemTotal:"):
                    ram.total_mb = int(line.split()[1]) // 1024
                elif line.startswith("MemAvailable:"):
                    ram.available_mb = int(line.split()[1]) // 1024

            # Type de RAM via dmidecode
            try:
                output = subprocess.check_output(
                    ["dmidecode", "-t", "memory"], timeout=5,
                    stderr=subprocess.DEVNULL
                ).decode()

                # Chercher le type DDR
                ddr_match = re.search(r"Type:\s*(DDR\d)", output)
                if ddr_match:
                    ram.type = ddr_match.group(1)

                # Vitesse
                speed_match = re.search(r"Speed:\s*(\d+)\s*MT/s", output)
                if speed_match:
                    ram.speed_mhz = int(speed_match.group(1))

                # Slots
                ram.slots_used = output.count("Size:") - output.count("Size: No Module Installed")
                ram.slots_total = output.count("Size:")

            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

        except FileNotFoundError:
            log.warning("/proc/meminfo not found")

        return ram

    def _detect_bios_type(self) -> str:
        """Détecte si on est en UEFI ou BIOS Legacy."""
        # Vérifier /sys/firmware/efi
        if os.path.exists("/sys/firmware/efi"):
            return "uefi"
        return "legacy"

    def _detect_secure_boot(self) -> bool:
        """Détecte si Secure Boot est activé."""
        try:
            # Sur UEFI, vérifier via efivar
            output = subprocess.check_output(
                ["efibootmgr"], timeout=5, stderr=subprocess.DEVNULL
            ).decode()
            return "SecureBoot" in output
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Vérifier via mokutil
        try:
            output = subprocess.check_output(
                ["mokutil", "--sb-state"], timeout=5, stderr=subprocess.DEVNULL
            ).decode()
            return "SecureBoot enabled" in output
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        return False

    def _detect_motherboard(self) -> str:
        """Détecte la carte mère."""
        try:
            output = subprocess.check_output(
                ["dmidecode", "-t", "baseboard"], timeout=5,
                stderr=subprocess.DEVNULL
            ).decode()

            manufacturer = re.search(r"Manufacturer:\s*(.+)", output)
            product = re.search(r"Product Name:\s*(.+)", output)

            if manufacturer and product:
                return f"{manufacturer.group(1).strip()} {product.group(1).strip()}"
            elif product:
                return product.group(1).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        return "unknown"

    def _detect_tpm(self) -> bool:
        """Détecte la présence d'un TPM."""
        return os.path.exists("/dev/tpm0") or os.path.exists("/dev/tpmrm0")

    def _detect_virtualization(self) -> bool:
        """Détecte le support de virtualisation CPU."""
        try:
            with open("/proc/cpuinfo") as f:
                content = f.read()
            return "vmx" in content or "svm" in content
        except FileNotFoundError:
            return False

    def _detect_gpus(self) -> list[GPUInfo]:
        """Détecte les GPUs via lspci."""
        gpus = []

        try:
            output = subprocess.check_output(
                ["lspci", "-v", "-nn"], timeout=10, stderr=subprocess.DEVNULL
            ).decode()

            current_gpu = None
            for line in output.split("\n"):
                if "VGA" in line or "3D" in line or "Display" in line:
                    if current_gpu:
                        gpus.append(current_gpu)
                    current_gpu = GPUInfo()
                    # Extraire le modèle
                    model_match = re.search(r'([A-Za-z0-9\s\[\]/]+?)(?:\s*\[|$)', line.split(": ")[-1])
                    if model_match:
                        current_gpu.model = model_match.group(1).strip()
                elif current_gpu and "Subsystem" in line:
                    pass  # Plus de détails
                elif current_gpu and "driver" in line.lower():
                    driver_match = re.search(r"Kernel driver in use:\s*(\S+)", line)
                    if driver_match:
                        current_gpu.driver = driver_match.group(1)

            if current_gpu:
                gpus.append(current_gpu)

        except (subprocess.CalledProcessError, FileNotFoundError):
            log.warning("lspci not available")

        # Fallback: vérifier /sys/class/drm
        if not gpus:
            gpus = self._detect_gpus_sysfs()

        return gpus

    def _detect_gpus_sysfs(self) -> list[GPUInfo]:
        """Détecte les GPUs via sysfs."""
        gpus = []
        drm_path = Path("/sys/class/drm")

        if drm_path.exists():
            for card in sorted(drm_path.glob("card*")):
                gpu = GPUInfo(model=f"GPU {card.name}")
                gpus.append(gpu)

        return gpus

    def _detect_disks(self) -> list[DiskInfo]:
        """Détecte tous les disques."""
        disks = []

        # Utiliser lsblk pour détecter tous les disques
        try:
            output = subprocess.check_output(
                ["lsblk", "-d", "-n", "-o", "NAME,SIZE,TYPE,TRAN,MODEL,ROTA"],
                timeout=10, stderr=subprocess.DEVNULL,
            ).decode()

            for line in output.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split(None, 5)
                if len(parts) < 2:
                    continue

                name = parts[0]
                size = parts[1] if len(parts) > 1 else ""
                dev_type = parts[2] if len(parts) > 2 else ""
                transport = parts[3] if len(parts) > 3 else ""
                model = parts[4] if len(parts) > 4 else "unknown"
                rotational = parts[5] if len(parts) > 5 else "1"

                # Filtrer seulement les disques
                if dev_type != "disk":
                    continue

                disk = DiskInfo(
                    device=f"/dev/{name}",
                    model=model,
                    type="ssd" if rotational == "0" else "hdd",
                    interface=transport,
                )

                # Taille
                try:
                    if "G" in size:
                        disk.size_gb = float(size.replace("G", ""))
                    elif "T" in size:
                        disk.size_gb = float(size.replace("T", "")) * 1024
                    elif "M" in size:
                        disk.size_gb = float(size.replace("M", "")) / 1024
                except ValueError:
                    pass

                # SMART
                disk.smart_status = self._check_smart(disk.device)
                disk.health = self._check_disk_health(disk.device)

                # Partitions
                disk.partitions = self._get_partitions(disk.device)

                disks.append(disk)

        except (subprocess.CalledProcessError, FileNotFoundError):
            log.warning("lsblk not available")
            disks = self._detect_disks_fallback()

        return disks

    def _detect_disks_fallback(self) -> list[DiskInfo]:
        """Fallback: détecte les disques via /dev."""
        disks = []
        for dev in sorted(Path("/dev").glob("sd*")):
            if dev.name[-1].isdigit():  # Skip partitions
                continue
            disks.append(DiskInfo(device=str(dev), model="unknown"))
        for dev in sorted(Path("/dev").glob("nvme*")):
            if "p" in dev.name:  # Skip partitions
                continue
            disks.append(DiskInfo(device=str(dev), model="unknown", interface="nvme"))
        return disks

    def _check_smart(self, device: str) -> str:
        """Vérifie le statut SMART d'un disque."""
        try:
            output = subprocess.check_output(
                ["smartctl", "-H", device], timeout=30, stderr=subprocess.DEVNULL
            ).decode()
            if "PASSED" in output:
                return "ok"
            elif "FAILED" in output:
                return "failed"
            return "unknown"
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "unknown"

    def _check_disk_health(self, device: str) -> str:
        """Vérifie l'état de santé du disque."""
        status = self._check_smart(device)
        if status == "ok":
            return "good"
        elif status == "failed":
            return "critical"
        return "unknown"

    def _get_partitions(self, device: str) -> list[dict]:
        """Liste les partitions d'un disque."""
        partitions = []
        try:
            output = subprocess.check_output(
                ["lsblk", "-n", "-o", "NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT", device],
                timeout=10, stderr=subprocess.DEVNULL,
            ).decode()

            for line in output.strip().split("\n")[1:]:  # Skip device line
                if not line.strip():
                    continue
                parts = line.split(None, 4)
                if len(parts) >= 2:
                    partitions.append({
                        "name": parts[0],
                        "size": parts[1],
                        "fs": parts[2] if len(parts) > 2 else "",
                        "label": parts[3] if len(parts) > 3 else "",
                        "mountpoint": parts[4] if len(parts) > 4 else "",
                    })
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        return partitions

    def _detect_network(self) -> list[NetworkInfo]:
        """Détecte les interfaces réseau."""
        network = []

        try:
            output = subprocess.check_output(
                ["lspci"], timeout=10, stderr=subprocess.DEVNULL
            ).decode()

            for line in output.split("\n"):
                if "Ethernet" in line:
                    model = line.split(": ")[-1].strip() if ": " in line else "unknown"
                    network.append(NetworkInfo(type="ethernet", model=model))
                elif "Network" in line or "WiFi" in line or "Wireless" in line:
                    model = line.split(": ")[-1].strip() if ": " in line else "unknown"
                    network.append(NetworkInfo(type="wifi", model=model))

        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Ajouter les interfaces détectées par ip link
        try:
            output = subprocess.check_output(
                ["ip", "-br", "link", "show"], timeout=5
            ).decode()
            for line in output.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 2 and parts[0] != "lo":
                    iface = parts[0]
                    status = "up" if "UP" in line else "down"
                    # Chercher si déjà dans la liste
                    if not any(n.interface == iface for n in network):
                        network.append(NetworkInfo(interface=iface, status=status))
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        return network

    def _detect_usb(self) -> list[dict]:
        """Détecte les périphériques USB."""
        devices = []
        try:
            output = subprocess.check_output(
                ["lsusb"], timeout=10, stderr=subprocess.DEVNULL
            ).decode()
            for line in output.strip().split("\n"):
                if line.strip():
                    # Format: Bus 001 Device 002: ID 8087:0024 Intel Corp.
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        devices.append({"id": parts[0].strip(), "description": parts[1].strip()})
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return devices

    def _detect_audio(self) -> list[dict]:
        """Détecte les périphériques audio."""
        devices = []
        try:
            output = subprocess.check_output(
                ["lspci"], timeout=10, stderr=subprocess.DEVNULL
            ).decode()
            for line in output.split("\n"):
                if "Audio" in line:
                    model = line.split(": ")[-1].strip() if ": " in line else "unknown"
                    devices.append({"type": "pci", "model": model})
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Vérifier aussi les cartes son ALSA
        try:
            cards_path = Path("/proc/asound/cards")
            if cards_path.exists():
                with open(cards_path) as f:
                    for line in f:
                        if ":" in line and "---" not in line:
                            card_info = line.split(":", 1)[1].strip()
                            if card_info:
                                devices.append({"type": "alsa", "model": card_info})
        except FileNotFoundError:
            pass

        return devices

    def to_json(self, hw: FullHardwareInfo) -> str:
        """Sérialise en JSON lisible."""
        return json.dumps(hw, default=lambda o: o.__dict__, indent=2, ensure_ascii=False)

    def summary(self, hw: FullHardwareInfo) -> str:
        """Génère un résumé texte."""
        lines = [
            "=" * 50,
            "  MATÉRIEL DÉTECTÉ",
            "=" * 50,
            "",
            f"CPU : {hw.cpu.model} ({hw.cpu.cores} cœurs, {hw.cpu.threads} threads)",
            f"RAM : {hw.ram.total_mb} MB ({hw.ram.type})",
            f"BIOS : {hw.bios_type.upper()}" + (" (Secure Boot)" if hw.secure_boot else ""),
            f"Carte mère : {hw.motherboard}",
            "",
            "GPUs :",
        ]
        for gpu in hw.gpus:
            lines.append(f"  - {gpu.model} (driver: {gpu.driver})")

        lines.extend(["", "Disques :"])
        for disk in hw.disks:
            health_icon = {"good": "✓", "critical": "⚠", "unknown": "?"}.get(disk.health, "?")
            lines.append(f"  {health_icon} {disk.device} - {disk.model} ({disk.size_gb:.0f}GB, {disk.type})")

        lines.extend(["", "Réseau :"])
        for net in hw.network:
            status_icon = "▲" if net.status == "up" else "▼"
            lines.append(f"  {status_icon} {net.type}: {net.model or net.interface}")

        if hw.tpm:
            lines.append("\nTPM : Présent")
        if hw.virtualization:
            lines.append("Virtualisation : Supportée")

        lines.extend(["", "=" * 50])
        return "\n".join(lines)


# ============================================================
# CLI Test
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    detector = HardwareDetector()
    hw = detector.detect_all()
    print(detector.summary(hw))
    print("\n--- JSON ---")
    print(detector.to_json(hw))
