"""
AI Rescue USB - Web API Server
===============================
Serveur HTTP qui expose l'API REST et sert l'interface web.
Tourne sur le port 8080.
"""

import asyncio
import itertools
import json
import logging
import os
import sys
import threading
from collections import deque
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Configuré ici (pas dans `if __name__ == "__main__"`) car ce module attache
# LogBuffer au root logger juste en dessous — basicConfig() ne fait rien si
# le root a déjà un handler, donc on doit garantir la sortie console d'abord.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

log = logging.getLogger("ui-server")


class LogBuffer(logging.Handler):
    """Capture tous les logs (détection, réparation, conversation, sécurité...)
    dans un buffer en mémoire que l'interface peut consulter en direct.

    C'est ce qui alimente le panneau "détails techniques" du chat : le client
    voit les vraies commandes/actions exécutées en arrière-plan, pas juste la
    réponse résumée de l'IA.
    """

    def __init__(self, maxlen: int = 500):
        super().__init__()
        self._entries = deque(maxlen=maxlen)
        self._counter = itertools.count(1)
        self._lock = threading.Lock()
        self.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                                             datefmt="%H:%M:%S"))

    def emit(self, record):
        try:
            line = self.format(record)
        except Exception:
            return
        with self._lock:
            self._entries.append((next(self._counter), line))

    def since(self, last_id: int):
        with self._lock:
            entries = [(i, line) for i, line in self._entries if i > last_id]
        return entries


log_buffer = LogBuffer()
logging.getLogger().addHandler(log_buffer)
logging.getLogger().setLevel(logging.INFO)

# Imports résilients — le serveur démarre même sans les déps Linux
try:
    from ai_core.conversation import ConversationManager, InstallFlow, RepairFlow
except Exception as e:
    log.warning(f"ConversationManager non disponible: {e}")
    ConversationManager = None
    InstallFlow = None
    RepairFlow = None

try:
    from detection.hardware.detector import HardwareDetector
except Exception as e:
    log.warning(f"HardwareDetector non disponible: {e}")
    HardwareDetector = None

try:
    from detection.os.detector import OSDetector
except Exception as e:
    log.warning(f"OSDetector non disponible: {e}")
    OSDetector = None

try:
    from agents.repair.repair_agent import RepairAgent
except Exception as e:
    log.warning(f"RepairAgent non disponible: {e}")
    RepairAgent = None


class RescueAPIHandler(SimpleHTTPRequestHandler):
    """
    Handler HTTP qui sert:
    - GET / → index.html
    - GET /api/status → état du système
    - GET /api/hardware → détection matériel
    - GET /api/os → détection OS
    - POST /api/process → traitement principal
    - Les fichiers statiques
    """

    # Initialisation unique des composants lourds
    _conversation = None
    _hw_detector = None
    _os_detector = None
    _repair_agent = None
    _hw_cache = None
    _os_cache = None

    @classmethod
    def init_components(cls):
        """Initialise tous les composants une seule fois."""
        if cls._conversation is None and ConversationManager is not None:
            try:
                cls._conversation = ConversationManager()
                # Enregistrer les flux
                if InstallFlow is not None:
                    cls._conversation.register_flow("install", InstallFlow)
                if RepairFlow is not None:
                    cls._conversation.register_flow("repair", RepairFlow)
                log.info("ConversationManager initialized")
            except Exception as e:
                log.warning(f"ConversationManager init failed: {e}")
        if cls._hw_detector is None and HardwareDetector is not None:
            try:
                cls._hw_detector = HardwareDetector()
            except Exception as e:
                log.warning(f"HardwareDetector init failed: {e}")
        if cls._os_detector is None and OSDetector is not None:
            try:
                cls._os_detector = OSDetector()
            except Exception as e:
                log.warning(f"OSDetector init failed: {e}")
        if cls._repair_agent is None and RepairAgent is not None:
            try:
                cls._repair_agent = RepairAgent()
            except Exception as e:
                log.warning(f"RepairAgent init failed: {e}")

    def do_GET(self):
        """Route les requêtes GET."""
        parsed = urlparse(self.path)
        path = parsed.path

        # API routes
        if path == "/api/status":
            self._handle_status()
        elif path == "/api/hardware":
            self._handle_hardware()
        elif path == "/api/os":
            self._handle_os()
        elif path == "/api/logs":
            self._handle_logs(parse_qs(parsed.query))
        elif path == "/" or path == "":
            self._serve_static("/index.html")
        else:
            self._serve_static(path)

    def do_POST(self):
        """Route les requêtes POST."""
        parsed = urlparse(self.path)

        if parsed.path == "/api/process":
            self._handle_process()
        elif parsed.path == "/api/chat":
            self._handle_chat()
        elif parsed.path == "/api/repair":
            self._handle_repair()
        elif parsed.path == "/api/install":
            self._handle_install()
        elif parsed.path == "/api/backup":
            self._handle_backup()
        elif parsed.path == "/api/diagnose-image":
            self._handle_diagnose_image()
        else:
            self.send_error(404, "Not Found")

    def do_OPTIONS(self):
        """CORS preflight."""
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json_response(self, data, status=200):
        """Envoie une réponse JSON."""
        self.send_response(status)
        self._cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

    def _read_body(self) -> dict:
        """Lit le body JSON de la requête."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            return json.loads(body)
        except (json.JSONDecodeError, ValueError):
            return {}

    def _serve_static(self, path: str):
        """Sert un fichier statique depuis ui/static/."""
        static_dir = Path(__file__).parent / "static"

        # Sécurité: empêcher path traversal
        safe_path = Path(path).name if "/" in path else path.lstrip("/")
        file_path = (static_dir / safe_path).resolve()

        if not str(file_path).startswith(str(static_dir.resolve())):
            self.send_error(403, "Forbidden")
            return

        if not file_path.exists() or not file_path.is_file():
            # Fallback to index.html for SPA routing
            file_path = static_dir / "index.html"
            if not file_path.exists():
                self.send_error(404, "Not Found")
                return

        content_type = self._guess_mime(file_path)
        try:
            with open(file_path, "rb") as f:
                content = f.read()

            self.send_response(200)
            self._cors_headers()
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            log.error(f"Error serving {file_path}: {e}")
            self.send_error(500, "Internal Server Error")

    def _guess_mime(self, path: Path) -> str:
        """Devine le type MIME."""
        ext = path.suffix.lower()
        return {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
            ".woff2": "font/woff2",
        }.get(ext, "application/octet-stream")

    # ============================================
    # API Handlers
    # ============================================

    def _handle_logs(self, query: dict):
        """GET /api/logs?since=N - Journal technique en direct (polling).

        Le client renvoie le dernier id qu'il a reçu ; on ne renvoie que les
        lignes plus récentes, pour éviter de retransmettre tout l'historique
        à chaque poll.
        """
        try:
            since = int(query.get("since", ["0"])[0])
        except (ValueError, IndexError):
            since = 0

        entries = log_buffer.since(since)
        self._json_response({
            "entries": [{"id": i, "line": line} for i, line in entries],
            "last_id": entries[-1][0] if entries else since,
        })

    def _handle_status(self):
        """GET /api/status - État rapide du système."""
        try:
            # Cache léger
            if self._hw_cache is None:
                self._hw_cache = self._hw_detector.detect_all()

            self._json_response({
                "status": "ready",
                "version": "0.1.0",
                "cpu": self._hw_cache.cpu.model[:40],
                "ram": f"{self._hw_cache.ram.total_mb}MB",
                "disks": len(self._hw_cache.disks),
                "bios": self._hw_cache.bios_type,
                "uptime": "running",
            })
        except Exception as e:
            self._json_response({
                "status": "initializing",
                "error": str(e),
            }, status=503)

    def _handle_hardware(self):
        """GET /api/hardware - Détection matériel complète."""
        try:
            hw = self._hw_detector.detect_all()
            self._hw_cache = hw

            import dataclasses
            class HwEncoder(json.JSONEncoder):
                def default(self, obj):
                    if dataclasses.is_dataclass(obj):
                        return dataclasses.asdict(obj)
                    return super().default(obj)

            self._json_response({
                "status": "ok",
                "hardware": json.loads(json.dumps(hw, cls=HwEncoder)),
            })
        except Exception as e:
            self._json_response({"status": "error", "error": str(e)}, status=500)

    def _handle_os(self):
        """GET /api/os - Détection OS."""
        try:
            os_info = self._os_detector.detect_all()
            self._os_cache = os_info

            self._json_response({
                "status": "ok",
                "boot_mode": os_info.boot_mode,
                "detected": [
                    {"name": o.name, "type": o.type, "version": o.version,
                     "partition": o.partition, "boot_status": o.boot_status}
                    for o in os_info.detected_os
                ],
                "partitions": [
                    {"device": p.device, "size": p.size, "fs": p.filesystem}
                    for p in os_info.partitions
                ],
            })
        except Exception as e:
            self._json_response({"status": "error", "error": str(e)}, status=500)

    def _handle_process(self):
        """POST /api/process - Traitement principal via système conversationnel."""
        try:
            body = self._read_body()
            message = body.get("message", "")
            lang = body.get("lang", "en")

            log.info(f"Processing chat message: {message[:100]}")

            if not self._conversation:
                self._json_response({
                    "status": "error",
                    "response": "Conversation system unavailable.",
                })
                return

            # Exécuter de manière synchrone (HTTP handler)
            loop = asyncio.new_event_loop()
            try:
                response = loop.run_until_complete(
                    self._conversation.process_user_input(message, lang=lang)
                )
            finally:
                loop.close()

            self._json_response({
                "status": "ok",
                "response": response,
                "has_context": bool(self._conversation.context.current_flow),
            })

        except Exception as e:
            log.error(f"Process error: {e}")
            self._json_response({
                "status": "error",
                "response": f"Erreur : {str(e)}",
            }, status=500)

    def _handle_chat(self):
        """POST /api/chat - Alias conversationnel (même logique que /api/process)."""
        self._handle_process()

    def _handle_diagnose_image(self):
        """POST /api/diagnose-image - Diagnostic à partir d'une capture d'écran.

        L'utilisateur envoie une photo/capture de son écran d'erreur (BSOD,
        boîte de dialogue...) au lieu de devoir taper le code d'erreur à la
        main. OCR pour extraire le texte, puis même chemin de diagnostic
        qu'un symptôme tapé au clavier. Read-only — ne répare rien.
        """
        try:
            from ai_core.screenshot_diagnosis import extract_text_from_image

            body = self._read_body()
            image_data = body.get("image", "")
            lang = body.get("lang", "en")

            if not image_data:
                self._json_response({"status": "error", "error": "No image provided"}, status=400)
                return

            extracted_text = extract_text_from_image(image_data)
            if extracted_text is None:
                self._json_response({
                    "status": "unavailable",
                    "message": (
                        "Screenshot diagnosis isn't available on this system "
                        "(OCR engine not installed). Please describe the error in the chat instead."
                        if lang != "fr" else
                        "Le diagnostic par capture d'écran n'est pas disponible sur ce système "
                        "(moteur OCR non installé). Décrivez l'erreur dans le chat à la place."
                    ),
                })
                return

            os_type = "windows"
            if self._os_detector:
                try:
                    detected = self._os_detector.detect_all().detected_os
                    if detected:
                        os_type = detected[0].type
                except Exception:
                    pass

            actions = self._repair_agent.diagnose(os_type, [extracted_text]) if self._repair_agent else []

            self._json_response({
                "status": "ok",
                "extracted_text": extracted_text,
                "os_type": os_type,
                "suggested_fixes": [
                    {"name": a.name, "description": a.description, "risk": a.risk.value}
                    for a in actions
                ],
            })
        except Exception as e:
            self._json_response({"status": "error", "error": str(e)}, status=500)

    def _handle_repair(self):
        """POST /api/repair - Réparation.

        Sans `confirmed: true` dans le corps, seules les actions SAFE/LOW
        s'exécutent réellement ; les actions MEDIUM+ sont renvoyées comme
        nécessitant confirmation, pas exécutées. Le client doit renvoyer
        la requête avec `confirmed: true` après avoir montré ces actions
        à l'utilisateur et obtenu son accord explicite.
        """
        try:
            body = self._read_body()
            os_type = body.get("os_type", "windows")
            symptoms = body.get("symptoms", ["boot problem"])
            confirmed = body.get("confirmed", False) is True

            results = self._repair_agent.auto_repair(
                os_type, symptoms, dry_run=False, confirm=not confirmed
            )

            self._json_response({
                "status": "ok",
                "summary": self._repair_agent.summary(),
                "actions": [
                    {"name": r.action, "status": "success" if r.success else "failed",
                     "time": r.time_taken, "error": r.error or None}
                    for r in results
                ],
            })
        except Exception as e:
            self._json_response({"status": "error", "error": str(e)}, status=500)

    def _handle_install(self):
        """POST /api/install - Analyse compatibilité installation."""
        try:
            body = self._read_body()
            target_os = body.get("os", "")

            if not self._hw_cache:
                self._hw_cache = self._hw_detector.detect_all()

            hw = self._hw_cache

            # Vérifier compatibilité basique
            compatible = []
            if hw.ram.total_mb >= 4096:
                compatible.append({"name": "Windows 11", "type": "windows"})
                compatible.append({"name": "Ubuntu 24.04", "type": "linux"})
                compatible.append({"name": "Fedora 40", "type": "linux"})
            if hw.ram.total_mb >= 2048:
                compatible.append({"name": "Windows 10", "type": "windows"})
                compatible.append({"name": "Debian 12", "type": "linux"})
                compatible.append({"name": "Linux Mint 21", "type": "linux"})
            if hw.ram.total_mb >= 1024:
                compatible.append({"name": "FreeBSD 14", "type": "bsd"})
                compatible.append({"name": "Arch Linux", "type": "linux"})

            self._json_response({
                "status": "ok",
                "compatible_os": compatible,
                "hardware": {
                    "cpu": hw.cpu.model,
                    "ram": f"{hw.ram.total_mb}MB",
                    "disks": len(hw.disks),
                },
                "disclaimer": "L'installation effacera les données du disque cible.",
            })
        except Exception as e:
            self._json_response({"status": "error", "error": str(e)}, status=500)

    def _handle_backup(self):
        """POST /api/backup - Analyse pour sauvegarde."""
        try:
            if not self._hw_cache:
                self._hw_cache = self._hw_detector.detect_all()

            self._json_response({
                "status": "ok",
                "message": "Prêt pour sauvegarde. Branchez un disque externe.",
                "disks_available": [
                    {"device": d.device, "size": f"{d.size_gb:.0f}GB", "model": d.model}
                    for d in self._hw_cache.disks
                ],
            })
        except Exception as e:
            self._json_response({"status": "error", "error": str(e)}, status=500)


def run_server(host=None, port=8080):
    """Démarre le serveur HTTP.

    Écoute sur localhost par défaut : ce serveur exécute des commandes
    système (réparation, etc.) sans authentification, donc l'exposer sur
    le réseau expose ces actions à quiconque sur le même réseau. Pour
    l'assistance à distance (cas d'usage légitime), définir explicitement
    AI_RESCUE_HOST=0.0.0.0.
    """
    if host is None:
        host = os.environ.get("AI_RESCUE_HOST", "127.0.0.1")
    # Initialiser les composants
    RescueAPIHandler.init_components()

    server = HTTPServer((host, port), RescueAPIHandler)
    log.info(f"AI Rescue API server running on http://{host}:{port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Server stopped")
        server.shutdown()


if __name__ == "__main__":
    run_server()
