"""
AI Rescue USB - Voice System
=============================
Reconnaissance vocale offline (Whisper) + Text-to-Speech (Piper).
Fonctionne 100% sans Internet.
"""

import asyncio
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Callable

log = logging.getLogger("voice")


class VoiceRecognition:
    """
    Reconnaissance vocale offline avec Whisper.cpp.
    Supporte FR/EN/ES/DE.
    """
    
    def __init__(self, model_size: str = "small"):
        """
        Args:
            model_size: "tiny", "base", "small", "medium" (tiny = rapide, medium = précis)
        """
        self.model_size = model_size
        self.model_path = None
        self.language = "fr"
        self._load_model()
    
    def _load_model(self):
        """Charge le modèle Whisper."""
        # Chemin vers le modèle
        model_dir = Path("/opt/ai-rescue/models/whisper")
        model_file = model_dir / f"ggml-{self.model_size}.bin"
        
        if model_file.exists():
            self.model_path = str(model_file)
            log.info(f"Whisper model loaded: {self.model_size}")
        else:
            log.warning(f"Whisper model not found at {model_file}")
            # Fallback: utiliser Vosk ou autre
            self.model_path = None
    
    def set_language(self, lang: str):
        """Définit la langue de reconnaissance."""
        self.language = lang
    
    async def listen(self, duration: int = 10, silence_threshold: float = 0.03) -> str:
        """
        Écoute le micro et retourne le texte transcrit.
        
        Args:
            duration: Durée max d'écoute (secondes)
            silence_threshold: Seuil de silence pour arrêter
            
        Returns:
            Texte transcrit
        """
        log.info("Listening...")
        
        # Enregistrer l'audio
        audio_file = await self._record_audio(duration, silence_threshold)
        
        if not audio_file:
            return ""
        
        # Transcrire
        text = await self._transcribe(audio_file)
        
        # Nettoyer
        os.unlink(audio_file)
        
        log.info(f"Transcribed: {text[:50]}...")
        return text.strip()
    
    async def _record_audio(self, duration: int, silence_threshold: float) -> Optional[str]:
        """Enregistre l'audio du micro."""
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            # Utiliser arecord (ALSA) ou sox
            cmd = [
                "arecord",
                "-f", "S16_LE",
                "-r", "16000",
                "-c", "1",
                "-d", str(duration),
                temp_path
            ]
            
            # Enregistrer avec détection de silence
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Attendre la fin ou silence
            try:
                await asyncio.wait_for(proc.wait(), timeout=duration + 2)
            except asyncio.TimeoutError:
                proc.kill()
            
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                return temp_path
            else:
                return None
        
        except Exception as e:
            log.error(f"Audio recording failed: {e}")
            return None
    
    async def _transcribe(self, audio_file: str) -> str:
        """Transcrit l'audio en texte avec Whisper."""
        if not self.model_path:
            log.warning("Whisper not available, using fallback")
            return "[Voice recognition not available]"
        
        try:
            # Utiliser whisper.cpp
            cmd = [
                "/opt/ai-rescue/tools/whisper-main",
                "-m", self.model_path,
                "-f", audio_file,
                "-l", self.language,
                "-t", str(os.cpu_count() or 4),
                "--no-timestamps"
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=30)
            
            if result.returncode == 0:
                return stdout.decode("utf-8").strip()
            else:
                log.error(f"Whisper failed: {stderr.decode()}")
                return ""
        
        except Exception as e:
            log.error(f"Transcription failed: {e}")
            return ""


class TextToSpeech:
    """
    Synthèse vocale offline avec Piper TTS.
    Voix naturelle en français.
    """
    
    def __init__(self, voice: str = "fr-siwis-low"):
        """
        Args:
            voice: Nom de la voix (ex: "fr-siwis-low", "fr-mls-medium")
        """
        self.voice = voice
        self.model_path = None
        self.config_path = None
        self.speed = 1.0
        self.pitch = 1.0
        
        self._load_model()
    
    def _load_model(self):
        """Charge le modèle TTS."""
        model_dir = Path(f"/opt/ai-rescue/models/piper/{self.voice}")
        model_file = model_dir / f"{self.voice}.onnx"
        config_file = model_dir / f"{self.voice}.onnx.json"
        
        if model_file.exists() and config_file.exists():
            self.model_path = str(model_file)
            self.config_path = str(config_file)
            log.info(f"Piper TTS loaded: {self.voice}")
        else:
            log.warning(f"Piper model not found at {model_file}")
            self.model_path = None
    
    def set_speed(self, speed: float):
        """Définit la vitesse de parole (0.5 = lent, 2.0 = rapide)."""
        self.speed = max(0.5, min(2.0, speed))
    
    def set_pitch(self, pitch: float):
        """Définit la hauteur tonale (0.5 = grave, 2.0 = aigu)."""
        self.pitch = max(0.5, min(2.0, pitch))
    
    async def speak(self, text: str, output_device: str = "default") -> bool:
        """
        Prononce le texte.
        
        Args:
            text: Texte à prononcer
            output_device: Périphérique audio de sortie
            
        Returns:
            True si succès
        """
        if not text.strip():
            return False
        
        log.info(f"Speaking: {text[:50]}...")
        
        # Générer l'audio
        audio_file = await self._synthesize(text)
        
        if not audio_file:
            return False
        
        # Jouer l'audio
        success = await self._play_audio(audio_file, output_device)
        
        # Nettoyer
        if os.path.exists(audio_file):
            os.unlink(audio_file)
        
        return success
    
    async def _synthesize(self, text: str) -> Optional[str]:
        """Synthétise le texte en audio."""
        if not self.model_path:
            log.warning("Piper not available, using festival fallback")
            return await self._festival_fallback(text)
        
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            # Utiliser Piper
            cmd = [
                "/opt/ai-rescue/tools/piper",
                "-m", self.model_path,
                "-c", self.config_path,
                "-f", temp_path,
                "--length_scale", str(1.0 / self.speed),
            ]
            
            # Entrée texte via stdin
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=text.encode("utf-8")),
                timeout=30
            )
            
            if proc.returncode == 0 and os.path.getsize(temp_path) > 0:
                return temp_path
            else:
                log.error(f"Piper synthesis failed: {stderr.decode()}")
                return None
        
        except Exception as e:
            log.error(f"Synthesis failed: {e}")
            return None
    
    async def _festival_fallback(self, text: str) -> Optional[str]:
        """Fallback: utilise Festival TTS si Piper indisponible."""
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            cmd = ["festival", "--tts", temp_path]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await asyncio.wait_for(
                proc.communicate(input=text.encode("utf-8")),
                timeout=30
            )
            
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                return temp_path
            else:
                return None
        
        except Exception as e:
            log.error(f"Festival fallback failed: {e}")
            return None
    
    async def _play_audio(self, audio_file: str, output_device: str) -> bool:
        """Joue le fichier audio."""
        try:
            # Utiliser aplay (ALSA) ou paplay (PulseAudio)
            cmd = ["aplay", "-D", output_device, audio_file]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await asyncio.wait_for(proc.wait(), timeout=60)
            
            return proc.returncode == 0
        
        except Exception as e:
            log.error(f"Audio playback failed: {e}")
            return False


class VoiceInterface:
    """
    Interface vocale complète.
    Combine reconnaissance + synthèse.
    """
    
    def __init__(self, whisper_size: str = "small", piper_voice: str = "fr-siwis-low"):
        self.recognition = VoiceRecognition(whisper_size)
        self.synthesis = TextToSpeech(piper_voice)
        
        self.wake_word = "hey rescue"
        self.language = "fr"
        
        # Callbacks
        self.on_listening_start: Optional[Callable] = None
        self.on_listening_end: Optional[Callable] = None
        self.on_speaking_start: Optional[Callable] = None
        self.on_speaking_end: Optional[Callable] = None
    
    def set_language(self, lang: str):
        """Définit la langue (fr, en, es, de)."""
        self.language = lang
        self.recognition.set_language(lang)
    
    async def listen_and_transcribe(self) -> str:
        """Écoute et transcrit la parole."""
        if self.on_listening_start:
            self.on_listening_start()
        
        text = await self.recognition.listen(duration=15)
        
        if self.on_listening_end:
            self.on_listening_end(text)
        
        return text
    
    async def speak_response(self, text: str) -> bool:
        """Prononce une réponse."""
        if self.on_speaking_start:
            self.on_speaking_start(text)
        
        success = await self.synthesis.speak(text)
        
        if self.on_speaking_end:
            self.on_speaking_end()
        
        return success
    
    async def listen_for_wake_word(self) -> bool:
        """Écoute en continu pour le wake word."""
        # TODO: Implémenter écoute continue
        # Pour l'instant, juste vérifier si le texte contient le wake word
        text = await self.recognition.listen(duration=5)
        return self.wake_word in text.lower()


class VoiceDemo:
    """Démo simplifiée sans dépendances lourdes."""
    
    @staticmethod
    async def demo():
        """Démo du système vocal."""
        print("=== Démo Voice System ===\n")
        
        # Simulation
        print("🎤 Écoute en cours...")
        await asyncio.sleep(1)
        
        user_text = "Installe Windows 11"
        print(f"📝 Texte transcrit: \"{user_text}\"\n")
        
        print("🤖 IA: Je vais installer Windows 11 pour vous...")
        await asyncio.sleep(1)
        
        print("📥 Téléchargement de l'ISO...")
        for i in range(0, 101, 20):
            await asyncio.sleep(0.1)
            print(f"   Progression : {i}%")
        
        print("\n✅ Installation terminée !")
        print("\n🔊 Prononciation de la réponse...")
        await asyncio.sleep(1)
        print("(Audio joué)")


if __name__ == "__main__":
    asyncio.run(VoiceDemo.demo())
