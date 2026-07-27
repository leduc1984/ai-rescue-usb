"""
AI Rescue USB - Core AI Engine
================================
Le cerveau central qui orchestre la détection, le diagnostic,
la planification et l'exécution des réparations.

Architecture:
    User Input → LLM → Goal Analyzer → Planner → Agent Manager → Executor → Verification
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

# ============================================================
# Logging setup
# ============================================================
def _resolve_log_path() -> Path:
    """Use /var/log on the live rescue system; fall back to a local logs/ dir elsewhere (e.g. dev machines, Windows)."""
    var_log = Path("/var/log/ai-rescue.log")
    if var_log.parent.is_dir() and os.access(var_log.parent, os.W_OK):
        return var_log
    fallback_dir = Path(__file__).resolve().parent.parent / "logs"
    fallback_dir.mkdir(parents=True, exist_ok=True)
    return fallback_dir / "ai-rescue.log"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(_resolve_log_path())],
)
log = logging.getLogger("ai-rescue")

# ============================================================
# Data models
# ============================================================
class ActionType(Enum):
    """Types d'actions que l'IA peut exécuter."""
    DETECT_HARDWARE = "detect_hardware"
    DETECT_OS = "detect_os"
    DIAGNOSE = "diagnose"
    REPAIR = "repair"
    INSTALL = "install"
    BACKUP = "backup"
    RESTORE = "restore"
    RECOVER = "recover"
    CONFIGURE = "configure"
    VERIFY = "verify"


class RiskLevel(Enum):
    """Niveau de risque d'une action."""
    SAFE = "safe"           # Lecture seule, aucun risque
    LOW = "low"             # Modification mineure
    MEDIUM = "medium"       # Modification significative
    HIGH = "high"           # Peut causer une perte de données
    DESTRUCTIVE = "destructive"  # Formatage, suppression définitive


@dataclass
class Action:
    """Une action à exécuter."""
    type: ActionType
    description: str
    command: Optional[str] = None
    risk: RiskLevel = RiskLevel.SAFE
    requires_confirmation: bool = False
    timeout: int = 300
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class Goal:
    """Objectif décomposé que l'IA doit accomplir."""
    user_request: str
    goal_type: ActionType
    actions: list[Action] = field(default_factory=list)
    estimated_time: int = 60  # secondes
    status: str = "pending"
    result: Optional[str] = None


@dataclass
class HardwareInfo:
    """Information matérielle détectée."""
    cpu: dict = field(default_factory=dict)
    ram: dict = field(default_factory=dict)
    gpu: list = field(default_factory=list)
    disks: list = field(default_factory=list)
    network: list = field(default_factory=list)
    usb: list = field(default_factory=list)
    audio: list = field(default_factory=list)
    bios: str = "unknown"  # uefi / legacy
    secure_boot: bool = False


@dataclass
class OSInfo:
    """Systèmes d'exploitation détectés."""
    detected: list = field(default_factory=list)
    partitions: list = field(default_factory=list)
    bootloader: str = "unknown"
    boot_status: str = "unknown"  # ok / broken / missing


# ============================================================
# LLM Interface - Local model loader
# ============================================================
class LocalLLM:
    """
    Gère le chargement et l'inférence de modèles LLM locaux.
    Supporte llama.cpp, MLX, et ONNX pour une compatibilité maximale.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = Path(model_path) if model_path else self._resolve_model_path()
        self.model = None
        self.tokenizer = None
        self.loaded = False
        self.backend = self._detect_backend()

    @staticmethod
    def _resolve_model_path() -> Path:
        """/opt/ai-rescue/models on the live rescue system; a local models/ dir elsewhere."""
        env_path = os.environ.get("AI_RESCUE_MODELS_DIR")
        if env_path:
            return Path(env_path)
        opt_path = Path("/opt/ai-rescue/models")
        if opt_path.is_dir():
            return opt_path
        return Path(__file__).resolve().parent.parent / "models"

    def _detect_backend(self) -> str:
        """Détecte quel backend LLM est disponible."""
        # Priorité: llama.cpp > onnx > fallback
        try:
            import llama_cpp  # noqa: F401
            return "llamacpp"
        except ImportError:
            pass
        try:
            import onnxruntime  # noqa: F401
            return "onnx"
        except ImportError:
            pass
        return "fallback"

    def load_model(self, model_name: str = "llama-3.2-3b-q4.gguf"):
        """Charge un modèle local. À défaut du nom demandé, prend le premier .gguf trouvé."""
        model_file = self.model_path / model_name
        if not model_file.exists() and self.model_path.is_dir():
            found = next(self.model_path.glob("*.gguf"), None)
            if found:
                log.info(f"{model_name} introuvable, utilisation de {found.name} à la place")
                model_file = found

        log.info(f"Loading model: {model_file} (backend: {self.backend})")

        if self.backend == "llamacpp":
            self._load_llamacpp(model_file)
        elif self.backend == "onnx":
            self._load_onnx(model_file)
        else:
            log.warning("No LLM backend available, using rule-based system")
            self.loaded = False

    def _load_llamacpp(self, model_file: Path):
        """Charge via llama.cpp."""
        try:
            from llama_cpp import Llama

            self.model = Llama(
                model_path=str(model_file),
                n_ctx=2048,
                n_threads=os.cpu_count() or 4,
                n_gpu_layers=0,  # CPU par défaut
                verbose=False,
            )
            self.loaded = True
            log.info(f"Model loaded: {model_file.name}")
        except Exception as e:
            log.error(f"Failed to load model: {e}")
            self.loaded = False

    def _load_onnx(self, model_file: Path):
        """Charge via ONNX Runtime."""
        log.info("ONNX backend not fully implemented, using fallback")
        self.loaded = False

    def generate(self, prompt: str, max_tokens: int = 256, system: Optional[str] = None) -> str:
        """Génère une réponse à partir du prompt.

        Utilise l'API chat (pas la complétion brute) : llama-cpp-python applique
        automatiquement le chat template embarqué dans le GGUF, ce qui donne des
        réponses cohérentes au lieu du modèle qui continue le texte au hasard.
        """
        if self.loaded and self.backend == "llamacpp":
            try:
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})

                output = self.model.create_chat_completion(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.7,
                )
                return output["choices"][0]["message"]["content"].strip()
            except Exception as e:
                log.error(f"Generation error: {e}")

        # Fallback: réponse basée sur des règles
        return self._rule_based_response(prompt)

    def _rule_based_response(self, prompt: str) -> str:
        """Système de règles basique quand aucun LLM n'est disponible."""
        prompt_lower = prompt.lower()

        if any(w in prompt_lower for w in ["répare", "repair", "fix", "boot", "démarre"]):
            return json.dumps({
                "goal": "repair_boot",
                "plan": [
                    "analyze_boot_sector",
                    "detect_operating_systems",
                    "repair_bootloader",
                    "verify_boot",
                ],
                "confidence": 0.8,
            })
        elif any(w in prompt_lower for w in ["installe", "install", "linux", "windows"]):
            return json.dumps({
                "goal": "install_os",
                "plan": [
                    "analyze_hardware",
                    "check_compatibility",
                    "suggest_os",
                    "download_iso",
                    "install",
                ],
                "confidence": 0.75,
            })
        elif any(w in prompt_lower for w in ["sauvegarde", "backup", "sauver"]):
            return json.dumps({
                "goal": "backup",
                "plan": [
                    "detect_disks",
                    "analyze_usage",
                    "select_backup_strategy",
                    "execute_backup",
                ],
                "confidence": 0.85,
            })
        elif any(w in prompt_lower for w in ["récupère", "recover", "perdu", "lost"]):
            return json.dumps({
                "goal": "recover_files",
                "plan": [
                    "scan_disk",
                    "find_recoverable",
                    "preview_results",
                    "recover_selected",
                ],
                "confidence": 0.7,
            })
        elif any(w in prompt_lower for w in ["diagnostique", "diagnose", "problème"]):
            return json.dumps({
                "goal": "diagnose",
                "plan": [
                    "run_hardware_tests",
                    "check_disk_health",
                    "analyze_logs",
                    "generate_report",
                ],
                "confidence": 0.9,
            })
        else:
            return json.dumps({
                "goal": "understand_request",
                "plan": ["clarify_with_user"],
                "confidence": 0.3,
            })


# ============================================================
# Goal Analyzer - Analyse la demande utilisateur
# ============================================================
class GoalAnalyzer:
    """
    Transforme une demande en langage naturel en objectif structuré.
    """

    def __init__(self, llm: LocalLLM):
        self.llm = llm

    async def analyze(self, user_input: str) -> Goal:
        """Analyse la demande et crée un Goal structuré."""
        log.info(f"Analyzing: {user_input}")

        prompt = f"""You are an AI computer technician. Analyze this user request and return a JSON goal:

User: {user_input}

Return JSON with these fields:
- goal_type: one of [detect_hardware, detect_os, diagnose, repair, install, backup, restore, recover, configure]
- description: short description
- estimated_time: seconds
- requires_confirmation: boolean

Response:"""

        response = self.llm.generate(prompt)

        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            # Fallback analysis
            data = self._fallback_analysis(user_input)

        return Goal(
            user_request=user_input,
            goal_type=ActionType(data.get("goal_type", "diagnose")),
            estimated_time=data.get("estimated_time", 60),
        )

    def _fallback_analysis(self, user_input: str) -> dict:
        """Analyse basique par mots-clés."""
        inp = user_input.lower()
        if any(w in inp for w in ["répare", "repair", "fix"]):
            return {"goal_type": "repair", "description": "Réparation système"}
        elif any(w in inp for w in ["installe", "install"]):
            return {"goal_type": "install", "description": "Installation OS"}
        elif any(w in inp for w in ["sauvegarde", "backup"]):
            return {"goal_type": "backup", "description": "Sauvegarde"}
        elif any(w in inp for w in ["récupère", "recover", "perdu"]):
            return {"goal_type": "recover", "description": "Récupération fichiers"}
        elif any(w in inp for w in ["diagnostique", "diagnose", "problème"]):
            return {"goal_type": "diagnose", "description": "Diagnostic"}
        else:
            return {"goal_type": "diagnose", "description": "Analyse générale"}


# ============================================================
# Planner - Crée un plan d'actions
# ============================================================
class Planner:
    """
    Décompose un Goal en séquence d'Actions exécutables.
    """

    def __init__(self, llm: LocalLLM):
        self.llm = llm

    async def plan(self, goal: Goal, context: dict) -> list[Action]:
        """Crée le plan d'actions pour accomplir l'objectif."""
        log.info(f"Planning for goal: {goal.goal_type.value}")

        actions = []

        # Phase 1: Toujours détecter le matériel d'abord
        actions.append(Action(
            type=ActionType.DETECT_HARDWARE,
            description="Détection du matériel",
            risk=RiskLevel.SAFE,
        ))

        # Phase 2: Détecter les OS présents
        actions.append(Action(
            type=ActionType.DETECT_OS,
            description="Détection des systèmes d'exploitation",
            risk=RiskLevel.SAFE,
        ))

        # Phase 3: Actions spécifiques selon le goal
        if goal.goal_type == ActionType.REPAIR:
            actions.extend(self._plan_repair(context))
        elif goal.goal_type == ActionType.INSTALL:
            actions.extend(self._plan_install(context))
        elif goal.goal_type == ActionType.BACKUP:
            actions.extend(self._plan_backup(context))
        elif goal.goal_type == ActionType.RECOVER:
            actions.extend(self._plan_recover(context))

        # Phase finale: Vérification
        actions.append(Action(
            type=ActionType.VERIFY,
            description="Vérification des résultats",
            risk=RiskLevel.SAFE,
        ))

        return actions

    def _plan_repair(self, context: dict) -> list[Action]:
        """Planifie une réparation selon l'OS détecté."""
        os_info = context.get("os_info", {})
        detected = os_info.get("detected", [])

        actions = []

        if "windows" in [o.lower() for o in detected]:
            actions.extend([
                Action(type=ActionType.REPAIR, description="Vérification boot Windows",
                       command="bootrec /fixmbr && bootrec /fixboot && bootrec /rebuildbcd",
                       risk=RiskLevel.MEDIUM, requires_confirmation=True),
                Action(type=ActionType.REPAIR, description="Réparation EFI Windows",
                       command="bcdboot C:\\Windows /s S: /f UEFI",
                       risk=RiskLevel.MEDIUM),
                Action(type=ActionType.REPAIR, description="Vérification disque Windows",
                       command="chkdsk C: /f /r",
                       risk=RiskLevel.LOW, timeout=600),
            ])
        elif "linux" in [o.lower() for o in detected]:
            actions.extend([
                Action(type=ActionType.REPAIR, description="Réparation GRUB",
                       command="grub-install --target=x86_64-efi --efi-directory=/boot/efi && update-grub",
                       risk=RiskLevel.MEDIUM, requires_confirmation=True),
                Action(type=ActionType.REPAIR, description="Vérification fsck",
                       command="fsck -f -y /dev/sda1",
                       risk=RiskLevel.LOW, timeout=600),
            ])

        return actions

    def _plan_install(self, context: dict) -> list[Action]:
        """Planifie une installation d'OS."""
        return [
            Action(type=ActionType.INSTALL, description="Vérification compatibilité matérielle",
                   risk=RiskLevel.SAFE),
            Action(type=ActionType.INSTALL, description="Téléchargement ISO",
                   risk=RiskLevel.SAFE, timeout=1800),
            Action(type=ActionType.INSTALL, description="Vérification intégrité ISO",
                   risk=RiskLevel.SAFE),
            Action(type=ActionType.INSTALL, description="Préparation partitionnement",
                   risk=RiskLevel.DESTRUCTIVE, requires_confirmation=True),
            Action(type=ActionType.INSTALL, description="Installation système",
                   risk=RiskLevel.DESTRUCTIVE, timeout=3600),
        ]

    def _plan_backup(self, context: dict) -> list[Action]:
        """Planifie une sauvegarde."""
        return [
            Action(type=ActionType.BACKUP, description="Analyse espace disque",
                   risk=RiskLevel.SAFE),
            Action(type=ActionType.BACKUP, description="Sélection stratégie sauvegarde",
                   risk=RiskLevel.SAFE),
            Action(type=ActionType.BACKUP, description="Sauvegarde fichiers",
                   risk=RiskLevel.LOW, timeout=3600),
        ]

    def _plan_recover(self, context: dict) -> list[Action]:
        """Planifie une récupération de fichiers."""
        return [
            Action(type=ActionType.RECOVER, description="Scan surface disque",
                   risk=RiskLevel.SAFE, timeout=1800),
            Action(type=ActionType.RECOVER, description="Recherche fichiers récupérables",
                   risk=RiskLevel.SAFE, timeout=600),
            Action(type=ActionType.RECOVER, description="Récupération fichiers",
                   risk=RiskLevel.LOW, timeout=3600),
        ]


# ============================================================
# Executor - Exécute les actions
# ============================================================
class Executor:
    """
    Exécute les actions planifiées dans un environnement sécurisé.
    """

    def __init__(self):
        self.history: list[dict] = []

    async def execute(self, action: Action) -> dict:
        """Exécute une action et retourne le résultat."""
        log.info(f"Executing: {action.description}")

        start_time = time.time()

        try:
            if action.command:
                result = await self._run_command(action.command, action.timeout)
            else:
                result = {"success": True, "output": "Action symbolique exécutée"}

            elapsed = time.time() - start_time
            self.history.append({
                "action": action.description,
                "success": result.get("success", False),
                "time": elapsed,
            })

            return result

        except Exception as e:
            log.error(f"Action failed: {e}")
            return {"success": False, "error": str(e), "time": time.time() - start_time}

    async def _run_command(self, command: str, timeout: int) -> dict:
        """Exécute une commande shell avec timeout."""
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )

            return {
                "success": proc.returncode == 0,
                "output": stdout.decode("utf-8", errors="replace")[:5000],
                "error": stderr.decode("utf-8", errors="replace")[:1000],
                "exit_code": proc.returncode,
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": "Timeout dépassé"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ============================================================
# Verification - Vérifie les résultats
# ============================================================
class Verifier:
    """
    Vérifie que les actions ont bien fonctionné.
    """

    async def verify(self, goal: Goal, results: list[dict]) -> dict:
        """Vérifie les résultats des actions."""
        all_success = all(r.get("success", False) for r in results)

        return {
            "verified": all_success,
            "actions_total": len(results),
            "actions_success": sum(1 for r in results if r.get("success")),
            "actions_failed": sum(1 for r in results if not r.get("success")),
            "total_time": sum(r.get("time", 0) for r in results),
        }


# ============================================================
# AI Rescue Core - Orchestrateur principal
# ============================================================
class AIRescueCore:
    """
    Orchestrateur principal : coordonne tous les composants.
    """

    def __init__(self):
        self.llm = LocalLLM()
        self.analyzer = GoalAnalyzer(self.llm)
        self.planner = Planner(self.llm)
        self.executor = Executor()
        self.verifier = Verifier()

    async def process(self, user_input: str) -> dict:
        """
        Point d'entrée principal.
        Transforme une demande en actions exécutées.
        """
        log.info(f"Processing: {user_input}")

        # Étape 1: Analyse
        goal = await self.analyzer.analyze(user_input)

        # Étape 2: Planification
        context = {}  # Sera enrichi par les détections
        actions = await self.planner.plan(goal, context)
        goal.actions = actions

        # Étape 3: Exécution
        results = []
        for action in actions:
            result = await self.executor.execute(action)
            results.append(result)

            # Arrêter si une action échoue et qu'elle est critique
            if not result.get("success") and action.risk in (RiskLevel.HIGH, RiskLevel.DESTRUCTIVE):
                log.warning(f"Stopping due to failed critical action: {action.description}")
                break

        # Étape 4: Vérification
        verification = await self.verifier.verify(goal, results)

        return {
            "goal": {
                "type": goal.goal_type.value,
                "description": goal.user_request,
            },
            "plan": [a.description for a in actions],
            "actions_results": results,
            "verification": verification,
            "summary": self._generate_summary(goal, results, verification),
        }

    def _generate_summary(self, goal, results, verification) -> str:
        """Génère un résumé lisible du résultat."""
        success_count = verification["actions_success"]
        total = verification["actions_total"]

        lines = [
            "=" * 50,
            f"  RAPPORT AI RESCUE",
            "=" * 50,
            "",
            f"Objectif : {goal.user_request}",
            f"Type : {goal.goal_type.value}",
            f"Temps total : {verification['total_time']:.1f}s",
            "",
            "Actions réalisées :",
        ]

        for r in results:
            status = "✓" if r.get("success") else "✗"
            lines.append(f"  {status} {r.get('action', 'Inconnue')}")

        lines.extend([
            "",
            f"Résultat : {success_count}/{total} actions réussies",
            "",
            "=" * 50,
        ])

        return "\n".join(lines)


# ============================================================
# CLI / Test
# ============================================================
async def main():
    """Point d'entrée CLI."""
    print("""
    ╔══════════════════════════════════════════╗
    ║          🤖 AI RESCUE CORE v1.0          ║
    ║   Le technicien informatique universel   ║
    ╚══════════════════════════════════════════╝
    """)

    core = AIRescueCore()

    # Charge le modèle si disponible
    core.llm.load_model()

    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
    else:
        print("Mode interactif. Tapez 'quit' pour quitter.\n")
        user_input = input("Que voulez-vous faire ? > ")

    if user_input.lower() in ("quit", "exit", "q"):
        return

    result = await core.process(user_input)
    print(result["summary"])


if __name__ == "__main__":
    asyncio.run(main())
