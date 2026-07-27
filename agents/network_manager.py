"""
AI Rescue USB - Network Manager
================================
Gestion du diagnostic et de la configuration réseau
Supporte WiFi, Ethernet, VPN
"""

import logging
import subprocess
import os
import json
from pathlib import Path
from typing import Optional, Dict, List

log = logging.getLogger("network-manager")


class NetworkManager:
    """
    Gestionnaire de configuration réseau
    Détection automatique, configuration WiFi/Ethernet, diagnostic
    """

    def __init__(self):
        self.interfaces = {}
        self._detect_interfaces()

    def _detect_interfaces(self) -> None:
        """Détecte toutes les interfaces réseau"""
        try:
            result = subprocess.run(
                ["ip", "-j", "link", "show"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.interfaces = json.loads(result.stdout)
            else:
                # Fallback si ip -j n'est pas disponible
                result = subprocess.run(
                    ["ip", "link", "show"],
                    capture_output=True,
                    text=True
                )
                self.interfaces = self._parse_ip_link(result.stdout)
        except Exception as e:
            log.error(f"Erreur détection interfaces: {e}")
            self.interfaces = []

    def _parse_ip_link(self, output: str) -> List[Dict]:
        """Parse la sortie classique de ip link show"""
        interfaces = []
        current = {}
        for line in output.split('\n'):
            if line and not line.startswith(' ') and ':' in line:
                if current:
                    interfaces.append(current)
                parts = line.split(':')
                current = {
                    'ifindex': int(parts[0].strip()) if parts[0].strip().isdigit() else 0,
                    'ifname': parts[1].strip(),
                    'flags': parts[2].strip().strip('<>').split(','),
                    'state': 'UP' if 'UP' in line else 'DOWN'
                }
            elif 'link/' in line:
                current['link_type'] = line.split('link/')[1].split()[0]
                if 'address' in line:
                    current['address'] = line.split('address')[1].strip()
        if current:
            interfaces.append(current)
        return interfaces

    def get_interfaces(self) -> List[Dict]:
        """Retourne la liste des interfaces réseau"""
        return self.interfaces

    def scan_wifi(self) -> Dict:
        """
        Scan des points d'accès WiFi disponibles
        """
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY,MODE", "dev", "wifi"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                # Tenter avec iw
                result = subprocess.run(
                    ["iw", "dev", "wlan0", "scan"],
                    capture_output=True,
                    text=True
                )
                return self._parse_iw_scan(result.stdout)

            networks = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split(':')
                if len(parts) >= 4:
                    ssid = parts[0]
                    signal = int(parts[1]) if parts[1].isdigit() else 0
                    security = parts[2]
                    mode = parts[3]

                    if ssid:  # Ignorer les SSID vides
                        networks.append({
                            'ssid': ssid,
                            'signal_strength': signal,
                            'security': security,
                            'mode': mode,
                            'secure': security != '' and security != 'OPEN'
                        })

            # Trier par signal strength
            networks.sort(key=lambda x: x['signal_strength'], reverse=True)

            return {
                'success': True,
                'networks': networks,
                'count': len(networks)
            }

        except Exception as e:
            log.error(f"Erreur scan WiFi: {e}")
            return {'success': False, 'error': str(e), 'networks': []}

    def _parse_iw_scan(self, output: str) -> Dict:
        """Parse la sortie de iw scan"""
        networks = []
        current = {}

        for line in output.split('\n'):
            if line.startswith('BSS '):
                if current and 'SSID' in current:
                    networks.append(current)
                current = {}
                # Extraire l'adresse MAC du BSS
                if ':' in line:
                    current['bssid'] = line.split()[1]
            elif 'SSID:' in line:
                ssid = line.split('SSID:')[1].strip()
                if ssid:
                    current['ssid'] = ssid
            elif 'signal:' in line and 'signal' not in current:
                parts = line.split()
                for i, part in enumerate(parts):
                    if 'signal:' in part and i + 1 < len(parts):
                        signal = float(parts[i + 1])
                        # Convertir dBm en pourcentage approximatif
                        current['signal_strength'] = min(100, max(0, (signal + 100) * 2))
                        break
            elif 'WPA' in line or 'RSN' in line:
                current['secure'] = True
                current['security'] = 'WPA'
            elif 'WEP' in line:
                current['secure'] = True
                current['security'] = 'WEP'

        if current and 'SSID' in current:
            networks.append(current)

        return {
            'success': True,
            'networks': networks,
            'count': len(networks)
        }

    def connect_wifi(self, ssid: str, password: Optional[str] = None) -> Dict:
        """
        Connexion à un réseau WiFi
        """
        try:
            # Vérifier si déjà connecté
            result = subprocess.run(
                ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"],
                capture_output=True,
                text=True
            )
            active = [line for line in result.stdout.split('\n') if 'wifi' in line]
            if active:
                log.info(f"Déjà connecté à un réseau WiFi: {active[0]}")

            # Construire la commande de connexion
            cmd = ["nmcli", "device", "wifi", "connect", ssid]
            if password:
                cmd.extend(["password", password])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                log.info(f"Connecté avec succès à {ssid}")
                return {
                    'success': True,
                    'connected': True,
                    'ssid': ssid,
                    'message': f"Connecté à {ssid}"
                }
            else:
                error = result.stderr.strip()
                log.error(f"Échec connexion: {error}")
                return {
                    'success': False,
                    'connected': False,
                    'error': error,
                    'message': f"Échec de la connexion: {error}"
                }

        except Exception as e:
            log.error(f"Erreur connexion WiFi: {e}")
            return {'success': False, 'error': str(e), 'message': str(e)}

    def get_connection_status(self) -> Dict:
        """
        Récupère le statut de toutes les connexions
        """
        status = {
            'interfaces': [],
            'default_route': None,
            'dns_servers': []
        }

        # Statut des interfaces
        for iface in self.interfaces:
            if 'ifname' not in iface:
                continue

            iface_name = iface['ifname']
            state = iface.get('state', 'UNKNOWN')

            # Ignorer loopback
            if iface_name == 'lo':
                continue

            iface_info = {
                'name': iface_name,
                'state': state,
                'type': iface.get('link_type', 'unknown'),
                'mac': iface.get('address', 'unknown'),
                'ipv4': [],
                'ipv6': []
            }

            # Obtenir les adresses IP
            try:
                result = subprocess.run(
                    ["ip", "-j", "addr", "show", iface_name],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    if data:
                        for addr_info in data[0].get('addr_info', []):
                            if addr_info.get('family') == 'inet':
                                iface_info['ipv4'].append({
                                    'address': addr_info.get('local'),
                                    'prefixlen': addr_info.get('prefixlen')
                                })
                            elif addr_info.get('family') == 'inet6':
                                iface_info['ipv6'].append({
                                    'address': addr_info.get('local'),
                                    'prefixlen': addr_info.get('prefixlen')
                                })
            except Exception as e:
                log.debug(f"Erreur obtention IP pour {iface_name}: {e}")

            status['interfaces'].append(iface_info)

        # Route par défaut
        try:
            result = subprocess.run(
                ["ip", "-j", "route", "show", "default"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                routes = json.loads(result.stdout)
                if routes:
                    status['default_route'] = {
                        'gateway': routes[0].get('gateway'),
                        'dev': routes[0].get('dev')
                    }
        except Exception as e:
            log.debug(f"Erreur route par défaut: {e}")

        # DNS servers
        try:
            with open('/etc/resolv.conf', 'r') as f:
                for line in f:
                    if line.startswith('nameserver'):
                        dns = line.split()[1]
                        status['dns_servers'].append(dns)
        except Exception as e:
            log.debug(f"Erreur lecture DNS: {e}")

        return status

    def test_internet(self) -> Dict:
        """
        Test de la connectivité Internet
        """
        tests = {
            'ping_8_8_8_8': None,
            'ping_1_1_1_1': None,
            'dns_resolution': None,
            'http_connectivity': None
        }

        # Test ping
        try:
            result = subprocess.run(
                ["ping", "-c", "3", "-W", "2", "8.8.8.8"],
                capture_output=True,
                text=True
            )
            tests['ping_8_8_8_8'] = {
                'success': result.returncode == 0,
                'details': result.stdout
            }
        except Exception as e:
            tests['ping_8_8_8_8'] = {'success': False, 'error': str(e)}

        # Test DNS
        try:
            result = subprocess.run(
                ["nslookup", "google.com"],
                capture_output=True,
                text=True
            )
            tests['dns_resolution'] = {
                'success': result.returncode == 0,
                'details': result.stdout
            }
        except Exception as e:
            tests['dns_resolution'] = {'success': False, 'error': str(e)}

        # Test HTTP (si curl est disponible)
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://example.com"],
                capture_output=True,
                text=True
            )
            http_code = int(result.stdout.strip()) if result.stdout.strip() else 0
            tests['http_connectivity'] = {
                'success': 200 <= http_code < 400,
                'http_code': http_code
            }
        except Exception as e:
            tests['http_connectivity'] = {'success': False, 'error': str(e)}

        # Résumé
        passed = sum(1 for t in tests.values() if t and t.get('success'))
        total = sum(1 for t in tests.values() if t is not None)

        return {
            'tests': tests,
            'passed': passed,
            'total': total,
            'internet_working': passed > 0 and passed >= total // 2,
            'summary': f"{passed}/{total} tests réussis"
        }

    def get_speed_test(self) -> Dict:
        """
        Test de vitesse réseau (bandwidth)
        """
        try:
            # Utiliser speedtest-cli si disponible
            result = subprocess.run(
                ["speedtest-cli", "--json"],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return {
                    'success': True,
                    'download_mbps': data.get('download', 0) / 1000000,
                    'upload_mbps': data.get('upload', 0) / 1000000,
                    'ping_ms': data.get('ping', 0)
                }
        except FileNotFoundError:
            log.debug("speedtest-cli non trouvé")
        except Exception as e:
            log.error(f"Erreur speed test: {e}")

        # Fallback: test manuel avec iperf ou dd
        return {
            'success': False,
            'message': "speedtest-cli non disponible. Installez avec: apt install speedtest-cli"
        }


if __name__ == "__main__":
    # Test rapide
    logging.basicConfig(level=logging.INFO)

    manager = NetworkManager()

    print("=== Interfaces réseau détectées ===")
    interfaces = manager.get_interfaces()
    for iface in interfaces:
        if 'ifname' in iface:
            print(f"- {iface['ifname']}: {iface.get('state', 'UNKNOWN')}")

    print("\n=== Statut des connexions ===")
    status = manager.get_connection_status()
    for iface in status['interfaces']:
        print(f"- {iface['name']}: {iface['state']}")
        if iface['ipv4']:
            print(f"  IPv4: {iface['ipv4'][0]['address']}/{iface['ipv4'][0]['prefixlen']}")

    print("\n=== Test Internet ===")
    result = manager.test_internet()
    print(f"Résultat: {result['summary']}")
    for test_name, test_result in result['tests'].items():
        if test_result:
            status = "✓" if test_result.get('success') else "✗"
            print(f"  {status} {test_name}")
