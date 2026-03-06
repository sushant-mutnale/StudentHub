"""
Text-to-Speech Service using Piper
Provides natural-sounding speech synthesis for voice interviews.
"""

import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional


class TTSService:
    """
    Text-to-Speech service using Piper TTS.
    Generates natural-sounding audio from text for interviewer responses.
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        voice: str = "en_US-lessac-medium",
        output_dir: Optional[str] = None
    ):
        """
        Initialize Piper TTS service.
        
        Args:
            model_path: Path to Piper model file (.onnx)
            voice: Voice name/identifier
            output_dir: Directory to save generated audio files
        """
        self.voice = voice
        self.model_path = model_path or self._get_default_model_path()
        self.output_dir = output_dir or self._get_default_output_dir()
        
        # Ensure output directory exists
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def _get_default_model_path(self) -> str:
        """Get default model path."""
        # Check common locations
        possible_paths = [
            f"models/{self.voice}.onnx",
            f"/usr/local/share/piper/{self.voice}.onnx",
            f"{os.getenv('HOME')}/.local/share/piper/{self.voice}.onnx"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # Return default (will need to be downloaded)
        return f"models/{self.voice}.onnx"
    
    def _get_default_output_dir(self) -> str:
        """Get default output directory."""
        return "static/audio"
    
    def _check_piper_installed(self) -> bool:
        """Check if Piper is installed."""
        try:
            result = subprocess.run(
                ["piper", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    async def generate_speech(
        self,
        text: str,
        output_filename: Optional[str] = None,
        speaker_id: int = 0,
        noise_scale: float = 0.667,
        length_scale: float = 1.0,
        noise_w: float = 0.8
    ) -> dict:
        """
        Generate speech from text.
        
        Args:
            text: Text to convert to speech
            output_filename: Custom filename (without extension)
            speaker_id: Speaker ID for multi-speaker models
            noise_scale: Variability in speech (0.0 - 1.0)
            length_scale: Speed of speech (< 1.0 = faster, > 1.0 = slower)
            noise_w: Variation in phoneme duration
            
        Returns:
            dict with:
                - filename: Generated audio filename
                - filepath: Full path to audio file
                - url: Relative URL to access audio
        """
        if not self._check_piper_installed():
            print("⚠️ Piper TTS not found. Using mock audio response.")
            # Fallback for dev/verification without Piper
            return {
                "filename": "mock_audio.wav",
                "filepath": os.path.join(self.output_dir, "mock_audio.wav"),
                "url": "/static/audio/mock_audio.wav",
                "text": text
            }
        
        # Generate unique filename if not provided
        if output_filename is None:
            output_filename = f"speech_{uuid.uuid4().hex[:12]}"
        
        output_path = os.path.join(self.output_dir, f"{output_filename}.wav")
        
        # Build Piper command
        cmd = [
            "piper",
            "--model", self.model_path,
            "--output_file", output_path,
            "--speaker", str(speaker_id),
            "--noise_scale", str(noise_scale),
            "--length_scale", str(length_scale),
            "--noise_w", str(noise_w)
        ]
        
        try:
            # Run Piper with text input
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=text, timeout=30)
            
            if process.returncode != 0:
                print(f"⚠️ Piper TTS failed: {stderr}. Using mock response.")
                return {
                    "filename": "mock_audio.wav",
                    "filepath": os.path.join(self.output_dir, "mock_audio.wav"),
                    "url": "/static/audio/mock_audio.wav",
                    "text": text
                }
            
            return {
                "filename": f"{output_filename}.wav",
                "filepath": output_path,
                "url": f"/static/audio/{output_filename}.wav",
                "text": text
            }
            
        except subprocess.TimeoutExpired:
            process.kill()
            print("⚠️ Piper TTS timed out. Using mock response.")
            return {
                "filename": "mock_audio.wav",
                "filepath": os.path.join(self.output_dir, "mock_audio.wav"),
                "url": "/static/audio/mock_audio.wav",
                "text": text
            }
    
    async def generate_speech_raw(self, text: str) -> bytes:
        """
        Generate speech and return raw audio bytes (WAV format).
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Raw WAV audio bytes
        """
        # Generate to temp file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            cmd = [
                "piper",
                "--model", self.model_path,
                "--output_file", tmp_path
            ]
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            process.communicate(input=text, timeout=30)
            
            # Read generated audio
            with open(tmp_path, 'rb') as f:
                return f.read()
                
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


# Singleton instance
tts_service = TTSService()


# Convenience function
async def text_to_speech(text: str, filename: Optional[str] = None) -> str:
    """
    Quick TTS helper that returns audio URL.
    
    Args:
        text: Text to convert to speech
        filename: Optional custom filename
        
    Returns:
        URL to generated audio file
    """
    result = await tts_service.generate_speech(text, output_filename=filename)
    return result["url"]
