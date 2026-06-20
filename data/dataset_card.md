# RecoveryBench Dataset Card

## Overview

**RecoveryBench Dataset** is a synthetic multilingual dataset of debt collection borrower messages, designed for training and evaluating intent classification models in the Indian financial services context.

## Dataset Description

- **Task:** Multi-class text classification (borrower intent detection)
- **Languages:** English, Hindi (Romanized), Bengali (Romanized), Hinglish (code-mixed English + Hindi)
- **Classes:** 6 intent categories
- **Total Size:** ~4,000+ labeled messages
- **Format:** CSV with columns: `text`, `label`, `language`, `split`
- **License:** Research / Educational Use

## Intent Classes

| Class | Description | Typical Examples |
|-------|-------------|-----------------|
| `LIKELY_PAY` | Borrower clearly intends to pay, may give a timeline | "I will pay by Friday", "Kal kar dunga" |
| `NEEDS_REMINDER` | Forgot or vague, needs a follow-up nudge | "Oh I forgot about this", "Due date kab thi?" |
| `DISPUTE` | Contesting the debt amount, ownership, or validity | "This amount is wrong", "Maine ye loan nahi liya" |
| `HIGH_RISK` | Hostile, threatening, or completely avoidant | "Stop calling me", "Do whatever you want" |
| `VAGUE` | Non-committal, unclear, monosyllabic | "Hmm", "Let me see", "Dekhte hain" |
| `ALREADY_PAID` | Borrower claims payment has already been made | "I already paid this last week", "Check your records, payment was done" |

## Language Distribution

| Language | Description | Script |
|----------|-------------|--------|
| English | Standard English responses | Latin |
| Hindi | Hindi in Romanized script (transliteration) | Latin (Romanized Devanagari) |
| Bengali | Bengali in Romanized script | Latin (Romanized Bengali) |
| Hinglish | Code-mixed English + Hindi | Latin |

## Generation Methodology

### Primary Method: Template-Based Generation

The dataset was generated using a comprehensive template-based approach with 50 unique templates per class × language combination (1,200 templates total across 6 classes × 4 languages). Each template includes:

- Variable slots for dates, timeframes, payment methods
- Random augmentations (casing, punctuation, emoji, filler words)
- Multiple template instantiations with different substitution values

### Supplemental Method: Ollama (if available)

When a local Ollama instance is detected, it supplements template generation with LLM-generated messages for additional diversity. The generation prompt requests:

```
Generate {N} short, realistic messages a loan defaulter might send via 
WhatsApp in response to an overdue EMI reminder.
Language: {language}
Category: {class_description}
```

### Quality Pipeline

1. **Exact deduplication** — MD5 hash on lowercased text
2. **Near-duplicate removal** — `difflib.SequenceMatcher` with 0.92 threshold
3. **Length filtering** — Remove messages under 3 or over 300 characters
4. **Language validation** — Flag rows where `langdetect` disagrees with label (kept but flagged)
5. **Stratified splitting** — 70/15/15 train/val/test, stratified by class × language

## Splits

| Split | Approximate Size | Purpose |
|-------|---------|---------|
| Train | ~70% | Model training |
| Val | ~15% | Hyperparameter tuning, early stopping |
| Test | ~15% | Final evaluation |

## Known Limitations

1. **Synthetic data** — All messages are generated, not collected from real borrowers. Real-world distribution may differ significantly.
2. **Romanized Bengali** — Bengali messages use Roman script (transliteration), not Unicode Bangla. This limits applicability to native-script Bengali NLP.
3. **Template repetition** — Despite augmentation, some structural patterns may repeat. This can lead to models learning template artifacts rather than true intent signals.
4. **Hinglish variety** — Code-mixing patterns are template-driven and may not capture the full spectrum of natural Hinglish usage.
5. **Class boundaries** — Some classes overlap in practice (e.g., `VAGUE` vs `NEEDS_REMINDER`, `ALREADY_PAID` vs `DISPUTE`). The dataset makes sharp distinctions that may not hold in real conversations.
6. **ALREADY_PAID verification** — The dataset does not distinguish between verifiable claims ("here's my UTR") and unverifiable ones ("I paid, trust me"). Both appear as ALREADY_PAID.
6. **No audio component** — This dataset is text-only. Real debt collection happens via phone calls with prosodic cues not captured here.
7. **Single-turn** — Each example is a single borrower message, not a full conversation context.

## How to Regenerate

```bash
cd recoverbench
python data/generate_data.py
python data/eda.py
```

Set `RANDOM_SEED` in `generate_data.py` for reproducibility.

## Citation

If you use this dataset, please cite:

```
RecoveryBench: A Multilingual AI Debt Collection Agent Evaluation Platform
Author: Sweta Jha, IEM Kolkata
Year: 2025
```

## Contact

- **Author:** Sweta Jha
- **Affiliation:** IEM Kolkata
