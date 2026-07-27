"""
AI Rescue USB - Universal Assistant
====================================
L'IA qui répond à TOUT, peu importe la question.
Pas de flux rigide : conversation naturelle, détection d'intention,
et redirection vers le bon agent quand nécessaire.
"""

import logging
from typing import Optional
from pathlib import Path

log = logging.getLogger("universal")


# ============================================================
# Base de connaissances embarquée
# ============================================================
KNOWLEDGE = {
    # Questions techniques fréquentes
    "windows_ne_demarre_plus": {
        "trigger": ["ne démarre pas", "ne boot pas", "écran noir", "bsod", "écran bleu"],
        "answer": "Un Windows qui ne démarre plus a 3 causes principales :\n\n" +
                  "1. **Bootloader endommagé** (le plus fréquent)\n" +
                  "2. **Fichiers système corrompus**\n" +
                  "3. **Disque défectueux**\n\n" +
                  "Je peux diagnostiquer automatiquement. Dites-moi juste **\"diagnostique\"** et je m'en occupe."
    },
    "linux_grub_rescue": {
        "trigger": ["grub rescue", "grub error", "no such partition"],
        "answer": "L'erreur **\"grub rescue\"** signifie que GRUB ne trouve plus sa config.\n\n" +
                  "Causes fréquentes :\n" +
                  "• Redimensionnement de partitions\n" +
                  "• Mise à jour cassée\n" +
                  "• Double boot cassé\n\n" +
                  "Je peux réinstaller GRUB en 2 minutes. Dites **\"répare le grub\"** et c'est parti."
    },
    "quel_os_vieux_pc": {
        "trigger": ["vieux pc", "ancien pc", "pc lent", "peu de ram", "quel os"],
        "answer": "Pour un vieux PC, voici mes recommandations :\n\n" +
                  "**< 2GB RAM** : Linux Mint XFCE ou Lubuntu\n" +
                  "**2-4GB RAM** : Ubuntu, Debian, Linux Mint\n" +
                  "**4-8GB RAM** : N'importe quelle distro Linux\n\n" +
                  "Windows 10/11 nécessite minimum 4GB RAM et 64GB disque.\n\n" +
                  "Dites-moi combien de RAM vous avez, et je vous recommande le meilleur OS."
    },
    "peut_pas_wifi": {
        "trigger": ["wifi", "pas d'internet", "network", "réseau"],
        "answer": "Un problème de WiFi peut venir de :\n\n" +
                  "1. **Pilote manquant** (Linux) — je peux l'installer\n" +
                  "2. **Configuration réseau** — je peux la reset\n" +
                  "3. **Matériel défectueux** — détectable\n\n" +
                  "Est-ce que vous êtes sous Windows ou Linux ? Je vais régler ça."
    },
    "donnees_perdues": {
        "trigger": ["perdu", "effacé", "supprimé", "formater", "récupérer"],
        "answer": "Pas de panique ! Les fichiers supprimés sont souvent **récupérables**.\n\n" +
                  "**IMPORTANT** : N'écrivez PLUS rien sur le disque !\n\n" +
                  "Je peux scanner avec **TestDisk** et **PhotoRec** gratuitement.\n\n" +
                  "Dites-moi quels fichiers vous avez perdus (photos, documents, videos...) " +
                  "et je lance la récupération."
    },
    "disque_sante": {
        "trigger": ["santé disque", "smart", " disque en panne", "bruit disque"],
        "answer": "Je vais analyser la santé de votre disque avec les outils SMART.\n\n" +
                  "Indicateurs analysés :\n" +
                  "• Secteurs défectueux\n" +
                  "• Température\n" +
                  "• Temps de fonctionnement\n" +
                  "• Taux d'erreur\n\n" +
                  "Dites **\"analyse mon disque\"** et je fais le scan complet."
    },
    "install_windows": {
        "trigger": ["installer windows", "reinstaller windows", "fresh install windows"],
        "answer": "Je peux installer Windows pour vous. Étapes :\n\n" +
                  "1. **Sauvegarde** de vos fichiers (IMPORTANT)\n" +
                  "2. **Téléchargement** de l'ISO officielle Microsoft\n" +
                  "3. **Installation** automatique\n" +
                  "4. **Configuration** (pilotes, mises à jour)\n\n" +
                  "**Combien de RAM** avez-vous ? Je dois vérifier la compatibilité."
    },
    "install_linux": {
        "trigger": ["installer linux", "ubuntu", "debian", "fedora", "arch", "mint"],
        "answer": "Excellent choix ! Linux est parfait pour sauver un vieux PC.\n\n" +
                  "**Mes recommandations :**\n" +
                  "• **Débutant** : Linux Mint (ressemble à Windows)\n" +
                  "• **Populaire** : Ubuntu 24.04 LTS\n" +
                  "• **Léger** : Debian 12 (vieux PC)\n" +
                  "• **Avancé** : Arch Linux\n\n" +
                  "Lequel vous intéresse ? Je gère tout de A à Z."
    },
    "install_freebsd": {
        "trigger": ["freebsd", "openbsd", "netbsd", "bsd"],
        "answer": "BSD est un choix solide pour les serveurs et les puristes !\n\n" +
                  "**Variantes disponibles :**\n" +
                  "• **FreeBSD 14** — le plus populaire, bon support matériel\n" +
                  "• **OpenBSD 7.4** — sécurité maximale\n" +
                  "• **NetBSD** — portable sur tout matériel\n\n" +
                  "Attention : BSD est moins compatible avec le matériel grand public.\n" +
                  "Je vérifie la compatibilité avant ?"
    },
    "slow_pc": {
        "trigger": ["lent", "ralenti", "slow", "fige", "freeze"],
        "answer": "Un PC lent a souvent 3 causes :\n\n" +
                  "1. **Disque dur vieillissant** (HDD → SSD résout 90% des cas)\n" +
                  "2. **RAM insuffisante** (trop de programs ouverts)\n" +
                  "3. **Malware/bloatware** (programmes parasites)\n\n" +
                  "Je lance un **diagnostic complet** ? Ça prend 30 secondes."
    },
    "mot_de_passe_windows": {
        "trigger": ["mot de passe", "password", "oublié", "perdu mot", "accès"],
        "answer": "Je peux remettre à zéro le mot de passe Windows local.\n\n" +
                  "**Attention** : ça ne fonctionne que pour Windows local, PAS pour compte Microsoft.\n\n" +
                  "**Méthode** : modification du SAM (base de données des comptes)\n\n" +
                  "Voulez-vous que je crée un **nouveau compte administrateur** à la place ? C'est plus sûr."
    },
    "virus_malware": {
        "trigger": ["virus", "malware", "infecté", "ransomware", "adware"],
        "answer": "Pas de panique. Voici la procédure :\n\n" +
                  "1. **Déconnecter d'Internet** (coupe la propagation)\n" +
                  "2. **Sauvegarder les fichiers importants** d'abord\n" +
                  "3. **Scanner avec ClamAV** (offline)\n" +
                  "4. **Nettoyer** ou **réinstaller** selon la gravité\n\n" +
                  "Je lance un scan ? Sauvegardez AVANT pour être safe."
    },
    "upgrade_ssd": {
        "trigger": ["ssd", "upgrade", "migrer", "cloner disque"],
        "answer": "Je peux cloner votre disque vers un SSD sans réinstaller.\n\n" +
                  "**Procédure :**\n" +
                  "1. Brancher le SSD (USB ou interne)\n" +
                  "2. **Clone exact** du disque source\n" +
                  "3. **Boot sur le SSD** — tout reste identique\n\n" +
                  "Boost typique : **5-10x plus rapide** qu'un HDD.\n\n" +
                  "Le SSD est-il branché ?"
    },
    "dual_boot": {
        "trigger": ["dual boot", "double boot", "deux os", "windows + linux"],
        "answer": "Je peux installer un double boot (Windows + Linux) proprement.\n\n" +
                  "**Étapes :**\n" +
                  "1. **Sauvegarder** Windows (au cas où)\n" +
                  "2. **Réduire la partition Windows**\n" +
                  "3. **Installer Linux** à côté\n" +
                  "4. **Configurer GRUB** (menu au démarrage)\n\n" +
                  "Au boot, vous choisirez Windows ou Linux.\n\n" +
                  "Combien d'espace libre sur votre disque ?"
    },
    "erreur_bsod": {
        "trigger": ["bsod", "blue screen", "écran bleu", "stop error", "0x0000"],
        "answer": "Un BSOD indique une erreur critique. Codes fréquents :\n\n" +
                  "• **CRITICAL_PROCESS_DIED** — pilote ou fichier système\n" +
                  "• **IRQL_NOT_LESS_OR_EQUAL** — conflit pilote\n" +
                  "• **MEMORY_MANAGEMENT** — RAM défectueuse\n" +
                  "• **PAGE_FAULT_IN_NONPAGED** — disque ou RAM\n\n" +
                  "Pouvez-vous me donner **le code d'erreur** (ex: 0x0000007E) ?"
    },
    "boot_usb": {
        "trigger": ["booter sur usb", "démarrer usb", "bios boot", "choisir usb"],
        "answer": "Pour démarrer sur la clé USB :\\n\\n" +
                  "1. **Brancher la clé** AI Rescue USB\\n" +
                  "2. **Redémarrer** le PC\\n" +
                  "3. **Appuyer sur F12/F2/Del/Echap** pendant le démarrage\\n" +
                  "   (dépend de la marque)\\n" +
                  "4. Choisir **\\\"USB\\\"** ou **\\\"UEFI: xxx\\\"** dans le menu\\n\\n" +
                  "**Marques courantes :**\\n" +
                  "• Dell : F12\\n" +
                  "• HP : F9 ou F10\\n" +
                  "• Lenovo : F12 ou Novo Button\\n" +
                  "• Asus : F8 ou Echap\\n" +
                  "• Acer : F12\\n\\n" +
                  "Quelle est la marque de votre PC ?"
    },
    "antivirus_scan": {
        "trigger": ["virus", "malware", "antivirus", "scan virus", "nettoyer", "infecté", "ransomware"],
        "answer": "Je peux scanner votre système pour détecter et éliminer les menaces.\\n\\n" +
                  "**Processus de scan :**\\n" +
                  "1. **Scan rapide** des zones critiques (2-5 minutes)\\n" +
                  "2. **Identification** des menaces\\n" +
                  "3. **Nettoyage automatique** (mise en quarantaine)\\n" +
                  "4. **Rapport détaillé**\\n\\n" +
                  "Dites **\\\"scan antivirus\\\"** pour lancer un scan complet.\\n\\n" +
                  "**Conseil important** : Si vous suspectez un ransomware, déconnectez-vous d'Internet immédiatement !\\n\\n" +
                  "Voulez-vous lancer un scan maintenant ?"
    },
    "network_config": {
        "trigger": ["wifi", "internet", "réseau", "network", "connexion"],
        "answer": "Je peux vous aider avec votre connexion réseau.\\n\\n" +
                  "**Ce que je peux faire :**\\n" +
                  "• **Détecter** automatiquement le WiFi disponible\\n" +
                  "• **Connexion sécurisée** avec mot de passe\\n" +
                  "• **Diagnostic** de la connexion\\n" +
                  "• **Configuration** des paramètres réseau\\n\\n" +
                  "Dites **\\\"connecter au wifi\\\"** pour scanner les réseaux disponibles.\\n\\n" +
                  "Ou **\\\"tester internet\\\"** pour vérifier votre connexion actuelle.\\n\\n" +
                  "Quel est votre problème réseau ?"
    },
    "format_disk": {
        "trigger": ["formater", "effacer tout", "remise à zéro", "wipe"],
        "answer": "**ATTENTION** : Formater efface TOUT définitivement.\n\n" +
                  "Avant de formater, je peux :\n" +
                  "1. **Sauvegarder** vos fichiers importants\n" +
                  "2. **Créer une image disque** complète\n" +
                  "3. **Réinstaller** l'OS de zéro\n\n" +
                  "Êtes-vous **sûr à 100%** de vouloir continuer ?\n" +
                  "C'est irréversible."
    },
}


class UniversalAssistant:
    """
    L'IA universelle qui répond à TOUTE question.
    Fonctionne hors flux spéciaux. Utilise la base de connaissance embarquée.
    """

    def __init__(self):
        self.knowledge = KNOWLEDGE
        self.hw_detector = None
        self.os_detector = None
        self._load_agents()

    def _load_agents(self):
        """Charge les agents (résilients)."""
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

    def answer(self, user_input: str) -> str:
        """
        Répond à n'importe quelle question utilisateur.
        Cherche dans la base de connaissances, sinon fait une réponse générique utile.
        """
        low = user_input.lower()

        # 1. Chercher dans la base de connaissances
        for key, data in self.knowledge.items():
            for trigger in data["trigger"]:
                if trigger in low:
                    return data["answer"]

        # 2. Salutations
        if any(w in low for w in ["bonjour", "hello", "hi", "hey", "salut"]):
            return self._greeting()

        # 3. Remerciements
        if any(w in low for w in ["merci", "thanks", "thx"]):
            return "Avec plaisir ! N'hésitez pas si vous avez d'autres questions."

        # 4. Capacités
        if any(w in low for w in ["que peux-tu", "que sais tu", "tes capacités", "help", "aide"]):
            return self._capabilities()

        # 5. Matériel
        if any(w in low for w in ["quel processeur", "quelle ram", "combien ram", "mon pc"]):
            return self._describe_hardware()

        # 6. Systèmes détectés
        if any(w in low for w in ["quel os", "système installé", "windows ou linux"]):
            return self._describe_os()

        # 7. Réponse générique utile
        return self._generic_help(user_input)

    def _greeting(self) -> str:
        """Salutation."""
        return (
            "👋 **Bonjour ! Je suis AI Rescue.**\n\n"
            "Je suis votre technicien informatique personnel. "
            "Je peux vous aider à :\n\n"
            "• **Réparer** votre ordinateur (Windows/Linux/Mac)\n"
            "• **Installer** un nouveau système d'exploitation\n"
            "• **Sauvegarder** vos fichiers importants\n"
            "• **Récupérer** des fichiers supprimés\n"
            "• **Diagnostiquer** un problème matériel\n\n"
            "Dites-moi simplement ce qui ne va pas, je gère tout !"
        )

    def _capabilities(self) -> str:
        """Liste des capacités."""
        return (
            "**Ce que je sais faire :**\n\n"
            "🛠️ **Réparation**\n"
            "• Windows qui ne démarre pas\n"
            "• GRUB cassé (Linux)\n"
            "• Fichiers système corrompus\n"
            "• Bootloader EFI/MBR\n\n"
            "💿 **Installation**\n"
            "• Windows 10, 11\n"
            "• Ubuntu, Debian, Fedora, Arch, Mint\n"
            "• FreeBSD, OpenBSD\n\n"
            "💾 **Sauvegarde**\n"
            "• Clone disque complet\n"
            "• Sauvegarde fichiers\n"
            "• Image système\n\n"
            "🔍 **Récupération**\n"
            "• Fichiers supprimés\n"
            "• Disque endommagé\n"
            "• Partitions perdues\n\n"
            "🩺 **Diagnostic**\n"
            "• Santé disque (SMART)\n"
            "• Test RAM\n"
            "• Analyse performance\n\n"
            "**Que voulez-vous faire ?**"
        )

    def _describe_hardware(self) -> str:
        """Décrit le matériel détecté."""
        if not self.hw_detector:
            return "Je ne peux pasanalyser le matériel pour le moment. Réessayez plus tard."

        try:
            hw = self.hw_detector.detect_all()

            msg = "**Votre matériel :**\n\n"
            msg += f"• **CPU :** {hw.cpu.model}\n"
            msg += f"  ({hw.cpu.cores} cores, {hw.cpu.threads} threads)\n\n"
            msg += f"• **RAM :** {hw.ram.total_mb}MB ({hw.ram.type})\n"
            if hw.ram.speed_mhz:
                msg += f"  Vitesse : {hw.ram.speed_mhz} MHz\n"
            msg += "\n"

            if hw.gpus:
                msg += "**GPUs :**\n"
                for g in hw.gpus[:2]:
                    msg += f"  • {g.model} ({g.driver})\n"
                msg += "\n"

            if hw.disks:
                msg += "**Disques :**\n"
                for d in hw.disks[:4]:
                    msg += f"  • {d.device} : {d.model} ({d.size_gb:.0f}GB {d.type.upper()})\n"
                msg += "\n"

            msg += f"**BIOS :** {hw.bios_type.upper()}\n"
            msg += f"**Secure Boot :** {'Oui' if hw.secure_boot else 'Non'}\n"

            return msg
        except Exception as e:
            return f"Erreur lors de l'analyse : {e}"

    def _describe_os(self) -> str:
        """Décrit les OS détectés."""
        if not self.os_detector:
            return "Je ne peux pasanalyser les systèmes pour le moment."

        try:
            os_info = self.os_detector.detect_all()

            if not os_info.detected_os:
                return ("**Aucun système détecté** sur les disques.\n\n"
                       "Les disques sont peut-être vides ou chiffrés. "
                       "Voulez-vous installer un OS ?")

            msg = "**Systèmes détectés :**\n\n"
            for o in os_info.detected_os:
                status = "✅" if o.boot_status == "ok" else "⚠️"
                msg += f"• {status} **{o.name} {o.version}**\n"
                msg += f"  Partition : {o.partition}\n"
                msg += f"  Boot : {o.boot_status}\n"
                if o.users:
                    msg += f"  Utilisateurs : {', '.join(o.users[:3])}\n"
                msg += "\n"

            msg += f"**Mode de boot :** {os_info.boot_mode.upper()}\n"
            msg += f"**Partition :** {os_info.disk_layout.upper()}\n"

            return msg
        except Exception as e:
            return f"Erreur : {e}"

    def _generic_help(self, user_input: str) -> str:
        """Réponse générique quand rien ne match."""
        return (
            f"Je comprends que vous dites : **\"{user_input}\"**\n\n"
            "Pour mieux vous aider, voici ce que je peux faire :\n\n"
            "🔧 **Réparer** — \"Mon PC ne démarre plus\"\n"
            "💿 **Installer** — \"Installe Windows 11\"\n"
            "💾 **Sauvegarder** — \"Sauvegarde mes fichiers\"\n"
            "🔍 **Récupérer** — \"J'ai perdu mes photos\"\n"
            "🩺 **Diagnostiquer** — \"Pourquoi c'est lent ?\"\n\n"
            "Ou cliquez sur une des cartes ci-dessus 👆"
        )
