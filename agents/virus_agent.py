"""
AI Rescue USB - Virus Agent
===========================
Scan et nettoyage de malware/virus/ransomwares
Fonctionne offline avec ClamAV
"""

import logging
import subprocess
import os
from pathlib import Path
from typing import Optional

log = logging.getLogger("virus-agent")


class VirusAgent:
    """
    Agent de détection et nettoyage de virus
    Utilise ClamAV pour le scan offline
    """

    def __init__(self):
        self.clamscan_path = self._find_clamscan()
        self.freshclam_path = self._find_freshclam()
        self.quarantine_dir = Path("/opt/ai-rescue/quarantine")
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

    def _find_clamscan(self) -> Optional[str]:
        """Trouve le binaire clamscan"""
        for path in ["/usr/bin/clamscan", "/usr/local/bin/clamscan"]:
            if os.path.exists(path):
                return path
        # Essayer de trouver via which
        try:
            result = subprocess.run(["which", "clamscan"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def _find_freshclam(self) -> Optional[str]:
        """Trouve le binaire freshclam"""
        for path in ["/usr/bin/freshclam", "/usr/local/bin/freshclam"]:
            if os.path.exists(path):
                return path
        return None

    def is_available(self) -> bool:
        """Vérifie si ClamAV est installé"""
        return self.clamscan_path is not None

    def update_definitions(self) -> dict:
        """Met à jour les définitions de virus (nécessite Internet)"""
        if not self.freshclam_path:
            return {"success": False, "message": "freshclam non trouvé"}

        try:
            result = subprocess.run(
                [self.freshclam_path],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                return {"success": True, "message": "Définitions mises à jour"}
            else:
                return {"success": False, "message": result.stderr}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def scan_quick(self, paths: Optional[list] = None) -> dict:
        """
        Scan rapide des zones critiques
        """
        if paths is None:
            paths = ["/boot", "/etc", "/home", "/tmp", "/var/tmp"]

        return self._scan_paths(paths, recursive=False)

    def scan_full(self, paths: Optional[list] = None) -> dict:
        """
        Scan complet et récursif
        """
        if paths is None:
            paths = ["/"]

        return self._scan_paths(paths, recursive=True)

    def _scan_paths(self, paths: list, recursive: bool) -> dict:
        """Exécute un scan sur les chemins spécifiés"""
        if not self.is_available():
            return {
                "success": False,
                "error": "ClamAV non installé. Installez avec: apt install clamav clamav-daemon"
            }

        results = []
        total_threats = 0
        total_cleaned = 0

        for path in paths:
            if not os.path.exists(path):
                continue

            try:
                cmd = [self.clamscan_path]
                if recursive:
                    cmd.append("-r")
                cmd.extend(["--infected", "--remove=no", path])

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=3600  # 1 heure max
                )

                threats = self._parse_clamscan_output(result.stdout)
                total_threats += len(threats)

                results.append({
                    "path": path,
                    "threats": threats,
                    "threat_count": len(threats),
                    "scan_output": result.stdout[-500:]  # Garder les dernières lignes
                })

            except subprocess.TimeoutExpired:
                results.append({
                    "path": path,
                    "error": "Timeout - scan trop long",
                    "threats": []
                })
            except Exception as e:
                results.append({
                    "path": path,
                    "error": str(e),
                    "threats": []
                })

        return {
            "success": True,
            "scan_type": "full" if recursive else "quick",
            "paths_scanned": len(paths),
            "total_threats": total_threats,
            "threats_removed": total_cleaned,
            "details": results
        }

    def _parse_clamscan_output(self, output: str) -> list:
        """Parse la sortie de clamscan pour extraire les menaces"""
        threats = []
        for line in output.split("\n"):
            if "FOUND" in line and ":" in line:
                # Format: /path/to/file: Win.Trojan.Name FOUND
                parts = line.split(":")
                if len(parts) >= 2:
                    path = parts[0].strip()
                    threat_info = parts[1].strip()
                    threats.append({
                        "path": path,
                        "threat": threat_info,
                        "type": self._classify_threat(threat_info),
                        "risk": self._assess_risk(threat_info)
                    })
        return threats

    def _classify_threat(self, threat_info: str) -> str:
        """Classifie le type de menace"""
        threat_lower = threat_info.lower()

        if any(w in threat_lower for w in ["trojan", "backdoor"]):
            return "Trojan"
        elif any(w in threat_lower for w in ["virus", "worm"]):
            return "Virus"
        elif "ransom" in threat_lower:
            return "Ransomware"
        elif any(w in threat_lower for w in ["spyware", "keylogger"]):
            return "Spyware"
        elif any(w in threat_lower for w in ["adware", "popup"]):
            return "Adware"
        elif "phishing" in threat_lower:
            return "Phishing"
        elif "rootkit" in threat_lower:
            return "Rootkit"
        else:
            return "Malware"

    def _assess_risk(self, threat_info: str) -> str:
        """Évalue le niveau de risque"""
        threat_lower = threat_info.lower()

        if any(w in threat_lower for w in ["ransom", "rootkit", "backdoor"]):
            return "CRITICAL"
        elif any(w in threat_lower for w in ["trojan", "virus", "worm"]):
            return "HIGH"
        elif any(w in threat_lower for w in ["spyware", "keylogger"]):
            return "MEDIUM"
        elif any(w in threat_lower for w in ["adware", "popup"]):
            return "LOW"
        else:
            return "MEDIUM"

    def scan_and_clean(self, scan_type: str = "quick") -> dict:
        """
        Scan et nettoyage automatique
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "ClamAV non installé. Installez avec: apt install clamav clamav-daemon"
            }

        log.info(f"Démarrage scan {scan_type} avec nettoyage automatique")

        # Étape 1: Scan
        if scan_type == "quick":
            scan_result = self.scan_quick()
        else:
            scan_result = self.scan_full()

        if not scan_result["success"]:
            return scan_result

        # Étape 2: Nettoyage si menaces trouvées
        threats_found = scan_result["total_threats"]

        if threats_found == 0:
            return {
                **scan_result,
                "status": "clean",
                "message": "Aucune menace détectée. Votre système est propre. ✓"
            }

        # Tenter de nettoyer
        cleaned_count = 0
        failed_count = 0
        quarantine_list = []

        for result in scan_result["details"]:
            for threat in result.get("threats", []):
                path = threat["path"]
                if not os.path.exists(path):
                    continue

                try:
                    # Déplacer vers quarantaine
                    quarantine_file = self.quarantine_dir / f"{os.path.basename(path)}.{os.getpid()}"
                    os.rename(path, str(quarantine_file))
                    cleaned_count += 1
                    quarantine_list.append({
                        "original": path,
                        "quarantined": str(quarantine_file),
                        "threat": threat["threat"]
                    })
                    log.info(f"Menace mise en quarantaine: {path}")
                except Exception as e:
                    failed_count += 1
                    log.error(f"Échec nettoyage {path}: {e}")

        # Construire le rapport
        return {
            **scan_result,
            "scan_type": scan_type,
            "threats_found": threats_found,
            "threats_cleaned": cleaned_count,
            "threats_failed": failed_count,
            "quarantine_list": quarantine_list,
            "status": "cleaned" if failed_count == 0 else "partially_cleaned",
            "message": f"Scan {scan_type} terminé. {threats_found} menace(s) trouvée(s), {cleaned_count} nettoyée(s)."
        }

    def get_quarantine_list(self) -> list:
        """Liste les fichiers en quarantaine"""
        if not self.quarantine_dir.exists():
            return []

        quarantine_files = []
        for item in self.quarantine_dir.iterdir():
            if item.is_file():
                quarantine_files.append({
                    "file": str(item),
                    "size": item.stat().st_size,
                    "modified": item.stat().st_mtime
                })

        return quarantine_files

    def restore_from_quarantine(self, file_path: str, restore_path: Optional[str] = None) -> dict:
        """Restaure un fichier depuis la quarantaine"""
        source = Path(file_path)
        if not source.exists():
            return {"success": False, "error": "Fichier non trouvé en quarantaine"}

        if restore_path is None:
            # Restaurer à l'emplacement original (sans le suffixe .pid)
            restore_path = str(source).rsplit(".", 1)[0]

        try:
            os.rename(str(source), restore_path)
            log.info(f"Fichier restauré: {restore_path}")
            return {
                "success": True,
                "restored_to": restore_path,
                "message": f"Fichier restauré à: {restore_path}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_quarantine_file(self, file_path: str) -> dict:
        """Supprime définitivement un fichier de la quarantaine"""
        source = Path(file_path)
        if not source.exists():
            return {"success": False, "error": "Fichier non trouvé en quarantaine"}

        try:
            os.remove(str(source))
            log.info(f"Fichier supprimé de la quarantaine: {file_path}")
            return {
                "success": True,
                "deleted": str(source),
                "message": "Fichier définitivement supprimé"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # Test rapide
    logging.basicConfig(level=logging.INFO)

    agent = VirusAgent()

    print("=== Vérification ClamAV ===")
    print(f"Disponible: {agent.is_available()}")

    if agent.is_available():
        print("\n=== Test scan quick ===")
        result = agent.scan_quick()
        print(f"Résultat: {result['success']}")
        print(f"Menaces: {result['total_threats']}")

        print("\n=== Test scan et nettoyage ===")
        result = agent.scan_and_clean("quick")
        print(f"Statut: {result['status']}")
        print(f"Message: {result['message']}")
