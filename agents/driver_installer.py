"""
AI Rescue USB - Driver Installer
================================
Détection automatique et installation des drivers manquants
Supporte Linux, Windows (via Wine/NTFS), macOS (limité)
"""

import logging
import subprocess
import os
import json
import re
from pathlib import Path
from typing import Optional, Dict, List

log = logging.getLogger("driver-installer")


class DriverInstaller:
    """
    Gestionnaire de drivers
    Détecte automatiquement le matériel et installe les drivers manquants
    """

    def __init__(self):
        self.drivers_db_path = Path("/opt/ai-rescue/drivers-db.json")
        self.drivers_db = self._load_drivers_db()

    def _load_drivers_db(self) -> Dict:
        """
        Charge la base de données des drivers
        Format: {vendor_id: {device_id: {driver_name, package, source}}}
        """
        if self.drivers_db_path.exists():
            try:
                with open(self.drivers_db_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                log.error(f"Erreur chargement DB: {e}")

        # DB par défaut avec les drivers communs
        return {
            "nvidia": {
                "package": "nvidia-driver",
                "install": "apt install -y nvidia-driver nvidia-settings",
                "modprobe": "nvidia"
            },
            "amd": {
                "package": "amdgpu",
                "install": "apt install -y xserver-xorg-video-amdgpu",
                "modprobe": "amdgpu"
            },
            "intel-wifi": {
                "package": "firmware-iwlwifi",
                "install": "apt install -y firmware-iwlwifi",
                "modprobe": "iwlwifi"
            },
            "realtek-wifi": {
                "package": "firmware-realtek",
                "install": "apt install -y firmware-realtek",
                "modprobe": "rtw88_8822ce"
            },
            "broadcom-wifi": {
                "package": "firmware-brcm80211",
                "install": "apt install -y firmware-brcm80211",
                "modprobe": "brcmfmac"
            },
            "bluetooth": {
                "package": "bluez",
                "install": "apt install -y bluez bluez-tools",
                "modprobe": "bluetooth"
            },
            "sound-hda": {
                "package": "alsa-utils",
                "install": "apt install -y alsa-utils pulseaudio",
                "modprobe": "snd_hda_intel"
            },
            "printer-hp": {
                "package": "hplip",
                "install": "apt install -y hplip hplip-gui",
                "modprobe": None  # Pas de kernel module
            },
            "usb-storage": {
                "package": None,
                "install": "modprobe usb-storage",
                "modprobe": "usb-storage"
            }
        }

    def detect_all(self) -> Dict:
        """
        Détecte tout le matériel nécessitant des drivers
        """
        devices = {
            'pci': [],
            'usb': [],
            'missing_drivers': [],
            'summary': {}
        }

        # PCI devices (lspci)
        try:
            result = subprocess.run(
                ["lspci", "-k"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                devices['pci'] = self._parse_lspci(result.stdout)
        except Exception as e:
            log.error(f"Erreur lspci: {e}")

        # USB devices (lsusb)
        try:
            result = subprocess.run(
                ["lsusb"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                devices['usb'] = self._parse_lsusb(result.stdout)
        except Exception as e:
            log.error(f"Erreur lsusb: {e}")

        # Identifier les drivers manquants
        devices['missing_drivers'] = self._find_missing_drivers(devices)

        # Résumé
        devices['summary'] = {
            'total_pci': len(devices['pci']),
            'total_usb': len(devices['usb']),
            'missing_count': len(devices['missing_drivers']),
            'categories': self._categorize_devices(devices)
        }

        return devices

    def _parse_lspci(self, output: str) -> List[Dict]:
        """Parse la sortie de lspci -k"""
        devices = []
        current_device = None

        for line in output.split('\n'):
            # Nouvelle ligne de device (ex: "00:02.0 VGA compatible controller...")
            if re.match(r'^\w{2}:\w{2}\.\w\s', line):
                if current_device:
                    devices.append(current_device)

                parts = line.split(':', 1)
                current_device = {
                    'type': 'pci',
                    'slot': parts[0].strip(),
                    'description': parts[1].strip() if len(parts) > 1 else '',
                    'kernel_driver': None,
                    'vendor': None,
                    'device_id': None
                }

            # Kernel driver in use (ex: "Kernel driver in use: i915")
            elif 'Kernel driver in use:' in line and current_device:
                driver = line.split('Kernel driver in use:')[1].strip()
                current_device['kernel_driver'] = driver

            # Kernel modules (ex: "Kernel modules: i915")
            elif 'Kernel modules:' in line and current_device:
                modules = line.split('Kernel modules:')[1].strip()
                current_device['kernel_modules'] = modules.split(',')

            # Vendor/Device ID (ex: "8086:5916")
            elif re.match(r'.*\[[\w\d]{4}:[\w\d]{4}\]', line) and current_device:
                match = re.search(r'\[([\w\d]{4}):([\w\d]{4})\]', line)
                if match:
                    current_device['vendor'] = match.group(1)
                    current_device['device_id'] = match.group(2)

        if current_device:
            devices.append(current_device)

        return devices

    def _parse_lsusb(self, output: str) -> List[Dict]:
        """Parse la sortie de lsusb"""
        devices = []

        for line in output.split('\n'):
            if not line.strip():
                continue

            # Format: "Bus 002 Device 003: ID 046d:c31c Logitech, Inc. Keyboard K120"
            match = re.match(r'Bus\s+(\d+)\s+Device\s+(\d+):\s+ID\s+([\da-fA-F]+):([\da-fA-F]+)\s+(.*)', line)
            if match:
                devices.append({
                    'type': 'usb',
                    'bus': match.group(1),
                    'device': match.group(2),
                    'vendor_id': match.group(3),
                    'product_id': match.group(4),
                    'description': match.group(5).strip()
                })

        return devices

    def _find_missing_drivers(self, devices: Dict) -> List[Dict]:
        """Identifie les devices sans drivers"""
        missing = []

        # PCI devices sans kernel driver
        for device in devices['pci']:
            # Vérifier si c'est un device qui a besoin d'un driver
            keywords = ['audio', 'network', 'ethernet', 'wi-fi', 'wifi', 
                       'bluetooth', 'printer', 'scanner', 'camera', 'gpu',
                       'vga', 'display', 'controller']

            description = device.get('description', '').lower()

            if any(keyword in description for keyword in keywords):
                if not device.get('kernel_driver'):
                    missing.append({
                        **device,
                        'reason': 'No kernel driver',
                        'suggested_driver': self._suggest_driver(device)
                    })

        return missing

    def _suggest_driver(self, device: Dict) -> Optional[str]:
        """Suggère un driver basé sur le device"""
        description = device.get('description', '').lower()

        # Mapping keywords -> drivers
        mappings = {
            'nvidia': 'nvidia',
            'geforce': 'nvidia',
            'radeon': 'amd',
            'amd.*display': 'amd',
            'intel.*wifi': 'intel-wifi',
            'wireless.*intel': 'intel-wifi',
            'qualcomm.*ath': 'intel-wifi',  # Atheros aussi
            'realtek.*rtl': 'realtek-wifi',
            'broadcom.*bcm': 'broadcom-wifi',
            'bluetooth': 'bluetooth',
            'audio.*intel': 'sound-hda',
            'sound.*intel': 'sound-hda',
            'hda.*audio': 'sound-hda',
            'printer': 'printer-hp'
        }

        for keyword, driver in mappings.items():
            if re.search(keyword, description):
                return driver

        return None

    def _categorize_devices(self, devices: Dict) -> Dict:
        """Catégorise les devices par type"""
        categories = {
            'network': 0,
            'display': 0,
            'audio': 0,
            'usb': 0,
            'other': 0
        }

        # Compter PCI devices par catégorie
        for device in devices['pci']:
            desc = device.get('description', '').lower()
            if 'network' in desc or 'ethernet' in desc or 'wifi' in desc:
                categories['network'] += 1
            elif 'display' in desc or 'vga' in desc or 'gpu' in desc:
                categories['display'] += 1
            elif 'audio' in desc or 'sound' in desc:
                categories['audio'] += 1
            else:
                categories['other'] += 1

        categories['usb'] = len(devices['usb'])

        return categories

    def install_missing(self, devices: Optional[Dict] = None) -> Dict:
        """
        Installe les drivers manquants
        """
        if devices is None:
            devices = self.detect_all()

        results = {
            'installed': [],
            'failed': [],
            'skipped': [],
            'summary': {}
        }

        for device in devices.get('missing_drivers', []):
            driver_name = device.get('suggested_driver')
            if not driver_name:
                results['skipped'].append({
                    'device': device['description'],
                    'reason': 'No driver suggestion available'
                })
                continue

            driver_info = self.drivers_db.get(driver_name)
            if not driver_info:
                results['skipped'].append({
                    'device': device['description'],
                    'reason': f'No driver info for {driver_name}'
                })
                continue

            # Tentative d'installation
            result = self._install_driver(driver_name, driver_info)

            if result['success']:
                results['installed'].append({
                    'device': device['description'],
                    'driver': driver_name,
                    'package': driver_info.get('package')
                })
            else:
                results['failed'].append({
                    'device': device['description'],
                    'driver': driver_name,
                    'error': result['error']
                })

        results['summary'] = {
            'total_missing': len(devices.get('missing_drivers', [])),
            'installed': len(results['installed']),
            'failed': len(results['failed']),
            'skipped': len(results['skipped'])
        }

        return results

    def _install_driver(self, driver_name: str, driver_info: Dict) -> Dict:
        """Installe un driver spécifique"""
        try:
            # Installer le package si spécifié
            package = driver_info.get('package')
            if package:
                install_cmd = driver_info.get('install', f"apt install -y {package}")
                result = subprocess.run(
                    install_cmd.split(),
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                if result.returncode != 0:
                    return {
                        'success': False,
                        'error': f"Package install failed: {result.stderr}"
                    }

            # Charger le module kernel si spécifié
            modprobe = driver_info.get('modprobe')
            if modprobe:
                result = subprocess.run(
                    ["modprobe", modprobe],
                    capture_output=True,
                    text=True
                )

                if result.returncode != 0:
                    return {
                        'success': False,
                        'error': f"Module load failed: {result.stderr}"
                    }

            log.info(f"Driver {driver_name} installé avec succès")
            return {'success': True}

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Timeout during installation'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def update_drivers_db(self) -> Dict:
        """
        Met à jour la base de données des drivers depuis Internet
        """
        try:
            # Tenter de télécharger une DB mise à jour
            result = subprocess.run(
                ["wget", "-O", str(self.drivers_db_path),
                 "https://raw.githubusercontent.com/ai-rescue-usb/drivers-db/main/drivers.json"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                self.drivers_db = self._load_drivers_db()
                return {
                    'success': True,
                    'message': 'Base de données mise à jour'
                }
            else:
                return {
                    'success': False,
                    'message': 'Échec de la mise à jour (DB par défaut conservée)'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Erreur: {e}'
            }


if __name__ == "__main__":
    # Test rapide
    logging.basicConfig(level=logging.INFO)

    installer = DriverInstaller()

    print("=== Détection du matériel ===")
    devices = installer.detect_all()
    print(f"PCI devices: {devices['summary']['total_pci']}")
    print(f"USB devices: {devices['summary']['total_usb']}")
    print(f"Drivers manquants: {devices['summary']['missing_count']}")

    if devices['missing_drivers']:
        print("\n=== Drivers manquants ===")
        for device in devices['missing_drivers'][:5]:  # Afficher les 5 premiers
            print(f"- {device['description']}")
            if device.get('suggested_driver'):
                print(f"  Driver suggéré: {device['suggested_driver']}")

        print("\n=== Installation des drivers ===")
        result = installer.install_missing(devices)
        print(f"Installés: {result['summary']['installed']}")
        print(f"Échecs: {result['summary']['failed']}")
        print(f"Ignorés: {result['summary']['skipped']}")
