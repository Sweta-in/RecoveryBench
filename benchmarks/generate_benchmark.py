#!/usr/bin/env python3
"""
RecoveryBench-100 — Benchmark Suite Generator (Phase 1B)

Generates exactly 100 curated benchmark scenarios for evaluating
the RecoveryBench pipeline. Each scenario tests a specific aspect
of debt collection conversation analysis.

Usage:
    python benchmarks/generate_benchmark.py

Output:
    benchmarks/recoverybench_100.json
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_PATH = PROJECT_ROOT / "benchmarks" / "recoverybench_100.json"


# ─── Scenario Categories ─────────────────────────────────────────────
# 15 categories covering the key evaluation dimensions

SCENARIO_CATEGORIES = [
    "straightforward",          # Clear, unambiguous messages
    "temporal_promise",         # Messages with explicit timelines
    "conditional_promise",      # "if salary comes..." type promises
    "language_switching",       # Code-mixed or mid-sentence language switch
    "emotional_distress",       # Borrower under genuine stress
    "aggressive_refusal",       # Hostile / threatening responses
    "dispute_legitimate",       # Genuine amount/ownership disputes
    "dispute_evasion",          # Using "dispute" as avoidance tactic
    "vague_non_committal",      # Minimal, unclear responses
    "already_paid_claim",       # Claims of prior payment
    "partial_payment",          # Willing to pay part, not full
    "short_message",            # Very brief (1-5 word) messages
    "formal_english",           # Professional/formal register
    "colloquial_hindi",         # Heavy slang/colloquial Hindi
    "bengali_romanized",        # Romanized Bengali edge cases
]


def generate_benchmark():
    """Generate the RecoveryBench-100 benchmark dataset."""
    scenarios = []
    scenario_id = 1

    # ─── LIKELY_PAY (20 scenarios) ──────────────────────────────────
    likely_pay_scenarios = [
        # straightforward (2)
        {
            "borrower_message": "I will pay the full EMI amount by this Friday.",
            "agent_response": "Thank you for confirming. We have noted your commitment to pay by Friday. Your outstanding EMI is ₹8,500.",
            "language": "English",
            "category": "straightforward",
            "expected_promise": True,
            "expected_window_days": 4,
            "rationale": "Clear English promise with specific timeline — model should classify with high confidence.",
        },
        {
            "borrower_message": "haan bhai kal payment kar dunga pakka",
            "agent_response": "Dhanyavaad. Aapka EMI ₹5,000 hai. Kal tak payment ka intezaar karenge.",
            "language": "Hinglish",
            "category": "straightforward",
            "expected_promise": True,
            "expected_window_days": 1,
            "rationale": "Straightforward Hinglish promise with 'kal' and 'pakka' — strong commitment signals.",
        },
        # temporal_promise (3)
        {
            "borrower_message": "I'll transfer the amount next week when I get my salary",
            "agent_response": "We understand. We'll follow up next week. Your outstanding is ₹12,000.",
            "language": "English",
            "category": "temporal_promise",
            "expected_promise": True,
            "expected_window_days": 7,
            "rationale": "Promise tied to salary cycle with 'next week' temporal marker.",
        },
        {
            "borrower_message": "salary aane do bhai, agle hafte bhej dunga",
            "agent_response": "Aapki salary ke baad follow up karenge. EMI amount ₹7,500 hai.",
            "language": "Hinglish",
            "category": "temporal_promise",
            "expected_promise": True,
            "expected_window_days": 7,
            "rationale": "Hindi promise with 'agle hafte' temporal and 'bhej dunga' commitment verb.",
        },
        {
            "borrower_message": "month end tak kar dunga payment, thoda time do",
            "agent_response": "Theek hai, month end tak note kar liya hai. ₹6,000 pending hai.",
            "language": "Hinglish",
            "category": "temporal_promise",
            "expected_promise": True,
            "expected_window_days": 30,
            "rationale": "Month-end timeline with polite request for time — clear LIKELY_PAY.",
        },
        # conditional_promise (2)
        {
            "borrower_message": "agar is hafte salary aa gayi toh pakka kar dunga",
            "agent_response": "Noted. Hum is hafte end tak follow up karenge.",
            "language": "Hinglish",
            "category": "conditional_promise",
            "expected_promise": True,
            "expected_window_days": 7,
            "rationale": "Conditional on salary but strong intent ('pakka kar dunga'). Parser should detect.",
        },
        {
            "borrower_message": "If my client pays me this week, I can settle the full amount",
            "agent_response": "We appreciate your intent. We'll check back at end of week.",
            "language": "English",
            "category": "conditional_promise",
            "expected_promise": True,
            "expected_window_days": 7,
            "rationale": "Conditional promise in English — still indicates likely payment intent.",
        },
        # language_switching (2)
        {
            "borrower_message": "bhai I will definitely pay kal, abhi paisa nahi hai but tomorrow pakka",
            "agent_response": "Noted, we'll follow up tomorrow. Your pending amount is ₹4,500.",
            "language": "Hinglish",
            "category": "language_switching",
            "expected_promise": True,
            "expected_window_days": 1,
            "rationale": "Hinglish code-switching between English and Hindi — promise clearly present.",
        },
        {
            "borrower_message": "aaj nahi ho payega but agle hafte definitely transfer kar dunga account mein",
            "agent_response": "Thank you. Next week we will follow up.",
            "language": "Hinglish",
            "category": "language_switching",
            "expected_promise": True,
            "expected_window_days": 7,
            "rationale": "Mixed register — starts with refusal for today but commits for next week.",
        },
        # partial_payment (2)
        {
            "borrower_message": "I can pay half now and the rest by month end, is that okay?",
            "agent_response": "We can discuss a payment plan. Let me check options for you.",
            "language": "English",
            "category": "partial_payment",
            "expected_promise": True,
            "expected_window_days": 30,
            "rationale": "Partial payment offer with timeline — indicates payment intent.",
        },
        {
            "borrower_message": "abhi 3000 de sakta hun, baaki agle mahine mein",
            "agent_response": "Partial payment note kar liya. Baaki ke liye agle mahine follow up karenge.",
            "language": "Hinglish",
            "category": "partial_payment",
            "expected_promise": True,
            "expected_window_days": 30,
            "rationale": "Partial payment in Hinglish — commitment present for both tranches.",
        },
        # colloquial_hindi (2)
        {
            "borrower_message": "are yaar tension mat le, parso tak sab clear ho jayega",
            "agent_response": "Theek hai, parso tak ka note le liya hai.",
            "language": "Hindi",
            "category": "colloquial_hindi",
            "expected_promise": True,
            "expected_window_days": 2,
            "rationale": "Colloquial Hindi with 'parso' and reassurance — clear intent to pay.",
        },
        {
            "borrower_message": "chill kar bhai, weekend tak dal dunga paise account mein",
            "agent_response": "Weekend tak note kiya hai. ₹9,000 hai outstanding.",
            "language": "Hindi",
            "category": "colloquial_hindi",
            "expected_promise": True,
            "expected_window_days": 3,
            "rationale": "Slang Hindi — 'chill kar' is informal but 'dal dunga' shows clear payment intent.",
        },
        # bengali_romanized (2)
        {
            "borrower_message": "kaal payment korbo ami, chinta korben na",
            "agent_response": "Dhonnobad. Kaal follow up korbo.",
            "language": "Bengali",
            "category": "bengali_romanized",
            "expected_promise": True,
            "expected_window_days": 1,
            "rationale": "Romanized Bengali with 'kaal korbo' — tomorrow commitment.",
        },
        {
            "borrower_message": "salary ashle debo, ek shoptah lagbe",
            "agent_response": "Noted. Ek shoptah por follow up korbo.",
            "language": "Bengali",
            "category": "bengali_romanized",
            "expected_promise": True,
            "expected_window_days": 7,
            "rationale": "Bengali promise tied to salary with 'ek shoptah' (one week) timeline.",
        },
        # emotional_distress (2)
        {
            "borrower_message": "please understand bhai, bohot mushkil chal raha hai, but I will pay next week for sure",
            "agent_response": "We understand your situation. We'll follow up next week.",
            "language": "Hinglish",
            "category": "emotional_distress",
            "expected_promise": True,
            "expected_window_days": 7,
            "rationale": "Distressed but committed — emotional context shouldn't override clear payment promise.",
        },
        {
            "borrower_message": "I know I'm late and I'm sorry. Will transfer tomorrow morning first thing.",
            "agent_response": "We appreciate that. We'll confirm receipt tomorrow.",
            "language": "English",
            "category": "emotional_distress",
            "expected_promise": True,
            "expected_window_days": 1,
            "rationale": "Apologetic tone with firm commitment — clear LIKELY_PAY despite emotional language.",
        },
        # formal_english (2)
        {
            "borrower_message": "I acknowledge the outstanding amount and will arrange for payment within the next 3 business days.",
            "agent_response": "Thank you for your prompt response. We'll confirm receipt within 3 days.",
            "language": "English",
            "category": "formal_english",
            "expected_promise": True,
            "expected_window_days": 3,
            "rationale": "Formal register — should still be classified as LIKELY_PAY with clear timeline.",
        },
        {
            "borrower_message": "Please note that the NEFT transfer has been initiated and should reflect by tomorrow.",
            "agent_response": "Noted. We will verify the credit tomorrow.",
            "language": "English",
            "category": "formal_english",
            "expected_promise": True,
            "expected_window_days": 1,
            "rationale": "Formal English indicating payment already in process — strong LIKELY_PAY.",
        },
        # short_message (1)
        {
            "borrower_message": "haan kal pakka",
            "agent_response": "Noted, kal tak ka intezaar karenge.",
            "language": "Hindi",
            "category": "short_message",
            "expected_promise": True,
            "expected_window_days": 1,
            "rationale": "Very short Hindi promise — 'yes tomorrow for sure'. Brief but clear commitment.",
        },
    ]

    for s in likely_pay_scenarios:
        scenarios.append({
            "scenario_id": f"RB-{scenario_id:03d}",
            "expected_intent": "LIKELY_PAY",
            **s,
        })
        scenario_id += 1

    # ─── NEEDS_REMINDER (20 scenarios) ──────────────────────────────
    needs_reminder_scenarios = [
        # straightforward (2)
        {
            "borrower_message": "oh I forgot about it, how much is the amount?",
            "agent_response": "Your outstanding EMI is ₹5,500 due on June 1st.",
            "language": "English",
            "category": "straightforward",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Forgot about payment, asking for amount — needs a reminder with details.",
        },
        {
            "borrower_message": "haan yaad hai, thoda late ho gaya",
            "agent_response": "No problem. Aapka EMI ₹4,000 hai. Kab tak payment ho sakta hai?",
            "language": "Hinglish",
            "category": "straightforward",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Acknowledges debt but doesn't commit — classic NEEDS_REMINDER.",
        },
        # short_message (3)
        {
            "borrower_message": "ok",
            "agent_response": "Your EMI of ₹6,000 is pending. Would you like to make the payment today?",
            "language": "English",
            "category": "short_message",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Single-word acknowledgment — not a promise, not hostile. Needs follow-up.",
        },
        {
            "borrower_message": "theek hai",
            "agent_response": "Kya aap kal tak payment kar sakte hain?",
            "language": "Hindi",
            "category": "short_message",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Hindi 'ok' — acknowledges but doesn't commit. Needs reminder.",
        },
        {
            "borrower_message": "acha",
            "agent_response": "Aapka EMI ₹5,000 hai. Payment kab tak ho sakta hai?",
            "language": "Hindi",
            "category": "short_message",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Minimal Hindi response — ambiguous but leans toward needing reminder.",
        },
        # vague_non_committal (3)
        {
            "borrower_message": "haan haan, batao kitna dena hai?",
            "agent_response": "Aapka total outstanding ₹15,000 hai. Kab tak payment kar sakte hain?",
            "language": "Hinglish",
            "category": "vague_non_committal",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Asking for amount — shows awareness but no commitment yet.",
        },
        {
            "borrower_message": "send me the details again, I don't have the reference number",
            "agent_response": "Your loan ref: LN-45678. EMI: ₹8,000. Due date: May 15.",
            "language": "English",
            "category": "vague_non_committal",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Requesting info — engaged but not committing. Classic NEEDS_REMINDER.",
        },
        {
            "borrower_message": "which loan are you talking about? I have multiple EMIs",
            "agent_response": "This is regarding your personal loan with account number PL-12345.",
            "language": "English",
            "category": "vague_non_committal",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Confusion about which loan — needs clarification, not hostile.",
        },
        # language_switching (2)
        {
            "borrower_message": "haan pata hai bhai, will check and let you know",
            "agent_response": "Please check at your earliest. Amount is ₹7,000.",
            "language": "Hinglish",
            "category": "language_switching",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Code-mixed acknowledgment without commitment — needs follow-up.",
        },
        {
            "borrower_message": "let me check karta hun, account mein kitna hai dekhna padega",
            "agent_response": "Please check and let us know. Your EMI is ₹5,500.",
            "language": "Hinglish",
            "category": "language_switching",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Needs to check finances first — engaged but uncommitted.",
        },
        # emotional_distress (2)
        {
            "borrower_message": "I'm going through a rough patch right now, can you send me the details?",
            "agent_response": "We understand. Your EMI is ₹6,500. We can discuss flexible options.",
            "language": "English",
            "category": "emotional_distress",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Distressed but requesting info — not refusing, needs supportive follow-up.",
        },
        {
            "borrower_message": "bohot pareshani chal rahi hai, batao kya karna hai",
            "agent_response": "Hum samajhte hain. Payment plan ka option hai. Discuss karna chahenge?",
            "language": "Hindi",
            "category": "emotional_distress",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Hindi distress — asking 'what to do' indicates willingness to engage.",
        },
        # formal_english (2)
        {
            "borrower_message": "Could you please share the updated statement of account?",
            "agent_response": "Of course. Your current outstanding is ₹22,000 across two EMIs.",
            "language": "English",
            "category": "formal_english",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Formal request for info — not refusing, needs gentle follow-up with details.",
        },
        {
            "borrower_message": "I received your message. Let me review the amount and revert.",
            "agent_response": "Thank you. We'll await your response.",
            "language": "English",
            "category": "formal_english",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Professional acknowledgment without commitment — NEEDS_REMINDER.",
        },
        # bengali_romanized (2)
        {
            "borrower_message": "haan shunlam, koto taka bolun to?",
            "agent_response": "Apnar outstanding EMI 8000 taka. Payment korte parben?",
            "language": "Bengali",
            "category": "bengali_romanized",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Bengali 'I heard, tell me how much' — engaged but not committed.",
        },
        {
            "borrower_message": "accha thik ache, details pathao email e",
            "agent_response": "Email pathiye dilam. Please check and confirm.",
            "language": "Bengali",
            "category": "bengali_romanized",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Asking for details via email — needs follow-up after providing info.",
        },
        # colloquial_hindi (2)
        {
            "borrower_message": "haan bhai sun raha hun, bol",
            "agent_response": "Aapka EMI ₹4,500 overdue hai. Payment kab tak karenge?",
            "language": "Hindi",
            "category": "colloquial_hindi",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Casual 'I'm listening, tell me' — open but uncommitted.",
        },
        {
            "borrower_message": "yaad hai, abhi busy hun, baad mein baat karte hain",
            "agent_response": "Theek hai, hum phir se contact karenge.",
            "language": "Hindi",
            "category": "colloquial_hindi",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Busy now, talk later — not hostile but not committing either.",
        },
        # partial_payment (2)
        {
            "borrower_message": "how much exactly do I owe? break it down for me",
            "agent_response": "Principal: ₹10,000. Interest: ₹2,000. Late fee: ₹500. Total: ₹12,500.",
            "language": "English",
            "category": "partial_payment",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Requesting breakdown — shows engagement, may lead to payment or dispute.",
        },
        {
            "borrower_message": "kitna late fee laga hai? main amount to pata hai",
            "agent_response": "Late fee ₹750 hai. Total with late fee: ₹8,750.",
            "language": "Hinglish",
            "category": "partial_payment",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Knows main amount, asking about fees — engaged, needs details to commit.",
        },
    ]

    for s in needs_reminder_scenarios:
        scenarios.append({
            "scenario_id": f"RB-{scenario_id:03d}",
            "expected_intent": "NEEDS_REMINDER",
            **s,
        })
        scenario_id += 1

    # ─── DISPUTE (20 scenarios) ─────────────────────────────────────
    dispute_scenarios = [
        # straightforward (2)
        {
            "borrower_message": "This amount is wrong. I only took a loan of 50,000 not 75,000.",
            "agent_response": "We will verify the amount with our records. Please allow 48 hours.",
            "language": "English",
            "category": "straightforward",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Clear dispute about loan amount — legitimate contestation.",
        },
        {
            "borrower_message": "yeh galat amount hai bhai, check karo apne records",
            "agent_response": "Records verify karenge aur 24 ghante mein update denge.",
            "language": "Hinglish",
            "category": "straightforward",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Hindi dispute about wrong amount — standard dispute pattern.",
        },
        # dispute_legitimate (4)
        {
            "borrower_message": "I never took this loan. There must be some identity mix-up. Check the PAN number.",
            "agent_response": "We take this seriously. Let us verify with the PAN on file.",
            "language": "English",
            "category": "dispute_legitimate",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Identity dispute — possible fraud case, needs investigation.",
        },
        {
            "borrower_message": "I paid ₹15,000 last month through UPI but it's not showing in your records",
            "agent_response": "Please share the UPI transaction ID and we will trace it.",
            "language": "English",
            "category": "dispute_legitimate",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Payment dispute with specific claim — legitimate grievance.",
        },
        {
            "borrower_message": "mera loan to close ho chuka hai, aap log galat insaan ko call kar rahe ho",
            "agent_response": "Aapke account ka status verify karte hain. Loan number bata sakte hain?",
            "language": "Hindi",
            "category": "dispute_legitimate",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Claims loan is already closed — system records may be wrong.",
        },
        {
            "borrower_message": "interest rate 12% tha agreement mein, aap 18% kaise laga rahe ho?",
            "agent_response": "Agreement ki copy check karke update denge.",
            "language": "Hinglish",
            "category": "dispute_legitimate",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Interest rate dispute referencing agreement — genuine concern.",
        },
        # dispute_evasion (3)
        {
            "borrower_message": "I don't think this amount is right, I need to check with my CA",
            "agent_response": "Please check and get back to us within a week.",
            "language": "English",
            "category": "dispute_evasion",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Using 'need to check' as delay tactic — may be evasion disguised as dispute.",
        },
        {
            "borrower_message": "mujhe verify karna padega, mujhe yaad nahi hai yeh loan",
            "agent_response": "Kya aap apna loan agreement check kar sakte hain?",
            "language": "Hindi",
            "category": "dispute_evasion",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Claims to not remember the loan — could be genuine or evasive.",
        },
        {
            "borrower_message": "I'll dispute this with my bank, don't call me until then",
            "agent_response": "Noted. We'll await the dispute outcome.",
            "language": "English",
            "category": "dispute_evasion",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Threatening to dispute via bank — avoidance strategy.",
        },
        # language_switching (2)
        {
            "borrower_message": "bhai this is wrong amount, mera loan sirf 30000 ka tha, check karo please",
            "agent_response": "Records check karke confirm karenge.",
            "language": "Hinglish",
            "category": "language_switching",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Code-mixed dispute with specific amount claim.",
        },
        {
            "borrower_message": "ei taka to amar na, bhul hoyeche apnader, please check korun",
            "agent_response": "Apnar account verify korchi. 48 ghonta somoy lagbe.",
            "language": "Bengali",
            "category": "bengali_romanized",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Bengali dispute — 'this isn't my money, your mistake'.",
        },
        # formal_english (2)
        {
            "borrower_message": "I wish to formally contest this amount. The principal should be ₹40,000 as per my agreement dated March 2024.",
            "agent_response": "We will review the agreement and respond in writing.",
            "language": "English",
            "category": "formal_english",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Formal dispute with specific reference — highly legitimate.",
        },
        {
            "borrower_message": "As per our earlier discussion, the late penalty was to be waived. Please rectify.",
            "agent_response": "We will check internal records for prior commitments.",
            "language": "English",
            "category": "formal_english",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "References prior agreement to waive penalty — legitimate grievance.",
        },
        # already_paid_claim (3)
        {
            "borrower_message": "bhai already pay kar diya tha last week, receipt bhi hai mere paas",
            "agent_response": "Receipt number share kijiye, hum verify karte hain.",
            "language": "Hinglish",
            "category": "already_paid_claim",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Claims already paid with receipt — DISPUTE since contesting the outstanding amount.",
        },
        {
            "borrower_message": "Check your system, I made the payment via NEFT on June 5th",
            "agent_response": "Let us trace the NEFT transaction. Can you share the reference number?",
            "language": "English",
            "category": "already_paid_claim",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Claims payment made with date — needs verification, classified as DISPUTE.",
        },
        {
            "borrower_message": "ami to taka diye diyechi, apnara check korun records",
            "agent_response": "Transaction details pathiye din, amra verify korbo.",
            "language": "Bengali",
            "category": "already_paid_claim",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Bengali 'I already gave the money' — DISPUTE over payment records.",
        },
        # colloquial_hindi (2)
        {
            "borrower_message": "abe yeh kya zyada amount dikha raha hai, mera itna loan nahi tha",
            "agent_response": "Amount verify karte hain. Loan number bataiye.",
            "language": "Hindi",
            "category": "colloquial_hindi",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Aggressive but focused on amount — dispute not threat.",
        },
        {
            "borrower_message": "extra charge kyun lagaya? agreement mein toh nahi tha",
            "agent_response": "Charges ka breakdown aur agreement copy share karenge.",
            "language": "Hindi",
            "category": "colloquial_hindi",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Questioning extra charges with agreement reference — legitimate dispute.",
        },
        # emotional_distress (2)
        {
            "borrower_message": "You people are charging me double, this is not fair at all, I'm so stressed about this",
            "agent_response": "We understand your concern. Let us review the charges in detail.",
            "language": "English",
            "category": "emotional_distress",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Emotional response to perceived overcharging — dispute with distress.",
        },
        {
            "borrower_message": "itna pareshaan kar diya hai tum logon ne, galat amount laga ke",
            "agent_response": "Maafi chahte hain. Amount verify karke call back karenge.",
            "language": "Hindi",
            "category": "emotional_distress",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Distressed Hindi dispute about wrong amount.",
        },
    ]

    for s in dispute_scenarios:
        scenarios.append({
            "scenario_id": f"RB-{scenario_id:03d}",
            "expected_intent": "DISPUTE",
            **s,
        })
        scenario_id += 1

    # ─── HIGH_RISK (20 scenarios) ───────────────────────────────────
    high_risk_scenarios = [
        # aggressive_refusal (4)
        {
            "borrower_message": "STOP CALLING ME! I will file a complaint with consumer forum!",
            "agent_response": "I apologize. Let me connect you with our senior resolution specialist.",
            "language": "English",
            "category": "aggressive_refusal",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "ALL CAPS threat of consumer forum — classic HIGH_RISK aggressive.",
        },
        {
            "borrower_message": "ek aur call aaya toh police complaint karunga",
            "agent_response": "Maafi chahte hain. Senior agent se connect karte hain.",
            "language": "Hindi",
            "category": "aggressive_refusal",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Hindi threat of police complaint — high risk, needs escalation.",
        },
        {
            "borrower_message": "You people are harassing me. I will sue your company.",
            "agent_response": "We sincerely apologize. Let me transfer to our supervisor.",
            "language": "English",
            "category": "aggressive_refusal",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Harassment claim + legal threat — requires immediate escalation.",
        },
        {
            "borrower_message": "fraud company ho tum log, RBI mein complaint karunga",
            "agent_response": "Aapki chinta samajhte hain. Senior se baat karaate hain.",
            "language": "Hindi",
            "category": "aggressive_refusal",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Calling company 'fraud' + RBI complaint threat.",
        },
        # straightforward (2)
        {
            "borrower_message": "I am not going to pay. Do whatever you want.",
            "agent_response": "We understand. Would you like to discuss restructuring options?",
            "language": "English",
            "category": "straightforward",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Clear refusal — 'do whatever you want' is antagonistic.",
        },
        {
            "borrower_message": "nahi dunga paisa, jo karna hai karo",
            "agent_response": "Hum restructuring ka option de sakte hain. Sochiye.",
            "language": "Hindi",
            "category": "straightforward",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Hindi flat refusal — 'won't give money, do what you want'.",
        },
        # emotional_distress (3)
        {
            "borrower_message": "band karo phone! bohot ho gaya! harassment hai yeh!!!",
            "agent_response": "Maafi chahte hain. Hum apna approach change karenge.",
            "language": "Hindi",
            "category": "emotional_distress",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Extremely agitated with harassment accusation — needs de-escalation.",
        },
        {
            "borrower_message": "I can't take this anymore, you call 5 times a day, this is mental torture",
            "agent_response": "We're very sorry. We'll limit communications. Please speak with our manager.",
            "language": "English",
            "category": "emotional_distress",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Mental health concern — very high risk, needs immediate senior intervention.",
        },
        {
            "borrower_message": "tum logon ki wajah se mere ghar mein jhagda ho raha hai!!!",
            "agent_response": "Bohot maafi chahte hain. Manager se baat karaate hain.",
            "language": "Hindi",
            "category": "emotional_distress",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Family conflict caused by collection calls — HIGH_RISK needing sensitivity.",
        },
        # language_switching (2)
        {
            "borrower_message": "bhai I will go to court, this is fraud, tum log ke khilaf case karunga",
            "agent_response": "We understand your frustration. Please let our senior team help.",
            "language": "Hinglish",
            "category": "language_switching",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Code-mixed legal threat — 'court', 'fraud', 'case' all present.",
        },
        {
            "borrower_message": "stop this nonsense already! paisa nahi dunga, lawyer se baat karo meri",
            "agent_response": "Noted. Our legal team will respond.",
            "language": "Hinglish",
            "category": "language_switching",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "English + Hindi mix with lawyer reference — adversarial posture.",
        },
        # bengali_romanized (2)
        {
            "borrower_message": "ar phone korben na! consumer forum e jaabo!",
            "agent_response": "Amra maafi chai. Apnar concern senior ke janabo.",
            "language": "Bengali",
            "category": "bengali_romanized",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Bengali 'stop calling' + consumer forum threat.",
        },
        {
            "borrower_message": "chor company! amar taka niye fraud korcho!",
            "agent_response": "Apnar concern amra seriously nichchi. Investigation korbo.",
            "language": "Bengali",
            "category": "bengali_romanized",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Bengali — calling company 'thief' and accusing of fraud.",
        },
        # short_message (2)
        {
            "borrower_message": "stop!!!",
            "agent_response": "We apologize. We'll adjust our communication frequency.",
            "language": "English",
            "category": "short_message",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Single-word aggressive demand — exclamation marks signal distress/anger.",
        },
        {
            "borrower_message": "FRAUD!!! HARASSMENT!!!",
            "agent_response": "We're sorry. Let me connect you with a supervisor.",
            "language": "English",
            "category": "short_message",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "All-caps accusations — clear HIGH_RISK signal.",
        },
        # colloquial_hindi (2)
        {
            "borrower_message": "bahut ho gaya, ab phone kiya toh dekh lena, legal notice bhejunga",
            "agent_response": "Samajhte hain. Hum aapko further disturb nahi karenge.",
            "language": "Hindi",
            "category": "colloquial_hindi",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Implicit threat ('dekh lena') + legal notice — highly confrontational.",
        },
        {
            "borrower_message": "tere baap ka paisa hai kya? band kar phone warna dekh",
            "agent_response": "Maafi chahte hain. Yeh appropriate nahi hai humari taraf se.",
            "language": "Hindi",
            "category": "colloquial_hindi",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Extremely hostile colloquial Hindi — 'your father's money?'",
        },
        # formal_english (1)
        {
            "borrower_message": "I am instructing my lawyer to send a cease and desist notice. Any further contact will be considered harassment under the Indian Penal Code.",
            "agent_response": "Noted. Our legal team will review.",
            "language": "English",
            "category": "formal_english",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Formal legal threat — sophisticated but clearly HIGH_RISK.",
        },
        # dispute_evasion (2)
        {
            "borrower_message": "I don't owe you anything, stop sending me these messages or I'll report you",
            "agent_response": "We'll verify the account. Please allow us to investigate.",
            "language": "English",
            "category": "dispute_evasion",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Complete denial + threat to report — crosses from DISPUTE into HIGH_RISK.",
        },
        {
            "borrower_message": "mera koi loan nahi hai tumhare paas, galat number hai, dobara call mat karna!!!",
            "agent_response": "Account verify karte hain. Aapka PAN confirm kar sakte hain?",
            "language": "Hindi",
            "category": "dispute_evasion",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Claims no loan + aggressive demand to stop — HIGH_RISK with exclamation marks.",
        },
    ]

    for s in high_risk_scenarios:
        scenarios.append({
            "scenario_id": f"RB-{scenario_id:03d}",
            "expected_intent": "HIGH_RISK",
            **s,
        })
        scenario_id += 1

    # ─── VAGUE (20 scenarios) ───────────────────────────────────────
    vague_scenarios = [
        # vague_non_committal (4)
        {
            "borrower_message": "hmm dekhte hain",
            "agent_response": "Kya aap kal tak payment kar sakte hain?",
            "language": "Hindi",
            "category": "vague_non_committal",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Literal translation: 'hmm let's see' — classic non-commitment.",
        },
        {
            "borrower_message": "maybe, let me think about it",
            "agent_response": "Sure. We'll follow up tomorrow.",
            "language": "English",
            "category": "vague_non_committal",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "'Maybe' + 'let me think' — deliberately vague.",
        },
        {
            "borrower_message": "pata nahi kab ho payega",
            "agent_response": "Koi specific timeline de sakte hain?",
            "language": "Hindi",
            "category": "vague_non_committal",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "'Don't know when it'll happen' — no timeline, no commitment.",
        },
        {
            "borrower_message": "sochta hun, baad mein bataunga",
            "agent_response": "Theek hai, hum kal phir contact karenge.",
            "language": "Hindi",
            "category": "vague_non_committal",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "'Let me think, will tell later' — putting off commitment.",
        },
        # short_message (4)
        {
            "borrower_message": "hmm",
            "agent_response": "Kya aap payment ka plan share kar sakte hain?",
            "language": "Hindi",
            "category": "short_message",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Single syllable — impossible to determine intent.",
        },
        {
            "borrower_message": "...",
            "agent_response": "Can we discuss your payment options?",
            "language": "English",
            "category": "short_message",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Ellipsis only — passive disengagement.",
        },
        {
            "borrower_message": "K",
            "agent_response": "Would you like to discuss a payment plan?",
            "language": "English",
            "category": "short_message",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Single letter — minimal engagement, no commitment.",
        },
        {
            "borrower_message": "haan haan",
            "agent_response": "Kya specific date bata sakte hain payment ke liye?",
            "language": "Hindi",
            "category": "short_message",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Double 'yes' but without substance — agreeing to nothing specific.",
        },
        # straightforward (2)
        {
            "borrower_message": "I'm not sure what I can do right now",
            "agent_response": "We can help you explore options. What's your current situation?",
            "language": "English",
            "category": "straightforward",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Expresses uncertainty without refusal or commitment.",
        },
        {
            "borrower_message": "abhi kuch nahi bol sakta",
            "agent_response": "Theek hai. Kab baat kar sakte hain?",
            "language": "Hindi",
            "category": "straightforward",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "'Can't say anything right now' — stalling without refusing.",
        },
        # language_switching (2)
        {
            "borrower_message": "bhai abhi situation tough hai, let me figure it out",
            "agent_response": "Samajhte hain. Specific plan ho toh bataye.",
            "language": "Hinglish",
            "category": "language_switching",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Code-mixed vague response — situation tough, will figure out.",
        },
        {
            "borrower_message": "I'll see what I can do, abhi kuch promise nahi kar sakta",
            "agent_response": "We understand. Let us know when you have clarity.",
            "language": "Hinglish",
            "category": "language_switching",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Explicitly says 'can't promise anything now' — definitionally VAGUE.",
        },
        # bengali_romanized (2)
        {
            "borrower_message": "dekhchi ki korte pari",
            "agent_response": "Apnar convenience e amader janaben.",
            "language": "Bengali",
            "category": "bengali_romanized",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Bengali 'let me see what I can do' — vague stalling.",
        },
        {
            "borrower_message": "bujhte parchi na ki korbo",
            "agent_response": "Amra help korte pari. Payment plan discuss korben?",
            "language": "Bengali",
            "category": "bengali_romanized",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Bengali 'don't understand what to do' — confused and non-committal.",
        },
        # emotional_distress (2)
        {
            "borrower_message": "I don't know... things are really hard right now",
            "agent_response": "We understand you're going through a difficult time. Can we help?",
            "language": "English",
            "category": "emotional_distress",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Expressing helplessness — not refusing but not committing.",
        },
        {
            "borrower_message": "bohot mushkil hai bhai, kya karoon samajh nahi aa raha",
            "agent_response": "Hum samajhte hain. Aapke liye options dekhte hain.",
            "language": "Hindi",
            "category": "emotional_distress",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Hindi distress — 'don't know what to do'. VAGUE, not HIGH_RISK.",
        },
        # conditional_promise (2)
        {
            "borrower_message": "agar kuch jugaad ho gaya toh de dunga, nahi toh kya karun",
            "agent_response": "Samajhte hain. Hum agle hafte follow up karenge.",
            "language": "Hindi",
            "category": "conditional_promise",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Heavily conditional — 'if I manage something' is too vague for LIKELY_PAY.",
        },
        {
            "borrower_message": "If things work out, maybe I can pay something, not sure though",
            "agent_response": "Let us know when you have more clarity.",
            "language": "English",
            "category": "conditional_promise",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "'Maybe', 'not sure' — conditional language without real commitment. VAGUE.",
        },
        # colloquial_hindi (2)
        {
            "borrower_message": "dekho bhai kuch karna padega, abhi toh kuch nahi hai",
            "agent_response": "Theek hai, options discuss karte hain.",
            "language": "Hindi",
            "category": "colloquial_hindi",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "Acknowledges need to do something but no plan — VAGUE.",
        },
        {
            "borrower_message": "manage karna padega kuch na kuch, dekhta hun",
            "agent_response": "Theek hai, jab plan ho toh bataye.",
            "language": "Hindi",
            "category": "colloquial_hindi",
            "expected_promise": False,
            "expected_window_days": None,
            "rationale": "'Will have to manage somehow, let me see' — non-committal.",
        },
    ]

    for s in vague_scenarios:
        scenarios.append({
            "scenario_id": f"RB-{scenario_id:03d}",
            "expected_intent": "VAGUE",
            **s,
        })
        scenario_id += 1

    # ─── Validate and save ──────────────────────────────────────────
    assert len(scenarios) == 100, f"Expected 100 scenarios, got {len(scenarios)}"

    # Validate distribution
    from collections import Counter
    intent_dist = Counter(s["expected_intent"] for s in scenarios)
    lang_dist = Counter(s["language"] for s in scenarios)
    cat_dist = Counter(s["category"] for s in scenarios)

    print(f"Generated {len(scenarios)} benchmark scenarios")
    print(f"\nIntent distribution:")
    for intent, count in sorted(intent_dist.items()):
        print(f"  {intent}: {count}")

    print(f"\nLanguage distribution:")
    for lang, count in sorted(lang_dist.items()):
        print(f"  {lang}: {count}")

    print(f"\nCategory distribution:")
    for cat, count in sorted(cat_dist.items()):
        print(f"  {cat}: {count}")

    # Validate minimums
    for intent in ["LIKELY_PAY", "NEEDS_REMINDER", "DISPUTE", "HIGH_RISK", "VAGUE"]:
        assert intent_dist[intent] >= 18, f"{intent} has only {intent_dist[intent]} records (need >= 18)"

    # Verify all 15 categories present
    assert len(cat_dist) >= 14, f"Only {len(cat_dist)} categories present (need >= 14)"

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(scenarios, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Benchmark saved to {OUTPUT_PATH}")
    print(f"  File size: {OUTPUT_PATH.stat().st_size / 1024:.1f} KB")

    return scenarios


if __name__ == "__main__":
    generate_benchmark()
