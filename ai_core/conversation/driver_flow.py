"""
AI Rescue USB - Driver Install Flow
===================================
Flux conversationnel pour installation automatique des drivers
"""

import asyncio
import logging
from typing import Dict, Optional

log = logging.getLogger("driver-flow")


class DriverInstallFlow:
    """
    Flux conversationnel pour détection et installation des drivers
    """

    def __init__(self, conversation):
        self.conversation = conversation
        self.current_step = "START"
        self.driver_installer = self._load_driver_installer()

    def _load_driver_installer(self):
        """Charge le DriverInstaller"""
        try:
            from agents.driver_installer import DriverInstaller
            return DriverInstaller()
        except Exception as e:
            log.error(f"Impossible de charger DriverInstaller: {e}")
            return None

    def get_message(self, step: str, context: Dict = None) -> str:
        """Retourne le message pour l'étape donnée"""
        messages = {
            "START": self._handle_start(),
            "SCANNING": self._handle_scanning(),
            "RESULTS": self._handle_results(context),
            "CONFIRM_INSTALL": self._handle_confirm_install(context),
            "INSTALLING": self._handle_installing(),
            "DONE": self._handle_done(context),
            "ERROR": self._handle_error(context)
        }
        return messages.get(step, "Étape inconnue")

    def _handle_start(self) -> str:
        return (
            "🔧 **Installation des drivers**\n\n"
            "Je vais détecter votre matériel et installer les drivers manquants.\n\n"
            "**Ce que je vais faire :**\n"
            "1. Scanner tout le matériel (PCI, USB)\n"
            "2. Identifier les drivers manquants\n"
            "3. Installer automatiquement les drivers\n"
            "4. Configurer le matériel\n\n"
            "Dites **\"commencer\"** pour lancer le scan."
        )

    def _handle_scanning(self) -> str:
        return (
            "🔍 **Scan du matériel en cours...**\n\n"
            "Je détecte tous vos périphériques...\n\n"
            "Cela peut prendre quelques secondes."
        )

    def _handle_results(self, context: Dict) -> str:
        if not context:
            return "Erreur: pas de résultats de scan"

        devices = context.get('devices', {})
        missing = devices.get('missing_drivers', [])
        summary = devices.get('summary', {})

        msg = "📋 **Résultats du scan**\n\n"
        msg += f"**Matériel détecté :**\n"
        msg += f"• Périphériques PCI : {summary.get('total_pci', 0)}\n"
        msg += f"• Périphériques USB : {summary.get('total_usb', 0)}\n"
        msg += f"• Drivers manquants : {summary.get('missing_count', 0)}\n\n"

        if not missing:
            msg += "✅ **Excellent !** Tous vos drivers sont installés.\n"
            msg += "Votre matériel est entièrement fonctionnel."
        else:
            msg += "⚠️ **Drivers manquants détectés :**\n\n"
            for i, device in enumerate(missing[:10], 1):  # Limiter à 10
                msg += f"{i}. {device.get('description', 'Périphérique inconnu')}\n"
                if device.get('suggested_driver'):
                    msg += f"   → Driver suggéré: `{device['suggested_driver']}`\n"

            if len(missing) > 10:
                msg += f"\n... et {len(missing) - 10} autres\n"

            msg += "\n\n"
            msg += "**Voulez-vous installer maintenant ?**\n"
            msg += "Dites **\"oui, installe\"** ou **\"non, pas maintenant\"**"

        return msg

    def _handle_confirm_install(self, context: Dict) -> str:
        return (
            "⚙️ **Préparation de l'installation...**\n\n"
            "Je vais installer les drivers manquants.\n\n"
            "**Note :** L'installation peut nécessiter une connexion Internet.\n"
            "Certains drivers peuvent nécessiter un redémarrage."
        )

    def _handle_installing(self) -> str:
        return (
            "📦 **Installation en cours...**\n\n"
            "J'installe les drivers manquants...\n\n"
            "Cela peut prendre quelques minutes selon le nombre de drivers."
        )

    def _handle_done(self, context: Dict) -> str:
        if not context:
            return "Installation terminée."

        results = context.get('results', {})
        summary = results.get('summary', {})

        msg = "✅ **Installation terminée !**\n\n"
        msg += f"**Résumé :**\n"
        msg += f"• Drivers installés : {summary.get('installed', 0)}\n"
        msg += f"• Échecs : {summary.get('failed', 0)}\n"
        msg += f"• Ignorés : {summary.get('skipped', 0)}\n\n"

        if summary.get('failed', 0) > 0:
            msg += "⚠️ **Certains drivers n'ont pas pu être installés.**\n"
            msg += "Vous pouvez : \n"
            msg += "• Réessayer plus tard\n"
            msg += "• Vérifier votre connexion Internet\n"
            msg += "• Installer manuellement les drivers\n\n"

        # Vérifier si reboot nécessaire
        msg += "\n💡 **Note :** Pour certains drivers (GPU, réseau), "
        msg += "un **redémarrage** peut être nécessaire.\n"

        return msg

    def _handle_error(self, context: Dict) -> str:
        error = context.get('error', 'Erreur inconnue')
        return (
            f"❌ **Erreur**\n\n"
            f"Une erreur est survenue : {error}\n\n"
            "Que voulez-vous faire ?\n"
            "• **Réessayer** - Tenter à nouveau\n"
            "• **Aide** - Obtenir de l'aide\n"
            "• **Retour** - Retour au menu principal"
        )

    async def run(self, context: Dict = None) -> Dict:
        """
        Exécute le flux complet
        """
        if not self.driver_installer:
            return {
                'success': False,
                'error': 'DriverInstaller non disponible',
                'next_step': 'ERROR',
                'context': {'error': 'DriverInstaller non disponible'}
            }

        try:
            # Step 1: Scanning
            self.current_step = "SCANNING"
            log.info("Scan du matériel...")

            # Simuler un délai pour le scan
            await asyncio.sleep(1)

            # Effectuer le scan réel
            devices = self.driver_installer.detect_all()

            # Step 2: Results
            self.current_step = "RESULTS"
            context = {'devices': devices}

            missing_count = devices.get('summary', {}).get('missing_count', 0)

            if missing_count == 0:
                # Pas de drivers manquants
                return {
                    'success': True,
                    'step': 'RESULTS',
                    'context': context,
                    'message': self.get_message('RESULTS', context),
                    'next_step': None  # Terminé
                }

            # Step 3: Attendre confirmation utilisateur
            log.info(f"{missing_count} drivers manquants détectés")
            return {
                'success': True,
                'step': 'RESULTS',
                'context': context,
                'message': self.get_message('RESULTS', context),
                'next_step': 'WAITING_CONFIRM',
                'needs_user_input': True
            }

        except Exception as e:
            log.error(f"Erreur DriverInstallFlow: {e}")
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
        if self.current_step == "START" or user_lower in ['commencer', 'start', 'scan']:
            return await self.run(context)

        # Confirmer l'installation
        if self.current_step == "RESULTS" and user_lower in ['oui', 'yes', 'installer', 'installe']:
            self.current_step = "CONFIRM_INSTALL"
            await asyncio.sleep(0.5)

            # Effectuer l'installation
            self.current_step = "INSTALLING"
            log.info("Installation des drivers...")

            devices = context.get('devices', {})
            results = self.driver_installer.install_missing(devices)

            context['results'] = results
            self.current_step = "DONE"

            return {
                'success': True,
                'step': 'DONE',
                'context': context,
                'message': self.get_message('DONE', context),
                'next_step': None  # Terminé
            }

        # Refuser l'installation
        if self.current_step == "RESULTS" and user_lower in ['non', 'no', 'pas maintenant']:
            log.info("Installation refusée par l'utilisateur")
            return {
                'success': True,
                'step': 'DONE',
                'context': {'cancelled': True},
                'message': "✅ Installation annulée. Vous pourrez le faire plus tard si besoin.",
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
        flow = DriverInstallFlow(MockConversation())

        print("=== Test DriverInstallFlow ===\n")

        # Étape 1: START
        result = await flow.run()
        print(f"Step: {result['step']}")
        print(f"Message: {result.get('message', 'N/A')}\n")

        # Simuler input utilisateur
        result = await flow.handle_user_input("oui", result['context'])
        print(f"Step: {result['step']}")
        print(f"Message: {result.get('message', 'N/A')}\n")

    asyncio.run(test_flow())
