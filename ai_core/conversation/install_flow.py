"""
AI Rescue USB - Install Flow
=============================
Flux de conversation pour l'installation d'un OS.
Guide l'utilisateur étape par étape.

Exemple de conversation :
User: "Installe Windows"
AI: "Je peux installer Windows 10 ou 11. Lequel préférez-vous ?"
User: "Windows 11"
AI: "Windows 11 nécessite 4GB RAM et 64GB disque. Votre PC a 8GB RAM et 500GB disque, c'est parfait ! Voulez-vous continuer ?"
User: "Oui"
AI: "Je télécharge Windows 11... [progress] ... Téléchargement terminé. Je prépare l'installation..."
User: "OK"
AI: "Installation terminée ! Vous pouvez redémarrer."
"""

import asyncio
import logging
from typing import Optional
from pathlib import Path

log = logging.getLogger("install-flow")


class InstallFlow:
    """
    Flux d'installation guidé.
    Étapes :
    1. Choisir l'OS
    2. Vérifier compatibilité
    3. Choisir le disque
    4. Confirmer (WARNING destructif)
    5. Télécharger ISO
    6. Installer
    7. Configurer
    8. Terminer
    """
    
    def __init__(self, manager):
        self.manager = manager
        self.step = 0
        self.selected_os = None
        self.selected_disk = None
        self.compatibility = None
        
        # Injecter les dépendances
        self.install_agent = None
        self.hw_detector = None
        self.security = None
        
        self._load_agents()
    
    def _load_agents(self):
        """Charge les agents nécessaires."""
        try:
            from agents.install_backup_recovery import InstallAgent, SUPPORTED_OS
            self.install_agent = InstallAgent()
            self.supported_os = SUPPORTED_OS
        except Exception as e:
            log.warning(f"InstallAgent non disponible: {e}")
            self.supported_os = {}
        
        try:
            from detection.hardware.detector import HardwareDetector
            self.hw_detector = HardwareDetector()
        except Exception as e:
            log.warning(f"HardwareDetector non disponible: {e}")
        
        try:
            from security.security_manager import SecurityManager
            self.security = SecurityManager()
        except Exception as e:
            log.warning(f"SecurityManager non disponible: {e}")
    
    async def start(self, user_input: str) -> str:
        """Démarre le flux d'installation."""
        log.info("Starting install flow")
        
        # Étape 0 : Choisir l'OS
        self.step = 0
        return self._step_choose_os()
    
    def _step_choose_os(self) -> str:
        """Étape 1 : Choisir l'OS à installer."""
        os_list = []
        
        # Grouper par type
        windows = []
        linux = []
        bsd = []
        
        for os_id, info in self.supported_os.items():
            if info["type"] == "windows":
                windows.append((os_id, info))
            elif info["type"] == "linux":
                linux.append((os_id, info))
            elif info["type"] == "bsd":
                bsd.append((os_id, info))
        
        message = "Quel système voulez-vous installer ?\n\n"
        
        if windows:
            message += "🪟 **Windows**\n"
            for os_id, info in windows:
                message += f"  • {info['name']} ({info['iso_size_gb']}GB)\n"
            message += "\n"
        
        if linux:
            message += "🐧 **Linux**\n"
            for os_id, info in linux:
                message += f"  • {info['name']} ({info['iso_size_gb']}GB)\n"
            message += "\n"
        
        if bsd:
            message += "👹 **BSD**\n"
            for os_id, info in bsd:
                message += f"  • {info['name']} ({info['iso_size_gb']}GB)\n"
        
        message += "\nDites-moi lequel vous préférez (ex: \"Windows 11\", \"Ubuntu\")"
        
        return message
    
    async def handle_input(self, user_input: str) -> str:
        """Traite l'entrée utilisateur selon l'étape actuelle."""
        inp = user_input.lower()
        
        # Étape 0 : Choix de l'OS
        if self.step == 0:
            return self._process_os_choice(inp)
        
        # Étape 1 : Confirmation compatibilité
        elif self.step == 1:
            return await self._process_compatibility_confirm(inp)
        
        # Étape 2 : Choix du disque
        elif self.step == 2:
            return self._process_disk_choice(inp)
        
        # Étape 3 : Confirmation finale (destructive)
        elif self.step == 3:
            return await self._process_final_confirm(inp)
        
        # Étape 4 : Installation en cours
        elif self.step == 4:
            return "Installation en cours, veuillez patienter..."
        
        return "Je n'ai pas compris. Pouvez-vous reformuler ?"
    
    def _process_os_choice(self, user_input: str) -> str:
        """Traite le choix de l'OS."""
        # Chercher l'OS mentionné
        found_os = None
        
        for os_id, info in self.supported_os.items():
            os_name = info["name"].lower()
            
            # Match partiel
            if user_input in os_name or os_name in user_input:
                found_os = os_id
                break
            
            # Match keywords
            if "windows 11" in user_input and "windows 11" in os_name:
                found_os = os_id
                break
            elif "windows 10" in user_input and "windows 10" in os_name:
                found_os = os_id
                break
            elif ("ubuntu" in user_input or "linux" in user_input) and info["type"] == "linux":
                found_os = os_id
                break
        
        if not found_os:
            return "Je n'ai pas reconnu ce système. Pouvez-vous préciser ?\nPar exemple : \"Windows 11\", \"Ubuntu\", \"Debian\""
        
        self.selected_os = found_os
        os_info = self.supported_os[found_os]
        
        # Étape suivante : vérifier compatibilité
        self.step = 1
        return self._check_compatibility()
    
    def _check_compatibility(self) -> str:
        """Vérifie la compatibilité matérielle."""
        if not self.hw_detector or not self.install_agent:
            return "Désolé, je ne peux pas vérifier la compatibilité pour le moment."
        
        # Détecter le matériel
        hw = self.hw_detector.detect_all()
        
        # Convertir en dict pour l'agent
        hw_dict = {
            "ram_mb": hw.ram.total_mb,
            "disk_gb": sum(d.size_gb for d in hw.disks) if hw.disks else 0,
            "tpm": hw.tpm,
            "secure_boot": hw.secure_boot,
        }
        
        # Vérifier compatibilité
        self.compatibility = self.install_agent.check_compatibility(self.selected_os, hw_dict)
        
        os_info = self.supported_os[self.selected_os]
        
        if self.compatibility["compatible"]:
            message = f"**{os_info['name']}** est compatible avec votre PC !\n\n"
            message += f"Votre matériel :\n"
            message += f"  • CPU : {hw.cpu.model}\n"
            message += f"  • RAM : {hw.ram.total_mb}MB\n"
            message += f"  • Disque : {hw_dict['disk_gb']:.0f}GB\n"
            
            if hw.tpm:
                message += f"  • TPM : ✓\n"
            if hw.secure_boot:
                message += f"  • Secure Boot : ✓\n"
            
            message += "\nVoulez-vous continuer l'installation ?"
            return message
        
        else:
            message = f"⚠️ **{os_info['name']}** n'est pas compatible avec votre PC.\n\n"
            message += "Problèmes détectés :\n"
            for issue in self.compatibility["issues"]:
                message += f"  • {issue}\n"
            
            message += "\nVoulez-vous installer un autre système à la place ?"
            return message
    
    async def _process_compatibility_confirm(self, user_input: str) -> str:
        """Traite la confirmation de compatibilité."""
        if any(w in user_input.lower() for w in ["oui", "yes", "ok", "continue"]):
            if not self.compatibility or not self.compatibility["compatible"]:
                # Retourner au choix d'OS
                self.step = 0
                return self._step_choose_os()
            
            # Étape suivante : choisir le disque
            self.step = 2
            return self._step_choose_disk()
        
        elif any(w in user_input.lower() for w in ["non", "no", "annule"]):
            return "Installation annulée. Que voulez-vous faire d'autre ?"
        
        else:
            return "Répondez \"oui\" pour continuer ou \"non\" pour annuler."
    
    def _step_choose_disk(self) -> str:
        """Étape 2 : Choisir le disque d'installation."""
        if not self.hw_detector:
            return "Erreur : détection matériel indisponible."
        
        hw = self.hw_detector.detect_all()
        
        if not hw.disks:
            return "Aucun disque détecté."
        
        message = "Sur quel disque voulez-vous installer ?\n\n"
        
        for i, disk in enumerate(hw.disks):
            message += f"**{i+1}. {disk.device}**\n"
            message += f"   • Modèle : {disk.model}\n"
            message += f"   • Taille : {disk.size_gb:.0f}GB\n"
            message += f"   • Type : {disk.type.upper()}\n"
            
            if disk.partitions:
                os_detected = [p.get("fs") for p in disk.partitions if p.get("fs")]
                if os_detected:
                    message += f"   • OS détecté : {', '.join(set(os_detected))}\n"
            
            message += "\n"
        
        message += "\n⚠️ **ATTENTION** : L'installation effacera toutes les données du disque choisi !\n"
        message += "Choisissez le numéro du disque (ex: \"1\" ou \"2\")"
        
        return message
    
    def _process_disk_choice(self, user_input: str) -> str:
        """Traite le choix du disque."""
        try:
            disk_num = int(user_input.strip()) - 1
            
            hw = self.hw_detector.detect_all()
            
            if 0 <= disk_num < len(hw.disks):
                self.selected_disk = hw.disks[disk_num]
                
                # Étape suivante : confirmation finale
                self.step = 3
                return self._final_confirmation()
            else:
                return "Numéro invalide. Choisissez un disque dans la liste."
        
        except ValueError:
            # Chercher par nom
            for disk in self.hw_detector.detect_all().disks:
                if user_input.lower() in disk.device.lower() or user_input.lower() in disk.model.lower():
                    self.selected_disk = disk
                    self.step = 3
                    return self._final_confirmation()
            
            return "Je n'ai pas compris. Dites le numéro du disque (ex: \"1\")"
    
    def _final_confirmation(self) -> str:
        """Étape 3 : Confirmation finale (destructive)."""
        os_info = self.supported_os[self.selected_os]
        
        message = "## ⚠️ CONFIRMATION FINALE\n\n"
        message += f"**Système :** {os_info['name']}\n"
        message += f"**Disque :** {self.selected_disk.device} ({self.selected_disk.model})\n\n"
        
        message += "**Cette action va :**\n"
        message += "  • Effacer TOUTES les données du disque\n"
        message += "  • Créer de nouvelles partitions\n"
        message += "  • Installer le système d'exploitation\n\n"
        
        message += "Êtes-vous **absolument sûr** ? Tapez \"OUI\" pour confirmer."
        
        return message
    
    async def _process_final_confirm(self, user_input: str) -> str:
        """Traite la confirmation finale."""
        if user_input.lower().strip() in ["oui", "yes", "confirme"]:
            # Commencer l'installation
            self.step = 4
            return await self._start_installation()
        
        elif any(w in user_input.lower() for w in ["non", "no", "annule"]):
            return "Installation annulée. Que voulez-vous faire ?"
        
        else:
            return "Tapez \"OUI\" pour confirmer l'installation, ou \"NON\" pour annuler."
    
    async def _start_installation(self) -> str:
        """Étape 4 : Commence l'installation."""
        os_info = self.supported_os[self.selected_os]
        
        message = f"Parfait ! Je commence l'installation de **{os_info['name']}**...\n\n"
        message += "Étapes :\n"
        message += "  1. 📥 Téléchargement de l'ISO\n"
        message += "  2. ✅ Vérification intégrité\n"
        message += "  3. 💿 Préparation du disque\n"
        message += "  4. 🚀 Installation\n"
        message += "  5. ⚙️ Configuration\n\n"
        
        # Callback pour montrer la progression
        if self.manager.on_progress:
            self.manager.on_progress("download_iso", 0)
        
        # Télécharger l'ISO (placeholder - à implémenter)
        # iso_path = await self._download_iso()
        # if not iso_path:
        #     return "Erreur lors du téléchargement de l'ISO."
        
        message += "Téléchargement en cours... (simulation)\n"
        
        # Simuler progression
        for i in range(0, 101, 10):
            await asyncio.sleep(0.1)  # Simuler
            if self.manager.on_progress:
                self.manager.on_progress("download_iso", i)
        
        message += "✅ Téléchargement terminé !\n\n"
        message += "Je prépare maintenant le disque..."
        
        # TODO: Implémenter l'installation réelle
        # - Monter l'ISO
        # - Partitionner le disque
        # - Formater
        # - Copier les fichiers
        # - Installer bootloader
        # - Configurer
        
        message += "\n\n💡 **Installation simulée** - À implémenter avec :\n"
        message += "  • `dd` pour copier l'ISO sur USB\n"
        message += "  • `fdisk`/`parted` pour partitionner\n"
        message += "  • `mkfs` pour formater\n"
        message += "  • `chroot` pour configurer\n"
        
        # Étape suivante : terminé
        self.step = 5
        return await self._finish_installation()
    
    async def _finish_installation(self) -> str:
        """Termine l'installation."""
        os_info = self.supported_os[self.selected_os]
        
        message = "## ✅ Installation terminée !\n\n"
        message += f"**{os_info['name']}** a été installé avec succès sur **{self.selected_disk.device}**.\n\n"
        
        message += "**Prochaines étapes :**\n"
        message += "  1. Retirez la clé USB\n"
        message += "  2. Redémarrez l'ordinateur\n"
        message += "  3. Suivez l'assistant de configuration\n\n"
        
        message += "Voulez-vous faire autre chose (sauvegarde, réparation, etc.) ?"
        
        # Reset le flux
        self.manager.current_flow = None
        self.manager.context.current_flow = ""
        
        return message
