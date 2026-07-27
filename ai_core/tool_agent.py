"""
AI Rescue USB - Tool-calling agent
===================================
Le LLM choisit lui-même quel outil appeler pour répondre à une demande
libre, plutôt que de suivre un routage par mots-clés figé. Volontairement
limité à des outils SAFE et en lecture seule (détection, diagnostic) —
aucune réparation/installation réelle ne part de ce chemin : ça reste le
travail des flux guidés (repair_flow.py, install_flow.py, ...) qui
demandent une confirmation explicite avant d'agir pour de vrai.

Design : les petits modèles locaux (ex. TinyLlama 1B) ne suivent pas de
façon fiable un format d'appel de fonction "à la OpenAI". On utilise donc
le mode `response_format={"type": "json_object"}` de llama-cpp-python, qui
force une sortie JSON valide par contrainte de grammaire — ça marche même
sur un modèle non spécifiquement entraîné pour ça.
"""
import json
import logging
from typing import Optional

log = logging.getLogger("tool-agent")


TOOLS = {
    "detect_hardware": "Get the computer's real detected hardware (CPU, RAM, disks, GPU).",
    "detect_os": "Get which operating systems are actually installed on this computer's disks.",
    "diagnose": "Diagnose a reported problem (boot issue, slow PC, disk error...) and get concrete suggested fixes.",
    "list_compatible_os": "List which operating systems (Windows/Linux/BSD versions) this computer can run.",
    "chat": "No tool needed — just answer the question directly from general knowledge.",
}

_TOOL_SELECTION_SYSTEM = (
    "You are a tool router for a computer-repair assistant. Given the user's message, "
    "pick the ONE tool that would best help answer it. Respond ONLY with JSON: "
    '{"tool": "<name>"}\n\nAvailable tools:\n' +
    "\n".join(f"- {name}: {desc}" for name, desc in TOOLS.items())
)


class ToolAgent:
    """Choisit un outil réel à appeler selon la demande, l'exécute, puis
    fait résumer le résultat réel par le LLM."""

    def __init__(self, llm):
        self.llm = llm
        self._hw_detector = None
        self._os_detector = None
        self._repair_agent = None
        self._install_agent = None

    def _load_agents(self):
        if self._hw_detector is None:
            try:
                from detection.hardware.detector import HardwareDetector
                self._hw_detector = HardwareDetector()
            except Exception as e:
                log.warning(f"HardwareDetector unavailable: {e}")
        if self._os_detector is None:
            try:
                from detection.os.detector import OSDetector
                self._os_detector = OSDetector()
            except Exception as e:
                log.warning(f"OSDetector unavailable: {e}")
        if self._repair_agent is None:
            try:
                from agents.repair.repair_agent import RepairAgent
                self._repair_agent = RepairAgent()
            except Exception as e:
                log.warning(f"RepairAgent unavailable: {e}")
        if self._install_agent is None:
            try:
                from agents.install_backup_recovery import InstallAgent
                self._install_agent = InstallAgent()
            except Exception as e:
                log.warning(f"InstallAgent unavailable: {e}")

    def select_tool(self, user_input: str) -> str:
        """Demande au LLM quel outil utiliser. Retombe sur "chat" si ambigu/indisponible."""
        try:
            resp = self.llm.model.create_chat_completion(
                messages=[
                    {"role": "system", "content": _TOOL_SELECTION_SYSTEM},
                    {"role": "user", "content": user_input},
                ],
                max_tokens=40,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(resp["choices"][0]["message"]["content"])
            tool = parsed.get("tool", "chat")
            return tool if tool in TOOLS else "chat"
        except Exception as e:
            log.warning(f"Tool selection failed, defaulting to chat: {e}")
            return "chat"

    def run_tool(self, tool: str, user_input: str) -> Optional[dict]:
        """Exécute réellement l'outil choisi. Retourne None si indisponible."""
        self._load_agents()
        try:
            if tool == "detect_hardware" and self._hw_detector:
                hw = self._hw_detector.detect_all()
                return {
                    "cpu": hw.cpu.model, "cores": hw.cpu.cores, "threads": hw.cpu.threads,
                    "ram_mb": hw.ram.total_mb, "disks": [
                        {"device": d.device, "model": d.model, "size_gb": round(d.size_gb, 1), "type": d.type}
                        for d in hw.disks
                    ],
                    "bios": hw.bios_type, "secure_boot": hw.secure_boot,
                }

            if tool == "detect_os" and self._os_detector:
                os_info = self._os_detector.detect_all()
                return {
                    "detected_os": [
                        {"name": o.name, "version": o.version, "boot_status": o.boot_status}
                        for o in os_info.detected_os
                    ],
                    "boot_mode": os_info.boot_mode,
                }

            if tool == "diagnose" and self._repair_agent:
                os_type = "windows"
                if self._os_detector:
                    try:
                        detected = self._os_detector.detect_all().detected_os
                        if detected:
                            os_type = detected[0].type
                    except Exception:
                        pass
                actions = self._repair_agent.diagnose(os_type, [user_input])
                return {
                    "os_type": os_type,
                    "suggested_fixes": [
                        {"name": a.name, "description": a.description, "risk": a.risk.value}
                        for a in actions
                    ],
                }

            if tool == "list_compatible_os" and self._install_agent and self._hw_detector:
                hw = self._hw_detector.detect_all()
                hardware_info = {
                    "ram_mb": hw.ram.total_mb,
                    "disk_gb": max((d.size_gb for d in hw.disks), default=0),
                    "tpm": getattr(hw, "tpm", False),
                    "secure_boot": hw.secure_boot,
                }
                return {"compatible_os": self._install_agent.list_compatible(hardware_info)}

        except Exception as e:
            log.warning(f"Tool '{tool}' execution failed: {e}")
            return {"error": str(e)}

        return None

    def answer(self, user_input: str, lang: str = "en") -> Optional[str]:
        """Point d'entrée : choisit un outil, l'exécute réellement, résume le résultat.

        Retourne None si aucun outil n'apporte de valeur (laisser l'appelant
        retomber sur la réponse LLM générique ou la base de connaissances).
        """
        if not self.llm or not getattr(self.llm, "loaded", False):
            return None

        tool = self.select_tool(user_input)
        if tool == "chat":
            return None

        result = self.run_tool(tool, user_input)
        if result is None:
            return None

        system = (
            "You are AI Rescue, a computer-repair assistant. You just ran a real check on "
            "the user's computer; here is the REAL result as JSON. Explain it to the user "
            "in plain, simple terms, in 3-4 sentences maximum, in "
            f"{'French' if lang == 'fr' else 'English'}. Do not invent data not present in "
            "the JSON. If suggested_fixes are present with risk MEDIUM or higher, tell the "
            "user what to type to start the guided repair (e.g. \"repair my PC\")."
        )
        prompt = f"User asked: \"{user_input}\"\n\nReal result:\n{json.dumps(result, ensure_ascii=False)}"
        try:
            return self.llm.generate(prompt, max_tokens=250, system=system)
        except Exception as e:
            log.warning(f"Summary generation failed: {e}")
            return None
