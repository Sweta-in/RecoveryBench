#!/usr/bin/env python3
"""
RecoveryBench — Intent Classifier Evaluation Script

Loads the trained model and generates comprehensive evaluation reports:
  - Classification report (overall + per-class precision/recall/F1)
  - Confusion matrix plot
  - Per-language F1 breakdown
  - Hard examples CSV for error analysis
  - Top false positives/negatives per class
  - Highest-confidence mistakes

Usage:
    python models/evaluate_intent_classifier.py
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
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    accuracy_score,
    precision_recall_fscore_support,
)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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

# Color palette
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


def load_model(model_dir: Path):
    """Load trained model and label encoder."""
    with open(model_dir / "model.pkl", "rb") as f:
        pipeline = pickle.load(f)
    with open(model_dir / "label_encoder.pkl", "rb") as f:
        le = pickle.load(f)
    logger.info(f"Model loaded from {model_dir}")
    return pipeline, le


def load_data(data_dir: Path):
    """Load test dataset."""
    test_df = pd.read_csv(data_dir / "test.csv")
    logger.info(f"Test data loaded: {len(test_df)} rows")
    return test_df


def preprocess_text(text: str) -> str:
    """Basic text preprocessing matching training."""
    import re
    if not isinstance(text, str):
        return ""
    text = text.strip().lower()
    text = re.sub(r'(.)\1{3,}', r'\1\1', text)
    return text


def generate_confusion_matrix_plot(y_true, y_pred, labels, save_path):
    """Generate and save confusion matrix plot."""
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
    ax.set_title("Confusion Matrix — Intent Classifier", fontweight="bold", fontsize=14)
    plt.colorbar(im, ax=ax, shrink=0.8)

    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Predicted", fontweight="bold")
    ax.set_ylabel("True", fontweight="bold")

    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(
                j, i, str(cm[i, j]),
                ha="center", va="center", fontsize=10, fontweight="bold",
                color="white" if cm[i, j] > cm.max() * 0.5 else "black",
            )

    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved confusion matrix: {save_path}")
    return cm


def generate_per_language_f1(test_df, y_pred_labels, le, y_pred_enc, save_path):
    """Generate per-language F1 report and CSV."""
    per_lang_lines = ["RecoveryBench — Per-Language Intent Classification Report"]
    per_lang_lines.append(f"Date: {datetime.now().isoformat()}\n")

    lang_f1s = {}
    lang_data = []

    for lang in LANGUAGES:
        mask = test_df["language"] == lang
        if mask.sum() == 0:
            continue

        y_lang_true = test_df[mask]["label"].values
        y_lang_pred = y_pred_labels[mask.values]

        lang_report = classification_report(
            y_lang_true, y_lang_pred, labels=CLASSES, digits=4, zero_division=0,
        )
        lang_f1 = f1_score(
            le.transform(y_lang_true), y_pred_enc[mask.values], average="macro",
        )
        lang_f1s[lang] = lang_f1

        # Per-class F1 for this language
        p, r, f, s = precision_recall_fscore_support(
            y_lang_true, y_lang_pred, labels=CLASSES, zero_division=0,
        )
        for cls_idx, cls_name in enumerate(CLASSES):
            lang_data.append({
                "language": lang,
                "class": cls_name,
                "precision": round(p[cls_idx], 4),
                "recall": round(r[cls_idx], 4),
                "f1": round(f[cls_idx], 4),
                "support": int(s[cls_idx]),
            })

        per_lang_lines.append(f"\n{'='*60}")
        per_lang_lines.append(f"{lang} (n={mask.sum()}, macro F1={lang_f1:.4f})")
        per_lang_lines.append(f"{'='*60}")
        per_lang_lines.append(lang_report)

    # Save text report
    report_path = save_path.parent / "per_language_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(per_lang_lines))
    logger.info(f"Saved per-language report: {report_path}")

    # Save CSV
    csv_path = save_path.parent / "per_language_f1.csv"
    pd.DataFrame(lang_data).to_csv(csv_path, index=False)
    logger.info(f"Saved per-language F1 CSV: {csv_path}")

    return lang_f1s


def extract_false_positives_negatives(test_df, y_pred_labels, y_confidence):
    """Extract top false positives and false negatives per class."""
    fp_records = []
    fn_records = []

    for cls in CLASSES:
        # False positives: predicted as cls but true label is different
        fp_mask = (y_pred_labels == cls) & (test_df["label"].values != cls)
        if fp_mask.sum() > 0:
            fp_df = test_df[fp_mask].copy()
            fp_df["predicted_label"] = y_pred_labels[fp_mask]
            fp_df["confidence"] = y_confidence[fp_mask]
            fp_df = fp_df.sort_values("confidence", ascending=False).head(10)
            for _, row in fp_df.iterrows():
                fp_records.append({
                    "target_class": cls,
                    "text": row["text"],
                    "true_label": row["label"],
                    "predicted_label": row["predicted_label"],
                    "confidence": round(row["confidence"], 4),
                    "language": row["language"],
                })

        # False negatives: true label is cls but predicted differently
        fn_mask = (test_df["label"].values == cls) & (y_pred_labels != cls)
        if fn_mask.sum() > 0:
            fn_df = test_df[fn_mask].copy()
            fn_df["predicted_label"] = y_pred_labels[fn_mask]
            fn_df["confidence"] = y_confidence[fn_mask]
            fn_df = fn_df.sort_values("confidence", ascending=False).head(10)
            for _, row in fn_df.iterrows():
                fn_records.append({
                    "target_class": cls,
                    "text": row["text"],
                    "true_label": row["label"],
                    "predicted_label": row["predicted_label"],
                    "confidence": round(row["confidence"], 4),
                    "language": row["language"],
                })

    return fp_records, fn_records


def main():
    """Main evaluation pipeline."""
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    model_dir = base_dir / "models" / "intent_classifier"
    results_dir = base_dir / "models" / "results"
    analysis_dir = base_dir / "analysis"

    results_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("RecoveryBench — Intent Classifier Evaluation")
    logger.info("=" * 60)

    # Load model and data
    pipeline, le = load_model(model_dir)
    test_df = load_data(data_dir)

    # Preprocess
    X_test = test_df["text"].apply(preprocess_text).values
    y_test = test_df["label"].values
    y_test_enc = le.transform(y_test)

    # Predictions with timing
    start_time = time.time()
    y_pred_enc = pipeline.predict(X_test)
    total_time = time.time() - start_time
    mean_latency_ms = (total_time / len(X_test)) * 1000

    y_pred_labels = le.inverse_transform(y_pred_enc)
    y_proba = pipeline.predict_proba(X_test)
    y_confidence = np.max(y_proba, axis=1)

    # --- Overall Metrics ---
    test_acc = accuracy_score(y_test_enc, y_pred_enc)
    test_f1_macro = f1_score(y_test_enc, y_pred_enc, average="macro")
    test_f1_weighted = f1_score(y_test_enc, y_pred_enc, average="weighted")

    logger.info(f"\nOverall Metrics:")
    logger.info(f"  Accuracy:     {test_acc:.4f}")
    logger.info(f"  Macro F1:     {test_f1_macro:.4f}")
    logger.info(f"  Weighted F1:  {test_f1_weighted:.4f}")
    logger.info(f"  Mean latency: {mean_latency_ms:.2f} ms/prediction")

    # --- Classification Report ---
    report_str = classification_report(
        y_test, y_pred_labels, labels=CLASSES, digits=4, zero_division=0,
    )
    logger.info(f"\nClassification Report:\n{report_str}")

    with open(results_dir / "classification_report.txt", "w", encoding="utf-8") as f:
        f.write("RecoveryBench — Intent Classifier — Test Set Classification Report\n")
        f.write(f"Date: {datetime.now().isoformat()}\n")
        f.write(f"Test size: {len(test_df)} examples\n")
        f.write(f"Accuracy: {test_acc:.4f}\n")
        f.write(f"Macro F1: {test_f1_macro:.4f}\n")
        f.write(f"Weighted F1: {test_f1_weighted:.4f}\n")
        f.write(f"Mean inference latency: {mean_latency_ms:.2f} ms/prediction\n\n")
        f.write(report_str)

    # --- Confusion Matrix ---
    cm = generate_confusion_matrix_plot(
        y_test, y_pred_labels, CLASSES, results_dir / "confusion_matrix.png"
    )

    # --- Per-Language F1 ---
    lang_f1s = generate_per_language_f1(
        test_df, y_pred_labels, le, y_pred_enc, results_dir / "per_language_f1.csv"
    )

    # --- False Positives / Negatives ---
    fp_records, fn_records = extract_false_positives_negatives(
        test_df, y_pred_labels, y_confidence
    )

    # --- Top 20 Highest-Confidence Mistakes ---
    mistakes_mask = y_pred_labels != y_test
    n_mistakes = int(mistakes_mask.sum())

    hc_mistakes = []
    if n_mistakes > 0:
        mistakes_df = test_df[mistakes_mask].copy()
        mistakes_df["predicted_label"] = y_pred_labels[mistakes_mask]
        mistakes_df["confidence"] = y_confidence[mistakes_mask]
        mistakes_df = mistakes_df.sort_values("confidence", ascending=False)
        top20 = mistakes_df.head(20)

        for _, row in top20.iterrows():
            hc_mistakes.append({
                "text": row["text"],
                "true_label": row["label"],
                "predicted_label": row["predicted_label"],
                "confidence": round(row["confidence"], 4),
                "language": row["language"],
            })

    # --- Hard Examples CSV ---
    hard_df = test_df.copy()
    hard_df["predicted_label"] = y_pred_labels
    hard_df["confidence"] = y_confidence
    hard_df["correct"] = (hard_df["label"] == hard_df["predicted_label"])
    hard_df = hard_df.sort_values(["correct", "confidence"], ascending=[True, False])
    hard_df = hard_df[["text", "label", "predicted_label", "confidence", "language"]]
    hard_df.rename(columns={"label": "true_label"}, inplace=True)
    hard_df.to_csv(analysis_dir / "hard_examples.csv", index=False)
    logger.info(f"Saved hard examples: {analysis_dir / 'hard_examples.csv'} ({len(hard_df)} rows)")

    # --- Per-class precision/recall/F1 ---
    p, r, f, s = precision_recall_fscore_support(
        y_test, y_pred_labels, labels=CLASSES, zero_division=0,
    )
    per_class_metrics = {}
    for idx, cls in enumerate(CLASSES):
        per_class_metrics[cls] = {
            "precision": round(p[idx], 4),
            "recall": round(r[idx], 4),
            "f1": round(f[idx], 4),
            "support": int(s[idx]),
        }

    # --- Model size ---
    model_path = model_dir / "model.pkl"
    model_size_mb = os.path.getsize(model_path) / (1024 * 1024)

    # --- Save evaluation summary ---
    eval_summary = {
        "date": datetime.now().isoformat(),
        "test_size": len(test_df),
        "accuracy": round(test_acc, 4),
        "macro_f1": round(test_f1_macro, 4),
        "weighted_f1": round(test_f1_weighted, 4),
        "mean_latency_ms": round(mean_latency_ms, 4),
        "model_size_mb": round(model_size_mb, 2),
        "n_mistakes": n_mistakes,
        "per_class": per_class_metrics,
        "per_language_f1": {k: round(v, 4) for k, v in lang_f1s.items()},
        "confusion_matrix": cm.tolist(),
        "top_20_hc_mistakes": hc_mistakes,
        "false_positives_sample": fp_records[:30],
        "false_negatives_sample": fn_records[:30],
    }

    with open(results_dir / "evaluation_summary.json", "w", encoding="utf-8") as f:
        json.dump(eval_summary, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved evaluation summary: {results_dir / 'evaluation_summary.json'}")

    # --- Print Summary ---
    logger.info("\n" + "=" * 60)
    logger.info("EVALUATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Accuracy:     {test_acc:.4f}")
    logger.info(f"  Macro F1:     {test_f1_macro:.4f}")
    logger.info(f"  Weighted F1:  {test_f1_weighted:.4f}")
    logger.info(f"  Model Size:   {model_size_mb:.2f} MB")
    logger.info(f"  Latency:      {mean_latency_ms:.2f} ms/prediction")
    logger.info(f"  Mistakes:     {n_mistakes}/{len(test_df)}")
    logger.info(f"\n  Per-Class F1:")
    for cls, m in per_class_metrics.items():
        logger.info(f"    {cls:20s}: P={m['precision']:.4f}  R={m['recall']:.4f}  F1={m['f1']:.4f}  (n={m['support']})")
    logger.info(f"\n  Per-Language F1:")
    for lang, f1 in lang_f1s.items():
        logger.info(f"    {lang:12s}: {f1:.4f}")

    return eval_summary


if __name__ == "__main__":
    main()
