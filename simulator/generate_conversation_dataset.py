#!/usr/bin/env python3
"""
RecoveryBench — Synthetic Conversation Dataset Generator

Generates 1,000+ synthetic multi-turn debt collection conversations
with balanced intent and language distribution.

Usage:
    python simulator/generate_conversation_dataset.py

Output:
    simulator/data/synthetic_conversations.json
    simulator/data/dataset_stats.json
"""

import sys
import json
import logging
from pathlib import Path
from collections import Counter
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from simulator.conversation_generator import ConversationGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recoverybench.simulator")

# Configuration
TARGET_COUNT = 1000
OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "synthetic_conversations.json"
STATS_FILE = OUTPUT_DIR / "dataset_stats.json"
SEED = 42


def generate_dataset():
    """Generate the full synthetic conversation dataset."""
    print("=" * 60)
    print("RecoveryBench — Synthetic Conversation Dataset Generator")
    print("=" * 60)
    print(f"Target: {TARGET_COUNT} conversations")
    print(f"Seed: {SEED}")
    print()

    # Initialize generator
    gen = ConversationGenerator(seed=SEED)

    # Generate conversations with balanced distribution
    print(f"Generating {TARGET_COUNT} conversations...")
    conversations = gen.generate_batch(
        count=TARGET_COUNT,
        balance_intents=True,
        balance_languages=True,
    )
    print(f"Generated {len(conversations)} conversations")

    # Compute statistics
    intent_counts = Counter(c["expected_intent"] for c in conversations)
    language_counts = Counter(c["language"] for c in conversations)
    agent_style_counts = Counter(
        c["agent_persona"]["style"] for c in conversations
    )
    borrower_persona_counts = Counter(
        c["borrower_persona"]["name"] for c in conversations
    )
    turn_counts = Counter(c["num_turns"] for c in conversations)
    compliance_counts = Counter(
        "compliant" if c["expected_compliance"] else "non-compliant"
        for c in conversations
    )

    # Cross-tabulation: intent × language
    intent_language = {}
    for c in conversations:
        intent = c["expected_intent"]
        lang = c["language"]
        key = f"{intent}_{lang}"
        intent_language[key] = intent_language.get(key, 0) + 1

    stats = {
        "generated_at": datetime.now().isoformat(),
        "total_conversations": len(conversations),
        "seed": SEED,
        "intent_distribution": dict(sorted(intent_counts.items())),
        "language_distribution": dict(sorted(language_counts.items())),
        "agent_style_distribution": dict(sorted(agent_style_counts.items())),
        "borrower_persona_distribution": dict(sorted(borrower_persona_counts.items())),
        "turn_count_distribution": {str(k): v for k, v in sorted(turn_counts.items())},
        "compliance_distribution": dict(compliance_counts),
        "intent_x_language": dict(sorted(intent_language.items())),
        "avg_turns": round(
            sum(c["num_turns"] for c in conversations) / len(conversations), 2
        ),
        "total_messages": sum(c["num_turns"] for c in conversations),
    }

    # Print statistics
    print("\n" + "=" * 60)
    print("DATASET STATISTICS")
    print("=" * 60)

    print(f"\nTotal conversations: {len(conversations)}")
    print(f"Average turns per conversation: {stats['avg_turns']}")
    print(f"Total messages: {stats['total_messages']}")

    print("\n--- Intent Distribution ---")
    for intent, count in sorted(intent_counts.items()):
        pct = count / len(conversations) * 100
        bar = "#" * int(pct / 2)
        print(f"  {intent:20s}: {count:4d} ({pct:5.1f}%) {bar}")

    print("\n--- Language Distribution ---")
    for lang, count in sorted(language_counts.items()):
        pct = count / len(conversations) * 100
        bar = "#" * int(pct / 2)
        print(f"  {lang:15s}: {count:4d} ({pct:5.1f}%) {bar}")

    print("\n--- Agent Style Distribution ---")
    for style, count in sorted(agent_style_counts.items()):
        pct = count / len(conversations) * 100
        print(f"  {style:20s}: {count:4d} ({pct:5.1f}%)")

    print("\n--- Compliance Distribution ---")
    for comp, count in sorted(compliance_counts.items()):
        pct = count / len(conversations) * 100
        print(f"  {comp:20s}: {count:4d} ({pct:5.1f}%)")

    print("\n--- Turn Count Distribution ---")
    for turns, count in sorted(turn_counts.items()):
        print(f"  {turns} turns: {count:4d}")

    # Save dataset
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(conversations, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Conversations saved to {OUTPUT_FILE}")
    print(f"     File size: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")

    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"[OK] Statistics saved to {STATS_FILE}")

    # Validation
    print("\n--- Validation ---")
    assert len(conversations) >= TARGET_COUNT, (
        f"Generated {len(conversations)} < target {TARGET_COUNT}"
    )
    print(f"  [OK] Count: {len(conversations)} >= {TARGET_COUNT}")

    # Check all intents present
    expected_intents = {"LIKELY_PAY", "NEEDS_REMINDER", "DISPUTE", "HIGH_RISK", "VAGUE", "ALREADY_PAID"}
    actual_intents = set(intent_counts.keys())
    assert expected_intents.issubset(actual_intents), (
        f"Missing intents: {expected_intents - actual_intents}"
    )
    print(f"  [OK] All {len(expected_intents)} intents present")

    # Check all languages present
    expected_langs = {"English", "Hindi", "Bengali", "Hinglish"}
    actual_langs = set(language_counts.keys())
    assert expected_langs.issubset(actual_langs), (
        f"Missing languages: {expected_langs - actual_langs}"
    )
    print(f"  [OK] All {len(expected_langs)} languages present")

    print("\n[DONE] Dataset generation complete!")
    return conversations, stats


if __name__ == "__main__":
    generate_dataset()
