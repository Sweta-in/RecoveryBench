#!/usr/bin/env python3
"""
RecoveryBench — ALREADY_PAID Data Generator (Phase B, Step 1)

Generates ~600 ALREADY_PAID examples using Groq LLM API:
  - ~400 clear ALREADY_PAID positives across 4 languages
  - ~200 hard negatives labeled to their correct classes

Output: data/already_paid_generated.csv
"""

import os
import sys
import csv
import json
import time
import random
import logging
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher

# Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Load .env manually (no dotenv dependency)
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ[key.strip()] = val.strip().strip('"').strip("'")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY not found in environment or .env")
    sys.exit(1)

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

# ============================================================
# Prompts for LLM generation
# ============================================================

ALREADY_PAID_POSITIVE_PROMPT = """You are generating realistic training data for a multilingual debt settlement NLP system used in India.

Generate {count} unique borrower messages in {language} where the borrower claims they have ALREADY PAID their debt/EMI/loan installment. These should be labeled as ALREADY_PAID.

Requirements:
- Messages should be natural, conversational, varied in tone (polite, frustrated, confused, matter-of-fact)
- Include variations: paid via UPI, NEFT, bank transfer, cash deposit, auto-debit, EMI auto-deducted
- Include temporal markers: paid yesterday, last week, 2 days ago, this morning, on the 5th
- Include reference mentions: transaction ID, receipt number, UTR number, bank reference
- Some should be short (3-8 words), some medium (8-20 words), some longer (20-40 words)
- For Hindi: use Devanagari-free romanized Hindi (like "maine payment kar diya hai")
- For Hinglish: mix English and romanized Hindi naturally (like "bhai payment already done hai")
- For Bengali: use romanized Bengali (like "ami toh taka diye diyechi")
- Each message on its own line
- NO numbering, NO quotes, NO labels — just the raw message text, one per line
- Do NOT repeat similar phrases — each must be meaningfully distinct

Examples of good ALREADY_PAID messages:
- "I already paid last Tuesday via NEFT"
- "maine kal hi payment kar diya UPI se"
- "ami toh gotokal e taka pathiye diyechi"
- "bhai check karo, payment ho chuka hai"
- "My EMI was auto-debited on the 5th, please check"
"""

HARD_NEGATIVE_PROMPT = """You are generating hard-negative training data for a multilingual debt settlement NLP system.

These are messages that LOOK similar to "already paid" claims but are actually something different. Generate {count} messages in {language}, each on its own line.

For each message, also output the correct label on the same line, separated by ||| (three pipes).

The labels should be one of: LIKELY_PAY, NEEDS_REMINDER, DISPUTE, HIGH_RISK, VAGUE

Categories of hard negatives:
1. LIKELY_PAY: Future payment promises ("I will pay tomorrow", "kal payment kar dunga") — NOT past tense
2. DISPUTE: Contesting the amount/validity, NOT claiming payment was made ("This amount is wrong", "I never took this loan", "You're charging me extra")
3. NEEDS_REMINDER: Partial payment situations ("I paid 5000 but 3000 is still due"), forgotten payments, processing issues
4. VAGUE: Uncertain claims ("Payment is processing", "My brother paid, I think", "I'm not sure if it went through")
5. HIGH_RISK: Hostile responses mentioning payment ("Stop harassing me about payments", "I won't pay a single rupee more")

Requirements:
- Messages should be natural and conversational
- For Hindi: romanized Hindi
- For Hinglish: mix of English and romanized Hindi
- For Bengali: romanized Bengali
- Each line format: message text ||| LABEL
- NO numbering, NO quotes

Examples:
I will pay by Friday ||| LIKELY_PAY
maine 5000 diye the lekin 3000 baaki hai ||| NEEDS_REMINDER
yeh amount galat hai, check karo ||| DISPUTE
shayad mere bhai ne diya hoga ||| VAGUE
band karo phone, paisa nahi dunga ||| HIGH_RISK
"""


def call_groq(prompt: str, max_tokens: int = 4000) -> str:
    """Call Groq API and return the response text."""
    try:
        from groq import Groq
    except ImportError:
        logger.error("groq package not installed. Run: python -m pip install groq")
        sys.exit(1)

    client = Groq(api_key=GROQ_API_KEY)

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.9,
                top_p=0.95,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Groq API attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
            else:
                raise

    return ""


def generate_positives(language: str, count: int) -> list:
    """Generate ALREADY_PAID positive examples for a language."""
    logger.info(f"Generating {count} ALREADY_PAID positives in {language}...")

    # Split into batches to stay within token limits and get more variety
    batch_size = 35
    all_examples = []

    for batch in range(0, count, batch_size):
        this_batch = min(batch_size, count - batch)
        prompt = ALREADY_PAID_POSITIVE_PROMPT.format(
            count=this_batch, language=language
        )
        if batch > 0:
            prompt += f"\n\nIMPORTANT: This is batch {batch // batch_size + 1}. Generate completely different messages from previous batches. Focus on different scenarios, tones, and payment methods."

        response = call_groq(prompt, max_tokens=3000)

        for line in response.strip().split("\n"):
            line = line.strip()
            # Skip empty lines, numbered lines, or meta-text
            if not line or len(line) < 3:
                continue
            # Remove leading numbers/bullets
            if line[0].isdigit() and len(line) > 1 and (line[1] == '.' or line[1] == ')'):
                line = line[2:].strip()
            elif line.startswith("- "):
                line = line[2:].strip()
            # Remove surrounding quotes
            if (line.startswith('"') and line.endswith('"')) or \
               (line.startswith("'") and line.endswith("'")):
                line = line[1:-1].strip()

            if len(line) >= 3 and len(line) <= 300:
                all_examples.append({
                    "text": line,
                    "label": "ALREADY_PAID",
                    "language": language,
                })

        logger.info(f"  Batch {batch // batch_size + 1}: got {len(all_examples)} total so far")
        time.sleep(2)  # Rate limiting

    return all_examples


def generate_hard_negatives(language: str, count: int) -> list:
    """Generate hard negative examples for a language."""
    logger.info(f"Generating {count} hard negatives in {language}...")

    batch_size = 30
    all_examples = []

    for batch in range(0, count, batch_size):
        this_batch = min(batch_size, count - batch)
        prompt = HARD_NEGATIVE_PROMPT.format(
            count=this_batch, language=language
        )
        if batch > 0:
            prompt += f"\n\nBatch {batch // batch_size + 1}: Generate completely different messages."

        response = call_groq(prompt, max_tokens=3000)

        for line in response.strip().split("\n"):
            line = line.strip()
            if not line or "|||" not in line:
                continue

            parts = line.rsplit("|||", 1)
            if len(parts) != 2:
                continue

            text = parts[0].strip()
            label = parts[1].strip().upper()

            # Remove leading numbers/bullets
            if text and text[0].isdigit() and len(text) > 1 and (text[1] == '.' or text[1] == ')'):
                text = text[2:].strip()
            elif text and text.startswith("- "):
                text = text[2:].strip()
            # Remove quotes
            if (text.startswith('"') and text.endswith('"')) or \
               (text.startswith("'") and text.endswith("'")):
                text = text[1:-1].strip()

            valid_labels = {"LIKELY_PAY", "NEEDS_REMINDER", "DISPUTE", "HIGH_RISK", "VAGUE"}
            if label not in valid_labels:
                continue

            if len(text) >= 3 and len(text) <= 300:
                all_examples.append({
                    "text": text,
                    "label": label,
                    "language": language,
                })

        logger.info(f"  Batch {batch // batch_size + 1}: got {len(all_examples)} total so far")
        time.sleep(2)

    return all_examples


def deduplicate(examples: list, threshold: float = 0.90) -> list:
    """Remove exact and near-duplicate examples."""
    seen_exact = set()
    unique = []

    # Exact dedup
    for ex in examples:
        key = ex["text"].lower().strip()
        if key not in seen_exact:
            seen_exact.add(key)
            unique.append(ex)

    logger.info(f"After exact dedup: {len(unique)} (removed {len(examples) - len(unique)})")

    # Near-duplicate removal (within same label)
    by_label = defaultdict(list)
    for ex in unique:
        by_label[ex["label"]].append(ex)

    final = []
    near_dupes_removed = 0
    for label, exs in by_label.items():
        kept = []
        for ex in exs:
            is_dupe = False
            for kept_ex in kept[-30:]:  # Check against recent 30 for speed
                sim = SequenceMatcher(None, ex["text"].lower(), kept_ex["text"].lower()).ratio()
                if sim > threshold:
                    is_dupe = True
                    near_dupes_removed += 1
                    break
            if not is_dupe:
                kept.append(ex)
        final.extend(kept)

    logger.info(f"After near-dedup: {len(final)} (removed {near_dupes_removed})")
    return final


def main():
    """Generate ALREADY_PAID dataset."""
    logger.info("=" * 60)
    logger.info("RecoveryBench — ALREADY_PAID Data Generator")
    logger.info("=" * 60)

    languages = ["English", "Hindi", "Bengali", "Hinglish"]
    positives_per_lang = 110  # ~440 total, aiming for 400+ after dedup
    negatives_per_lang = 55   # ~220 total, aiming for 200+ after dedup

    all_examples = []

    # Generate positives
    for lang in languages:
        examples = generate_positives(lang, positives_per_lang)
        all_examples.extend(examples)
        logger.info(f"  {lang} positives: {len(examples)}")

    # Generate hard negatives
    for lang in languages:
        examples = generate_hard_negatives(lang, negatives_per_lang)
        all_examples.extend(examples)
        logger.info(f"  {lang} hard negatives: {len(examples)}")

    # Deduplicate
    logger.info(f"\nTotal before dedup: {len(all_examples)}")
    all_examples = deduplicate(all_examples)

    # Stats
    label_counts = defaultdict(int)
    lang_counts = defaultdict(int)
    label_lang_counts = defaultdict(lambda: defaultdict(int))
    for ex in all_examples:
        label_counts[ex["label"]] += 1
        lang_counts[ex["language"]] += 1
        label_lang_counts[ex["label"]][ex["language"]] += 1

    logger.info("\n=== Final Dataset Stats ===")
    logger.info(f"Total examples: {len(all_examples)}")
    logger.info("\nBy label:")
    for label, count in sorted(label_counts.items()):
        logger.info(f"  {label}: {count}")
    logger.info("\nBy language:")
    for lang, count in sorted(lang_counts.items()):
        logger.info(f"  {lang}: {count}")
    logger.info("\nALREADY_PAID by language:")
    for lang, count in sorted(label_lang_counts["ALREADY_PAID"].items()):
        logger.info(f"  {lang}: {count}")

    # Save
    output_path = Path(__file__).parent / "already_paid_generated.csv"
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "label", "language"])
        writer.writeheader()
        for ex in all_examples:
            writer.writerow(ex)

    logger.info(f"\nSaved: {output_path} ({len(all_examples)} rows)")
    return all_examples


if __name__ == "__main__":
    main()
