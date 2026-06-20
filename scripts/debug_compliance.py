#!/usr/bin/env python3
"""Debug compliance keyword matching."""
import sys
sys.path.insert(0, ".")

from pipeline.evaluator import AgentEvaluator, _THREAT_KEYWORDS, _HARASSMENT_KEYWORDS, _COERCION_KEYWORDS

e = AgentEvaluator()

test_msgs = [
    "You are a fraud and a cheat, pay up now",
    "Borrow from your relatives to pay us back immediately",
]

for msg in test_msgs:
    msg_lower = msg.lower()
    print(f"\n--- Agent msg: {msg}")
    
    # Check threat keywords
    for kw in _THREAT_KEYWORDS:
        if kw in msg_lower:
            print(f"  THREAT match: '{kw}'")
    
    # Check harassment keywords
    for kw in _HARASSMENT_KEYWORDS:
        if kw in msg_lower:
            print(f"  HARASSMENT match: '{kw}'")
    
    # Check coercion keywords
    for kw in _COERCION_KEYWORDS:
        if kw in msg_lower:
            print(f"  COERCION match: '{kw}'")
    
    # Run evaluator
    result = e.evaluate(
        borrower_message="I can't pay right now",
        intent="HIGH_RISK",
        confidence=0.75,
        agent_response=msg,
    )
    print(f"  compliance_score: {result['compliance_score']}")
