#!/usr/bin/env python3
"""
RecoveryBench — Main Analysis Pipeline

Orchestrates all components to analyze debt collection conversations.

Usage:
    from pipeline.analyzer import RecoveryBenchAnalyzer

    analyzer = RecoveryBenchAnalyzer()
    result = analyzer.analyze_text("kal kar dunga payment")
    print(result)
"""

import sys
import json
import logging
from pathlib import Path
from typing import Optional

# Ensure project root is on path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)


class RecoveryBenchAnalyzer:
    """
    Main pipeline that orchestrates:
      1. Language detection
      2. Intent classification
      3. Promise extraction (Phase 3)
      4. Risk scoring (Phase 4)
      5. Compliance checking (Phase 5)
      6. Agent evaluation (Phase 6)
    """

    def __init__(self):
        self._intent_classifier = None
        self._promise_parser = None
        self._risk_scorer = None
        self._compliance_checker = None
        self._evaluator = None
        self._load_components()

    def _load_components(self):
        """Load available pipeline components."""
        # Intent classifier (Phase 2 — required)
        try:
            from models.intent_classifier.predict import IntentClassifier
            self._intent_classifier = IntentClassifier()
            logger.info("Intent classifier loaded")
        except Exception as e:
            logger.warning(f"Intent classifier not available: {e}")

        # Promise parser (Phase 3 — optional until built)
        try:
            from pipeline.promise_parser import PromiseParser
            self._promise_parser = PromiseParser()
            logger.info("Promise parser loaded")
        except ImportError:
            logger.debug("Promise parser not yet built (Phase 3)")

        # Risk scorer (Phase 4 — optional until built)
        try:
            from pipeline.risk_scorer import RiskScorer
            self._risk_scorer = RiskScorer()
            logger.info("Risk scorer loaded")
        except ImportError:
            logger.debug("Risk scorer not yet built (Phase 4)")

        # Compliance checker (Phase 5 — optional until built)
        try:
            from pipeline.compliance import ComplianceChecker
            self._compliance_checker = ComplianceChecker()
            logger.info("Compliance checker loaded")
        except ImportError:
            logger.debug("Compliance checker not yet built (Phase 5)")

        # Agent evaluator (Phase 6 — optional until built)
        try:
            from pipeline.evaluator import AgentEvaluator
            self._evaluator = AgentEvaluator()
            logger.info("Agent evaluator loaded")
        except ImportError:
            logger.debug("Agent evaluator not yet built (Phase 6)")

    def _detect_language(self, text: str) -> str:
        """Detect language of input text."""
        try:
            from langdetect import detect
            lang_code = detect(text)
            lang_map = {
                "en": "English",
                "hi": "Hindi",
                "bn": "Bengali",
            }
            detected = lang_map.get(lang_code, "Hinglish")
            return detected
        except Exception:
            return "Unknown"

    def analyze_text(
        self,
        borrower_message: str,
        agent_response: Optional[str] = None,
    ) -> dict:
        """
        Analyze a text-based debt collection interaction.

        Args:
            borrower_message: The borrower's message text.
            agent_response: Optional agent response to evaluate.

        Returns:
            Unified analysis JSON dict.
        """
        result = {}

        # 1. Language detection
        result["language"] = self._detect_language(borrower_message)

        # 2. Intent classification
        if self._intent_classifier:
            intent_result = self._intent_classifier.predict(borrower_message)
            result["repayment_intent"] = intent_result["label"]
            result["intent_confidence"] = intent_result["confidence"]
        else:
            result["repayment_intent"] = "UNKNOWN"
            result["intent_confidence"] = 0.0

        # 3. Promise extraction
        if self._promise_parser:
            promise_result = self._promise_parser.extract(borrower_message)
            result["promise_to_pay"] = promise_result.get("promise_to_pay", False)
            result["payment_window_days"] = promise_result.get("payment_window_days")
        else:
            result["promise_to_pay"] = False
            result["payment_window_days"] = None

        # 4. Risk scoring
        if self._risk_scorer:
            risk_features = {
                "intent": result["repayment_intent"],
                "has_promise": result["promise_to_pay"],
                "payment_window_days": result.get("payment_window_days") or 0,
                "message_length": len(borrower_message),
                "exclamation_count": borrower_message.count("!"),
                "question_count": borrower_message.count("?"),
                "caps_ratio": sum(1 for c in borrower_message if c.isupper()) / max(len(borrower_message), 1),
                "dispute_keywords": 0,
                "hostile_keywords": 0,
            }
            result["risk_score"] = self._risk_scorer.score(risk_features)
        else:
            result["risk_score"] = None

        # 5. Sentiment (simple heuristic until we have a proper model)
        result["sentiment"] = self._simple_sentiment(borrower_message)

        # 6. Recommended action
        result["recommended_action"] = self._recommend_action(result)

        # 7. Compliance check (on agent response)
        if agent_response and self._compliance_checker:
            compliance_result = self._compliance_checker.check(agent_response)
            result["compliance"] = compliance_result
        else:
            result["compliance"] = {
                "compliant": True,
                "violations": [],
                "severity": "none",
            }

        # 8. Agent evaluation
        if agent_response and self._evaluator:
            try:
                eval_result = self._evaluator.evaluate(
                    borrower_message=borrower_message,
                    intent=result["repayment_intent"],
                    confidence=result["intent_confidence"],
                    agent_response=agent_response,
                )
                result["agent_eval"] = eval_result
            except Exception as e:
                logger.warning(f"Agent evaluation failed: {e}")
                result["agent_eval"] = None
        else:
            result["agent_eval"] = None

        return result

    def analyze_audio(self, audio_path: str) -> dict:
        """
        Analyze an audio debt collection conversation.

        Args:
            audio_path: Path to audio file (.wav or .mp3).

        Returns:
            Unified analysis JSON dict including transcript.
        """
        try:
            from voice.pipeline import VoicePipeline
            VOICE_AVAILABLE = True
        except ImportError:
            VOICE_AVAILABLE = False

        if not VOICE_AVAILABLE:
            raise RuntimeError(
                "Voice pipeline not available. Run Checkpoint 8 first."
            )

        vp = VoicePipeline()
        voice_result = vp.analyze(audio_path)
        return voice_result

    def _simple_sentiment(self, text: str) -> str:
        """Simple keyword-based sentiment as placeholder."""
        text_lower = text.lower()
        negative_words = [
            "angry", "stop", "harass", "fraud", "cheat", "never",
            "gussa", "band karo", "pareshan", "pagal",
        ]
        positive_words = [
            "pay", "payment", "will do", "sure", "definitely",
            "kar dunga", "karunga", "debo", "haan",
        ]

        neg_count = sum(1 for w in negative_words if w in text_lower)
        pos_count = sum(1 for w in positive_words if w in text_lower)

        if neg_count > pos_count:
            return "negative"
        elif pos_count > neg_count:
            return "positive"
        return "neutral"

    def _recommend_action(self, analysis: dict) -> str:
        """Generate recommended action based on analysis."""
        intent = analysis.get("repayment_intent", "UNKNOWN")
        has_promise = analysis.get("promise_to_pay", False)
        window = analysis.get("payment_window_days")

        recommendations = {
            "LIKELY_PAY": (
                f"follow-up after {max(window - 2, 1)} days"
                if has_promise and window
                else "follow-up after 5 days"
            ),
            "NEEDS_REMINDER": "send reminder in 2-3 days with clear EMI details",
            "DISPUTE": "escalate to dispute resolution team for verification",
            "HIGH_RISK": "escalate to senior agent; consider restructuring options",
            "VAGUE": "send clarification message with specific payment options",
            "ALREADY_PAID": "verify payment records and confirm receipt to borrower",
        }
        return recommendations.get(intent, "review manually")

    def __repr__(self):
        components = []
        if self._intent_classifier:
            components.append("intent")
        if self._promise_parser:
            components.append("promise")
        if self._risk_scorer:
            components.append("risk")
        if self._compliance_checker:
            components.append("compliance")
        if self._evaluator:
            components.append("evaluator")
        return f"RecoveryBenchAnalyzer(components={components})"
