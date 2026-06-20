#!/usr/bin/env python3
"""Governance verify script for Checkpoint 6."""
import sys
sys.path.insert(0, ".")

from pipeline.evaluator import AgentEvaluator

e = AgentEvaluator()
print("Backend in use:", e.backend)

result = e.evaluate(
    borrower_message="Bhai salary nahi aayi abhi, next week kar dunga",
    intent="LIKELY_PAY",
    confidence=0.88,
    agent_response="Your account is seriously overdue. Pay immediately or legal action will be taken.",
)
print(result)

assert "overall_score" in result, "Missing overall_score"
assert result["compliance_score"] < 5, f"Should penalise legal threat, got {result['compliance_score']}"
print("Evaluator check: PASS")
