#!/usr/bin/env python3
"""
RecoveryBench — Risk Scorer

Produces a 0–1 risk score from conversation features using XGBoost.
Trained on synthetic labels derived from intent class base scores.

Features:
  - intent_encoded: 0-4 ordinal encoding of intent class
  - has_promise: binary (1 if promise_to_pay is True)
  - payment_window_days: 0 if no promise, else capped at 90
  - message_length: character count of borrower message
  - exclamation_count: number of '!'
  - question_count: number of '?'
  - caps_ratio: proportion of uppercase characters
  - dispute_keywords: count of dispute-related keywords
  - hostile_keywords: count of hostile keywords

Usage:
    from pipeline.risk_scorer import RiskScorer

    scorer = RiskScorer()
    score = scorer.score({
        'intent': 'LIKELY_PAY',
        'has_promise': True,
        'payment_window_days': 7,
        'message_length': 40,
        'exclamation_count': 0,
        'question_count': 0,
        'caps_ratio': 0.05,
        'dispute_keywords': 0,
        'hostile_keywords': 0,
    })
    print(f"Risk score: {score:.3f}")
"""

import os
import sys
import json
import logging
import numpy as np
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
MODEL_DIR = PROJECT_ROOT / "models" / "risk_scorer"


# Intent encoding: ordered by increasing risk
INTENT_ENCODING = {
    "LIKELY_PAY": 0,
    "ALREADY_PAID": 0,  # Same risk level as LIKELY_PAY
    "NEEDS_REMINDER": 1,
    "VAGUE": 2,
    "DISPUTE": 3,
    "HIGH_RISK": 4,
}

# Base risk scores by intent class (for synthetic training labels)
RISK_BASE = {
    "LIKELY_PAY": 0.15,
    "ALREADY_PAID": 0.10,
    "NEEDS_REMINDER": 0.40,
    "VAGUE": 0.60,
    "DISPUTE": 0.75,
    "HIGH_RISK": 0.92,
}

# Feature names in order
FEATURE_NAMES = [
    "intent_encoded",
    "has_promise",
    "payment_window_days",
    "message_length",
    "exclamation_count",
    "question_count",
    "caps_ratio",
    "dispute_keywords",
    "hostile_keywords",
]

# Dispute-related keywords
DISPUTE_KEYWORDS = [
    "galat", "wrong", "not mine", "check", "error", "mistake",
    "incorrect", "mera nahi", "bhul", "verify", "fraud", "fake",
    "overcharged", "zyada", "extra", "already paid", "paid already",
]

# Hostile keywords
HOSTILE_KEYWORDS = [
    "court", "police", "fraud", "report", "lawyer", "legal",
    "sue", "complaint", "consumer forum", "rbi", "harassment",
    "threat", "abuse", "harass", "marunga", "dhamki",
    "goli", "maar", "udhar", "chor",
]


class RiskScorer:
    """
    XGBoost-based risk scorer for debt collection conversations.

    Produces a 0-1 risk score where:
      - 0.0-0.3: Low risk (likely to pay)
      - 0.3-0.6: Medium risk (needs follow-up)
      - 0.6-0.8: High risk (dispute/evasion)
      - 0.8-1.0: Critical risk (hostile/avoidant)
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize RiskScorer.

        Args:
            model_path: Path to saved XGBoost model JSON.
                        Defaults to models/risk_scorer/xgb_model.json
        """
        self._model = None
        self._model_path = Path(model_path) if model_path else MODEL_DIR / "xgb_model.json"

        if self._model_path.exists():
            self._load_model()
        else:
            logger.info("No pre-trained model found. Training new model...")
            self._train_and_save()

    def _load_model(self):
        """Load a pre-trained XGBoost model from disk."""
        try:
            import xgboost as xgb
            self._model = xgb.XGBRegressor()
            self._model.load_model(str(self._model_path))
            logger.info(f"Risk scorer model loaded from {self._model_path}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise RuntimeError(
                f"Failed to load risk scorer model from {self._model_path}: {e}\n"
                "Try deleting the model file and re-initializing to retrain."
            )

    def _generate_training_data(self) -> tuple:
        """
        Generate synthetic training data from the dataset.

        Uses the training CSV if available, otherwise generates
        synthetic examples covering all intent classes.

        Returns:
            (X, y) — feature matrix and risk labels
        """
        import pandas as pd

        train_path = PROJECT_ROOT / "data" / "train.csv"

        if train_path.exists():
            logger.info(f"Generating training data from {train_path}")
            df = pd.read_csv(train_path)
        else:
            logger.info("No training CSV found — generating synthetic examples")
            df = self._generate_synthetic_df()

        X_list = []
        y_list = []

        np.random.seed(42)

        for _, row in df.iterrows():
            text = str(row["text"])
            label = row["label"]
            text_lower = text.lower()

            # Extract features from text
            intent_encoded = INTENT_ENCODING.get(label, 2)

            # Simple promise detection for feature engineering
            promise_keywords = [
                "will pay", "kar dunga", "karunga", "debo", "korbo",
                "bhej dunga", "tomorrow", "kal", "next week", "agle hafte",
                "pakka", "promise", "definitely",
            ]
            has_promise = 1 if any(kw in text_lower for kw in promise_keywords) else 0

            # Simple temporal extraction for window
            payment_window = 0
            if has_promise:
                if any(w in text_lower for w in ["kal", "tomorrow", "kaal"]):
                    payment_window = 1
                elif any(w in text_lower for w in ["parso", "2 din", "do din", "in 2 days"]):
                    payment_window = 2
                elif any(w in text_lower for w in ["teen din", "3 din", "in 3 days"]):
                    payment_window = 3
                elif any(w in text_lower for w in ["hafte", "week", "shoptah"]):
                    payment_window = 7
                elif any(w in text_lower for w in ["month", "mahine", "mash"]):
                    payment_window = 30
                elif any(w in text_lower for w in ["salary", "beton"]):
                    payment_window = 10
                else:
                    payment_window = 5  # Default if promise but no temporal

            # Cap at 90
            payment_window = min(payment_window, 90)

            message_length = len(text)
            exclamation_count = text.count("!")
            question_count = text.count("?")
            caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)

            dispute_kw_count = sum(1 for kw in DISPUTE_KEYWORDS if kw in text_lower)
            hostile_kw_count = sum(1 for kw in HOSTILE_KEYWORDS if kw in text_lower)

            features = [
                intent_encoded,
                has_promise,
                payment_window,
                message_length,
                exclamation_count,
                question_count,
                caps_ratio,
                dispute_kw_count,
                hostile_kw_count,
            ]
            X_list.append(features)

            # Synthetic risk label: base score + noise + feature adjustments
            base_risk = RISK_BASE.get(label, 0.5)
            noise = np.random.normal(0, 0.08)

            # Adjustments based on features
            if has_promise:
                base_risk -= 0.05
            if payment_window > 0 and payment_window <= 7:
                base_risk -= 0.03
            if exclamation_count >= 3:
                base_risk += 0.05
            if caps_ratio > 0.3:
                base_risk += 0.05
            if hostile_kw_count > 0:
                base_risk += 0.08 * hostile_kw_count
            if dispute_kw_count > 0:
                base_risk += 0.04 * dispute_kw_count

            risk_label = np.clip(base_risk + noise, 0.01, 0.99)
            y_list.append(risk_label)

        X = np.array(X_list, dtype=np.float32)
        y = np.array(y_list, dtype=np.float32)

        logger.info(f"Training data: {X.shape[0]} samples, {X.shape[1]} features")
        return X, y

    def _generate_synthetic_df(self):
        """Generate a minimal synthetic DataFrame for training when no CSV exists."""
        import pandas as pd

        rows = []
        intents = ["LIKELY_PAY", "NEEDS_REMINDER", "VAGUE", "DISPUTE", "HIGH_RISK"]
        examples = {
            "LIKELY_PAY": [
                "kal kar dunga payment", "I will pay tomorrow",
                "pakka next week bhej dunga", "I promise to pay by month end",
                "abhi transfer karta hun", "will pay definitely",
                "salary aane do, de dunga", "weekend tak kar deta hun",
            ],
            "NEEDS_REMINDER": [
                "haan yaad hai", "oh I forgot about it",
                "remind me please", "acha theek hai",
                "batao kitna dena hai", "when is it due",
                "send me details again", "yaad dilana",
            ],
            "VAGUE": [
                "hmm", "dekhte hain", "ok", "thik hai",
                "maybe", "pata nahi", "sochta hun",
                "let me think", "acha", "haan haan",
            ],
            "DISPUTE": [
                "yeh galat hai amount", "this is not my loan check records",
                "I already paid verify", "wrong amount bhai",
                "mera loan nahi hai", "I dispute this amount",
                "check karo records", "error hai yeh",
            ],
            "HIGH_RISK": [
                "stop calling me!!!", "I will report to police",
                "fraud company hai ye", "COURT JAAUNGA MAIN",
                "harass mat karo!!!", "consumer forum jaaunga",
                "band karo phone bahut ho gaya!!!", "lawyer se baat karo",
            ],
        }

        for intent in intents:
            for text in examples[intent]:
                rows.append({"text": text, "label": intent, "language": "Mixed", "split": "train"})

        return pd.DataFrame(rows)

    def _train_and_save(self):
        """Train a new XGBoost model and save to disk."""
        try:
            import xgboost as xgb
        except ImportError:
            raise RuntimeError(
                "xgboost is required for the risk scorer.\n"
                "Install with: python -m pip install xgboost"
            )

        X, y = self._generate_training_data()

        # Train XGBoost regressor
        self._model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42,
            objective="reg:squarederror",
        )

        self._model.fit(X, y, verbose=False)

        # Save model
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        self._model.save_model(str(self._model_path))
        logger.info(f"Risk scorer model saved to {self._model_path}")

        # Save feature names
        feature_names_path = MODEL_DIR / "feature_names.json"
        with open(feature_names_path, "w") as f:
            json.dump(FEATURE_NAMES, f, indent=2)

        # Save feature importance
        importance_path = MODEL_DIR / "feature_importance.json"
        importances = dict(zip(FEATURE_NAMES, self._model.feature_importances_.tolist()))
        with open(importance_path, "w") as f:
            json.dump(importances, f, indent=2)
        logger.info(f"Feature importance saved to {importance_path}")

        # Generate SHAP analysis if available
        self._generate_shap(X)

    def _generate_shap(self, X: np.ndarray):
        """Generate SHAP feature importance plot if shap is available."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        shap_path = MODEL_DIR / "shap_importance.png"
        shap_summary_path = MODEL_DIR / "shap_summary.json"

        # Attempt SHAP-based analysis
        try:
            import shap
            import pandas as pd

            # Convert to DataFrame with feature names for SHAP compatibility
            X_df = pd.DataFrame(X, columns=FEATURE_NAMES)

            explainer = shap.TreeExplainer(
                self._model,
                feature_perturbation="tree_path_dependent",
            )
            shap_values = explainer.shap_values(X_df)

            # Summary bar plot
            plt.figure(figsize=(10, 6))
            shap.summary_plot(
                shap_values, X_df,
                feature_names=FEATURE_NAMES,
                plot_type="bar",
                show=False,
            )
            plt.title("Risk Scorer — SHAP Feature Importance")
            plt.tight_layout()
            plt.savefig(str(shap_path), dpi=150, bbox_inches="tight")
            plt.close()
            logger.info(f"SHAP importance plot saved to {shap_path}")

            # Save SHAP summary values
            mean_abs_shap = np.abs(shap_values).mean(axis=0)
            shap_summary = dict(zip(FEATURE_NAMES, mean_abs_shap.tolist()))
            with open(shap_summary_path, "w") as f:
                json.dump(shap_summary, f, indent=2)
            logger.info(f"SHAP summary saved to {shap_summary_path}")
            return

        except ImportError:
            logger.debug("shap not available — falling back to XGBoost importance")
        except Exception as e:
            logger.warning(f"SHAP analysis failed ({e}) — falling back to XGBoost importance")

        # Fallback: generate importance plot from XGBoost native feature_importances_
        try:
            if self._model is None:
                logger.warning("Model is None — cannot generate feature importance plot")
                return
            importances = self._model.feature_importances_
            sorted_idx = np.argsort(importances)
            sorted_names = [FEATURE_NAMES[i] for i in sorted_idx]
            sorted_vals = importances[sorted_idx]

            plt.figure(figsize=(10, 6))
            plt.barh(range(len(sorted_names)), sorted_vals, color="#4C72B0", edgecolor="white")
            plt.yticks(range(len(sorted_names)), sorted_names)
            plt.xlabel("Feature Importance (XGBoost gain)")
            plt.title("Risk Scorer — Feature Importance (XGBoost)")
            plt.tight_layout()
            plt.savefig(str(shap_path), dpi=150, bbox_inches="tight")
            plt.close()
            logger.info(f"XGBoost importance plot saved to {shap_path}")

            # Save as SHAP-format JSON for downstream compatibility
            shap_summary = dict(zip(FEATURE_NAMES, importances.tolist()))
            with open(shap_summary_path, "w") as f:
                json.dump(shap_summary, f, indent=2)
            logger.info(f"Feature importance summary saved to {shap_summary_path}")

        except Exception as e2:
            logger.warning(f"Fallback importance plot also failed: {e2}")

    def score(self, features: dict) -> float:
        """
        Compute risk score from conversation features.

        Args:
            features: Dict with keys matching FEATURE_NAMES.
                Required keys:
                  - intent: str (class label)
                  - has_promise: bool
                  - payment_window_days: int
                  - message_length: int
                  - exclamation_count: int
                  - question_count: int
                  - caps_ratio: float
                  - dispute_keywords: int
                  - hostile_keywords: int

        Returns:
            Risk score as float in [0, 1].
        """
        if self._model is None:
            raise RuntimeError("Risk scorer model not loaded or trained.")

        # Encode intent
        intent = features.get("intent", "VAGUE")
        intent_encoded = INTENT_ENCODING.get(intent, 2)

        # Build feature vector
        x = np.array([[
            intent_encoded,
            1 if features.get("has_promise", False) else 0,
            min(features.get("payment_window_days", 0) or 0, 90),
            features.get("message_length", 0),
            features.get("exclamation_count", 0),
            features.get("question_count", 0),
            features.get("caps_ratio", 0.0),
            features.get("dispute_keywords", 0),
            features.get("hostile_keywords", 0),
        ]], dtype=np.float32)

        # Predict and clip to [0, 1]
        raw_score = float(self._model.predict(x)[0])
        return float(np.clip(raw_score, 0.0, 1.0))

    def train(self):
        """
        Public method to (re-)train the XGBoost model and save artifacts.

        This regenerates the model, feature importance, and SHAP plot.
        Useful for retraining after data updates or to generate
        missing artifacts like the SHAP importance plot.
        """
        logger.info("Training risk scorer model...")
        self._train_and_save()
        logger.info("Training complete.")

    def score_batch(self, features_list: list) -> list:
        """
        Score a batch of conversations.

        Args:
            features_list: List of feature dicts (same format as score()).

        Returns:
            List of risk scores.
        """
        return [self.score(f) for f in features_list]

    def get_risk_band(self, score: float) -> str:
        """
        Map a risk score to a human-readable band.

        Args:
            score: Risk score in [0, 1].

        Returns:
            'low', 'medium', 'high', or 'critical'.
        """
        if score < 0.3:
            return "low"
        elif score < 0.6:
            return "medium"
        elif score < 0.8:
            return "high"
        else:
            return "critical"

    def get_feature_importance(self) -> dict:
        """Return feature importance from the trained model."""
        if self._model is None:
            return {}
        return dict(zip(FEATURE_NAMES, self._model.feature_importances_.tolist()))

    @staticmethod
    def extract_features_from_text(text: str, intent: str, promise_result: dict) -> dict:
        """
        Helper to extract all risk features from text + pipeline outputs.

        Args:
            text: Borrower message text.
            intent: Classified intent label.
            promise_result: Output from PromiseParser.extract().

        Returns:
            Feature dict ready for score().
        """
        text_lower = text.lower()
        return {
            "intent": intent,
            "has_promise": promise_result.get("promise_to_pay", False),
            "payment_window_days": promise_result.get("payment_window_days") or 0,
            "message_length": len(text),
            "exclamation_count": text.count("!"),
            "question_count": text.count("?"),
            "caps_ratio": sum(1 for c in text if c.isupper()) / max(len(text), 1),
            "dispute_keywords": sum(1 for kw in DISPUTE_KEYWORDS if kw in text_lower),
            "hostile_keywords": sum(1 for kw in HOSTILE_KEYWORDS if kw in text_lower),
        }


if __name__ == "__main__":
    """Quick verification: train and test the risk scorer."""
    logging.basicConfig(level=logging.INFO)

    scorer = RiskScorer()

    test_cases = [
        {
            "name": "LIKELY_PAY (promise, 7 days)",
            "features": {
                "intent": "LIKELY_PAY",
                "has_promise": True,
                "payment_window_days": 7,
                "message_length": 40,
                "exclamation_count": 0,
                "question_count": 0,
                "caps_ratio": 0.05,
                "dispute_keywords": 0,
                "hostile_keywords": 0,
            },
        },
        {
            "name": "NEEDS_REMINDER (no promise)",
            "features": {
                "intent": "NEEDS_REMINDER",
                "has_promise": False,
                "payment_window_days": 0,
                "message_length": 20,
                "exclamation_count": 0,
                "question_count": 1,
                "caps_ratio": 0.0,
                "dispute_keywords": 0,
                "hostile_keywords": 0,
            },
        },
        {
            "name": "VAGUE (short response)",
            "features": {
                "intent": "VAGUE",
                "has_promise": False,
                "payment_window_days": 0,
                "message_length": 5,
                "exclamation_count": 0,
                "question_count": 0,
                "caps_ratio": 0.0,
                "dispute_keywords": 0,
                "hostile_keywords": 0,
            },
        },
        {
            "name": "DISPUTE (keywords present)",
            "features": {
                "intent": "DISPUTE",
                "has_promise": False,
                "payment_window_days": 0,
                "message_length": 60,
                "exclamation_count": 1,
                "question_count": 1,
                "caps_ratio": 0.1,
                "dispute_keywords": 2,
                "hostile_keywords": 0,
            },
        },
        {
            "name": "HIGH_RISK (hostile, caps)",
            "features": {
                "intent": "HIGH_RISK",
                "has_promise": False,
                "payment_window_days": 0,
                "message_length": 80,
                "exclamation_count": 3,
                "question_count": 0,
                "caps_ratio": 0.4,
                "dispute_keywords": 0,
                "hostile_keywords": 2,
            },
        },
    ]

    print("\n" + "=" * 60)
    print("Risk Scorer — Verification")
    print("=" * 60)

    scores = {}
    for tc in test_cases:
        score = scorer.score(tc["features"])
        band = scorer.get_risk_band(score)
        scores[tc["features"]["intent"]] = score
        print(f"  {tc['name']:40s} → {score:.3f} ({band})")

    # Ordering check
    print("\n--- Ordering Check ---")
    order_ok = (
        scores["LIKELY_PAY"] < scores["NEEDS_REMINDER"]
        < scores["VAGUE"] < scores["DISPUTE"]
        < scores["HIGH_RISK"]
    )
    if order_ok:
        print("  ✓ LIKELY_PAY < NEEDS_REMINDER < VAGUE < DISPUTE < HIGH_RISK")
        print("  Ordering check: PASS")
    else:
        print("  ✗ Ordering VIOLATED!")
        for intent, s in sorted(scores.items(), key=lambda x: x[1]):
            print(f"    {intent}: {s:.3f}")
        print("  Ordering check: FAIL")

    # Feature importance
    print("\n--- Feature Importance ---")
    importance = scorer.get_feature_importance()
    for feat, imp in sorted(importance.items(), key=lambda x: -x[1]):
        print(f"  {feat:25s}: {imp:.4f}")
