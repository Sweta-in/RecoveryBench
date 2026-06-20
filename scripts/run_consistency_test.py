#!/usr/bin/env python3
"""Checkpoint 6 — Consistency Test: 5 inputs × 3 runs each."""
import sys
import json
sys.path.insert(0, ".")

from pipeline.evaluator import AgentEvaluator

e = AgentEvaluator()
print(f"Backend: {e.backend} ({e.backend_model})")

test_cases = [
    {
        "borrower_message": "Bhai salary nahi aayi abhi, next week kar dunga",
        "intent": "LIKELY_PAY",
        "confidence": 0.88,
        "agent_response": "We understand you're waiting for your salary. We've noted your commitment to pay next week. Your outstanding EMI is ₹5,000.",
    },
    {
        "borrower_message": "Amount galat hai, mera loan toh isse kam tha",
        "intent": "DISPUTE",
        "confidence": 0.78,
        "agent_response": "We take your concern seriously. Let us verify your records. Our team will review and get back to you within 48 hours.",
    },
    {
        "borrower_message": "STOP CALLING ME!! I will file complaint!",
        "intent": "HIGH_RISK",
        "confidence": 0.95,
        "agent_response": "I understand your frustration. Let me connect you with our senior resolution specialist who can address your concerns.",
    },
    {
        "borrower_message": "haan yaad hai, bhool gaya tha",
        "intent": "NEEDS_REMINDER",
        "confidence": 0.82,
        "agent_response": "No worries. Your outstanding EMI is ₹3,500 due since May 15. You can pay via UPI, NEFT, or our website.",
    },
    {
        "borrower_message": "dekhte hain kya hota hai",
        "intent": "VAGUE",
        "confidence": 0.55,
        "agent_response": "We'd like to help you plan your payment. Would you like to discuss options? Your account has ₹7,200 outstanding.",
    },
]

result = e.run_consistency_test(test_cases, runs=3)

print(f"\n{'='*70}")
print("CONSISTENCY TEST RESULTS")
print(f"{'='*70}")
print(f"Backend: {result['backend']}")
print(f"Runs per case: {result['runs_per_case']}")
print(f"\nAggregate variance per rubric:")
for rubric, var in result["aggregate_variance"].items():
    flag = " ⚠️ HIGH VARIANCE" if var > 1.5 else ""
    print(f"  {rubric}: {var}{flag}")

print(f"\nPer-case breakdown:")
for case in result["per_case_results"]:
    print(f"\n  Case {case['case_index']}: {case['input_summary']}")
    for rubric, var in case["variance_per_rubric"].items():
        flag = " ⚠️" if var > 1.5 else ""
        print(f"    {rubric}: variance={var}{flag}")
    # Show individual run scores
    for run_idx, run in enumerate(case["runs"]):
        print(f"    Run {run_idx+1}: overall={run['overall_score']}, "
              f"intent={run['intent_accuracy']}, tone={run['tone_score']}, "
              f"compliance={run['compliance_score']}, escalation={run['escalation_score']}")

if result["flags"]:
    print(f"\n  FLAGGED (variance > 1.5):")
    for flag in result["flags"]:
        print(f"  Case {flag['case_index']} -- {flag['rubric']}: variance={flag['variance']}")
else:
    print(f"\n  [OK] No rubrics with variance > 1.5")

# Save to JSON for report
with open("scripts/consistency_results.json", "w") as f:
    json.dump(result, f, indent=2)
print(f"\nResults saved to scripts/consistency_results.json")
