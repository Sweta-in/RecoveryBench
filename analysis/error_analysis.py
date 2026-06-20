#!/usr/bin/env python3
"""
RecoveryBench — Error Analysis Module

Performs detailed error analysis on the intent classifier's test set predictions.
Generates:
  - analysis/reports/error_report.md  — comprehensive failure mode analysis
  - analysis/reports/hard_examples.csv — exactly 100 hard/misclassified examples

Usage:
    python analysis/error_analysis.py
"""

import sys
import os
import json
import time
import pickle
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

import numpy as np
import pandas as pd

# ── Ensure project root is on path ──────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ── Helper: load the trained intent classifier ──────────────────────────────
def _load_classifier():
    """Load the intent classifier from models/intent_classifier/."""
    from models.intent_classifier.predict import IntentClassifier
    return IntentClassifier()


# ── Step 1: Run inference on test set (or load cached predictions) ──────────
def generate_predictions(test_csv: Path, predictions_csv: Path) -> pd.DataFrame:
    """
    Run the intent classifier on every row in data/test.csv and save results
    to models/results/test_predictions.csv.  If predictions already exist,
    load them instead.
    """
    if predictions_csv.exists():
        print(f"[INFO] Loading cached predictions from {predictions_csv}")
        return pd.read_csv(predictions_csv)

    print("[INFO] Running inference on test set …")
    clf = _load_classifier()
    df = pd.read_csv(test_csv)

    predicted_labels = []
    confidences = []
    latencies = []

    for text in df["text"]:
        t0 = time.perf_counter()
        result = clf.predict(str(text))
        t1 = time.perf_counter()
        predicted_labels.append(result["label"])
        confidences.append(result["confidence"])
        latencies.append((t1 - t0) * 1000)  # ms

    df["predicted_label"] = predicted_labels
    df["confidence"] = confidences
    df["latency_ms"] = latencies
    df["correct"] = df["label"] == df["predicted_label"]

    predictions_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(predictions_csv, index=False)
    print(f"[INFO] Predictions saved to {predictions_csv} ({len(df)} rows)")
    return df


# ── Step 2: Build the hard-examples CSV (exactly 100 rows) ─────────────────
def build_hard_examples(df: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    """
    Select exactly 100 hard examples from the test predictions.

    Selection strategy (in priority order, to fill 100 rows):
      1. All misclassified examples (wrong prediction).
      2. Correct but low-confidence predictions (confidence < 0.50).
      3. Correct but borderline predictions (confidence < 0.70).
      4. Remaining slots: hardest correct examples by ascending confidence.
    """
    TARGET = 100

    # 1. All misclassified rows
    wrong = df[~df["correct"]].copy()
    wrong["hard_reason"] = "misclassified"

    # 2. Correct but very low confidence
    low_conf = df[(df["correct"]) & (df["confidence"] < 0.50)].copy()
    low_conf["hard_reason"] = "low_confidence"

    # 3. Correct but borderline confidence
    borderline = df[(df["correct"]) & (df["confidence"] >= 0.50) & (df["confidence"] < 0.70)].copy()
    borderline["hard_reason"] = "borderline_confidence"

    # 4. Next-hardest correct examples
    remaining = df[(df["correct"]) & (df["confidence"] >= 0.70)].copy()
    remaining["hard_reason"] = "near_boundary"
    remaining = remaining.sort_values("confidence", ascending=True)

    # Combine in priority order
    pool = pd.concat([wrong, low_conf, borderline, remaining], ignore_index=True)
    pool = pool.drop_duplicates(subset=["text"])

    if len(pool) >= TARGET:
        hard = pool.head(TARGET)
    else:
        # Extremely unlikely but handle gracefully
        hard = pool.copy()
        print(f"[WARN] Only {len(hard)} hard examples available (target: {TARGET})")

    # Select output columns
    hard = hard[["text", "label", "predicted_label", "confidence", "language", "hard_reason"]].copy()
    hard.columns = ["text", "true_label", "predicted_label", "confidence", "language", "hard_reason"]
    hard = hard.reset_index(drop=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    hard.to_csv(output_path, index=False)
    print(f"[INFO] Hard examples saved to {output_path} ({len(hard)} rows)")
    return hard


# ── Step 3: Compute error statistics ───────────────────────────────────────
def compute_error_stats(df: pd.DataFrame) -> dict:
    """Compute comprehensive error statistics from predictions DataFrame."""
    stats = {}

    # Overall accuracy
    total = len(df)
    correct = df["correct"].sum()
    wrong = total - correct
    stats["total"] = total
    stats["correct"] = int(correct)
    stats["wrong"] = int(wrong)
    stats["accuracy"] = round(correct / total, 4)

    # Per-class error rates
    classes = sorted(df["label"].unique())
    per_class = {}
    for cls in classes:
        cls_df = df[df["label"] == cls]
        n = len(cls_df)
        n_correct = cls_df["correct"].sum()
        n_wrong = n - n_correct
        per_class[cls] = {
            "total": n,
            "correct": int(n_correct),
            "wrong": int(n_wrong),
            "accuracy": round(n_correct / n, 4) if n > 0 else 0.0,
            "error_rate": round(n_wrong / n, 4) if n > 0 else 0.0,
        }
    stats["per_class"] = per_class

    # Per-language error rates
    languages = sorted(df["language"].unique())
    per_lang = {}
    for lang in languages:
        lang_df = df[df["language"] == lang]
        n = len(lang_df)
        n_correct = lang_df["correct"].sum()
        per_lang[lang] = {
            "total": n,
            "correct": int(n_correct),
            "wrong": int(n - n_correct),
            "accuracy": round(n_correct / n, 4) if n > 0 else 0.0,
        }
    stats["per_language"] = per_lang

    # Confusion pairs (what gets confused with what)
    mistakes = df[~df["correct"]]
    confusion_pairs = Counter()
    for _, row in mistakes.iterrows():
        pair = f"{row['label']} → {row['predicted_label']}"
        confusion_pairs[pair] += 1
    stats["top_confusion_pairs"] = dict(confusion_pairs.most_common(15))

    # Failure modes analysis
    failure_modes = {}

    # Mode 1: ALREADY_PAID collapse (biggest known issue)
    ap_mistakes = df[(df["label"] == "ALREADY_PAID") & (~df["correct"])]
    if len(ap_mistakes) > 0:
        ap_confusion = Counter(ap_mistakes["predicted_label"])
        failure_modes["already_paid_misclassification"] = {
            "description": "ALREADY_PAID examples misclassified into other classes (0% recall)",
            "count": len(ap_mistakes),
            "confusion_targets": dict(ap_confusion.most_common()),
            "severity": "critical",
        }

    # Mode 2: Short message ambiguity
    short_msgs = df[df["text"].str.len() < 15]
    if len(short_msgs) > 0:
        short_wrong = short_msgs[~short_msgs["correct"]]
        failure_modes["short_message_ambiguity"] = {
            "description": "Short messages (< 15 chars) are inherently ambiguous",
            "total_short": len(short_msgs),
            "wrong_short": len(short_wrong),
            "error_rate": round(len(short_wrong) / len(short_msgs), 4) if len(short_msgs) > 0 else 0.0,
            "severity": "moderate",
        }

    # Mode 3: High-confidence mistakes
    hc_mistakes = df[(~df["correct"]) & (df["confidence"] >= 0.60)]
    if len(hc_mistakes) > 0:
        failure_modes["high_confidence_mistakes"] = {
            "description": "Wrong predictions with confidence >= 0.60 (dangerous overconfidence)",
            "count": len(hc_mistakes),
            "mean_confidence": round(hc_mistakes["confidence"].mean(), 4),
            "severity": "high",
        }

    # Mode 4: Cross-language confusion
    lang_error_rates = {}
    for lang in languages:
        lang_df = df[df["language"] == lang]
        if len(lang_df) > 0:
            lang_error_rates[lang] = round((~lang_df["correct"]).mean(), 4)
    failure_modes["cross_language_variation"] = {
        "description": "Error rate varies across languages",
        "error_rates": lang_error_rates,
        "severity": "moderate",
    }

    stats["failure_modes"] = failure_modes

    # Mean confidence for correct vs wrong
    stats["mean_confidence_correct"] = round(df[df["correct"]]["confidence"].mean(), 4)
    stats["mean_confidence_wrong"] = round(df[~df["correct"]]["confidence"].mean(), 4) if wrong > 0 else None

    # Latency stats
    stats["mean_latency_ms"] = round(df["latency_ms"].mean(), 4)
    stats["p95_latency_ms"] = round(df["latency_ms"].quantile(0.95), 4)

    return stats


# ── Step 4: Generate error_report.md ────────────────────────────────────────
def generate_error_report(stats: dict, hard_df: pd.DataFrame, output_path: Path):
    """Generate a comprehensive markdown error report."""
    now = datetime.now().isoformat()

    lines = []
    lines.append("# RecoveryBench — Error Analysis Report")
    lines.append(f"**Generated:** {now}")
    lines.append("")

    # ── Overall Summary ──
    lines.append("## 1. Overall Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total test examples | {stats['total']} |")
    lines.append(f"| Correct predictions | {stats['correct']} |")
    lines.append(f"| Wrong predictions | {stats['wrong']} |")
    lines.append(f"| Accuracy | {stats['accuracy']:.2%} |")
    lines.append(f"| Mean confidence (correct) | {stats['mean_confidence_correct']:.4f} |")
    if stats["mean_confidence_wrong"] is not None:
        lines.append(f"| Mean confidence (wrong) | {stats['mean_confidence_wrong']:.4f} |")
    lines.append(f"| Mean latency | {stats['mean_latency_ms']:.2f} ms |")
    lines.append(f"| P95 latency | {stats['p95_latency_ms']:.2f} ms |")
    lines.append("")

    # ── Per-Class Error Rates ──
    lines.append("## 2. Per-Class Error Rates")
    lines.append("")
    lines.append("| Class | Total | Correct | Wrong | Accuracy | Error Rate |")
    lines.append("|-------|-------|---------|-------|----------|------------|")
    for cls, info in sorted(stats["per_class"].items()):
        lines.append(
            f"| {cls} | {info['total']} | {info['correct']} | {info['wrong']} "
            f"| {info['accuracy']:.2%} | {info['error_rate']:.2%} |"
        )
    lines.append("")

    # ── Per-Language Error Rates ──
    lines.append("## 3. Per-Language Error Rates")
    lines.append("")
    lines.append("| Language | Total | Correct | Wrong | Accuracy |")
    lines.append("|----------|-------|---------|-------|----------|")
    for lang, info in sorted(stats["per_language"].items()):
        lines.append(
            f"| {lang} | {info['total']} | {info['correct']} | {info['wrong']} "
            f"| {info['accuracy']:.2%} |"
        )
    lines.append("")

    # ── Top Confusion Pairs ──
    lines.append("## 4. Top Confusion Pairs")
    lines.append("")
    lines.append("| True Label → Predicted Label | Count |")
    lines.append("|------------------------------|-------|")
    for pair, count in stats["top_confusion_pairs"].items():
        lines.append(f"| {pair} | {count} |")
    lines.append("")

    # ── Failure Mode Analysis ──
    lines.append("## 5. Failure Mode Analysis")
    lines.append("")
    for mode_name, mode_info in stats["failure_modes"].items():
        severity = mode_info.get("severity", "unknown")
        severity_badge = {"critical": "🔴", "high": "🟠", "moderate": "🟡", "low": "🟢"}.get(severity, "⚪")
        lines.append(f"### {severity_badge} {mode_name.replace('_', ' ').title()}")
        lines.append(f"**Severity:** {severity}")
        lines.append(f"**Description:** {mode_info['description']}")
        lines.append("")
        for k, v in mode_info.items():
            if k in ("description", "severity"):
                continue
            if isinstance(v, dict):
                lines.append(f"**{k.replace('_', ' ').title()}:**")
                for sub_k, sub_v in v.items():
                    lines.append(f"  - {sub_k}: {sub_v}")
            else:
                lines.append(f"- **{k.replace('_', ' ').title()}:** {v}")
        lines.append("")

    # ── Top 3 Failure Modes (Summary) ──
    lines.append("## 6. Top 3 Failure Modes — Actionable Recommendations")
    lines.append("")
    lines.append("### 1. ALREADY_PAID Class Collapse (Critical)")
    lines.append("The TF-IDF model was trained on 5 classes only (no ALREADY_PAID training data).")
    lines.append("Keyword override catches some cases but misses nuanced expressions.")
    lines.append("**Fix:** Add ALREADY_PAID as a 6th training class with dedicated labelled data,")
    lines.append("or fine-tune an IndicBERT model that can learn the distinction from context.")
    lines.append("")
    lines.append("### 2. Short Message Ambiguity (Moderate)")
    lines.append("Messages under 15 characters (e.g., 'ok', 'hmm', '...') lack sufficient")
    lines.append("signal for any text classifier. These are inherently ambiguous even to humans.")
    lines.append("**Fix:** Introduce a VAGUE-by-default policy for messages below a character")
    lines.append("threshold, or request clarification in the agent response strategy.")
    lines.append("")
    lines.append("### 3. High-Confidence Misclassifications (High)")
    lines.append("Some wrong predictions carry confidence > 0.60, which is dangerous in")
    lines.append("production because downstream systems trust the classifier's certainty.")
    lines.append("**Fix:** Implement confidence calibration (Platt scaling) and add a")
    lines.append("'needs-human-review' threshold band between 0.40–0.65.")
    lines.append("")

    # ── Hard Examples Sample ──
    lines.append("## 7. Hard Examples Sample (first 25)")
    lines.append("")
    lines.append("| # | Text | True | Predicted | Conf. | Lang | Reason |")
    lines.append("|---|------|------|-----------|-------|------|--------|")
    for i, row in hard_df.head(25).iterrows():
        text_short = str(row["text"])[:50].replace("|", "\\|")
        lines.append(
            f"| {i+1} | {text_short} | {row['true_label']} | {row['predicted_label']} "
            f"| {row['confidence']:.3f} | {row['language']} | {row['hard_reason']} |"
        )
    lines.append("")
    lines.append(f"Full list: `analysis/reports/hard_examples.csv` ({len(hard_df)} rows)")
    lines.append("")

    # ── Recommendations ──
    lines.append("## 8. Recommendations for Next Iteration")
    lines.append("")
    lines.append("1. **Retrain with ALREADY_PAID class** — include as 6th label in training data")
    lines.append("2. **Upgrade to IndicBERT** — transformer embeddings will capture contextual")
    lines.append("   nuances missed by character n-gram TF-IDF")
    lines.append("3. **Confidence calibration** — apply Platt scaling to reduce overconfident errors")
    lines.append("4. **Data augmentation** — more code-mixed and short-form examples")
    lines.append("5. **Active learning loop** — route low-confidence predictions to human annotators")
    lines.append("")

    report_text = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text, encoding="utf-8")
    print(f"[INFO] Error report saved to {output_path}")


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    test_csv = PROJECT_ROOT / "data" / "test.csv"
    predictions_csv = PROJECT_ROOT / "models" / "results" / "test_predictions.csv"
    hard_examples_csv = PROJECT_ROOT / "analysis" / "reports" / "hard_examples.csv"
    error_report_md = PROJECT_ROOT / "analysis" / "reports" / "error_report.md"

    if not test_csv.exists():
        print(f"[ERROR] Test data not found at {test_csv}")
        sys.exit(1)

    # Step 1: Generate or load predictions
    df = generate_predictions(test_csv, predictions_csv)
    print(f"[INFO] Predictions: {len(df)} rows, accuracy = {df['correct'].mean():.4f}")

    # Step 2: Build hard examples (exactly 100 rows)
    hard_df = build_hard_examples(df, hard_examples_csv)
    assert len(hard_df) == 100, f"Expected 100 hard examples, got {len(hard_df)}"
    print(f"[OK] hard_examples.csv has {len(hard_df)} rows (PASS)")

    # Step 3: Compute error statistics
    stats = compute_error_stats(df)

    # Step 4: Generate error report
    generate_error_report(stats, hard_df, error_report_md)

    # Print summary
    print("\n" + "=" * 60)
    print("ERROR ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"  Test accuracy:  {stats['accuracy']:.2%}")
    print(f"  Total errors:   {stats['wrong']} / {stats['total']}")
    print(f"  Hard examples:  {len(hard_df)} rows saved")
    print(f"  Reports:")
    print(f"    - {error_report_md}")
    print(f"    - {hard_examples_csv}")
    print()

    # Print top failure modes
    print("Top Failure Modes:")
    for mode_name, mode_info in stats["failure_modes"].items():
        severity = mode_info.get("severity", "?")
        print(f"  [{severity.upper()}] {mode_name}: {mode_info['description']}")
    print()


if __name__ == "__main__":
    main()
