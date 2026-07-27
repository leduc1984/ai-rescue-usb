"""
AI Rescue USB - Network Manager Agent
======================================
Gestion automatique des connexions réseau
"""

import logging
import subprocess
import os
import re
from pathlib import Path
from typing import Optional

log = logging.getLogger("network-agent")


class NetworkAgent:
    """Agent de gestion réseau automatique"""
    
    def __init__(self):
        self.wifi_config_dir = Path("/opt/ai-rescue/wifi-configs")
        self.wifi_config_dir.mkdir(parents=True, exist_ok=True)
        
    def scan_wifi(self) -> list[dict]:
        """Scanne les réseaux WiFi disponibles"""
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            networks = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split(":")
                    if len(parts) >= 3:
                        ssid = parts[0]
                        signal = parts[1]
                        security = parts[2]
                        
                        if ssid:  # Ignorer les réseaux cachés
                            networks.append({
                                "ssid": ssid,
                                "signal": int(signal),
                                "secured": bool(security),
                                "security_type": security
                            })
            
            # Trier par signal strength
            networks.sort(key=lambda x: x["signal"], reverse=True)
            return networks[:10]  # Top 10
            
        except Exception as e:
            log.error(f"WiFi scan failed: {e}")
            return []
    
    def connect_wifi(self, ssid: str, password: Optional[str] = None) -> dict:
        """Connecte à un réseau WiFi"""
        try:
            # Créer la connexion
            cmd = ["nmcli", "dev", "wifi", "connect", ssid]
            if password:
                cmd.append("password")
                cmd.append(password)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                # Sauvegarder la config pour usage futur
                self._save_wifi_config(ssid, password)
                return {
                    "success": True,
                    "message": f"Connecté à {ssid}"
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
    
    def _save_wifi_config(self, ssid: str, password: Optional[str]):
        """Sauvegarde la config WiFi pour réutilisation"""
        try:
            config = {
                "ssid": ssid,
                "password": password,
                "auto_connect": True
            }
            import json
            config_file = self.wifi_config_dir / f"{ssid}.json"
            with open(config_file, "w") as f:
                json.dump(config, f)
        except Exception as e:
            log.warning(f"Could not save WiFi config: {e}")
    
    def get_connection_status(self) -> dict:
        """Obtient le statut de connexion actuel"""
        try:
            # Vérifier WiFi
            wifi_result = subprocess.run(
                ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "dev", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            connection_type = "disconnected"
            for line in wifi_result.stdout.strip().split("\n"):
                if "wifi" in line and "connected" in line:
                    connection_type = "wifi"
                    break
            
            # Vérifier Ethernet
            eth_result = subprocess.run(
                ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "dev", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            for line in eth_result.stdout.strip().split("\n"):
                if "ethernet" in line and "connected" in line:
                    connection_type = "ethernet"
                    break
            
            # Obtenir l'IP
            ip = "unknown"
            if connection_type != "disconnected":
                ip_result = subprocess.run(
                    ["ip", "-4", "addr", "show"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                ip_match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)/\d+", ip_result.stdout)
                if ip_match:
                    ip = ip_match.group(1)
            
            return {
                "connected": connection_type != "disconnected",
                "type": connection_type,
                "ip": ip
            }
        except Exception as e:
            return {
                "connected": False,
                "type": "error",
                "message": str(e)
            }
    
    def test_internet(self) -> dict:
        """Teste la connexion Internet"""
        try:
            # Test ping Google DNS
            ping_result = subprocess.run(
                ["ping", "-c", "3", "8.8.8.8"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if ping_result.returncode == 0:
                return {
                    "success": True,
                    "message": "Internet accessible"
                }
            else:
                return {
                    "success": False,
                    "message": "Pas de connexion Internet"
                }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
    
    def get_saved_networks(self) -> list[str]:
        """Récupère les réseaux WiFi sauvegardés"""
        try:
            networks = []
            if self.wifi_config_dir.exists():
                import json
                for config_file in self.wifi_config_dir.glob("*.json"):
                    with open(config_file) as f:
                        config = json.load(f)
                        networks.append(config["ssid"])
            return networks
        except Exception as e:
            log.error(f"Could not read saved networks: {e}")
            return []
