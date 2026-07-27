"""
AI Rescue USB - Security System
================================
Système de sécurité pour les opérations critiques.
Aucune opération destructive sans confirmation explicite.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

log = logging.getLogger("security")


class OperationRisk(Enum):
    """Niveaux de risque d'une opération."""
    SAFE = 1        # Lecture seule
    LOW = 2         # Modification fichiers
    MEDIUM = 3      # Modification système
    HIGH = 4        # Partitionnement
    DESTRUCTIVE = 5 # Formatage, suppression définitive


@dataclass
class Operation:
    """Une opération avec son niveau de risque."""
    name: str
    description: str
    risk: OperationRisk = OperationRisk.SAFE
    command: Optional[str] = None
    affected_disks: list[str] = field(default_factory=list)
    affected_data: dict = field(default_factory=dict)
    reversible: bool = False


class SecurityManager:
    """
    Gestionnaire de sécurité.
    Intercepte les opérations risquées pour confirmation.
    """

    def __init__(self):
        self.confirmed_operations: set = set()
        self.audit_log_path = Path("/var/log/ai-rescue-audit.log")
        self.dry_run = False
        self.require_confirmation_for = [
            OperationRisk.MEDIUM,
            OperationRisk.HIGH,
            OperationRisk.DESTRUCTIVE,
        ]
        self._confirmations_pending: dict[str, Operation] = {}

    def evaluate_risk(self, operation: Operation) -> OperationRisk:
        """
        Évalue le risque d'une opération.
        """
        # Opérations de lecture = SAFE
        read_only_commands = ["ls", "cat", "grep", "find", "lspci", "lsblk",
                              "smartctl", "dmidecode", "fdisk -l", "blkid"]
        if operation.command:
            for safe_cmd in read_only_commands:
                if operation.command.strip().startswith(safe_cmd):
                    return OperationRisk.SAFE

        # Formatage = DESTRUCTIVE
        destructive = ["mkfs", "dd if=", "format", "wipefs", "shred"]
        if operation.command:
            for d in destructive:
                if d in operation.command:
                    return OperationRisk.DESTRUCTIVE

        # Partitionnement = HIGH
        partition_commands = ["parted", "gdisk", "fdisk", "cfdisk",
                              "sgdisk", "gpart", "bcdedit"]
        if operation.command:
            for p in partition_commands:
                if p in operation.command:
                    return OperationRisk.HIGH

        # Boot modification = MEDIUM
        boot_commands = ["grub-install", "bootrec", "bcdboot",
                         "efibootmgr", "gpart bootcode"]
        if operation.command:
            for b in boot_commands:
                if b in operation.command:
                    return OperationRisk.MEDIUM

        # Fix / réparation = LOW
        fix_commands = ["fsck", "chkdsk", "apt-get", "pacman", "dnf",
                        "sfc", "dism", "pkg check", "fsck"]
        if operation.command:
            for f in fix_commands:
                if f in operation.command:
                    return OperationRisk.LOW

        return OperationRisk.LOW

    def needs_confirmation(self, operation: Operation) -> bool:
        """
        Vérifie si l'opération nécessite une confirmation.
        """
        risk = self.evaluate_risk(operation)
        operation.risk = risk

        # Vérifier si déjà confirmé
        op_key = f"{operation.name}:{operation.command}"
        if op_key in self.confirmed_operations:
            return False

        return risk in self.require_confirmation_for

    def request_confirmation(self, operation: Operation) -> dict:
        """
        Demande confirmation pour une opération risquée.
        Retourne les infos à afficher à l'utilisateur.
        """
        risk_labels = {
            OperationRisk.SAFE: "✅ Sans risque",
            OperationRisk.LOW: "🟢 Risque faible",
            OperationRisk.MEDIUM: "🟡 Risque modéré",
            OperationRisk.HIGH: "🟠 Risque élevé - peut modifier le disque",
            OperationRisk.DESTRUCTIVE: "🔴 DESTRUCTIF - effacement de données",
        }

        # Log l'opération
        self._audit(operation, "confirmation_requested")

        return {
            "title": "⚠️ CONFIRMATION REQUISE",
            "operation": operation.name,
            "description": operation.description,
            "risk_level": operation.risk.name,
            "risk_label": risk_labels.get(operation.risk, "Inconnu"),
            "command": operation.command,
            "affected": {
                "disks": operation.affected_disks,
                "data": operation.affected_data,
            },
            "reversible": operation.reversible,
            "message": (
                f"Cette action est de niveau {operation.risk.name}.\n"
                f"Elle va modifier : {', '.join(operation.affected_disks) if operation.affected_disks else 'le système'}.\n\n"
                f"Êtes-vous sûr de vouloir continuer ?"
            ),
        }

    def confirm(self, operation: Operation) -> bool:
        """
        Confirme une opération.
        Retourne True si l'opération peut continuer.
        """
        op_key = f"{operation.name}:{operation.command}"
        self.confirmed_operations.add(op_key)
        self._audit(operation, "confirmed")
        log.info(f"Opération confirmée: {operation.name}")
        return True

    def deny(self, operation: Operation):
        """
        Refuse une opération.
        """
        self._audit(operation, "denied")
        log.warning(f"Opération refusée: {operation.name}")

    def _audit(self, operation: Operation, action: str):
        """
        Enregistre dans le journal d'audit.
        """
        entry = {
            "timestamp": "",  # Sera rempli
            "action": action,
            "operation": operation.name,
            "description": operation.description,
            "command": operation.command,
            "risk": operation.risk.name,
        }

        try:
            import datetime
            entry["timestamp"] = datetime.datetime.now().isoformat()

            with open(self.audit_log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            log.error(f"Audit log error: {e}")

    def get_audit_log(self, limit: int = 50) -> list[dict]:
        """Lit le journal d'audit."""
        if not self.audit_log_path.exists():
            return []

        entries = []
        try:
            with open(self.audit_log_path) as f:
                for line in f:
                    if line.strip():
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass

        return entries[-limit:]

    def what_will_happen(self, operation: Operation) -> str:
        """
        Explique ce qui va se passer en langage simple.
        """
        risk = self.evaluate_risk(operation)

        templates = {
            OperationRisk.SAFE:
                "Je vais simplement analyser. Aucune modification ne sera faite.",
            OperationRisk.LOW:
                "Je vais faire une petite réparation. C'est sans danger.",
            OperationRisk.MEDIUM:
                f"Je vais modifier le démarrage sur {', '.join(operation.affected_disks) or 'le disque'}.\n"
                f"Vos fichiers personnels ne seront pas touchés.",
            OperationRisk.HIGH:
                f"⚠️ Je vais modifier les partitions sur {', '.join(operation.affected_disks) or 'le disque'}.\n"
                f"Vos données seront préservées, mais le partitionnement change.",
            OperationRisk.DESTRUCTIVE:
                f"🔴 ATTENTION : Cette action va EFFACER toutes les données sur "
                f"{', '.join(operation.affected_disks) or 'le disque'}.\n"
                f"Cette action est IRRÉVERSIBLE. Sauvegardez vos données avant.",
        }

        return templates.get(risk, "Opération en attente.")


# ============================================================
# Safety Wrappers
# ============================================================
def safe_execute(command: str, dry_run: bool = False) -> dict:
    """
    Exécute une commande de manière sécurisée.
    Vérifie le risque avant exécution.
    """
    import subprocess

    security = SecurityManager()
    operation = Operation(
        name="shell_command",
        description=f"Exécution de: {command}",
        command=command,
    )

    risk = security.evaluate_risk(operation)

    if risk == OperationRisk.DESTRUCTIVE and not dry_run:
        return {
            "success": False,
            "error": "Cette opération destructive nécessite une confirmation explicite.",
            "risk": risk.name,
            "confirmation_required": True,
        }

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "command": command,
            "risk": risk.name,
            "message": f"[DRY RUN] {security.what_will_happen(operation)}",
        }

    # Exécution réelle
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=300
        )
        security._audit(operation, "executed" if result.returncode == 0 else "failed")
        return {
            "success": result.returncode == 0,
            "output": result.stdout[:5000],
            "error": result.stderr[:1000],
            "exit_code": result.returncode,
            "risk": risk.name,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout", "risk": risk.name}
    except Exception as e:
        return {"success": False, "error": str(e), "risk": risk.name}


# ============================================================
# Data discovery (pour montrer ce qui va être affecté)
# ============================================================
def discover_data_on_disk(mountpoint: str) -> dict:
    """
    Découvre les données sur un disque pour informer l'utilisateur
    AVANT une opération destructive.
    """
    stats = {
        "photos": 0,
        "documents": 0,
        "videos": 0,
        "music": 0,
        "archives": 0,
        "other": 0,
        "total_size_gb": 0,
    }

    photo_exts = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".raw", ".cr2", ".nef"}
    doc_exts = {".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf", ".xlsx", ".pptx"}
    video_exts = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}
    music_exts = {".mp3", ".flac", ".wav", ".aac", ".ogg", ".wma"}
    archive_exts = {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"}

    try:
        for root, dirs, files in os.walk(mountpoint):
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for fname in files:
                ext = Path(fname).suffix.lower()
                try:
                    size = os.path.getsize(os.path.join(root, fname))
                except OSError:
                    continue

                stats["total_size_gb"] += size / 1e9

                if ext in photo_exts:
                    stats["photos"] += 1
                elif ext in doc_exts:
                    stats["documents"] += 1
                elif ext in video_exts:
                    stats["videos"] += 1
                elif ext in music_exts:
                    stats["music"] += 1
                elif ext in archive_exts:
                    stats["archives"] += 1
                else:
                    stats["other"] += 1

    except Exception:
        pass

    return stats


# ============================================================
# CLI Test
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    sec = SecurityManager()

    # Test évaluation risque
    ops = [
        Operation("read", "Lecture disque", command="lsblk"),
        Operation("fix", "Réparation fsck", command="fsck -y /dev/sda1"),
        Operation("boot", "Install GRUB", command="grub-install /dev/sda"),
        Operation("partition", "Créer partition", command="parted /dev/sda mkpart"),
        Operation("format", "Formater disque", command="mkfs.ext4 /dev/sda1",
                  affected_disks=["/dev/sda"]),
    ]

    for op in ops:
        risk = sec.evaluate_risk(op)
        needs = sec.needs_confirmation(op)
        print(f"\n{op.name}:")
        print(f"  Commande: {op.command}")
        print(f"  Risque: {risk.name}")
        print(f"  Confirmation requise: {needs}")
        if needs:
            confirm_info = sec.request_confirmation(op)
            print(f"  Message: {confirm_info['title']}")
