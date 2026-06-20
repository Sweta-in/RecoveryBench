#!/usr/bin/env python3
"""
RecoveryBench — Intent Classifier (Phase 2)

Trains a multilingual intent classifier for debt collection borrower messages.
Uses scikit-learn with TF-IDF features as the baseline (no paid APIs, no GPU required).

Supports 6 classes:
    LIKELY_PAY, NEEDS_REMINDER, DISPUTE, HIGH_RISK, VAGUE, ALREADY_PAID

Outputs:
    - models/intent_classifier/model.pkl — trained model pipeline
    - models/intent_classifier/label_encoder.pkl — label encoder
    - models/intent_classifier/config.json — model metadata
    - models/results/classification_report.txt
    - models/results/confusion_matrix.png
    - models/results/training_curves.png
    - models/results/per_language_report.txt
    - analysis/hard_examples.csv
"""

import os
import sys
import json
import time
import pickle
import logging
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    accuracy_score,
)
from sklearn.pipeline import Pipeline
from sklearn.model_selection import learning_curve

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Constants
CLASSES = ["LIKELY_PAY", "NEEDS_REMINDER", "DISPUTE", "HIGH_RISK", "VAGUE", "ALREADY_PAID"]
LANGUAGES = ["English", "Hindi", "Bengali", "Hinglish"]
RANDOM_SEED = 42

# Color palette for plots
CLASS_COLORS = {
    "LIKELY_PAY": "#2ecc71",
    "NEEDS_REMINDER": "#f39c12",
    "DISPUTE": "#e74c3c",
    "HIGH_RISK": "#9b59b6",
    "VAGUE": "#3498db",
    "ALREADY_PAID": "#1abc9c",
}

plt.rcParams.update({
    "figure.facecolor": "#f8f9fa",
    "axes.facecolor": "#ffffff",
    "axes.edgecolor": "#dee2e6",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 11,
    "font.family": "sans-serif",
})


def load_data(data_dir: Path):
    """Load train/val/test CSVs."""
    train = pd.read_csv(data_dir / "train.csv")
    val = pd.read_csv(data_dir / "val.csv")
    test = pd.read_csv(data_dir / "test.csv")

    logger.info(f"Loaded: train={len(train)}, val={len(val)}, test={len(test)}")
    return train, val, test


def preprocess_text(text: str) -> str:
    """Basic text preprocessing."""
    if not isinstance(text, str):
        return ""
    text = text.strip()
    text = text.lower()
    # Remove repeated chars (e.g., "!!!!" -> "!!")
    import re
    text = re.sub(r'(.)\1{3,}', r'\1\1', text)
    return text


def train_model(train_df: pd.DataFrame, val_df: pd.DataFrame):
    """Train TF-IDF + Logistic Regression intent classifier."""
    logger.info("\n=== Training Intent Classifier ===")

    # Prepare data
    X_train = train_df["text"].apply(preprocess_text).values
    y_train = train_df["label"].values
    X_val = val_df["text"].apply(preprocess_text).values
    y_val = val_df["label"].values

    # Encode labels — fit only on classes present in training data
    # This avoids a mismatch when some classes (e.g. ALREADY_PAID) have
    # 0 training examples, which would cause pipeline.classes_ to skip
    # those indices while the label encoder retains them.
    train_classes = sorted(train_df["label"].unique())
    le = LabelEncoder()
    le.fit(train_classes)
    logger.info(f"Training classes ({len(train_classes)}): {train_classes}")

    # Check for classes in val that aren't in train (they'll be evaluated as errors)
    val_only_classes = set(val_df["label"].unique()) - set(train_classes)
    if val_only_classes:
        logger.warning(f"Classes in val but NOT in train: {val_only_classes}")
        logger.warning("These classes cannot be predicted by the model.")
        # Filter val to only include trainable classes for metric computation
        val_df_filtered = val_df[val_df["label"].isin(train_classes)].copy()
    else:
        val_df_filtered = val_df

    y_train_enc = le.transform(y_train)
    X_val = val_df_filtered["text"].apply(preprocess_text).values
    y_val = val_df_filtered["label"].values
    y_val_enc = le.transform(y_val)

    # Build pipeline: TF-IDF + Logistic Regression
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            analyzer="char_wb",       # char n-grams at word boundaries — works well for multilingual
            ngram_range=(2, 5),       # character n-grams from bigrams to 5-grams
            max_features=50000,
            sublinear_tf=True,
            min_df=2,
            max_df=0.95,
        )),
        ("clf", LogisticRegression(
            C=1.0,
            max_iter=2000,
            solver="lbfgs",
            multi_class="multinomial",
            class_weight="balanced",
            random_state=RANDOM_SEED,
        )),
    ])

    # Train
    start_time = time.time()
    pipeline.fit(X_train, y_train_enc)
    train_time = time.time() - start_time
    logger.info(f"Training completed in {train_time:.2f}s")

    # Evaluate on validation
    y_val_pred = pipeline.predict(X_val)
    val_f1 = f1_score(y_val_enc, y_val_pred, average="macro")
    val_acc = accuracy_score(y_val_enc, y_val_pred)
    logger.info(f"Validation: accuracy={val_acc:.4f}, macro F1={val_f1:.4f}")

    # Evaluate on training (to check overfitting)
    y_train_pred = pipeline.predict(X_train)
    train_f1 = f1_score(y_train_enc, y_train_pred, average="macro")
    train_acc = accuracy_score(y_train_enc, y_train_pred)
    logger.info(f"Train: accuracy={train_acc:.4f}, macro F1={train_f1:.4f}")

    return pipeline, le, {
        "train_time": train_time,
        "train_accuracy": train_acc,
        "train_f1": train_f1,
        "val_accuracy": val_acc,
        "val_f1": val_f1,
    }


def evaluate_model(pipeline, le, test_df: pd.DataFrame, results_dir: Path, analysis_dir: Path):
    """Full evaluation on test set."""
    logger.info("\n=== Evaluating on Test Set ===")

    trained_classes = list(le.classes_)
    untrained_classes = set(test_df["label"].unique()) - set(trained_classes)
    if untrained_classes:
        logger.warning(f"Test set contains classes not in training: {untrained_classes}")
        logger.warning("These will be counted as misclassifications in overall metrics.")

    X_test = test_df["text"].apply(preprocess_text).values
    y_test = test_df["label"].values

    # Predictions
    start_time = time.time()
    y_pred = pipeline.predict(X_test)
    total_time = time.time() - start_time
    mean_latency_ms = (total_time / len(X_test)) * 1000

    # Convert predictions back to label names
    y_pred_labels = le.inverse_transform(y_pred)

    # Get probabilities for confidence analysis
    y_proba = pipeline.predict_proba(X_test)
    y_confidence = np.max(y_proba, axis=1)

    # Classification report
    report_str = classification_report(
        y_test, y_pred_labels,
        labels=CLASSES,
        digits=4,
        zero_division=0,
    )
    logger.info(f"\nClassification Report:\n{report_str}")

    with open(results_dir / "classification_report.txt", "w") as f:
        f.write("RecoveryBench — Intent Classifier — Test Set Classification Report\n")
        f.write(f"Date: {datetime.now().isoformat()}\n")
        f.write(f"Test size: {len(test_df)} examples\n")
        f.write(f"Mean inference latency: {mean_latency_ms:.2f} ms/prediction\n\n")
        f.write(report_str)

    # Overall metrics
    test_f1 = f1_score(y_test, y_pred_labels, average="macro")
    test_acc = accuracy_score(y_test, y_pred_labels)
    logger.info(f"Test: accuracy={test_acc:.4f}, macro F1={test_f1:.4f}")
    logger.info(f"Mean latency: {mean_latency_ms:.2f} ms/prediction")

    # ============================================================
    # Confusion Matrix Plot
    # ============================================================
    cm = confusion_matrix(y_test, y_pred_labels, labels=CLASSES)
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
    ax.set_title("Confusion Matrix — Intent Classifier", fontweight="bold", fontsize=14)
    plt.colorbar(im, ax=ax, shrink=0.8)

    ax.set_xticks(range(len(CLASSES)))
    ax.set_yticks(range(len(CLASSES)))
    ax.set_xticklabels(CLASSES, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(CLASSES, fontsize=9)
    ax.set_xlabel("Predicted", fontweight="bold")
    ax.set_ylabel("True", fontweight="bold")

    # Add text annotations
    for i in range(len(CLASSES)):
        for j in range(len(CLASSES)):
            ax.text(
                j, i, str(cm[i, j]),
                ha="center", va="center", fontsize=10, fontweight="bold",
                color="white" if cm[i, j] > cm.max() * 0.5 else "black",
            )

    plt.tight_layout()
    fig.savefig(results_dir / "confusion_matrix.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {results_dir / 'confusion_matrix.png'}")

    # ============================================================
    # Per-Language Report
    # ============================================================
    per_lang_report = "RecoveryBench — Per-Language Intent Classification Report\n"
    per_lang_report += f"Date: {datetime.now().isoformat()}\n\n"

    lang_f1s = {}
    for lang in LANGUAGES:
        mask = test_df["language"] == lang
        if mask.sum() == 0:
            continue
        y_lang = test_df[mask]["label"].values
        y_lang_pred = y_pred_labels[mask.values]
        lang_report = classification_report(
            y_lang, y_lang_pred,
            labels=CLASSES,
            digits=4,
            zero_division=0,
        )
        lang_f1 = f1_score(
            y_lang, y_lang_pred,
            average="macro",
            zero_division=0,
        )
        lang_f1s[lang] = lang_f1
        per_lang_report += f"\n{'='*60}\n{lang} (n={mask.sum()}, macro F1={lang_f1:.4f})\n{'='*60}\n"
        per_lang_report += lang_report + "\n"

    with open(results_dir / "per_language_report.txt", "w") as f:
        f.write(per_lang_report)
    logger.info(f"Saved: {results_dir / 'per_language_report.txt'}")

    # ============================================================
    # Top 20 Highest-Confidence Mistakes
    # ============================================================
    mistakes_mask = y_pred_labels != y_test
    if mistakes_mask.sum() > 0:
        mistakes_df = test_df[mistakes_mask].copy()
        mistakes_df["predicted_label"] = y_pred_labels[mistakes_mask]
        mistakes_df["confidence"] = y_confidence[mistakes_mask]
        mistakes_df = mistakes_df.sort_values("confidence", ascending=False)
        top20 = mistakes_df.head(20)

        top20_report = "\nTop 20 Highest-Confidence Mistakes:\n"
        top20_report += "-" * 80 + "\n"
        for _, row in top20.iterrows():
            top20_report += (
                f"  Text: {row['text'][:80]}...\n"
                f"  True: {row['label']} | Predicted: {row['predicted_label']} | "
                f"Confidence: {row['confidence']:.4f} | Language: {row['language']}\n\n"
            )
        logger.info(top20_report)
    else:
        top20 = pd.DataFrame()

    # ============================================================
    # Hard Examples CSV
    # ============================================================
    hard_df = test_df.copy()
    hard_df["predicted_label"] = y_pred_labels
    hard_df["confidence"] = y_confidence
    hard_df["correct"] = (hard_df["label"] == hard_df["predicted_label"])

    # Save all predictions for analysis, sorted by confidence descending for wrong ones first
    hard_df = hard_df.sort_values(["correct", "confidence"], ascending=[True, False])
    hard_df = hard_df[["text", "label", "predicted_label", "confidence", "language", "correct"]]
    hard_df.rename(columns={"label": "true_label"}, inplace=True)

    analysis_dir.mkdir(parents=True, exist_ok=True)
    hard_df.to_csv(analysis_dir / "hard_examples.csv", index=False)
    logger.info(f"Saved: {analysis_dir / 'hard_examples.csv'} ({len(hard_df)} rows)")

    return {
        "test_accuracy": test_acc,
        "test_f1": test_f1,
        "mean_latency_ms": mean_latency_ms,
        "per_language_f1": lang_f1s,
        "n_mistakes": int(mistakes_mask.sum()),
        "confusion_matrix": cm.tolist(),
    }


def plot_learning_curves(pipeline, X_train, y_train, results_dir: Path):
    """Generate learning curves showing model performance vs training size."""
    logger.info("Generating learning curves...")

    train_sizes, train_scores, val_scores = learning_curve(
        pipeline, X_train, y_train,
        cv=3,
        n_jobs=1,
        train_sizes=np.linspace(0.1, 1.0, 8),
        scoring="f1_macro",
        random_state=RANDOM_SEED,
    )

    train_mean = train_scores.mean(axis=1)
    train_std = train_scores.std(axis=1)
    val_mean = val_scores.mean(axis=1)
    val_std = val_scores.std(axis=1)

    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    ax.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, alpha=0.1, color="#3498db")
    ax.fill_between(train_sizes, val_mean - val_std, val_mean + val_std, alpha=0.1, color="#e74c3c")
    ax.plot(train_sizes, train_mean, "o-", color="#3498db", label="Training F1")
    ax.plot(train_sizes, val_mean, "o-", color="#e74c3c", label="Cross-Validation F1")

    ax.set_xlabel("Training Set Size", fontweight="bold")
    ax.set_ylabel("Macro F1 Score", fontweight="bold")
    ax.set_title("Learning Curves — Intent Classifier", fontweight="bold", fontsize=14)
    ax.legend(loc="lower right")
    ax.set_ylim(0, 1.05)

    plt.tight_layout()
    fig.savefig(results_dir / "training_curves.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {results_dir / 'training_curves.png'}")


def save_model(pipeline, le, metrics: dict, model_dir: Path):
    """Save model, label encoder, and metadata."""
    model_dir.mkdir(parents=True, exist_ok=True)

    # Save model pipeline
    with open(model_dir / "model.pkl", "wb") as f:
        pickle.dump(pipeline, f)
    model_size_mb = os.path.getsize(model_dir / "model.pkl") / (1024 * 1024)
    logger.info(f"Model saved: {model_dir / 'model.pkl'} ({model_size_mb:.2f} MB)")

    # Save label encoder
    with open(model_dir / "label_encoder.pkl", "wb") as f:
        pickle.dump(le, f)

    # Save label_map.json — maps encoder index to class name
    trained_classes = list(le.classes_)
    label_map = {str(i): cls for i, cls in enumerate(trained_classes)}
    with open(model_dir / "label_map.json", "w") as f:
        json.dump(label_map, f, indent=2)
    logger.info(f"Label map saved: {label_map}")

    # Save config/metadata
    config = {
        "model_type": "TF-IDF + LogisticRegression",
        "tfidf_analyzer": "char_wb",
        "tfidf_ngram_range": [2, 5],
        "tfidf_max_features": 50000,
        "all_classes": CLASSES,
        "trained_classes": trained_classes,
        "languages": LANGUAGES,
        "model_size_mb": round(model_size_mb, 2),
        "metrics": metrics,
        "timestamp": datetime.now().isoformat(),
    }
    with open(model_dir / "config.json", "w") as f:
        json.dump(config, f, indent=2)
    logger.info(f"Config saved: {model_dir / 'config.json'}")

    return model_size_mb


def main():
    """Main training and evaluation pipeline."""
    # Path: models/intent_classifier/train.py → parent.parent.parent = project root
    base_dir = Path(__file__).parent.parent.parent
    data_dir = base_dir / "data"
    model_dir = base_dir / "models" / "intent_classifier"
    results_dir = base_dir / "models" / "results"
    analysis_dir = base_dir / "analysis"

    results_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("RecoveryBench — Intent Classifier Training")
    logger.info("=" * 60)

    # Load data
    train_df, val_df, test_df = load_data(data_dir)

    # Train model
    pipeline, le, train_metrics = train_model(train_df, val_df)

    # Generate learning curves
    X_train = train_df["text"].apply(preprocess_text).values
    y_train_enc = le.transform(train_df["label"].values)
    plot_learning_curves(pipeline, X_train, y_train_enc, results_dir)

    # Evaluate on test
    test_metrics = evaluate_model(pipeline, le, test_df, results_dir, analysis_dir)

    # Combine metrics
    all_metrics = {**train_metrics, **test_metrics}

    # Save model
    model_size = save_model(pipeline, le, all_metrics, model_dir)
    all_metrics["model_size_mb"] = model_size

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TRAINING COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Test Accuracy:  {all_metrics['test_accuracy']:.4f}")
    logger.info(f"  Test Macro F1:  {all_metrics['test_f1']:.4f}")
    logger.info(f"  Model Size:     {model_size:.2f} MB")
    logger.info(f"  Latency:        {all_metrics['mean_latency_ms']:.2f} ms/prediction")
    logger.info(f"  Per-Language F1:")
    for lang, f1 in all_metrics['per_language_f1'].items():
        logger.info(f"    {lang}: {f1:.4f}")

    # Determine status
    test_f1 = all_metrics['test_f1']
    if test_f1 < 0.50:
        status = "FAIL"
    elif test_f1 < 0.70:
        status = "PASS WITH WARNINGS"
    else:
        status = "PASS"

    # Check Bengali F1 gap
    if "Bengali" in all_metrics['per_language_f1']:
        bn_f1 = all_metrics['per_language_f1']['Bengali']
        other_f1s = [v for k, v in all_metrics['per_language_f1'].items() if k != 'Bengali']
        if other_f1s:
            avg_other = sum(other_f1s) / len(other_f1s)
            if avg_other - bn_f1 > 0.15:
                if status == "PASS":
                    status = "PASS WITH WARNINGS"
                logger.warning(f"Bengali F1 ({bn_f1:.4f}) is {avg_other - bn_f1:.4f} below average ({avg_other:.4f})")

    logger.info(f"\n  STATUS: {status}")

    # Save overall summary
    summary = {
        "status": status,
        "metrics": all_metrics,
        "timestamp": datetime.now().isoformat(),
    }
    with open(results_dir / "training_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    return status, all_metrics


if __name__ == "__main__":
    main()
