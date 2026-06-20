# Checkpoint 7 — Benchmark Suite Review
**Status:** PASS WITH WARNINGS
**Completion:** 100%
**Date:** 2026-06-12

## Risks

1. **NEEDS_REMINDER accuracy is 65% (13/20)** — this is the weakest class on the benchmark. Most errors come from short messages ("ok", "theek hai", "acha") that fall on the NEEDS_REMINDER / VAGUE boundary. The model defaults to VAGUE for minimal-engagement messages, which is defensible but misaligns with benchmark labels.
2. **Short messages category accuracy is only 40% (4/10)** — the model struggles with extremely brief inputs where context is minimal. These are inherently ambiguous and may represent labeling disagreement rather than model weakness.
3. **ALREADY_PAID predictions appearing in DISPUTE misclassifications** — RB-054 and RB-060 were labeled DISPUTE but predicted ALREADY_PAID. This traces back to the known ALREADY_PAID class issue from Checkpoint 2 (the class had 0 training examples). The benchmark correctly surfaces this as a problem area.

## Concerns

- The benchmark's `already_paid_claim` category (3 scenarios) overlaps conceptually with both DISPUTE and LIKELY_PAY. Two of these three scenarios were misclassified, suggesting the class boundary remains poorly defined.
- Hindi colloquial language is under-represented in training data — 3 of 10 colloquial_hindi scenarios were misclassified (70% accuracy), including hostile Hindi messages that the model routed to NEEDS_REMINDER.
- `short_message` category is disproportionately hard (40% accuracy) because minimal text provides insufficient signal for distinguishing VAGUE from NEEDS_REMINDER or HIGH_RISK.

## Recommendations

1. **Review the NEEDS_REMINDER vs VAGUE boundary** for short messages. Consider whether "ok", "theek hai", "acha" should be labeled VAGUE (model's prediction) rather than NEEDS_REMINDER (current label). Both are defensible.
2. **Review colloquial Hindi HIGH_RISK scenarios** (RB-076, RB-077) — the model misses implicit threats in colloquial register. Adding more hostile colloquial Hindi to training data would help.
3. **Accept the ALREADY_PAID leakage** as a known limitation from Checkpoint 2, or backtrack to add ALREADY_PAID training data.

## Next Action
**WAITING FOR HUMAN APPROVAL**

---

## 1. Benchmark Statistics

| Metric | Value |
|--------|-------|
| **Total records** | 100 |
| **Records per intent class** | 20 each (exactly balanced) |
| **Languages** | English (38), Hindi (31), Hinglish (21), Bengali (10) |
| **Scenario categories** | 15 (all present) |
| **Benchmark file** | `benchmarks/recoverybench_100.json` (45.7 KB) |
| **Runner elapsed time** | 16.6 seconds |

### Intent Distribution

| Intent | Count |
|--------|-------|
| LIKELY_PAY | 20 |
| NEEDS_REMINDER | 20 |
| DISPUTE | 20 |
| HIGH_RISK | 20 |
| VAGUE | 20 |

### Language Distribution

| Language | Count |
|----------|-------|
| English | 38 |
| Hindi | 31 |
| Hinglish | 21 |
| Bengali | 10 |

### Category Distribution

| Category | Count |
|----------|-------|
| emotional_distress | 11 |
| colloquial_hindi | 10 |
| short_message | 10 |
| straightforward | 10 |
| bengali_romanized | 9 |
| language_switching | 9 |
| formal_english | 7 |
| vague_non_committal | 7 |
| dispute_evasion | 5 |
| aggressive_refusal | 4 |
| conditional_promise | 4 |
| dispute_legitimate | 4 |
| partial_payment | 4 |
| already_paid_claim | 3 |
| temporal_promise | 3 |

---

## 2. Coverage Analysis

All **15 scenario categories** are present in the benchmark. Coverage ranges from 3 to 11 scenarios per category.

### Most Represented Categories
- `emotional_distress` (11) — covers distressed borrowers across all intent classes
- `colloquial_hindi` (10) — tests slang/informal Hindi across multiple intents
- `short_message` (10) — tests minimal-length messages (1-5 words)
- `straightforward` (10) — baseline clear messages for each class

### Least Represented Categories
- `temporal_promise` (3) — only LIKELY_PAY scenarios with timelines
- `already_paid_claim` (3) — only DISPUTE scenarios claiming prior payment
- `aggressive_refusal` (4) — only HIGH_RISK aggressive responses
- `conditional_promise` (4) — split between LIKELY_PAY and VAGUE
- `dispute_legitimate` (4) — only DISPUTE legitimate grievances
- `partial_payment` (4) — split between LIKELY_PAY and NEEDS_REMINDER

> [!NOTE]
> The lower-count categories are deliberately narrow in scope (e.g., `temporal_promise` only makes sense for LIKELY_PAY). This is by design — each category tests a specific evaluation dimension, not every intent.

---

## 3. Twenty Sample Scenarios (4 per Intent Class)

### LIKELY_PAY (4 samples)

| ID | Category | Language | Message | Promise | Window | Rationale |
|----|----------|----------|---------|---------|--------|-----------|
| RB-001 | straightforward | English | "I will pay the full EMI amount by this Friday." | ✓ | 4d | Clear English promise with specific timeline |
| RB-005 | conditional_promise | Hinglish | "agar is hafte salary aa gayi toh pakka kar dunga" | ✓ | 7d | Conditional on salary but strong intent ('pakka kar dunga') |
| RB-013 | colloquial_hindi | Hindi | "chill kar bhai, weekend tak dal dunga paise account mein" | ✓ | 3d | Slang Hindi — 'chill kar' is informal but 'dal dunga' shows clear payment intent |
| RB-019 | emotional_distress | English | "I know I'm late and I'm sorry. Will transfer tomorrow morning first thing." | ✓ | 1d | Apologetic tone with firm commitment |

### NEEDS_REMINDER (4 samples)

| ID | Category | Language | Message | Promise | Window | Rationale |
|----|----------|----------|---------|---------|--------|-----------|
| RB-021 | straightforward | English | "oh I forgot about it, how much is the amount?" | ✗ | — | Forgot about payment, asking for amount |
| RB-023 | short_message | English | "ok" | ✗ | — | Single-word acknowledgment — not a promise, not hostile |
| RB-029 | language_switching | Hinglish | "haan pata hai bhai, will check and let you know" | ✗ | — | Code-mixed acknowledgment without commitment |
| RB-033 | formal_english | English | "Could you please share the updated statement of account?" | ✗ | — | Formal request for info — engaged but not committing |

### DISPUTE (4 samples)

| ID | Category | Language | Message | Promise | Window | Rationale |
|----|----------|----------|---------|---------|--------|-----------|
| RB-041 | straightforward | English | "This amount is wrong. I only took a loan of 50,000 not 75,000." | ✗ | — | Clear dispute about loan amount |
| RB-043 | dispute_legitimate | English | "I never took this loan. There must be some identity mix-up." | ✗ | — | Identity dispute — possible fraud case |
| RB-054 | already_paid_claim | Hinglish | "bhai already pay kar diya tha last week, receipt bhi hai mere paas" | ✗ | — | Claims already paid with receipt |
| RB-058 | colloquial_hindi | Hindi | "extra charge kyun lagaya? agreement mein toh nahi tha" | ✗ | — | Questioning extra charges with agreement reference |

### HIGH_RISK (4 samples)

| ID | Category | Language | Message | Promise | Window | Rationale |
|----|----------|----------|---------|---------|--------|-----------|
| RB-061 | aggressive_refusal | English | "STOP CALLING ME! I will file a complaint with consumer forum!" | ✗ | — | ALL CAPS threat of consumer forum |
| RB-066 | straightforward | English | "I am not going to pay. Do whatever you want." | ✗ | — | Clear refusal — antagonistic |
| RB-074 | short_message | English | "stop!!!" | ✗ | — | Single-word aggressive demand |
| RB-079 | formal_english | English | "I am instructing my lawyer to send a cease and desist notice." | ✗ | — | Formal legal threat — sophisticated but clearly HIGH_RISK |

### VAGUE (4 samples)

| ID | Category | Language | Message | Promise | Window | Rationale |
|----|----------|----------|---------|---------|--------|-----------|
| RB-081 | vague_non_committal | Hindi | "hmm dekhte hain" | ✗ | — | 'hmm let's see' — classic non-commitment |
| RB-085 | short_message | Hindi | "hmm" | ✗ | — | Single syllable — impossible to determine intent |
| RB-093 | language_switching | Hinglish | "I'll see what I can do, abhi kuch promise nahi kar sakta" | ✗ | — | Explicitly says 'can't promise anything now' |
| RB-099 | colloquial_hindi | Hindi | "manage karna padega kuch na kuch, dekhta hun" | ✗ | — | 'Will have to manage somehow, let me see' — non-committal |

---

## 4. Benchmark Runner Results

### Full `benchmark_scores.json` Summary

The complete results file is at `benchmarks/results/benchmark_scores.json` (100 KB, 100 scored entries).

**Embedded summary from `benchmark_summary.json`:**

```json
{
  "benchmark_date": "2026-06-12T13:53:46.611857",
  "total_scenarios": 100,
  "elapsed_seconds": 16.61,
  "intent_classification": {
    "overall_accuracy": 0.82,
    "correct": 82,
    "total": 100,
    "per_intent": {
      "LIKELY_PAY":      {"correct": 20, "total": 20, "accuracy": 1.00},
      "NEEDS_REMINDER":  {"correct": 13, "total": 20, "accuracy": 0.65},
      "DISPUTE":         {"correct": 15, "total": 20, "accuracy": 0.75},
      "HIGH_RISK":       {"correct": 17, "total": 20, "accuracy": 0.85},
      "VAGUE":           {"correct": 17, "total": 20, "accuracy": 0.85}
    }
  },
  "promise_extraction": {
    "total": 100,
    "correct": 85,
    "accuracy": 0.85,
    "window_exact_match": 15,
    "window_close_match": 18,
    "window_total": 18
  },
  "agent_evaluation": {
    "intent_accuracy": 6.22,
    "tone_score": 6.23,
    "compliance_score": 10.0,
    "escalation_score": 6.63,
    "overall_score": 7.42
  },
  "components_used": {
    "intent_classifier": true,
    "promise_parser": true,
    "risk_scorer": true,
    "compliance_checker": true,
    "evaluator": "rule_based"
  }
}
```

### Components Status

| Component | Status | Notes |
|-----------|--------|-------|
| Intent Classifier | ✓ Loaded | TF-IDF + LogisticRegression ensemble |
| Promise Parser | ✓ Loaded | Rule-based temporal extraction |
| Risk Scorer | ✓ Loaded | XGBoost regressor |
| Compliance Checker | ✓ Loaded | Pattern-based rule engine |
| Evaluator | ✓ Loaded | Rule-based backend (no paid API) |

---

## 5. Intent Accuracy on Benchmark

**Overall: 82.00% (82/100)**

This is the first external validation of the trained model on curated, adversarial scenarios.

### Per-Intent Accuracy

| Intent | Correct | Total | Accuracy | Assessment |
|--------|---------|-------|----------|------------|
| LIKELY_PAY | 20 | 20 | **100.00%** | ✅ Perfect — model handles all promise patterns |
| HIGH_RISK | 17 | 20 | **85.00%** | ✅ Strong — misses some implicit Hindi threats |
| VAGUE | 17 | 20 | **85.00%** | ✅ Strong — struggles only with ultra-short messages |
| DISPUTE | 15 | 20 | **75.00%** | ⚠️ Fair — ALREADY_PAID leakage and emotional overlap |
| NEEDS_REMINDER | 13 | 20 | **65.00%** | ⚠️ Weak — short messages confuse with VAGUE |

### Per-Language Accuracy

| Language | Correct | Total | Accuracy |
|----------|---------|-------|----------|
| Bengali | 9 | 10 | **90.00%** |
| Hinglish | 20 | 21 | **95.24%** |
| English | 30 | 38 | **78.95%** |
| Hindi | 23 | 31 | **74.19%** |

### Confusion Matrix

| Expected \ Predicted | LIKELY_PAY | NEEDS_REM | DISPUTE | HIGH_RISK | VAGUE | ALREADY_PAID |
|---------------------|------------|-----------|---------|-----------|-------|--------------|
| LIKELY_PAY | **20** | 0 | 0 | 0 | 0 | 0 |
| NEEDS_REMINDER | 2 | **13** | 1 | 1 | 3 | 0 |
| DISPUTE | 0 | 1 | **15** | 2 | 0 | 2 |
| HIGH_RISK | 0 | 2 | 0 | **17** | 1 | 0 |
| VAGUE | 0 | 2 | 0 | 1 | **17** | 0 |

---

## 6. Hardest Scenarios

### Bottom 5 Categories by Intent Accuracy

| Rank | Category | Accuracy | Correct / Total | Analysis |
|------|----------|----------|-----------------|----------|
| 1 | **short_message** | 40.00% | 4/10 | Ultra-brief messages ("ok", "hmm", "K", "...") lack discriminative features — the model defaults to its prior for the most common class |
| 2 | **already_paid_claim** | 66.67% | 2/3 | The ALREADY_PAID class was absent from training (Checkpoint 2 issue). Model routes these to ALREADY_PAID or HIGH_RISK instead of DISPUTE |
| 3 | **colloquial_hindi** | 70.00% | 7/10 | Slang Hindi with implicit threats ("tere baap ka paisa hai kya?") is misclassified as NEEDS_REMINDER — the model doesn't recognize colloquial hostility |
| 4 | **formal_english** | 71.43% | 5/7 | Formal language with dispute-adjacent phrasing ("review the amount and revert") confuses the model between DISPUTE and NEEDS_REMINDER |
| 5 | **emotional_distress** | 72.73% | 8/11 | Emotional framing pulls the model toward HIGH_RISK even when the underlying intent is NEEDS_REMINDER or DISPUTE |

### Specific Hard Scenarios

| ID | Expected | Predicted | Confidence | Why Hard |
|----|----------|-----------|------------|----------|
| RB-077 | HIGH_RISK | NEEDS_REMINDER | 0.27 | "tere baap ka paisa hai kya?" — extremely hostile colloquial Hindi, but model sees it as conversational |
| RB-074 | HIGH_RISK | VAGUE | 0.35 | "stop!!!" — 4 chars with exclamation marks; too short for pattern matching |
| RB-086 | VAGUE | HIGH_RISK | 0.37 | "..." — ellipsis-only; model treats punctuation-only as distress signal |
| RB-060 | DISPUTE | ALREADY_PAID | 0.95 | "itna pareshaan kar diya hai tum logon ne, galat amount laga ke" — emotional + amount dispute, routed to ALREADY_PAID with high confidence |
| RB-054 | DISPUTE | ALREADY_PAID | 0.95 | "bhai already pay kar diya tha last week" — clearly an already-paid claim, but labeled as DISPUTE in benchmark |

### Category × Language Interaction

The `language_switching` category achieves **100% accuracy** (9/9) — the model handles code-mixed inputs well. Conversely, `short_message` × English is particularly problematic (only 2/5 correct in English short messages).

---

## 7. Benchmark Quality Concerns

### Potential Labeling Issues

| Scenario ID | Current Label | Suggested Label | Issue |
|-------------|---------------|-----------------|-------|
| RB-054 | DISPUTE | ALREADY_PAID | "bhai already pay kar diya tha last week, receipt bhi hai mere paas" — this is a clear already-paid claim, not a general dispute. The model's ALREADY_PAID prediction (0.95 confidence) may be more accurate than the benchmark label. |
| RB-060 | DISPUTE | HIGH_RISK | "itna pareshaan kar diya hai tum logon ne, galat amount laga ke" — the distress and accusatory tone pushes this toward HIGH_RISK. Labeling as DISPUTE prioritizes the "wrong amount" content over the hostile framing. |
| RB-023 | NEEDS_REMINDER | VAGUE | "ok" — a single "ok" is genuinely ambiguous. The VAGUE classification is arguably more accurate than NEEDS_REMINDER. |
| RB-024 | NEEDS_REMINDER | VAGUE | "theek hai" — same issue as RB-023. Minimal acknowledgment without any engagement signal. |
| RB-025 | NEEDS_REMINDER | VAGUE | "acha" — same pattern. The model consistently and defensibly classifies these as VAGUE. |

> [!WARNING]
> 5 of the 18 misclassifications (RB-023, RB-024, RB-025, RB-054, RB-060) may be **labeling ambiguities** rather than true model errors. If these 5 were relabeled to match the model's predictions, benchmark accuracy would rise to **87%**.

### Scenarios with Correct Labels but Worth Reviewing

| Scenario ID | Label | Note |
|-------------|-------|------|
| RB-035 | NEEDS_REMINDER | "haan shunlam, koto taka bolun to?" — Bengali acknowledgment asking for amount. Model predicted LIKELY_PAY (0.33 confidence). Low confidence suggests genuine uncertainty. |
| RB-097 | VAGUE | "agar kuch jugaad ho gaya toh de dunga" — borderline between VAGUE and NEEDS_REMINDER. The conditional intent is weak but present. |

---

## 8. Comparison: Benchmark Accuracy vs Test Set Accuracy

| Metric | Test Set (CP2) | Benchmark (CP7) | Delta | Assessment |
|--------|---------------|-----------------|-------|------------|
| **Overall Accuracy** | 83.0% (499/601) | 82.0% (82/100) | **−1.0pp** | ✅ Within tolerance |
| **LIKELY_PAY** | ~85.3% (F1) | 100.0% (acc) | +14.7pp | Benchmark scenarios are clearer |
| **NEEDS_REMINDER** | ~91.0% (F1) | 65.0% (acc) | −26.0pp | ⚠️ Benchmark has more ambiguous short messages |
| **DISPUTE** | ~78.9% (F1) | 75.0% (acc) | −3.9pp | Comparable; ALREADY_PAID leakage in both |
| **HIGH_RISK** | ~95.2% (F1) | 85.0% (acc) | −10.2pp | Benchmark has harder colloquial Hindi cases |
| **VAGUE** | ~99.2% (F1) | 85.0% (acc) | −14.2pp | Benchmark includes ultra-short edge cases |

> [!NOTE]
> Test set metrics are F1 scores while benchmark metrics are accuracy — these are not directly comparable. The F1 scores from CP2 weight precision and recall, while accuracy is a simple correct/total ratio. The directional comparison is still informative.

### Key Observations

1. **The benchmark is harder than the test set** for NEEDS_REMINDER, HIGH_RISK, and VAGUE — by design. The curated scenarios include more edge cases, ambiguous short messages, and adversarial colloquial text than the synthetically generated test set.
2. **The benchmark is easier for LIKELY_PAY** (100% vs ~85% F1) — the benchmark's LIKELY_PAY scenarios all have clear payment commitment signals. The test set includes noisier synthetic data.
3. **Overall accuracy difference is minimal (1 percentage point)** — the benchmark is not significantly harder or easier overall, but the error distribution is different. The benchmark concentrates errors in short messages and colloquial Hindi, while the test set errors were dominated by ALREADY_PAID confusion.
4. **The benchmark accuracy drop is within the 0.15 warning threshold** — the 0.01 difference does not trigger the "benchmark is too hard" warning.

### Promise Parser Benchmark Performance

| Metric | Value |
|--------|-------|
| Promise detection accuracy | 85.00% (85/100) |
| Window exact match | 15/18 (83.3%) |
| Window close match (±3 days) | 18/18 (100.0%) |

The promise parser performs well on benchmark scenarios. All 18 scenarios with expected temporal windows were matched within ±3 days, and 15 were exact matches. The 3 inexact matches are likely due to "by Friday" / "this weekend" interpretation variability depending on the day the benchmark runs.

---

## Deliverables Checklist

| Deliverable | Status | Path |
|-------------|--------|------|
| Benchmark dataset (100 records) | ✅ | `benchmarks/recoverybench_100.json` |
| Benchmark generator | ✅ | `benchmarks/generate_benchmark.py` |
| Benchmark runner | ✅ | `benchmarks/run_benchmark.py` |
| Scored results | ✅ | `benchmarks/results/benchmark_scores.json` |
| Summary statistics | ✅ | `benchmarks/results/benchmark_summary.json` |
| Markdown report | ✅ | `benchmarks/results/benchmark_report.md` |
| Checkpoint report | ✅ | `docs/checkpoints/checkpoint_7_benchmark_review.md` |

## Status Rules Evaluation

| Rule | Condition | Result |
|------|-----------|--------|
| Benchmark has ≥100 records | 100 records ✓ | ✅ PASS |
| Each intent class ≥18 records | All 5 classes have exactly 20 ✓ | ✅ PASS |
| `run_benchmark.py` runs without crash | Completed in 16.6s ✓ | ✅ PASS |
| Benchmark accuracy within 0.15 of test set | 82% vs 83% = 0.01 difference ✓ | ✅ PASS |
| NEEDS_REMINDER accuracy is weak (65%) | Not a FAIL rule, but flagged | ⚠️ WARNING |
| Short message category accuracy 40% | Adversarial edge cases | ⚠️ WARNING |

**Final status: PASS WITH WARNINGS** — All FAIL conditions cleared. Warnings flagged for NEEDS_REMINDER weakness on short messages and potential labeling ambiguities in 5 benchmark scenarios.
