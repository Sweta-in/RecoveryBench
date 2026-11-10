#!/usr/bin/env python3
"""
RecoveryBench — Intent Classifier Inference Module

Provides a simple API for loading and using the trained intent classifier.

Usage:
    from models.intent_classifier.predict import IntentClassifier
    
    clf = IntentClassifier()
    result = clf.predict("I will pay by Friday")
    # Returns: {"label": "LIKELY_PAY", "confidence": 0.92, "probabilities": {...}}
"""

import os
import json
import pickle
from pathlib import Path
from typing import Optional

import numpy as np


class IntentClassifier:
    """Wrapper around the trained intent classification pipeline."""

    CLASSES = ["LIKELY_PAY", "NEEDS_REMINDER", "DISPUTE", "HIGH_RISK", "VAGUE", "ALREADY_PAID"]

    # Keywords that trigger ALREADY_PAID override (case-insensitive)
    _ALREADY_PAID_KEYWORDS = [
        "already paid", "paid already", "payment done", "payment kar diya",
        "kar diya hai", "kar chuka", "de diya", "de chuka", "bhej diya",
        "transfer kar diya", "paid last week", "paid yesterday",
        "already transferred", "already sent", "paise de diye",
        "paisa de diya", "check your records", "receipt hai",
        "transaction complete", "diye the", "dia tha", "diya tha",
        "pay kar diya", "jama kar diya", "jama kiya", "paid this",
        "diye hain", "de diya hai", "bhej diya hai", "transfer ho gaya",
    ]

    # Keywords that trigger HARDSHIP override (case-insensitive).
    # The ML classifier has no HARDSHIP class (trained on 6 classes: ALREADY_PAID,
    # DISPUTE, HIGH_RISK, LIKELY_PAY, NEEDS_REMINDER, VAGUE). Hardship utterances
    # fall into DISPUTE/HIGH_RISK due to character n-gram overlap with refusal language.
    # This keyword layer directly fixes Bug 3: "I can't afford to pay this month"
    # was classified as DISPUTE instead of HARDSHIP.
    _HARDSHIP_KEYWORDS = [
        # English — ability-to-pay expressions
        "can't afford", "cannot afford", "cant afford",
        "can't make the payment", "cannot make the payment",
        "no money", "don't have money", "dont have money", "no funds",
        "not enough money", "insufficient funds",
        "financial difficulty", "financial hardship", "financial trouble",
        "financial crisis", "financial problem", "financial issue",
        "struggling to pay", "struggle to pay", "struggling with payment",
        "hard to pay", "difficult to pay", "trouble paying",
        "can't pay right now", "cannot pay right now",
        "don't have the funds", "dont have the funds",
        "tight on money", "tight financially",
        "going through a tough time", "tough situation", "difficult situation",
        "lost my job", "lost my income", "job loss",
        "medical bills", "medical expenses", "hospital bills",
        # Hindi / Hinglish — inability to pay
        "afford nahi", "afford nahi kar",
        "paise nahi hain", "paisa nahi hai", "paise nahi",
        "paisa nahi hai mere paas", "mere paas paisa nahi",
        "takat nahi", "aukat nahi",
        "mushkil hai", "bahut mushkil", "dikkat ho rahi", "takleef hai",
        "nahi de sakta", "nahi de sakti", "de nahi sakta", "de nahi sakti",
        "dene mein dikkat", "dene mein mushkil", "dene mein taklif",
        "abhi nahi de sakta", "abhi paisa nahi", "abhi funds nahi",
        "halat theek nahi", "situation theek nahi", "condition theek nahi",
        "paisa nahi hai abhi", "abhi afford nahi kar sakta",
        # Bengali / Hinglish overlap
        "pay korte parchi na", "pay korte pari na",
        "taka nei", "taka nai",
    ]

    # Keywords that trigger PARTIAL_PAYMENT override (case-insensitive).
    # The ML classifier has no PARTIAL_PAYMENT class. Partial-payment offers
    # ("I can pay 6,000 now, rest later") get misclassified as ALREADY_PAID or
    # LIKELY_PAY because of n-gram overlap with full-payment language.
    # This keyword layer directly fixes Bug 1 from the Arjun Mehta test call:
    # "I can pay 6,000 now. Rest, I can pay after" → ALREADY_PAID → verification-pause.
    _PARTIAL_PAYMENT_KEYWORDS = [
        # English — partial/installment patterns
        "can pay part", "pay part of", "partial payment", "part payment",
        "pay some now", "pay some of", "pay half", "paid half",
        "pay in parts", "paid part",
        "pay in instalments", "pay in installments",
        "rest later", "rest i can pay", "rest, i can pay",
        "rest can pay", "rest after",
        "remaining later", "remaining after", "remaining i can",
        "pay now rest", "now and rest", "now rest later",
        "i can pay after", "can pay after",
        "some now some later", "half now half later",
        "part now part later", "part now",
        "installment plan", "instalment plan",
        "pay in emi", "convert to emi", "emi option",
        # Hindi / Hinglish — partial payment patterns
        "baaki baad mein", "baki baad mein", "baki bad mein",
        "aadha de", "aadha abhi", "kuch de sakta", "kuch de sakti",
        "kuch abhi", "thoda thoda", "thoda abhi",
        "installment mein", "kist mein", "kist se",
        "abhi itna", "abhi ye de",
        # Bengali / Banglish
        "kichuta kichuta", "baki ta", "baki portion",
    ]

    def __init__(self, model_dir: Optional[str] = None):
        if model_dir is None:
            model_dir = Path(__file__).parent
        else:
            model_dir = Path(model_dir)

        model_path = model_dir / "model.pkl"
        le_path = model_dir / "label_encoder.pkl"

        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at {model_path}. Run train.py first.")

        with open(model_path, "rb") as f:
            self._pipeline = pickle.load(f)
        with open(le_path, "rb") as f:
            self._le = pickle.load(f)

        # Load config if available
        config_path = model_dir / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                self._config = json.load(f)
        else:
            self._config = {}

    def _check_already_paid(self, text: str) -> bool:
        """Check if text matches ALREADY_PAID keyword override patterns."""
        text_lower = text.lower().strip()
        return any(kw in text_lower for kw in self._ALREADY_PAID_KEYWORDS)

    def _check_partial_payment(self, text: str) -> bool:
        """Check if text matches PARTIAL_PAYMENT keyword override patterns.

        The ML model has no PARTIAL_PAYMENT class — this keyword layer is
        the primary mechanism for correctly routing partial-payment offers
        to the resolveHardship() settlement-proposal engine path.
        """
        text_lower = text.lower().strip()
        return any(kw in text_lower for kw in self._PARTIAL_PAYMENT_KEYWORDS)

    def _check_hardship(self, text: str) -> bool:
        """Check if text matches HARDSHIP keyword override patterns.

        The ML model has no HARDSHIP class — this keyword layer is the
        primary (and currently only) mechanism for correctly routing
        hardship utterances to the resolveHardship() engine path.
        """
        text_lower = text.lower().strip()
        return any(kw in text_lower for kw in self._HARDSHIP_KEYWORDS)

    def predict(self, text: str) -> dict:
        """
        Predict intent for a single text.

        Phase B: ML model is primary (6-class including ALREADY_PAID).
        Keyword layer is a secondary confidence signal:
          - If keywords match and ML agrees → boost confidence
          - If keywords match but ML disagrees → log disagreement, use keyword
            with moderate confidence (0.80)
          - If no keyword match → use ML prediction directly

        Args:
            text: Borrower message text

        Returns:
            dict with keys: label, confidence, probabilities, keyword_match
        """
        keyword_match = self._check_already_paid(text)
        hardship_match = self._check_hardship(text)
        partial_payment_match = self._check_partial_payment(text)

        # Get ML prediction
        proba = self._pipeline.predict_proba([text])[0]
        pred_idx = np.argmax(proba)
        ml_label = self._le.inverse_transform([pred_idx])[0]
        ml_confidence = float(proba[pred_idx])

        probabilities = {
            self._le.inverse_transform([i])[0]: float(p)
            for i, p in enumerate(proba)
        }

        # Ensure ALREADY_PAID key exists in probabilities
        if "ALREADY_PAID" not in probabilities:
            probabilities["ALREADY_PAID"] = 0.0

        # ── PARTIAL_PAYMENT override (checked FIRST — most specific) ──────────
        # The ML classifier has no PARTIAL_PAYMENT class. Partial-payment offers
        # like "I can pay 6,000 now, rest later" get misclassified as ALREADY_PAID
        # (n-gram overlap) or LIKELY_PAY (payment commitment language). This
        # keyword layer overrides to PARTIAL_PAYMENT regardless of ML output
        # (except DISPUTE — a disputed partial offer should stay disputed).
        #
        # Checked before HARDSHIP: a partial offer WITH hardship language
        # ("I can only pay part, things are tough") should route as PARTIAL_PAYMENT
        # — the settlement engine handles both the partial offer and hardship context.
        _PARTIAL_PAYMENT_OVERRIDE_FROM = {"LIKELY_PAY", "ALREADY_PAID", "HIGH_RISK", "VAGUE", "NEEDS_REMINDER"}
        if partial_payment_match and ml_label in _PARTIAL_PAYMENT_OVERRIDE_FROM:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                f"PARTIAL_PAYMENT_KEYWORD_OVERRIDE: ml={ml_label} (conf={ml_confidence:.4f}), "
                f"overriding to PARTIAL_PAYMENT, text='{text[:80]}'"
            )
            return {
                "label": "PARTIAL_PAYMENT",
                "confidence": 0.82,
                "probabilities": {**probabilities, "PARTIAL_PAYMENT": 0.82},
                "keyword_match": False,
                "hardship_keyword_match": False,
                "partial_payment_keyword_match": True,
            }

        # ── HARDSHIP override (checked before ALREADY_PAID) ──────────────────
        # The ML classifier has no HARDSHIP class. When hardship keywords match
        # and the ML returned a non-commitment class (DISPUTE, HIGH_RISK, VAGUE,
        # NEEDS_REMINDER), override to HARDSHIP. This fixes Bug 3: "I can't afford
        # to pay this month" was classified as DISPUTE.
        #
        # Note: if keywords say HARDSHIP but ML says LIKELY_PAY or ALREADY_PAID,
        # we trust the ML — explicit payment intent/confirmation overrides hardship.
        _NON_COMMITMENT_CLASSES = {"DISPUTE", "HIGH_RISK", "VAGUE", "NEEDS_REMINDER"}
        if hardship_match and ml_label in _NON_COMMITMENT_CLASSES:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                f"HARDSHIP_KEYWORD_OVERRIDE: ml={ml_label} (conf={ml_confidence:.4f}), "
                f"overriding to HARDSHIP, text='{text[:80]}'"
            )
            return {
                "label": "HARDSHIP",
                "confidence": 0.82,
                "probabilities": {**probabilities, "HARDSHIP": 0.82},
                "keyword_match": False,
                "hardship_keyword_match": True,
            }

        # ── ALREADY_PAID override ────────────────────────────────────────────
        # Secondary signal logic
        if keyword_match:
            if ml_label == "ALREADY_PAID":
                # Agreement: ML and keywords both say ALREADY_PAID → boost confidence
                final_label = "ALREADY_PAID"
                final_confidence = min(ml_confidence + 0.05, 0.99)
            else:
                # Disagreement: keywords say ALREADY_PAID but ML disagrees
                # Trust keywords (they're high-precision) but with moderate confidence
                import logging
                logger = logging.getLogger(__name__)
                logger.info(
                    f"KEYWORD_ML_DISAGREEMENT: keywords=ALREADY_PAID, "
                    f"ml={ml_label} (conf={ml_confidence:.4f}), text='{text[:80]}'"
                )
                final_label = "ALREADY_PAID"
                final_confidence = 0.80
                # Adjust probabilities to reflect override
                probabilities["ALREADY_PAID"] = 0.80
        else:
            # No keyword match — use ML prediction directly
            final_label = ml_label
            final_confidence = ml_confidence

        return {
            "label": final_label,
            "confidence": round(final_confidence, 4),
            "probabilities": {k: round(v, 4) for k, v in probabilities.items()},
            "keyword_match": keyword_match,
            "hardship_keyword_match": False,
        }

    def predict_batch(self, texts: list[str]) -> list[dict]:
        """
        Predict intents for a batch of texts.

        Args:
            texts: List of borrower message texts

        Returns:
            List of prediction dicts
        """
        probas = self._pipeline.predict_proba(texts)
        results = []
        for proba in probas:
            pred_idx = np.argmax(proba)
            label = self._le.inverse_transform([pred_idx])[0]
            confidence = float(proba[pred_idx])
            probabilities = {
                self._le.inverse_transform([i])[0]: float(p)
                for i, p in enumerate(proba)
            }
            results.append({
                "label": label,
                "confidence": round(confidence, 4),
                "probabilities": {k: round(v, 4) for k, v in probabilities.items()},
            })
        return results

    @property
    def model_info(self) -> dict:
        """Return model metadata."""
        return self._config

    def __repr__(self):
        return f"IntentClassifier(classes={self.CLASSES})"
