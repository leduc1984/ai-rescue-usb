"""
AI Rescue USB - Main Entry Point
=================================
Démarre le système AI Rescue USB.
Connecte tous les composants : IA, voix, détection, agents.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_core.voice_system import VoiceInterface
from ai_core.conversation import ConversationManager, InstallFlow, RepairFlow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger("main")


class AIRescueSystem:
    """Système principal AI Rescue USB."""
    
    def __init__(self):
        # Initialiser les composants
        self.voice = VoiceInterface()
        self.conversation = ConversationManager()
        
        # Connecter les flows
        self.conversation.register_flow("install", InstallFlow)
        self.conversation.register_flow("repair", RepairFlow)
        
        # Callbacks pour la voix
        self.conversation.on_ai_response = self._on_ai_response
        
        log.info("AI Rescue System initialized")
    
    async def _on_ai_response(self, text: str):
        """Callback quand l'IA génère une réponse."""
        # Prononcer la réponse si voix activée
        await self.voice.speak_response(text)
    
    async def run_interactive(self):
        """Mode interactif : attend les commandes utilisateur."""
        print("\n" + "=" * 60)
        print("  AI RESCUE USB - Universal Computer Technician")
        print("=" * 60)
        print("\nJe suis prêt à vous aider.\n")
        print("Vous pouvez me parler ou taper du texte.\n")
        print("Exemples :\n")
        print("  • \"Installe Windows 11\"")
        print("  • \"Mon PC ne démarre plus\"")
        print("  • \"Sauvegarde mes fichiers\"")
        print("  • \"Diagnostique mon ordinateur\"\n")
        print("-" * 60 + "\n")
        
        # Accueil vocal
        await self.voice.speak_response("Bonjour, je suis AI Rescue. Comment puis-je vous aider ?")
        
        while True:
            try:
                # Écouter ou lire l'entrée
                print("🎤 Parlez ou tapez votre demande (Ctrl+C pour quitter)...\n")
                
                # Mode vocal
                user_text = await self.voice.listen_and_transcribe()
                
                # Si rien entendu, demander texte
                if not user_text.strip():
                    user_text = input("💬 Entrez votre demande : ").strip()
                
                if not user_text:
                    continue
                
                # Traiter la demande
                response = await self.conversation.process_user_input(user_text, is_voice=True)
                
                # Afficher la réponse
                print(f"\n🤖 AI Rescue :\n\n{response}\n")
                print("-" * 60 + "\n")
            
            except KeyboardInterrupt:
                print("\n\nAu revoir ! 👋\n")
                await self.voice.speak_response("Au revoir !")
                break
            except Exception as e:
                log.error(f"Error in main loop: {e}")
                print(f"Erreur : {e}\n")
    
    async def run_text_only(self):
        """Mode texte uniquement (sans voix)."""
        print("\n" + "=" * 60)
        print("  AI RESCUE USB - Mode Texte")
        print("=" * 60 + "\n")
        
        while True:
            try:
                user_text = input("Vous : ").strip()
                
                if not user_text:
                    continue
                
                if user_text.lower() in ["quit", "exit", "q"]:
                    break
                
                response = await self.conversation.process_user_input(user_text)
                print(f"\nAI Rescue :\n{response}\n")
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                log.error(f"Error: {e}")


async def main():
    """Point d'entrée principal."""
    system = AIRescueSystem()
    
    # Choisir le mode
    if "--text-only" in sys.argv:
        await system.run_text_only()
    else:
        await system.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())
