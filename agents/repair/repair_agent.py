"""
AI Rescue USB - Universal Repair Agent
=======================================
Agent de réparation universel pour Windows, Linux et BSD.
Détecte automatiquement le problème et propose la solution.
"""

import logging
import os
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

log = logging.getLogger("repair-agent")


class RepairStatus(Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    NEEDS_CONFIRMATION = "needs_confirmation"


class RiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class RepairAction:
    name: str
    description: str
    command: str
    risk: RiskLevel = RiskLevel.LOW
    reversible: bool = True
    timeout: int = 300
    os_filter: str = "all"  # windows/linux/bsd/all


@dataclass
class RepairResult:
    action: str
    success: bool
    output: str
    error: str
    time_taken: float


# ============================================================
# Windows Repair Actions
# ============================================================
WINDOWS_REPAIRS = [
    RepairAction(
        name="fix_mbr",
        description="Réparer le Master Boot Record (MBR)",
        command="bootrec /fixmbr",
        risk=RiskLevel.MEDIUM,
        os_filter="windows",
    ),
    RepairAction(
        name="fix_boot",
        description="Réparer le secteur de boot",
        command="bootrec /fixboot",
        risk=RiskLevel.MEDIUM,
        os_filter="windows",
    ),
    RepairAction(
        name="rebuild_bcd",
        description="Reconstruire la base de données de boot (BCD)",
        command="bootrec /rebuildbcd",
        risk=RiskLevel.MEDIUM,
        os_filter="windows",
    ),
    RepairAction(
        name="scan_os",
        description="Scanner les systèmes d'exploitation",
        command="bootrec /scanos",
        risk=RiskLevel.SAFE,
        os_filter="windows",
    ),
    RepairAction(
        name="sfc_scannow",
        description="Vérifier les fichiers système (SFC)",
        command="sfc /scannow /offbootdir=C:\\ /offwindir=C:\\Windows",
        risk=RiskLevel.SAFE,
        timeout=1800,
        os_filter="windows",
    ),
    RepairAction(
        name="dism_restorehealth",
        description="Restaurer l'image système (DISM)",
        command="dism /Image:C:\\ /Cleanup-Image /RestoreHealth",
        risk=RiskLevel.LOW,
        timeout=3600,
        os_filter="windows",
    ),
    RepairAction(
        name="chkdsk",
        description="Vérifier et réparer le disque (CHKDSK)",
        command="chkdsk C: /f /r",
        risk=RiskLevel.LOW,
        timeout=3600,
        os_filter="windows",
    ),
    RepairAction(
        name="fix_efi_windows",
        description="Réparer le démarrage EFI Windows",
        command="bcdboot C:\\Windows /s S: /f UEFI",
        risk=RiskLevel.MEDIUM,
        os_filter="windows",
    ),
    RepairAction(
        name="fix_efi_legacy",
        description="Réparer le démarrage Legacy Windows",
        command="bcdboot C:\\Windows /s C: /f BIOS",
        risk=RiskLevel.MEDIUM,
        os_filter="windows",
    ),
]

# ============================================================
# Linux Repair Actions
# ============================================================
LINUX_REPAIRS = [
    RepairAction(
        name="grub_install_efi",
        description="Réinstaller GRUB (EFI)",
        command="grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=GRUB",
        risk=RiskLevel.MEDIUM,
        os_filter="linux",
    ),
    RepairAction(
        name="grub_install_legacy",
        description="Réinstaller GRUB (Legacy)",
        command="grub-install --target=i386-pc /dev/sda",
        risk=RiskLevel.MEDIUM,
        os_filter="linux",
    ),
    RepairAction(
        name="update_grub",
        description="Mettre à jour la configuration GRUB",
        command="update-grub || grub-mkconfig -o /boot/grub/grub.cfg",
        risk=RiskLevel.SAFE,
        os_filter="linux",
    ),
    RepairAction(
        name="fsck_root",
        description="Vérifier le système de fichiers racine",
        command="fsck -f -y /dev/sda1",
        risk=RiskLevel.LOW,
        timeout=600,
        os_filter="linux",
    ),
    RepairAction(
        name="fix_packages_debian",
        description="Réparer les paquets cassés (Debian/Ubuntu)",
        command="apt-get update && apt-get --fix-broken install -y && dpkg --configure -a",
        risk=RiskLevel.LOW,
        timeout=600,
        os_filter="linux",
    ),
    RepairAction(
        name="fix_packages_arch",
        description="Réparer les paquets cassés (Arch)",
        command="pacman -Syu --noconfirm",
        risk=RiskLevel.LOW,
        timeout=600,
        os_filter="linux",
    ),
    RepairAction(
        name="fix_packages_fedora",
        description="Réparer les paquets cassés (Fedora)",
        command="dnf check && dnf distro-sync -y",
        risk=RiskLevel.LOW,
        timeout=600,
        os_filter="linux",
    ),
    RepairAction(
        name="regenerate_initramfs",
        description="Régénérer initramfs",
        command="mkinitcpio -P || update-initramfs -u -k all || dracut --force --regenerate-all",
        risk=RiskLevel.LOW,
        os_filter="linux",
    ),
]

# ============================================================
# BSD Repair Actions
# ============================================================
BSD_REPAIRS = [
    RepairAction(
        name="bsd_fsck",
        description="Vérifier le système de fichiers (fsck)",
        command="fsck -y",
        risk=RiskLevel.LOW,
        timeout=3600,
        os_filter="bsd",
    ),
    RepairAction(
        name="bsd_boot_repair",
        description="Réparer le chargeur de démarrage FreeBSD",
        command="gpart bootcode -b /boot/pmbr -p /boot/gptboot -i 1 ada0",
        risk=RiskLevel.MEDIUM,
        os_filter="bsd",
    ),
    RepairAction(
        name="bsd_pkg_check",
        description="Vérifier les paquets FreeBSD",
        command="pkg check -da",
        risk=RiskLevel.SAFE,
        timeout=600,
        os_filter="bsd",
    ),
]


class RepairAgent:
    """
    Agent de réparation universel.
    Détecte le problème et applique la réparation appropriée.
    """

    def __init__(self):
        self.all_repairs = WINDOWS_REPAIRS + LINUX_REPAIRS + BSD_REPAIRS
        self.results: list[RepairResult] = []

    def diagnose(self, os_type: str, symptoms: list[str]) -> list[RepairAction]:
        """
        Diagnostique le problème et retourne les réparations suggérées.
        """
        log.info(f"Diagnosing: OS={os_type}, symptoms={symptoms}")

        suggested = []
        symptoms_lower = [s.lower() for s in symptoms]

        # Filtrer par OS
        applicable = [r for r in self.all_repairs
                      if r.os_filter == "all" or r.os_filter == os_type]

        # Boot problems
        if any(w in " ".join(symptoms_lower) for w in
               ["boot", "démarre", "démarrage", "start", "grub", "bcd", "mbr", "efi"]):

            if os_type == "windows":
                suggested.extend([r for r in applicable if r.name in [
                    "scan_os", "fix_mbr", "fix_boot", "rebuild_bcd", "fix_efi_windows"
                ]])
            elif os_type == "linux":
                suggested.extend([r for r in applicable if r.name in [
                    "grub_install_efi", "grub_install_legacy", "update_grub",
                    "regenerate_initramfs",
                ]])
            elif os_type == "bsd":
                suggested.extend([r for r in applicable if r.name in [
                    "bsd_boot_repair",
                ]])

        # Filesystem problems
        if any(w in " ".join(symptoms_lower) for w in
               ["fichier", "file", "corrompu", "corrupt", "fsck", "chkdsk", "disk", "disque"]):

            if os_type == "windows":
                suggested.extend([r for r in applicable if r.name in ["chkdsk", "sfc_scannow"]])
            elif os_type == "linux":
                suggested.extend([r for r in applicable if r.name in ["fsck_root"]])
            elif os_type == "bsd":
                suggested.extend([r for r in applicable if r.name in ["bsd_fsck"]])

        # System file problems
        if any(w in " ".join(symptoms_lower) for w in
               ["système", "system", "sfc", "dism", "package", "paquet", "dll"]):

            if os_type == "windows":
                suggested.extend([r for r in applicable if r.name in [
                    "sfc_scannow", "dism_restorehealth"
                ]])
            elif os_type == "linux":
                suggested.extend([r for r in applicable if r.name in [
                    "fix_packages_debian", "fix_packages_arch", "fix_packages_fedora"
                ]])
            elif os_type == "bsd":
                suggested.extend([r for r in applicable if r.name in ["bsd_pkg_check"]])

        # Si rien trouvé, proposer un diagnostic complet
        if not suggested:
            suggested = [r for r in applicable if r.risk != RiskLevel.HIGH]

        return suggested[:5]  # Max 5 suggestions

    def execute_repair(self, action: RepairAction, dry_run: bool = False) -> RepairResult:
        """
        Exécute une action de réparation.
        """
        log.info(f"Executing repair: {action.name} - {action.description}")

        if dry_run:
            return RepairResult(
                action=action.description,
                success=True,
                output="[DRY RUN] Simulation réussie",
                error="",
                time_taken=0.0,
            )

        start = time.time()

        try:
            result = subprocess.run(
                action.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=action.timeout,
            )

            success = result.returncode == 0
            repair_result = RepairResult(
                action=action.description,
                success=success,
                output=result.stdout[:5000],
                error=result.stderr[:1000],
                time_taken=time.time() - start,
            )

        except subprocess.TimeoutExpired:
            repair_result = RepairResult(
                action=action.description,
                success=False,
                output="",
                error=f"Timeout après {action.timeout}s",
                time_taken=time.time() - start,
            )
        except Exception as e:
            repair_result = RepairResult(
                action=action.description,
                success=False,
                output="",
                error=str(e),
                time_taken=time.time() - start,
            )

        self.results.append(repair_result)
        return repair_result

    def auto_repair(self, os_type: str, symptoms: list[str],
                    dry_run: bool = False, confirm: bool = True) -> list[RepairResult]:
        """
        Réparation automatique complète.
        Diagnostique et exécute séquentiellement.
        """
        log.info(f"Auto-repair: OS={os_type}, symptoms={symptoms}")

        # Étape 1: Diagnostic
        actions = self.diagnose(os_type, symptoms)

        # Étape 2: Filtrer les actions risquées
        safe_actions = [a for a in actions if a.risk in (RiskLevel.SAFE, RiskLevel.LOW)]
        medium_actions = [a for a in actions if a.risk == RiskLevel.MEDIUM]

        # Étape 3: Exécuter safe d'abord
        results = []
        for action in safe_actions:
            result = self.execute_repair(action, dry_run=dry_run)
            results.append(result)
            log.info(f"  {action.name}: {'✓' if result.success else '✗'}")

        # Étape 4: Exécuter medium avec confirmation si demandé
        for action in medium_actions:
            if confirm and not dry_run:
                log.info(f"  Action risquée: {action.description}")
                log.info(f"  Commande: {action.command}")
                # En mode interactif, demander confirmation
                # Pour l'instant, on skip
                log.info("  [SKIP - confirmation requise]")
                results.append(RepairResult(
                    action=action.description,
                    success=False,
                    output="",
                    error="Confirmation requise",
                    time_taken=0,
                ))
            else:
                result = self.execute_repair(action, dry_run=dry_run)
                results.append(result)

        return results

    def summary(self) -> str:
        """Génère un résumé des réparations."""
        lines = [
            "=" * 50,
            "  RAPPORT DE RÉPARATION",
            "=" * 50,
            "",
        ]

        for r in self.results:
            status = "✓" if r.success else "✗"
            lines.append(f"  {status} {r.action} ({r.time_taken:.1f}s)")
            if r.error:
                lines.append(f"     Erreur: {r.error[:100]}")

        success_count = sum(1 for r in self.results if r.success)
        total = len(self.results)
        lines.extend([
            "",
            f"Résultat: {success_count}/{total} réparations réussies",
            "=" * 50,
        ])

        return "\n".join(lines)


# ============================================================
# CLI Test
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    agent = RepairAgent()

    # Test diagnostic
    print("=== Diagnostic Windows Boot ===")
    actions = agent.diagnose("windows", ["ne démarre plus", "boot error"])
    for a in actions:
        print(f"  - {a.name}: {a.description} (risque: {a.risk.value})")

    print("\n=== Diagnostic Linux Boot ===")
    actions = agent.diagnose("linux", ["grub rescue", "no boot device"])
    for a in actions:
        print(f"  - {a.name}: {a.description} (risque: {a.risk.value})")

    print("\n=== Auto-repair (dry run) ===")
    results = agent.auto_repair("windows", ["boot problem"], dry_run=True)
    print(agent.summary())
