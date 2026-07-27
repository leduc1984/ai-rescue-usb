"""
AI Rescue USB - Conversation Manager
=====================================
Gère les conversations avec l'utilisateur.
Flux guidés (install, repair, backup, recover, diagnose) + Assistant universel pour TOUT le reste.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable

# Assistant universel (répond à TOUTE question)
from ai_core.conversation.universal_assistant import UniversalAssistant
from ai_core.conversation.install_flow import InstallFlow
from ai_core.conversation.repair_flow import RepairFlow
from ai_core.conversation.backup_flow import BackupFlow
from ai_core.conversation.recovery_flow import RecoveryFlow
from ai_core.conversation.diagnose_flow import DiagnoseFlow
from ai_core.conversation.antivirus_flow import AntivirusFlow
from ai_core.conversation.network_flow import NetworkFlow
from ai_core.conversation.driver_flow import DriverInstallFlow

log = logging.getLogger("conversation")


class ConversationState(Enum):
    """État de la conversation."""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    WAITING_CONFIRMATION = "waiting_confirmation"
    EXECUTING = "executing"
    ERROR = "error"


class IntentType(Enum):
    """Type d'intention détectée."""
    INSTALL_OS = "install_os"
    REPAIR_SYSTEM = "repair_system"
    BACKUP_DATA = "backup_data"
    RECOVER_FILES = "recover_files"
    DIAGNOSE = "diagnose"
    SCAN_VIRUS = "scan_virus"
    NETWORK = "network"
    INSTALL_DRIVERS = "install_drivers"
    CONFIRM = "confirm"
    DENY = "deny"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class ConversationContext:
    """Contexte de la conversation."""
    current_flow: str = ""
    flow_step: int = 0
    collected_data: dict = field(default_factory=dict)
    history: list = field(default_factory=list)


class ConversationManager:
    """
    Gestionnaire principal de conversation.
    Orchestre les flux guidés + fallback universel.
    """

    def __init__(self, llm=None, voice=None):
        self.llm = llm if llm is not None else self._load_default_llm()
        self.voice = voice

        # Assistant universel (répond à TOUTE question)
        self.universal = UniversalAssistant(llm=self.llm)

        # État
        self.state = ConversationState.IDLE
        self.context = ConversationContext()
        self.current_flow = None

        # Callbacks
        self.on_state_change: Optional[Callable] = None
        self.on_ai_response: Optional[Callable] = None
        self.on_progress: Optional[Callable] = None
        self.on_confirmation_needed: Optional[Callable] = None

        # Flux disponibles
        self.flows = {
            "install": InstallFlow,
            "repair": RepairFlow,
            "backup": BackupFlow,
            "recovery": RecoveryFlow,
            "diagnose": DiagnoseFlow,
            "antivirus": AntivirusFlow,
            "network": NetworkFlow,
            "driver": DriverInstallFlow,
        }

    @staticmethod
    def _load_default_llm():
        """Charge le LLM local si llama-cpp-python + un modèle .gguf sont disponibles.

        Dégrade silencieusement (retourne None) si l'un des deux manque — le reste
        du système continue de fonctionner en mode rule-based (voir universal_assistant).
        """
        try:
            from ai_core.engine import LocalLLM
            llm = LocalLLM()
            llm.load_model()
            if llm.loaded:
                log.info("LLM local chargé pour la conversation.")
                return llm
            log.info("Aucun LLM local chargé (paquet ou modèle absent) — mode rule-based.")
        except Exception as e:
            log.warning(f"Chargement du LLM local échoué, mode rule-based: {e}")
        return None

    def register_flow(self, name: str, flow_class):
        """Enregistre un flux de conversation."""
        self.flows[name] = flow_class

    def switch_flow(self, flow_name: str, context: Optional[dict] = None) -> bool:
        """Bascule vers un flux."""
        if flow_name in self.flows:
            flow_class = self.flows[flow_name]
            self.current_flow = flow_class(self)
            self.context.current_flow = flow_name
            self.context.flow_step = 0
            if context:
                self.context.collected_data.update(context)
            return True
        return False

    async def end_current_flow(self):
        """Termine le flux actif et revient au mode conversation libre."""
        if self.current_flow:
            if hasattr(self.current_flow, 'on_end'):
                await self.current_flow.on_end()
            self.current_flow = None
            self.context.current_flow = ""
            self.context.flow_step = 0
            self.state = ConversationState.IDLE

    def set_state(self, new_state: ConversationState):
        """Change l'état de la conversation."""
        old_state = self.state
        self.state = new_state
        log.info(f"State: {old_state.value} → {new_state.value}")

        if self.on_state_change:
            self.on_state_change(old_state, new_state)

    async def process_user_input(self, user_input: str, is_voice: bool = False) -> str:
        """
        Traite l'entrée utilisateur (texte ou voix).
        Retourne la réponse de l'IA.
        Logique :
        - Si un flux est actif → continuer le flux
        - Sinon → détecter intention
          - Si intention connue → démarrer le flux correspondant
          - Sinon → assistant universel (répond à TOUT)
        """
        log.info(f"User input: {user_input[:100]}...")

        # Enregistrer dans l'historique
        self.context.history.append({
            "role": "user",
            "content": user_input,
            "timestamp": asyncio.get_event_loop().time()
        })

        # Si un flux est actif, continuer avec lui
        if self.current_flow:
            response = await self.current_flow.handle_input(user_input)
            # Vérifier si le flux est terminé
            if hasattr(self.current_flow, 'is_finished') and self.current_flow.is_finished():
                await self.end_current_flow()
        else:
            # Détecter l'intention
            intent = self._detect_intent(user_input)
            log.info(f"Detected intent: {intent.value}")

            # Démarrer un flux si l'intention correspond
            flow_map = {
                IntentType.INSTALL_OS: "install",
                IntentType.REPAIR_SYSTEM: "repair",
                IntentType.BACKUP_DATA: "backup",
                IntentType.RECOVER_FILES: "recovery",
                IntentType.DIAGNOSE: "diagnose",
                IntentType.SCAN_VIRUS: "antivirus",
                IntentType.NETWORK: "network",
                IntentType.INSTALL_DRIVERS: "driver",
            }

            if intent in flow_map:
                flow_name = flow_map[intent]
                if flow_name in self.flows:
                    flow_started = self.switch_flow(flow_name)
                    if flow_started:
                        response = await self.current_flow.start(user_input)
                    else:
                        response = self.universal.answer(user_input)
                else:
                    # Flux non disponible, utiliser l'assistant universel
                    response = self.universal.answer(user_input)
            else:
                # Pas d'intention de flux → assistant universel
                response = self.universal.answer(user_input)

        # Callback
        if self.on_ai_response:
            self.on_ai_response(response)

        # Si voix activée, parler la réponse
        if is_voice and self.voice:
            await self.voice.speak(response)

        # Enregistrer la réponse
        self.context.history.append({
            "role": "assistant",
            "content": response,
            "timestamp": asyncio.get_event_loop().time()
        })

        return response

    def _detect_intent(self, user_input: str) -> IntentType:
        """Détecte l'intention de l'utilisateur.
        
        Ordre important : intentions métier AVANT intentions conversationnelles
        pour éviter que 'no' dans 'diagnostic' ne matche DENY.
        """
        inp = user_input.lower()

        # === INTENTIONS MÉTIER (priorité haute) ===

        # Installation
        if any(w in inp for w in ["installe", "install", "windows", "linux", "ubuntu"]):
            return IntentType.INSTALL_OS

        # Réparation
        elif any(w in inp for w in ["répare", "repair", "fix", "casse", "marche plus", "démarre plus", "démarre pas", "ne démarre", "boot", "démarrage"]):
            return IntentType.REPAIR_SYSTEM

        # Sauvegarde
        elif any(w in inp for w in ["sauvegarde", "backup", "copie", "sauver"]):
            return IntentType.BACKUP_DATA

        # Récupération
        elif any(w in inp for w in ["récupère", "recover", "perdu", "effacé"]):
            return IntentType.RECOVER_FILES

        # Diagnostic (avant CONFIRM/DENY car 'diagnostic' contient 'no')
        elif any(w in inp for w in ["diagnostique", "diagnostic", "vérifie", "vérifier", "analyse", "problème", "pourquoi"]):
            return IntentType.DIAGNOSE

        # Aide
        elif any(w in inp for w in ["aide", "help", "comment", "quoi faire"]):
            return IntentType.HELP

        # === INTENTIONS CONVERSATIONNELLES (après les intentions métier) ===
        # Exiger match exact pour éviter les faux positifs

        # Confirmations (exiger match plus strict)
        elif inp.strip() in ["oui", "yes", "ok", "d'accord", "confirme", "go", "yep", "ouais"]:
            return IntentType.CONFIRM
        elif inp.strip() in ["non", "no", "annule", "cancel", "stop"]:
            return IntentType.DENY

        else:
            return IntentType.UNKNOWN

    async def request_confirmation(self, message: str, data: dict = None) -> bool:
        """
        Demande une confirmation à l'utilisateur.
        Retourne True si confirmé, False sinon.
        """
        self.set_state(ConversationState.WAITING_CONFIRMATION)

        if self.on_confirmation_needed:
            self.on_confirmation_needed(message, data)

        # TODO: Attendre la réponse utilisateur
        # Pour l'instant, on retourne via handle_input

        return True  # Placeholder

    def ask_question(self, question: str, options: list = None) -> str:
        """
        Pose une question à l'utilisateur.
        Peut afficher des options si fournies.
        """
        if options:
            options_text = "\n".join([f"  {i+1}. {opt}" for i, opt in enumerate(options)])
            return f"{question}\n\n{options_text}"
        return question


class ConversationFlow:
    """Base pour tous les flux de conversation guidés."""

    def __init__(self, manager: ConversationManager):
        self.manager = manager
        self.step = 0
        self.data = {}

    async def start(self, user_input: str) -> str:
        """Démarre le flux."""
        raise NotImplementedError

    async def handle_input(self, user_input: str) -> str:
        """Traite l'entrée utilisateur pendant le flux."""
        raise NotImplementedError

    def is_finished(self) -> bool:
        """Vérifie si le flux est terminé."""
        return False  # À surcharger dans les flux spécifiques

    async def on_end(self):
        """Appelé quand le flux se termine."""
        pass  # À surcharger si nécessaire

    def next_step(self) -> str:
        """Passe à l'étape suivante."""
        self.step += 1
        self.manager.context.flow_step = self.step
        return f"step_{self.step}"

    def get_step_name(self) -> str:
        """Retourne le nom de l'étape actuelle."""
        return f"step_{self.step}"
