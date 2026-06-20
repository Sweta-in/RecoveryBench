#!/usr/bin/env python3
"""
Tests for the Intent Classifier model.
"""

import os
import sys
import pickle
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd


CLASSES = ["LIKELY_PAY", "NEEDS_REMINDER", "DISPUTE", "HIGH_RISK", "VAGUE", "ALREADY_PAID"]
MODEL_DIR = Path(__file__).parent.parent / "models" / "intent_classifier"
DATA_DIR = Path(__file__).parent.parent / "data"


@pytest.fixture(scope="module")
def model():
    """Load trained model pipeline."""
    model_path = MODEL_DIR / "model.pkl"
    if not model_path.exists():
        pytest.skip("Model not trained yet")
    with open(model_path, "rb") as f:
        return pickle.load(f)


@pytest.fixture(scope="module")
def label_encoder():
    """Load label encoder."""
    le_path = MODEL_DIR / "label_encoder.pkl"
    if not le_path.exists():
        pytest.skip("Label encoder not found")
    with open(le_path, "rb") as f:
        return pickle.load(f)


@pytest.fixture(scope="module")
def test_data():
    """Load test data."""
    test_path = DATA_DIR / "test.csv"
    if not test_path.exists():
        pytest.skip("Test data not found")
    return pd.read_csv(test_path)


class TestModelExists:
    """Test that model artifacts exist."""

    def test_model_file_exists(self):
        assert (MODEL_DIR / "model.pkl").exists(), "model.pkl not found"

    def test_label_encoder_exists(self):
        assert (MODEL_DIR / "label_encoder.pkl").exists(), "label_encoder.pkl not found"

    def test_config_exists(self):
        assert (MODEL_DIR / "config.json").exists(), "config.json not found"


class TestModelInference:
    """Test model inference on known examples."""

    def test_predict_english_likely_pay(self, model, label_encoder):
        texts = ["I will pay by Friday", "Payment confirmed for next week"]
        preds = model.predict(texts)
        pred_labels = label_encoder.inverse_transform(preds)
        assert all(p == "LIKELY_PAY" for p in pred_labels), f"Expected LIKELY_PAY, got {pred_labels}"

    def test_predict_english_dispute(self, model, label_encoder):
        texts = ["This amount is wrong", "I never took this loan"]
        preds = model.predict(texts)
        pred_labels = label_encoder.inverse_transform(preds)
        assert all(p == "DISPUTE" for p in pred_labels), f"Expected DISPUTE, got {pred_labels}"

    def test_predict_english_high_risk(self, model, label_encoder):
        texts = ["Stop calling me", "I will file a complaint"]
        preds = model.predict(texts)
        pred_labels = label_encoder.inverse_transform(preds)
        assert all(p == "HIGH_RISK" for p in pred_labels), f"Expected HIGH_RISK, got {pred_labels}"

    def test_predict_english_already_paid(self, model, label_encoder):
        """ALREADY_PAID is handled via keyword override in IntentClassifier, not the raw model."""
        from models.intent_classifier.predict import IntentClassifier
        clf = IntentClassifier()
        texts = ["I already paid this last week", "Check your records, payment was done"]
        for text in texts:
            result = clf.predict(text)
            assert result["label"] == "ALREADY_PAID", f"Expected ALREADY_PAID, got {result['label']} for '{text}'"

    def test_predict_hindi(self, model, label_encoder):
        texts = ["Kal payment kar dunga"]
        preds = model.predict(texts)
        pred_labels = label_encoder.inverse_transform(preds)
        assert pred_labels[0] in CLASSES, f"Invalid class: {pred_labels[0]}"

    def test_predict_hinglish(self, model, label_encoder):
        texts = ["Bhai already transfer kar diya tha, check karo"]
        preds = model.predict(texts)
        pred_labels = label_encoder.inverse_transform(preds)
        assert pred_labels[0] in CLASSES, f"Invalid class: {pred_labels[0]}"

    def test_predict_returns_probabilities(self, model):
        """Raw model has 5 classes (ALREADY_PAID is keyword override, not in ML model)."""
        texts = ["I will pay tomorrow"]
        proba = model.predict_proba(texts)
        ml_classes = [c for c in CLASSES if c != "ALREADY_PAID"]
        assert proba.shape == (1, len(ml_classes)), f"Expected shape (1, {len(ml_classes)}), got {proba.shape}"
        assert abs(proba.sum() - 1.0) < 0.01, f"Probabilities don't sum to 1: {proba.sum()}"

    def test_predict_empty_string(self, model, label_encoder):
        """Model should handle empty/short input gracefully."""
        texts = ["", " ", "ok"]
        preds = model.predict(texts)
        pred_labels = label_encoder.inverse_transform(preds)
        assert all(p in CLASSES for p in pred_labels)


class TestModelQuality:
    """Test model quality metrics."""

    def test_macro_f1_above_threshold(self, model, label_encoder, test_data):
        """Evaluate F1 only on the 5 ML classes (ALREADY_PAID is keyword override)."""
        from sklearn.metrics import f1_score
        # Filter out ALREADY_PAID rows — not handled by ML model
        ml_data = test_data[test_data["label"] != "ALREADY_PAID"]
        X_test = ml_data["text"].values
        y_test = label_encoder.transform(ml_data["label"].values)
        y_pred = model.predict(X_test)
        f1 = f1_score(y_test, y_pred, average="macro")
        assert f1 >= 0.50, f"Macro F1 {f1:.4f} is below 0.50 threshold"

    def test_all_classes_predicted(self, model, label_encoder, test_data):
        """ML model should predict all 5 trained classes. ALREADY_PAID tested separately via keyword override."""
        # Filter to ML-only data
        ml_data = test_data[test_data["label"] != "ALREADY_PAID"]
        X_test = ml_data["text"].values
        y_pred = model.predict(X_test)
        pred_labels = label_encoder.inverse_transform(y_pred)
        predicted_classes = set(pred_labels)
        ml_classes = [c for c in CLASSES if c != "ALREADY_PAID"]
        for cls in ml_classes:
            assert cls in predicted_classes, f"Class {cls} never predicted"

    def test_already_paid_keyword_override(self):
        """ALREADY_PAID should be detected via keyword override in IntentClassifier."""
        from models.intent_classifier.predict import IntentClassifier
        clf = IntentClassifier()
        test_texts = [
            "I already paid last week",
            "Payment done yesterday",
            "Check your records, I paid already",
        ]
        for text in test_texts:
            result = clf.predict(text)
            assert result["label"] == "ALREADY_PAID", f"Expected ALREADY_PAID for '{text}', got {result['label']}"

    def test_inference_latency(self, model, test_data):
        """Inference should be fast for sklearn models."""
        import time
        X_test = test_data["text"].values
        start = time.time()
        model.predict(X_test)
        elapsed = time.time() - start
        mean_ms = (elapsed / len(X_test)) * 1000
        assert mean_ms < 10, f"Mean latency {mean_ms:.2f}ms exceeds 10ms threshold"
