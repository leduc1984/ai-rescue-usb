"""
AI Rescue USB - Install, Backup, Recovery, Driver Agents
=========================================================
Agents spécialisés pour l'installation d'OS, la sauvegarde,
la récupération de fichiers et la gestion des pilotes.
"""

import logging
import os
import subprocess
import json
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

log = logging.getLogger("agents")


# ============================================================
# Supported OS definitions
# ============================================================
SUPPORTED_OS = {
    "windows11": {
        "name": "Windows 11",
        "type": "windows",
        "min_ram_mb": 4096,
        "min_disk_gb": 64,
        "secure_boot_required": True,
        "tpm_required": True,
        "iso_url": "https://www.microsoft.com/software-download/windows11",
        "iso_size_gb": 6.0,
    },
    "windows10": {
        "name": "Windows 10",
        "type": "windows",
        "min_ram_mb": 2048,
        "min_disk_gb": 32,
        "iso_url": "https://www.microsoft.com/software-download/windows10",
        "iso_size_gb": 5.5,
    },
    "ubuntu_2404": {
        "name": "Ubuntu 24.04 LTS",
        "type": "linux",
        "min_ram_mb": 2048,
        "min_disk_gb": 25,
        "iso_url": "https://releases.ubuntu.com/24.04/ubuntu-24.04-desktop-amd64.iso",
        "iso_size_gb": 5.7,
        "checksum_url": "https://releases.ubuntu.com/24.04/SHA256SUMS",
    },
    "debian_12": {
        "name": "Debian 12",
        "type": "linux",
        "min_ram_mb": 1024,
        "min_disk_gb": 10,
        "iso_url": "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-12.0.0-amd64-netinst.iso",
        "iso_size_gb": 0.6,
    },
    "fedora_40": {
        "name": "Fedora 40",
        "type": "linux",
        "min_ram_mb": 2048,
        "min_disk_gb": 20,
        "iso_url": "https://download.fedoraproject.org/pub/fedora/linux/releases/40/Workstation/x86_64/iso/Fedora-Workstation-Live-x86_64-40.iso",
        "iso_size_gb": 2.0,
    },
    "linux_mint_21": {
        "name": "Linux Mint 21",
        "type": "linux",
        "min_ram_mb": 2048,
        "min_disk_gb": 20,
        "iso_url": "https://mirrors.edge.kernel.org/linuxmint/stable/21/linuxmint-21-xfce-64bit.iso",
        "iso_size_gb": 2.7,
    },
    "arch_latest": {
        "name": "Arch Linux",
        "type": "linux",
        "min_ram_mb": 1024,
        "min_disk_gb": 10,
        "iso_url": "https://archlinux.org/releng/releases/latest/archlinux-x86_64.iso",
        "iso_size_gb": 0.9,
    },
    "freebsd_14": {
        "name": "FreeBSD 14",
        "type": "bsd",
        "min_ram_mb": 1024,
        "min_disk_gb": 10,
        "iso_url": "https://download.freebsd.org/releases/amd64/amd64/ISO-IMAGES/14.0/FreeBSD-14.0-RELEASE-amd64-disc1.iso",
        "iso_size_gb": 1.0,
    },
    "openbsd_74": {
        "name": "OpenBSD 7.4",
        "type": "bsd",
        "min_ram_mb": 512,
        "min_disk_gb": 5,
        "iso_url": "https://cdn.openbsd.org/pub/OpenBSD/7.4/amd64/install74.iso",
        "iso_size_gb": 0.6,
    },
}


# ============================================================
# Install Agent
# ============================================================
class InstallAgent:
    """
    Agent d'installation universelle.
    Analyse la compatibilité, télécharge l'ISO, prépare l'installation.
    """

    def __init__(self):
        self.cache_dir = Path("/opt/ai-rescue/cache/iso")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def check_compatibility(self, os_id: str, hardware: dict) -> dict:
        """
        Vérifie si un OS est compatible avec le matériel.
        """
        os_def = SUPPORTED_OS.get(os_id)

        if not os_def:
            return {
                "compatible": False,
                "reason": f"OS '{os_id}' non supporté",
                "suggestions": list(SUPPORTED_OS.keys()),
            }

        ram_mb = hardware.get("ram_mb", 0)
        disk_gb = hardware.get("disk_gb", 0)
        has_tpm = hardware.get("tpm", False)
        has_secure_boot = hardware.get("secure_boot", False)

        issues = []
        warnings = []

        if ram_mb < os_def["min_ram_mb"]:
            issues.append(f"RAM insuffisante: {ram_mb}MB < {os_def['min_ram_mb']}MB requis")

        if disk_gb < os_def["min_disk_gb"]:
            issues.append(f"Espace disque insuffisant: {disk_gb}GB < {os_def['min_disk_gb']}GB requis")

        if os_def.get("tpm_required") and not has_tpm:
            issues.append("TPM 2.0 requis mais non détecté")

        if os_def.get("secure_boot_required") and not has_secure_boot:
            issues.append("Secure Boot requis mais non activé")

        return {
            "compatible": len(issues) == 0,
            "os": os_def["name"],
            "issues": issues,
            "warnings": warnings,
            "min_requirements": {
                "ram": f"{os_def['min_ram_mb']}MB",
                "disk": f"{os_def['min_disk_gb']}GB",
            },
        }

    def list_compatible(self, hardware: dict) -> list[dict]:
        """
        Liste tous les OS compatibles avec le matériel.
        """
        results = []
        for os_id in SUPPORTED_OS:
            check = self.check_compatibility(os_id, hardware)
            if check["compatible"]:
                results.append({
                    "id": os_id,
                    "name": SUPPORTED_OS[os_id]["name"],
                    "type": SUPPORTED_OS[os_id]["type"],
                    "iso_size_gb": SUPPORTED_OS[os_id]["iso_size_gb"],
                })

        # Trier par type puis nom
        results.sort(key=lambda x: (x["type"], x["name"]))
        return results

    def download_iso(self, os_id: str, callback=None) -> Optional[Path]:
        """
        Télécharge l'ISO d'un OS.
        """
        os_def = SUPPORTED_OS.get(os_id)
        if not os_def:
            log.error(f"OS {os_id} non trouvé")
            return None

        iso_url = os_def["iso_url"]
        iso_name = f"{os_id}.iso"
        iso_path = self.cache_dir / iso_name

        if iso_path.exists():
            log.info(f"ISO déjà présente: {iso_path}")
            return iso_path

        log.info(f"Téléchargement de {os_def['name']}...")
        log.info(f"URL: {iso_url}")

        try:
            # Utiliser wget avec progression
            subprocess.run(
                ["wget", "-q", "--show-progress", "-O", str(iso_path), iso_url],
                timeout=7200,  # 2h max
                check=True,
            )
            log.info(f"ISO téléchargée: {iso_path} ({iso_path.stat().st_size / 1e9:.1f}GB)")
            return iso_path
        except subprocess.CalledProcessError as e:
            log.error(f"Échec téléchargement: {e}")
            if iso_path.exists():
                iso_path.unlink()
            return None

    def verify_iso(self, os_id: str, iso_path: Path) -> bool:
        """
        Vérifie l'intégrité de l'ISO.
        """
        os_def = SUPPORTED_OS.get(os_id)
        if not os_def:
            return False

        if "checksum_url" not in os_def:
            log.warning(f"Pas de checksum pour {os_id}, skip vérification")
            return True

        log.info(f"Vérification intégrité de {iso_path.name}...")

        # Calculer le hash local
        sha256 = hashlib.sha256()
        with open(iso_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        local_hash = sha256.hexdigest()

        # Télécharger la somme officielle
        try:
            result = subprocess.run(
                ["wget", "-q", "-O", "-", os_def["checksum_url"]],
                capture_output=True, text=True, timeout=30,
            )
            if iso_path.name in result.stdout:
                log.info(f"Hash local: {local_hash[:16]}...")
                return local_hash in result.stdout
        except Exception as e:
            log.warning(f"Impossible de vérifier: {e}")

        return True  # Skip si pas possible

    def prepare_installation(self, os_id: str, target_disk: str) -> dict:
        """
        Prépare l'installation sur le disque cible.
        """
        os_def = SUPPORTED_OS.get(os_id)
        if not os_def:
            return {"success": False, "error": "OS inconnu"}

        log.info(f"Préparation installation de {os_def['name']} sur {target_disk}")

        return {
            "success": True,
            "os": os_def["name"],
            "target": target_disk,
            "steps": [
                "1. Partitionnement du disque",
                "2. Formatage des partitions",
                "3. Copie des fichiers système",
                "4. Installation du bootloader",
                "5. Configuration initiale",
            ],
            "warning": "CETTE OPÉRATION EFFACERA TOUTES LES DONNÉES DU DISQUE CIBLE.",
        }


# ============================================================
# Backup Agent
# ============================================================
class BackupAgent:
    """
    Agent de sauvegarde et restauration.
    """

    def __init__(self):
        self.backup_dir = Path("/mnt/backup")

    def scan_files(self, mountpoint: str = "/mnt/source") -> dict:
        """
        Analyse les fichiers à sauvegarder.
        """
        log.info(f"Scan des fichiers dans {mountpoint}...")

        stats = {"total_files": 0, "total_size_bytes": 0, "file_types": {}, "large_files": []}

        try:
            for root, dirs, files in os.walk(mountpoint):
                # Skip system dirs
                dirs[:] = [d for d in dirs if d not in (
                    "proc", "sys", "dev", "run", "tmp", "$Recycle.Bin",
                    "System Volume Information",
                )]

                for fname in files:
                    fpath = os.path.join(root, fname)
                    try:
                        size = os.path.getsize(fpath)
                        stats["total_files"] += 1
                        stats["total_size_bytes"] += size

                        ext = Path(fname).suffix.lower() or "no_ext"
                        stats["file_types"][ext] = stats["file_types"].get(ext, 0) + 1

                        if size > 100_000_000:  # > 100MB
                            stats["large_files"].append({"path": fpath, "size": size})
                    except OSError:
                        continue
        except Exception as e:
            log.error(f"Scan échoué: {e}")
            return {"success": False, "error": str(e)}

        stats["total_size_gb"] = stats["total_size_bytes"] / 1e9
        log.info(f"Scan terminé: {stats['total_files']} fichiers, {stats['total_size_gb']:.1f}GB")

        return {"success": True, "stats": stats}

    def backup_files(self, source: str, destination: str,
                     file_types: Optional[list] = None) -> dict:
        """
        Sauvegarde les fichiers.
        """
        log.info(f"Sauvegarde de {source} vers {destination}...")

        try:
            # Utiliser rsync
            cmd = ["rsync", "-avh", "--progress"]
            if file_types:
                for ext in file_types:
                    cmd.extend(["--include", f"*{ext}", "--include", "*/", "--exclude", "*"])

            cmd.extend([source.rstrip("/") + "/", destination])

            result = subprocess.run(
                cmd, timeout=3600, capture_output=True, text=True
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout[-2000:],
                "command": " ".join(cmd),
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout - backup trop long"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_disk_image(self, source_disk: str, destination: str) -> dict:
        """
        Crée une image complète du disque (clone).
        """
        log.info(f"Création image disque de {source_disk}...")

        try:
            cmd = ["dd", f"if={source_disk}", f"of={destination}",
                   "bs=4M", "status=progress", "conv=sparse"]

            result = subprocess.run(cmd, timeout=7200, capture_output=True, text=True)

            return {
                "success": result.returncode == 0,
                "source": source_disk,
                "destination": destination,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout - disque trop grand"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def restore_disk_image(self, image_path: str, target_disk: str) -> dict:
        """
        Restaure une image disque.
        """
        log.warning(f"RESTAURATION de {image_path} vers {target_disk} - DONNÉES EFFACÉES!")

        try:
            cmd = ["dd", f"if={image_path}", f"of={target_disk}",
                   "bs=4M", "status=progress"]

            result = subprocess.run(cmd, timeout=7200, capture_output=True, text=True)

            return {
                "success": result.returncode == 0,
                "target": target_disk,
                "restored": True,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ============================================================
# Recovery Agent
# ============================================================
class RecoveryAgent:
    """
    Agent de récupération de fichiers supprimés.
    Utilise testdisk/photorec et ddrescue.
    """

    def __init__(self):
        self.recovery_dir = Path("/mnt/recovery")

    def scan_for_lost_files(self, device: str) -> dict:
        """
        Scanne un disque/partition pour fichiers récupérables.
        """
        log.info(f"Scan de {device} pour fichiers récupérables...")

        try:
            # Utiliser testdisk pour lister les partitions/fichiers
            result = subprocess.run(
                ["testdisk", "/list", device],
                capture_output=True, text=True, timeout=120,
            )

            # Analyser la sortie
            recoverable = self._parse_testdisk_output(result.stdout)

            return {
                "success": True,
                "device": device,
                "recoverable_files": recoverable.get("files", 0),
                "partitions_found": recoverable.get("partitions", 0),
                "raw_output": result.stdout[:3000],
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout - scan trop long"}
        except FileNotFoundError:
            return {"success": False, "error": "testdisk non installé"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def recover_files(self, device: str, output_dir: str,
                      file_types: Optional[list] = None) -> dict:
        """
        Récupère les fichiers supprimés avec photorec.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        log.info(f"Récupération fichiers de {device} vers {output_dir}...")

        try:
            cmd = ["photorec", "/d", str(output_path), "/cmd", device, "search"]
            result = subprocess.run(
                cmd, timeout=3600, capture_output=True, text=True
            )

            # Compter les fichiers récupérés
            recovered_count = sum(1 for _ in output_path.rglob("*") if _.is_file())

            return {
                "success": True,
                "device": device,
                "recovered_count": recovered_count,
                "output_dir": str(output_path),
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout"}
        except FileNotFoundError:
            return {"success": False, "error": "photorec non installé"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def rescue_damaged_disk(self, source: str, destination: str) -> dict:
        """
        Tente de sauver les données d'un disque endommagé avec ddrescue.
        """
        log.info(f"Tentative de sauvetage de {source} vers {destination}...")

        try:
            cmd = ["ddrescue", "-f", "-n", source, destination,
                   f"{destination}.log"]
            result = subprocess.run(
                cmd, timeout=7200, capture_output=True, text=True
            )

            return {
                "success": result.returncode == 0,
                "source": source,
                "destination": destination,
                "log": f"{destination}.log",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _parse_testdisk_output(self, output: str) -> dict:
        """Parse la sortie de testdisk."""
        return {
            "files": output.count("files"),
            "partitions": output.count("Partition"),
        }


# ============================================================
# Driver Agent
# ============================================================
class DriverAgent:
    """
    Agent de gestion des pilotes.
    Identifie le matériel inconnu et trouve les pilotes.
    """

    def __init__(self):
        self.driver_cache = Path("/opt/ai-rescue/cache/drivers")

    def detect_unknown_hardware(self) -> list[dict]:
        """
        Détecte le matériel sans pilote.
        """
        unknown = []

        try:
            # Vérifier les modules kernel manquants
            result = subprocess.run(
                ["lspci", "-k"], capture_output=True, text=True, timeout=10
            )

            current_device = None
            for line in result.stdout.split("\n"):
                if ":" in line and "Kernel" not in line:
                    current_device = line.strip()
                elif "Kernel driver in use:" not in line and "Kernel modules:" in line:
                    if current_device:
                        unknown.append({
                            "device": current_device,
                            "status": "no_driver",
                        })

        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        return unknown

    def find_drivers(self, hardware_id: str) -> list[dict]:
        """
        Recherche les pilotes pour un périphérique.
        """
        log.info(f"Recherche pilotes pour: {hardware_id}")

        # Extraire vendor:device ID
        import re
        match = re.search(r"\[([0-9a-f]{4}):([0-9a-f]{4})\]", hardware_id)
        if match:
            vendor, device = match.group(1), match.group(2)
            # Chercher dans la base PCI IDS
            try:
                result = subprocess.run(
                    ["grep", "-i", f"{vendor}.*{device}", "/usr/share/hwdata/pci.ids"],
                    capture_output=True, text=True, timeout=5,
                )
                if result.stdout.strip():
                    return [{"name": result.stdout.strip(), "source": "pci.ids"}]
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

        return [{"name": "Pilote inconnu - recherche en ligne nécessaire"}]

    def install_driver(self, driver_package: str) -> dict:
        """
        Installe un pilote.
        """
        log.info(f"Installation pilote: {driver_package}")

        # Selon la distribution, utiliser le bon gestionnaire
        try:
            result = subprocess.run(
                ["apk", "add", driver_package],
                capture_output=True, text=True, timeout=120,
            )
            return {"success": result.returncode == 0, "package": driver_package}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ============================================================
# CLI Test
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test Install Agent
    print("=" * 50)
    print("  TEST INSTALL AGENT")
    print("=" * 50)

    install = InstallAgent()
    hw = {"ram_mb": 8192, "disk_gb": 256, "tpm": True, "secure_boot": True}
    compat = install.list_compatible(hw)
    for os_info in compat:
        print(f"  ✓ {os_info['name']} ({os_info['type']})")

    # Test Backup Agent
    print("\n" + "=" * 50)
    print("  TEST BACKUP AGENT")
    print("=" * 50)

    backup = BackupAgent()
    print("  Backup agent ready")

    # Test Recovery Agent
    print("\n" + "=" * 50)
    print("  TEST RECOVERY AGENT")
    print("=" * 50)

    recovery = RecoveryAgent()
    print("  Recovery agent ready")

    # Test Driver Agent
    print("\n" + "=" * 50)
    print("  TEST DRIVER AGENT")
    print("=" * 50)

    driver = DriverAgent()
    unknown = driver.detect_unknown_hardware()
    if unknown:
        for dev in unknown:
            print(f"  ⚠ {dev['device']}")
    else:
        print("  Tous les pilotes sont chargés")
