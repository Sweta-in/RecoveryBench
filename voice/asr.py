#!/usr/bin/env python3
"""
RecoveryBench — Automatic Speech Recognition (ASR) Module

Transcribes audio files using OpenAI Whisper (free, runs locally).
Supports Hindi, English, Bengali, and Hinglish (code-mixed).

Usage:
    from voice.asr import ASREngine
    engine = ASREngine(model_size="base")
    result = engine.transcribe("path/to/audio.mp3")
    print(result["text"])
    print(result["language"])

Requirements:
    pip install openai-whisper torch
    - Whisper automatically downloads model weights on first use (~140MB for base)
    - Requires ffmpeg installed and on PATH for audio decoding
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ASREngine:
    """
    Whisper-based ASR engine for multilingual transcription.

    Supports three model sizes:
        - 'base' (default): ~140MB, fastest, adequate for clear speech
        - 'small': ~460MB, better accuracy for noisy/accented audio
        - 'medium': ~1.5GB, best accuracy but slow on CPU

    For CPU-only environments, 'base' is recommended.
    """

    # Map Whisper language codes to RecoveryBench language names
    LANGUAGE_MAP = {
        "en": "English",
        "hi": "Hindi",
        "bn": "Bengali",
        "ur": "Hinglish",  # Whisper sometimes detects Hinglish as Urdu
    }

    SUPPORTED_FORMATS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm"}

    def __init__(self, model_size: str = "base"):
        """
        Initialize the ASR engine.

        Args:
            model_size: Whisper model size — 'base', 'small', or 'medium'.

        Raises:
            RuntimeError: If openai-whisper is not installed.
        """
        self.model_size = model_size
        self._model = None
        self._load_model()

    def _load_model(self):
        """Load the Whisper model."""
        try:
            import whisper
        except ImportError:
            raise RuntimeError(
                "openai-whisper is not installed. Install it with:\n"
                "  pip install openai-whisper\n"
                "Also ensure ffmpeg is installed and on your PATH.\n"
                "  Windows: choco install ffmpeg  or  scoop install ffmpeg\n"
                "  macOS: brew install ffmpeg\n"
                "  Linux: sudo apt install ffmpeg"
            )

        logger.info(f"Loading Whisper model: {self.model_size}")
        start = time.time()
        self._model = whisper.load_model(self.model_size)
        elapsed = time.time() - start
        logger.info(f"Whisper model loaded in {elapsed:.1f}s")

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> dict:
        """
        Transcribe an audio file to text.

        Args:
            audio_path: Path to audio file (.mp3, .wav, .m4a, .flac, .ogg).
            language: Optional ISO-639-1 code to force language (e.g., 'hi', 'en').
                      If None, Whisper auto-detects the language.

        Returns:
            dict with keys:
                - text (str): Full transcription text.
                - language (str): Detected language name (e.g., 'Hindi', 'English').
                - language_code (str): ISO-639-1 code (e.g., 'hi', 'en').
                - segments (list): Timestamped segments from Whisper.
                - duration_seconds (float): Audio duration in seconds.
                - model_size (str): Which Whisper model was used.
                - transcription_time_seconds (float): Time taken to transcribe.

        Raises:
            FileNotFoundError: If audio file does not exist.
            ValueError: If audio format is not supported.
            RuntimeError: If transcription fails.
        """
        audio_path = Path(audio_path)

        # Validate file exists
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Validate format
        suffix = audio_path.suffix.lower()
        if suffix not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported audio format: {suffix}. "
                f"Supported: {', '.join(sorted(self.SUPPORTED_FORMATS))}"
            )

        # Transcribe
        logger.info(f"Transcribing: {audio_path.name}")
        start = time.time()

        transcribe_opts = {
            "fp16": False,  # CPU-safe (no fp16 on CPU)
        }
        if language:
            transcribe_opts["language"] = language

        try:
            result = self._model.transcribe(str(audio_path), **transcribe_opts)
        except Exception as e:
            raise RuntimeError(
                f"Transcription failed for {audio_path}: {e}\n"
                "Ensure ffmpeg is installed and the audio file is valid."
            )

        elapsed = time.time() - start

        # Extract language
        detected_lang_code = result.get("language", "en")
        detected_lang_name = self.LANGUAGE_MAP.get(
            detected_lang_code, "Hinglish"
        )

        # Estimate duration from segments
        segments = result.get("segments", [])
        duration = segments[-1]["end"] if segments else 0.0

        return {
            "text": result["text"].strip(),
            "language": detected_lang_name,
            "language_code": detected_lang_code,
            "segments": [
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip(),
                }
                for seg in segments
            ],
            "duration_seconds": round(duration, 2),
            "model_size": self.model_size,
            "transcription_time_seconds": round(elapsed, 2),
        }

    def get_model_info(self) -> dict:
        """Return metadata about the loaded model."""
        return {
            "model_size": self.model_size,
            "model_loaded": self._model is not None,
            "supported_formats": sorted(self.SUPPORTED_FORMATS),
        }
