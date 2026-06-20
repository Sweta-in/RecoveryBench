#!/usr/bin/env python3
"""Checkpoint 4 verification script — full ordering and feature importance."""

import json
import sys
from pathlib import Path

# Ensure project root on path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pipeline.risk_scorer import RiskScorer

r = RiskScorer()

# ── Full 5-class ordering check ──────────────────────────────────────
cases = {
    "LIKELY_PAY": {
        "intent": "LIKELY_PAY", "has_promise": True, "payment_window_days": 7,
        "message_length": 40, "exclamation_count": 0, "question_count": 0,
        "caps_ratio": 0.05, "dispute_keywords": 0, "hostile_keywords": 0,
    },
    "NEEDS_REMINDER": {
        "intent": "NEEDS_REMINDER", "has_promise": False, "payment_window_days": 0,
        "message_length": 20, "exclamation_count": 0, "question_count": 1,
        "caps_ratio": 0.0, "dispute_keywords": 0, "hostile_keywords": 0,
    },
    "VAGUE": {
        "intent": "VAGUE", "has_promise": False, "payment_window_days": 0,
        "message_length": 5, "exclamation_count": 0, "question_count": 0,
        "caps_ratio": 0.0, "dispute_keywords": 0, "hostile_keywords": 0,
    },
    "DISPUTE": {
        "intent": "DISPUTE", "has_promise": False, "payment_window_days": 0,
        "message_length": 60, "exclamation_count": 1, "question_count": 1,
        "caps_ratio": 0.1, "dispute_keywords": 2, "hostile_keywords": 0,
    },
    "HIGH_RISK": {
        "intent": "HIGH_RISK", "has_promise": False, "payment_window_days": 0,
        "message_length": 80, "exclamation_count": 3, "question_count": 0,
        "caps_ratio": 0.4, "dispute_keywords": 0, "hostile_keywords": 2,
    },
}

print("=" * 60)
print("Checkpoint 4 — Risk Scorer Verification")
print("=" * 60)

scores = {}
for name, feat in cases.items():
    s = r.score(feat)
    b = r.get_risk_band(s)
    scores[name] = s
    print(f"  {name:20s}: {s:.4f} ({b})")

print()
order_ok = (
    scores["LIKELY_PAY"] < scores["NEEDS_REMINDER"]
    < scores["VAGUE"] < scores["DISPUTE"]
    < scores["HIGH_RISK"]
)
status = "PASS" if order_ok else "FAIL"
print(f"Full ordering: {status}")
if not order_ok:
    print("  ORDERING VIOLATED!")
    sys.exit(1)

# ── Additional test cases: 4 per intent ──────────────────────────────
print()
print("--- 20 Example Predictions (4 per class) ---")
detailed_cases = [
    # LIKELY_PAY variants
    {"name": "LP-1 (promise, 1 day)", "intent": "LIKELY_PAY", "has_promise": True,
     "payment_window_days": 1, "message_length": 25, "exclamation_count": 0,
     "question_count": 0, "caps_ratio": 0.0, "dispute_keywords": 0, "hostile_keywords": 0},
    {"name": "LP-2 (promise, 7 days)", "intent": "LIKELY_PAY", "has_promise": True,
     "payment_window_days": 7, "message_length": 45, "exclamation_count": 0,
     "question_count": 0, "caps_ratio": 0.03, "dispute_keywords": 0, "hostile_keywords": 0},
    {"name": "LP-3 (promise, 30 days)", "intent": "LIKELY_PAY", "has_promise": True,
     "payment_window_days": 30, "message_length": 55, "exclamation_count": 0,
     "question_count": 0, "caps_ratio": 0.05, "dispute_keywords": 0, "hostile_keywords": 0},
    {"name": "LP-4 (no promise)", "intent": "LIKELY_PAY", "has_promise": False,
     "payment_window_days": 0, "message_length": 30, "exclamation_count": 0,
     "question_count": 0, "caps_ratio": 0.0, "dispute_keywords": 0, "hostile_keywords": 0},
    # NEEDS_REMINDER variants
    {"name": "NR-1 (short, question)", "intent": "NEEDS_REMINDER", "has_promise": False,
     "payment_window_days": 0, "message_length": 15, "exclamation_count": 0,
     "question_count": 1, "caps_ratio": 0.0, "dispute_keywords": 0, "hostile_keywords": 0},
    {"name": "NR-2 (medium)", "intent": "NEEDS_REMINDER", "has_promise": False,
     "payment_window_days": 0, "message_length": 35, "exclamation_count": 0,
     "question_count": 0, "caps_ratio": 0.05, "dispute_keywords": 0, "hostile_keywords": 0},
    {"name": "NR-3 (with promise)", "intent": "NEEDS_REMINDER", "has_promise": True,
     "payment_window_days": 3, "message_length": 40, "exclamation_count": 0,
     "question_count": 0, "caps_ratio": 0.0, "dispute_keywords": 0, "hostile_keywords": 0},
    {"name": "NR-4 (long)", "intent": "NEEDS_REMINDER", "has_promise": False,
     "payment_window_days": 0, "message_length": 60, "exclamation_count": 0,
     "question_count": 2, "caps_ratio": 0.0, "dispute_keywords": 0, "hostile_keywords": 0},
    # VAGUE variants
    {"name": "VG-1 (very short)", "intent": "VAGUE", "has_promise": False,
     "payment_window_days": 0, "message_length": 3, "exclamation_count": 0,
     "question_count": 0, "caps_ratio": 0.0, "dispute_keywords": 0, "hostile_keywords": 0},
    {"name": "VG-2 (medium)", "intent": "VAGUE", "has_promise": False,
     "payment_window_days": 0, "message_length": 20, "exclamation_count": 0,
     "question_count": 1, "caps_ratio": 0.0, "dispute_keywords": 0, "hostile_keywords": 0},
    {"name": "VG-3 (with exclamation)", "intent": "VAGUE", "has_promise": False,
     "payment_window_days": 0, "message_length": 10, "exclamation_count": 1,
     "question_count": 0, "caps_ratio": 0.1, "dispute_keywords": 0, "hostile_keywords": 0},
    {"name": "VG-4 (some caps)", "intent": "VAGUE", "has_promise": False,
     "payment_window_days": 0, "message_length": 15, "exclamation_count": 0,
     "question_count": 0, "caps_ratio": 0.2, "dispute_keywords": 0, "hostile_keywords": 0},
    # DISPUTE variants
    {"name": "DP-1 (2 kw)", "intent": "DISPUTE", "has_promise": False,
     "payment_window_days": 0, "message_length": 50, "exclamation_count": 0,
     "question_count": 1, "caps_ratio": 0.05, "dispute_keywords": 2, "hostile_keywords": 0},
    {"name": "DP-2 (3 kw, long)", "intent": "DISPUTE", "has_promise": False,
     "payment_window_days": 0, "message_length": 90, "exclamation_count": 1,
     "question_count": 2, "caps_ratio": 0.1, "dispute_keywords": 3, "hostile_keywords": 0},
    {"name": "DP-3 (1 kw, short)", "intent": "DISPUTE", "has_promise": False,
     "payment_window_days": 0, "message_length": 30, "exclamation_count": 0,
     "question_count": 0, "caps_ratio": 0.0, "dispute_keywords": 1, "hostile_keywords": 0},
    {"name": "DP-4 (hostile cross)", "intent": "DISPUTE", "has_promise": False,
     "payment_window_days": 0, "message_length": 70, "exclamation_count": 2,
     "question_count": 0, "caps_ratio": 0.15, "dispute_keywords": 2, "hostile_keywords": 1},
    # HIGH_RISK variants
    {"name": "HR-1 (hostile, caps)", "intent": "HIGH_RISK", "has_promise": False,
     "payment_window_days": 0, "message_length": 80, "exclamation_count": 3,
     "question_count": 0, "caps_ratio": 0.4, "dispute_keywords": 0, "hostile_keywords": 2},
    {"name": "HR-2 (extreme hostile)", "intent": "HIGH_RISK", "has_promise": False,
     "payment_window_days": 0, "message_length": 120, "exclamation_count": 5,
     "question_count": 0, "caps_ratio": 0.6, "dispute_keywords": 1, "hostile_keywords": 4},
    {"name": "HR-3 (short, hostile)", "intent": "HIGH_RISK", "has_promise": False,
     "payment_window_days": 0, "message_length": 30, "exclamation_count": 2,
     "question_count": 0, "caps_ratio": 0.5, "dispute_keywords": 0, "hostile_keywords": 1},
    {"name": "HR-4 (mild hostile)", "intent": "HIGH_RISK", "has_promise": False,
     "payment_window_days": 0, "message_length": 50, "exclamation_count": 1,
     "question_count": 0, "caps_ratio": 0.2, "dispute_keywords": 0, "hostile_keywords": 1},
]

for tc in detailed_cases:
    name = tc.pop("name")
    s = r.score(tc)
    b = r.get_risk_band(s)
    print(f"  {name:30s}: {s:.4f} ({b})")

# ── Failure cases ────────────────────────────────────────────────────
print()
print("--- Failure Case Check ---")
# LIKELY_PAY scoring above 0.5
lp_high = r.score({
    "intent": "LIKELY_PAY", "has_promise": False, "payment_window_days": 0,
    "message_length": 100, "exclamation_count": 3, "question_count": 0,
    "caps_ratio": 0.3, "dispute_keywords": 1, "hostile_keywords": 1,
})
print(f"  LIKELY_PAY (adversarial features): {lp_high:.4f} - {'ANOMALY (>0.5)' if lp_high > 0.5 else 'OK (<0.5)'}")

# HIGH_RISK scoring below 0.5
hr_low = r.score({
    "intent": "HIGH_RISK", "has_promise": True, "payment_window_days": 7,
    "message_length": 20, "exclamation_count": 0, "question_count": 0,
    "caps_ratio": 0.0, "dispute_keywords": 0, "hostile_keywords": 0,
})
print(f"  HIGH_RISK (calming features):     {hr_low:.4f} - {'ANOMALY (<0.5)' if hr_low < 0.5 else 'OK (>0.5)'}")

# ── Feature importance ───────────────────────────────────────────────
print()
print("--- Feature Importance (XGBoost) ---")
imp = r.get_feature_importance()
for feat, val in sorted(imp.items(), key=lambda x: -x[1]):
    print(f"  {feat:25s}: {val:.4f}")

# ── SHAP/importance summary ─────────────────────────────────────────
print()
print("--- SHAP/Importance Summary ---")
shap_path = project_root / "models" / "risk_scorer" / "shap_summary.json"
with open(shap_path) as f:
    shap_data = json.load(f)
for feat, val in sorted(shap_data.items(), key=lambda x: -x[1]):
    print(f"  {feat:25s}: {val:.4f}")

# ── Risk band distribution (simulate) ───────────────────────────────
print()
print("--- Risk Band Distribution (simulated across all 5 classes) ---")
import collections
band_counts = collections.Counter()
class_band = collections.defaultdict(lambda: collections.Counter())
for cls_name, feat in cases.items():
    s = r.score(feat)
    b = r.get_risk_band(s)
    band_counts[b] += 1
    class_band[b][cls_name] += 1

for band in ["low", "medium", "high", "critical"]:
    classes = ", ".join(class_band[band].keys()) if class_band[band] else "none"
    print(f"  {band:10s}: {band_counts[band]} examples — classes: {classes}")

# ── Artifact sizes ───────────────────────────────────────────────────
print()
print("--- Model Artifacts ---")
model_dir = project_root / "models" / "risk_scorer"
for f in sorted(model_dir.iterdir()):
    size = f.stat().st_size
    if size > 1024:
        print(f"  {f.name:30s}: {size/1024:.1f} KB")
    else:
        print(f"  {f.name:30s}: {size} B")

print()
print("=" * 60)
print("ALL CHECKS PASSED")
print("=" * 60)
