"""
AI Rescue USB - Skill System
=============================
Système de plugins modulaire.
Chaque skill est un module autonome avec documentation, outils,
agents, scripts et tests.

Structure d'un skill:
    skills/
    └── skill_name/
        ├── __init__.py
        ├── skill.json       # Métadonnées
        ├── agent.py         # Logique principale
        ├── tools.py         # Outils spécifiques
        ├── README.md        # Documentation
        └── tests/           # Tests
            └── test_skill.py
"""

import importlib
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

log = logging.getLogger("skill-manager")


@dataclass
class SkillMetadata:
    """Métadonnées d'un skill."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = "AI Rescue Team"
    category: str = "general"
    dependencies: list = field(default_factory=list)
    os_support: list = field(default_factory=lambda: ["windows", "linux", "bsd"])
    min_ram_mb: int = 0
    offline_compatible: bool = True
    risk_level: str = "safe"  # safe/low/medium/high/destructive
    enabled: bool = True
    auto_load: bool = False


class Skill:
    """
    Un skill individuel - encapsule une capacité de l'IA Rescue.
    """

    def __init__(self, metadata: SkillMetadata, module_path: Path):
        self.metadata = metadata
        self.module_path = module_path
        self.loaded = False
        self._agent = None
        self._tools = {}

    def load(self) -> bool:
        """Charge le skill."""
        try:
            # Charger le module Python
            spec = importlib.util.spec_from_file_location(
                self.metadata.name,
                str(self.module_path / "__init__.py"),
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[self.metadata.name] = module
                spec.loader.exec_module(module)

                # Récupérer l'agent si présent
                if hasattr(module, "Agent"):
                    self._agent = module.Agent()

                # Récupérer les outils
                if hasattr(module, "TOOLS"):
                    self._tools = module.TOOLS

                self.loaded = True
                log.info(f"Skill chargé: {self.metadata.name}")
                return True
        except Exception as e:
            log.error(f"Échec chargement skill {self.metadata.name}: {e}")

        return False

    def execute(self, action: str, params: dict = None) -> dict:
        """Exécute une action du skill."""
        if not self.loaded:
            if not self.load():
                return {"success": False, "error": "Skill non chargé"}

        params = params or {}

        try:
            if self._agent and hasattr(self._agent, action):
                method = getattr(self._agent, action)
                result = method(**params)
                return {"success": True, "result": result}
            elif action in self._tools:
                tool = self._tools[action]
                result = tool(**params)
                return {"success": True, "result": result}
            else:
                return {"success": False, "error": f"Action '{action}' inconnue"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def unload(self):
        """Décharge le skill."""
        if self.metadata.name in sys.modules:
            del sys.modules[self.metadata.name]
        self.loaded = False
        self._agent = None
        self._tools = {}


class SkillManager:
    """
    Gestionnaire de skills.
    Découvre, charge, exécute et gère les skills.
    """

    def __init__(self, skills_dir: str = "/opt/ai-rescue/skills"):
        self.skills_dir = Path(skills_dir)
        self.skills: dict[str, Skill] = {}
        self.discover()

    def discover(self):
        """Découvre tous les skills disponibles."""
        if not self.skills_dir.exists():
            log.warning(f"Répertoire skills non trouvé: {self.skills_dir}")
            return

        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            metadata_file = skill_dir / "skill.json"
            if not metadata_file.exists():
                continue

            try:
                with open(metadata_file) as f:
                    data = json.load(f)

                metadata = SkillMetadata(
                    name=data.get("name", skill_dir.name),
                    version=data.get("version", "1.0.0"),
                    description=data.get("description", ""),
                    author=data.get("author", "AI Rescue Team"),
                    category=data.get("category", "general"),
                    dependencies=data.get("dependencies", []),
                    os_support=data.get("os_support", ["all"]),
                    min_ram_mb=data.get("min_ram_mb", 0),
                    offline_compatible=data.get("offline_compatible", True),
                    risk_level=data.get("risk_level", "safe"),
                    enabled=data.get("enabled", True),
                    auto_load=data.get("auto_load", False),
                )

                self.skills[metadata.name] = Skill(metadata, skill_dir)

                if metadata.auto_load:
                    self.skills[metadata.name].load()

            except Exception as e:
                log.error(f"Erreur chargement metadata {skill_dir}: {e}")

        log.info(f"Skills découverts: {len(self.skills)}")

    def list_skills(self, category: str = None) -> list[SkillMetadata]:
        """Liste les skills disponibles."""
        skills = []

        for skill in self.skills.values():
            if category and skill.metadata.category != category:
                continue
            skills.append(skill.metadata)

        return sorted(skills, key=lambda s: s.name)

    def get_skill(self, name: str) -> Optional[Skill]:
        """Récupère un skill par son nom."""
        return self.skills.get(name)

    def load_skill(self, name: str) -> bool:
        """Charge un skill spécifique."""
        skill = self.skills.get(name)
        if not skill:
            log.error(f"Skill inconnu: {name}")
            return False
        return skill.load()

    def unload_skill(self, name: str):
        """Décharge un skill."""
        skill = self.skills.get(name)
        if skill:
            skill.unload()

    def execute(self, skill_name: str, action: str, params: dict = None) -> dict:
        """Exécute une action d'un skill."""
        skill = self.skills.get(skill_name)
        if not skill:
            return {"success": False, "error": f"Skill '{skill_name}' non trouvé"}

        return skill.execute(action, params)

    def get_skills_by_os(self, os_type: str) -> list[SkillMetadata]:
        """Retourne les skills compatibles avec un OS."""
        return [
            s.metadata for s in self.skills.values()
            if "all" in s.metadata.os_support or os_type in s.metadata.os_support
        ]

    def get_offline_skills(self) -> list[SkillMetadata]:
        """Retourne les skills utilisables hors ligne."""
        return [
            s.metadata for s in self.skills.values()
            if s.metadata.offline_compatible
        ]


# ============================================================
# Built-in skills definitions
# ============================================================
BUILTIN_SKILLS = [
    {
        "name": "windows-repair",
        "version": "1.0.0",
        "description": "Réparation système Windows (boot, BCD, SFC, DISM)",
        "category": "repair",
        "os_support": ["windows"],
        "risk_level": "medium",
        "auto_load": False,
    },
    {
        "name": "linux-repair",
        "version": "1.0.0",
        "description": "Réparation système Linux (GRUB, fsck, packages)",
        "category": "repair",
        "os_support": ["linux"],
        "risk_level": "medium",
        "auto_load": False,
    },
    {
        "name": "bsd-repair",
        "version": "1.0.0",
        "description": "Réparation système BSD (boot, fsck, packages)",
        "category": "repair",
        "os_support": ["bsd"],
        "risk_level": "medium",
        "auto_load": False,
    },
    {
        "name": "backup-system",
        "version": "1.0.0",
        "description": "Sauvegarde et restauration complète du système",
        "category": "backup",
        "os_support": ["all"],
        "risk_level": "medium",
        "auto_load": False,
    },
    {
        "name": "file-recovery",
        "version": "1.0.0",
        "description": "Récupération de fichiers supprimés ou perdus",
        "category": "recovery",
        "os_support": ["all"],
        "risk_level": "low",
        "auto_load": False,
        "min_ram_mb": 1024,
    },
    {
        "name": "hardware-diagnostics",
        "version": "1.0.0",
        "description": "Diagnostic matériel complet (CPU, RAM, disques)",
        "category": "diagnostic",
        "os_support": ["all"],
        "risk_level": "safe",
        "auto_load": True,
        "offline_compatible": True,
    },
    {
        "name": "driver-manager",
        "version": "1.0.0",
        "description": "Gestion des pilotes matériel",
        "category": "system",
        "os_support": ["linux"],
        "risk_level": "low",
        "auto_load": False,
    },
    {
        "name": "network-repair",
        "version": "1.0.0",
        "description": "Réparation et diagnostic réseau",
        "category": "repair",
        "os_support": ["all"],
        "risk_level": "low",
        "auto_load": False,
        "offline_compatible": False,
    },
    {
        "name": "secure-erase",
        "version": "1.0.0",
        "description": "Effacement sécurisé de disques",
        "category": "security",
        "os_support": ["all"],
        "risk_level": "destructive",
        "auto_load": False,
    },
]

# ============================================================
# CLI Test
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("📦 AI Rescue USB - Skill System")
    print("=" * 50)
    print(f"\nSkills intégrés: {len(BUILTIN_SKILLS)}")

    for s in BUILTIN_SKILLS:
        icon = {"safe": "✅", "low": "🟢", "medium": "🟡", "high": "🟠", "destructive": "🔴"}
        print(f"\n  {icon.get(s['risk_level'], '❓')} {s['name']}")
        print(f"     {s['description']}")
        print(f"     OS: {', '.join(s['os_support'])} | "
              f"Offline: {'✓' if s.get('offline_compatible', True) else '✗'}")
