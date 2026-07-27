"""
AI Rescue USB - Antivirus Agent
================================
Scan et nettoyage de malware/virus
"""

import logging
import subprocess
import os
from pathlib import Path

log = logging.getLogger("antivirus-agent")


class AntivirusAgent:
    """Agent de détection et nettoyage de malware"""
    
    def __init__(self):
        self.clamscan_path = "/usr/bin/clamscan"
        self.freshclam_path = "/usr/bin/freshclam"
        self.log_dir = Path("/var/log/ai-rescue")
        
    def update_definitions(self) -> dict:
        """Met à jour les définitions de virus"""
        try:
            result = subprocess.run(
                [self.freshclam_path],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "Définitions mises à jour"
                }
            else:
                return {
                    "success": False,
                    "message": f"Échec: {result.stderr}"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Erreur: {str(e)}"
            }
    
    def quick_scan(self, path: str = "/") -> dict:
        """Scan rapide des zones critiques"""
        critical_dirs = [
            "/boot",
            "/etc",
            "/usr/bin",
            "/usr/sbin",
            "/home",
            "/root"
        ]
        
        results = []
        for directory in critical_dirs:
            if os.path.exists(directory):
                result = self._scan_directory(directory)
                results.append(result)
        
        threats_found = sum(r.get("threats", 0) for r in results)
        
        return {
            "success": True,
            "threats_found": threats_found,
            "scanned_dirs": len(critical_dirs),
            "details": results
        }
    
    def full_scan(self, path: str = "/") -> dict:
        """Scan complet du système"""
        return self._scan_directory(path, recursive=True)
    
    def _scan_directory(self, path: str, recursive: bool = False) -> dict:
        """Scanne un répertoire pour malware"""
        try:
            cmd = [self.clamscan_path, "-r" if recursive else ""]
            if recursive:
                cmd.append("--infected")
            cmd.append(path)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 heure max
            )
            
            # Parser la sortie de clamscan
            infected_files = []
            for line in result.stdout.split("\n"):
                if "FOUND" in line:
                    infected_files.append(line)
            
            return {
                "success": result.returncode in [0, 1],  # 0=clean, 1=infected
                "path": path,
                "threats": len(infected_files),
                "infected_files": infected_files[:20],  # Limiter à 20
                "scan_time": result.stderr.split("Time:")[-1].strip() if "Time:" in result.stderr else "Unknown"
            }
        except Exception as e:
            return {
                "success": False,
                "path": path,
                "message": f"Erreur: {str(e)}"
            }
    
    def quarantine_infected(self, infected_files: list) -> dict:
        """Met en quarantaine les fichiers infectés"""
        quarantine_dir = Path("/opt/ai-rescue/quarantine")
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        
        moved_count = 0
        errors = []
        
        for file_info in infected_files:
            # Extraire le chemin du fichier
            if ":" in file_info:
                file_path = file_info.split(":")[0].strip()
                
                if os.path.exists(file_path):
                    try:
                        # Déplacer vers quarantaine
                        dest = quarantine_dir / os.path.basename(file_path)
                        os.rename(file_path, dest)
                        moved_count += 1
                        log.info(f"Quarantined: {file_path}")
                    except Exception as e:
                        errors.append(f"{file_path}: {str(e)}")
        
        return {
            "success": len(errors) == 0,
            "quarantined": moved_count,
            "errors": errors
        }
    
    def remove_threats(self, infected_files: list) -> dict:
        """Supprime les fichiers infectés (irréversible!)"""
        removed_count = 0
        errors = []
        
        for file_info in infected_files:
            if ":" in file_info:
                file_path = file_info.split(":")[0].strip()
                
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        removed_count += 1
                        log.info(f"Removed threat: {file_path}")
                    except Exception as e:
                        errors.append(f"{file_path}: {str(e)}")
        
        return {
            "success": len(errors) == 0,
            "removed": removed_count,
            "errors": errors
        }
    
    def create_report(self, scan_results: dict) -> str:
        """Crée un rapport de scan"""
        report = []
        report.append("=" * 60)
        report.append("AI RESCUE USB - RAPPORT ANTIVIRUS")
        report.append("=" * 60)
        report.append("")
        
        if scan_results.get("threats_found", 0) == 0:
            report.append("✅ AUCUNE MENACE DÉTECTÉE")
            report.append("")
            report.append("Votre système est propre.")
        else:
            report.append(f"⚠️  {scan_results['threats_found']} MENACE(S) DÉTECTÉE(S)")
            report.append("")
            
            for detail in scan_results.get("details", []):
                if detail.get("threats", 0) > 0:
                    report.append(f"Dossier: {detail['path']}")
                    for infected in detail.get("infected_files", []):
                        report.append(f"  - {infected}")
            report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)
