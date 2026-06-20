#!/usr/bin/env python3
"""
RecoveryBench — Pipeline Statistics Generator

Generates a comprehensive statistics report from trace logs.
Outputs to traces/reports/pipeline_stats.json and prints a summary.

Usage:
    python traces/generate_stats.py
    python traces/generate_stats.py --output traces/reports/custom_stats.json
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import Counter

# Ensure project root is on path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from traces.logger import TraceLogger


def generate_pipeline_stats(trace_dir: str = None, output_path: str = None) -> dict:
    """
    Generate comprehensive pipeline statistics from trace logs.

    Args:
        trace_dir: Path to trace logs directory.
        output_path: Path to save the stats JSON report.

    Returns:
        Statistics dict.
    """
    default_trace_dir = str(Path(__file__).parent / "logs")
    default_output = str(Path(__file__).parent / "reports" / "pipeline_stats.json")

    trace_dir = trace_dir or default_trace_dir
    output_path = output_path or default_output

    trace_logger = TraceLogger(trace_dir=trace_dir)

    # Get basic stats
    basic_stats = trace_logger.get_stats()

    # Load all traces for detailed analysis
    all_traces = trace_logger.list_traces(limit=10000)
    trace_files = list(Path(trace_dir).glob("*.json"))

    # Intent distribution from responses
    intent_counts = Counter()
    risk_scores = []
    compliance_results = {"compliant": 0, "non_compliant": 0}
    languages_detected = Counter()
    promise_counts = {"with_promise": 0, "without_promise": 0}

    for trace_file in trace_files:
        try:
            with open(trace_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            response = data.get("response", {})
            if isinstance(response, dict):
                # Intent distribution
                intent = response.get("repayment_intent")
                if intent:
                    intent_counts[intent] += 1

                # Risk scores
                risk = response.get("risk_score")
                if risk is not None:
                    risk_scores.append(risk)

                # Compliance
                compliance = response.get("compliance", {})
                if isinstance(compliance, dict):
                    if compliance.get("compliant") is True:
                        compliance_results["compliant"] += 1
                    elif compliance.get("compliant") is False:
                        compliance_results["non_compliant"] += 1

                # Language
                lang = response.get("language")
                if lang:
                    languages_detected[lang] += 1

                # Promises
                if response.get("promise_to_pay") is True:
                    promise_counts["with_promise"] += 1
                elif response.get("promise_to_pay") is False:
                    promise_counts["without_promise"] += 1

        except Exception:
            continue

    # Build stats report
    stats_report = {
        "generated_at": datetime.utcnow().isoformat(),
        "summary": basic_stats,
        "pipeline_analysis": {
            "intent_distribution": dict(intent_counts.most_common()),
            "risk_score_stats": {
                "count": len(risk_scores),
                "mean": round(sum(risk_scores) / len(risk_scores), 4) if risk_scores else 0,
                "min": round(min(risk_scores), 4) if risk_scores else 0,
                "max": round(max(risk_scores), 4) if risk_scores else 0,
            },
            "compliance_breakdown": compliance_results,
            "language_distribution": dict(languages_detected.most_common()),
            "promise_breakdown": promise_counts,
        },
    }

    # Save report
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(stats_report, f, indent=2, ensure_ascii=False)

    return stats_report


def print_stats_summary(stats: dict):
    """Print a human-readable summary of pipeline stats."""
    summary = stats.get("summary", {})
    analysis = stats.get("pipeline_analysis", {})

    print(f"\n{'='*60}")
    print(f"  RECOVERYBENCH PIPELINE STATISTICS")
    print(f"  Generated: {stats.get('generated_at', '?')}")
    print(f"{'='*60}\n")

    # Basic metrics
    print(f"  -- API METRICS {'-'*42}")
    print(f"  Total requests:   {summary.get('total_traces', 0)}")
    print(f"  Successful:       {summary.get('success_count', 0)}")
    print(f"  Errors:           {summary.get('error_count', 0)}")
    print(f"  Error rate:       {summary.get('error_rate', 0)*100:.1f}%")
    print(f"  Avg latency:      {summary.get('avg_latency_ms', 0):.1f} ms")
    print(f"  P95 latency:      {summary.get('p95_latency_ms', 0):.1f} ms")
    print()

    # Intent distribution
    intents = analysis.get("intent_distribution", {})
    if intents:
        print(f"  -- INTENT DISTRIBUTION {'-'*34}")
        total_intents = sum(intents.values())
        for intent, count in intents.items():
            pct = (count / total_intents * 100) if total_intents > 0 else 0
            bar = "#" * int(pct / 5)
            print(f"  {intent:<18} {count:>4}  ({pct:>5.1f}%)  {bar}")
        print()

    # Risk scores
    risk = analysis.get("risk_score_stats", {})
    if risk.get("count", 0) > 0:
        print(f"  -- RISK SCORES {'-'*42}")
        print(f"  Analyzed:         {risk['count']}")
        print(f"  Mean:             {risk['mean']:.4f}")
        print(f"  Range:            {risk['min']:.4f} - {risk['max']:.4f}")
        print()

    # Compliance
    comp = analysis.get("compliance_breakdown", {})
    if comp.get("compliant", 0) + comp.get("non_compliant", 0) > 0:
        print(f"  -- COMPLIANCE {'-'*43}")
        print(f"  Compliant:        {comp.get('compliant', 0)}")
        print(f"  Non-compliant:    {comp.get('non_compliant', 0)}")
        print()

    # Languages
    langs = analysis.get("language_distribution", {})
    if langs:
        print(f"  -- LANGUAGES {'-'*44}")
        for lang, count in langs.items():
            print(f"  {lang:<18} {count:>4}")
        print()

    # Promises
    promises = analysis.get("promise_breakdown", {})
    if promises.get("with_promise", 0) + promises.get("without_promise", 0) > 0:
        print(f"  -- PROMISES {'-'*45}")
        print(f"  With promise:     {promises.get('with_promise', 0)}")
        print(f"  Without promise:  {promises.get('without_promise', 0)}")
        print()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate RecoveryBench pipeline statistics from trace logs."
    )
    parser.add_argument(
        "--trace-dir",
        default=None,
        help="Path to trace logs directory",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path for stats JSON",
    )
    args = parser.parse_args()

    stats = generate_pipeline_stats(
        trace_dir=args.trace_dir,
        output_path=args.output,
    )
    print_stats_summary(stats)

    output_path = args.output or str(Path(__file__).parent / "reports" / "pipeline_stats.json")
    print(f"  Report saved to: {output_path}\n")


if __name__ == "__main__":
    main()
