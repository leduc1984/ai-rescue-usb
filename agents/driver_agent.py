"""
AI Rescue USB - Driver Agent
=============================
Gère la détection et l'installation de pilotes automatiquement.
"""

import logging
import subprocess
import os
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("driver-agent")


@dataclass
class DeviceInfo:
    """Information sur un périphérique matériel."""
    vendor_id: str
    device_id: str
    vendor_name: str
    device_name: str
    driver_status: str  # "installed", "missing", "unknown"
    driver_path: str = ""
    bus_type: str = ""  # "pci", "usb", etc.


class DriverAgent:
    """
    Agent de gestion des pilotes.
    Détecte automatiquement le matériel manquant et installe les pilotes.
    """

    def __init__(self):
        self.driver_cache_dir = Path("/opt/ai-rescue/drivers")
        self.driver_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Base de données de pilotes courants
        self.known_drivers = {
            "Intel WiFi": ["iwlwifi", "iwlmvm"],
            "Realtek Ethernet": ["r8169", "r8168"],
            "NVIDIA GPU": ["nvidia", "nouveau"],
            "AMD GPU": ["amdgpu", "radeon"],
            "Intel GPU": ["i915"],
            "Audio Realtek": ["snd_hda_intel"],
        }

    def scan_devices(self) -> list[DeviceInfo]:
        """
        Scanne tous les périphériques PCI et USB pour détecter le matériel.
        Retourne la liste des périphériques détectés.
        """
        devices = []
        
        try:
            # Scanner les périphériques PCI
            pci_output = self._run_command("lspci -nn")
            if pci_output:
                devices.extend(self._parse_lspci(pci_output))
            
            # Scanner les périphériques USB
            usb_output = self._run_command("lsusb")
            if usb_output:
                devices.extend(self._parse_lsusb(usb_output))
                
            log.info(f"Scan terminé: {len(devices)} périphériques détectés")
            return devices
            
        except Exception as e:
            log.error(f"Erreur lors du scan: {e}")
            return devices

    def _parse_lspci(self, output: str) -> list[DeviceInfo]:
        """Parse la sortie de lspci."""
        devices = []
        import re
        
        for line in output.split("\n"):
            if not line.strip():
                continue
            
            # Format: "00:1f.2 SATA controller [0106]: Intel Corporation ..."
            match = re.match(r'^[0-9a-f:]+\s+(.+?\s+\[([0-9a-f]+)\]):\s+(.*)', line)
            if match:
                device_type = match.group(1)
                device_class = match.group(2)
                device_name = match.group(3)
                
                # Extraire vendor:device ID
                vendor_match = re.search(r'\[([0-9a-f]{4}):([0-9a-f]{4})\]', device_name)
                if vendor_match:
                    vendor_id = vendor_match.group(1)
                    device_id = vendor_match.group(2)
                else:
                    vendor_id = "unknown"
                    device_id = "unknown"
                
                devices.append(DeviceInfo(
                    vendor_id=vendor_id,
                    device_id=device_id,
                    vendor_name=self._get_vendor_name(vendor_id),
                    device_name=device_name,
                    driver_status="unknown",
                    bus_type="pci"
                ))
        
        return devices

    def _parse_lsusb(self, output: str) -> list[DeviceInfo]:
        """Parse la sortie de lsusb."""
        devices = []
        import re
        
        for line in output.split("\n"):
            if not line.strip():
                continue
            
            # Format: "Bus 001 Device 002: ID 8087:0a2b Intel Corp."
            match = re.search(r'ID\s+([0-9a-f]{4}):([0-9a-f]{4})\s+(.*)', line)
            if match:
                vendor_id = match.group(1)
                device_id = match.group(2)
                device_name = match.group(3)
                
                devices.append(DeviceInfo(
                    vendor_id=vendor_id,
                    device_id=device_id,
                    vendor_name=self._get_vendor_name(vendor_id),
                    device_name=device_name,
                    driver_status="unknown",
                    bus_type="usb"
                ))
        
        return devices

    def _get_vendor_name(self, vendor_id: str) -> str:
        """Retourne le nom du vendor basé sur l'ID."""
        # Base simplifiée - en production, utiliser usb.ids et pci.ids
        vendors = {
            "8086": "Intel Corporation",
            "10de": "NVIDIA Corporation",
            "1002": "Advanced Micro Devices, Inc.",
            "10ec": "Realtek Semiconductor Co., Ltd.",
            "14e4": "Broadcom Corporation",
            "0cf3": "Qualcomm Atheros Communications",
        }
        return vendors.get(vendor_id, f"Unknown ({vendor_id})")

    def check_missing_drivers(self, devices: list[DeviceInfo]) -> list[DeviceInfo]:
        """
        Vérifie quels pilotes sont manquants.
        Retourne la liste des périphériques sans pilotes.
        """
        missing = []
        
        for device in devices:
            # Vérifier si le périphérique a un pilote chargé
            try:
                # Pour les périphériques PCI, vérifier /sys/bus/pci/devices/
                if device.bus_type == "pci":
                    pci_path = f"/sys/bus/pci/devices/*/driver"
                    result = self._run_command(f"ls {pci_path} 2>/dev/null | grep {device.vendor_id}")
                    if not result:
                        device.driver_status = "missing"
                        missing.append(device)
                    else:
                        device.driver_status = "installed"
                        
                # Pour les périphériques USB
                elif device.bus_type == "usb":
                    # Vérifier si le périphérique est reconnu
                    usb_path = f"/sys/bus/usb/devices/*/idVendor"
                    result = self._run_command(f"grep -r {device.vendor_id} {usb_path} 2>/dev/null")
                    if not result:
                        device.driver_status = "missing"
                        missing.append(device)
                    else:
                        device.driver_status = "installed"
                        
            except Exception as e:
                log.debug(f"Erreur vérification pilote pour {device.device_name}: {e}")
        
        log.info(f"{len(missing)} périphériques sans pilotes détectés")
        return missing

    def suggest_driver(self, device: DeviceInfo) -> str:
        """
        Suggère le pilote approprié pour un périphérique.
        Retourne le nom du module/pilote à charger.
        """
        device_name_lower = device.device_name.lower()
        
        # Chercher dans la base de données de pilotes connus
        for key, drivers in self.known_drivers.items():
            if key.lower() in device_name_lower:
                return drivers[0]  # Retourner le pilote principal
        
        # Fallback: utiliser modinfo pour chercher
        try:
            result = self._run_command(f"modinfo -F alias {device.vendor_id}:{device.device_id}")
            if result:
                return result.strip()
        except Exception:
            pass
        
        return "unknown"

    def install_driver(self, driver_name: str) -> dict:
        """
        Tente d'installer un pilote.
        Retourne le statut de l'installation.
        """
        log.info(f"Installation du pilote: {driver_name}")
        
        try:
            # Essayer de charger le module
            result = self._run_command(f"modprobe {driver_name}")
            
            if result is not None:
                # Vérifier si le module est chargé
                loaded = self._run_command(f"lsmod | grep {driver_name}")
                
                if loaded:
                    return {
                        "success": True,
                        "driver": driver_name,
                        "message": f"Pilote {driver_name} chargé avec succès"
                    }
                else:
                    return {
                        "success": False,
                        "driver": driver_name,
                        "message": f"Échec du chargement du pilote {driver_name}"
                    }
            else:
                return {
                    "success": False,
                    "driver": driver_name,
                    "message": f"Module {driver_name} non trouvé"
                }
                
        except Exception as e:
            return {
                "success": False,
                "driver": driver_name,
                "message": f"Erreur: {str(e)}"
            }

    def auto_install_all_missing(self, devices: list[DeviceInfo]) -> list[dict]:
        """
        Tente d'installer automatiquement tous les pilotes manquants.
        Retourne la liste des résultats.
        """
        results = []
        
        for device in devices:
            driver_name = self.suggest_driver(device)
            
            if driver_name != "unknown":
                result = self.install_driver(driver_name)
                result["device"] = device.device_name
                results.append(result)
                log.info(f"{device.device_name}: {result['message']}")
            else:
                results.append({
                    "success": False,
                    "driver": "unknown",
                    "device": device.device_name,
                    "message": "Aucun pilote trouvé pour ce périphérique"
                })
        
        return results

    def _run_command(self, command: str) -> str:
        """Exécute une commande shell et retourne la sortie."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception as e:
            log.error(f"Erreur commande '{command}': {e}")
            return ""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    agent = DriverAgent()
    
    print("=== Scan des périphériques ===")
    devices = agent.scan_devices()
    print(f"Détecté {len(devices)} périphériques\n")
    
    print("=== Vérification des pilotes ===")
    missing = agent.check_missing_drivers(devices)
    print(f"Pilotes manquants: {len(missing)}\n")
    
    if missing:
        print("=== Suggestion de pilotes ===")
        for device in missing[:5]:  # Afficher les 5 premiers
            driver = agent.suggest_driver(device)
            print(f"  {device.device_name}: {driver}")
