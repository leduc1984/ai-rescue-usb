@echo off
chcp 65001 >nul
title AI Rescue USB - Demo Launcher

echo.
echo     ╔══════════════════════════════════════════╗
echo     ║             🤖 AI RESCUE USB             ║
echo     ║      Assistant IA pour réparation        ║
echo     ║        informatique — Prototype          ║
echo     ╚══════════════════════════════════════════╝
echo.
echo     Ce lanceur démarre l'interface AI Rescue sur Windows.
echo     L'IA va détecter ton matériel et tu pourras lui parler.
echo.
echo     [!] Mode démo — l'ISO Linux complète nécessite un build Docker.
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo     [ERREUR] Python n'est pas installé.
    echo     Télécharge Python sur https://python.org
    pause
    exit /b 1
)

:: Install deps if needed
echo     [1/3] Vérification des dépendances...
pip install -r requirements.txt --quiet 2>nul
if %errorlevel% neq 0 (
    echo     [!] Certaines dépendances n'ont pas pu être installées (llama-cpp nécessite un compilateur C).
    echo     Le mode démo fonctionnera quand même avec le fallback intégré.
)

:: Start web server
echo     [2/3] Démarrage du serveur web...
start "AI Rescue Server" python ui/server.py

:: Wait a bit for server
timeout /t 3 /nobreak >nul

:: Open browser
echo     [3/3] Ouverture de l'interface...
start http://localhost:8080

echo.
echo     ✅ AI Rescue USB est démarré !
echo.
echo     🌐 Interface : http://localhost:8080
echo     💬 Parle à l'IA ou clique sur les cartes
echo.
echo     Appuie sur une touche pour arrêter le serveur...
pause >nul

:: Cleanup
taskkill /FI "WINDOWTITLE eq AI Rescue Server" /F 2>nul
echo     Serveur arrêté. À bientôt ! 👋
pause
