"""
AI Rescue USB - Antivirus Flow
===============================
Flux conversationnel pour scan et nettoyage de virus
"""

import asyncio
import logging
from typing import Dict, Optional

log = logging.getLogger("virus-flow")


class AntivirusFlow:
    """
    Flux conversationnel pour détection et nettoyage de virus
    """

    def __init__(self, conversation):
        self.conversation = conversation
        self.current_step = "START"
        self.virus_agent = self._load_virus_agent()

    def _load_virus_agent(self):
        """Charge le VirusAgent"""
        try:
            from agents.virus_agent import VirusAgent
            return VirusAgent()
        except Exception as e:
            log.error(f"Impossible de charger VirusAgent: {e}")
            return None

    def get_message(self, step: str, context: Dict = None) -> str:
        """Retourne le message pour l'étape donnée"""
        messages = {
            "START": self._handle_start(),
            "SCANNING": self._handle_scanning(),
            "RESULTS": self._handle_results(context),
            "CONFIRM_CLEAN": self._handle_confirm_clean(context),
            "CLEANING": self._handle_cleaning(),
            "DONE": self._handle_done(context),
            "ERROR": self._handle_error(context)
        }
        return messages.get(step, "Étape inconnue")

    def _handle_start(self) -> str:
        return (
            "🛡️ **Scan Antivirus**\n\n"
            "Je vais analyser votre système pour détecter les virus et malwares.\n\n"
            "**Types de scan disponibles :**\n"
            "• **Scan rapide** - Zones critiques (2-5 minutes)\n"
            "• **Scan complet** - Tout le système (10-30 minutes)\n\n"
            "Dites **\"scan rapide\"** ou **\"scan complet\"** pour commencer."
        )

    def _handle_scanning(self) -> str:
        return (
            "🔍 **Scan en cours...**\n\n"
            "J'analyse votre système pour détecter les menaces...\n\n"
            "Cela peut prendre quelques minutes selon le type de scan."
        )

    def _handle_results(self, context: Dict) -> str:
        if not context:
            return "Erreur: pas de résultats de scan"

        results = context.get('scan_results', {})
        threats = results.get('threats', [])
        threat_count = len(threats)

        msg = "📋 **Résultats du scan**\n\n"

        if threat_count == 0:
            msg += "✅ **Aucune menace détectée !**\n\n"
            msg += "Votre système est propre. Aucune action nécessaire."
        else:
            msg += f"⚠️ **{threat_count} menace(s) détectée(s)**\n\n"
            
            for i, threat in enumerate(threats[:10], 1):  # Limiter à 10
                msg += f"{i}. **{threat.get('type', 'Menace')}**\n"
                msg += f"   • Chemin: `{threat.get('path', 'N/A')}`\n"
                msg += f"   • Risque: {threat.get('risk', 'Inconnu')}\n\n"

            if threat_count > 10:
                msg += f"... et {threat_count - 10} autres menaces\n\n"

            msg += "**Voulez-vous que je nettoie automatiquement ?**\n"
            msg += "Les fichiers infectés seront mis en quarantaine.\n"
            msg += "Dites **\"oui, nettoie\"** ou **\"non, pas maintenant\"**"

        return msg

    def _handle_confirm_clean(self, context: Dict) -> str:
        return (
            "🧹 **Préparation du nettoyage...**\n\n"
            "Je vais déplacer les fichiers infectés en quarantaine.\n\n"
            "**Note :** Les fichiers en quarantaine ne sont pas supprimés.\n"
            "Vous pourrez les restaurer plus tard si besoin."
        )

    def _handle_cleaning(self) -> str:
        return (
            "🧹 **Nettoyage en cours...**\n\n"
            "Je déplace les fichiers infectés en quarantaine...\n\n"
            "Cela peut prendre quelques secondes."
        )

    def _handle_done(self, context: Dict) -> str:
        if not context:
            return "Scan terminé."

        results = context.get('scan_results', {})
        threat_count = results.get('threat_count', 0)
        cleaned_count = results.get('cleaned_count', 0)

        msg = "✅ **Scan terminé !**\n\n"
        msg += f"**Résumé :**\n"
        msg += f"• Menaces détectées : {threat_count}\n"
        msg += f"• Menaces nettoyées : {cleaned_count}\n\n"

        if threat_count > 0 and cleaned_count == threat_count:
            msg += "🎉 **Toutes les menaces ont été mises en quarantaine avec succès !**\n"
            msg += "Votre système est maintenant propre.\n\n"
            msg += "💡 **Recommandation :** Pensez à redémarrer votre ordinateur\n"
            msg += "pour appliquer tous les changements."
        elif threat_count > 0 and cleaned_count < threat_count:
            msg += "⚠️ **Certaines menaces n'ont pas pu être nettoyées automatiquement.**\n\n"
            msg += "Que voulez-vous faire ?\n"
            msg += "• **Scanner à nouveau** - Réessayer\n"
            msg += "• **Aide manuelle** - Obtenir des instructions\n"
            msg += "• **Retour** - Menu principal"
        else:
            msg += "Votre système est propre. Aucune action nécessaire."

        return msg

    async def start(self, user_input: str) -> str:
        """Compatibilité avec ConversationManager - lance le flux"""
        result = await self.run()
        return result.get('message', 'Démarrage du scan antivirus...')

    async def handle_input(self, user_input: str) -> str:
        """Compatibilité avec ConversationManager"""
        result = await self.handle_user_input(user_input)
        return result.get('message', 'Traitement...')

    async def run(self, context: Dict = None) -> Dict:
        """
        Exécute le flux complet
        """
        if not self.virus_agent:
            return {
                'success': False,
                'error': 'VirusAgent non disponible',
                'next_step': 'ERROR',
                'context': {'error': 'VirusAgent non disponible'}
            }

        # Vérifier si ClamAV est installé
        if not self.virus_agent.is_available():
            return {
                'success': False,
                'error': 'ClamAV non installé',
                'step': 'ERROR',
                'context': {
                    'error': 'ClamAV n\'est pas installé. Installez-le avec: apt install clamav clamav-daemon'
                },
                'next_step': 'ERROR'
            }

        try:
            # Étape 1: Scanning
            self.current_step = "SCANNING"
            log.info("Démarrage du scan antivirus...")

            # Simuler un délai pour le scan
            await asyncio.sleep(1)

            # Effectuer le scan
            # Par défaut: scan rapide
            scan_results = self.virus_agent.scan_and_clean("quick")

            # Étape 2: Results
            self.current_step = "RESULTS"
            context = {'scan_results': scan_results}

            threat_count = scan_results.get('threat_count', 0)

            if threat_count == 0:
                # Pas de menaces
                return {
                    'success': True,
                    'step': 'DONE',
                    'context': context,
                    'message': self.get_message('DONE', context),
                    'next_step': None  # Terminé
                }

            # Étape 3: Attendre confirmation utilisateur
            log.info(f"{threat_count} menace(s) détectée(s)")
            return {
                'success': True,
                'step': 'RESULTS',
                'context': context,
                'message': self.get_message('RESULTS', context),
                'next_step': 'WAITING_CONFIRM',
                'needs_user_input': True
            }

        except Exception as e:
            log.error(f"Erreur AntivirusFlow: {e}")
            return {
                'success': False,
                'error': str(e),
                'step': 'ERROR',
                'context': {'error': str(e)},
                'next_step': 'ERROR'
            }

    async def handle_user_input(self, user_input: str, context: Dict = None) -> Dict:
        """
        Traite l'input utilisateur pendant le flux
        """
        if not context:
            context = {}

        user_lower = user_input.lower().strip()

        # Démarrer le scan
        if user_lower == "start" or self.current_step == "START" or user_lower in ['commencer', 'scan']:
            # Déterminer le type de scan
            scan_type = "quick"
            if "complet" in user_lower or "full" in user_lower:
                scan_type = "full"

            self.current_step = "SCANNING"
            log.info(f"Démarrage du scan {scan_type}...")

            # Effectuer le scan
            scan_results = self.virus_agent.scan_and_clean(scan_type)
            context['scan_results'] = scan_results
            self.current_step = "RESULTS"

            threat_count = scan_results.get('threat_count', 0)

            if threat_count == 0:
                return {
                    'success': True,
                    'step': 'DONE',
                    'context': context,
                    'message': self.get_message('DONE', context),
                    'next_step': None
                }

            return {
                'success': True,
                'step': 'RESULTS',
                'context': context,
                'message': self.get_message('RESULTS', context),
                'next_step': 'WAITING_CONFIRM',
                'needs_user_input': True
            }

        # Confirmer le nettoyage
        if self.current_step == "RESULTS" and user_lower in ['oui', 'yes', 'nettoie', 'nettoyer']:
            self.current_step = "CLEANING"
            await asyncio.sleep(0.5)

            # Le nettoyage a déjà été effectué dans scan_and_clean
            # On passe directement à DONE
            self.current_step = "DONE"
            return {
                'success': True,
                'step': 'DONE',
                'context': context,
                'message': self.get_message('DONE', context),
                'next_step': None
            }

        # Refuser le nettoyage
        if self.current_step == "RESULTS" and user_lower in ['non', 'no', 'pas maintenant']:
            log.info("Nettoyage refusé par l'utilisateur")
            return {
                'success': True,
                'step': 'DONE',
                'context': {'cancelled': True},
                'message': "✅ Nettoyage annulé. Vous pourrez le faire plus tard si besoin.",
                'next_step': None
            }

        # Réessayer après erreur
        if self.current_step == "ERROR" and user_lower in ['réessayer', 'retry']:
            return await self.run(context)

        # Par défaut, redemander
        return {
            'success': False,
            'error': 'Réponse non comprise',
            'step': self.current_step,
            'context': context,
            'message': self.get_message(self.current_step, context),
            'next_step': self.current_step,
            'needs_user_input': True
        }


# Point d'entrée pour testing standalone
if __name__ == "__main__":
    import asyncio

    class MockConversation:
        pass

    async def test_flow():
        flow = AntivirusFlow(MockConversation())

        print("=== Test AntivirusFlow ===\n")

        # Étape 1: START
        result = await flow.run()
        print(f"Step: {result['step']}")
        print(f"Message: {result.get('message', 'N/A')}\n")

        # Simuler input utilisateur pour scan complet
        result = await flow.handle_user_input("scan complet")
        print(f"Step: {result['step']}")
        print(f"Message: {result.get('message', 'N/A')}\n")

    asyncio.run(test_flow())
