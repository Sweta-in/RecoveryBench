#!/usr/bin/env python3
"""Checkpoint 6 — Generate scored examples and edge case tests for report."""
import sys
import json
sys.path.insert(0, ".")

from pipeline.evaluator import AgentEvaluator

e = AgentEvaluator()
print(f"Backend: {e.backend} ({e.backend_model})")

# ── 10 scored examples: 2 per intent class ──
scored_examples = [
    # LIKELY_PAY — Good response
    {
        "label": "LIKELY_PAY #1 (Good agent response)",
        "borrower_message": "Bhai salary nahi aayi abhi, next week kar dunga",
        "intent": "LIKELY_PAY",
        "confidence": 0.88,
        "agent_response": "Thank you for confirming your commitment. We've noted your plan to pay next week after salary. Your outstanding EMI is Rs 5,000. We'll follow up then.",
    },
    # LIKELY_PAY — Bad response
    {
        "label": "LIKELY_PAY #2 (Bad agent response)",
        "borrower_message": "I will pay by next Friday for sure",
        "intent": "LIKELY_PAY",
        "confidence": 0.92,
        "agent_response": "This is your FINAL warning. Pay immediately or legal action will be taken against you. We will arrest you.",
    },
    # NEEDS_REMINDER — Good response
    {
        "label": "NEEDS_REMINDER #1 (Good agent response)",
        "borrower_message": "haan yaad hai, kitna dena hai?",
        "intent": "NEEDS_REMINDER",
        "confidence": 0.82,
        "agent_response": "Your outstanding EMI amount is Rs 3,500. The due date was June 1st. You can pay via UPI, NEFT, or visit our website. Would you like help setting up a payment?",
    },
    # NEEDS_REMINDER — Bad response
    {
        "label": "NEEDS_REMINDER #2 (Bad agent response)",
        "borrower_message": "bhool gaya tha, remind karo",
        "intent": "NEEDS_REMINDER",
        "confidence": 0.78,
        "agent_response": "You always forget! We will tell your employer about your loan default. Don't test our patience.",
    },
    # DISPUTE — Good response
    {
        "label": "DISPUTE #1 (Good agent response)",
        "borrower_message": "Amount galat hai, mera loan toh isse kam tha",
        "intent": "DISPUTE",
        "confidence": 0.78,
        "agent_response": "We take your concern seriously. Let us review your records and verify the amount. Our team will investigate and get back to you within 48 hours.",
    },
    # DISPUTE — Bad response
    {
        "label": "DISPUTE #2 (Bad agent response)",
        "borrower_message": "Yeh amount wrong hai check karo",
        "intent": "DISPUTE",
        "confidence": 0.75,
        "agent_response": "Pay now or we will file a case against you. No disputes accepted. Must pay now.",
    },
    # HIGH_RISK — Good response
    {
        "label": "HIGH_RISK #1 (Good agent response)",
        "borrower_message": "STOP CALLING ME!! I will file complaint against you!",
        "intent": "HIGH_RISK",
        "confidence": 0.95,
        "agent_response": "I understand your frustration, and I sincerely apologize for any inconvenience. Let me connect you with our senior resolution specialist who can better address your concerns directly.",
    },
    # HIGH_RISK — Bad response
    {
        "label": "HIGH_RISK #2 (Bad agent response)",
        "borrower_message": "band karo phone! harass mat karo mujhe!",
        "intent": "HIGH_RISK",
        "confidence": 0.92,
        "agent_response": "If you don't pay by tomorrow, police will come to your house. We will arrest you. You have no choice.",
    },
    # VAGUE — Good response
    {
        "label": "VAGUE #1 (Good agent response)",
        "borrower_message": "dekhte hain kya hota hai",
        "intent": "VAGUE",
        "confidence": 0.55,
        "agent_response": "We'd like to help you find a solution. Could you let us know your current situation? We have flexible payment plans that may work for you.",
    },
    # VAGUE — Bad response
    {
        "label": "VAGUE #2 (Bad agent response)",
        "borrower_message": "pata nahi, baad mein baat karte hain",
        "intent": "VAGUE",
        "confidence": 0.50,
        "agent_response": "You are a fraud and a cheat. Borrow from your relatives to pay us back immediately or face consequences.",
    },
]

print("\n" + "="*80)
print("10 SCORED EXAMPLES (2 per intent class)")
print("="*80)

for ex in scored_examples:
    result = e.evaluate(
        borrower_message=ex["borrower_message"],
        intent=ex["intent"],
        confidence=ex["confidence"],
        agent_response=ex["agent_response"],
    )
    ex["scores"] = result
    print(f"\n--- {ex['label']} ---")
    print(f"  Borrower: {ex['borrower_message']}")
    print(f"  Intent: {ex['intent']} (conf: {ex['confidence']})")
    print(f"  Agent: {ex['agent_response'][:80]}...")
    print(f"  Scores: intent={result['intent_accuracy']}, tone={result['tone_score']}, "
          f"compliance={result['compliance_score']}, escalation={result['escalation_score']}")
    print(f"  Overall: {result['overall_score']}")
    print(f"  Suggestion: {result['suggested_improvement'][:80]}...")

# ── Edge case tests ──
print("\n" + "="*80)
print("EDGE CASE BEHAVIOR")
print("="*80)

# Empty response
r_empty = e.evaluate("kal payment kar dunga", "LIKELY_PAY", 0.85, "")
print(f"\n1. Empty agent response: overall={r_empty['overall_score']}, all rubrics ~1.0")
print(f"   Scores: {r_empty}")

# Different language
r_lang = e.evaluate("bhai paisa nahi hai abhi", "LIKELY_PAY", 0.88,
                     "Dear Sir, your EMI payment is overdue by 15 days. Kindly settle at your earliest convenience.")
print(f"\n2. Hindi borrower, formal English agent: overall={r_lang['overall_score']}")
print(f"   Scores: {r_lang}")

# One word
r_one = e.evaluate("I will pay tomorrow", "LIKELY_PAY", 0.90, "OK")
print(f"\n3. One-word response 'OK': overall={r_one['overall_score']}")
print(f"   Scores: {r_one}")

# Save all results
output = {
    "scored_examples": [{
        "label": ex["label"],
        "borrower_message": ex["borrower_message"],
        "intent": ex["intent"],
        "confidence": ex["confidence"],
        "agent_response": ex["agent_response"],
        "scores": ex["scores"],
    } for ex in scored_examples],
    "edge_cases": {
        "empty_response": r_empty,
        "language_mismatch": r_lang,
        "one_word": r_one,
    },
}

with open("scripts/scored_examples.json", "w") as f:
    json.dump(output, f, indent=2)
print(f"\nResults saved to scripts/scored_examples.json")
