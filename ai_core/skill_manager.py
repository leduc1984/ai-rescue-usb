"""
AI Rescue USB - Skill Manager
=============================
Système extensible de plugins modulaires.
Chaque skill = un ensemble de capabilities (OEM, diagnostic, réparation)
"""

import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

log = logging.getLogger("skill-manager")


class SkillStatus(Enum):
    """État d'un skill."""
    AVAILABLE = "available"      # Installé et prêt
    DOWNLOADING = "downloading"  # En cours de téléchargement
    INSTALLED = "installed"      # Installé mais pas encore chargé
    LOADED = "loaded"            # Chargé en mémoire
    ERROR = "error"              # Erreur de chargement
    MISSING = "missing"          # Non installé


@dataclass
class SkillRequirement:
    """Exigences d'un skill."""
    min_ram_mb: int = 0
    min_disk_mb: int = 0
    os_filter: list = field(default_factory=list)  # ["windows", "linux", "bsd"]
    packages: list = field(default_factory=list)   # paquets système requis
    hardware: list = field(default_factory=list)    # matériel spécifique requis


@dataclass
class SkillMetadata:
    """Métadonnées d'un skill."""
    id: str
    name: str
    version: str
    description: str
    category: str  # repair, install, backup, recovery, driver, diagnostic
    author: str = "AI Rescue Team"
    size_mb: int = 0
    requirements: SkillRequirement = field(default_factory=SkillRequirement)
    entry_point: str = ""  # module:Class
    icon: str = ""  # emoji ou chemin icône
    documentation: str = ""
    tools: list = field(default_factory=list)
    agents: list = field(default_factory=list)
    scripts: list = field(default_factory=list)
    tests: list = field(default_factory=list)


class Skill:
    """Un skill chargeable."""

    def __init__(self, metadata: SkillMetadata, skill_dir: Path):
        self.metadata = metadata
        self.skill_dir = skill_dir
        self.module = None
        self.instance = None
        self.status = SkillStatus.AVAILABLE

    def load(self) -> bool:
        """
        Charge le skill en mémoire.
        """
        log.info(f"Loading skill: {self.metadata.name}")

        try:
            # Vérifier les requirements
            if not self._check_requirements():
                log.warning(f"Requirements not met for {self.metadata.name}")
                return False

            # Charger le module Python si entry_point défini
            if self.metadata.entry_point:
                module_name, class_name = self.metadata.entry_point.split(":")
                skill_file = self.skill_dir / f"{module_name}.py"

                if skill_file.exists():
                    import sys
                    sys.path.insert(0, str(self.skill_dir))

                    import importlib.util
                    spec = importlib.util.spec_from_file_location(module_name, skill_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    self.module = module

                    if hasattr(module, class_name):
                        self.instance = getattr(module, class_name)()
                        log.info(f"Skill loaded successfully: {self.metadata.name}")
                        self.status = SkillStatus.LOADED
                        return True
                else:
                    log.warning(f"Entry point not found: {skill_file}")

            # Si pas de entry_point, marquer quand même comme chargé
            self.status = SkillStatus.LOADED
            return True

        except Exception as e:
            log.error(f"Failed to load skill {self.metadata.name}: {e}")
            self.status = SkillStatus.ERROR
            return False

    def _check_requirements(self) -> bool:
        """Vérifie que les requirements du skill sont satisfaites."""
        req = self.metadata.requirements

        # Vérifier RAM
        try:
            import psutil
            available_ram = psutil.virtual_memory().available // (1024 * 1024)
            if available_ram < req.min_ram_mb:
                log.warning(f"Insufficient RAM: {available_ram}MB < {req.min_ram_mb}MB")
                return False
        except ImportError:
            pass

        # Vérifier packages système
        for pkg in req.packages:
            result = subprocess.run(
                ["which", pkg],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                log.warning(f"Required package not found: {pkg}")
                return False

        return True

    def execute(self, action: str, params: dict = None) -> dict:
        """
        Exécute une action du skill.
        """
        if self.status != SkillStatus.LOADED:
            return {
                "success": False,
                "error": f"Skill not loaded (status: {self.status.value})"
            }

        if not self.instance:
            return {
                "success": False,
                "error": "Skill instance not available"
            }

        # Chercher la méthode
        method = getattr(self.instance, action, None)
        if not method or not callable(method):
            return {
                "success": False,
                "error": f"Action not found: {action}"
            }

        # Exécuter
        try:
            import inspect
            sig = inspect.signature(method)
            kwargs = params or {}
            filtered_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
            result = method(**filtered_kwargs)
            return result

        except Exception as e:
            log.error(f"Skill execution error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def unload(self):
        """Décharge le skill de la mémoire."""
        self.module = None
        self.instance = None
        self.status = SkillStatus.AVAILABLE
        log.info(f"Skill unloaded: {self.metadata.name}")


class SkillManager:
    """
    Gestionnaire de skills.
    Gère l'installation, le chargement et l'exécution des skills.
    """

    def __init__(self, skills_root: Path):
        self.skills_root = skills_root
        self.skills_root.mkdir(parents=True, exist_ok=True)
        self.skills: dict[str, Skill] = {}
        self.metadata_file = self.skills_root / "skills.json"
        self._load_metadata()

    def _load_metadata(self):
        """Charge le catalogue des skills disponibles."""
        if not self.metadata_file.exists():
            self._generate_default_catalog()
            return

        try:
            with open(self.metadata_file) as f:
                data = json.load(f)

            for skill_data in data.get("skills", []):
                metadata = SkillMetadata(**skill_data)
                skill_dir = self.skills_root / metadata.category / metadata.id
                skill = Skill(metadata, skill_dir)
                self.skills[metadata.id] = skill

        except Exception as e:
            log.error(f"Failed to load metadata: {e}")
            self._generate_default_catalog()

    def _generate_default_catalog(self):
        """Génère le catalogue de skills par défaut."""
        default_skills = [
            SkillMetadata(
                id="windows-repair",
                name="Windows Repair",
                version="1.0.0",
                description="Réparation Windows : boot, BCD, SFC, DISM",
                category="repair",
                size_mb=50,
                entry_point="windows_repair:WindowsRepairSkill",
                requirements=SkillRequirement(min_ram_mb=512),
            ),
            SkillMetadata(
                id="linux-repair",
                name="Linux Repair",
                version="1.0.0",
                description="Réparation Linux : GRUB, fsck, paquets",
                category="repair",
                size_mb=40,
                entry_point="linux_repair:LinuxRepairSkill",
                requirements=SkillRequirement(min_ram_mb=512),
            ),
            SkillMetadata(
                id="bsd-repair",
                name="BSD Repair",
                version="1.0.0",
                description="Réparation FreeBSD/OpenBSD",
                category="repair",
                size_mb=35,
                entry_point="bsd_repair:BSDRepairSkill",
                requirements=SkillRequirement(min_ram_mb=512),
            ),
            SkillMetadata(
                id="universal-installer",
                name="Universal Installer",
                version="1.0.0",
                description="Installation d'OS : Windows, Linux, BSD",
                category="install",
                size_mb=100,
                entry_point="universal_installer:UniversalInstallerSkill",
                requirements=SkillRequirement(min_ram_mb=1024),
            ),
            SkillMetadata(
                id="backup-system",
                name="Backup System",
                version="1.0.0",
                description="Sauvegarde et restauration de fichiers",
                category="backup",
                size_mb=30,
                entry_point="backup_system:BackupSystemSkill",
                requirements=SkillRequirement(min_ram_mb=512),
            ),
            SkillMetadata(
                id="file-recovery",
                name="File Recovery",
                version="1.0.0",
                description="Récupération de fichiers supprimés",
                category="recovery",
                size_mb=60,
                entry_point="file_recovery:FileRecoverySkill",
                requirements=SkillRequirement(min_ram_mb=1024),
                tools=["testdisk", "photorec", "ddrescue"],
            ),
            SkillMetadata(
                id="hardware-diagnostics",
                name="Hardware Diagnostics",
                version="1.0.0",
                description="Tests matériels : CPU, RAM, disques, réseau",
                category="diagnostic",
                size_mb=45,
                entry_point="hardware_diagnostics:HardwareDiagnosticsSkill",
                requirements=SkillRequirement(min_ram_mb=512),
            ),
            SkillMetadata(
                id="driver-manager",
                name="Driver Manager",
                version="1.0.0",
                description="Gestion des pilotes matériels",
                category="driver",
                size_mb=80,
                entry_point="driver_manager:DriverManagerSkill",
                requirements=SkillRequirement(min_ram_mb=1024),
            ),
            SkillMetadata(
                id="network-repair",
                name="Network Repair",
                version="1.0.0",
                description="Diagnostic et réparation réseau",
                category="repair",
                size_mb=25,
                entry_point="network_repair:NetworkRepairSkill",
                requirements=SkillRequirement(min_ram_mb=256),
            ),
            SkillMetadata(
                id="secure-erase",
                name="Secure Erase",
                version="1.0.0",
                description="Effacement sécurisé de disques",
                category="recovery",
                size_mb=20,
                entry_point="secure_erase:SecureEraseSkill",
                requirements=SkillRequirement(min_ram_mb=256),
            ),
        ]

        catalog = {"skills": [s.__dict__ for s in default_skills]}

        try:
            with open(self.metadata_file, "w") as f:
                json.dump(catalog, f, indent=2, ensure_ascii=False)
            log.info(f"Default catalog generated: {len(default_skills)} skills")
        except Exception as e:
            log.error(f"Failed to generate catalog: {e}")

    def list_available(self, category: Optional[str] = None) -> list[SkillMetadata]:
        """Liste les skills disponibles."""
        skills = []
        for skill in self.skills.values():
            if category is None or skill.metadata.category == category:
                skills.append(skill.metadata)
        return skills

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Récupère un skill par son ID."""
        return self.skills.get(skill_id)

    def install_skill(self, skill_id: str, source_url: Optional[str] = None) -> dict:
        """
        Installe un skill.
        Télécharge ou copie depuis une source locale.
        """
        skill = self.skills.get(skill_id)

        if not skill:
            return {"success": False, "error": f"Skill not found: {skill_id}"}

        if skill.status == SkillStatus.LOADED:
            return {"success": True, "message": "Skill already installed and loaded"}

        if source_url:
            # Télécharger depuis URL
            return self._download_skill(skill, source_url)
        else:
            # Skill local (déjà présent sur la clé)
            return self._install_local_skill(skill)

    def _download_skill(self, skill: Skill, url: str) -> dict:
        """Télécharge un skill depuis une URL."""
        skill.status = SkillStatus.DOWNLOADING
        target_dir = skill.skill_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        archive_path = target_dir / f"{skill.metadata.id}.tar.gz"

        try:
            # Télécharger l'archive
            result = subprocess.run(
                ["wget", "-q", "-O", str(archive_path), url],
                timeout=300, check=True, capture_output=True, text=True,
            )

            # Extraire
            subprocess.run(
                ["tar", "-xzf", str(archive_path), "-C", str(target_dir)],
                check=True, capture_output=True, text=True,
            )

            # Nettoyer l'archive
            archive_path.unlink()

            skill.status = SkillStatus.INSTALLED
            log.info(f"Skill installed: {skill.metadata.id}")

            return {
                "success": True,
                "message": f"Skill {skill.metadata.id} installed successfully"
            }

        except Exception as e:
            skill.status = SkillStatus.ERROR
            log.error(f"Failed to download skill: {e}")
            return {"success": False, "error": str(e)}

    def _install_local_skill(self, skill: Skill) -> dict:
        """Installe un skill local (déjà présent)."""
        if not skill.skill_dir.exists():
            return {
                "success": False,
                "error": f"Skill directory not found: {skill.skill_dir}"
            }

        skill.status = SkillStatus.INSTALLED
        log.info(f"Local skill ready: {skill.metadata.id}")

        return {
            "success": True,
            "message": f"Skill {skill.metadata.id} ready for loading"
        }

    def load_skill(self, skill_id: str) -> dict:
        """Charge un skill en mémoire."""
        skill = self.skills.get(skill_id)

        if not skill:
            return {"success": False, "error": f"Skill not found: {skill_id}"}

        if skill.status == SkillStatus.LOADED:
            return {"success": True, "message": "Skill already loaded"}

        if skill.status not in (SkillStatus.AVAILABLE, SkillStatus.INSTALLED):
            return {
                "success": False,
                "error": f"Skill not ready (status: {skill.status.value})"
            }

        success = skill.load()

        if success:
            return {"success": True, "message": "Skill loaded successfully"}
        else:
            return {"success": False, "error": f"Failed to load skill {skill_id}"}

    def unload_skill(self, skill_id: str) -> dict:
        """Décharge un skill de la mémoire."""
        skill = self.skills.get(skill_id)

        if not skill:
            return {"success": False, "error": f"Skill not found: {skill_id}"}

        if skill.status != SkillStatus.LOADED:
            return {"success": True, "message": "Skill not loaded"}

        skill.unload()
        return {"success": True, "message": "Skill unloaded successfully"}

    def load_recommended_skills(self, hardware_info: dict) -> list[str]:
        """
        Charge automatiquement les skills recommandés en fonction du matériel.
        """
        recommended = []

        # Basé sur le matériel détecté
        # (logique simplifiée, peut être améliorée)

        for skill in self.skills.values():
            # Vérifier les requirements
            req = skill.metadata.requirements

            if req.min_ram_mb > hardware_info.get("ram_mb", 0):
                continue

            # Auto-load pour les catégories courantes
            if skill.metadata.category in ("repair", "diagnostic"):
                try:
                    self.load_skill(skill.metadata.id)
                    recommended.append(skill.metadata.id)
                except Exception as e:
                    log.warning(f"Failed to auto-load {skill.metadata.id}: {e}")

        return recommended

    def execute_skill_action(self, skill_id: str, action: str, params: dict = None) -> dict:
        """
        Exécute une action d'un skill.
        Charge automatiquement le skill si nécessaire.
        """
        skill = self.skills.get(skill_id)

        if not skill:
            return {"success": False, "error": f"Skill not found: {skill_id}"}

        # Charger si pas déjà chargé
        if skill.status != SkillStatus.LOADED:
            load_result = self.load_skill(skill_id)
            if not load_result["success"]:
                return load_result

        # Exécuter l'action
        return skill.execute(action, params)

    def get_skill_info(self, skill_id: str) -> dict:
        """Récupère les informations détaillées d'un skill."""
        skill = self.skills.get(skill_id)

        if not skill:
            return {"error": "Skill not found"}

        return {
            "id": skill.metadata.id,
            "name": skill.metadata.name,
            "version": skill.metadata.version,
            "description": skill.metadata.description,
            "category": skill.metadata.category,
            "status": skill.status.value,
            "size_mb": skill.metadata.size_mb,
            "requirements": skill.metadata.requirements.__dict__,
            "tools": skill.metadata.tools,
        }


# ============================================================
# Instance globale
# ============================================================
_skill_manager: Optional[SkillManager] = None


def get_skill_manager(skills_root: Path = None) -> SkillManager:
    """Récupère l'instance globale du gestionnaire de skills."""
    global _skill_manager
    if _skill_manager is None:
        if skills_root is None:
            skills_root = Path("/opt/ai-rescue/skills")
        _skill_manager = SkillManager(skills_root)
    return _skill_manager


# ============================================================
# Test
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Créer un répertoire temporaire pour tester
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())

    manager = SkillManager(temp_dir)

    print("=== Skills disponibles ===")
    for skill_meta in manager.list_available():
        print(f"  - {skill_meta.name} ({skill_meta.category})")

    print("\n=== Informations windows-repair ===")
    info = manager.get_skill_info("windows-repair")
    print(json.dumps(info, indent=2, ensure_ascii=False))

    # Nettoyer
    shutil.rmtree(temp_dir)
