"""
AI Rescue USB - Network Flow
=============================
Flux conversationnel pour gestion réseau
"""

import asyncio
import logging

log = logging.getLogger("network-flow")


class NetworkFlow:
    """Flux de gestion réseau guidé"""
    
    def __init__(self, manager):
        self.manager = manager
        self.step = 0
        self.finished = False
        self.selected_network = None
        
        try:
            from agents.network_agent import NetworkAgent
            self.network = NetworkAgent()
        except Exception as e:
            log.error(f"Cannot load NetworkAgent: {e}")
            self.network = None
    
    async def start(self, user_input: str) -> str:
        """Démarre le flux réseau"""
        if not self.network:
            return "❌ L'agent réseau n'est pas disponible sur ce système."
        
        return (
            "🌐 **Gestion Réseau - AI Rescue USB**\n\n"
            "Que voulez-vous faire ?\n\n"
            "1. **Voir les réseaux WiFi disponibles**\n"
            "2. **Se connecter à un réseau WiFi**\n"
            "3. **Tester la connexion Internet**\n"
            "4. **Voir le statut actuel**\n"
            "5. **Réseaux sauvegardés**\n\n"
            "Dites-moi le numéro."
        )
    
    async def handle_input(self, user_input: str) -> str:
        """Traite l'entrée utilisateur selon l'étape"""
        inp = user_input.lower().strip()
        
        # Étape 0 : Menu principal
        if self.step == 0:
            return await self._handle_menu(inp)
        
        # Étape 1 : Sélection réseau WiFi
        elif self.step == 1:
            return await self._handle_wifi_selection(inp)
        
        # Étape 2 : Mot de passe WiFi
        elif self.step == 2:
            return await self._handle_wifi_password(inp)
        
        # Étape 3 : Résultat de connexion
        elif self.step == 3:
            self.finished = True
            return "✅ Opération terminée !"
        
        return "Veuillez choisir une option valide."
    
    async def _handle_menu(self, user_input: str) -> str:
        """Gère le menu principal"""
        if any(w in user_input for w in ["1", "wifi", "réseaux", "réseau", "network", "networks"]):
            # Afficher les réseaux WiFi disponibles
            networks = self.network.scan_wifi()
            
            if not networks:
                return "❌ Aucun réseau WiFi trouvé.\n\nVérifiez que la carte WiFi est activée."
            
            self.step = 1
            msg = "📡 **Réseaux WiFi détectés :**\n\n"
            
            for i, net in enumerate(networks, 1):
                signal_bar = "📶" * (net["signal"] // 25 + 1)
                lock = "🔒" if net["secured"] else "🔓"
                msg += f"{i}. {lock} **{net['ssid']}** {signal_bar}\n"
                msg += f"   Signal : {net['signal']}%\n"
            
            msg += "\nQuel réseau voulez-vous ? (numéro)"
            return msg
        
        elif any(w in user_input for w in ["2", "connecter", "connect"]):
            # Demander le nom du réseau
            return (
                "Quel est le nom (SSID) du réseau WiFi ?\n\n"
                "Entrez le nom exact du réseau (respectez la casse)."
            )
        
        elif any(w in user_input for w in ["3", "test", "tester", "internet"]):
            # Tester la connexion
            result = self.network.test_internet()
            
            if result["success"]:
                return (
                    "✅ **CONNEXION INTERNET OK**\n\n"
                    "Vous êtes connecté à Internet.\n\n"
                    "Que voulez-vous faire maintenant ?"
                )
            else:
                return (
                    "❌ **PAS DE CONNEXION INTERNET**\n\n"
                    f"Raison : {result['message']}\n\n"
                    "Voulez-vous :\n"
                    "1. Vérifier le statut réseau\n"
                    "2. Se connecter à un WiFi\n"
                    "3. Retour au menu principal"
                )
        
        elif any(w in user_input for w in ["4", "statut", "status"]):
            # Statut actuel
            status = self.network.get_connection_status()
            
            if status["connected"]:
                return (
                    f"✅ **CONNECTÉ**\n\n"
                    f"Type : {status['type']}\n"
                    f"IP : {status['ip']}\n\n"
                    "Que voulez-vous faire maintenant ?"
                )
            else:
                return (
                    f"❌ **DÉCONNECTÉ**\n\n"
                    "Aucune connexion réseau active.\n\n"
                    "Voulez-vous vous connecter à un WiFi ?"
                )
        
        elif any(w in user_input for w in ["5", "sauvegardé", "saved"]):
            # Réseaux sauvegardés
            networks = self.network.get_saved_networks()
            
            if networks:
                msg = "📋 **Réseaux WiFi sauvegardés :**\n\n"
                for net in networks:
                    msg += f"  • {net}\n"
                msg += "\nVoulez-vous vous connecter à l'un d'eux ?"
                return msg
            else:
                return "Aucun réseau sauvegardé pour le moment."
        
        else:
            return (
                "Je n'ai pas compris. Choisissez :\n"
                "1. Voir les réseaux WiFi\n"
                "2. Se connecter\n"
                "3. Tester Internet\n"
                "4. Statut actuel\n"
                "5. Réseaux sauvegardés"
            )
    
    async def _handle_wifi_selection(self, user_input: str) -> str:
        """Gère la sélection du réseau WiFi"""
        try:
            # Récupérer les réseaux
            networks = self.network.scan_wifi()
            
            # Tenter de parser un numéro
            if user_input.isdigit():
                index = int(user_input) - 1
                if 0 <= index < len(networks):
                    self.selected_network = networks[index]
                    
                    # Demander le mot de passe si nécessaire
                    if self.selected_network["secured"]:
                        self.step = 2
                        return (
                            f"🔒 **{self.selected_network['ssid']}** est sécurisé.\n\n"
                            "Quel est le mot de passe WiFi ?"
                        )
                    else:
                        # Réseau ouvert, connecter directement
                        self.step = 2
                        return await self._connect_wifi(None)
                else:
                    return "Numéro invalide. Choisissez un réseau de la liste."
            else:
                # Chercher par SSID
                for net in networks:
                    if user_input.lower() == net["ssid"].lower():
                        self.selected_network = net
                        if net["secured"]:
                            self.step = 2
                            return (
                                f"🔒 **{net['ssid']}** est sécurisé.\n\n"
                                "Quel est le mot de passe WiFi ?"
                            )
                        else:
                            self.step = 2
                            return await self._connect_wifi(None)
                
                return "Réseau non trouvé. Essayez à nouveau."
                
        except Exception as e:
            log.error(f"WiFi selection error: {e}")
            return f"Erreur : {str(e)}"
    
    async def _handle_wifi_password(self, password: str) -> str:
        """Gère l'entrée du mot de passe WiFi"""
        if not password or password.strip() == "":
            return "Mot de passe vide. Réessayez ou tapez 'annuler'."
        
        if password.lower() in ["annuler", "cancel", "retour", "back"]:
            self.step = 0
            return await self.start("")
        
        return await self._connect_wifi(password)
    
    async def _connect_wifi(self, password: str) -> str:
        """Tente la connexion WiFi"""
        if not self.selected_network:
            return "Aucun réseau sélectionné."
        
        result = self.network.connect_wifi(self.selected_network["ssid"], password)
        
        self.step = 3
        
        if result["success"]:
            # Vérifier la connexion
            status = self.network.get_connection_status()
            internet = self.network.test_internet()
            
            msg = f"✅ **CONNECTÉ À {self.selected_network['ssid']}**\n\n"
            msg += f"IP : {status.get('ip', 'unknown')}\n"
            
            if internet["success"]:
                msg += "Internet : ✅ Accessible\n\n"
            else:
                msg += "Internet : ❌ {internet['message']}\n\n"
            
            msg += "Que voulez-vous faire maintenant ?"
            return msg
        else:
            return (
                f"❌ **ÉCHEC DE CONNEXION**\n\n"
                f"Raison : {result['message']}\n\n"
                "Vérifiez que le mot de passe est correct.\n\n"
                "Voulez-vous réessayer ?"
            )
    
    def is_finished(self) -> bool:
        """Vérifie si le flux est terminé"""
        return self.finished
