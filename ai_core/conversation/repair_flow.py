"""
AI Rescue USB - Repair Flow
============================
Flux de conversation pour la réparation.
Guide l'utilisateur pas à pas.

Exemple :
User: "Mon PC ne démarre plus"
AI: "Je vais diagnostiquer le problème. Pouvez-vous me dire ce qui se passe exactement ?"
User: "Écran noir au démarrage"
AI: "D'accord. Je détecte Windows 10 sur votre disque. Je vais réparer le démarrage. Voulez-vous continuer ?"
User: "Oui"
AI: "Réparation en cours... ✅ Boot repair terminé ✅ BCD reconstruit ✅ EFI réparé. Votre PC devrait redémarrer maintenant !"
"""

import asyncio
import logging
from typing import Optional

log = logging.getLogger("repair-flow")


class RepairFlow:
    """
    Flux de réparation guidé.
    Étapes :
    1. Comprendre le problème
    2. Diagnostiquer
    3. Proposer solutions
    4. Confirmer
    5. Exécuter
    6. Vérifier
    7. Rapport
    """
    
    def __init__(self, manager):
        self.manager = manager
        self.step = 0
        self.symptoms = []
        self.detected_os = None
        self.repair_actions = []
        
        # Injecter les dépendances
        self.repair_agent = None
        self.os_detector = None
        self.hw_detector = None
        
        self._load_agents()
    
    def _load_agents(self):
        """Charge les agents nécessaires."""
        try:
            from agents.repair.repair_agent import RepairAgent
            self.repair_agent = RepairAgent()
        except Exception as e:
            log.warning(f"RepairAgent non disponible: {e}")
        
        try:
            from detection.os.detector import OSDetector
            self.os_detector = OSDetector()
        except Exception as e:
            log.warning(f"OSDetector non disponible: {e}")
        
        try:
            from detection.hardware.detector import HardwareDetector
            self.hw_detector = HardwareDetector()
        except Exception as e:
            log.warning(f"HardwareDetector non disponible: {e}")
    
    async def start(self, user_input: str) -> str:
        """Démarre le flux de réparation."""
        log.info("Starting repair flow")
        
        # Étape 0 : Comprendre le problème
        self.step = 0
        return self._step_describe_problem()
    
    def _step_describe_problem(self) -> str:
        """Étape 1 : Demander une description du problème."""
        message = "Je vais vous aider à réparer votre ordinateur.\n\n"
        message += "Pouvez-vous me décrire le problème ? Par exemple :\n"
        message += "  • \"Mon PC ne démarre plus\"\n"
        message += "  • \"Écran bleu au démarrage\"\n"
        message += "  • \"Windows ne se lance pas\"\n"
        message += "  • \"Disque introuvable\"\n\n"
        message += "Décrivez-moi ce qui se passe."
        
        return message
    
    async def handle_input(self, user_input: str) -> str:
        """Traite l'entrée utilisateur selon l'étape."""
        inp = user_input.lower()
        
        # Étape 0 : Description du problème
        if self.step == 0:
            return await self._process_problem_description(inp)
        
        # Étape 1 : Confirmation diagnostic
        elif self.step == 1:
            return await self._process_diagnostic_confirm(inp)
        
        # Étape 2 : Confirmation réparation
        elif self.step == 2:
            return await self._process_repair_confirm(inp)
        
        # Étape 3 : Exécution
        elif self.step == 3:
            return "Réparation en cours, veuillez patienter..."
        
        return "Je n'ai pas compris. Pouvez-vous reformuler ?"
    
    async def _process_problem_description(self, user_input: str) -> str:
        """Traite la description du problème."""
        # Extraire les symptômes
        self.symptoms = [user_input]
        
        message = "D'accord, je comprends. "
        
        # Détecter les OS présents
        if self.os_detector:
            os_info = self.os_detector.detect_all()
            
            if os_info.detected_os:
                self.detected_os = os_info.detected_os[0]
                message += f"Je détecte **{self.detected_os.name} {self.detected_os.version}** sur **{self.detected_os.partition}**.\n\n"
                
                # Vérifier le statut du boot
                if self.detected_os.boot_status == "broken":
                    message += "⚠️ Le démarrage semble endommagé.\n\n"
                else:
                    message += "Le démarrage semble intact, mais je vais vérifier plus en détail.\n\n"
            else:
                message += "Aucun système d'exploitation détecté sur les disques.\n\n"
        
        message += "Je vais maintenant analyser le problème et proposer des solutions.\n\n"
        message += "Voulez-vous que je continue le diagnostic ?"
        
        # Étape suivante
        self.step = 1
        return message
    
    async def _process_diagnostic_confirm(self, user_input: str) -> str:
        """Traite la confirmation du diagnostic."""
        if any(w in user_input.lower() for w in ["oui", "yes", "continue"]):
            # Exécuter le diagnostic
            return await self._run_diagnostic()
        
        elif any(w in user_input.lower() for w in ["non", "no", "annule"]):
            return "Diagnostic annulé. Que voulez-vous faire d'autre ?"
        
        else:
            return "Répondez \"oui\" pour continuer le diagnostic."
    
    async def _run_diagnostic(self) -> str:
        """Exécute le diagnostic complet."""
        message = "## 🔍 Diagnostic en cours...\n\n"
        
        if not self.repair_agent:
            return "Erreur : agent de réparation indisponible."
        
        # Simuler progression
        for i in range(0, 101, 20):
            await asyncio.sleep(0.1)
            if self.manager.on_progress:
                self.manager.on_progress("diagnose", i)
        
        # Obtenir le type d'OS
        os_type = self.detected_os.type if self.detected_os else "windows"
        
        # Diagnostiquer
        self.repair_actions = self.repair_agent.diagnose(os_type, self.symptoms)
        
        if not self.repair_actions:
            message += "Aucune réparation automatique disponible pour ce problème.\n\n"
            message += "Suggestions :\n"
            message += "  • Essayez de redémarrer en mode sans échec\n"
            message += "  • Vérifiez les câbles et connexions\n"
            message += "  • Consultez un technicien\n"
            return message
        
        message += "**Problème identifié :**\n"
        
        if "boot" in " ".join(self.symptoms).lower() or "démarre" in " ".join(self.symptoms).lower():
            message += "  • Démarrage endommagé\n\n"
        else:
            message += "  • Problème système détecté\n\n"
        
        message += "**Réparations proposées :**\n\n"
        
        for i, action in enumerate(self.repair_actions, 1):
            risk_icon = "🟢" if action.risk.value == "safe" else "🟡" if action.risk.value == "low" else "🟠"
            message += f"{i}. {risk_icon} **{action.description}**\n"
            if action.risk.value in ["medium", "high"]:
                message += f"   (Nécessite redémarrage)\n"
            message += "\n"
        
        message += "**Voulez-vous que j'exécute ces réparations ?**"
        
        # Étape suivante
        self.step = 2
        return message
    
    async def _process_repair_confirm(self, user_input: str) -> str:
        """Traite la confirmation de la réparation."""
        if any(w in user_input.lower() for w in ["oui", "yes", "go"]):
            # Exécuter les réparations
            return await self._execute_repairs()
        
        elif any(w in user_input.lower() for w in ["non", "no", "annule"]):
            return "Réparation annulée. Que voulez-vous faire ?"
        
        else:
            return "Répondez \"oui\" pour exécuter les réparations."
    
    async def _execute_repairs(self) -> str:
        """Exécute les réparations."""
        message = "## 🔧 Réparation en cours...\n\n"
        
        if not self.repair_actions:
            return "Erreur : aucune réparation à exécuter."
        
        results = []
        
        for i, action in enumerate(self.repair_actions, 1):
            # Progression
            if self.manager.on_progress:
                self.manager.on_progress("repair", (i / len(self.repair_actions)) * 100)
            
            # L'utilisateur a déjà vu la liste des actions (avec niveau de risque)
            # et a explicitement confirmé à l'étape précédente : on exécute pour de vrai.
            result = self.repair_agent.execute_repair(action, dry_run=False)
            results.append(result)
        
        # Rapport
        message += "**Résultats des réparations :**\n\n"
        
        success_count = sum(1 for r in results if r.success)
        
        for i, result in enumerate(results, 1):
            icon = "✅" if result.success else "❌"
            message += f"{icon} {result.action}\n"
            if result.error and not result.success:
                message += f"   Erreur : {result.error[:50]}\n"
            message += "\n"
        
        message += f"\n**{success_count}/{len(results)} réparations réussies**\n\n"
        
        if success_count == len(results):
            message += "🎉 **Toutes les réparations ont réussi !**\n\n"
            message += "Votre ordinateur devrait fonctionner normalement maintenant.\n"
            message += "Redémarrez pour appliquer les changements.\n\n"
        else:
            message += "Certaines réparations n'ont pas fonctionné.\n"
            message += "Vous pouvez essayer de redémarrer, ou tenter d'autres réparations.\n\n"
        
        message += "Voulez-vous faire autre chose ?"
        
        # Reset le flux
        self.manager.current_flow = None
        self.manager.context.current_flow = ""
        
        return message
