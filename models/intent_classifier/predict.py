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

    def predict(self, text: str) -> dict:
        """
        Predict intent for a single text.

        Uses keyword override for ALREADY_PAID detection before ML model.
        Per Checkpoint 2 decision: 5-class model + ALREADY_PAID keyword override.

        Args:
            text: Borrower message text

        Returns:
            dict with keys: label, confidence, probabilities
        """
        # Keyword override for ALREADY_PAID
        if self._check_already_paid(text):
            # Build probabilities dict with model classes at 0 + ALREADY_PAID at 1.0
            probabilities = {
                self._le.inverse_transform([i])[0]: 0.0
                for i in range(len(self._le.classes_))
            }
            probabilities["ALREADY_PAID"] = 1.0
            return {
                "label": "ALREADY_PAID",
                "confidence": 0.95,
                "probabilities": probabilities,
            }

        proba = self._pipeline.predict_proba([text])[0]
        pred_idx = np.argmax(proba)
        label = self._le.inverse_transform([pred_idx])[0]
        confidence = float(proba[pred_idx])

        probabilities = {
            self._le.inverse_transform([i])[0]: float(p)
            for i, p in enumerate(proba)
        }
        # Add ALREADY_PAID with 0 probability for completeness
        probabilities["ALREADY_PAID"] = 0.0

        return {
            "label": label,
            "confidence": round(confidence, 4),
            "probabilities": {k: round(v, 4) for k, v in probabilities.items()},
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
