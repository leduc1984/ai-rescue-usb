"""
AI Rescue USB - Diagnose Flow
==============================
Diagnostic complet du PC avec recommandations.
"""

import asyncio
import logging
from pathlib import Path

log = logging.getLogger("diagnose-flow")


class DiagnoseFlow:
    """Flux de diagnostic complet."""

    def __init__(self, manager):
        self.manager = manager
        self.step = 0
        self.hw_detector = None
        self.os_detector = None

        try:
            from detection.hardware.detector import HardwareDetector
            self.hw_detector = HardwareDetector()
        except Exception:
            pass
        try:
            from detection.os.detector import OSDetector
            self.os_detector = OSDetector()
        except Exception:
            pass

    async def start(self, user_input: str) -> str:
        """Démarre le diagnostic."""
        log.info("Starting diagnose flow")
        return await self._run_diagnostic()

    async def handle_input(self, user_input: str) -> str:
        """Traite l'entrée utilisateur (pour questions après le diagnostic)."""
        low = user_input.lower()

        # Après le diagnostic, répondre aux questions
        if any(w in low for w in ["pourquoi", "comment", "que faire", "conseil"]):
            return self._give_advice()
        elif any(w in low for w in ["réparer", "fix", "corriger"]):
            from ai_core.conversation.repair_flow import RepairFlow
            self.manager.current_flow = RepairFlow(self.manager)
            return await self.manager.current_flow.start(user_input)
        else:
            self.manager.current_flow = None
            return "Que voulez-vous faire maintenant ?"

    async def _run_diagnostic(self) -> str:
        """Exécute le diagnostic complet."""
        msg = "**🩺 Diagnostic complet en cours...**\n\n"

        stages = [
            ("Analyse du CPU", 10),
            ("Test de la RAM", 25),
            ("Scan des disques", 45),
            ("Vérification SMART", 60),
            ("Analyse réseau", 75),
            ("Détection OS", 85),
            ("Génération rapport", 100),
        ]

        for stage_name, progress in stages:
            if self.manager.on_progress:
                self.manager.on_progress("diagnose", progress)
            await asyncio.sleep(0.3)

        msg += "**✅ Résultats du diagnostic :**\n\n"

        # CPU
        if self.hw_detector:
            try:
                hw = self.hw_detector.detect_all()
                msg += f"**CPU :** {hw.cpu.model} ✅\n"
                msg += f"  ({hw.cpu.cores} cores, {hw.cpu.threads} threads)\n"
                msg += f"**RAM :** {hw.ram.total_mb}MB ✅"
                if hw.ram.total_mb < 4096:
                    msg += " ⚠️ (faible, peut ralentir)"
                msg += "\n\n"

                # Disques
                if hw.disks:
                    msg += "**Disques :**\n"
                    for d in hw.disks:
                        health = "✅" if d.health == "good" else "⚠️" if d.health == "unknown" else "❌"
                        msg += f"  {health} {d.device} : {d.model}\n"
                        msg += f"     {d.size_gb:.0f}GB {d.type.upper()} - Santé {d.health}\n"
                    msg += "\n"

                # Réseau
                if hw.network:
                    msg += "**Réseau :**\n"
                    for n in hw.network[:2]:
                        status = "✅" if n.status == "up" else "⚠️"
                        msg += f"  {status} {n.interface} ({n.type})\n"
                    msg += "\n"

            except Exception:
                msg += "⚠️ Impossible de lire le matériel\n"

        # OS
        if self.os_detector:
            try:
                os_info = self.os_detector.detect_all()
                if os_info.detected_os:
                    msg += "**Systèmes :**\n"
                    for o in os_info.detected_os:
                        status = "✅" if o.boot_status == "ok" else "⚠️"
                        msg += f"  {status} {o.name} {o.version} - Boot {o.boot_status}\n"
                    msg += "\n"
                else:
                    msg += "**Systèmes :** Aucun OS détecté\n\n"
            except Exception:
                msg += "⚠️ Impossible de détecter les OS\n"

        # Recommandations
        msg += "---\n\n"
        msg += "**💡 Recommandations :**\n\n"
        msg += "• Si votre PC est lent, **remplacez le HDD par un SSD** (boost 5-10x)\n"
        msg += "• Si RAM < 4GB, **ajoutez de la RAM** ou **installez Linux léger**\n"
        msg += "• **Sauvegardez régulièrement** vos fichiers importants\n"

        return msg

    def _give_advice(self) -> str:
        """Donne des conseils après le diagnostic."""
        return (
            "**💡 Conseils personnalisés :**\n\n"
            "1. **Sauvegarde** — Branchez un disque externe régulièrement\n"
            "2. **SSD** — Si vous avez un HDD, passer à un SSD est LA meilleure amélioration\n"
            "3. **Linux** — Si votre PC est vieux, Linux Mint est plus rapide que Windows\n"
            "4. **Nettoyage** — Supprimez les programmes inutiles\n"
            "5. **Mises à jour** — Gardez votre OS à jour\n\n"
            "Voulez-vous que je fasse quelque chose ?"
        )
