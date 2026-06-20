#!/usr/bin/env python3
"""
RecoveryBench — Voice Pipeline Orchestrator

End-to-end audio analysis:
  audio file → ASR (Whisper) → diarization → text analysis → full JSON

Usage:
    from voice.pipeline import VoicePipeline
    vp = VoicePipeline()
    result = vp.analyze("path/to/audio.mp3")
    print(result["transcript"])
    print(result["repayment_intent"])

Requirements:
    - openai-whisper + ffmpeg (for ASR)
    - pyannote.audio + HF_TOKEN (optional, for accurate diarization)
    - All RecoveryBench pipeline components (intent classifier, etc.)
"""

import sys
import time
import logging
from pathlib import Path
from typing import Optional

# Ensure project root is on path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)


class VoicePipeline:
    """
    Orchestrates the full voice analysis pipeline:

    1. ASR (Whisper) — transcribe audio to text with timestamps
    2. Diarization — separate speakers (Agent / Borrower)
    3. Text Analysis — run RecoveryBenchAnalyzer.analyze_text()
       on the borrower's combined utterances

    The final output merges voice-specific metadata (transcript,
    speakers, timings) with the standard RecoveryBench analysis JSON.
    """

    def __init__(
        self,
        whisper_model_size: str = "base",
        hf_token: Optional[str] = None,
    ):
        """
        Initialize the voice pipeline.

        Args:
            whisper_model_size: Whisper model size ('base', 'small', 'medium').
            hf_token: HuggingFace token for pyannote diarization.
        """
        self._asr = None
        self._diarizer = None
        self._analyzer = None
        self._whisper_model_size = whisper_model_size
        self._hf_token = hf_token
        self._init_components()

    def _init_components(self):
        """Load all pipeline components."""
        # ASR engine
        from voice.asr import ASREngine
        self._asr = ASREngine(model_size=self._whisper_model_size)
        logger.info(f"ASR loaded: Whisper {self._whisper_model_size}")

        # Diarizer
        from voice.diarize import Diarizer
        self._diarizer = Diarizer(hf_token=self._hf_token)
        logger.info(f"Diarizer loaded: {self._diarizer.backend}")

        # Text analyzer
        from pipeline.analyzer import RecoveryBenchAnalyzer
        self._analyzer = RecoveryBenchAnalyzer()
        logger.info("RecoveryBenchAnalyzer loaded")

    def analyze(self, audio_path: str) -> dict:
        """
        Full end-to-end voice analysis.

        Args:
            audio_path: Path to audio file (.mp3, .wav, etc.).

        Returns:
            dict containing:
                - transcript (str): Full raw transcript
                - language (str): Detected language
                - speakers (list): Diarized speaker turns
                - borrower_text (str): Combined borrower utterances
                - agent_text (str): Combined agent utterances
                - duration_seconds (float): Audio duration
                - asr_model (str): Whisper model used
                - diarization_backend (str): 'pyannote' or 'heuristic_fallback'
                - processing_time_seconds (float): Total pipeline time
                - repayment_intent (str): Classified intent
                - intent_confidence (float): Classification confidence
                - risk_score (float): Risk score
                - promise_to_pay (bool): Whether a payment promise was detected
                - payment_window_days (int|None): Promised payment window
                - sentiment (str): Detected sentiment
                - recommended_action (str): Suggested next step
                - compliance (dict): Compliance check result
                - agent_eval (dict|None): Agent evaluation result
        """
        pipeline_start = time.time()
        audio_path_obj = Path(audio_path)

        if not audio_path_obj.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # ── Step 1: ASR — Transcribe ────────────────────────────────────
        logger.info(f"Step 1/3: Transcribing {audio_path_obj.name}")
        asr_result = self._asr.transcribe(str(audio_path))

        transcript = asr_result["text"]
        segments = asr_result["segments"]
        detected_language = asr_result["language"]
        duration = asr_result["duration_seconds"]

        logger.info(
            f"Transcription complete: {len(transcript)} chars, "
            f"language={detected_language}, duration={duration}s"
        )

        # ── Step 2: Diarization — Speaker separation ───────────────────
        logger.info("Step 2/3: Diarizing speakers")
        turns = self._diarizer.diarize(str(audio_path), segments=segments)

        # Extract borrower and agent text
        borrower_texts = [
            t["text"] for t in turns if t["speaker"] == "Borrower"
        ]
        agent_texts = [
            t["text"] for t in turns if t["speaker"] == "Agent"
        ]

        borrower_text = " ".join(borrower_texts).strip()
        agent_text = " ".join(agent_texts).strip()

        # If diarization produced no borrower text (e.g., single speaker),
        # treat the entire transcript as borrower input
        if not borrower_text:
            logger.warning(
                "No borrower text identified — treating full "
                "transcript as borrower input"
            )
            borrower_text = transcript
            agent_text = ""

        logger.info(
            f"Diarization complete: {len(turns)} turns, "
            f"borrower={len(borrower_text)} chars, "
            f"agent={len(agent_text)} chars"
        )

        # ── Step 3: Text Analysis ──────────────────────────────────────
        logger.info("Step 3/3: Running text analysis")
        analysis = self._analyzer.analyze_text(
            borrower_message=borrower_text,
            agent_response=agent_text if agent_text else None,
        )

        pipeline_elapsed = time.time() - pipeline_start

        # ── Build unified result ───────────────────────────────────────
        result = {
            # Voice-specific metadata
            "transcript": transcript,
            "speakers": [
                {
                    "speaker": t["speaker"],
                    "text": t["text"],
                    "start": t["start"],
                    "end": t["end"],
                }
                for t in turns
            ],
            "borrower_text": borrower_text,
            "agent_text": agent_text,
            "duration_seconds": duration,
            "asr_model": f"whisper-{self._whisper_model_size}",
            "diarization_backend": self._diarizer.backend,
            "processing_time_seconds": round(pipeline_elapsed, 2),
            # Merge in all text analysis fields
            "language": analysis.get("language", detected_language),
            "repayment_intent": analysis.get("repayment_intent", "UNKNOWN"),
            "intent_confidence": analysis.get("intent_confidence", 0.0),
            "risk_score": analysis.get("risk_score"),
            "promise_to_pay": analysis.get("promise_to_pay", False),
            "payment_window_days": analysis.get("payment_window_days"),
            "sentiment": analysis.get("sentiment", "neutral"),
            "recommended_action": analysis.get(
                "recommended_action", "review manually"
            ),
            "compliance": analysis.get("compliance", {
                "compliant": True,
                "violations": [],
                "severity": "none",
            }),
            "agent_eval": analysis.get("agent_eval"),
        }

        logger.info(
            f"Voice pipeline complete in {pipeline_elapsed:.2f}s — "
            f"intent={result['repayment_intent']}, "
            f"risk={result['risk_score']}"
        )

        return result

    def get_info(self) -> dict:
        """Return metadata about the pipeline configuration."""
        info = {
            "asr": self._asr.get_model_info() if self._asr else None,
            "diarizer": (
                self._diarizer.get_info() if self._diarizer else None
            ),
            "analyzer_loaded": self._analyzer is not None,
        }
        return info
