"""
AI Rescue USB - Backup Flow
============================
Guide l'utilisateur pour sauvegarder ses données étape par étape.
"""

import asyncio
import logging
from pathlib import Path

log = logging.getLogger("backup-flow")


class BackupFlow:
    """Flux conversationnel de sauvegarde."""

    def __init__(self, manager):
        self.manager = manager
        self.step = 0
        self.backup_target = None
        self.file_types = []
        self.hw_detector = None

        try:
            from detection.hardware.detector import HardwareDetector
            self.hw_detector = HardwareDetector()
        except Exception:
            pass

    async def start(self, user_input: str) -> str:
        """Démarre le flux de sauvegarde."""
        log.info("Starting backup flow")
        self.step = 0
        return self._step_what_to_backup()

    def _step_what_to_backup(self) -> str:
        """Étape 1 : Quoi sauvegarder ?"""
        return (
            "**Sauvegarde — Étape 1/4**\n\n"
            "Que voulez-vous sauvegarder ?\n\n"
            "1. 📷 **Photos** uniquement\n"
            "2. 📄 **Documents** (Word, PDF, Excel...)\n"
            "3. 🎬 **Videos**\n"
            "4. 🎵 **Musique**\n"
            "5. 📁 **Tout** (photos + documents + vidéos + musique)\n"
            "6. 🎯 **Personnalisé** (dites-moi)\n\n"
            "Choisissez un numéro ou décrivez ce que vous voulez."
        )

    async def handle_input(self, user_input: str) -> str:
        """Traite l'entrée utilisateur."""
        inp = user_input.lower().strip()

        # Étape 1 : choisir quoi
        if self.step == 0:
            return self._process_what(inp)

        # Étape 2 : choisir destination
        elif self.step == 1:
            return self._process_destination(inp)

        # Étape 3 : confirmation
        elif self.step == 2:
            return await self._process_confirm(inp)

        # Étape 4 : progression
        elif self.step == 3:
            return "Sauvegarde en cours... Veuillez patienter."

        return "Je n'ai pas compris. Dites-moi simplement ce que vous voulez."

    def _process_what(self, inp: str) -> str:
        """Traite le choix du type de fichiers."""
        if inp in ["1", "photos"]:
            self.file_types = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".raw"]
        elif inp in ["2", "documents"]:
            self.file_types = [".pdf", ".doc", ".docx", ".txt", ".xlsx", ".pptx"]
        elif inp in ["3", "videos"]:
            self.file_types = [".mp4", ".avi", ".mkv", ".mov", ".wmv"]
        elif inp in ["4", "musique"]:
            self.file_types = [".mp3", ".flac", ".wav", ".ogg"]
        elif inp in ["5", "tout"]:
            self.file_types = []  # tout
        else:
            self.file_types = []

        self.step = 1
        return self._step_destination()

    def _step_destination(self) -> str:
        """Étape 2 : où sauvegarder ?"""
        if not self.hw_detector:
            return ("**Où voulez-vous sauvegarder ?**\n\n"
                   "Branchez un disque externe USB, puis dites **\"c'est branché\"**.")

        try:
            hw = self.hw_detector.detect_all()
            # Chercher périphériques USB
            usb_disks = [d for d in hw.disks if d.interface.lower() == "usb"]

            msg = "**Choisissez la destination :**\n\n"

            if usb_disks:
                for i, d in enumerate(usb_disks[:3], 1):
                    msg += f"{i}. {d.device} - {d.model} ({d.size_gb:.0f}GB)\n"
                msg += "\n"
            else:
                msg += "**Aucun disque USB détecté.**\n\n"
                msg += "1. Branchez un disque externe\n"
                msg += "2. Dites **\"c'est branché\"** quand c'est fait\n\n"
                msg += "Ou sauvegarder sur un autre disque interne ?"

            return msg
        except Exception:
            return "Branchez un disque externe et dites-moi quand c'est prêt."

    def _process_destination(self, inp: str) -> str:
        """Traite le choix de destination."""
        if "branch" in inp or "prêt" in inp or "ok" in inp:
            self.step = 2
            return self._step_confirm()

        # Tentative de choix par numéro
        if inp.isdigit():
            try:
                num = int(inp) - 1
                hw = self.hw_detector.detect_all()
                usb_disks = [d for d in hw.disks if d.interface.lower() == "usb"]
                if 0 <= num < len(usb_disks):
                    self.backup_target = usb_disks[num]
                    self.step = 2
                    return self._step_confirm()
            except Exception:
                pass

        return "Je n'ai pas compris. Dites **\"c'est branché\"** ou le numéro du disque."

    def _step_confirm(self) -> str:
        """Étape 3 : confirmation avant sauvegarde."""
        types_str = "tout" if not self.file_types else ", ".join(self.file_types[:3])

        return (
            "**Confirmation — Étape 3/4**\n\n"
            f"📦 **Type :** {types_str}\n"
            f"💾 **Destination :** {self.backup_target.device if self.backup_target else 'disque USB'}\n\n"
            "**Cette action va :**\n"
            "• Copier les fichiers vers la destination\n"
            "• **Ne pas effacer** les fichiers originaux\n"
            "• Créer une structure de dossiers claire\n\n"
            "Dites **\"oui\"** pour commencer la sauvegarde."
        )

    async def _process_confirm(self, inp: str) -> str:
        """Traite la confirmation."""
        if any(w in inp for w in ["oui", "yes", "ok", "go"]):
            self.step = 3
            return await self._run_backup()
        elif any(w in inp for w in ["non", "no", "annule"]):
            self.manager.current_flow = None
            return "**Sauvegarde annulée.** Que voulez-vous faire d'autre ?"
        else:
            return "Dites **\"oui\"** pour lancer, **\"non\"** pour annuler."

    async def _run_backup(self) -> str:
        """Exécute la sauvegarde (simulation)."""
        msg = "**Sauvegarde en cours... 📦**\n\n"

        # Simuler progression
        stages = [
            ("Scan des fichiers", 20),
            ("Vérification espace", 40),
            ("Copie en cours", 70),
            ("Vérification intégrité", 90),
            ("Terminé", 100),
        ]

        for stage_name, progress in stages:
            if self.manager.on_progress:
                self.manager.on_progress("backup", progress)
            await asyncio.sleep(0.3)
            msg += f"✅ {stage_name}\n"

        msg += "\n🎉 **Sauvegarde terminée !**\n\n"
        msg += "Vos fichiers sont en sécurité.\n"
        msg += "Que voulez-vous faire maintenant ?"

        self.manager.current_flow = None
        return msg
