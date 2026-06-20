#!/usr/bin/env python3
"""
RecoveryBench-100 — Benchmark Runner (Phase 1B)

Runs the full pipeline on each of the 100 benchmark scenarios and
produces a scored results file.

Usage:
    python benchmarks/run_benchmark.py

Output:
    benchmarks/results/benchmark_scores.json
    benchmarks/results/benchmark_summary.json
"""

import json
import sys
import time
import logging
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BENCHMARK_PATH = PROJECT_ROOT / "benchmarks" / "recoverybench_100.json"
RESULTS_DIR = PROJECT_ROOT / "benchmarks" / "results"
SCORES_PATH = RESULTS_DIR / "benchmark_scores.json"
SUMMARY_PATH = RESULTS_DIR / "benchmark_summary.json"
REPORT_PATH = RESULTS_DIR / "benchmark_report.md"

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def load_benchmark():
    """Load the RecoveryBench-100 dataset."""
    if not BENCHMARK_PATH.exists():
        raise FileNotFoundError(
            f"Benchmark file not found: {BENCHMARK_PATH}\n"
            "Run: python benchmarks/generate_benchmark.py"
        )
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        scenarios = json.load(f)
    print(f"Loaded {len(scenarios)} benchmark scenarios")
    return scenarios


def run_benchmark():
    """Run all benchmark scenarios through the pipeline."""
    scenarios = load_benchmark()

    # Import pipeline components
    print("Loading pipeline components...")

    # Intent classifier
    intent_classifier = None
    try:
        from models.intent_classifier.predict import IntentClassifier
        intent_classifier = IntentClassifier()
        print("  [OK] Intent classifier loaded")
    except Exception as e:
        print(f"  [WARN] Intent classifier not available: {e}")

    # Promise parser
    promise_parser = None
    try:
        from pipeline.promise_parser import PromiseParser
        promise_parser = PromiseParser()
        print("  [OK] Promise parser loaded")
    except Exception as e:
        print(f"  [WARN] Promise parser not available: {e}")

    # Risk scorer
    risk_scorer = None
    try:
        from pipeline.risk_scorer import RiskScorer
        risk_scorer = RiskScorer()
        print("  [OK] Risk scorer loaded")
    except Exception as e:
        print(f"  [WARN] Risk scorer not available: {e}")

    # Compliance checker
    compliance_checker = None
    try:
        from pipeline.compliance import ComplianceChecker
        compliance_checker = ComplianceChecker()
        print("  [OK] Compliance checker loaded")
    except Exception as e:
        print(f"  [WARN] Compliance checker not available: {e}")

    # Evaluator
    evaluator = None
    try:
        from pipeline.evaluator import AgentEvaluator
        evaluator = AgentEvaluator()
        print(f"  [OK] Evaluator loaded (backend: {evaluator.backend})")
    except Exception as e:
        print(f"  [WARN] Evaluator not available: {e}")

    print(f"\nRunning {len(scenarios)} benchmark scenarios...")
    print("=" * 60)

    results = []
    intent_correct = 0
    intent_total = 0
    promise_correct = 0
    promise_total = 0
    start_time = time.time()

    for i, scenario in enumerate(scenarios):
        scenario_id = scenario["scenario_id"]
        borrower_msg = scenario["borrower_message"]
        agent_resp = scenario.get("agent_response", "")
        expected_intent = scenario["expected_intent"]
        expected_promise = scenario.get("expected_promise", False)
        expected_window = scenario.get("expected_window_days")

        result_entry = {
            "scenario_id": scenario_id,
            "expected_intent": expected_intent,
            "language": scenario["language"],
            "category": scenario["category"],
            "borrower_message": borrower_msg,
        }

        # --- Intent classification ---
        if intent_classifier:
            try:
                pred = intent_classifier.predict(borrower_msg)
                predicted_intent = pred["label"]
                intent_confidence = pred["confidence"]
                intent_match = predicted_intent == expected_intent
                if intent_match:
                    intent_correct += 1
                intent_total += 1
                result_entry["predicted_intent"] = predicted_intent
                result_entry["intent_confidence"] = round(intent_confidence, 4)
                result_entry["intent_correct"] = intent_match
            except Exception as e:
                result_entry["predicted_intent"] = "ERROR"
                result_entry["intent_confidence"] = 0.0
                result_entry["intent_correct"] = False
                result_entry["intent_error"] = str(e)
                intent_total += 1
        else:
            result_entry["predicted_intent"] = "UNAVAILABLE"
            result_entry["intent_correct"] = None

        # --- Promise extraction ---
        if promise_parser:
            try:
                promise_result = promise_parser.extract(borrower_msg)
                predicted_promise = promise_result.get("promise_to_pay", False)
                predicted_window = promise_result.get("payment_window_days")
                promise_match = predicted_promise == expected_promise
                if promise_match:
                    promise_correct += 1
                promise_total += 1
                result_entry["predicted_promise"] = predicted_promise
                result_entry["predicted_window_days"] = predicted_window
                result_entry["expected_promise"] = expected_promise
                result_entry["expected_window_days"] = expected_window
                result_entry["promise_correct"] = promise_match

                # Window accuracy (only if both have a window)
                if predicted_window is not None and expected_window is not None:
                    result_entry["window_exact_match"] = predicted_window == expected_window
                    result_entry["window_close_match"] = abs(predicted_window - expected_window) <= 3
                else:
                    result_entry["window_exact_match"] = None
                    result_entry["window_close_match"] = None
            except Exception as e:
                result_entry["predicted_promise"] = None
                result_entry["promise_correct"] = False
                result_entry["promise_error"] = str(e)
                promise_total += 1
        else:
            result_entry["predicted_promise"] = None
            result_entry["promise_correct"] = None

        # --- Risk scoring ---
        if risk_scorer and intent_classifier:
            try:
                risk_features = {
                    "intent": result_entry.get("predicted_intent", "VAGUE"),
                    "has_promise": result_entry.get("predicted_promise", False),
                    "payment_window_days": result_entry.get("predicted_window_days") or 0,
                    "message_length": len(borrower_msg),
                    "exclamation_count": borrower_msg.count("!"),
                    "question_count": borrower_msg.count("?"),
                    "caps_ratio": sum(1 for c in borrower_msg if c.isupper()) / max(len(borrower_msg), 1),
                    "dispute_keywords": 0,
                    "hostile_keywords": 0,
                }
                risk_score = risk_scorer.score(risk_features)
                result_entry["risk_score"] = round(risk_score, 4)
                result_entry["risk_band"] = risk_scorer.get_risk_band(risk_score)
            except Exception as e:
                result_entry["risk_score"] = None
                result_entry["risk_error"] = str(e)

        # --- Compliance check ---
        if compliance_checker and agent_resp:
            try:
                compliance_result = compliance_checker.check(agent_resp)
                result_entry["compliance"] = {
                    "compliant": compliance_result["compliant"],
                    "severity": compliance_result.get("severity", "none"),
                    "violation_count": len(compliance_result.get("violations", [])),
                }
            except Exception as e:
                result_entry["compliance"] = {"error": str(e)}

        # --- Agent evaluation ---
        if evaluator and agent_resp:
            try:
                eval_result = evaluator.evaluate(
                    borrower_message=borrower_msg,
                    intent=result_entry.get("predicted_intent", expected_intent),
                    confidence=result_entry.get("intent_confidence", 0.5),
                    agent_response=agent_resp,
                )
                result_entry["agent_eval"] = eval_result
            except Exception as e:
                result_entry["agent_eval"] = {"error": str(e)}

        results.append(result_entry)

        # Progress
        if (i + 1) % 20 == 0 or (i + 1) == len(scenarios):
            elapsed = time.time() - start_time
            print(f"  [{i+1:3d}/{len(scenarios)}] {elapsed:.1f}s elapsed")

    elapsed = time.time() - start_time
    print(f"\nBenchmark complete in {elapsed:.1f}s")

    # --- Compute summary statistics ---
    intent_accuracy = intent_correct / intent_total if intent_total > 0 else 0
    promise_accuracy = promise_correct / promise_total if promise_total > 0 else 0

    # Per-intent accuracy
    per_intent = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in results:
        if r.get("intent_correct") is not None:
            intent = r["expected_intent"]
            per_intent[intent]["total"] += 1
            if r["intent_correct"]:
                per_intent[intent]["correct"] += 1

    per_intent_accuracy = {}
    for intent, counts in sorted(per_intent.items()):
        acc = counts["correct"] / counts["total"] if counts["total"] > 0 else 0
        per_intent_accuracy[intent] = {
            "correct": counts["correct"],
            "total": counts["total"],
            "accuracy": round(acc, 4),
        }

    # Per-category accuracy
    per_category = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in results:
        if r.get("intent_correct") is not None:
            cat = r["category"]
            per_category[cat]["total"] += 1
            if r["intent_correct"]:
                per_category[cat]["correct"] += 1

    per_category_accuracy = {}
    for cat, counts in sorted(per_category.items()):
        acc = counts["correct"] / counts["total"] if counts["total"] > 0 else 0
        per_category_accuracy[cat] = {
            "correct": counts["correct"],
            "total": counts["total"],
            "accuracy": round(acc, 4),
        }

    # Per-language accuracy
    per_language = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in results:
        if r.get("intent_correct") is not None:
            lang = r["language"]
            per_language[lang]["total"] += 1
            if r["intent_correct"]:
                per_language[lang]["correct"] += 1

    per_language_accuracy = {}
    for lang, counts in sorted(per_language.items()):
        acc = counts["correct"] / counts["total"] if counts["total"] > 0 else 0
        per_language_accuracy[lang] = {
            "correct": counts["correct"],
            "total": counts["total"],
            "accuracy": round(acc, 4),
        }

    # Confusion matrix
    confusion = defaultdict(lambda: defaultdict(int))
    for r in results:
        if r.get("predicted_intent") and r.get("predicted_intent") not in ("UNAVAILABLE", "ERROR"):
            confusion[r["expected_intent"]][r["predicted_intent"]] += 1

    # Promise accuracy details
    promise_stats = {
        "total": promise_total,
        "correct": promise_correct,
        "accuracy": round(promise_accuracy, 4),
    }

    # Window match stats
    window_exact = sum(1 for r in results if r.get("window_exact_match") is True)
    window_close = sum(1 for r in results if r.get("window_close_match") is True)
    window_total = sum(1 for r in results if r.get("window_exact_match") is not None)
    promise_stats["window_exact_match"] = window_exact
    promise_stats["window_close_match"] = window_close
    promise_stats["window_total"] = window_total

    # Agent eval averages
    eval_scores = defaultdict(list)
    for r in results:
        ae = r.get("agent_eval", {})
        if isinstance(ae, dict) and "overall_score" in ae:
            for key in ["intent_accuracy", "tone_score", "compliance_score",
                        "escalation_score", "overall_score"]:
                if key in ae and isinstance(ae[key], (int, float)):
                    eval_scores[key].append(ae[key])

    eval_averages = {}
    for key, vals in eval_scores.items():
        eval_averages[key] = round(sum(vals) / len(vals), 2) if vals else None

    # Hardest categories (lowest intent accuracy)
    hardest = sorted(per_category_accuracy.items(), key=lambda x: x[1]["accuracy"])[:5]

    # Misclassified scenarios
    misclassified = [
        {
            "scenario_id": r["scenario_id"],
            "expected": r["expected_intent"],
            "predicted": r.get("predicted_intent"),
            "confidence": r.get("intent_confidence"),
            "category": r["category"],
            "language": r["language"],
            "message": r["borrower_message"][:80],
        }
        for r in results
        if r.get("intent_correct") is False
    ]

    summary = {
        "benchmark_date": datetime.now().isoformat(),
        "total_scenarios": len(scenarios),
        "elapsed_seconds": round(elapsed, 2),
        "intent_classification": {
            "overall_accuracy": round(intent_accuracy, 4),
            "correct": intent_correct,
            "total": intent_total,
            "per_intent": per_intent_accuracy,
            "per_category": per_category_accuracy,
            "per_language": per_language_accuracy,
            "confusion_matrix": {k: dict(v) for k, v in confusion.items()},
        },
        "promise_extraction": promise_stats,
        "agent_evaluation": eval_averages,
        "hardest_categories": [
            {"category": cat, **stats} for cat, stats in hardest
        ],
        "misclassified_count": len(misclassified),
        "misclassified_scenarios": misclassified,
        "components_used": {
            "intent_classifier": intent_classifier is not None,
            "promise_parser": promise_parser is not None,
            "risk_scorer": risk_scorer is not None,
            "compliance_checker": compliance_checker is not None,
            "evaluator": evaluator.backend if evaluator else None,
        },
    }

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(SCORES_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"Total scenarios: {len(scenarios)}")
    print(f"Time: {elapsed:.1f}s")
    print(f"\n--- Intent Classification ---")
    print(f"Overall accuracy: {intent_accuracy:.2%} ({intent_correct}/{intent_total})")
    print(f"\nPer-intent accuracy:")
    for intent, stats in sorted(per_intent_accuracy.items()):
        print(f"  {intent:20s}: {stats['accuracy']:.2%} ({stats['correct']}/{stats['total']})")
    print(f"\nPer-language accuracy:")
    for lang, stats in sorted(per_language_accuracy.items()):
        print(f"  {lang:15s}: {stats['accuracy']:.2%} ({stats['correct']}/{stats['total']})")
    print(f"\nHardest categories:")
    for cat, stats in hardest:
        print(f"  {cat:25s}: {stats['accuracy']:.2%} ({stats['correct']}/{stats['total']})")
    print(f"\n--- Promise Extraction ---")
    print(f"Promise accuracy: {promise_accuracy:.2%} ({promise_correct}/{promise_total})")
    if window_total > 0:
        print(f"Window exact match: {window_exact}/{window_total}")
        print(f"Window close match (+/-3 days): {window_close}/{window_total}")
    print(f"\n--- Agent Evaluation ---")
    for key, val in eval_averages.items():
        print(f"  {key:25s}: {val}")
    print(f"\nMisclassified: {len(misclassified)} scenarios")
    if misclassified:
        print(f"\nTop misclassifications:")
        for m in misclassified[:10]:
            print(f"  {m['scenario_id']} [{m['category']}] {m['expected']} -> {m['predicted']} ({m['confidence']:.2f}): {m['message']}")

    print(f"\n[OK] Results saved to {SCORES_PATH}")
    print(f"[OK] Summary saved to {SUMMARY_PATH}")

    # Generate markdown report
    generate_report(summary)
    print(f"[OK] Report saved to {REPORT_PATH}")

    return summary


def generate_report(summary: dict):
    """Generate a human-readable markdown benchmark report."""
    ic = summary["intent_classification"]
    pe = summary["promise_extraction"]
    ae = summary.get("agent_evaluation", {})
    misclassified = summary.get("misclassified_scenarios", [])
    hardest = summary.get("hardest_categories", [])

    lines = []
    lines.append("# RecoveryBench-100 — Benchmark Report")
    lines.append("")
    lines.append(f"**Date:** {summary['benchmark_date']}")
    lines.append(f"**Scenarios:** {summary['total_scenarios']}")
    lines.append(f"**Elapsed:** {summary['elapsed_seconds']}s")
    lines.append("")

    # Overall
    lines.append("## Overall Results")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Intent Accuracy | {ic['overall_accuracy']:.2%} ({ic['correct']}/{ic['total']}) |")
    lines.append(f"| Promise Accuracy | {pe['accuracy']:.2%} ({pe['correct']}/{pe['total']}) |")
    if pe.get("window_total", 0) > 0:
        lines.append(f"| Window Exact Match | {pe['window_exact_match']}/{pe['window_total']} |")
        lines.append(f"| Window Close Match (±3d) | {pe['window_close_match']}/{pe['window_total']} |")
    if ae.get("overall_score") is not None:
        lines.append(f"| Agent Eval (mean) | {ae['overall_score']} / 10 |")
    lines.append("")

    # Per-intent
    lines.append("## Per-Intent Accuracy")
    lines.append("")
    lines.append("| Intent | Correct | Total | Accuracy |")
    lines.append("|--------|---------|-------|----------|")
    for intent, stats in sorted(ic.get("per_intent", {}).items()):
        lines.append(f"| {intent} | {stats['correct']} | {stats['total']} | {stats['accuracy']:.2%} |")
    lines.append("")

    # Per-language
    lines.append("## Per-Language Accuracy")
    lines.append("")
    lines.append("| Language | Correct | Total | Accuracy |")
    lines.append("|----------|---------|-------|----------|")
    for lang, stats in sorted(ic.get("per_language", {}).items()):
        lines.append(f"| {lang} | {stats['correct']} | {stats['total']} | {stats['accuracy']:.2%} |")
    lines.append("")

    # Per-category
    lines.append("## Per-Category Accuracy")
    lines.append("")
    lines.append("| Category | Correct | Total | Accuracy |")
    lines.append("|----------|---------|-------|----------|")
    for cat, stats in sorted(ic.get("per_category", {}).items(), key=lambda x: x[1]["accuracy"]):
        lines.append(f"| {cat} | {stats['correct']} | {stats['total']} | {stats['accuracy']:.2%} |")
    lines.append("")

    # Hardest categories
    lines.append("## Top 5 Hardest Categories")
    lines.append("")
    for item in hardest:
        lines.append(f"- **{item['category']}**: {item['accuracy']:.2%} ({item['correct']}/{item['total']})")
    lines.append("")

    # Confusion matrix
    lines.append("## Confusion Matrix")
    lines.append("")
    cm = ic.get("confusion_matrix", {})
    all_labels = sorted(set(list(cm.keys()) + [lbl for row in cm.values() for lbl in row.keys()]))
    header = "| Expected \\ Predicted | " + " | ".join(all_labels) + " |"
    sep = "|" + "---|" * (len(all_labels) + 1)
    lines.append(header)
    lines.append(sep)
    for expected in all_labels:
        row_data = cm.get(expected, {})
        cells = [str(row_data.get(pred, 0)) for pred in all_labels]
        lines.append(f"| {expected} | " + " | ".join(cells) + " |")
    lines.append("")

    # Misclassifications
    lines.append(f"## Misclassified Scenarios ({len(misclassified)} total)")
    lines.append("")
    if misclassified:
        lines.append("| ID | Category | Language | Expected | Predicted | Conf | Message |")
        lines.append("|----|----------|----------|----------|-----------|------|---------|")
        for m in misclassified[:18]:
            msg = m.get("message", "")[:60].replace("|", "\\|")
            conf = f"{m.get('confidence', 0):.2f}"
            lines.append(f"| {m['scenario_id']} | {m['category']} | {m['language']} | {m['expected']} | {m['predicted']} | {conf} | {msg} |")
    lines.append("")

    # Agent evaluation averages
    if ae:
        lines.append("## Agent Evaluation Averages")
        lines.append("")
        lines.append("| Rubric | Mean Score |")
        lines.append("|--------|-----------|")
        for key, val in ae.items():
            if val is not None:
                lines.append(f"| {key} | {val} |")
        lines.append("")

    # Components
    comp = summary.get("components_used", {})
    lines.append("## Components Used")
    lines.append("")
    for k, v in comp.items():
        status = "✓" if v else "✗"
        if isinstance(v, str):
            status = f"✓ ({v})"
        lines.append(f"- **{k}**: {status}")
    lines.append("")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    run_benchmark()

