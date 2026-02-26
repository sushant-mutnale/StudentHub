"""
Speech-to-Text Service using Faster-Whisper
Provides high-accuracy transcription with 4x speed improvement over standard Whisper.
"""

import os
import tempfile
from typing import Optional
from pathlib import Path


class STTService:
    """
    Speech-to-Text service using Faster-Whisper.
    Supports both CPU and GPU inference with quantization for efficiency.
    """
    
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8"
    ):
        """
        Initialize Faster-Whisper STT service.
        
        Args:
            model_size: Model size (tiny, base, small, medium, large-v2, large-v3)
            device: Device to run on ('cpu' or 'cuda')
            compute_type: Computation type ('int8', 'int8_float16', 'float16')
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None
        
    def _load_model(self):
        """Lazy load the Whisper model."""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type
                )
                print(f"Loaded Faster-Whisper model: {self.model_size} on {self.device}")
            except ImportError:
                raise ImportError(
                    "faster-whisper not installed. Install with: pip install faster-whisper"
                )
    
    async def transcribe(
        self,
        audio_file,
        language: Optional[str] = "en",
        beam_size: int = 5,
        vad_filter: bool = True
    ) -> dict:
        """
        Transcribe audio file to text.
        
        Args:
            audio_file: Path to audio file or file-like object
            language: Language code (e.g., 'en', 'es', 'fr') or None for auto-detect
            beam_size: Beam size for decoding (higher = more accurate but slower)
            vad_filter: Apply voice activity detection to filter silence
            
        Returns:
            dict with:
                - text: Full transcription
                - segments: List of segments with timestamps
                - language: Detected language
        """
        self._load_model()
        
        # Handle file-like objects
        if hasattr(audio_file, 'read'):
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
                tmp.write(audio_file.read())
                audio_path = tmp.name
        else:
            audio_path = str(audio_file)
        
        try:
            # Transcribe
            segments, info = self._model.transcribe(
                audio_path,
                language=language,
                beam_size=beam_size,
                vad_filter=vad_filter
            )
            
            # Collect results
            all_text = []
            segment_list = []
            
            for segment in segments:
                all_text.append(segment.text)
                segment_list.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip()
                })
            
            result = {
                "text": " ".join(all_text).strip(),
                "segments": segment_list,
                "language": info.language,
                "language_probability": info.language_probability
            }
            
            return result
            
        finally:
            # Clean up temp file
            if hasattr(audio_file, 'read') and os.path.exists(audio_path):
                os.unlink(audio_path)
    
    async def transcribe_streaming(self, audio_chunks):
        """
        Transcribe audio chunks in streaming mode (future implementation).
        Currently returns aggregated transcription.
        """
        # TODO: Implement streaming transcription
        # For now, combine chunks and transcribe
        raise NotImplementedError("Streaming transcription not yet implemented")


# Singleton instance
stt_service = STTService()


# Convenience function
async def transcribe_audio(audio_file, language: str = "en") -> str:
    """
    Quick transcription helper.
    
    Args:
        audio_file: Audio file to transcribe
        language: Language code
        
    Returns:
        Transcribed text
    """
    result = await stt_service.transcribe(audio_file, language=language)
    return result["text"]
