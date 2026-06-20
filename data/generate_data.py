#!/usr/bin/env python3
"""
RecoveryBench — Multilingual Debt Collection Dataset Generator

Generates synthetic multilingual (English, Hindi, Bengali, Hinglish) debt collection
messages across 6 intent classes: LIKELY_PAY, NEEDS_REMINDER, DISPUTE, HIGH_RISK, VAGUE, ALREADY_PAID.

Generation strategy:
    1. Try local Ollama model first (free)
    2. Try HuggingFace Inference API free tier
    3. Fall back to comprehensive template-based generation (always works, no API needed)

Target: 200+ examples per class per language = 4,000+ rows minimum.
"""

import csv
import os
import sys
import random
import hashlib
import logging
from pathlib import Path
from difflib import SequenceMatcher
from collections import defaultdict
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ============================================================
# Constants
# ============================================================

CLASSES = ["LIKELY_PAY", "NEEDS_REMINDER", "DISPUTE", "HIGH_RISK", "VAGUE", "ALREADY_PAID"]
LANGUAGES = ["English", "Hindi", "Bengali", "Hinglish"]
TARGET_PER_CLASS_PER_LANGUAGE = 300  # Generate extra to survive dedup
MIN_LENGTH = 3
MAX_LENGTH = 300
NEAR_DUPLICATE_THRESHOLD = 0.92  # 0.85 was too aggressive for template data
RANDOM_SEED = 42

CLASS_DESCRIPTIONS = {
    "LIKELY_PAY": "Borrower clearly intends to pay, may give a timeline",
    "NEEDS_REMINDER": "Forgot or vague, needs a follow-up nudge",
    "DISPUTE": "Contesting the debt amount, ownership, or validity",
    "HIGH_RISK": "Hostile, threatening, or completely avoidant",
    "VAGUE": "Non-committal, unclear, monosyllabic",
    "ALREADY_PAID": "Borrower claims payment has already been made",
}

# ============================================================
# Template-Based Generator — Comprehensive & Realistic
# ============================================================

TEMPLATES = {
    "LIKELY_PAY": {
        "English": [
            "I will pay by {day}",
            "Payment will be done {timeframe}",
            "Yes I know, will transfer {timeframe}",
            "Salary coming on {date_num}, will pay immediately after",
            "I'll pay the full amount {timeframe}",
            "Don't worry, payment is on the way",
            "I'm arranging the money, will pay {timeframe}",
            "Will do NEFT {timeframe}",
            "I'll clear the dues {timeframe}",
            "Can I pay in two parts? First part {timeframe}",
            "I just need {days} more days",
            "My payment is scheduled for {day}",
            "I am transferring today evening",
            "Will pay before end of this month",
            "Money is ready, will transfer {timeframe}",
            "Paying today itself, please wait",
            "Let me pay half now and rest {timeframe}",
            "I already initiated the transfer, please check",
            "I will definitely pay, just give me till {day}",
            "Will make the payment right now",
            "Just processing the payment, will be done in an hour",
            "I promise to pay by {day} for sure",
            "Can you share UPI? I will pay now",
            "Ok I understand, paying {timeframe}",
            "Will clear the pending amount before {day}",
            "I am serious about paying, give me {days} days",
            "Payment confirmed for {day}",
            "Sorry for delay, paying {timeframe} definitely",
            "I've kept the money aside, will pay {timeframe}",
            "Yes yes, I will pay this week only",
            "I can do partial payment today",
            "I've already spoken to my bank, transfer will come {timeframe}",
            "I am ready to pay, please share account details",
            "The amount will be credited {timeframe}",
            "I accept the due amount, will pay {timeframe}",
            "Fine, I will pay. How much exactly?",
            "Let me check my balance and pay {timeframe}",
            "I had forgotten, but I will pay now",
            "Ok fine, take the payment {timeframe}",
            "My friend will lend me, I'll pay {timeframe}",
            "I am not avoiding payment, I will pay {timeframe}",
            "Payment will be done, I assure you",
            "No problem, I will arrange the money",
            "Give me one more day, will pay for sure",
            "I got my bonus, paying {timeframe}",
            "Transaction initiated already",
            "I remember now, let me pay quickly",
            "You will receive payment {timeframe}, guaranteed",
            "Consider it done, paying {timeframe}",
            "Just waiting for my salary to hit, then paying immediately",
        ],
        "Hindi": [
            "Kal payment kar dunga",
            "Haan bhai, {timeframe_hi} tak kar dunga",
            "Paisa arrange ho raha hai, {timeframe_hi} mein de dunga",
            "Salary aa jayegi {day_hi} ko, uske baad turant",
            "Main payment karunga, tension mat lo",
            "Abhi paisa nahi hai, {timeframe_hi} tak pakka",
            "Haan mujhe pata hai, {timeframe_hi} kar dunga",
            "NEFT kar dunga {timeframe_hi}",
            "Pura amount de dunga {timeframe_hi}",
            "Do hisson mein de sakta hun, pehla {timeframe_hi}",
            "Mujhe {days} din aur chahiye bas",
            "Aaj shaam tak transfer kar dunga",
            "Payment fix hai {day_hi} ko",
            "UPI bhej do, abhi kar deta hun",
            "Aaj hi payment ho jayega",
            "Main kar raha hun arrange, {timeframe_hi} tak ho jayega",
            "Half abhi de deta hun, baaki {timeframe_hi}",
            "Main serious hun, {timeframe_hi} tak pakka",
            "Bilkul karunga payment",
            "Thoda aur time do, {timeframe_hi} tak de dunga",
            "Paise ready hain, transfer kar raha hun",
            "Bhai promise karta hun, {timeframe_hi} tak",
            "Maine apne side se arrangement kar liya hai",
            "Amount bhej raha hun thodi der mein",
            "Salary aate hi turant karunga",
            "Abhi process mein hai payment",
            "Ek-do ghante mein ho jayega",
            "Parso tak pakka de dunga",
            "Main bhool gaya tha, abhi karta hun",
            "Account number do, abhi transfer karta hun",
            "Poora paisa ek saath de dunga",
            "Main kabhi mana nahi kiya, payment karunga",
            "Bas thoda sa wait karo",
            "Aaj raat tak ho jayega",
            "Main koshish kar raha hun, {timeframe_hi} tak",
            "Online payment kar deta hun abhi",
            "EMI amount ready hai, bhej raha hun",
            "Mera plan hai {day_hi} ko dene ka",
            "Bonus aaya hai, abhi de deta hun",
            "Transaction start kar diya hai",
            "De dunga, chinta mat karo",
            "Ek din aur please, pakka dunga",
            "Bhai time pe de dunga",
            "Main zimmedar hun, payment karunga",
            "EMI ka paisa alag rakha hai",
            "Bas salary ka wait hai",
            "De raha hun, patience rakho",
            "Koshish karunga jaldi se jaldi",
            "Haan theek hai, de deta hun",
            "Payment ho jayega, guarantee deta hun",
        ],
        "Bengali": [
            "Kaal payment kore debo",
            "Haan bhai, {timeframe_bn} er moddhe kore debo",
            "Taka arrange hocche, {timeframe_bn} diye debo",
            "Salary ashbe {day_bn}, tarpor e diye debo",
            "Ami payment korbo, tension nio na",
            "Ekhon taka nei, {timeframe_bn} porjonto wait koro",
            "Haan jani, {timeframe_bn} e korbo",
            "Transfer kore debo {timeframe_bn}",
            "Pura taka diye debo {timeframe_bn}",
            "Dui bhage dite pari, prothom ta {timeframe_bn}",
            "Amake aro {days} din dao",
            "Aaj bikale transfer kore debo",
            "Payment fix ache {day_bn}",
            "UPI pathao, ekhon e kori",
            "Aaj e payment hoye jabe",
            "Ami arrange korchi, {timeframe_bn} hoye jabe",
            "Adha ekhon, baki ta {timeframe_bn}",
            "Ami serious, {timeframe_bn} porjonto pakka",
            "Nishchoi payment korbo",
            "Ektu somoy dao, {timeframe_bn} diye debo",
            "Taka ready, transfer korchi",
            "Promise korchi, {timeframe_bn} e",
            "Amar side theke arrangement hoye geche",
            "Taka pathacchi ektu pore",
            "Salary ashle tukni korbo",
            "Ekhon process e ache payment",
            "Ek-dui ghontar moddhe hoye jabe",
            "Porshudino porjonto pakka diye debo",
            "Bhule gechilam, ekhon korchi",
            "Account number dao, ekhon transfer kori",
            "Poora taka ekbare diye debo",
            "Ami kokhono mana korini, payment korbo",
            "Bas ektu wait koro",
            "Aaj raater moddhe hoye jabe",
            "Ami cheshta korchi, {timeframe_bn} e",
            "Online payment kore dii ekhon",
            "EMI er taka ready, pathacchi",
            "Amar plan ache {day_bn} dite",
            "Bonus peyechi, ekhon e dei",
            "Transaction shuru kore diyechi",
            "Diye debo, chinta koro na",
            "Ekdin aro please, pakka debo",
            "Bhai time e diye debo",
            "Ami responsible, payment korbo",
            "EMI taka alag rekhechi",
            "Salary er wait ache bas",
            "Diye debo, dhairyo dhoro",
            "Cheshta korbo taratari",
            "Haan thik ache, diye dii",
            "Payment hoye jabe, guarantee dichhi",
        ],
        "Hinglish": [
            "Bhai salary nahi aayi abhi, {timeframe_hi} mein pakka kar dunga",
            "Haan I know, will pay {timeframe}",
            "Payment ho jayega by {day}",
            "Kal se pehle kar dunga definitely",
            "Bro let me arrange, {timeframe_hi} tak done",
            "I will do NEFT {timeframe_hi} mein",
            "Salary aate hi immediately karunga",
            "Yaar {days} din aur de do, pakka payment",
            "Transfer initiate kar diya hai already",
            "Ok bhai, I'll pay {timeframe}",
            "Thoda time chahiye, but I will pay for sure",
            "Amount ready hai, bas transfer karna hai",
            "Aaj evening ko payment kar deta hun",
            "I promise bhai, {timeframe_hi} tak",
            "Half now baaki {timeframe}",
            "UPI ID share karo, abhi bhejta hun",
            "Let me check balance, {timeframe_hi} mein done",
            "Bhai mera bonus aaya hai, paying today",
            "I'm not running away, will pay {timeframe}",
            "Paisa arrange ho gaya, aaj transfer",
            "Haan haan karunga, {timeframe_hi} tak pakka",
            "Bro tension mat le, I'll clear it {timeframe}",
            "Give me {days} more days please",
            "Meri side se confirmed hai payment",
            "I forgot sorry, will do it now",
            "Bhai paise rakh diye hain, just need to transfer",
            "Full amount de dunga {timeframe}",
            "Main kabhi avoid nahi karta, will pay",
            "Salary credited nahi hui, but jaise hi aaye payment done",
            "Let me pay in installments, first one {timeframe}",
            "I accept the amount, will pay {timeframe}",
            "Bhai I have arranged already, doing NEFT",
            "Don't worry yaar, karke dunga",
            "Today raat tak ho jayega guarantee",
            "Main zimmedar hun, definitely paying",
            "EMI ka paisa alag set hai",
            "Account details do, abhi karta hun",
            "Ek aur chance do, {timeframe_hi} guaranteed",
            "Processing hai bhai, thoda wait",
            "Boss ne salary hold ki thi, ab aayi, de dunga",
            "Bhai mera plan hai {day} ko clear karna",
            "Koshish karunga within {days} days",
            "Consider it done, paying {timeframe}",
            "Meri taraf se pakka, no tension",
            "I got money from friend, paying now",
            "Abhi tight hai but {timeframe_hi} tak karunga",
            "Let me do partial now, rest later",
            "I'm serious about this, will pay {timeframe}",
            "Already talked to bank, will come {timeframe}",
            "Payment guaranteed, just {days} more days",
        ],
    },
    "NEEDS_REMINDER": {
        "English": [
            "Oh I forgot about this",
            "When was the due date again?",
            "I didn't get any notification",
            "Can you remind me later?",
            "Is it already due? I thought it was next month",
            "How much is it exactly?",
            "I'll check and let you know",
            "What's the account number for payment?",
            "Sorry I was busy, will look into it",
            "I need to check my bank balance first",
            "Send me the details again please",
            "Can you call me tomorrow about this?",
            "I wasn't aware it was overdue",
            "Let me get back to you on this",
            "How many days overdue is it?",
            "I think I missed the notification",
            "Was there an SMS? I didn't see it",
            "Ok noted, let me check",
            "I'll handle it soon",
            "Which EMI is this for?",
            "Remind me once more next week please",
            "I lost track of the dates",
            "I changed my number, didn't get reminders",
            "Where do I pay? What's the link?",
            "I thought auto-debit was on",
            "Ok I'll look into it this weekend",
            "Thanks for telling me, I'll check",
            "My accountant handles this, let me ask",
            "Can you send the bill again?",
            "I need to verify the amount",
            "Give me a couple of days to sort this out",
            "I was traveling, just got back",
            "Sorry missed your earlier calls",
            "How do I set up auto-pay?",
            "Ok let me figure this out",
            "I changed banks recently, need to update",
            "Which loan are we talking about?",
            "Can I get a statement?",
            "I need to talk to my spouse first",
            "I'll review my finances and get back",
            "Honestly I just forgot, sorry",
            "Can you email me the details?",
            "What's the penalty if I pay late?",
            "Is there a grace period?",
            "I'll take care of it, don't keep calling",
            "Just busy with work, will handle soon",
            "Where can I check my outstanding?",
            "Ok understood, I'll do something about it",
            "Let me know the exact amount due",
            "I didn't realize it was already late",
        ],
        "Hindi": [
            "Oh bhool gaya tha",
            "Due date kab thi?",
            "Notification nahi aaya mujhe",
            "Baad mein yaad dilana please",
            "Abhi due ho gaya? Mujhe laga next month hai",
            "Kitna hai exactly?",
            "Check karke batata hun",
            "Payment ka account number kya hai?",
            "Busy tha, dekh lunga",
            "Pehle bank balance check karna padega",
            "Details fir se bhejo",
            "Kal call kar lena is baare mein",
            "Mujhe pata nahi tha overdue hai",
            "Main baad mein batata hun",
            "Kitne din overdue hai?",
            "Notification miss ho gayi lagta hai",
            "SMS aaya tha kya? Nahi dekha",
            "Ok noted, check karta hun",
            "Jaldi handle karunga",
            "Ye kaun si EMI hai?",
            "Agle hafte yaad dilana fir se",
            "Dates ka track nahi raha",
            "Number change kiya tha, reminder nahi aaya",
            "Kahan pay karna hai? Link bhejo",
            "Auto-debit on tha na?",
            "Weekend mein dekhta hun",
            "Batane ke liye shukriya, check karunga",
            "Mera CA dekhta hai ye sab, usse puchta hun",
            "Bill dobara bhej do",
            "Amount verify karna padega",
            "Do din do sort karne ke liye",
            "Travel pe tha, abhi aaya hun",
            "Pichli calls miss ho gayi sorry",
            "Auto-pay kaise set karna hai?",
            "Samajh leta hun main",
            "Bank change kiya recently, update karna hai",
            "Kaun sa loan hai?",
            "Statement mil sakta hai?",
            "Pehle wife se baat karna padega",
            "Finances check karke batata hun",
            "Sach mein bhool gaya tha, sorry",
            "Email pe details bhej do",
            "Late fee kitni lagegi?",
            "Grace period milta hai kya?",
            "Karunga, baar baar call mat karo",
            "Kaam mein busy hun, jaldi karunga",
            "Outstanding kahan check karun?",
            "Samajh gaya, kuch karunga",
            "Exact due amount batao",
            "Pata hi nahi chala late ho gaya",
        ],
        "Bengali": [
            "Oh bhule gechilam",
            "Due date kokhon chhilo?",
            "Amake notification asheni",
            "Pore mone koriye dio please",
            "Ekhon e due hoye geche? Ami bhebechilam porer mash",
            "Koto taka exactly?",
            "Check kore janabo",
            "Payment er account number ki?",
            "Busy chhilam, dekhbo",
            "Age bank balance check korte hobe",
            "Details ta abar pathao",
            "Kaal call koro ei byapare",
            "Ami jantam na overdue hoyeche",
            "Pore bolbo ami",
            "Koto din overdue hoyeche?",
            "Notification miss hoye geche mone hoy",
            "SMS eshechhilo ki? Dekhini to",
            "Ok noted, check korchi",
            "Taratari handle korbo",
            "Eta kon EMI?",
            "Agle shoptahe mone koriyo",
            "Dates er track rakhte parini",
            "Number change korechi, reminder asheni",
            "Kothai pay korte hobe? Link dao",
            "Auto-debit on chhilo na?",
            "Weekend e dekhchi",
            "Janano r jonno dhonnobad, check korbo",
            "Amar CA dekhe ei shob, take jigges kori",
            "Bill ta abar pathao",
            "Amount verify korte hobe",
            "Dui din dao sort korar jonno",
            "Travel e chhilam, ekhon firchi",
            "Ager call gulo miss hoye geche sorry",
            "Auto-pay kibhabe set korte hoy?",
            "Bujhe nii ami",
            "Bank change korechi recently, update korte hobe",
            "Kon loan er kotha bolcho?",
            "Statement pawa jabe?",
            "Age bou er shathe kotha bolte hobe",
            "Finance check kore janabo",
            "Shotti bhule gechilam, sorry",
            "Email e details pathao",
            "Late fee koto lagbe?",
            "Grace period ache ki?",
            "Korbo, bar bar call koro na",
            "Kaje busy, jholdi korbo",
            "Outstanding kothay check korbo?",
            "Bujhechi, kichu ekta korbo",
            "Exact due amount bolo",
            "Bujhtei parlam na je late hoye geche",
        ],
        "Hinglish": [
            "Oh yaar forgot about this one",
            "Due date kab thi again?",
            "Bhai notification nahi aaya",
            "Remind me later please",
            "Already due? I thought next month hai",
            "Exactly kitna hai?",
            "Let me check and I'll tell you",
            "Account number kya hai for payment?",
            "Was busy, will look into it",
            "Pehle balance check karna padega",
            "Send details again please",
            "Call me tomorrow about this",
            "Didn't know it was overdue yaar",
            "I'll get back to you",
            "How many days overdue hai?",
            "I think notification miss ho gayi",
            "SMS aaya tha kya? Nahi dekha",
            "Ok noted, will check",
            "Handle karunga jaldi",
            "Which EMI is this for?",
            "Next week yaad dilana please",
            "Lost track of dates yaar",
            "Number change kiya, didn't get reminders",
            "Payment link bhejo please",
            "Mera auto-debit on tha na?",
            "Weekend mein dekhunga",
            "Thanks for letting me know, checking now",
            "My CA handles this, let me ask him",
            "Bill dubara bhejo please",
            "Amount verify karna hai mujhe",
            "Give me 2 days to sort this",
            "Traveling tha, just came back",
            "Sorry bhai, missed earlier calls",
            "How to set up auto-pay?",
            "Let me figure this out",
            "Recently bank change kiya, need to update",
            "Which loan ki baat ho rahi hai?",
            "Statement milega kya?",
            "Wife se puchna padega pehle",
            "Finances check karke bataunga",
            "Honestly forgot, my bad",
            "Email karo details please",
            "Late pay karne pe kitni penalty?",
            "Any grace period available?",
            "Karunga handle, stop calling repeatedly",
            "Work mein busy, will sort soon",
            "Outstanding kahan check karun?",
            "Understood, will do something about it",
            "Exact amount bata do",
            "Realize hi nahi hua it was late",
        ],
    },
    "DISPUTE": {
        "English": [
            "This amount is wrong",
            "I already paid this EMI",
            "Check your records, I don't owe this much",
            "The interest calculation is incorrect",
            "I never took this loan",
            "This is someone else's loan, not mine",
            "I need a detailed statement before I pay anything",
            "The penalty charges are too high",
            "I was promised a different interest rate",
            "My payment was deducted but you're showing pending",
            "I have the payment receipt, shall I share?",
            "There's a discrepancy in the amount",
            "I paid through {payment_method}, check again",
            "Your system shows wrong data",
            "I want to speak to your manager about this",
            "This is a billing error on your end",
            "I dispute this charge",
            "The amount doesn't match what I signed for",
            "I've been overcharged",
            "Send me a complete breakdown of charges",
            "My balance should be zero, I completed all payments",
            "I closed this loan last year",
            "Why are there hidden charges?",
            "This late fee is not valid, I paid on time",
            "I need to verify this with my bank",
            "The loan agreement says different terms",
            "Your agent told me a different amount last time",
            "I want a detailed audit of my account",
            "Something is wrong with your calculation",
            "I don't agree with the outstanding amount",
            "I think there's been a mistake",
            "Who authorized these additional charges?",
            "My co-applicant already paid this",
            "I made a prepayment, it's not reflected",
            "The foreclosure amount is wrong",
            "Why was the interest rate changed?",
            "I want written proof of the amount owed",
            "My payment on {date_num} was not credited",
            "I need an escalation, this amount is disputed",
            "I refuse to pay until you fix the calculation",
            "This doesn't add up",
            "Please share the loan agreement copy",
            "I never agreed to these terms",
            "The processing fee was supposed to be waived",
            "Check the {date_num} transaction",
            "I am raising a formal complaint",
            "My bank shows successful payment",
            "Why is this still showing as unpaid?",
            "I need clarification before paying",
            "Contact my bank, the issue is on your side",
        ],
        "Hindi": [
            "Ye amount galat hai",
            "Maine ye EMI already pay ki hai",
            "Apne records check karo, itna nahi banta",
            "Interest calculation galat hai",
            "Maine ye loan nahi liya",
            "Ye kisi aur ka loan hai, mera nahi",
            "Statement chahiye detailed, tab tak kuch nahi dunga",
            "Penalty charges bahut zyada hain",
            "Mujhe alag interest rate promise kiya tha",
            "Payment kata tha lekin pending dikha raha hai",
            "Receipt hai mere paas, bhejun?",
            "Amount mein discrepancy hai",
            "Maine {payment_method} se pay kiya, check karo",
            "Tumhara system galat data dikha raha hai",
            "Manager se baat karao mujhe",
            "Ye tumhari galti hai billing mein",
            "Main ye charge dispute karta hun",
            "Amount wo nahi hai jo sign kiya tha",
            "Overcharge kiya hai mujhe",
            "Charges ka complete breakdown bhejo",
            "Mera balance zero hona chahiye, sab pay kiya",
            "Ye loan pichle saal band kiya tha",
            "Hidden charges kyun hain?",
            "Late fee valid nahi hai, time pe pay kiya tha",
            "Bank se verify karna padega mujhe",
            "Loan agreement mein alag terms hain",
            "Tumhare agent ne alag amount bataya tha last time",
            "Mera account audit karo",
            "Calculation mein kuch gadbad hai",
            "Outstanding amount se agree nahi hun main",
            "Lagta hai koi mistake hai",
            "Ye additional charges kisne authorize kiye?",
            "Mere co-applicant ne pay kar diya hai",
            "Prepayment kiya tha, reflect nahi ho raha",
            "Foreclosure amount galat hai",
            "Interest rate kyun badla?",
            "Written proof do kitna banta hai",
            "{date_num} ko payment kiya tha, credit nahi hua",
            "Escalation chahiye, amount disputed hai",
            "Jab tak calculation fix nahi karoge tab tak nahi dunga",
            "Ye add up nahi ho raha",
            "Loan agreement copy share karo",
            "Maine in terms pe agree nahi kiya tha",
            "Processing fee waive honi thi",
            "{date_num} ka transaction check karo",
            "Formal complaint kar raha hun",
            "Meri bank successful payment dikha rahi hai",
            "Abhi tak unpaid kyun hai?",
            "Pehle clarification do, phir payment",
            "Meri bank se contact karo, issue tumhara hai",
        ],
        "Bengali": [
            "Ei amount bhul ache",
            "Ami ei EMI already diyechi",
            "Tomar records check koro, eto hoy na",
            "Interest calculation bhul ache",
            "Ami ei loan niini",
            "Eta onyo karo loan, amar na",
            "Detailed statement chai, noyto kichu debo na",
            "Penalty charges onek beshi",
            "Amake onno interest rate promise kora hoyechhilo",
            "Payment kata hoyechhilo kintu pending dekhacche",
            "Receipt ache amar kache, pathabo?",
            "Amount e discrepancy ache",
            "Ami {payment_method} diye pay korechi, abar check koro",
            "Tomar system bhul data dekhacche",
            "Manager er shathe kotha bolte chai",
            "Eta tomar billing er bhul",
            "Ami ei charge dispute korchi",
            "Amount ota na jeta sign kora hoyechhilo",
            "Amake overcharge kora hoyeche",
            "Charges er complete breakdown pathao",
            "Amar balance zero howar kotha, shob pay korechi",
            "Ei loan goto bochor bond kora hoyechhilo",
            "Hidden charges keno?",
            "Late fee valid na, time e pay korechi",
            "Bank theke verify korte hobe amake",
            "Loan agreement e onno terms ache",
            "Tomar agent last time onno amount bolechhilo",
            "Amar account audit koro",
            "Calculation e kichu godbod ache",
            "Outstanding amount e agree na ami",
            "Mone hoy kono mistake hoyeche",
            "Ei additional charges ke authorize koreche?",
            "Amar co-applicant pay kore diyeche",
            "Prepayment korechilem, reflect hochhe na",
            "Foreclosure amount bhul",
            "Interest rate keno bodlano holo?",
            "Written proof dao koto taka baki",
            "{date_num} e payment korechilem, credit hoyni",
            "Escalation chai, amount disputed",
            "Jotokkhon calculation thik na korbe totokkhon debo na",
            "Eta add up hochhe na",
            "Loan agreement copy share koro",
            "Ami ei terms e agree korini",
            "Processing fee waive howar kotha chhilo",
            "{date_num} er transaction check koro",
            "Formal complaint korchi",
            "Amar bank successful payment dekhacche",
            "Ekhono unpaid keno?",
            "Age clarification dao, tarpor payment",
            "Amar bank e contact koro, issue tomar dik e",
        ],
        "Hinglish": [
            "Bhai ye amount galat hai",
            "I already paid this EMI, check karo",
            "Records dekho, itna nahi banta mera",
            "Interest calculation is wrong",
            "Maine ye loan nahi liya hai",
            "This is not my loan yaar",
            "Detailed statement do, tab tak nahi dunga",
            "Penalty charges too much hai",
            "Different interest rate promise kiya tha mujhe",
            "Payment cut hua but showing pending",
            "I have the receipt, want to see?",
            "Amount mein mismatch hai",
            "{payment_method} se paid already, recheck please",
            "Your system data is wrong bhai",
            "I want to speak to manager",
            "This is your billing mistake",
            "I'm disputing this charge",
            "Amount jo sign kiya tha wo nahi hai",
            "You have overcharged me",
            "Complete breakdown of charges bhejo",
            "Balance zero hona chahiye, all paid",
            "Last year this loan was closed",
            "Why hidden charges bhai?",
            "Late fee wrong hai, I paid on time",
            "I need to verify with my bank",
            "Agreement mein different terms the",
            "Your agent said different amount last time",
            "Please audit my account",
            "Calculation mein something wrong hai",
            "I don't agree with outstanding amount",
            "I think koi mistake hai",
            "Who authorized ye extra charges?",
            "Co-applicant already paid this",
            "Did prepayment, not showing in system",
            "Foreclosure amount is incorrect",
            "Why interest rate change hua?",
            "Written proof do amount ka",
            "{date_num} ko payment kiya but not credited",
            "Need escalation, disputing the amount",
            "Fix the calculation first, then I'll pay",
            "Numbers don't add up yaar",
            "Share loan agreement copy please",
            "I never agreed to these terms yaar",
            "Processing fee waive honi thi",
            "Check {date_num} transaction please",
            "Filing formal complaint about this",
            "My bank shows payment successful",
            "Why still showing unpaid?",
            "Clarification do pehle, phir payment",
            "Your side pe issue hai, contact my bank",
        ],
    },
    "HIGH_RISK": {
        "English": [
            "Stop calling me",
            "I don't care about your loan",
            "Do whatever you want, I'm not paying",
            "I'll report you for harassment",
            "This is fraud, I'm going to the police",
            "Leave me alone or I'll take legal action",
            "You people are scammers",
            "I'm blocking this number",
            "Don't call me again or I'll file a complaint",
            "Go ahead and sue me, I don't care",
            "I have nothing to pay with",
            "You can't do anything to me",
            "I know my rights, stop threatening me",
            "I'll go to consumer court against you",
            "Your company is a fraud",
            "I'm recording this call",
            "My lawyer will handle this",
            "I refuse to pay and that's final",
            "Try whatever you want, I'm not scared",
            "This is the last time I'm telling you",
            "Enough of your harassment",
            "I've already complained to RBI about you",
            "Don't ever contact me again",
            "I will expose your company on social media",
            "Your threats don't work on me",
            "I'm not the person you're looking for",
            "I don't owe anything and won't pay",
            "Keep calling, see what happens",
            "File a case if you dare",
            "I'll make sure your company is shut down",
            "I'm done talking to you people",
            "This is extortion",
            "I'll go to the media about this",
            "Your company harasses innocent people",
            "I know people in government, be careful",
            "One more call and I'm reporting you",
            "I'll file an FIR against you",
            "Mind your own business",
            "You'll regret calling me",
            "I have no obligation to pay this",
            "Get lost",
            "This is illegal what you're doing",
            "I'll destroy your reputation",
            "I'm never going to pay, deal with it",
            "You're wasting your time",
            "Don't test my patience",
            "I'll handle this my way",
            "You people have no shame",
            "I'm going to the banking ombudsman",
            "Talk to my lawyer from now on",
        ],
        "Hindi": [
            "Mujhe call karna band karo",
            "Tumhare loan ki koi parwah nahi hai mujhe",
            "Jo karna hai karo, main nahi dunga",
            "Harassment ke liye report karunga tumko",
            "Ye fraud hai, police mein jaaunga",
            "Mujhe akela chodo nahi to legal action lunga",
            "Tum log scammer ho",
            "Number block kar raha hun",
            "Dubara call kiya to complaint karunga",
            "Case karo, mujhe fark nahi padta",
            "Mere paas kuch nahi hai dene ko",
            "Tum mera kuch nahi kar sakte",
            "Mujhe apne rights pata hain, dhamki dena band karo",
            "Consumer court jaaunga tumhare khilaf",
            "Tumhari company fraud hai",
            "Main ye call record kar raha hun",
            "Mera lawyer dekhega ye sab",
            "Nahi dunga aur ye final hai",
            "Jo karna hai karo, mujhe darr nahi",
            "Aakhri baar bol raha hun tumhe",
            "Bahut hua tumhara harassment",
            "RBI mein complaint kar chuka hun",
            "Dubara contact mat karna",
            "Social media pe expose karunga",
            "Tumhari dhamkiyan kaam nahi karti mujh pe",
            "Main wo insaan nahi hun jisko dhundh rahe ho",
            "Kuch bhi nahi dena hai mujhe",
            "Call karte raho, dekh lena kya hota hai",
            "Case karo agar himmat hai",
            "Company band karwa dunga tumhari",
            "Tum logon se baat khatam",
            "Ye vasuli hai",
            "Media mein jaaunga",
            "Tumhari company seedhe logon ko pareshan karti hai",
            "Government mein jaanta hun logon ko, sambhal ke",
            "Ek aur call aaya to report karunga",
            "FIR karunga tumhare naam pe",
            "Apna kaam karo",
            "Pachtaoge mujhe call karke",
            "Koi obligation nahi hai mera ye dene ka",
            "Door ho jao",
            "Jo kar rahe ho illegal hai",
            "Reputation barbaad kar dunga tumhari",
            "Kabhi nahi dunga, deal with it",
            "Apna time waste kar rahe ho",
            "Mera patience mat check karo",
            "Apne tarike se handle karunga",
            "Tum logon ko sharam nahi aati",
            "Banking ombudsman ke paas jaaunga",
            "Aage se mere lawyer se baat karo",
        ],
        "Bengali": [
            "Amake call kora bondho koro",
            "Tomar loan niye ami care kori na",
            "Ja khoushi koro, ami debo na",
            "Harassment er jonno report korbo tomake",
            "Eta fraud, police e jabo",
            "Amake chhere dao nahole legal action nebo",
            "Tora shob scammer",
            "Number block korchi",
            "Abar call korle complaint korbo",
            "Case koro, amar kichu jai ashe na",
            "Amar kache kichu nei debar",
            "Tumi amar kichu korte parbe na",
            "Amar rights jana ache, dhamki dewa bondho koro",
            "Consumer court e jabo tomar biruddhe",
            "Tomar company fraud",
            "Ami ei call record korchi",
            "Amar lawyer dekhbe",
            "Debo na ar eta final",
            "Ja korte chao koro, dar nei amar",
            "Shesh bar bolchi tomake",
            "Onek hoyeche tomar harassment",
            "RBI te complaint kore diyechi",
            "Abar contact koro na",
            "Social media te expose korbo",
            "Tomar dhamki kaje ashe na amar upor",
            "Ami shei lok na jake khujcho",
            "Kichu debar nei amar",
            "Call korte thako, dekhe neo ki hoy",
            "Case koro jodi shahos thake",
            "Company bondho koriye debo tomar",
            "Toder shathe kotha shesh",
            "Eta josuli",
            "Media te jabo",
            "Tomar company bhalo lokeder harrass kore",
            "Government e chinchi lokjon, shambhale",
            "Aro ekta call ashle report korbo",
            "FIR korbo tomar name",
            "Nijer kaj koro",
            "Pashtabe amake call kore",
            "Kono obligation nei amar eta debar",
            "Dure jao",
            "Ja korcho illegal",
            "Reputation noshto kore debo tomar",
            "Kokhono debo na, deal with it",
            "Nijer time noshto korcho",
            "Amar patience test koro na",
            "Nijer moto handle korbo",
            "Toder lojja nei",
            "Banking ombudsman er kache jabo",
            "Ekhon theke amar lawyer er shathe kotha bolo",
        ],
        "Hinglish": [
            "Stop calling me bhai",
            "I don't care tumhare loan ke baare mein",
            "Do whatever, not paying",
            "I'll report you for harassment bro",
            "This is fraud hai ye, going to police",
            "Leave me alone ya legal action lunga",
            "You guys are scammers",
            "Blocking this number right now",
            "One more call and complaint file karunga",
            "Sue me if you want, I don't care",
            "I have nothing to give",
            "You can't touch me bhai",
            "I know my rights, stop this",
            "Consumer court jaaunga against you",
            "Your company is totally fraud",
            "Recording this call FYI",
            "My lawyer will deal with this",
            "Final answer: no payment",
            "Do your worst, I'm not scared",
            "Last time bol raha hun",
            "Your harassment is enough",
            "Already complained to RBI about you guys",
            "Never contact me again",
            "Social media pe viral karunga",
            "Your threats are useless on me",
            "Wrong person ko call kar rahe ho",
            "I don't owe anything, stop this",
            "Keep calling, achha nahi hoga",
            "Case karo if you dare",
            "Main tumhari company band karwa dunga",
            "Done talking to you people",
            "This is pure extortion hai ye",
            "Media mein jaunga with proof",
            "You harass innocent log",
            "Government mein contacts hain mere, careful",
            "One more call = FIR",
            "FIR file karunga tum pe",
            "Mind your business bro",
            "You will regret this",
            "No obligation hai mera",
            "Get lost yaar",
            "What you're doing is illegal bhai",
            "I'll ruin your company reputation",
            "Never ever paying, that's it",
            "Time waste mat karo apna",
            "Don't test me",
            "I'll handle it my way",
            "Tum logon ko sharam nahi",
            "Banking ombudsman se baat karunga",
            "Talk to my lawyer aage se",
        ],
    },
    "VAGUE": {
        "English": [
            "Ok",
            "Hmm",
            "Let me see",
            "I don't know",
            "Maybe",
            "We'll see",
            "I'm thinking about it",
            "Can't say right now",
            "Not sure",
            "Let me think",
            "I'll try",
            "Possibly",
            "Depends",
            "I need time",
            "Will think about it",
            "Can't promise anything",
            "I'm not sure what to do",
            "Could be",
            "Something like that",
            "Yeah maybe",
            "I'll look into it",
            "Hard to say",
            "Who knows",
            "Might be able to",
            "No comment",
            "I have to think",
            "Let's see what happens",
            "Can't commit right now",
            "Will get back to you",
            "Need to figure things out",
            "It's complicated",
            "I don't have an answer right now",
            "Maybe later",
            "We'll figure it out",
            "Uncertain",
            "I'm working on it",
            "Give me some time to decide",
            "I have other priorities",
            "Not right now",
            "I'll consider it",
            "Things are difficult",
            "Can't really say",
            "It's not that simple",
            "I don't know what to say",
            "Let me check my situation",
            "Life is tough right now",
            "I'm trying my best",
            "Situation is complicated",
            "I have issues",
            "Whatever",
        ],
        "Hindi": [
            "Theek hai",
            "Hmm",
            "Dekh leta hun",
            "Pata nahi",
            "Shayad",
            "Dekhte hain",
            "Soch raha hun",
            "Abhi nahi bata sakta",
            "Sure nahi hun",
            "Sochne do",
            "Koshish karunga",
            "Ho sakta hai",
            "Depend karta hai",
            "Time chahiye mujhe",
            "Sochunga",
            "Promise nahi kar sakta",
            "Samajh nahi aa raha kya karun",
            "Shayad ho jaye",
            "Kuch aisa hi",
            "Haan shayad",
            "Dekhunga main",
            "Batana mushkil hai",
            "Kaun jaane",
            "Kar paunga shayad",
            "Koi comment nahi",
            "Sochna padega",
            "Dekhte hain kya hota hai",
            "Abhi commit nahi kar sakta",
            "Baad mein bataunga",
            "Samajhna padega",
            "Complicated hai",
            "Abhi jawab nahi de sakta",
            "Baad mein shayad",
            "Dekhte hain kuch hota hai",
            "Aur options sochne do",
            "Kuch kar raha hun",
            "Decide karne mein time do",
            "Aur priorities hain",
            "Abhi nahi",
            "Sochunga iske baare mein",
            "Mushkil hai situation",
            "Nahi bata sakta sach mein",
            "Itna simple nahi hai",
            "Kya bolun samajh nahi aa raha",
            "Situation dekhni padegi",
            "Zindagi mushkil chal rahi hai",
            "Koshish kar raha hun apni taraf se",
            "Haalat kharab hain",
            "Issues hain",
            "Jo bhi",
        ],
        "Bengali": [
            "Thik ache",
            "Hmm",
            "Dekhi",
            "Jani na",
            "Hoyto",
            "Dekha jabe",
            "Bhebhe dekhchi",
            "Ekhon bolte parbo na",
            "Sure na",
            "Bhabte dao",
            "Cheshta korbo",
            "Hote pare",
            "Depend kore",
            "Time chai amake",
            "Bhebhe dekhbo",
            "Promise korte parbo na",
            "Ki korbo bujhte parchi na",
            "Hoyto hoye jabe",
            "Kichu ekta",
            "Haan hoyto",
            "Dekhe nii",
            "Bola mushkil",
            "Ke jane",
            "Korte parbo hoyto",
            "No comment",
            "Bhabte hobe",
            "Dekha jak ki hoy",
            "Ekhon commit korte parbo na",
            "Pore janabo",
            "Bujhte hobe",
            "Complicated byapar",
            "Ekhon uttor dite parbo na",
            "Pore hoyto",
            "Dekha jak kichu hoy ki na",
            "Onno option bhabte dao",
            "Kichu ekta korchi",
            "Decide korte time dao",
            "Onno priorities ache",
            "Ekhon na",
            "Bhabbo ei niye",
            "Mushkil obostha",
            "Bolte parbo na shotti",
            "Eto simple na",
            "Ki bolbo bujhte parchi na",
            "Situation dekhte hobe",
            "Jibon mushkil cholche",
            "Cheshta korchi nijer dik theke",
            "Obostha kharap",
            "Issues ache",
            "Ja bhi",
        ],
        "Hinglish": [
            "Theek hai ok",
            "Hmm ok",
            "Let me dekh leta hun",
            "I don't know yaar",
            "Maybe ho jayega",
            "Dekhte hain bhai",
            "I'm thinking about it abhi",
            "Abhi can't say",
            "Not sure honestly",
            "Sochne do mujhe",
            "Try karunga",
            "Possibly ho sakta hai",
            "It depends yaar",
            "Time chahiye merko",
            "Will think about it definitely",
            "Can't promise kuch bhi",
            "Samajh nahi aa raha what to do",
            "Maybe shayad",
            "Something like that hi hai",
            "Yeah probably",
            "I'll look into it dekhta hun",
            "Hard to say honestly",
            "Who knows yaar",
            "Might kar paunga",
            "No comment bhai",
            "Sochna padega mujhe",
            "Let's see kya hota hai",
            "Can't commit abhi",
            "Will get back to you later",
            "Need to figure out karunga",
            "It's complicated hai",
            "Abhi answer nahi hai mere paas",
            "Maybe later sometime",
            "Figure out ho jayega",
            "Uncertain hun main",
            "Working on it hun",
            "Time do decide karne ke liye",
            "Other priorities hain abhi",
            "Not right now bhai",
            "I'll consider it sochunga",
            "Things are difficult bahut",
            "Really can't say bro",
            "It's not that simple yaar",
            "Kya bolun pata nahi",
            "Situation check karna padega",
            "Life tough hai abhi",
            "I'm trying apni taraf se",
            "Situation complicated hai",
            "Issues hain mere",
            "Whatever jo bhi",
        ],
    },
    "ALREADY_PAID": {
        "English": [
            "I already paid this last week",
            "Check your records, payment was done",
            "I paid on {date_num}, please verify",
            "Payment was already transferred via {payment_method}",
            "I made the payment {timeframe}",
            "The amount has already been paid",
            "I cleared this EMI already",
            "Check your system, I paid via {payment_method}",
            "My bank shows the debit, payment is done",
            "I already transferred the money",
            "Please check, payment was successful",
            "I paid the full amount on {date_num}",
            "The transaction was completed, check your end",
            "I have the UTR number, want to see?",
            "Payment receipt is with me, shall I share?",
            "I did the NEFT {timeframe}, it should reflect",
            "Already cleared, don't call again for this",
            "This was paid ages ago, check properly",
            "My payment went through on {date_num}",
            "I paid via auto-debit, check the bank",
            "Transaction successful on my end",
            "The money left my account already",
            "I got the confirmation message after paying",
            "Paid in full, you should have received it",
            "I completed the payment before the due date",
            "Already done, please update your records",
            "I transferred via {payment_method} on {date_num}",
            "Your system is not updated, I paid already",
            "I paid twice actually, check for overpayment",
            "The cheque was deposited last week",
            "I have proof of payment, want me to send?",
            "Auto-debit happened on {date_num}, verify please",
            "Paid through the app, transaction ID available",
            "I settled this account already",
            "Why are you calling? I already paid",
            "This is resolved, payment was made",
            "I paid this off months ago",
            "The EMI was deducted from my account",
            "Check the {date_num} credit, that's my payment",
            "Online payment done, waiting for your confirmation",
            "I sent the money through {payment_method}",
            "Bank statement shows the payment clearly",
            "Already paid everything, nothing pending",
            "Payment proof is in my email, can forward",
            "Transaction reference number: check your system",
            "I made partial payment on {date_num} and rest on {date_num}",
            "This EMI was covered under auto-debit",
            "Paid and done, update your records please",
            "I recall paying this, let me check my statement",
            "Definitely paid, here's my transaction screenshot",
        ],
        "Hindi": [
            "Maine pehle hi kar diya",
            "Payment ho chuka hai",
            "Maine {date_num} ko pay kiya tha",
            "{payment_method} se transfer kar diya tha",
            "Paise bhej diye the, check karo",
            "Mera payment already ho gaya hai",
            "EMI already kat gayi hai",
            "System mein check karo, payment hua hai",
            "Bank mein debit dikha raha hai",
            "Maine paisa already transfer kar diya",
            "Check karo please, payment successful tha",
            "Full amount diya tha {date_num} ko",
            "Transaction complete ho gaya tha",
            "UTR number hai mere paas",
            "Receipt hai, bhejun kya?",
            "NEFT kiya tha {timeframe_hi}, reflect hona chahiye",
            "Clear kar diya tha, dubara mat call karo",
            "Bahut pehle pay kar diya tha",
            "Mera payment {date_num} ko gaya tha",
            "Auto-debit se kat gaya hai",
            "Meri taraf se transaction successful hai",
            "Paisa nikal gaya account se",
            "Confirmation message aaya tha pay karne ke baad",
            "Poora pay kiya hai, tumhe mil gaya hoga",
            "Due date se pehle hi kar diya tha",
            "Ho gaya hai, records update karo",
            "{payment_method} se {date_num} ko transfer kiya tha",
            "System update nahi hua, pay kar diya hai",
            "Do baar pay kiya hai actually",
            "Cheque deposit kiya tha pichle hafte",
            "Proof hai payment ka, bhejun?",
            "Auto-debit {date_num} ko hua tha",
            "App se pay kiya, transaction ID hai",
            "Account settle kar diya hai",
            "Kyun call kar rahe ho? Already pay kiya",
            "Ye solve ho gaya hai, payment hua",
            "Months pehle pay kar diya tha",
            "EMI account se kat gayi",
            "{date_num} ko credit check karo",
            "Online payment kar diya, confirmation ka wait hai",
            "{payment_method} se bhej diya paisa",
            "Bank statement mein clear hai payment",
            "Sab pay kar diya, kuch pending nahi",
            "Payment proof email mein hai",
            "Transaction reference number check karo",
            "Partial {date_num} ko kiya tha aur baaki {date_num} ko",
            "Auto-debit se cover ho gayi thi EMI",
            "Pay karke khatam kiya, update karo",
            "Yaad hai pay kiya tha, statement dekhta hun",
            "Pakka pay kiya hai, screenshot hai",
        ],
        "Bengali": [
            "Ami age-i diye diyechi",
            "Payment hoye geche",
            "Ami {date_num} e pay korechi",
            "{payment_method} diye transfer kore diyechi",
            "Taka pathiye diyechi, check koro",
            "Amar payment already hoye geche",
            "EMI already kete geche",
            "System e check koro, payment hoyeche",
            "Bank e debit dekhacche",
            "Ami taka already transfer kore diyechi",
            "Check koro please, payment successful chhilo",
            "Full amount diyechilam {date_num} e",
            "Transaction complete hoye gechilo",
            "UTR number ache amar kache",
            "Receipt ache, pathabo?",
            "NEFT korechilem {timeframe_bn}, reflect howar kotha",
            "Clear kore diyechi, abar call koro na",
            "Onek age pay kore diyechilem",
            "Amar payment {date_num} e gechilo",
            "Auto-debit theke kete geche",
            "Amar dik theke transaction successful",
            "Taka ber hoye geche account theke",
            "Confirmation message esechilo pay korar por",
            "Pura pay korechi, tomar kache pouche jawar kotha",
            "Due date er age-i kore diyechilem",
            "Hoye geche, records update koro",
            "{payment_method} diye {date_num} e transfer korechilem",
            "System update hoyni, pay kore diyechi",
            "Dui bar pay korechi actually",
            "Cheque deposit korechilem goto shoptahe",
            "Proof ache payment er, pathabo?",
            "Auto-debit {date_num} e hoyechhilo",
            "App diye pay korechi, transaction ID ache",
            "Account settle kore diyechi",
            "Keno call korcho? Already pay korechi",
            "Eta solve hoye geche, payment hoyeche",
            "Months age pay kore diyechilem",
            "EMI account theke kete geche",
            "{date_num} er credit check koro",
            "Online payment kore diyechi, confirmation er wait",
            "{payment_method} diye pathiye diyechi taka",
            "Bank statement e clear ache payment",
            "Shob pay kore diyechi, kichu pending nei",
            "Payment proof email e ache",
            "Transaction reference number check koro",
            "Partial {date_num} e korechilem ar baki {date_num} e",
            "Auto-debit diye cover hoye gechilo EMI",
            "Pay kore shesh, update koro",
            "Mone ache pay korechilem, statement dekhchi",
            "Pakka pay korechi, screenshot ache",
        ],
        "Hinglish": [
            "Bhai already transfer kar diya tha, check karo",
            "I already paid yaar, records dekho",
            "Payment ho gaya hai, {date_num} ko kiya tha",
            "{payment_method} se pay kiya already",
            "Bhai paisa bhej diya, tumhare system mein nahi aya?",
            "Already paid hai ye, don't call again",
            "EMI already clear hai bro",
            "System check karo, mera payment ho gaya",
            "Bank mein debit hai, payment done",
            "I transferred already yaar",
            "Check please, my payment was successful",
            "Full amount on {date_num} pay kiya tha",
            "Transaction complete ho gaya, your side pe check karo",
            "UTR number hai, share karun?",
            "Receipt hai mere paas, want to see?",
            "NEFT kar diya tha {timeframe_hi}, should reflect now",
            "Bhai clear kar diya, stop calling",
            "Ages ago paid this, check properly",
            "Mera payment {date_num} ko go through hua",
            "Auto-debit se ho gaya hai bhai",
            "My side se transaction successful",
            "Money already left my account",
            "Got confirmation after paying bhai",
            "Paid in full, you should have it",
            "Before due date hi pay kar diya tha",
            "Done hai, please update records",
            "Transfer kiya tha {payment_method} se on {date_num}",
            "Your system not updated, I paid already bro",
            "I paid twice actually, check overpayment",
            "Cheque deposit kiya last week",
            "Proof hai payment ka, bhej dun?",
            "Auto-debit hua tha {date_num} ko",
            "App se paid, transaction ID available hai",
            "Account settle ho gaya hai bhai",
            "Why calling? Already paid hai",
            "This is sorted, payment done",
            "Months pehle pay kiya tha yaar",
            "EMI cut ho gayi account se",
            "Check {date_num} credit, woh mera payment hai",
            "Online payment done, awaiting confirmation",
            "{payment_method} se paisa bheja hai",
            "Bank statement clearly shows payment",
            "Everything paid, nothing pending bro",
            "Payment proof email mein hai, forward karun?",
            "Transaction reference number hai, check system",
            "Partial on {date_num} kiya tha and rest on {date_num}",
            "EMI covered under auto-debit",
            "Paid and done bhai, update karo",
            "I remember paying, let me check statement",
            "Definitely paid hai, screenshot dikhata hun",
        ],
    },
}

# Substitution values for template variations
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAYS_HI = ["Somvaar", "Mangalvaar", "Budhvaar", "Guruvaar", "Shukravaar", "Shanivaar", "Ravivaar"]
DAYS_BN = ["Shombar", "Mongolbar", "Budhbar", "Brihoshpotibar", "Shukrobar", "Shonibar", "Robibar"]
TIMEFRAMES = ["tomorrow", "next week", "this weekend", "by end of month", "in 2 days", "in 3 days", "within a week", "by Friday"]
TIMEFRAMES_HI = ["kal", "agle hafte", "is weekend", "month end tak", "2 din mein", "3 din mein", "ek hafte mein", "Shukravaar tak"]
TIMEFRAMES_BN = ["kaal", "agle shoptahe", "ei weekend", "mash sheshe", "dui din e", "tin din e", "ek shoptahe", "Shukrobar er moddhe"]
DATE_NUMS = ["5th", "10th", "15th", "20th", "25th", "1st", "last month"]
PAYMENT_METHODS = ["UPI", "NEFT", "RTGS", "Google Pay", "PhonePe", "bank transfer", "Paytm", "cheque"]
DAYS_NUMS = ["2", "3", "4", "5", "7", "10", "15"]


def fill_template(template: str) -> str:
    """Fill a template string with random substitution values."""
    result = template
    result = result.replace("{day}", random.choice(DAYS))
    result = result.replace("{day_hi}", random.choice(DAYS_HI))
    result = result.replace("{day_bn}", random.choice(DAYS_BN))
    result = result.replace("{timeframe}", random.choice(TIMEFRAMES))
    result = result.replace("{timeframe_hi}", random.choice(TIMEFRAMES_HI))
    result = result.replace("{timeframe_bn}", random.choice(TIMEFRAMES_BN))
    result = result.replace("{date_num}", random.choice(DATE_NUMS))
    result = result.replace("{payment_method}", random.choice(PAYMENT_METHODS))
    result = result.replace("{days}", random.choice(DAYS_NUMS))
    return result


# Additional filler phrases for realistic WhatsApp variation
FILLER_PREFIXES = [
    "Actually ", "See ", "Look ", "Listen ", "Ok so ", "Haan ", "Arey ",
    "Bhai ", "Yaar ", "Sir ", "Madam ", "Boss ", "Dude ", "Hey ",
    "Dekho ", "Suno ", "Acha ", "Well ", "Basically ", "Honestly ",
    "", "", "", "", "",  # empty for no prefix (weighted toward no prefix)
]

FILLER_SUFFIXES = [
    " ok?", " na?", " bro", " sir", " yaar", " boss",
    " thx", " thanks", " plz", " asap",
    " 🙏", " 😢", " 😡", " 🤷", " 👍", " 😭", " 💰", " 🙏🙏",
    " !!", " ...", ".", " 🙂",
    "", "", "", "", "", "",  # empty for no suffix
]

TYPO_MAP = {
    "payment": ["payement", "paymnt", "paymt"],
    "transfer": ["transffr", "trnsfr", "transfr"],
    "tomorrow": ["tmrw", "tmrrow", "2morrow", "2mrw"],
    "please": ["plz", "pls", "plss"],
    "amount": ["amnt", "amt"],
    "salary": ["sal", "salry"],
}


def augment_message(message: str) -> str:
    """Apply random augmentations to increase diversity."""
    # Apply 1-3 augmentations from a rich set
    aug_options = []

    # Casing variations
    r = random.random()
    if r < 0.1:
        message = message.upper()
    elif r < 0.25:
        message = message.lower()
    elif r < 0.35:
        # Random capitalization
        message = ''.join(c.upper() if random.random() > 0.7 else c.lower() for c in message)

    # Prefix
    if random.random() < 0.3:
        prefix = random.choice(FILLER_PREFIXES)
        if prefix and not message.startswith(prefix.strip()):
            message = prefix + message[0].lower() + message[1:] if prefix else message

    # Suffix
    if random.random() < 0.35:
        suffix = random.choice(FILLER_SUFFIXES)
        if suffix:
            message = message.rstrip(".!?, ") + suffix

    # Punctuation variation
    r = random.random()
    if r < 0.15:
        message = message.rstrip(".!?")  # strip trailing punctuation
    elif r < 0.25:
        message = message + "!!"  # add emphasis
    elif r < 0.30:
        message = message + "???"  # question emphasis

    # WhatsApp-style abbreviations (apply typos rarely)
    if random.random() < 0.15:
        for word, typos in TYPO_MAP.items():
            if word in message.lower():
                message = message.replace(word, random.choice(typos), 1)
                break

    # Repetition for emphasis
    if random.random() < 0.1:
        words = message.split()
        if len(words) >= 3:
            idx = random.randint(0, min(2, len(words) - 1))
            words[idx] = words[idx] + " " + words[idx]
            message = " ".join(words)

    return message.strip()


def generate_from_templates(label: str, language: str, count: int) -> list[str]:
    """Generate 'count' messages from templates for a given label and language."""
    templates = TEMPLATES.get(label, {}).get(language, [])
    if not templates:
        logger.warning(f"No templates for label={label}, language={language}")
        return []

    messages = []
    # First pass: use each template at least once with fill
    for template in templates:
        msg = fill_template(template)
        messages.append(msg)

    # Second pass: generate more with augmentations until we reach count
    attempts = 0
    max_attempts = count * 10
    while len(messages) < count and attempts < max_attempts:
        template = random.choice(templates)
        msg = fill_template(template)
        msg = augment_message(msg)
        if msg and msg not in messages:
            messages.append(msg)
        attempts += 1

    return messages[:count]


# ============================================================
# Ollama-based generator (try first)
# ============================================================

def try_ollama_generate(label: str, language: str, count: int) -> list[str] | None:
    """Try generating messages using local Ollama. Returns None if unavailable."""
    try:
        import requests
        # Check if Ollama is running
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code != 200:
            return None

        tags = resp.json().get("models", [])
        model_names = [m.get("name", "") for m in tags]

        # Prefer smaller models
        preferred = ["qwen2.5:7b", "phi3:mini", "llama3.2:3b", "llama3:8b", "mistral:7b"]
        selected = None
        for pref in preferred:
            for mn in model_names:
                if pref in mn:
                    selected = mn
                    break
            if selected:
                break

        if not selected and model_names:
            selected = model_names[0]

        if not selected:
            return None

        logger.info(f"Using Ollama model: {selected}")

        prompt = f"""Generate {count} short, realistic messages a loan defaulter might send via 
WhatsApp in response to an overdue EMI reminder.
Language: {language}
Category: {CLASS_DESCRIPTIONS[label]}
Rules:
- Each message on its own line
- Vary length (3 words to 2 sentences)
- Be realistic, not textbook
- For Hinglish: mix Hindi words naturally into English sentences
- For Bengali: use romanized Bengali (not Unicode script) — e.g. "ami debo", "ekhon nei"
- No numbering, no quotes"""

        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": selected, "prompt": prompt, "stream": False},
            timeout=120,
        )

        if resp.status_code == 200:
            text = resp.json().get("response", "")
            lines = [
                line.strip().lstrip("0123456789.-) ").strip('"\'')
                for line in text.strip().split("\n")
                if line.strip() and len(line.strip()) >= 3
            ]
            if len(lines) >= count // 2:
                logger.info(f"Ollama generated {len(lines)} messages for {label}/{language}")
                return lines

        return None
    except Exception:
        return None


# ============================================================
# Deduplication & Quality Filtering
# ============================================================

def exact_dedup(rows: list[dict]) -> tuple[list[dict], int]:
    """Remove exact duplicate texts. Returns (deduped_rows, num_removed)."""
    seen = set()
    deduped = []
    removed = 0
    for row in rows:
        text_hash = hashlib.md5(row["text"].strip().lower().encode()).hexdigest()
        if text_hash not in seen:
            seen.add(text_hash)
            deduped.append(row)
        else:
            removed += 1
    return deduped, removed


def near_dedup(rows: list[dict], threshold: float = NEAR_DUPLICATE_THRESHOLD) -> tuple[list[dict], int]:
    """Remove near-duplicates using SequenceMatcher. O(n^2) but acceptable for ~5k rows."""
    if not rows:
        return rows, 0

    kept = []
    removed = 0
    kept_texts = []

    for row in rows:
        text = row["text"].strip().lower()
        is_dup = False
        for kt in kept_texts:
            if SequenceMatcher(None, text, kt).ratio() >= threshold:
                is_dup = True
                removed += 1
                break
        if not is_dup:
            kept.append(row)
            kept_texts.append(text)

    return kept, removed


def length_filter(rows: list[dict], min_len: int = MIN_LENGTH, max_len: int = MAX_LENGTH) -> tuple[list[dict], int]:
    """Remove messages under min_len or over max_len characters."""
    filtered = []
    removed = 0
    for row in rows:
        text_len = len(row["text"].strip())
        if min_len <= text_len <= max_len:
            filtered.append(row)
        else:
            removed += 1
    return filtered, removed


def validate_language(rows: list[dict]) -> tuple[list[dict], int, list[dict]]:
    """
    Validate language labels using langdetect.
    Returns (valid_rows, flagged_count, flagged_rows).
    Note: langdetect is unreliable for Hinglish/romanized Bengali, so we only flag
    and keep all rows (don't remove flagged ones).
    """
    flagged = []
    try:
        from langdetect import detect, LangDetectException
    except ImportError:
        logger.warning("langdetect not installed — skipping language validation")
        return rows, 0, []

    lang_map = {
        "English": ["en"],
        "Hindi": ["hi", "ur"],  # Hindi often detected as Urdu
        "Bengali": ["bn", "en"],  # Romanized Bengali often detected as English
        "Hinglish": ["en", "hi", "ur"],  # Code-mixed
    }

    for row in rows:
        try:
            detected = detect(row["text"])
            expected_langs = lang_map.get(row["language"], [])
            if detected not in expected_langs:
                flagged.append({**row, "detected_language": detected})
        except LangDetectException:
            pass  # Short texts often fail detection

    return rows, len(flagged), flagged


# ============================================================
# Train/Val/Test Split
# ============================================================

def stratified_split(
    rows: list[dict],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Stratified split by (label, language)."""
    from collections import defaultdict

    groups = defaultdict(list)
    for row in rows:
        key = (row["label"], row["language"])
        groups[key].append(row)

    train, val, test = [], [], []
    for key, group_rows in groups.items():
        random.shuffle(group_rows)
        n = len(group_rows)
        n_train = max(1, int(n * train_ratio))
        n_val = max(1, int(n * val_ratio))
        # rest goes to test
        train.extend(group_rows[:n_train])
        val.extend(group_rows[n_train:n_train + n_val])
        test.extend(group_rows[n_train + n_val:])

    # Shuffle each split
    random.shuffle(train)
    random.shuffle(val)
    random.shuffle(test)

    return train, val, test


# ============================================================
# Main Generation Pipeline
# ============================================================

def main():
    random.seed(RANDOM_SEED)
    data_dir = Path(__file__).parent
    data_dir.mkdir(exist_ok=True)

    logger.info("=" * 60)
    logger.info("RecoveryBench Dataset Generator")
    logger.info("=" * 60)

    # Step 1: Generate raw data
    all_rows = []
    generation_backend = "template-based"  # default
    ollama_available = False

    # Check if Ollama is available for any supplemental generation
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code == 200:
            ollama_available = True
            generation_backend = "template-based + Ollama supplement"
            logger.info("Ollama detected — will use for supplemental generation")
    except Exception:
        pass

    total_target = TARGET_PER_CLASS_PER_LANGUAGE * len(CLASSES) * len(LANGUAGES)
    logger.info(f"Target: {TARGET_PER_CLASS_PER_LANGUAGE} examples × {len(CLASSES)} classes × {len(LANGUAGES)} languages = {total_target} rows")

    for label in CLASSES:
        for language in LANGUAGES:
            logger.info(f"Generating: {label} / {language}")

            messages = []

            # Try Ollama first for supplemental diversity
            if ollama_available:
                ollama_msgs = try_ollama_generate(label, language, count=60)
                if ollama_msgs:
                    messages.extend(ollama_msgs)
                    logger.info(f"  Ollama contributed {len(ollama_msgs)} messages")

            # Fill remaining with templates
            remaining = TARGET_PER_CLASS_PER_LANGUAGE - len(messages)
            if remaining > 0:
                template_msgs = generate_from_templates(label, language, remaining)
                messages.extend(template_msgs)
                logger.info(f"  Templates contributed {len(template_msgs)} messages")

            for msg in messages:
                all_rows.append({
                    "text": msg.strip(),
                    "label": label,
                    "language": language,
                })

    logger.info(f"\nTotal raw generated: {len(all_rows)}")

    # Step 2: Deduplication
    logger.info("\n--- Deduplication & Quality Filtering ---")

    rows, exact_removed = exact_dedup(all_rows)
    logger.info(f"Exact duplicates removed: {exact_removed}")

    rows, near_removed = near_dedup(rows, NEAR_DUPLICATE_THRESHOLD)
    logger.info(f"Near-duplicates removed (threshold={NEAR_DUPLICATE_THRESHOLD}): {near_removed}")

    rows, length_removed = length_filter(rows)
    logger.info(f"Length-filtered (min={MIN_LENGTH}, max={MAX_LENGTH}): {length_removed} removed")

    rows, flagged_count, flagged_rows = validate_language(rows)
    logger.info(f"Language validation: {flagged_count} rows flagged (kept but flagged)")

    logger.info(f"After cleaning: {len(rows)} rows")

    # Step 3: Split
    logger.info("\n--- Stratified Split ---")
    train, val, test = stratified_split(rows)

    # Add split column
    for row in train:
        row["split"] = "train"
    for row in val:
        row["split"] = "val"
    for row in test:
        row["split"] = "test"

    logger.info(f"Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")

    # Step 4: Save CSVs
    columns = ["text", "label", "language", "split"]

    for split_name, split_data in [("train", train), ("val", val), ("test", test)]:
        filepath = data_dir / f"{split_name}.csv"
        # Retry with fallback: delete-then-write if permission denied
        for attempt in range(3):
            try:
                if filepath.exists():
                    filepath.unlink()  # Force delete before write
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=columns)
                    writer.writeheader()
                    for row in split_data:
                        writer.writerow({k: row[k] for k in columns})
                logger.info(f"Saved: {filepath} ({len(split_data)} rows)")
                break
            except PermissionError:
                import time
                logger.warning(f"PermissionError on {filepath}, retrying in 2s (attempt {attempt+1}/3)...")
                time.sleep(2)
        else:
            # Last resort: save with alternate name
            alt_path = data_dir / f"{split_name}_new.csv"
            with open(alt_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                for row in split_data:
                    writer.writerow({k: row[k] for k in columns})
            logger.warning(f"Saved to alternate path: {alt_path} ({len(split_data)} rows)")

    # Save metadata for downstream use
    metadata = {
        "total_rows": len(rows),
        "train_rows": len(train),
        "val_rows": len(val),
        "test_rows": len(test),
        "classes": CLASSES,
        "languages": LANGUAGES,
        "generation_backend": generation_backend,
        "exact_duplicates_removed": exact_removed,
        "near_duplicates_removed": near_removed,
        "near_duplicate_threshold": NEAR_DUPLICATE_THRESHOLD,
        "length_filtered_removed": length_removed,
        "language_flagged": flagged_count,
        "timestamp": datetime.now().isoformat(),
    }

    import json
    with open(data_dir / "generation_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Metadata saved: {data_dir / 'generation_metadata.json'}")

    # Save flagged rows if any
    if flagged_rows:
        with open(data_dir / "flagged_language_mismatches.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "label", "language", "detected_language"])
            writer.writeheader()
            for row in flagged_rows:
                writer.writerow({k: row[k] for k in ["text", "label", "language", "detected_language"]})
        logger.info(f"Flagged rows saved: {data_dir / 'flagged_language_mismatches.csv'}")

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("GENERATION COMPLETE")
    logger.info("=" * 60)

    # Class distribution
    class_counts = defaultdict(int)
    lang_counts = defaultdict(int)
    for row in rows:
        class_counts[row["label"]] += 1
        lang_counts[row["language"]] += 1

    logger.info("\nClass Distribution:")
    for cls in CLASSES:
        logger.info(f"  {cls}: {class_counts[cls]} ({100*class_counts[cls]/len(rows):.1f}%)")

    logger.info("\nLanguage Distribution:")
    for lang in LANGUAGES:
        logger.info(f"  {lang}: {lang_counts[lang]} ({100*lang_counts[lang]/len(rows):.1f}%)")


if __name__ == "__main__":
    main()
