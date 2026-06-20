#!/usr/bin/env python3
"""
RecoveryBench — Inter-Annotator Agreement Calculator

Computes Cohen's Kappa, Krippendorff's Alpha, and percentage agreement
across multiple annotators using the annotation data from the annotation tool.

Usage:
    python annotation/inter_annotator_agreement.py

Output:
    annotation/reports/iaa_report.json
    annotation/reports/iaa_report.md
"""

import sys
import json
import logging
from pathlib import Path
from collections import defaultdict, Counter
from itertools import combinations
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recoverybench.iaa")

# Paths
DATA_DIR = Path(__file__).parent / "data"
REPORTS_DIR = Path(__file__).parent / "reports"
ANNOTATIONS_FILE = DATA_DIR / "annotations.json"
REPORT_JSON = REPORTS_DIR / "iaa_report.json"
REPORT_MD = REPORTS_DIR / "iaa_report.md"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def load_annotations():
    """Load annotations from file."""
    if not ANNOTATIONS_FILE.exists():
        logger.warning(f"No annotations file found at {ANNOTATIONS_FILE}")
        return []
    with open(ANNOTATIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def cohens_kappa(labels_a, labels_b):
    """
    Compute Cohen's Kappa between two annotators.

    Args:
        labels_a: List of labels from annotator A
        labels_b: List of labels from annotator B

    Returns:
        float: Cohen's Kappa score (-1 to 1)
    """
    assert len(labels_a) == len(labels_b), "Label lists must be same length"
    n = len(labels_a)
    if n == 0:
        return 0.0

    # All possible categories
    categories = sorted(set(labels_a) | set(labels_b))
    k = len(categories)
    cat_to_idx = {c: i for i, c in enumerate(categories)}

    # Confusion matrix
    matrix = [[0] * k for _ in range(k)]
    for la, lb in zip(labels_a, labels_b):
        matrix[cat_to_idx[la]][cat_to_idx[lb]] += 1

    # Observed agreement
    po = sum(matrix[i][i] for i in range(k)) / n

    # Expected agreement
    row_sums = [sum(matrix[i]) for i in range(k)]
    col_sums = [sum(matrix[j][i] for j in range(k)) for i in range(k)]
    pe = sum(row_sums[i] * col_sums[i] for i in range(k)) / (n * n)

    if pe == 1.0:
        return 1.0

    kappa = (po - pe) / (1 - pe)
    return round(kappa, 4)


def percentage_agreement(labels_a, labels_b):
    """Compute simple percentage agreement."""
    if not labels_a:
        return 0.0
    matches = sum(1 for a, b in zip(labels_a, labels_b) if a == b)
    return round(matches / len(labels_a), 4)


def krippendorff_alpha_nominal(annotations_by_annotator):
    """
    Compute Krippendorff's Alpha for nominal data.

    Args:
        annotations_by_annotator: Dict[annotator_id -> Dict[item_id -> label]]

    Returns:
        float: Krippendorff's Alpha (-1 to 1)
    """
    # Build reliability matrix
    annotators = list(annotations_by_annotator.keys())
    all_items = set()
    for ann_labels in annotations_by_annotator.values():
        all_items.update(ann_labels.keys())
    items = sorted(all_items)

    if len(annotators) < 2 or len(items) < 2:
        return 0.0

    # Count coincidences
    all_values = set()
    for ann_labels in annotations_by_annotator.values():
        all_values.update(ann_labels.values())
    values = sorted(all_values)

    # Observed disagreement
    n_total = 0
    observed_disagree = 0

    for item in items:
        item_labels = []
        for ann in annotators:
            label = annotations_by_annotator[ann].get(item)
            if label is not None:
                item_labels.append(label)

        m = len(item_labels)
        if m < 2:
            continue

        n_total += m
        # Count disagreements within this item
        for i in range(len(item_labels)):
            for j in range(i + 1, len(item_labels)):
                if item_labels[i] != item_labels[j]:
                    observed_disagree += 1

    if n_total < 2:
        return 0.0

    # Total pairs
    total_pairs = 0
    for item in items:
        item_labels = []
        for ann in annotators:
            label = annotations_by_annotator[ann].get(item)
            if label is not None:
                item_labels.append(label)
        m = len(item_labels)
        if m >= 2:
            total_pairs += m * (m - 1) / 2

    if total_pairs == 0:
        return 0.0

    do = observed_disagree / total_pairs

    # Expected disagreement
    value_counts = Counter()
    for ann_labels in annotations_by_annotator.values():
        value_counts.update(ann_labels.values())

    total_labels = sum(value_counts.values())
    if total_labels < 2:
        return 0.0

    de = 0
    for v1 in values:
        for v2 in values:
            if v1 != v2:
                de += value_counts[v1] * value_counts[v2]
    de = de / (total_labels * (total_labels - 1))

    if de == 0:
        return 1.0

    alpha = 1 - (do / de)
    return round(alpha, 4)


def compute_iaa(annotations):
    """
    Compute inter-annotator agreement metrics.

    Returns:
        Dict with agreement metrics
    """
    if not annotations:
        return {"error": "No annotations available"}

    # Group by annotator
    by_annotator = defaultdict(list)
    for ann in annotations:
        by_annotator[ann["annotator_id"]].append(ann)

    annotators = sorted(by_annotator.keys())
    n_annotators = len(annotators)

    print(f"Found {len(annotations)} annotations from {n_annotators} annotator(s)")

    results = {
        "computed_at": datetime.now().isoformat(),
        "total_annotations": len(annotations),
        "annotator_count": n_annotators,
        "annotators": {},
        "pairwise_agreement": {},
        "overall": {},
    }

    # Per-annotator stats
    for ann_id in annotators:
        ann_list = by_annotator[ann_id]
        intent_dist = Counter(a["labels"]["intent"] for a in ann_list)
        agreement_with_expected = sum(
            1 for a in ann_list if a.get("agreement_with_expected", False)
        )
        results["annotators"][ann_id] = {
            "count": len(ann_list),
            "intent_distribution": dict(intent_dist),
            "agreement_with_expected": round(
                agreement_with_expected / len(ann_list) * 100, 1
            ) if ann_list else 0,
            "avg_tone_score": round(
                sum(a["labels"].get("tone_score", 5) for a in ann_list) / len(ann_list), 2
            ),
            "avg_quality_score": round(
                sum(a["labels"].get("agent_quality_score", 5) for a in ann_list) / len(ann_list), 2
            ),
        }

    # Pairwise agreement (if multiple annotators)
    if n_annotators >= 2:
        # Group annotations by conversation_id per annotator
        ann_by_conv = {}
        for ann_id in annotators:
            ann_by_conv[ann_id] = {}
            for a in by_annotator[ann_id]:
                conv_id = a.get("conversation_id", a.get("conversation_index"))
                ann_by_conv[ann_id][conv_id] = a["labels"]["intent"]

        # Pairwise Cohen's Kappa
        for ann_a, ann_b in combinations(annotators, 2):
            # Find common conversations
            common_convs = set(ann_by_conv[ann_a].keys()) & set(ann_by_conv[ann_b].keys())
            if not common_convs:
                results["pairwise_agreement"][f"{ann_a}_vs_{ann_b}"] = {
                    "common_items": 0,
                    "note": "No overlapping annotations",
                }
                continue

            labels_a = [ann_by_conv[ann_a][c] for c in sorted(common_convs)]
            labels_b = [ann_by_conv[ann_b][c] for c in sorted(common_convs)]

            kappa = cohens_kappa(labels_a, labels_b)
            pct_agree = percentage_agreement(labels_a, labels_b)

            results["pairwise_agreement"][f"{ann_a}_vs_{ann_b}"] = {
                "common_items": len(common_convs),
                "cohens_kappa": kappa,
                "percentage_agreement": pct_agree,
                "kappa_interpretation": interpret_kappa(kappa),
            }

        # Krippendorff's Alpha (all annotators)
        alpha_input = {}
        for ann_id in annotators:
            alpha_input[ann_id] = ann_by_conv[ann_id]
        alpha = krippendorff_alpha_nominal(alpha_input)
        results["overall"]["krippendorffs_alpha"] = alpha
        results["overall"]["alpha_interpretation"] = interpret_alpha(alpha)
    else:
        # Single annotator — compute agreement with expected labels
        ann_id = annotators[0]
        ann_list = by_annotator[ann_id]
        expected = [a.get("expected_intent", "") for a in ann_list]
        actual = [a["labels"]["intent"] for a in ann_list]
        kappa = cohens_kappa(actual, expected)
        pct = percentage_agreement(actual, expected)

        results["pairwise_agreement"]["annotator_vs_expected"] = {
            "common_items": len(ann_list),
            "cohens_kappa": kappa,
            "percentage_agreement": pct,
            "kappa_interpretation": interpret_kappa(kappa),
        }
        results["overall"]["note"] = (
            "Only 1 annotator found. Showing agreement with expected labels. "
            "For proper IAA, need ≥2 annotators labeling the same conversations."
        )

    # Compliance agreement
    compliance_labels = defaultdict(list)
    for ann in annotations:
        conv_id = ann.get("conversation_id", ann.get("conversation_index"))
        compliance_labels[conv_id].append(ann["labels"].get("compliance", ""))

    multi_labeled = {k: v for k, v in compliance_labels.items() if len(v) >= 2}
    if multi_labeled:
        agree_count = sum(
            1 for labels in multi_labeled.values()
            if len(set(labels)) == 1
        )
        results["overall"]["compliance_agreement"] = round(
            agree_count / len(multi_labeled) * 100, 1
        )

    return results


def interpret_kappa(kappa):
    """Interpret Cohen's Kappa value."""
    if kappa < 0:
        return "Less than chance agreement"
    elif kappa < 0.20:
        return "Slight agreement"
    elif kappa < 0.40:
        return "Fair agreement"
    elif kappa < 0.60:
        return "Moderate agreement"
    elif kappa < 0.80:
        return "Substantial agreement"
    else:
        return "Almost perfect agreement"


def interpret_alpha(alpha):
    """Interpret Krippendorff's Alpha value."""
    if alpha < 0.667:
        return "Unreliable — should not draw conclusions"
    elif alpha < 0.800:
        return "Tentatively acceptable — use with caution"
    else:
        return "Reliable — acceptable for most purposes"


def generate_report(results):
    """Generate markdown report from IAA results."""
    lines = [
        "# Inter-Annotator Agreement Report",
        "",
        f"**Computed:** {results.get('computed_at', 'N/A')}",
        f"**Total Annotations:** {results.get('total_annotations', 0)}",
        f"**Annotators:** {results.get('annotator_count', 0)}",
        "",
        "---",
        "",
    ]

    # Per-annotator stats
    lines.append("## Annotator Statistics")
    lines.append("")
    lines.append("| Annotator | Annotations | Agree w/ Expected | Avg Tone | Avg Quality |")
    lines.append("|-----------|-------------|-------------------|----------|-------------|")
    for ann_id, stats in results.get("annotators", {}).items():
        lines.append(
            f"| {ann_id} | {stats['count']} | {stats['agreement_with_expected']}% | "
            f"{stats['avg_tone_score']} | {stats['avg_quality_score']} |"
        )
    lines.append("")

    # Pairwise
    lines.append("## Pairwise Agreement")
    lines.append("")
    for pair, stats in results.get("pairwise_agreement", {}).items():
        lines.append(f"### {pair}")
        if stats.get("common_items", 0) == 0:
            lines.append(f"  {stats.get('note', 'No data')}")
        else:
            lines.append(f"- **Common items:** {stats['common_items']}")
            lines.append(f"- **Cohen's Kappa:** {stats.get('cohens_kappa', 'N/A')}")
            lines.append(f"- **% Agreement:** {stats.get('percentage_agreement', 'N/A')}")
            lines.append(f"- **Interpretation:** {stats.get('kappa_interpretation', 'N/A')}")
        lines.append("")

    # Overall
    lines.append("## Overall")
    lines.append("")
    overall = results.get("overall", {})
    if "krippendorffs_alpha" in overall:
        lines.append(f"- **Krippendorff's Alpha:** {overall['krippendorffs_alpha']}")
        lines.append(f"- **Interpretation:** {overall['alpha_interpretation']}")
    if "note" in overall:
        lines.append(f"\n> **Note:** {overall['note']}")
    if "compliance_agreement" in overall:
        lines.append(f"- **Compliance Agreement:** {overall['compliance_agreement']}%")
    lines.append("")

    return "\n".join(lines)


def main():
    """Run IAA computation."""
    print("=" * 60)
    print("RecoveryBench — Inter-Annotator Agreement")
    print("=" * 60)

    annotations = load_annotations()

    if not annotations:
        print("\nNo annotations found. To generate sample annotations:")
        print("  1. Run: python simulator/generate_conversation_dataset.py")
        print("  2. Run: python annotation/app.py")
        print("  3. Annotate conversations through the web interface")

        # Generate sample annotations for demonstration
        print("\nGenerating sample annotations for demonstration...")
        sample_annotations = generate_sample_annotations()
        if sample_annotations:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(ANNOTATIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(sample_annotations, f, indent=2)
            annotations = sample_annotations
            print(f"Generated {len(annotations)} sample annotations")
        else:
            print("Could not generate samples. Exiting.")
            return

    results = compute_iaa(annotations)

    # Save JSON report
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] JSON report saved to {REPORT_JSON}")

    # Save markdown report
    report_md = generate_report(results)
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"[OK] Markdown report saved to {REPORT_MD}")

    # Print summary
    print("\n--- Summary ---")
    for pair, stats in results.get("pairwise_agreement", {}).items():
        kappa = stats.get("cohens_kappa", "N/A")
        pct = stats.get("percentage_agreement", "N/A")
        print(f"  {pair}: κ={kappa}, agreement={pct}")

    overall = results.get("overall", {})
    if "krippendorffs_alpha" in overall:
        print(f"\n  Krippendorff's α = {overall['krippendorffs_alpha']}")
        print(f"  → {overall['alpha_interpretation']}")

    print("\n✅ IAA computation complete!")


def generate_sample_annotations():
    """Generate sample annotations from synthetic conversations for demo."""
    import random
    random.seed(42)

    intents = ["LIKELY_PAY", "NEEDS_REMINDER", "DISPUTE", "HIGH_RISK", "VAGUE", "ALREADY_PAID"]
    tones = ["Professional", "Empathetic", "Neutral", "Aggressive", "Threatening"]
    compliance = ["Compliant", "Non-compliant"]

    annotations = []
    for conv_idx in range(50):
        # Simulate 2 annotators labeling the same conversation
        true_intent = random.choice(intents)
        for ann_id in ["annotator_A", "annotator_B"]:
            # Add some noise to simulate disagreement
            if random.random() < 0.75:  # 75% agreement
                labeled_intent = true_intent
            else:
                labeled_intent = random.choice(intents)

            annotations.append({
                "annotation_id": f"sample-{ann_id}-{conv_idx}",
                "annotator_id": ann_id,
                "timestamp": datetime.now().isoformat(),
                "conversation_id": f"conv-{conv_idx:04d}",
                "conversation_index": conv_idx,
                "language": random.choice(["English", "Hindi", "Bengali", "Hinglish"]),
                "labels": {
                    "intent": labeled_intent,
                    "intent_confidence": round(random.uniform(0.5, 1.0), 2),
                    "compliance": random.choice(compliance),
                    "severity": random.choice(["None", "Minor", "Moderate", "Critical"]),
                    "tone": random.choice(tones),
                    "tone_score": round(random.uniform(3, 9), 1),
                    "agent_quality_score": round(random.uniform(3, 9), 1),
                },
                "notes": "",
                "expected_intent": true_intent,
                "agreement_with_expected": labeled_intent == true_intent,
            })

    return annotations


if __name__ == "__main__":
    main()
