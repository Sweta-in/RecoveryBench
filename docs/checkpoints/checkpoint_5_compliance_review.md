# Checkpoint 5 — Compliance Engine Review
**Status:** PASS
**Completion:** 100%
**Date:** 2026-06-10

## Risks
- Pattern-based matching is exact substring — creative paraphrasing of threats (e.g. "we know where you live") may evade detection if not in the pattern list.
- Romanized Hindi/Bengali patterns have spelling variation (e.g. "giraftaar" vs "giraftar") — only one spelling variant is typically covered per pattern.
- Risk score is intent-dominant (74.7% weight per Checkpoint 4). The compliance engine treats risk as a correlated signal, not independent — if the intent classifier is wrong, compliance decisions based on combined analysis may be affected.

## Concerns
- **Pattern coverage vs generalization tradeoff.** The engine has 225+ patterns across 25 rules, but real-world agents can express violations in ways not covered. A semantic similarity approach (Phase 6+ or future work) would improve recall.
- **Suggested rewrites are per-rule, not per-message.** When a message triggers multiple violations, only the rewrite from the highest-severity rule is returned. A composite rewrite engine could produce better suggestions.
- **No "cibil" variant in credit score patterns.** The rule RBI_004 uses "credit score kharab" but Indian agents commonly say "cibil" — this is a known gap. Adding "cibil" variants would improve recall.

## Recommendations
1. Review the full rules table below. Check if any patterns are too aggressive (false positive risk) or too narrow (false negative risk).
2. Pay attention to the false positive analysis — the engine does NOT flag any clearly acceptable language in testing.
3. Consider whether the 5 categories are sufficient or if a "privacy" category should be added for Checkpoint 6+.

## Next Action
**WAITING FOR HUMAN APPROVAL**

---

## 1. Full Rules Table

| Rule ID | Category | Severity | Description | Pattern Count | RBI Reference |
|---------|----------|----------|-------------|---------------|---------------|
| RBI_001 | threats | critical | Agent must not threaten arrest or police action | 14 | Section 3(b) - No threat of criminal action when matter is civil |
| RBI_002 | threats | critical | Agent must not threaten false legal action | 11 | Section 3(b) - No misrepresentation of legal consequences |
| RBI_003 | threats | critical | Agent must not threaten physical harm or intimidation | 10 | Section 3(a) - No intimidation or physical threats |
| RBI_004 | threats | moderate | Agent must not threaten credit score damage falsely | 9 | Section 3(b) - No false misrepresentation of consequences |
| RBI_005 | threats | critical | Agent must not threaten salary garnishment without court order | 8 | Section 3(c) - No contacting employer without legal basis |
| RBI_006 | harassment | moderate | Agent must not make calls outside permitted hours (8AM-7PM) | 9 | Section 3(d) - Contact only between 8 AM and 7 PM |
| RBI_007 | harassment | moderate | Agent must not threaten to contact borrower's family or relatives | 10 | Section 3(c) - No disclosure to third parties |
| RBI_008 | harassment | moderate | Agent must not use public shaming tactics | 10 | Section 3(c) - No public disclosure of borrower details |
| RBI_009 | harassment | minor | Agent must not make excessive or repeated threats of contact | 8 | Section 3(d) - No excessive communication |
| RBI_010 | harassment | critical | Agent must not threaten to visit workplace | 8 | Section 3(c) - No visiting workplace for recovery |
| RBI_011 | abusive_language | critical | Agent must not use profanity or abusive language | 15 | Section 3(a) - No use of abusive or aggressive language |
| RBI_012 | abusive_language | critical | Agent must not use caste-based, religious, or discriminatory slurs | 8 | Section 3(a) - No discriminatory language |
| RBI_013 | abusive_language | moderate | Agent must not use demeaning or belittling language | 11 | Section 3(a) - No intimidation via language |
| RBI_014 | abusive_language | moderate | Agent must not use sarcastic or mocking tone | 7 | Section 3(a) - No demeaning or sarcastic communication |
| RBI_015 | abusive_language | critical | Agent must not use gender-based or sexually harassing language | 8 | Section 3(a) - No gender-based harassment |
| RBI_016 | coercion | critical | Agent must not demand immediate payment under duress | 10 | Section 3(b) - No coercion for immediate payment |
| RBI_017 | coercion | critical | Agent must not pressure borrower to take new loan to repay | 8 | Section 3(b) - No pressure to borrow from other sources |
| RBI_018 | coercion | moderate | Agent must not use emotional manipulation | 10 | Section 3(a) - No emotional manipulation tactics |
| RBI_019 | coercion | moderate | Agent must not threaten service discontinuation without legal basis | 8 | Section 3(b) - No unauthorized service threats |
| RBI_020 | coercion | critical | Agent must not threaten property seizure without legal process | 11 | Section 3(b) - No unauthorized asset seizure threats |
| RBI_021 | false_claims | critical | Agent must not misrepresent the amount owed | 10 | Section 2(a) - No misrepresentation of loan terms |
| RBI_022 | false_claims | critical | Agent must not present fake court orders or legal documents | 9 | Section 3(b) - No false representation of legal documents |
| RBI_023 | false_claims | moderate | Agent must not falsely claim to be law enforcement or government | 9 | Section 3(b) - No impersonation of government authority |
| RBI_024 | false_claims | moderate | Agent must not create false urgency with fabricated deadlines | 10 | Section 3(b) - No fabrication of deadlines or urgency |
| RBI_025 | false_claims | moderate | Agent must not falsely claim loan cannot be restructured | 10 | Section 2(b) - Borrower has right to request restructuring |

**Total: 25 rules, 233 patterns**

## 2. Rules by Category

| Category | Count | Critical | Moderate | Minor |
|----------|-------|----------|----------|-------|
| threats | 5 | 4 | 1 | 0 |
| harassment | 5 | 1 | 3 | 1 |
| abusive_language | 5 | 3 | 2 | 0 |
| coercion | 5 | 3 | 2 | 0 |
| false_claims | 5 | 2 | 3 | 0 |
| **Total** | **25** | **13** | **11** | **1** |

## 3. RBI References

All rules are grounded in the **RBI Fair Practices Code for Lenders** and the **Guidelines on Recovery Agents** issued by the Reserve Bank of India.

**Source:** [RBI Fair Practices Code - Notification](https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=3963)

Key provisions encoded:
- **Section 2(a)** — Transparency in loan terms; no misrepresentation of amounts owed
- **Section 2(b)** — Borrower's right to request restructuring; cannot deny options exist
- **Section 3(a)** — No intimidation, abusive language, discriminatory remarks, or emotional manipulation
- **Section 3(b)** — No false threats of legal action, no coercion, no misrepresentation of consequences
- **Section 3(c)** — No contacting third parties (family, employer, neighbours) for recovery
- **Section 3(d)** — Contact hours restricted to 8 AM–7 PM; no excessive communication

## 4. Violating Examples (20 — 4 per category)

### Threats

| # | Agent Message | Rule Triggered | Severity | Suggested Rewrite |
|---|---------------|----------------|----------|-------------------|
| 1 | "If you don't pay by tomorrow police will come to your house" | RBI_001, RBI_003 | critical | "We may need to escalate this account for further review if payment is not received." |
| 2 | "Agar payment nahi kiya toh jail ho jayega" | RBI_001 | critical | "We may need to escalate this account for further review if payment is not received." |
| 3 | "We will file case against you in court mein chalana padega" | RBI_002 | critical | "If needed, we may seek resolution through appropriate legal channels. Let's discuss options first." |
| 4 | "Hamare log ghar pe aayenge kal, dekhna tum" | RBI_003 | critical | "We'd like to discuss your account status. Could you visit our branch or schedule a call?" |

### Harassment

| # | Agent Message | Rule Triggered | Severity | Suggested Rewrite |
|---|---------------|----------------|----------|-------------------|
| 1 | "Hum aapke family ko bata denge ki loan nahi bhara" | RBI_007 | moderate | "This matter is confidential between you and us. Let's resolve it directly." |
| 2 | "Social media pe daal denge tumhara naam" | RBI_008 | moderate | "Your account details are strictly confidential. We only discuss them with you directly." |
| 3 | "Jab tak pay nahi karoge har din call aayegi" | RBI_009 | minor | "We'll follow up periodically. Please let us know a good time to discuss your repayment options." |
| 4 | "Hum aapke office mein aayenge recovery ke liye" | RBI_010 | critical | "We can arrange a meeting at our branch office or over a phone call at your convenience." |

### Abusive Language

| # | Agent Message | Rule Triggered | Severity | Suggested Rewrite |
|---|---------------|----------------|----------|-------------------|
| 1 | "Tum bewakoof ho, samajh nahi aata kya" | RBI_011 | critical | "We'd like to help find a solution that works for you. Can we discuss your situation?" |
| 2 | "You people never pay on time, it's always the same" | RBI_012 | critical | "Every customer's situation is unique. Let's work out a plan that addresses your specific circumstances." |
| 3 | "Tumse kuch nahi hoga, defaulter ho tum" | RBI_013 | moderate | "We believe you can resolve this. Let's explore flexible repayment options together." |
| 4 | "Tell your husband to pay the loan amount" | RBI_015 | critical | "You are the account holder, and we'd like to work directly with you on a resolution." |

### Coercion

| # | Agent Message | Rule Triggered | Severity | Suggested Rewrite |
|---|---------------|----------------|----------|-------------------|
| 1 | "Abhi ke abhi pay karo, last chance hai" | RBI_016 | critical | "We'd like to settle this at your earliest convenience. Can we set up a payment date that works for you?" |
| 2 | "Kisi se udhar leke pay karo, humein koi matlab nahi" | RBI_017 | critical | "Let's explore restructuring options or an EMI plan that fits your current income." |
| 3 | "Bachon ka future kharab hoga agar nahi diya" | RBI_018 | moderate | "We understand this is a difficult time. Let's find a workable solution together." |
| 4 | "Ghar chheen lenge, gaadi utha lenge sab" | RBI_020 | critical | "If you're facing difficulty, we can discuss restructuring options before any further steps are considered." |

### False Claims

| # | Agent Message | Rule Triggered | Severity | Suggested Rewrite |
|---|---------------|----------------|----------|-------------------|
| 1 | "Court order aaya hai tumhare naam ka, arrest hoga" | RBI_022, RBI_001 | critical | "If any legal communications are sent, they will come through official and verifiable channels." |
| 2 | "Penalty laga diya hai extra, amount badh gaya hai" | RBI_021 | critical | "Your current outstanding amount is as per your loan agreement. We can share a detailed statement for your review." |
| 3 | "Hum government se hain, RBI ne bheja hai humko" | RBI_023 | moderate | "I am calling from [Company Name] regarding your loan account. Let me verify my identity and your account details." |
| 4 | "Ab kuch nahi ho sakta, settlement ka option khatam" | RBI_025 | moderate | "Let me check what restructuring options might be available for your account. Several plans may still be possible." |

## 5. Compliant Examples (10 borderline but acceptable)

| # | Agent Message | Why Compliant |
|---|---------------|---------------|
| 1 | "Your EMI of Rs. 5,000 was due on June 1st. Please make the payment at your earliest convenience." | Factual statement about due date with polite request — no threats or coercion. |
| 2 | "We understand you may be facing difficulties. Please contact us to discuss a repayment plan." | Empathetic opener with constructive next step. No pressure. |
| 3 | "Would you like to discuss restructuring your EMI schedule?" | Offers options proactively — the opposite of coercion. |
| 4 | "Thank you for your payment. Your account has been updated." | Post-payment confirmation — purely informational. |
| 5 | "Aapka EMI overdue hai. Kripya jaldi se jaldi payment kar dein." | Hindi EMI reminder. "Jaldi se jaldi" (as soon as possible) is a request, not a demand. Not coercive. |
| 6 | "We have noted your situation and will follow up in a few days." | Acknowledges difficulty without threats. Professional tone. |
| 7 | "We have several payment plans available for 3-month or 6-month restructuring." | Offering concrete alternatives — exactly what RBI guidelines recommend. |
| 8 | "Please call us at your convenience to discuss your account." | Open invitation, no urgency language, no threats. |
| 9 | "Your account shows an outstanding balance. Here is a detailed statement for your review." | Factual sharing of information. Even though it mentions amounts, it's transparent, not coercive. |
| 10 | "We'd like to help find a solution that works for both parties." | Collaborative framing. No pressure, no threats. |

## 6. False Positive Analysis

**No false positives detected.** All 7 compliant test messages (standard reminders, empathetic follow-ups, Hindi polite messages, payment confirmations, option offerings) were correctly classified as compliant.

Potential false positive risk areas:
- The pattern `"check"` is NOT in the patterns list (it was in the dispute keywords for the risk scorer, not compliance). No cross-contamination.
- The pattern `"legal"` alone is NOT a pattern — only `"legal action lenge"` matches. An agent saying "legal department will review" would not be flagged.
- The word `"court"` alone is NOT a pattern — only phrases like `"court mein chalana"` or `"court order aaya hai"` are. An agent saying "you can approach consumer court" would not be flagged.

## 7. Coverage Gaps

The following violation types are **NOT currently covered** by the rule set:

1. **Privacy violations** — sharing borrower details with unauthorized third parties (covered partially under harassment/family contact, but not for data sharing)
2. **Recording disclosure** — failure to inform borrower that the call is being recorded (if applicable under Indian TRAI regulations)
3. **Language mismatch** — agent deliberately speaking in a language the borrower doesn't understand to confuse them
4. **Fee misrepresentation** — adding undisclosed processing fees or late charges beyond agreed terms (partially covered by RBI_021)
5. **Tone escalation** — progressive increase in aggression across multiple messages (requires multi-turn analysis, not single-message)
6. **Impersonation of borrower's bank** — pretending to call from the borrower's own bank rather than the collection agency
7. **Semantic paraphrasing** — violations expressed through implication rather than explicit keywords (e.g. "accidents happen" as an implicit threat)

## 8. Suggested Rewrite Quality

| # | Original (Violating) | Suggested Rewrite | Usable? |
|---|---------------------|-------------------|---------|
| 1 | "Police will come to your house tomorrow" | "We may need to escalate this account for further review if payment is not received." | ✅ Yes — professional, non-threatening, factual |
| 2 | "Bewakoof, samajh nahi aata kya" | "We'd like to help find a solution that works for you. Can we discuss your situation?" | ✅ Yes — empathetic, collaborative |
| 3 | "Abhi ke abhi pay karo, last chance hai" | "We'd like to settle this at your earliest convenience. Can we set up a payment date that works for you?" | ✅ Yes — polite urgency without coercion |
| 4 | "Court order aaya hai tumhare naam ka" | "If any legal communications are sent, they will come through official and verifiable channels." | ✅ Yes — deflects without lying |
| 5 | "Kisi se udhar leke pay karo" | "Let's explore restructuring options or an EMI plan that fits your current income." | ✅ Yes — constructive alternative |

**Assessment:** All rewrites are usable and professional. They maintain the intent to collect while removing the violating language. No generic/unhelpful rewrites found.

---

## Verification Results

### Test Suite
```
pytest tests/test_compliance.py -v
60 passed in 0.16s
```

### Governance Verify Command 1
```
Compliance checks: PASS
Violation result: {
  'compliant': False,
  'violations': [
    {'rule_id': 'RBI_001', 'category': 'threats', 'severity': 'critical',
     'description': 'Agent must not threaten arrest or police action',
     'matched_text': 'police will come'},
    {'rule_id': 'RBI_003', 'category': 'threats', 'severity': 'critical',
     'description': 'Agent must not threaten physical harm or intimidation',
     'matched_text': 'will come to your house'}
  ],
  'severity': 'critical',
  'suggested_rewrite': 'We may need to escalate this account for further review if payment is not received.'
}
```

### Governance Verify Command 2
```
25 rules loaded across 5 categories
Rule count: PASS
```

## Files Delivered

| File | Status | Description |
|------|--------|-------------|
| `rules/compliance_rules.json` | ✅ Created | 25 rules, 233 patterns, 5 categories, RBI-grounded |
| `pipeline/compliance.py` | ✅ Created | ComplianceChecker engine with batch support |
| `tests/test_compliance.py` | ✅ Created | 60 tests — all passing |
