"""
AI Rescue USB - Internationalization (i18n)
============================================
Système multilingue complet.
Supporte : FR, EN, ES, DE, IT, PT, NL, JA, ZH
"""

import json
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("i18n")


# ============================================================
# Traductions - toutes les chaînes du système
# ============================================================
TRANSLATIONS = {
    "en": {
        "app_name": "AI Rescue",
        "greeting": "Hello.",
        "what_to_do": "What would you like to do?",
        "menu_repair": "🛠 Repair my computer",
        "menu_install": "💿 Install a system",
        "menu_backup": "📁 Backup my files",
        "menu_restore": "🔄 Restore a backup",
        "menu_diagnose": "🔍 Diagnose my PC",
        "menu_talk": "🎤 Talk to me",
        "analyzing": "Analyzing your computer...",
        "analysis_complete": "Analysis complete.",
        "repair_complete": "Repair complete.",
        "reboot_ready": "You can now reboot.",
        "boot_problem_found": "I found a boot problem.",
        "can_repair": "I can repair this automatically.",
        "confirm_continue": "Continue? YES / NO",
        "operation_cancelled": "Operation cancelled.",
        "no_os_found": "No operating system found.",
        "warning_destructive": "⚠️ WARNING: This action will modify the disk.",
        "data_detected": "Data detected",
        "photos": "Photos",
        "documents": "Documents",
        "videos": "Videos",
        "backup_before": "Backup recommended before proceeding.",
        "backup_done": "Backup complete.",
        "download_starting": "Starting download...",
        "download_complete": "Download complete.",
        "verifying_integrity": "Verifying integrity...",
        "integrity_ok": "Integrity verified.",
        "installation_starting": "Starting installation...",
        "installation_complete": "Installation complete.",
        "hardware_detected": "Hardware detected",
        "os_detected": "Operating systems detected",
        "compatible_systems": "Compatible systems",
        "recovery_starting": "Starting recovery...",
        "files_recovered": "Files recovered",
        "unknown_error": "An error occurred.",
        "please_wait": "Please wait...",
        "enter_command": "Type your request:",
        "help_text": "Tell me what you need in plain language.",
    },
    "fr": {
        "app_name": "AI Rescue",
        "greeting": "Bonjour.",
        "what_to_do": "Que voulez-vous faire ?",
        "menu_repair": "🛠 Réparer mon ordinateur",
        "menu_install": "💿 Installer un système",
        "menu_backup": "📁 Sauvegarder mes fichiers",
        "menu_restore": "🔄 Restaurer une sauvegarde",
        "menu_diagnose": "🔍 Diagnostiquer mon PC",
        "menu_talk": "🎤 Parler",
        "analyzing": "Analyse de votre ordinateur...",
        "analysis_complete": "Analyse terminée.",
        "repair_complete": "Réparation terminée.",
        "reboot_ready": "Vous pouvez redémarrer.",
        "boot_problem_found": "J'ai trouvé un problème de démarrage.",
        "can_repair": "Je peux réparer automatiquement.",
        "confirm_continue": "Continuer ? OUI / NON",
        "operation_cancelled": "Opération annulée.",
        "no_os_found": "Aucun système d'exploitation trouvé.",
        "warning_destructive": "⚠️ ATTENTION : Cette action va modifier le disque.",
        "data_detected": "Données détectées",
        "photos": "Photos",
        "documents": "Documents",
        "videos": "Vidéos",
        "backup_before": "Sauvegarde recommandée avant de continuer.",
        "backup_done": "Sauvegarde terminée.",
        "download_starting": "Téléchargement en cours...",
        "download_complete": "Téléchargement terminé.",
        "verifying_integrity": "Vérification de l'intégrité...",
        "integrity_ok": "Intégrité vérifiée.",
        "installation_starting": "Démarrage de l'installation...",
        "installation_complete": "Installation terminée.",
        "hardware_detected": "Matériel détecté",
        "os_detected": "Systèmes d'exploitation détectés",
        "compatible_systems": "Systèmes compatibles",
        "recovery_starting": "Démarrage de la récupération...",
        "files_recovered": "Fichiers récupérés",
        "unknown_error": "Une erreur est survenue.",
        "please_wait": "Veuillez patienter...",
        "enter_command": "Tapez votre demande :",
        "help_text": "Dites-moi ce dont vous avez besoin en langage naturel.",
    },
    "es": {
        "app_name": "AI Rescue",
        "greeting": "Hola.",
        "what_to_do": "¿Qué desea hacer?",
        "menu_repair": "🛠 Reparar mi computadora",
        "menu_install": "💿 Instalar un sistema",
        "menu_backup": "📁 Respaldar mis archivos",
        "menu_restore": "🔄 Restaurar una copia",
        "menu_diagnose": "🔍 Diagnosticar mi PC",
        "menu_talk": "🎤 Hablar",
        "analyzing": "Analizando su computadora...",
        "analysis_complete": "Análisis completado.",
        "repair_complete": "Reparación completada.",
        "reboot_ready": "Puede reiniciar.",
        "boot_problem_found": "Encontré un problema de inicio.",
        "can_repair": "Puedo repararlo automáticamente.",
        "confirm_continue": "¿Continuar? SÍ / NO",
        "operation_cancelled": "Operación cancelada.",
        "no_os_found": "No se encontró sistema operativo.",
        "warning_destructive": "⚠️ ADVERTENCIA: Esta acción modificará el disco.",
        "data_detected": "Datos detectados",
        "photos": "Fotos",
        "documents": "Documentos",
        "videos": "Videos",
        "backup_before": "Se recomienda respaldo antes de continuar.",
        "backup_done": "Respaldo completado.",
        "download_starting": "Inicio de descarga...",
        "download_complete": "Descarga completada.",
        "verifying_integrity": "Verificando integridad...",
        "integrity_ok": "Integridad verificada.",
        "installation_starting": "Iniciando instalación...",
        "installation_complete": "Instalación completada.",
        "hardware_detected": "Hardware detectado",
        "os_detected": "Sistemas operativos detectados",
        "compatible_systems": "Sistemas compatibles",
        "recovery_starting": "Iniciando recuperación...",
        "files_recovered": "Archivos recuperados",
        "unknown_error": "Ocurrió un error.",
        "please_wait": "Por favor espere...",
        "enter_command": "Escriba su solicitud:",
        "help_text": "Dígame lo que necesita en lenguaje natural.",
    },
    "de": {
        "app_name": "AI Rescue",
        "greeting": "Hallo.",
        "what_to_do": "Was möchten Sie tun?",
        "menu_repair": "🛠 Computer reparieren",
        "menu_install": "💿 System installieren",
        "menu_backup": "📁 Dateien sichern",
        "menu_restore": "🔄 Backup wiederherstellen",
        "menu_diagnose": "🔍 PC diagnostizieren",
        "menu_talk": "🎤 Sprechen",
        "analyzing": "Computer wird analysiert...",
        "analysis_complete": "Analyse abgeschlossen.",
        "repair_complete": "Reparatur abgeschlossen.",
        "reboot_ready": "Sie können neu starten.",
        "boot_problem_found": "Ich habe ein Boot-Problem gefunden.",
        "can_repair": "Ich kann es automatisch reparieren.",
        "confirm_continue": "Fortfahren? JA / NEIN",
        "operation_cancelled": "Vorgang abgebrochen.",
        "no_os_found": "Kein Betriebssystem gefunden.",
        "warning_destructive": "⚠️ WARNUNG: Diese Aktion verändert die Festplatte.",
        "data_detected": "Daten erkannt",
        "photos": "Fotos",
        "documents": "Dokumente",
        "videos": "Videos",
        "backup_before": "Backup vor dem Fortfahren empfohlen.",
        "backup_done": "Backup abgeschlossen.",
        "download_starting": "Download wird gestartet...",
        "download_complete": "Download abgeschlossen.",
        "verifying_integrity": "Integrität wird überprüft...",
        "integrity_ok": "Integrität überprüft.",
        "installation_starting": "Installation wird gestartet...",
        "installation_complete": "Installation abgeschlossen.",
        "hardware_detected": "Hardware erkannt",
        "os_detected": "Erkannte Betriebssysteme",
        "compatible_systems": "Kompatible Systeme",
        "recovery_starting": "Wiederherstellung wird gestartet...",
        "files_recovered": "Dateien wiederhergestellt",
        "unknown_error": "Ein Fehler ist aufgetreten.",
        "please_wait": "Bitte warten...",
        "enter_command": "Geben Sie Ihre Anfrage ein:",
        "help_text": "Sagen Sie mir in natürlicher Sprache, was Sie brauchen.",
    },
    "it": {
        "app_name": "AI Rescue",
        "greeting": "Ciao.",
        "what_to_do": "Cosa vuoi fare?",
        "menu_repair": "🛠 Ripara il mio computer",
        "menu_install": "💿 Installa un sistema",
        "menu_backup": "📁 Backup dei miei file",
        "menu_restore": "🔄 Ripristina un backup",
        "menu_diagnose": "🔍 Diagnostica il mio PC",
        "menu_talk": "🎤 Parla",
        "analyzing": "Analisi del computer in corso...",
        "analysis_complete": "Analisi completata.",
        "repair_complete": "Riparazione completata.",
        "reboot_ready": "Puoi riavviare.",
        "boot_problem_found": "Ho trovato un problema di avvio.",
        "can_repair": "Posso ripararlo automaticamente.",
        "confirm_continue": "Continua? SÌ / NO",
        "operation_cancelled": "Operazione annullata.",
        "no_os_found": "Nessun sistema operativo trovato.",
        "warning_destructive": "⚠️ ATTENZIONE: Questa azione modificherà il disco.",
        "data_detected": "Dati rilevati",
        "photos": "Foto",
        "documents": "Documenti",
        "videos": "Video",
        "backup_before": "Backup consigliato prima di continuare.",
        "backup_done": "Backup completato.",
        "download_starting": "Download in corso...",
        "download_complete": "Download completato.",
        "verifying_integrity": "Verifica integrità...",
        "integrity_ok": "Integrità verificata.",
        "installation_starting": "Avvio installazione...",
        "installation_complete": "Installazione completata.",
        "hardware_detected": "Hardware rilevato",
        "os_detected": "Sistemi operativi rilevati",
        "compatible_systems": "Sistemi compatibili",
        "recovery_starting": "Avvio recupero...",
        "files_recovered": "File recuperati",
        "unknown_error": "Si è verificato un errore.",
        "please_wait": "Attendere prego...",
        "enter_command": "Scrivi la tua richiesta:",
        "help_text": "Dimmi cosa ti serve in linguaggio naturale.",
    },
    "pt": {
        "app_name": "AI Rescue",
        "greeting": "Olá.",
        "what_to_do": "O que deseja fazer?",
        "menu_repair": "🛠 Reparar meu computador",
        "menu_install": "💿 Instalar um sistema",
        "menu_backup": "📁 Fazer backup dos meus arquivos",
        "menu_restore": "🔄 Restaurar um backup",
        "menu_diagnose": "🔍 Diagnosticar meu PC",
        "menu_talk": "🎤 Falar",
        "analyzing": "Analisando seu computador...",
        "analysis_complete": "Análise concluída.",
        "repair_complete": "Reparo concluído.",
        "reboot_ready": "Você pode reiniciar.",
        "boot_problem_found": "Encontrei um problema de inicialização.",
        "can_repair": "Posso reparar automaticamente.",
        "confirm_continue": "Continuar? SIM / NÃO",
        "operation_cancelled": "Operação cancelada.",
        "no_os_found": "Nenhum sistema operacional encontrado.",
        "warning_destructive": "⚠️ AVISO: Esta ação modificará o disco.",
        "data_detected": "Dados detectados",
        "photos": "Fotos",
        "documents": "Documentos",
        "videos": "Vídeos",
        "backup_before": "Backup recomendado antes de continuar.",
        "backup_done": "Backup concluído.",
        "download_starting": "Iniciando download...",
        "download_complete": "Download concluído.",
        "verifying_integrity": "Verificando integridade...",
        "integrity_ok": "Integridade verificada.",
        "installation_starting": "Iniciando instalação...",
        "installation_complete": "Instalação concluída.",
        "hardware_detected": "Hardware detectado",
        "os_detected": "Sistemas operacionais detectados",
        "compatible_systems": "Sistemas compatíveis",
        "recovery_starting": "Iniciando recuperação...",
        "files_recovered": "Arquivos recuperados",
        "unknown_error": "Ocorreu um erro.",
        "please_wait": "Aguarde...",
        "enter_command": "Digite sua solicitação:",
        "help_text": "Diga-me o que precisa em linguagem natural.",
    },
    "ja": {
        "app_name": "AI Rescue",
        "greeting": "こんにちは。",
        "what_to_do": "何をしますか？",
        "menu_repair": "🛠 コンピュータを修理",
        "menu_install": "💿 システムをインストール",
        "menu_backup": "📁 ファイルをバックアップ",
        "menu_restore": "🔄 バックアップを復元",
        "menu_diagnose": "🔍 PCを診断",
        "menu_talk": "🎤 話す",
        "analyzing": "コンピュータを分析中...",
        "analysis_complete": "分析完了。",
        "repair_complete": "修理完了。",
        "reboot_ready": "再起動できます。",
        "boot_problem_found": "起動問題が見つかりました。",
        "can_repair": "自動的に修理できます。",
        "confirm_continue": "続けますか？ はい / いいえ",
        "operation_cancelled": "操作がキャンセルされました。",
        "no_os_found": "OSが見つかりません。",
        "warning_destructive": "⚠️ 警告：この操作はディスクを変更します。",
        "data_detected": "データ検出",
        "photos": "写真",
        "documents": "ドキュメント",
        "videos": "動画",
        "backup_before": "続行する前にバックアップを推奨します。",
        "backup_done": "バックアップ完了。",
        "download_starting": "ダウンロード開始...",
        "download_complete": "ダウンロード完了。",
        "verifying_integrity": "整合性確認中...",
        "integrity_ok": "整合性確認済み。",
        "installation_starting": "インストール開始...",
        "installation_complete": "インストール完了。",
        "hardware_detected": "ハードウェア検出",
        "os_detected": "OS検出",
        "compatible_systems": "互換性のあるシステム",
        "recovery_starting": "回復開始...",
        "files_recovered": "ファイル回復済み",
        "unknown_error": "エラーが発生しました。",
        "please_wait": "お待ちください...",
        "enter_command": "リクエストを入力：",
        "help_text": "自然な言葉で必要事項を教えてください。",
    },
    "zh": {
        "app_name": "AI Rescue",
        "greeting": "你好。",
        "what_to_do": "您想做什么？",
        "menu_repair": "🛠 修复我的电脑",
        "menu_install": "💿 安装系统",
        "menu_backup": "📁 备份我的文件",
        "menu_restore": "🔄 恢复备份",
        "menu_diagnose": "🔍 诊断我的电脑",
        "menu_talk": "🎤 对话",
        "analyzing": "正在分析您的电脑...",
        "analysis_complete": "分析完成。",
        "repair_complete": "修复完成。",
        "reboot_ready": "您可以重新启动了。",
        "boot_problem_found": "我发现了一个启动问题。",
        "can_repair": "我可以自动修复。",
        "confirm_continue": "继续吗？ 是 / 否",
        "operation_cancelled": "操作已取消。",
        "no_os_found": "未找到操作系统。",
        "warning_destructive": "⚠️ 警告：此操作将修改磁盘。",
        "data_detected": "检测到数据",
        "photos": "照片",
        "documents": "文档",
        "videos": "视频",
        "backup_before": "建议先备份。",
        "backup_done": "备份完成。",
        "download_starting": "开始下载...",
        "download_complete": "下载完成。",
        "verifying_integrity": "验证完整性...",
        "integrity_ok": "完整性已验证。",
        "installation_starting": "开始安装...",
        "installation_complete": "安装完成。",
        "hardware_detected": "检测到硬件",
        "os_detected": "检测到操作系统",
        "compatible_systems": "兼容系统",
        "recovery_starting": "开始恢复...",
        "files_recovered": "文件已恢复",
        "unknown_error": "发生错误。",
        "please_wait": "请稍候...",
        "enter_command": "请输入您的请求：",
        "help_text": "用自然语言告诉我您的需求。",
    },
    "nl": {
        "app_name": "AI Rescue",
        "greeting": "Hallo.",
        "what_to_do": "Wat wilt u doen?",
        "menu_repair": "🛠 Mijn computer repareren",
        "menu_install": "💿 Een systeem installeren",
        "menu_backup": "📁 Mijn bestanden back-uppen",
        "menu_restore": "🔄 Een back-up herstellen",
        "menu_diagnose": "🔍 Mijn PC diagnosticeren",
        "menu_talk": "🎤 Praten",
        "analyzing": "Uw computer wordt geanalyseerd...",
        "analysis_complete": "Analyse voltooid.",
        "repair_complete": "Reparatie voltooid.",
        "reboot_ready": "U kunt herstarten.",
        "boot_problem_found": "Ik heb een opstartprobleem gevonden.",
        "can_repair": "Ik kan het automatisch repareren.",
        "confirm_continue": "Doorgaan? JA / NEE",
        "operation_cancelled": "Bewerking geannuleerd.",
        "no_os_found": "Geen besturingssysteem gevonden.",
        "warning_destructive": "⚠️ WAARSCHUWING: Deze actie wijzigt de schijf.",
        "data_detected": "Gegevens gedetecteerd",
        "photos": "Foto's",
        "documents": "Documenten",
        "videos": "Video's",
        "backup_before": "Back-up aanbevolen voordat u doorgaat.",
        "backup_done": "Back-up voltooid.",
        "download_starting": "Download starten...",
        "download_complete": "Download voltooid.",
        "verifying_integrity": "Integriteit controleren...",
        "integrity_ok": "Integriteit geverifieerd.",
        "installation_starting": "Installatie starten...",
        "installation_complete": "Installatie voltooid.",
        "hardware_detected": "Hardware gedetecteerd",
        "os_detected": "Besturingssystemen gedetecteerd",
        "compatible_systems": "Compatibele systemen",
        "recovery_starting": "Herstel starten...",
        "files_recovered": "Bestanden hersteld",
        "unknown_error": "Er is een fout opgetreden.",
        "please_wait": "Even geduld...",
        "enter_command": "Typ uw verzoek:",
        "help_text": "Vertel me in gewone taal wat u nodig heeft.",
    },
}

# Langues supportées pour détection automatique
SUPPORTED_LANGUAGES = {
    "en": "English",
    "fr": "Français",
    "es": "Español",
    "de": "Deutsch",
    "it": "Italiano",
    "pt": "Português",
    "nl": "Nederlands",
    "ja": "日本語",
    "zh": "中文",
}


class LanguageManager:
    """
    Gestionnaire multilingue.
    Détecte la langue, charge les traductions, fournit les textes.
    """

    def __init__(self, default_lang: str = "auto"):
        self.default_lang = default_lang
        self.current_lang: str = "en"
        self.translations = TRANSLATIONS
        
        if default_lang != "auto":
            self.current_lang = default_lang
        else:
            self.current_lang = self._detect_language()
            
        log.info(f"Language set to: {self.current_lang} ({SUPPORTED_LANGUAGES.get(self.current_lang, 'unknown')})")

    def _detect_language(self) -> str:
        """
        Détecte la langue système automatiquement.
        """
        import os
        
        # Vérifier LANG/LC_ALL
        for env_var in ["LC_ALL", "LC_MESSAGES", "LANG"]:
            lang = os.environ.get(env_var, "")
            if lang:
                # Extraire fr_FR.UTF-8 -> fr
                lang_code = lang.split("_")[0].split(".")[0].lower()
                if lang_code in self.translations:
                    return lang_code

        # Vérifier la locale Windows (via kernel32)
        try:
            import ctypes
            if hasattr(ctypes, "windll"):
                locale_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
                lang_code = locale_id & 0xFF
                # Windows locale ID -> ISO
                lang_map = {
                    0x0C: "fr", 0x09: "en", 0x0A: "es",
                    0x07: "de", 0x10: "it", 0x16: "pt",
                    0x13: "nl", 0x11: "ja", 0x04: "zh",
                }
                code = lang_map.get(lang_code)
                if code and code in self.translations:
                    return code
        except Exception:
            pass

        return "en"

    def set_language(self, lang_code: str) -> bool:
        """
        Change la langue active.
        """
        if lang_code in self.translations:
            self.current_lang = lang_code
            log.info(f"Language changed to: {lang_code}")
            return True
        log.warning(f"Language not supported: {lang_code}")
        return False

    def get(self, key: str, **kwargs) -> str:
        """
        Récupère une traduction par clé.
        """
        # Chercher dans la langue courante
        text = self.translations.get(self.current_lang, {}).get(key)
        
        # Fallback sur anglais
        if text is None:
            text = self.translations.get("en", {}).get(key)
            
        # Fallback ultime
        if text is None:
            text = key
            
        # Interpolation
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, IndexError):
                pass
                
        return text

    def get_available_languages(self) -> dict:
        """
        Retourne les langues disponibles.
        """
        return SUPPORTED_LANGUAGES.copy()


# ============================================================
# Instance globale
# ============================================================
_i18n_instance: Optional[LanguageManager] = None


def get_i18n(lang: str = "auto") -> LanguageManager:
    """
    Récupère l'instance globale du gestionnaire de langues.
    """
    global _i18n_instance
    if _i18n_instance is None:
        _i18n_instance = LanguageManager(lang)
    return _i18n_instance


def t(key: str, **kwargs) -> str:
    """
    Shortcut: t("greeting") retourne la traduction.
    """
    return get_i18n().get(key, **kwargs)


# ============================================================
# Test
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    i18n = get_i18n("fr")
    
    print(f"Langue active: {i18n.current_lang}")
    print(f"Disponible: {i18n.get_available_languages()}")
    print()
    
    for key in ["greeting", "what_to_do", "menu_repair", "menu_install", "analyzing"]:
        print(f"  {key}: {i18n.get(key)}")
        
    i18n.set_language("en")
    print(f"\n--- English ---")
    for key in ["greeting", "what_to_do", "menu_repair"]:
        print(f"  {key}: {i18n.get(key)}")
        
    i18n.set_language("ja")
    print(f"\n--- 日本語 ---")
    for key in ["greeting", "what_to_do", "menu_repair"]:
        print(f"  {key}: {i18n.get(key)}")
