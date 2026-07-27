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
    # Questions techniques fréquentes. Chaque entrée a une réponse EN et FR ;
    # `answer()` choisit selon la langue demandée. Les triggers eux restent
    # une liste unique mélangeant EN/FR (les deux doivent déclencher la
    # bonne entrée, peu importe la langue choisie par l'utilisateur).
    "windows_wont_boot": {
        "trigger": ["ne démarre pas", "ne boot pas", "écran noir", "bsod", "écran bleu",
                    "won't boot", "wont boot", "black screen", "doesn't start"],
        "answer_en": "A Windows that won't boot usually has 3 main causes:\n\n" +
                     "1. **Damaged bootloader** (most common)\n" +
                     "2. **Corrupted system files**\n" +
                     "3. **Failing disk**\n\n" +
                     "I can diagnose this automatically. Just say **\"diagnose\"** and I'll take care of it.",
        "answer_fr": "Un Windows qui ne démarre plus a 3 causes principales :\n\n" +
                     "1. **Bootloader endommagé** (le plus fréquent)\n" +
                     "2. **Fichiers système corrompus**\n" +
                     "3. **Disque défectueux**\n\n" +
                     "Je peux diagnostiquer automatiquement. Dites-moi juste **\"diagnostique\"** et je m'en occupe."
    },
    "linux_grub_rescue": {
        "trigger": ["grub rescue", "grub error", "no such partition"],
        "answer_en": "The **\"grub rescue\"** error means GRUB can't find its config anymore.\n\n" +
                     "Common causes:\n" +
                     "• Partition resizing\n" +
                     "• A broken update\n" +
                     "• Broken dual-boot setup\n\n" +
                     "I can reinstall GRUB in 2 minutes. Say **\"repair grub\"** and I'll get started.",
        "answer_fr": "L'erreur **\"grub rescue\"** signifie que GRUB ne trouve plus sa config.\n\n" +
                     "Causes fréquentes :\n" +
                     "• Redimensionnement de partitions\n" +
                     "• Mise à jour cassée\n" +
                     "• Double boot cassé\n\n" +
                     "Je peux réinstaller GRUB en 2 minutes. Dites **\"répare le grub\"** et c'est parti."
    },
    "which_os_old_pc": {
        "trigger": ["vieux pc", "ancien pc", "pc lent", "peu de ram", "quel os",
                    "old pc", "old computer", "little ram", "which os", "what os"],
        "answer_en": "For an old PC, here are my recommendations:\n\n" +
                     "**< 2GB RAM**: Linux Mint XFCE or Lubuntu\n" +
                     "**2-4GB RAM**: Ubuntu, Debian, Linux Mint\n" +
                     "**4-8GB RAM**: Any Linux distro\n\n" +
                     "Windows 10/11 needs at least 4GB RAM and 64GB of disk space.\n\n" +
                     "Tell me how much RAM you have, and I'll recommend the best OS.",
        "answer_fr": "Pour un vieux PC, voici mes recommandations :\n\n" +
                     "**< 2GB RAM** : Linux Mint XFCE ou Lubuntu\n" +
                     "**2-4GB RAM** : Ubuntu, Debian, Linux Mint\n" +
                     "**4-8GB RAM** : N'importe quelle distro Linux\n\n" +
                     "Windows 10/11 nécessite minimum 4GB RAM et 64GB disque.\n\n" +
                     "Dites-moi combien de RAM vous avez, et je vous recommande le meilleur OS."
    },
    "wifi_issue": {
        "trigger": ["wifi", "pas d'internet", "network", "réseau", "no internet", "no wifi"],
        "answer_en": "A WiFi problem can come from:\n\n" +
                     "1. **Missing driver** (Linux) — I can install it\n" +
                     "2. **Network configuration** — I can reset it\n" +
                     "3. **Faulty hardware** — detectable\n\n" +
                     "Are you on Windows or Linux? I'll sort this out.",
        "answer_fr": "Un problème de WiFi peut venir de :\n\n" +
                     "1. **Pilote manquant** (Linux) — je peux l'installer\n" +
                     "2. **Configuration réseau** — je peux la reset\n" +
                     "3. **Matériel défectueux** — détectable\n\n" +
                     "Est-ce que vous êtes sous Windows ou Linux ? Je vais régler ça."
    },
    "lost_data": {
        "trigger": ["perdu", "effacé", "supprimé", "formater", "récupérer",
                    "lost", "deleted", "erased", "recover files"],
        "answer_en": "Don't panic! Deleted files are often **recoverable**.\n\n" +
                     "**IMPORTANT**: Stop writing anything else to that disk!\n\n" +
                     "I can scan with **TestDisk** and **PhotoRec** for free.\n\n" +
                     "Tell me which files you lost (photos, documents, videos...) " +
                     "and I'll start the recovery.",
        "answer_fr": "Pas de panique ! Les fichiers supprimés sont souvent **récupérables**.\n\n" +
                     "**IMPORTANT** : N'écrivez PLUS rien sur le disque !\n\n" +
                     "Je peux scanner avec **TestDisk** et **PhotoRec** gratuitement.\n\n" +
                     "Dites-moi quels fichiers vous avez perdus (photos, documents, videos...) " +
                     "et je lance la récupération."
    },
    "disk_health": {
        "trigger": ["santé disque", "disque en panne", "bruit disque",
                    "disk health", "failing disk", "disk noise", "smart"],
        "answer_en": "I'll analyze your disk's health using SMART data.\n\n" +
                     "Indicators checked:\n" +
                     "• Bad sectors\n" +
                     "• Temperature\n" +
                     "• Power-on hours\n" +
                     "• Error rate\n\n" +
                     "Say **\"scan my disk\"** and I'll run the full check.",
        "answer_fr": "Je vais analyser la santé de votre disque avec les outils SMART.\n\n" +
                     "Indicateurs analysés :\n" +
                     "• Secteurs défectueux\n" +
                     "• Température\n" +
                     "• Temps de fonctionnement\n" +
                     "• Taux d'erreur\n\n" +
                     "Dites **\"analyse mon disque\"** et je fais le scan complet."
    },
    "install_windows": {
        "trigger": ["installer windows", "reinstaller windows", "fresh install windows",
                    "install windows", "reinstall windows"],
        "answer_en": "I can install Windows for you. Steps:\n\n" +
                     "1. **Back up** your files (IMPORTANT)\n" +
                     "2. **Download** the official Microsoft ISO\n" +
                     "3. **Automatic installation**\n" +
                     "4. **Setup** (drivers, updates)\n\n" +
                     "**How much RAM** do you have? I need to check compatibility.",
        "answer_fr": "Je peux installer Windows pour vous. Étapes :\n\n" +
                     "1. **Sauvegarde** de vos fichiers (IMPORTANT)\n" +
                     "2. **Téléchargement** de l'ISO officielle Microsoft\n" +
                     "3. **Installation** automatique\n" +
                     "4. **Configuration** (pilotes, mises à jour)\n\n" +
                     "**Combien de RAM** avez-vous ? Je dois vérifier la compatibilité."
    },
    "install_linux": {
        "trigger": ["installer linux", "ubuntu", "debian", "fedora", "arch", "mint", "install linux"],
        "answer_en": "Great choice! Linux is perfect for saving an old PC.\n\n" +
                     "**My recommendations:**\n" +
                     "• **Beginner**: Linux Mint (looks like Windows)\n" +
                     "• **Popular**: Ubuntu 24.04 LTS\n" +
                     "• **Lightweight**: Debian 12 (old PCs)\n" +
                     "• **Advanced**: Arch Linux\n\n" +
                     "Which one interests you? I'll handle everything end to end.",
        "answer_fr": "Excellent choix ! Linux est parfait pour sauver un vieux PC.\n\n" +
                     "**Mes recommandations :**\n" +
                     "• **Débutant** : Linux Mint (ressemble à Windows)\n" +
                     "• **Populaire** : Ubuntu 24.04 LTS\n" +
                     "• **Léger** : Debian 12 (vieux PC)\n" +
                     "• **Avancé** : Arch Linux\n\n" +
                     "Lequel vous intéresse ? Je gère tout de A à Z."
    },
    "install_freebsd": {
        "trigger": ["freebsd", "openbsd", "netbsd", "bsd"],
        "answer_en": "BSD is a solid choice for servers and purists!\n\n" +
                     "**Available variants:**\n" +
                     "• **FreeBSD 14** — most popular, good hardware support\n" +
                     "• **OpenBSD 7.4** — maximum security\n" +
                     "• **NetBSD** — portable to almost any hardware\n\n" +
                     "Note: BSD is less compatible with consumer hardware.\n" +
                     "Should I check compatibility first?",
        "answer_fr": "BSD est un choix solide pour les serveurs et les puristes !\n\n" +
                     "**Variantes disponibles :**\n" +
                     "• **FreeBSD 14** — le plus populaire, bon support matériel\n" +
                     "• **OpenBSD 7.4** — sécurité maximale\n" +
                     "• **NetBSD** — portable sur tout matériel\n\n" +
                     "Attention : BSD est moins compatible avec le matériel grand public.\n" +
                     "Je vérifie la compatibilité avant ?"
    },
    "slow_pc": {
        "trigger": ["lent", "ralenti", "fige", "freeze", "slow", "frozen", "sluggish"],
        "answer_en": "A slow PC usually has 3 causes:\n\n" +
                     "1. **Aging hard drive** (HDD → SSD fixes 90% of cases)\n" +
                     "2. **Insufficient RAM** (too many programs open)\n" +
                     "3. **Malware/bloatware** (unwanted programs)\n\n" +
                     "Should I run a **full diagnostic**? It takes 30 seconds.",
        "answer_fr": "Un PC lent a souvent 3 causes :\n\n" +
                     "1. **Disque dur vieillissant** (HDD → SSD résout 90% des cas)\n" +
                     "2. **RAM insuffisante** (trop de programs ouverts)\n" +
                     "3. **Malware/bloatware** (programmes parasites)\n\n" +
                     "Je lance un **diagnostic complet** ? Ça prend 30 secondes."
    },
    "windows_password": {
        "trigger": ["mot de passe", "oublié", "perdu mot", "accès",
                    "password", "forgot password", "locked out"],
        "answer_en": "I can reset the local Windows password.\n\n" +
                     "**Note**: this only works for a local Windows account, NOT a Microsoft account.\n\n" +
                     "**Method**: editing the SAM (account database)\n\n" +
                     "Would you rather I create a **new administrator account** instead? It's safer.",
        "answer_fr": "Je peux remettre à zéro le mot de passe Windows local.\n\n" +
                     "**Attention** : ça ne fonctionne que pour Windows local, PAS pour compte Microsoft.\n\n" +
                     "**Méthode** : modification du SAM (base de données des comptes)\n\n" +
                     "Voulez-vous que je crée un **nouveau compte administrateur** à la place ? C'est plus sûr."
    },
    "virus_malware": {
        "trigger": ["virus", "malware", "infecté", "ransomware", "adware", "infected"],
        "answer_en": "Don't panic. Here's the procedure:\n\n" +
                     "1. **Disconnect from the Internet** (stops it from spreading)\n" +
                     "2. **Back up important files** first\n" +
                     "3. **Scan with ClamAV** (offline)\n" +
                     "4. **Clean** or **reinstall** depending on severity\n\n" +
                     "Should I start a scan? Back up first to be safe.",
        "answer_fr": "Pas de panique. Voici la procédure :\n\n" +
                     "1. **Déconnecter d'Internet** (coupe la propagation)\n" +
                     "2. **Sauvegarder les fichiers importants** d'abord\n" +
                     "3. **Scanner avec ClamAV** (offline)\n" +
                     "4. **Nettoyer** ou **réinstaller** selon la gravité\n\n" +
                     "Je lance un scan ? Sauvegardez AVANT pour être safe."
    },
    "upgrade_ssd": {
        "trigger": ["cloner disque", "upgrade", "migrer", "ssd", "clone disk"],
        "answer_en": "I can clone your disk to an SSD without reinstalling anything.\n\n" +
                     "**Procedure:**\n" +
                     "1. Plug in the SSD (USB or internal)\n" +
                     "2. **Exact clone** of the source disk\n" +
                     "3. **Boot from the SSD** — everything stays identical\n\n" +
                     "Typical speedup: **5-10x faster** than an HDD.\n\n" +
                     "Is the SSD plugged in?",
        "answer_fr": "Je peux cloner votre disque vers un SSD sans réinstaller.\n\n" +
                     "**Procédure :**\n" +
                     "1. Brancher le SSD (USB ou interne)\n" +
                     "2. **Clone exact** du disque source\n" +
                     "3. **Boot sur le SSD** — tout reste identique\n\n" +
                     "Boost typique : **5-10x plus rapide** qu'un HDD.\n\n" +
                     "Le SSD est-il branché ?"
    },
    "dual_boot": {
        "trigger": ["dual boot", "double boot", "deux os", "windows + linux", "two os"],
        "answer_en": "I can set up a clean dual boot (Windows + Linux).\n\n" +
                     "**Steps:**\n" +
                     "1. **Back up** Windows (just in case)\n" +
                     "2. **Shrink the Windows partition**\n" +
                     "3. **Install Linux** alongside it\n" +
                     "4. **Set up GRUB** (boot menu)\n\n" +
                     "At boot, you'll choose Windows or Linux.\n\n" +
                     "How much free space do you have on your disk?",
        "answer_fr": "Je peux installer un double boot (Windows + Linux) proprement.\n\n" +
                     "**Étapes :**\n" +
                     "1. **Sauvegarder** Windows (au cas où)\n" +
                     "2. **Réduire la partition Windows**\n" +
                     "3. **Installer Linux** à côté\n" +
                     "4. **Configurer GRUB** (menu au démarrage)\n\n" +
                     "Au boot, vous choisirez Windows ou Linux.\n\n" +
                     "Combien d'espace libre sur votre disque ?"
    },
    "bsod_error": {
        "trigger": ["bsod", "blue screen", "écran bleu", "stop error", "0x0000"],
        "answer_en": "A BSOD indicates a critical error. Common codes:\n\n" +
                     "• **CRITICAL_PROCESS_DIED** — driver or system file\n" +
                     "• **IRQL_NOT_LESS_OR_EQUAL** — driver conflict\n" +
                     "• **MEMORY_MANAGEMENT** — faulty RAM\n" +
                     "• **PAGE_FAULT_IN_NONPAGED** — disk or RAM\n\n" +
                     "Can you give me **the error code** (e.g. 0x0000007E)?",
        "answer_fr": "Un BSOD indique une erreur critique. Codes fréquents :\n\n" +
                     "• **CRITICAL_PROCESS_DIED** — pilote ou fichier système\n" +
                     "• **IRQL_NOT_LESS_OR_EQUAL** — conflit pilote\n" +
                     "• **MEMORY_MANAGEMENT** — RAM défectueuse\n" +
                     "• **PAGE_FAULT_IN_NONPAGED** — disque ou RAM\n\n" +
                     "Pouvez-vous me donner **le code d'erreur** (ex: 0x0000007E) ?"
    },
    "boot_from_usb": {
        "trigger": ["booter sur usb", "démarrer usb", "bios boot", "choisir usb", "boot from usb"],
        "answer_en": "To boot from the USB drive:\n\n" +
                     "1. **Plug in** the AI Rescue USB drive\n" +
                     "2. **Restart** the PC\n" +
                     "3. **Press F12/F2/Del/Esc** during startup\n" +
                     "   (depends on the brand)\n" +
                     "4. Choose **\"USB\"** or **\"UEFI: xxx\"** in the menu\n\n" +
                     "**Common brands:**\n" +
                     "• Dell: F12\n" +
                     "• HP: F9 or F10\n" +
                     "• Lenovo: F12 or Novo Button\n" +
                     "• Asus: F8 or Esc\n" +
                     "• Acer: F12\n\n" +
                     "What brand is your PC?",
        "answer_fr": "Pour démarrer sur la clé USB :\n\n" +
                     "1. **Brancher la clé** AI Rescue USB\n" +
                     "2. **Redémarrer** le PC\n" +
                     "3. **Appuyer sur F12/F2/Del/Echap** pendant le démarrage\n" +
                     "   (dépend de la marque)\n" +
                     "4. Choisir **\"USB\"** ou **\"UEFI: xxx\"** dans le menu\n\n" +
                     "**Marques courantes :**\n" +
                     "• Dell : F12\n" +
                     "• HP : F9 ou F10\n" +
                     "• Lenovo : F12 ou Novo Button\n" +
                     "• Asus : F8 ou Echap\n" +
                     "• Acer : F12\n\n" +
                     "Quelle est la marque de votre PC ?"
    },
    "antivirus_scan": {
        "trigger": ["scan virus", "nettoyer", "infecté", "antivirus", "clean virus", "scan for virus"],
        "answer_en": "I can scan your system to detect and remove threats.\n\n" +
                     "**Scan process:**\n" +
                     "1. **Quick scan** of critical areas (2-5 minutes)\n" +
                     "2. **Identify** threats\n" +
                     "3. **Automatic cleanup** (quarantine)\n" +
                     "4. **Detailed report**\n\n" +
                     "Say **\"antivirus scan\"** to start a full scan.\n\n" +
                     "**Important**: if you suspect ransomware, disconnect from the Internet immediately!\n\n" +
                     "Want to start a scan now?",
        "answer_fr": "Je peux scanner votre système pour détecter et éliminer les menaces.\n\n" +
                     "**Processus de scan :**\n" +
                     "1. **Scan rapide** des zones critiques (2-5 minutes)\n" +
                     "2. **Identification** des menaces\n" +
                     "3. **Nettoyage automatique** (mise en quarantaine)\n" +
                     "4. **Rapport détaillé**\n\n" +
                     "Dites **\"scan antivirus\"** pour lancer un scan complet.\n\n" +
                     "**Conseil important** : Si vous suspectez un ransomware, déconnectez-vous d'Internet immédiatement !\n\n" +
                     "Voulez-vous lancer un scan maintenant ?"
    },
    "network_config": {
        "trigger": ["internet", "connexion", "connection"],
        "answer_en": "I can help with your network connection.\n\n" +
                     "**What I can do:**\n" +
                     "• Automatically **detect** available WiFi\n" +
                     "• **Secure connection** with a password\n" +
                     "• **Diagnose** the connection\n" +
                     "• **Configure** network settings\n\n" +
                     "Say **\"connect to wifi\"** to scan for available networks.\n\n" +
                     "Or **\"test internet\"** to check your current connection.\n\n" +
                     "What's your network issue?",
        "answer_fr": "Je peux vous aider avec votre connexion réseau.\n\n" +
                     "**Ce que je peux faire :**\n" +
                     "• **Détecter** automatiquement le WiFi disponible\n" +
                     "• **Connexion sécurisée** avec mot de passe\n" +
                     "• **Diagnostic** de la connexion\n" +
                     "• **Configuration** des paramètres réseau\n\n" +
                     "Dites **\"connecter au wifi\"** pour scanner les réseaux disponibles.\n\n" +
                     "Ou **\"tester internet\"** pour vérifier votre connexion actuelle.\n\n" +
                     "Quel est votre problème réseau ?"
    },
    "format_disk": {
        "trigger": ["formater", "effacer tout", "remise à zéro", "wipe", "format disk", "erase everything"],
        "answer_en": "**WARNING**: Formatting permanently erases EVERYTHING.\n\n" +
                     "Before formatting, I can:\n" +
                     "1. **Back up** your important files\n" +
                     "2. **Create a full disk image**\n" +
                     "3. **Reinstall** the OS from scratch\n\n" +
                     "Are you **100% sure** you want to continue?\n" +
                     "This is irreversible.",
        "answer_fr": "**ATTENTION** : Formater efface TOUT définitivement.\n\n" +
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

    def __init__(self, llm=None):
        self.knowledge = KNOWLEDGE
        self.hw_detector = None
        self.os_detector = None
        self.llm = llm
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

    def answer(self, user_input: str, lang: str = "en") -> str:
        """
        Répond à n'importe quelle question utilisateur.
        Cherche dans la base de connaissances, sinon fait une réponse générique utile.

        `lang` ("en" par défaut, ou "fr") couvre toute cette méthode, y compris
        la base de connaissances. Les flux guidés (install/repair/backup/...)
        restent en français pour l'instant — les traduire est un chantier séparé.
        """
        low = user_input.lower()
        lang = lang if lang in ("en", "fr") else "en"

        # 1. Chercher dans la base de connaissances
        for key, data in self.knowledge.items():
            for trigger in data["trigger"]:
                if trigger in low:
                    return data["answer_fr"] if lang == "fr" else data["answer_en"]

        # 2. Salutations
        if any(w in low for w in ["bonjour", "hello", "hi", "hey", "salut"]):
            return self._greeting(lang)

        # 3. Remerciements
        if any(w in low for w in ["merci", "thanks", "thx"]):
            return ("You're welcome! Let me know if you have other questions."
                    if lang == "en" else
                    "Avec plaisir ! N'hésitez pas si vous avez d'autres questions.")

        # 4. Capacités
        if any(w in low for w in ["what can you", "your capabilities", "help",
                                   "que peux-tu", "que sais tu", "tes capacités", "aide"]):
            return self._capabilities(lang)

        # 5. Matériel
        if any(w in low for w in ["what cpu", "what ram", "how much ram", "my computer", "my pc",
                                   "quel processeur", "quelle ram", "combien ram", "mon pc"]):
            return self._describe_hardware(lang)

        # 6. Systèmes détectés
        if any(w in low for w in ["what os", "which os", "installed system", "windows or linux",
                                   "quel os", "système installé", "windows ou linux"]):
            return self._describe_os(lang)

        # 7. LLM local si disponible, sinon réponse générique statique
        if self.llm and getattr(self.llm, "loaded", False):
            llm_answer = self._llm_answer(user_input, lang)
            if llm_answer:
                return llm_answer

        return self._generic_help(user_input, lang)

    def _llm_answer(self, user_input: str, lang: str = "en") -> Optional[str]:
        """Demande au LLM local de répondre, avec le contexte de ce que l'outil sait faire."""
        if lang == "fr":
            system = (
                "Tu es AI Rescue, un assistant IA embarqué sur une clé USB de dépannage "
                "informatique. Tu aides à réparer Windows/Linux/BSD, installer un OS, "
                "sauvegarder des fichiers, récupérer des fichiers supprimés et diagnostiquer "
                "un ordinateur. Réponds en français, en 2-3 phrases maximum, de façon simple "
                "et concrète. Si la demande correspond à une de ces actions, dis à "
                "l'utilisateur quoi taper pour la démarrer (ex: \"répare mon PC\", "
                "\"installe Ubuntu\")."
            )
        else:
            system = (
                "You are AI Rescue, an AI assistant embedded on a computer-repair USB "
                "drive. You help repair Windows/Linux/BSD, install an OS, back up files, "
                "recover deleted files, and diagnose a computer. Reply in English, in 2-3 "
                "sentences maximum, simply and concretely. If the request matches one of "
                "these actions, tell the user what to type to start it (e.g. \"repair my "
                "PC\", \"install Ubuntu\")."
            )
        try:
            return self.llm.generate(user_input, max_tokens=200, system=system)
        except Exception as e:
            log.warning(f"LLM answer failed, falling back to static help: {e}")
            return None

    def _greeting(self, lang: str = "en") -> str:
        """Salutation."""
        if lang == "fr":
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
        return (
            "👋 **Hello! I'm AI Rescue.**\n\n"
            "I'm your personal computer technician. "
            "I can help you:\n\n"
            "• **Repair** your computer (Windows/Linux/Mac)\n"
            "• **Install** a new operating system\n"
            "• **Back up** your important files\n"
            "• **Recover** deleted files\n"
            "• **Diagnose** a hardware problem\n\n"
            "Just tell me what's wrong, I'll take care of the rest!"
        )

    def _capabilities(self, lang: str = "en") -> str:
        """Liste des capacités."""
        if lang == "fr":
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
        return (
            "**Here's what I can do:**\n\n"
            "🛠️ **Repair**\n"
            "• Windows that won't boot\n"
            "• Broken GRUB (Linux)\n"
            "• Corrupted system files\n"
            "• EFI/MBR bootloader\n\n"
            "💿 **Install**\n"
            "• Windows 10, 11\n"
            "• Ubuntu, Debian, Fedora, Arch, Mint\n"
            "• FreeBSD, OpenBSD\n\n"
            "💾 **Backup**\n"
            "• Full disk clone\n"
            "• File backup\n"
            "• System image\n\n"
            "🔍 **Recovery**\n"
            "• Deleted files\n"
            "• Damaged disk\n"
            "• Lost partitions\n\n"
            "🩺 **Diagnose**\n"
            "• Disk health (SMART)\n"
            "• RAM test\n"
            "• Performance analysis\n\n"
            "**What would you like to do?**"
        )

    def _describe_hardware(self, lang: str = "en") -> str:
        """Décrit le matériel détecté."""
        if not self.hw_detector:
            return ("I can't analyze the hardware right now. Try again later."
                    if lang == "en" else
                    "Je ne peux pas analyser le matériel pour le moment. Réessayez plus tard.")

        try:
            hw = self.hw_detector.detect_all()

            if lang == "fr":
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

            msg = "**Your hardware:**\n\n"
            msg += f"• **CPU:** {hw.cpu.model}\n"
            msg += f"  ({hw.cpu.cores} cores, {hw.cpu.threads} threads)\n\n"
            msg += f"• **RAM:** {hw.ram.total_mb}MB ({hw.ram.type})\n"
            if hw.ram.speed_mhz:
                msg += f"  Speed: {hw.ram.speed_mhz} MHz\n"
            msg += "\n"
            if hw.gpus:
                msg += "**GPUs:**\n"
                for g in hw.gpus[:2]:
                    msg += f"  • {g.model} ({g.driver})\n"
                msg += "\n"
            if hw.disks:
                msg += "**Disks:**\n"
                for d in hw.disks[:4]:
                    msg += f"  • {d.device}: {d.model} ({d.size_gb:.0f}GB {d.type.upper()})\n"
                msg += "\n"
            msg += f"**BIOS:** {hw.bios_type.upper()}\n"
            msg += f"**Secure Boot:** {'Yes' if hw.secure_boot else 'No'}\n"
            return msg
        except Exception as e:
            return f"Error during analysis: {e}" if lang == "en" else f"Erreur lors de l'analyse : {e}"

    def _describe_os(self, lang: str = "en") -> str:
        """Décrit les OS détectés."""
        if not self.os_detector:
            return ("I can't analyze the systems right now."
                    if lang == "en" else
                    "Je ne peux pas analyser les systèmes pour le moment.")

        try:
            os_info = self.os_detector.detect_all()

            if not os_info.detected_os:
                if lang == "fr":
                    return ("**Aucun système détecté** sur les disques.\n\n"
                            "Les disques sont peut-être vides ou chiffrés. "
                            "Voulez-vous installer un OS ?")
                return ("**No system detected** on the disks.\n\n"
                        "The disks may be empty or encrypted. "
                        "Would you like to install an OS?")

            if lang == "fr":
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

            msg = "**Detected systems:**\n\n"
            for o in os_info.detected_os:
                status = "✅" if o.boot_status == "ok" else "⚠️"
                msg += f"• {status} **{o.name} {o.version}**\n"
                msg += f"  Partition: {o.partition}\n"
                msg += f"  Boot: {o.boot_status}\n"
                if o.users:
                    msg += f"  Users: {', '.join(o.users[:3])}\n"
                msg += "\n"
            msg += f"**Boot mode:** {os_info.boot_mode.upper()}\n"
            msg += f"**Partition:** {os_info.disk_layout.upper()}\n"
            return msg
        except Exception as e:
            return f"Error: {e}" if lang == "en" else f"Erreur : {e}"

    def _generic_help(self, user_input: str, lang: str = "en") -> str:
        """Réponse générique quand rien ne match."""
        if lang == "fr":
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
        return (
            f"I understand you're saying: **\"{user_input}\"**\n\n"
            "To help you better, here's what I can do:\n\n"
            "🔧 **Repair** — \"My PC won't boot\"\n"
            "💿 **Install** — \"Install Windows 11\"\n"
            "💾 **Backup** — \"Back up my files\"\n"
            "🔍 **Recover** — \"I lost my photos\"\n"
            "🩺 **Diagnose** — \"Why is it slow?\"\n\n"
            "Or click one of the cards above 👆"
        )
