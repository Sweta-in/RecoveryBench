# RecoveryBench — Error Analysis Report
**Generated:** 2026-06-13T09:18:41.208335

## 1. Overall Summary

| Metric | Value |
|--------|-------|
| Total test examples | 601 |
| Correct predictions | 513 |
| Wrong predictions | 88 |
| Accuracy | 85.36% |
| Mean confidence (correct) | 0.7125 |
| Mean confidence (wrong) | 0.5082 |
| Mean latency | 1.58 ms |
| P95 latency | 2.71 ms |

## 2. Per-Class Error Rates

| Class | Total | Correct | Wrong | Accuracy | Error Rate |
|-------|-------|---------|-------|----------|------------|
| ALREADY_PAID | 92 | 20 | 72 | 21.74% | 78.26% |
| DISPUTE | 85 | 81 | 4 | 95.29% | 4.71% |
| HIGH_RISK | 91 | 88 | 3 | 96.70% | 3.30% |
| LIKELY_PAY | 115 | 112 | 3 | 97.39% | 2.61% |
| NEEDS_REMINDER | 92 | 86 | 6 | 93.48% | 6.52% |
| VAGUE | 126 | 126 | 0 | 100.00% | 0.00% |

## 3. Per-Language Error Rates

| Language | Total | Correct | Wrong | Accuracy |
|----------|-------|---------|-------|----------|
| Bengali | 159 | 132 | 27 | 83.02% |
| English | 145 | 126 | 19 | 86.90% |
| Hindi | 148 | 125 | 23 | 84.46% |
| Hinglish | 149 | 130 | 19 | 87.25% |

## 4. Top Confusion Pairs

| True Label → Predicted Label | Count |
|------------------------------|-------|
| ALREADY_PAID → DISPUTE | 33 |
| ALREADY_PAID → LIKELY_PAY | 25 |
| ALREADY_PAID → NEEDS_REMINDER | 10 |
| ALREADY_PAID → HIGH_RISK | 4 |
| DISPUTE → ALREADY_PAID | 3 |
| NEEDS_REMINDER → HIGH_RISK | 3 |
| NEEDS_REMINDER → DISPUTE | 2 |
| HIGH_RISK → ALREADY_PAID | 2 |
| NEEDS_REMINDER → VAGUE | 1 |
| LIKELY_PAY → DISPUTE | 1 |
| LIKELY_PAY → ALREADY_PAID | 1 |
| HIGH_RISK → VAGUE | 1 |
| DISPUTE → LIKELY_PAY | 1 |
| LIKELY_PAY → NEEDS_REMINDER | 1 |

## 5. Failure Mode Analysis

### 🔴 Already Paid Misclassification
**Severity:** critical
**Description:** ALREADY_PAID examples misclassified into other classes (0% recall)

- **Count:** 72
**Confusion Targets:**
  - DISPUTE: 33
  - LIKELY_PAY: 25
  - NEEDS_REMINDER: 10
  - HIGH_RISK: 4

### 🟡 Short Message Ambiguity
**Severity:** moderate
**Description:** Short messages (< 15 chars) are inherently ambiguous

- **Total Short:** 36
- **Wrong Short:** 0
- **Error Rate:** 0.0

### 🟠 High Confidence Mistakes
**Severity:** high
**Description:** Wrong predictions with confidence >= 0.60 (dangerous overconfidence)

- **Count:** 21
- **Mean Confidence:** 0.7763

### 🟡 Cross Language Variation
**Severity:** moderate
**Description:** Error rate varies across languages

**Error Rates:**
  - Bengali: 0.1698
  - English: 0.131
  - Hindi: 0.1554
  - Hinglish: 0.1275

## 6. Top 3 Failure Modes — Actionable Recommendations

### 1. ALREADY_PAID Class Collapse (Critical)
The TF-IDF model was trained on 5 classes only (no ALREADY_PAID training data).
Keyword override catches some cases but misses nuanced expressions.
**Fix:** Add ALREADY_PAID as a 6th training class with dedicated labelled data,
or fine-tune an IndicBERT model that can learn the distinction from context.

### 2. Short Message Ambiguity (Moderate)
Messages under 15 characters (e.g., 'ok', 'hmm', '...') lack sufficient
signal for any text classifier. These are inherently ambiguous even to humans.
**Fix:** Introduce a VAGUE-by-default policy for messages below a character
threshold, or request clarification in the agent response strategy.

### 3. High-Confidence Misclassifications (High)
Some wrong predictions carry confidence > 0.60, which is dangerous in
production because downstream systems trust the classifier's certainty.
**Fix:** Implement confidence calibration (Platt scaling) and add a
'needs-human-review' threshold band between 0.40–0.65.

## 7. Hard Examples Sample (first 25)

| # | Text | True | Predicted | Conf. | Lang | Reason |
|---|------|------|-----------|-------|------|--------|
| 1 | Partial 5th e korechilem ar baki 5th e boss??? | ALREADY_PAID | DISPUTE | 0.342 | Bengali | misclassified |
| 2 | Dude acCOUnt seTtle kOrE diyeChI | ALREADY_PAID | DISPUTE | 0.320 | Bengali | misclassified |
| 3 | Mere Mere co-applicant ne pay kar diya hai yaar | DISPUTE | ALREADY_PAID | 0.950 | Hindi | misclassified |
| 4 | I transffrred via bank transfer on 25th | ALREADY_PAID | DISPUTE | 0.483 | English | misclassified |
| 5 | I have the UTR number, want to see? | ALREADY_PAID | HIGH_RISK | 0.351 | English | misclassified |
| 6 | Ok Ok so the EMI was deducted from my account | ALREADY_PAID | NEEDS_REMINDER | 0.428 | English | misclassified |
| 7 | Kaun sa loan hai 🙂 | NEEDS_REMINDER | DISPUTE | 0.347 | Hindi | misclassified |
| 8 | Arey pAYMENT PROOF EMAIL MEIN HAI 💰 | ALREADY_PAID | LIKELY_PAY | 0.446 | Hindi | misclassified |
| 9 | App diye pay korechi, transaction ID ache | ALREADY_PAID | DISPUTE | 0.573 | Bengali | misclassified |
| 10 | RBI mein complaint kar chuka hun | HIGH_RISK | ALREADY_PAID | 0.950 | Hindi | misclassified |
| 11 | Mera CA dekhta hai ye sab, usse puchta hun | NEEDS_REMINDER | VAGUE | 0.330 | Hindi | misclassified |
| 12 | NEFT korechilem Shukrobar er moddhe, reflect howar | ALREADY_PAID | DISPUTE | 0.348 | Bengali | misclassified |
| 13 | Ok so alReaDy cleAreD, DOn'T CaLl aGaIn For ThIs 🙂 | ALREADY_PAID | HIGH_RISK | 0.379 | English | misclassified |
| 14 | Paytm diye pathiye diyechi taka | ALREADY_PAID | LIKELY_PAY | 0.594 | Bengali | misclassified |
| 15 | Payment proof is in my email, can forward | ALREADY_PAID | LIKELY_PAY | 0.415 | English | misclassified |
| 16 | See proof hai payment ka, bhej dun thx | ALREADY_PAID | LIKELY_PAY | 0.616 | Hinglish | misclassified |
| 17 | Paid in full, you should have it | ALREADY_PAID | DISPUTE | 0.339 | Hinglish | misclassified |
| 18 | Check 5th credit, woh mera payment hai | ALREADY_PAID | DISPUTE | 0.715 | Hinglish | misclassified |
| 19 | Proof hai payment ka, bhejun sir | ALREADY_PAID | LIKELY_PAY | 0.607 | Hindi | misclassified |
| 20 | Got confirmation after paying bhai | ALREADY_PAID | LIKELY_PAY | 0.438 | Hinglish | misclassified |
| 21 | Transaction shuru kore diyechi | LIKELY_PAY | DISPUTE | 0.409 | Bengali | misclassified |
| 22 | Dekho pAYMENT HO CHUKA HAI | ALREADY_PAID | LIKELY_PAY | 0.539 | Hindi | misclassified |
| 23 | Bhai aUTO-DEBIT 10TH E HOYECHHILO | ALREADY_PAID | NEEDS_REMINDER | 0.680 | Bengali | misclassified |
| 24 | NEFT kiya tha ek hafte mein, reflect hona chahiye | ALREADY_PAID | DISPUTE | 0.412 | Hindi | misclassified |
| 25 | Dekho this is resolved, payment was made | ALREADY_PAID | LIKELY_PAY | 0.386 | English | misclassified |

Full list: `analysis/reports/hard_examples.csv` (100 rows)

## 8. Recommendations for Next Iteration

1. **Retrain with ALREADY_PAID class** — include as 6th label in training data
2. **Upgrade to IndicBERT** — transformer embeddings will capture contextual
   nuances missed by character n-gram TF-IDF
3. **Confidence calibration** — apply Platt scaling to reduce overconfident errors
4. **Data augmentation** — more code-mixed and short-form examples
5. **Active learning loop** — route low-confidence predictions to human annotators
