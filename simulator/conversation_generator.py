#!/usr/bin/env python3
"""
RecoveryBench — Conversation Generator

Generates realistic multi-turn debt collection conversations
with configurable personas, languages, and scenarios.

Usage:
    from simulator.conversation_generator import ConversationGenerator
    gen = ConversationGenerator()
    conversation = gen.generate()
"""

import random
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict


# ── Personas ───────────────────────────────────────────────────────────

@dataclass
class BorrowerPersona:
    """Represents a borrower archetype."""
    name: str
    intent: str
    tone: str
    cooperativeness: float  # 0-1
    description: str


@dataclass
class AgentPersona:
    """Represents a collection agent archetype."""
    name: str
    style: str
    compliance_level: str  # "high", "medium", "low"
    empathy: float  # 0-1
    description: str


BORROWER_PERSONAS = [
    BorrowerPersona("Cooperative Payer", "LIKELY_PAY", "calm", 0.9,
                     "Willing to pay, gives clear timeline"),
    BorrowerPersona("Forgetful Borrower", "NEEDS_REMINDER", "neutral", 0.7,
                     "Forgot about EMI, needs details"),
    BorrowerPersona("Genuine Disputant", "DISPUTE", "assertive", 0.5,
                     "Believes amount is wrong, wants verification"),
    BorrowerPersona("Hostile Refuser", "HIGH_RISK", "angry", 0.1,
                     "Refuses to pay, threatens back"),
    BorrowerPersona("Evasive Talker", "VAGUE", "evasive", 0.3,
                     "Non-committal, avoids clear answers"),
    BorrowerPersona("Already Paid", "ALREADY_PAID", "frustrated", 0.6,
                     "Claims to have already made payment"),
    BorrowerPersona("Salary Delay", "LIKELY_PAY", "apologetic", 0.8,
                     "Wants to pay but salary is delayed"),
    BorrowerPersona("Conditional Payer", "VAGUE", "cautious", 0.4,
                     "Will pay only if certain conditions are met"),
    BorrowerPersona("Partial Payer", "LIKELY_PAY", "negotiating", 0.7,
                     "Can pay part now, rest later"),
    BorrowerPersona("Distressed Borrower", "NEEDS_REMINDER", "emotional", 0.6,
                     "Facing financial hardship, needs help"),
]

AGENT_PERSONAS = [
    AgentPersona("Compliant Professional", "professional", "high", 0.8,
                  "Follows all RBI guidelines, empathetic"),
    AgentPersona("Firm but Fair", "firm", "high", 0.5,
                  "Direct communication, still compliant"),
    AgentPersona("Aggressive Collector", "aggressive", "low", 0.1,
                  "Uses threats, non-compliant language"),
    AgentPersona("Robotic Agent", "mechanical", "medium", 0.3,
                  "Script-following, lacks empathy"),
    AgentPersona("Empathetic Counselor", "empathetic", "high", 0.9,
                  "Very understanding, offers solutions"),
]

LANGUAGES = ["English", "Hindi", "Bengali", "Hinglish"]


# ── Message Templates ──────────────────────────────────────────────────

AGENT_OPENERS = {
    "English": [
        "Good morning, this is {agent_name} from {company}. I'm calling regarding your overdue EMI of ₹{amount}.",
        "Hello, I'm calling from {company} about your pending EMI payment of ₹{amount}.",
        "Hi, this is {agent_name}. Your EMI of ₹{amount} was due on {due_date} and remains unpaid.",
    ],
    "Hindi": [
        "Namaste, main {agent_name} bol raha hun {company} se. Aapki ₹{amount} ki EMI pending hai.",
        "Hello ji, {company} se bol rahe hain. Aapki EMI ₹{amount} overdue hai.",
        "Ji, main {company} se call kar raha hun. Aapki ₹{amount} ki payment {due_date} tak due thi.",
    ],
    "Bengali": [
        "Nomoskar, ami {agent_name} bolchi {company} theke. Apnar ₹{amount} er EMI pending ache.",
        "Hello, {company} theke bolchi. Apnar ₹{amount} er EMI overdue hoye geche.",
        "Ji, ami {company} theke call korchi. Apnar ₹{amount} er payment {due_date} porjonto due chhilo.",
    ],
    "Hinglish": [
        "Hello ji, {company} se {agent_name} bol raha hun. Your EMI of ₹{amount} pending hai.",
        "Hi, {company} se call kar raha hun regarding your ₹{amount} ki overdue EMI.",
        "Good morning, I'm calling from {company}. Aapki EMI ₹{amount} due hai since {due_date}.",
    ],
}

BORROWER_RESPONSES = {
    "LIKELY_PAY": {
        "English": [
            "Yes, I know. I'll pay by {timeline}.",
            "Sorry for the delay, I'll transfer the amount by {timeline}.",
            "I've kept the money aside, will pay by {timeline} for sure.",
            "My payment is scheduled for {timeline}, don't worry.",
            "I promise to pay by {timeline}. Please give me a few days.",
            "OK fine, I'll do NEFT by {timeline}.",
            "Let me pay in installments, first one by {timeline}.",
            "I am serious about paying, give me till {timeline}.",
        ],
        "Hindi": [
            "Haan bhai, {timeline} tak kar dunga payment.",
            "Sorry, salary aate hi immediately karunga. {timeline} tak pakka.",
            "Paisa arrange ho raha hai, {timeline} tak de dunga.",
            "Main zimmedar hun, {timeline} tak payment karunga.",
            "Abhi paisa nahi hai, {timeline} tak pakka.",
            "Thoda aur time do, {timeline} tak de dunga.",
            "Pura amount de dunga {timeline} tak.",
        ],
        "Bengali": [
            "Haan bhai, {timeline} er moddhe kore debo.",
            "Taka arrange hocche, {timeline} porjonto pakka diye debo.",
            "Ami serious, {timeline} porjonto pakka.",
            "Salary ashbe, tarpor e diye debo. {timeline} er moddhe.",
            "Ektu somoy dao, {timeline} er moddhe kore debo.",
            "Payment hoye jabe, {timeline} porjonto guarantee.",
        ],
        "Hinglish": [
            "Haan I know, will pay by {timeline}.",
            "Bhai let me arrange, {timeline} tak done.",
            "Ek aur chance do, {timeline} tak guaranteed.",
            "I promise bhai, {timeline} tak payment ho jayega.",
            "Money is ready, will transfer by {timeline}.",
        ],
    },
    "NEEDS_REMINDER": {
        "English": [
            "Oh, I forgot about this. Can you send me the details?",
            "Which EMI are we talking about? I thought auto-debit was on.",
            "I didn't realize it was already late. When was the due date?",
            "Sorry, I missed your earlier calls. Let me check my balance.",
            "Can you send me the bill again? I'll look into it.",
            "Give me a couple of days to sort this out.",
            "Is there a grace period?",
        ],
        "Hindi": [
            "Haan bhai, yaad nahi tha. Details bhej do.",
            "Kaun si EMI hai? Auto-debit on nahi tha kya?",
            "Mujhe pata nahi tha overdue hai. Email pe details bhej do.",
            "Busy tha, dekh lunga. Statement mil sakta hai?",
            "Bill dobara bhej do. Late fee kitni lagegi?",
            "SMS aaya tha kya? Nahi dekha.",
        ],
        "Bengali": [
            "Oh, bhule gechilam. Details ta pathao.",
            "Eta kon EMI? Auto-debit on chhilo na?",
            "Bujhe nii ami. Email e details pathao.",
            "Kaje busy chhilam, jordi korbo.",
            "Bill ta abar pathao. Late fee koto?",
            "SMS eshechhilo ki? Dekhini to.",
        ],
        "Hinglish": [
            "Oh I forgot about this. Can you resend the details?",
            "Which EMI? I thought auto-debit was on.",
            "Notification miss ho gayi. Email karo details please.",
            "Sorry missed your earlier calls. Any grace period?",
            "Bhai let me know the exact amount due.",
        ],
    },
    "DISPUTE": {
        "English": [
            "This amount is wrong. I don't owe this much.",
            "I never took this loan. Check your records.",
            "The interest calculation is incorrect. I need a breakdown.",
            "I paid through Paytm, check again.",
            "This is someone else's loan, not mine.",
            "I've been overcharged. Send me a detailed statement.",
            "My payment was credited but not showing in your system.",
        ],
        "Hindi": [
            "Ye galat amount hai. Maine ye loan nahi liya.",
            "Interest rate kyun badla? Agreement mein different terms the.",
            "Amount wo nahi hai jo sign kiya tha.",
            "Maine cheque se pay kiya, check karo.",
            "Outstanding amount se agree nahi hun main.",
            "Statement chahiye detailed, tab tak kuch nahi dunga.",
        ],
        "Bengali": [
            "Eta bhul amount. Ami ei loan niini.",
            "Interest rate keno bollo? Agreement e onno terms ache.",
            "Amount ota na jeta sign kora hoyechhilo.",
            "Ami PhonePe diye pay korechi, abar check koro.",
            "Ei amount bhul ache. Charges er breakdown pathao.",
        ],
        "Hinglish": [
            "Bhai ye amount wrong hai. Maine itna loan nahi liya.",
            "Interest rate change kaise hua? Agreement different tha.",
            "I dispute this charge. Send me complete breakdown.",
            "Did prepayment, not showing in system.",
            "Late fee wrong hai, I paid on time.",
            "Your system data is wrong bhai.",
        ],
    },
    "HIGH_RISK": {
        "English": [
            "Don't ever contact me again. I'm blocking this number.",
            "I will expose your company on social media.",
            "You can't do anything to me. Try if you dare.",
            "I have nothing to give. Leave me alone.",
            "I'm filing an FIR against you for harassment.",
            "Get lost. I don't care about your threats.",
            "Sue me if you want, I don't care.",
        ],
        "Hindi": [
            "Mujhe call karna band karo! Number block kar raha hun.",
            "Tum log scammer ho. Social media pe expose karunga.",
            "Tum mera kuch nahi kar sakte. Apna kaam karo.",
            "Nahi dunga aur ye final hai. Case karo jo karna hai.",
            "Bahut hua tumhara harassment. RBI mein complaint karunga.",
            "Time waste mat karo apna.",
        ],
        "Bengali": [
            "Amake call kora bondho koro. Number block korchi.",
            "Reputation noshto kore debo tomar company er.",
            "Toder lojja nei? Abar call korle complaint korbo.",
            "Kichu debar nei amar. Ja khoushi koro.",
            "Media te jabo. Eta harassment.",
            "Ja korcho illegal. Amar rights jana ache.",
        ],
        "Hinglish": [
            "Stop calling me. I'm blocking this number.",
            "Tum log scammers ho. I'll report you.",
            "Leave me alone or I'll take legal action against YOU.",
            "File a case if you dare. I don't care.",
            "Don't test me bhai. You harass innocent people.",
            "Never contact me again. Final answer: no payment.",
        ],
    },
    "VAGUE": {
        "English": [
            "I'll think about it.",
            "Maybe. Can't commit right now.",
            "It's complicated. I don't know.",
            "Possibly. Hard to say.",
            "We'll see. I'm not sure.",
            "I need time. Can't answer now.",
            "Might be able to. Not promising anything.",
        ],
        "Hindi": [
            "Sochunga.",
            "Shayad. Abhi commit nahi kar sakta.",
            "Mushkil hai. Pata nahi.",
            "Dekhte hain kya hota hai.",
            "Ho sakta hai. Promise nahi kar sakta.",
            "Batana mushkil hai.",
            "Dekhunga main.",
        ],
        "Bengali": [
            "Bhebhe dekhbo.",
            "Hoyto. Ekhon bolte parbo na.",
            "Mushkil obostha. Jani na.",
            "Dekha jak kichu hoy ki na.",
            "Hoyto hoye jabe. Promise korte parbo na.",
            "Complicated byapar.",
        ],
        "Hinglish": [
            "I'll consider it. Maybe later.",
            "Abhi can't say. Dekhta hun.",
            "It depends yaar. Not sure.",
            "Shayad. Dekho ja bhi.",
            "Not right now bhai. Maybe later.",
            "Hmm ok. Dekhte hain.",
        ],
    },
    "ALREADY_PAID": {
        "English": [
            "I already paid this last week. Check your records.",
            "Payment was already transferred via UPI. Check again.",
            "I made the payment by end of month. Your system is not updated.",
            "My bank shows the debit, payment is done.",
            "I paid through NEFT. Here's my transaction reference.",
            "The EMI was auto-debited from my account.",
        ],
        "Hindi": [
            "Bhai paisa already transfer kar diya hai. Records check karo.",
            "Payment ho chuka hai. Auto-debit se cover ho gayi thi.",
            "Paise bhej diye the, check karo.",
            "NEFT se bhej diya paisa. Transaction reference hai.",
            "EMI account se kat gayi thi already.",
        ],
        "Bengali": [
            "Ami already pay korechi. Records check koro.",
            "PhonePe diye transfer kore diyechi. Check koro.",
            "Transaction complete hoye gechilo. Records update koro.",
            "Auto-debit e hoye gechilo. Check koro.",
            "Taka pathiye diyechi. Check koro.",
        ],
        "Hinglish": [
            "Bhai already paid hai. Check your system.",
            "Transaction complete ho gaya, your side pe check karo.",
            "I already paid via UPI. Records dekho.",
            "Check please, my payment was successful.",
            "Proof hai payment ka, bhejun?",
        ],
    },
}

AGENT_FOLLOW_UPS = {
    "professional": {
        "English": [
            "I understand your situation. Let me note down the timeline you mentioned.",
            "Thank you for the commitment. We'll follow up on the date you provided.",
            "I appreciate your willingness to resolve this. Let me offer some options.",
            "We understand difficulties happen. Would you like to discuss a revised payment plan?",
        ],
        "Hindi": [
            "Samajhta hun aapki situation. Aapne jo timeline bataya wo note kar leta hun.",
            "Dhanyavaad commitment ke liye. Hum follow up karenge.",
            "Aapki pareshani samajhte hain. Kya aap payment plan discuss karna chahenge?",
        ],
        "Bengali": [
            "Apnar obostha bujhte parchi. Apni je timeline bolechhen sheita note korchi.",
            "Commitment er jonno dhonnobad. Amra follow up korbo.",
        ],
        "Hinglish": [
            "I understand sir. Let me note the timeline.",
            "Thank you for your commitment. Hum follow up karenge.",
            "Samajhta hun. Would you like to discuss a payment plan?",
        ],
    },
    "aggressive": {
        "English": [
            "You must pay immediately or we will take legal action.",
            "Final warning. If you don't pay by tomorrow, police will be informed.",
            "Don't test our patience. Pay now or face consequences.",
            "We know where you live. This won't end well for you.",
        ],
        "Hindi": [
            "Abhi ke abhi pay karo nahi toh legal action hoga.",
            "Ye last warning hai. Kal tak nahi diya toh police complaint hogi.",
            "Hamara patience test mat karo. Paisa do warna anjam bura hoga.",
            "Ghar walo ko bata denge. Sabko pata chal jayega.",
        ],
        "Bengali": [
            "Ekhuni pay koro nahole legal action hobe.",
            "Ei last warning. Kaal porjonto na dile police complaint hobe.",
            "Amader patience test koro na. Taka dao nahole kharap hobe.",
        ],
        "Hinglish": [
            "Pay immediately or legal action will be taken.",
            "Last chance hai. Don't blame us later.",
            "Tumhare ghar walo ko inform kar denge. Pay now.",
        ],
    },
    "empathetic": {
        "English": [
            "I completely understand, and I appreciate you sharing that with me. Let's find a solution together.",
            "Thank you for being honest. We have flexible options we can explore.",
            "I understand this is stressful. Our goal is to help you resolve this comfortably.",
            "I appreciate your openness. Let me see what restructuring options are available.",
        ],
        "Hindi": [
            "Bilkul samajhta hun aapki mushkil. Hum saath mein solution dhundhte hain.",
            "Shukriya imandari ke liye. Hamare paas flexible options hain.",
            "Aapki pareshani samajhte hain. Hum aapki madad karne chahte hain.",
        ],
        "Bengali": [
            "Ami puropuri bujhte parchi. Amra eksathe solution khujhbo.",
            "Shottota er jonno dhonnobad. Amader kache flexible options ache.",
            "Apnar koshto bujhi. Amra apnake sahayta korte chai.",
        ],
        "Hinglish": [
            "I completely understand. Let's find a solution together.",
            "Thank you for being honest. Flexible options hain hamare paas.",
            "Aapki problem samajhte hain. We want to help you resolve this.",
        ],
    },
    "mechanical": {
        "English": [
            "As per our records, your EMI of ₹{amount} is overdue. Please make the payment.",
            "Your account shows a pending balance. Kindly clear it at the earliest.",
            "This is a reminder regarding your outstanding dues. Please pay immediately.",
        ],
        "Hindi": [
            "Hamare records ke anusaar aapki ₹{amount} ki EMI pending hai. Payment karein.",
            "Aapke account mein pending balance hai. Jaldi se jaldi clear karein.",
            "Ye aapke outstanding dues ke baare mein reminder hai.",
        ],
        "Bengali": [
            "Amader records onusare apnar ₹{amount} er EMI pending ache. Payment korun.",
            "Apnar account e pending balance ache. Jotatari clear korun.",
        ],
        "Hinglish": [
            "As per records, your ₹{amount} EMI is pending. Please pay.",
            "Account mein balance pending hai. Kindly clear it.",
        ],
    },
    "firm": {
        "English": [
            "I understand, but payment is overdue. We need a concrete commitment from you.",
            "We've been flexible so far. We need to see action this time.",
            "I hear you, but this account needs resolution. What's your plan?",
        ],
        "Hindi": [
            "Samajhta hun, lekin payment overdue hai. Hamen pakka commitment chahiye.",
            "Ab tak humne flexibility dikhayi hai. Is baar action chahiye.",
            "Suna maine, lekin account resolve hona chahiye. Kya plan hai?",
        ],
        "Bengali": [
            "Bujhte parchi, kintu payment overdue. Amader pakka commitment chai.",
            "Amra etodin flexibility dieyechi. Ebar action chai.",
        ],
        "Hinglish": [
            "I understand, but payment is overdue. We need a commitment.",
            "We've been flexible. Ab action chahiye from your side.",
        ],
    },
}

TIMELINES = {
    "English": ["tomorrow", "by Friday", "next week", "end of this month",
                "in 2 days", "this weekend", "within a week", "by Wednesday"],
    "Hindi": ["kal", "Shukravaar tak", "agle hafte", "mahine ke end tak",
              "2 din mein", "is weekend", "ek hafte mein", "Budhvaar tak"],
    "Bengali": ["kaal", "Shukrobar porjonto", "agle shoptahe", "mash sheshe",
                "dui din e", "ei weekend", "ek shoptahe e", "Budhbar porjonto"],
    "Hinglish": ["tomorrow", "Friday tak", "next week", "month end tak",
                 "2 din mein", "this weekend", "ek hafte mein", "Wednesday tak"],
}

COMPANY_NAMES = [
    "ABC Finance", "QuickLoan Services", "PayEasy NBFC",
    "TrustCredit Solutions", "EasyPay Finance", "StarLend Corp",
    "PrimeDebt Solutions", "SwiftRecovery Ltd",
]

AGENT_NAMES = [
    "Rajesh", "Priya", "Amit", "Neha", "Suresh",
    "Anjali", "Vikram", "Meera", "Rahul", "Pooja",
]


# ── Conversation Generator ─────────────────────────────────────────────

class ConversationGenerator:
    """Generate realistic multi-turn debt collection conversations."""

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def generate(
        self,
        borrower_persona: Optional[BorrowerPersona] = None,
        agent_persona: Optional[AgentPersona] = None,
        language: Optional[str] = None,
        num_turns: Optional[int] = None,
    ) -> Dict:
        """
        Generate a single conversation.

        Returns:
            Dict with keys: conversation_id, language, borrower_persona,
            agent_persona, turns, metadata
        """
        # Pick parameters
        if borrower_persona is None:
            borrower_persona = random.choice(BORROWER_PERSONAS)
        if agent_persona is None:
            agent_persona = random.choice(AGENT_PERSONAS)
        if language is None:
            language = random.choice(LANGUAGES)
        if num_turns is None:
            num_turns = random.randint(2, 5)

        # Context
        amount = random.choice([5000, 8000, 10000, 12000, 15000, 20000, 25000, 50000])
        due_date = random.choice([
            "1st December", "15th November", "25th October",
            "5th January", "10th last month", "20th December",
        ])
        company = random.choice(COMPANY_NAMES)
        agent_name = random.choice(AGENT_NAMES)
        timeline = random.choice(TIMELINES.get(language, TIMELINES["English"]))

        context = {
            "amount": str(amount),
            "due_date": due_date,
            "company": company,
            "agent_name": agent_name,
            "timeline": timeline,
        }

        turns = []

        # Agent opener
        opener_templates = AGENT_OPENERS.get(language, AGENT_OPENERS["English"])
        opener = random.choice(opener_templates).format(**context)
        turns.append({"speaker": "agent", "message": opener})

        # Borrower response
        intent = borrower_persona.intent
        response_templates = BORROWER_RESPONSES.get(intent, {}).get(
            language, BORROWER_RESPONSES.get(intent, {}).get("English", ["I'll think about it."])
        )
        borrower_msg = random.choice(response_templates).format(**context)
        turns.append({"speaker": "borrower", "message": borrower_msg})

        # Additional turns
        for turn_idx in range(num_turns - 1):
            # Agent follow-up
            style = agent_persona.style
            follow_ups = AGENT_FOLLOW_UPS.get(style, AGENT_FOLLOW_UPS["mechanical"])
            lang_follow_ups = follow_ups.get(language, follow_ups.get("English", [
                "Please make the payment."
            ]))
            if lang_follow_ups:
                agent_msg = random.choice(lang_follow_ups).format(**context)
                turns.append({"speaker": "agent", "message": agent_msg})

            # Borrower follow-up (shorter, may shift tone)
            if turn_idx < num_turns - 2:
                follow_borrower_msg = random.choice(response_templates).format(**context)
                turns.append({"speaker": "borrower", "message": follow_borrower_msg})

        # Build conversation object
        conversation = {
            "conversation_id": str(uuid.uuid4())[:12],
            "timestamp": datetime.now().isoformat(),
            "language": language,
            "borrower_persona": {
                "name": borrower_persona.name,
                "intent": borrower_persona.intent,
                "tone": borrower_persona.tone,
                "cooperativeness": borrower_persona.cooperativeness,
            },
            "agent_persona": {
                "name": agent_persona.name,
                "style": agent_persona.style,
                "compliance_level": agent_persona.compliance_level,
                "empathy": agent_persona.empathy,
            },
            "context": {
                "amount": amount,
                "due_date": due_date,
                "company": company,
                "agent_name": agent_name,
            },
            "turns": turns,
            "num_turns": len(turns),
            "expected_intent": borrower_persona.intent,
            "expected_compliance": agent_persona.compliance_level == "high",
        }

        return conversation

    def generate_batch(
        self,
        count: int = 100,
        balance_intents: bool = True,
        balance_languages: bool = True,
    ) -> List[Dict]:
        """
        Generate a batch of conversations.

        Args:
            count: Number of conversations to generate
            balance_intents: If True, ensure roughly equal intent distribution
            balance_languages: If True, ensure roughly equal language distribution
        """
        conversations = []

        if balance_intents and balance_languages:
            # Generate equal splits across intents and languages
            intents = list(set(p.intent for p in BORROWER_PERSONAS))
            per_combo = max(1, count // (len(intents) * len(LANGUAGES)))
            remainder = count - (per_combo * len(intents) * len(LANGUAGES))

            for intent in intents:
                personas_for_intent = [
                    p for p in BORROWER_PERSONAS if p.intent == intent
                ]
                for lang in LANGUAGES:
                    for _ in range(per_combo):
                        bp = random.choice(personas_for_intent)
                        ap = random.choice(AGENT_PERSONAS)
                        conversations.append(self.generate(bp, ap, lang))

            # Fill remainder randomly
            for _ in range(remainder):
                conversations.append(self.generate())
        else:
            for _ in range(count):
                conversations.append(self.generate())

        random.shuffle(conversations)
        return conversations


if __name__ == "__main__":
    gen = ConversationGenerator(seed=42)
    conv = gen.generate()
    print(json.dumps(conv, indent=2, ensure_ascii=False))
    print(f"\nGenerated conversation with {conv['num_turns']} turns")
    print(f"Intent: {conv['expected_intent']}, Language: {conv['language']}")
