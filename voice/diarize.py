#!/usr/bin/env python3
"""
RecoveryBench — Speaker Diarization Module

Separates audio into speaker turns (Agent vs Borrower).

Primary backend: pyannote.audio (requires HuggingFace token).
Fallback: Sentence-alternation heuristic (unreliable — clearly warned).

Usage:
    from voice.diarize import Diarizer
    diarizer = Diarizer()
    turns = diarizer.diarize(audio_path, segments)
    # turns = [{"speaker": "Agent", "text": "..."}, {"speaker": "Borrower", "text": "..."}]

Requirements (for pyannote backend):
    pip install pyannote.audio torch
    export HF_TOKEN=<your-huggingface-token>
    # Accept pyannote terms at https://huggingface.co/pyannote/speaker-diarization-3.1

Fallback (no extra dependencies):
    Used automatically if pyannote is unavailable. Splits transcript
    into alternating Agent/Borrower turns by sentence — NOT accurate
    for real-world use.
"""

import os
import re
import logging
import warnings
from typing import List, Optional

logger = logging.getLogger(__name__)

# ── Pyannote availability check ──────────────────────────────────────────────

_PYANNOTE_AVAILABLE = False
_PYANNOTE_IMPORT_ERROR = None

try:
    from pyannote.audio import Pipeline as PyannotePipeline
    _PYANNOTE_AVAILABLE = True
except ImportError as e:
    _PYANNOTE_IMPORT_ERROR = str(e)


class Diarizer:
    """
    Speaker diarization with automatic backend selection.

    Attempts to use pyannote.audio for accurate neural diarization.
    Falls back to a simple heuristic if pyannote is unavailable.

    Attributes:
        backend (str): 'pyannote' or 'heuristic_fallback'.
    """

    def __init__(self, hf_token: Optional[str] = None):
        """
        Initialize the diarizer.

        Args:
            hf_token: HuggingFace API token for pyannote model access.
                      If not provided, reads from HF_TOKEN env var.
        """
        self.backend = "unknown"
        self._pipeline = None
        self._hf_token = hf_token or os.environ.get("HF_TOKEN", "")

        if _PYANNOTE_AVAILABLE and self._hf_token:
            self._init_pyannote()
        else:
            self._init_fallback()

    def _init_pyannote(self):
        """Initialize pyannote.audio pipeline."""
        try:
            self._pipeline = PyannotePipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=self._hf_token,
            )
            self.backend = "pyannote"
            logger.info("Diarizer initialized with pyannote backend")
        except Exception as e:
            logger.warning(
                f"pyannote initialization failed: {e}. "
                "Falling back to heuristic."
            )
            self._init_fallback()

    def _init_fallback(self):
        """Initialize fallback heuristic diarizer."""
        self.backend = "heuristic_fallback"
        reasons = []
        if not _PYANNOTE_AVAILABLE:
            reasons.append(f"pyannote.audio not installed ({_PYANNOTE_IMPORT_ERROR})")
        if not self._hf_token:
            reasons.append("HF_TOKEN not set")
        reason_str = "; ".join(reasons) if reasons else "pyannote init failed"

        warning_msg = (
            f"⚠ DIARIZATION FALLBACK ACTIVE — {reason_str}\n"
            "Speaker attribution uses a simple sentence-alternation heuristic.\n"
            "Results are NOT reliable for production use.\n"
            "For accurate diarization, install pyannote.audio and set HF_TOKEN:\n"
            "  pip install pyannote.audio torch\n"
            "  export HF_TOKEN=<your-huggingface-token>\n"
            "  # Accept terms at https://huggingface.co/pyannote/speaker-diarization-3.1"
        )
        warnings.warn(warning_msg, UserWarning, stacklevel=2)
        logger.warning(warning_msg)

    def diarize(
        self,
        audio_path: str,
        segments: Optional[List[dict]] = None,
    ) -> List[dict]:
        """
        Diarize audio into speaker turns.

        Args:
            audio_path: Path to audio file.
            segments: Whisper transcript segments (list of dicts with
                      'start', 'end', 'text' keys). Required for
                      heuristic fallback; used for alignment with pyannote.

        Returns:
            List of turn dicts, each with:
                - speaker (str): 'Agent' or 'Borrower'
                - text (str): Turn text
                - start (float): Start time in seconds
                - end (float): End time in seconds
        """
        if self.backend == "pyannote":
            return self._diarize_pyannote(audio_path, segments)
        else:
            return self._diarize_fallback(segments)

    # ── Pyannote backend ────────────────────────────────────────────────────

    def _diarize_pyannote(
        self,
        audio_path: str,
        segments: Optional[List[dict]] = None,
    ) -> List[dict]:
        """
        Diarize using pyannote.audio neural pipeline.

        Maps pyannote speaker labels to Agent/Borrower by assuming
        the first speaker detected is the Agent (debt collector
        typically initiates the call).
        """
        diarization = self._pipeline(audio_path, num_speakers=2)

        # Build speaker timeline
        speaker_timeline = []
        for turn, _, speaker_label in diarization.itertracks(yield_label=True):
            speaker_timeline.append({
                "start": turn.start,
                "end": turn.end,
                "speaker_id": speaker_label,
            })

        if not speaker_timeline:
            logger.warning("pyannote found no speaker turns — returning empty")
            return []

        # Map first speaker → Agent, second → Borrower
        speaker_ids = list(dict.fromkeys(
            t["speaker_id"] for t in speaker_timeline
        ))
        speaker_map = {}
        speaker_map[speaker_ids[0]] = "Agent"
        if len(speaker_ids) >= 2:
            speaker_map[speaker_ids[1]] = "Borrower"
        # Any extra speakers mapped to Borrower
        for sid in speaker_ids[2:]:
            speaker_map[sid] = "Borrower"

        # Align Whisper segments to pyannote turns
        if segments:
            return self._align_segments_to_turns(
                segments, speaker_timeline, speaker_map
            )
        else:
            # No Whisper segments — return timeline with empty text
            return [
                {
                    "speaker": speaker_map.get(t["speaker_id"], "Unknown"),
                    "text": "",
                    "start": round(t["start"], 2),
                    "end": round(t["end"], 2),
                }
                for t in speaker_timeline
            ]

    def _align_segments_to_turns(
        self,
        segments: List[dict],
        speaker_timeline: List[dict],
        speaker_map: dict,
    ) -> List[dict]:
        """
        Assign each Whisper segment to the pyannote speaker turn
        with the largest temporal overlap.
        """
        result = []
        for seg in segments:
            seg_start = seg["start"]
            seg_end = seg["end"]
            seg_mid = (seg_start + seg_end) / 2.0

            # Find speaker turn that contains the segment midpoint
            best_speaker = "Borrower"  # default
            for turn in speaker_timeline:
                if turn["start"] <= seg_mid <= turn["end"]:
                    best_speaker = speaker_map.get(
                        turn["speaker_id"], "Borrower"
                    )
                    break

            result.append({
                "speaker": best_speaker,
                "text": seg["text"],
                "start": round(seg_start, 2),
                "end": round(seg_end, 2),
            })

        # Merge consecutive turns by same speaker
        return self._merge_consecutive(result)

    # ── Heuristic fallback ──────────────────────────────────────────────────

    def _diarize_fallback(
        self,
        segments: Optional[List[dict]] = None,
    ) -> List[dict]:
        """
        Fallback heuristic diarization — sentence alternation.

        Splits transcript into sentences and alternates
        Agent → Borrower → Agent → ... starting with Agent.

        This is a rough approximation and NOT suitable for
        production evaluation. Clearly documented as such.
        """
        if not segments:
            return []

        # Flatten all segment text
        full_text = " ".join(seg["text"] for seg in segments).strip()
        if not full_text:
            return []

        # Split on sentence boundaries
        sentences = self._split_sentences(full_text)
        if not sentences:
            return []

        # Assign timings from segments proportionally
        total_chars = sum(len(s) for s in sentences)
        if total_chars == 0:
            return []

        total_duration = (
            segments[-1]["end"] - segments[0]["start"]
            if segments
            else 0.0
        )
        start_time = segments[0]["start"] if segments else 0.0

        turns = []
        current_time = start_time
        speakers = ["Agent", "Borrower"]

        for i, sentence in enumerate(sentences):
            char_ratio = len(sentence) / total_chars
            duration = total_duration * char_ratio
            end_time = current_time + duration

            turns.append({
                "speaker": speakers[i % 2],
                "text": sentence.strip(),
                "start": round(current_time, 2),
                "end": round(end_time, 2),
            })
            current_time = end_time

        return turns

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using punctuation and common patterns.
        Handles Hindi/English mixed text.
        """
        # Split on sentence-ending punctuation, keeping the delimiter
        parts = re.split(r'(?<=[.!?।])\s+', text)
        # Also split on comma followed by space for longer chunks
        sentences = []
        for part in parts:
            part = part.strip()
            if len(part) > 100:
                # Long chunk — split further on commas
                sub = re.split(r',\s+', part)
                sentences.extend(s.strip() for s in sub if s.strip())
            elif part:
                sentences.append(part)
        return sentences

    # ── Shared utilities ────────────────────────────────────────────────────

    @staticmethod
    def _merge_consecutive(turns: List[dict]) -> List[dict]:
        """Merge consecutive turns by the same speaker."""
        if not turns:
            return []
        merged = [turns[0].copy()]
        for turn in turns[1:]:
            if turn["speaker"] == merged[-1]["speaker"]:
                merged[-1]["text"] = (
                    merged[-1]["text"] + " " + turn["text"]
                ).strip()
                merged[-1]["end"] = turn["end"]
            else:
                merged.append(turn.copy())
        return merged

    def get_info(self) -> dict:
        """Return metadata about the diarizer configuration."""
        return {
            "backend": self.backend,
            "pyannote_available": _PYANNOTE_AVAILABLE,
            "hf_token_set": bool(self._hf_token),
        }
