# RecoveryBench-100 — Benchmark Report

**Date:** 2026-06-12T13:53:46.611857
**Scenarios:** 100
**Elapsed:** 16.61s

## Overall Results

| Metric | Value |
|--------|-------|
| Intent Accuracy | 82.00% (82/100) |
| Promise Accuracy | 85.00% (85/100) |
| Window Exact Match | 15/18 |
| Window Close Match (±3d) | 18/18 |
| Agent Eval (mean) | 7.42 / 10 |

## Per-Intent Accuracy

| Intent | Correct | Total | Accuracy |
|--------|---------|-------|----------|
| DISPUTE | 15 | 20 | 75.00% |
| HIGH_RISK | 17 | 20 | 85.00% |
| LIKELY_PAY | 20 | 20 | 100.00% |
| NEEDS_REMINDER | 13 | 20 | 65.00% |
| VAGUE | 17 | 20 | 85.00% |

## Per-Language Accuracy

| Language | Correct | Total | Accuracy |
|----------|---------|-------|----------|
| Bengali | 9 | 10 | 90.00% |
| English | 30 | 38 | 78.95% |
| Hindi | 23 | 31 | 74.19% |
| Hinglish | 20 | 21 | 95.24% |

## Per-Category Accuracy

| Category | Correct | Total | Accuracy |
|----------|---------|-------|----------|
| short_message | 4 | 10 | 40.00% |
| already_paid_claim | 2 | 3 | 66.67% |
| colloquial_hindi | 7 | 10 | 70.00% |
| formal_english | 5 | 7 | 71.43% |
| emotional_distress | 8 | 11 | 72.73% |
| conditional_promise | 3 | 4 | 75.00% |
| dispute_legitimate | 3 | 4 | 75.00% |
| bengali_romanized | 8 | 9 | 88.89% |
| aggressive_refusal | 4 | 4 | 100.00% |
| dispute_evasion | 5 | 5 | 100.00% |
| language_switching | 9 | 9 | 100.00% |
| partial_payment | 4 | 4 | 100.00% |
| straightforward | 10 | 10 | 100.00% |
| temporal_promise | 3 | 3 | 100.00% |
| vague_non_committal | 7 | 7 | 100.00% |

## Top 5 Hardest Categories

- **short_message**: 40.00% (4/10)
- **already_paid_claim**: 66.67% (2/3)
- **colloquial_hindi**: 70.00% (7/10)
- **formal_english**: 71.43% (5/7)
- **emotional_distress**: 72.73% (8/11)

## Confusion Matrix

| Expected \ Predicted | ALREADY_PAID | DISPUTE | HIGH_RISK | LIKELY_PAY | NEEDS_REMINDER | VAGUE |
|---|---|---|---|---|---|---|
| ALREADY_PAID | 0 | 0 | 0 | 0 | 0 | 0 |
| DISPUTE | 2 | 15 | 2 | 0 | 1 | 0 |
| HIGH_RISK | 0 | 0 | 17 | 0 | 2 | 1 |
| LIKELY_PAY | 0 | 0 | 0 | 20 | 0 | 0 |
| NEEDS_REMINDER | 0 | 1 | 1 | 2 | 13 | 3 |
| VAGUE | 0 | 0 | 1 | 0 | 2 | 17 |

## Misclassified Scenarios (18 total)

| ID | Category | Language | Expected | Predicted | Conf | Message |
|----|----------|----------|----------|-----------|------|---------|
| RB-023 | short_message | English | NEEDS_REMINDER | VAGUE | 0.53 | ok |
| RB-024 | short_message | Hindi | NEEDS_REMINDER | VAGUE | 0.62 | theek hai |
| RB-025 | short_message | Hindi | NEEDS_REMINDER | VAGUE | 0.54 | acha |
| RB-031 | emotional_distress | English | NEEDS_REMINDER | HIGH_RISK | 0.30 | I'm going through a rough patch right now, can you send me t |
| RB-034 | formal_english | English | NEEDS_REMINDER | DISPUTE | 0.52 | I received your message. Let me review the amount and revert |
| RB-035 | bengali_romanized | Bengali | NEEDS_REMINDER | LIKELY_PAY | 0.33 | haan shunlam, koto taka bolun to? |
| RB-037 | colloquial_hindi | Hindi | NEEDS_REMINDER | LIKELY_PAY | 0.39 | haan bhai sun raha hun, bol |
| RB-045 | dispute_legitimate | Hindi | DISPUTE | HIGH_RISK | 0.44 | mera loan to close ho chuka hai, aap log galat insaan ko cal |
| RB-053 | formal_english | English | DISPUTE | NEEDS_REMINDER | 0.51 | As per our earlier discussion, the late penalty was to be wa |
| RB-054 | already_paid_claim | Hinglish | DISPUTE | ALREADY_PAID | 0.95 | bhai already pay kar diya tha last week, receipt bhi hai mer |
| RB-059 | emotional_distress | English | DISPUTE | HIGH_RISK | 0.49 | You people are charging me double, this is not fair at all,  |
| RB-060 | emotional_distress | Hindi | DISPUTE | ALREADY_PAID | 0.95 | itna pareshaan kar diya hai tum logon ne, galat amount laga  |
| RB-074 | short_message | English | HIGH_RISK | VAGUE | 0.35 | stop!!! |
| RB-076 | colloquial_hindi | Hindi | HIGH_RISK | NEEDS_REMINDER | 0.43 | bahut ho gaya, ab phone kiya toh dekh lena, legal notice bhe |
| RB-077 | colloquial_hindi | Hindi | HIGH_RISK | NEEDS_REMINDER | 0.27 | tere baap ka paisa hai kya? band kar phone warna dekh |
| RB-086 | short_message | English | VAGUE | HIGH_RISK | 0.37 | ... |
| RB-087 | short_message | English | VAGUE | NEEDS_REMINDER | 0.33 | K |
| RB-097 | conditional_promise | Hindi | VAGUE | NEEDS_REMINDER | 0.34 | agar kuch jugaad ho gaya toh de dunga, nahi toh kya karun |

## Agent Evaluation Averages

| Rubric | Mean Score |
|--------|-----------|
| intent_accuracy | 6.22 |
| tone_score | 6.23 |
| compliance_score | 10.0 |
| escalation_score | 6.63 |
| overall_score | 7.42 |

## Components Used

- **intent_classifier**: ✓
- **promise_parser**: ✓
- **risk_scorer**: ✓
- **compliance_checker**: ✓
- **evaluator**: ✓ (rule_based)
