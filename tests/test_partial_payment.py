#!/usr/bin/env python3
"""
RecoveryBench — PARTIAL_PAYMENT Keyword Override Test Suite

Tests the PARTIAL_PAYMENT keyword override in predict.py.
Same pattern as the earlier HARDSHIP fix's 8/8 test.

10 cases:
  5 positive (clear partial-payment offers)
  3 negative (must NOT trigger partial payment)
  2 edge cases (ambiguous inputs)

Run: python -m pytest tests/test_partial_payment.py -v
  or: cd recoverbench && python tests/test_partial_payment.py
"""

import sys
import os

# Ensure recoverbench root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.intent_classifier.predict import IntentClassifier


def test_partial_payment():
    clf = IntentClassifier()

    cases = [
        # ── Positive cases: must classify as PARTIAL_PAYMENT ─────────────
        {
            "id": "PP-01",
            "text": "I can pay 6,000 now. Rest, I can pay after",
            "expected": "PARTIAL_PAYMENT",
            "desc": "Clear partial offer with specific amount (Bug 1 exact case)",
        },
        {
            "id": "PP-02",
            "text": "Can I pay half now and half later?",
            "expected": "PARTIAL_PAYMENT",
            "desc": "Split payment request",
        },
        {
            "id": "PP-03",
            "text": "I'll pay in instalments",
            "expected": "PARTIAL_PAYMENT",
            "desc": "EMI/instalment request",
        },
        {
            "id": "PP-04",
            "text": "Kuch abhi de sakta hun, baki baad mein",
            "expected": "PARTIAL_PAYMENT",
            "desc": "Hindi partial offer",
        },
        {
            "id": "PP-05",
            "text": "Pay part now part later please",
            "expected": "PARTIAL_PAYMENT",
            "desc": "English explicit partial offer",
        },

        # ── Negative cases: must NOT classify as PARTIAL_PAYMENT ─────────
        {
            "id": "PP-NEG-01",
            "text": "I already paid this EMI last week",
            "expected": "ALREADY_PAID",
            "desc": "ALREADY_PAID must not trigger partial payment",
        },
        {
            "id": "PP-NEG-02",
            "text": "I will pay by Friday",
            "expected": "LIKELY_PAY",
            "desc": "Full PTP must not trigger partial payment",
        },
        {
            "id": "PP-NEG-03",
            "text": "I can't afford to pay this month",
            "expected": "HARDSHIP",
            "desc": "Hardship must not trigger partial payment",
        },

        # ── Edge cases ───────────────────────────────────────────────────
        {
            "id": "PP-EDGE-01",
            "text": "I already paid half",
            "expected": "PARTIAL_PAYMENT",
            "desc": "Ambiguous — 'pay half' matches PARTIAL_PAYMENT keywords; "
                    "PARTIAL_PAYMENT checked before ALREADY_PAID per priority chain",
        },
        {
            "id": "PP-EDGE-02",
            "text": "What if I can only pay part of it?",
            "expected": "PARTIAL_PAYMENT",
            "desc": "Question-shaped but contains 'pay part' → PARTIAL_PAYMENT keyword",
        },
    ]

    passed = 0
    failed = 0
    results = []

    for tc in cases:
        result = clf.predict(tc["text"])
        actual = result["label"]
        ok = actual == tc["expected"]

        status = "PASS" if ok else "FAIL"
        results.append({
            "id": tc["id"],
            "status": status,
            "expected": tc["expected"],
            "actual": actual,
            "confidence": result["confidence"],
            "desc": tc["desc"],
            "partial_kw": result.get("partial_payment_keyword_match", False),
            "hardship_kw": result.get("hardship_keyword_match", False),
            "keyword_match": result.get("keyword_match", False),
        })

        if ok:
            passed += 1
        else:
            failed += 1

    # Print results
    print(f"\n{'='*70}")
    print(f"  PARTIAL_PAYMENT Override Test — {len(cases)} cases")
    print(f"{'='*70}\n")

    for r in results:
        icon = "PASS" if r["status"] == "PASS" else "FAIL"
        print(f"  {icon} [{r['id']}] {r['desc']}")
        print(f"   Expected: {r['expected']}  |  Got: {r['actual']}  "
              f"(conf={r['confidence']:.2f}, partial_kw={r['partial_kw']}, "
              f"hardship_kw={r['hardship_kw']}, keyword={r['keyword_match']})")
        if r["status"] == "FAIL":
            print(f"   MISMATCH: expected {r['expected']}, got {r['actual']}")
        print()

    print(f"{'─'*70}")
    print(f"  TOTAL: {passed}/{len(cases)} PASSED  |  {failed} FAILED")
    print(f"{'─'*70}\n")

    # Assert for pytest
    for r in results:
        assert r["actual"] == r["expected"], (
            f"[{r['id']}] {r['desc']}: "
            f"expected {r['expected']}, got {r['actual']}"
        )


if __name__ == "__main__":
    test_partial_payment()
