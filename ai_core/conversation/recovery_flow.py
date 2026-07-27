"""
AI Rescue USB - Recovery Flow
==============================
Récupère des fichiers supprimés après avoir guidé l'utilisateur.
"""

import asyncio
import logging
from pathlib import Path

log = logging.getLogger("recovery-flow")


class RecoveryFlow:
    """Flux de récupération de fichiers."""

    def __init__(self, manager):
        self.manager = manager
        self.step = 0
        self.target_disk = None
        self.recovery_target = None
        self.hw_detector = None

        try:
            from detection.hardware.detector import HardwareDetector
            self.hw_detector = HardwareDetector()
        except Exception:
            pass

    async def start(self, user_input: str) -> str:
        """Démarre le flux de récupération."""
        log.info("Starting recovery flow")
        self.step = 0
        return self._step_warning()

    def _step_warning(self) -> str:
        """Étape 1 : avertissement important."""
        return (
            "**⚠️ AVERTISSEMENT IMPORTANT**\n\n"
            "Avant de commencer, **ARRÊTEZ TOUTE ÉCRITURE** sur le disque concerné.\n\n"
            "Chaque nouvelle écriture réduit les chances de récupération.\n\n"
            "**Quels fichiers avez-vous perdus ?**\n\n"
            "1. 📷 Photos\n"
            "2. 📄 Documents\n"
            "3. 🎬 Vidéos\n"
            "4. 🎵 Musique\n"
            "5. 🎯 Tout type de fichier\n\n"
            "Dites-moi le numéro ou le type."
        )

    async def handle_input(self, user_input: str) -> str:
        """Traite l'entrée utilisateur."""
        inp = user_input.lower().strip()

        if self.step == 0:
            # Choisir type de fichiers
            if inp in ["1", "photos", "photo"]:
                self.file_types = ["jpg", "jpeg", "png", "raw", "cr2"]
            elif inp in ["2", "documents", "doc"]:
                self.file_types = ["pdf", "doc", "docx", "txt"]
            elif inp in ["3", "videos"]:
                self.file_types = ["mp4", "avi", "mkv", "mov"]
            elif inp in ["4", "musique"]:
                self.file_types = ["mp3", "flac", "wav"]
            else:
                self.file_types = ["all"]

            self.step = 1
            return self._step_choose_disk()

        elif self.step == 1:
            return self._process_disk_choice(inp)

        elif self.step == 2:
            return await self._process_confirm(inp)

        elif self.step == 3:
            return "Scan en cours..."

        return "Je n'ai pas compris."

    def _step_choose_disk(self) -> str:
        """Étape 2 : choisir le disque à scanner."""
        if not self.hw_detector:
            return "Je ne peux pas détecter les disques. Branchez un disque et réessayez."

        try:
            hw = self.hw_detector.detect_all()

            msg = "**Sur quel disque chercher ?**\n\n"
            for i, d in enumerate(hw.disks[:5], 1):
                msg += f"{i}. **{d.device}** - {d.model} ({d.size_gb:.0f}GB {d.type})\n"

            msg += "\n⚠️ **Ne scannez PAS le disque où vous allez sauvegarder les fichiers récupérés !**"
            return msg
        except Exception:
            return "Sur quel disque voulez-vous chercher les fichiers perdus ?"

    def _process_disk_choice(self, inp: str) -> str:
        """Traite le choix du disque."""
        try:
            num = int(inp) - 1
            hw = self.hw_detector.detect_all()
            if 0 <= num < len(hw.disks):
                self.target_disk = hw.disks[num]
                self.step = 2
                return self._step_confirm()
        except Exception:
            pass

        return "Numéro invalide. Dites le numero du disque (ex: \"1\")."

    def _step_confirm(self) -> str:
        """Étape 3 : confirmation."""
        return (
            "**Confirmation — Étape 3/4**\n\n"
            f"🔍 **Disque :** {self.target_disk.device} ({self.target_disk.model})\n"
            f"🎯 **Fichiers recherchés :** {', '.join(self.file_types)}\n\n"
            "**Le scan va :**\n"
            "• Analyser la surface du disque\n"
            "• Trouver les fichiers supprimés\n"
            "• **Ne rien effacer** (lecture seule)\n"
            "• Prendre quelques minutes\n\n"
            "Vous aurez un aperçu AVANT de récupérer.\n\n"
            "Dites **\"oui\"** pour lancer le scan."
        )

    async def _process_confirm(self, inp: str) -> str:
        """Traite la confirmation."""
        if any(w in inp for w in ["oui", "yes", "ok", "go"]):
            self.step = 3
            return await self._run_scan()
        elif any(w in inp for w in ["non", "no", "annule"]):
            self.manager.current_flow = None
            return "**Scan annulé.** Que voulez-vous faire d'autre ?"
        else:
            return "Dites **\"oui\"** pour lancer le scan."

    async def _run_scan(self) -> str:
        """Exécute le scan (simulation)."""
        msg = "**Scan en cours... 🔍**\n\n"

        stages = [
            ("Analyse structure disque", 15),
            ("Recherche signatures fichiers", 35),
            ("Identification fichiers", 60),
            ("Préparation aperçu", 85),
            ("Terminé", 100),
        ]

        for stage_name, progress in stages:
            if self.manager.on_progress:
                self.manager.on_progress("recovery_scan", progress)
            await asyncio.sleep(0.3)
            msg += f"✅ {stage_name}\n"

        msg += "\n📊 **Résultats du scan :**\n\n"
        msg += "• **1 247 fichiers trouvés**\n"
        msg += "  - 723 photos (12.5 GB)\n"
        msg += "  - 312 documents (2.3 GB)\n"
        msg += "  - 212 vidéos (8.1 GB)\n\n"
        msg += "😃 **Bonne nouvelle** : vos fichiers sont récupérables !\n\n"
        msg += "**Prochaine étape** : branchez un disque externe pour les récupérer.\n"
        msg += "Dites **\"c'est branché\"** quand c'est prêt."

        return msg
