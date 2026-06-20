# Checkpoint 1 — Dataset Review
**Status:** PASS WITH WARNINGS
**Completion:** 100%
**Date:** 2026-06-09

## Risks
- WARNING: Near-duplicate removal removed 45.5% of generated data (threshold >20%)

## Concerns
- Template-based generation means some structural patterns repeat across examples
- Romanized Bengali may not fully represent natural Bengali writing patterns
- Hinglish code-mixing patterns are template-driven, not corpus-extracted

## Recommendations
- Review the 50 edge cases below for misclassified or ambiguous examples
- Consider whether VAGUE vs NEEDS_REMINDER class boundary is too blurry for production use
- The near-duplicate removal rate of 45.5% suggests template diversity could be improved

## Next Action
**WAITING FOR HUMAN APPROVAL**

---

## 1. Dataset Statistics

| Metric | Value |
|--------|-------|
| Total rows | 3268 |
| Train rows | 2279 |
| Val rows | 480 |
| Test rows | 509 |
| Mean message length | 31.6 chars |
| Median message length | 31.0 chars |
| Min message length | 3 chars |
| Max message length | 69 chars |

## 2. Duplicate Removal Log

| Step | Count | Details |
|------|-------|---------|
| Raw generated | 6000 | 300 per class × language |
| Exact duplicates removed | 917 | MD5 hash on lowercased text |
| Near-duplicates removed | 1814 | difflib.SequenceMatcher, threshold=0.92 |
| Length-filtered | 1 | Min 3, max 300 chars |
| Language flagged (kept) | 1933 | langdetect disagreements |
| **Final count** | **3268** | |
| **Removal rate** | **45.5%** | |

## 3. Generation Methodology

- **Backend used:** template-based
- **Templates:** 50 unique templates per class × language (1,000 total templates)
- **Augmentations:** casing variation, WhatsApp-style prefixes/suffixes, typo injection, punctuation variation, repetition emphasis
- **Languages:** English, Hindi (Romanized), Bengali (Romanized), Hinglish (code-mixed)
- **No paid APIs used** — fully template-based generation

### Prompts Used (for each class)
Each class used structured templates covering:
- **LIKELY_PAY:** Payment commitments with temporal expressions (e.g., "kal", "next week", "{day}")
- **NEEDS_REMINDER:** Forgetfulness, information requests, scheduling follow-ups
- **DISPUTE:** Amount/validity challenges, receipt references, escalation requests
- **HIGH_RISK:** Threats, avoidance, hostility, legal language
- **VAGUE:** Monosyllabic, non-committal, uncertain responses

## 4. Class Distribution Table

| Class | Total | % | Train | Val | Test |
|-------|-------|---|-------|-----|------|
| LIKELY_PAY | 737 | 22.6% | 514 | 108 | 115 |
| NEEDS_REMINDER | 593 | 18.1% | 414 | 87 | 92 |
| DISPUTE | 545 | 16.7% | 380 | 80 | 85 |
| HIGH_RISK | 582 | 17.8% | 406 | 85 | 91 |
| VAGUE | 811 | 24.8% | 565 | 120 | 126 |

## 5. Language Distribution Table

| Language | Total | % | Train | Val | Test |
|----------|-------|---|-------|-----|------|
| English | 793 | 24.3% | 553 | 116 | 124 |
| Hindi | 790 | 24.2% | 550 | 116 | 124 |
| Bengali | 872 | 26.7% | 609 | 128 | 135 |
| Hinglish | 813 | 24.9% | 567 | 120 | 126 |

## 6. Random Examples per Class (25 each, 125 total)


### LIKELY_PAY (25 examples)

| # | Text | Language | Split |
|---|------|----------|-------|
| 1 | dO HissOn mEin De sakTa hun, PEhlA Month enD Tak | Hindi | test |
| 2 | Bhai mera plan hai Thursday ko clear karna | Hinglish | train |
| 3 | Half abhi de deta hun, baaki 2 din mein plz | Hindi | val |
| 4 | Payment fix hai Ravivaar ko!! | Hindi | train |
| 5 | Payment confirmed for Tuesday | English | train |
| 6 | I'll clear the dues in 3 days | English | val |
| 7 | Will clear the pending amount before Sunday.!! | English | train |
| 8 | Dude mujhe mujhe 15 din aur chahiye bas | Hindi | val |
| 9 | I got my bonus, paying in 2 days | English | val |
| 10 | Parso tak pakka de dunga | Hindi | val |
| 11 | Let me check balance, is weekend mein done 👍??? | Hinglish | train |
| 12 | Honestly i accept the due amount, will pay by Friday 🙏🙏??? | English | train |
| 13 | Listen bhai salry nahi aayi abhi, Shukravaar tak mein pakka kar dunga | Hinglish | train |
| 14 | Half now baaki in 2 days boss | Hinglish | test |
| 15 | Madam haan haan karunga, agle hafte tak pakka | Hinglish | train |
| 16 | Transfer kore debo agle shoptahe | Bengali | train |
| 17 | I ACCEPT THE AMOUNT, WILL PAY WITHIN A WEEK!! | Hinglish | train |
| 18 | let me pay in installments, first one by friday | Hinglish | train |
| 19 | Madam aaj hi payment ho jayega | Hindi | train |
| 20 | Dui bhage dite pari, prothom ta kaal yaar!! | Bengali | test |
| 21 | Can I pay in two parts? First part this weekend | English | train |
| 22 | Sir my friend will lend me, I'll pay by end of month | English | train |
| 23 | Paisa arrange ho gaya, aaj transfer | Hinglish | train |
| 24 | salary ashbe shombar, tarpor e diye debo 🙏🙏!! | Bengali | train |
| 25 | Poora Poora taka ekbare diye debo | Bengali | train |

### NEEDS_REMINDER (25 examples)

| # | Text | Language | Split |
|---|------|----------|-------|
| 1 | Busy chhilam, dekhbo | Bengali | train |
| 2 | Remind me later please | Hinglish | train |
| 3 | Amount verify karna padega | Hindi | train |
| 4 | Ok so aMI JANTAM NA OVERDUE HOYECHE | Bengali | val |
| 5 | Taratari handle korbo | Bengali | train |
| 6 | Yaar Yaar dUI DIN DAO SORT KORAR JONNO 👍 | Bengali | train |
| 7 | Weekend mein dekhta hun thx!! | Hindi | train |
| 8 | Is there a grace period thanks | English | test |
| 9 | Ok so kAHAN PAY KARNA HAI? LINK BHEJO | Hindi | train |
| 10 | I'll get get back to you | Hinglish | train |
| 11 | Work mein busy, will sort soon | Hinglish | train |
| 12 | Sir whICh loan ARE we talkIng abOUt 👍 | English | train |
| 13 | Boss let me get back to you on this??? | English | train |
| 14 | Look when was the due date again | English | train |
| 15 | tRAveL tRAveL pe thA, aBHi aayA hUn yaar | Hindi | val |
| 16 | Bhai auto-pay auto-pay kaise set karna hai | Hindi | val |
| 17 | Hey oh oh bhool gaya tha | Hindi | train |
| 18 | Is there a grace period? | English | test |
| 19 | Honestly Honestly what's the account number for payment? | English | train |
| 20 | Give me 2 days to sort this | Hinglish | train |
| 21 | Listen i think notification miss ho gayi | Hinglish | val |
| 22 | Ye kaun si EMI hai? | Hindi | val |
| 23 | Arey jaldi handle karunga | Hindi | train |
| 24 | Hey ok understood, I'll do something about it ... | English | train |
| 25 | Ok noted, will check | Hinglish | train |

### DISPUTE (25 examples)

| # | Text | Language | Split |
|---|------|----------|-------|
| 1 | I never agreed to these terms | English | train |
| 2 | Loan agreement copy share karo | Hindi | train |
| 3 | 15th ka transAcTioN cHECk karo sir | Hindi | train |
| 4 | Yaar i THINK KOI MISTAKE HAI | Hinglish | train |
| 5 | Basically Basically written proof do kitna banta hai!! | Hindi | test |
| 6 | Hey detailed detailed statement chai, noyto kichu debo na | Bengali | train |
| 7 | My balance should be zero, I completed all payments | English | train |
| 8 | Dekho 15Th E paymEnT KorechiLem, cRedit hOyNi | Bengali | train |
| 9 | Foreclosure amount amount bhul | Bengali | test |
| 10 | Meri bank se contact karo, issue tumhara hai | Hindi | val |
| 11 | I don't agree with the outstanding amount | English | train |
| 12 | Haan 5th er transaction check koro | Bengali | test |
| 13 | Boss i never took this loan | English | val |
| 14 | Boss written proof do amount ka | Hinglish | val |
| 15 | I have the payment receipt, shall I share? | English | test |
| 16 | Charges er er complete breakdown pathao plz | Bengali | test |
| 17 | Suno iNTEREST RATE KYUN BADLA 😢 | Hindi | test |
| 18 | PhonePe se paid already, recheck please | Hinglish | train |
| 19 | Formal complaint kar raha hun | Hindi | test |
| 20 | Processing Processing fee waive honi thi 🙏🙏 | Hinglish | test |
| 21 | Acha ami ei loan niini | Bengali | train |
| 22 | CHECK THE 20TH TRANSACTION | English | train |
| 23 | Bhai Bhai ye amount galat hai | Hinglish | test |
| 24 | Check 15th transaction pls | Hinglish | train |
| 25 | Ok so i waS PROmised A DIFfeReNT intEResT rate 🤷 | English | train |

### HIGH_RISK (25 examples)

| # | Text | Language | Split |
|---|------|----------|-------|
| 1 | I have nothing to give | Hinglish | test |
| 2 | Bhai ye vasuli hai | Hindi | train |
| 3 | You harass innocent log | Hinglish | train |
| 4 | Dure jao 😡 | Bengali | val |
| 5 | Nijer kaj kaj koro | Bengali | val |
| 6 | RBI mein complaint kar chuka hun | Hindi | train |
| 7 | I have no obligation to pay this | English | train |
| 8 | Mind your business business bro | Hinglish | train |
| 9 | Sir oNE MORE CALL = FIR na? | Hinglish | train |
| 10 | Banking ombudsman se baat karunga | Hinglish | train |
| 11 | Honestly your company is totally fraud | Hinglish | test |
| 12 | I don't owe anything and won't pay | English | train |
| 13 | Nahi dunga aur ye final hai | Hindi | train |
| 14 | Ok so tumhari company fraud hai | Hindi | train |
| 15 | Kichu debar nei amar | Bengali | val |
| 16 | See dOOR HO JAO??? | Hindi | train |
| 17 | Haan number block kar raha hun 🙏🙏 | Hindi | val |
| 18 | I'm blocking this number thanks | English | train |
| 19 | Listen you can't do anything to me | English | train |
| 20 | media te jabO jabO 💰 | Bengali | val |
| 21 | don't don't ever contact me again | English | train |
| 22 | Dekho i don't owe anything and won't pay!! | English | train |
| 23 | Kichu debar nei amar yaar??? | Bengali | train |
| 24 | Hey i've already complained to RBI about you.!! | English | test |
| 25 | Actually yOU yOU harass INnoCent log | Hinglish | train |

### VAGUE (25 examples)

| # | Text | Language | Split |
|---|------|----------|-------|
| 1 | Haan muShkIl oBOstha | Bengali | train |
| 2 | issues ache 🤷??? | Bengali | val |
| 3 | I'll look look into it yaar!! | English | train |
| 4 | sochne do 😢 | Hindi | train |
| 5 | See aUR PRIORITIES PRIORITIES HAIN | Hindi | train |
| 6 | Shayad yaar | Hindi | test |
| 7 | Sir no comment??? | Bengali | train |
| 8 | bhebhe dekhchi ... | Bengali | val |
| 9 | Sochunga !! | Hindi | train |
| 10 | haan hOyTO sir | Bengali | val |
| 11 | Arey dekhte hain kya hota hai | Hindi | train |
| 12 | Well ke jane??? | Bengali | train |
| 13 | Yaar it's complicated hai | Hinglish | train |
| 14 | MAYBE LATER LATER SOMETIME | Hinglish | test |
| 15 | who knows 💰 | English | train |
| 16 | NOT SURE HONESTLY boss | Hinglish | train |
| 17 | Mushkil hai hai situation | Hindi | train |
| 18 | It's not that simple yaar | English | train |
| 19 | Honestly abHI ansWer nahi hAI meRe paas | Hinglish | train |
| 20 | who knows yaar | English | train |
| 21 | Time chahiye mujhe | Hindi | train |
| 22 | Haan not right now bhai | Hinglish | train |
| 23 | Ekhon uttor dite dite parbo na yaar??? | Bengali | train |
| 24 | Could be | English | train |
| 25 | Well hoyto hoye jabe 😭 | Bengali | train |

## 7. Random Examples per Language (25 each, 100 total)


### English (25 examples)

| # | Text | Label | Split |
|---|------|-------|-------|
| 1 | Can you share UPI? I will pay now | LIKELY_PAY | train |
| 2 | I'll I'll clear the dues by end of month !!??? | LIKELY_PAY | train |
| 3 | I was traveling, just got back | NEEDS_REMINDER | test |
| 4 | Yaar maybe | VAGUE | val |
| 5 | Sir i don't know | VAGUE | val |
| 6 | I am not avoiding payment, I will pay in 3 days | LIKELY_PAY | train |
| 7 | Hey why was the interest rate changed 🙏 | DISPUTE | train |
| 8 | Honestly yOu peOple are scammeRs boss | HIGH_RISK | train |
| 9 | will do neft next week thanks!! | LIKELY_PAY | train |
| 10 | YOU CAN'T DO DO ANYTHING TO ME 🙂 | HIGH_RISK | train |
| 11 | Haan i'll look into it | VAGUE | train |
| 12 | Leave me alone or I'll take legal action | HIGH_RISK | train |
| 13 | Let me pay half now and rest by end of month | LIKELY_PAY | train |
| 14 | Why is this still showing as unpaid? | DISPUTE | train |
| 15 | I was traveling, traveling, just got back | NEEDS_REMINDER | test |
| 16 | The foreclosure amount is wrong | DISPUTE | train |
| 17 | Ok fine, take the payment by Friday | LIKELY_PAY | train |
| 18 | Ok so i waS PROmised A DIFfeReNT intEResT rate 🤷 | DISPUTE | train |
| 19 | I didn't get any notification | NEEDS_REMINDER | val |
| 20 | I wasn't aware it was overdue | NEEDS_REMINDER | train |
| 21 | Let me check my balance and pay tomorrow | LIKELY_PAY | val |
| 22 | Was Was there an SMS? I didn't see it 😭 | NEEDS_REMINDER | test |
| 23 | You people people have no shame 🙏🙏 | HIGH_RISK | train |
| 24 | This is someone else's loan, not mine | DISPUTE | val |
| 25 | Send Send me a complete breakdown of charges 😭 | DISPUTE | train |

### Hindi (25 examples)

| # | Text | Label | Split |
|---|------|-------|-------|
| 1 | tHodA aur TIme DO, monTh end tak taK DE DuNga | LIKELY_PAY | train |
| 2 | PEHLE PEHLE WIFE SE BAAT KARNA PADEGA!! | NEEDS_REMINDER | train |
| 3 | Bhai bas thoda sa wait karo 😢!! | LIKELY_PAY | train |
| 4 | Foreclosure amount galat hai | DISPUTE | train |
| 5 | Grace period milta hai kya? | NEEDS_REMINDER | train |
| 6 | complicated hai yaar | VAGUE | train |
| 7 | Mujhe pata nahi tha overdue hai | NEEDS_REMINDER | val |
| 8 | Honestly haan bhai, Shukravaar tak tak kar dunga | LIKELY_PAY | train |
| 9 | Hey Hey baad mein bataunga | VAGUE | train |
| 10 | Kal payment kar dunga plz | LIKELY_PAY | train |
| 11 | Aage se mere lawyer se baat karo | HIGH_RISK | train |
| 12 | Situation dekhni padegi | VAGUE | train |
| 13 | Boss email pe details bhej do | NEEDS_REMINDER | train |
| 14 | Kuch aisa hi | VAGUE | train |
| 15 | Shayad | VAGUE | train |
| 16 | Bhai samajhna padega!! | VAGUE | train |
| 17 | Honestly main bhool gaya tha, abhi karta hun | LIKELY_PAY | test |
| 18 | Koshish karunga | VAGUE | train |
| 19 | Actually amnt bhej raha hun thodi der mein | LIKELY_PAY | train |
| 20 | AAJ HI PAYMENT HO JAYEGA yaar | LIKELY_PAY | test |
| 21 | Ok so tumhari company fraud hai | HIGH_RISK | train |
| 22 | Basically Basically written proof do kitna banta hai!! | DISPUTE | test |
| 23 | half abhi de deta hun, baaki ek hafte mein | LIKELY_PAY | train |
| 24 | See cHECK KARKE BATATA HUN 💰!! | NEEDS_REMINDER | train |
| 25 | Arey fIr karungA tuMhare Naam Pe ... | HIGH_RISK | train |

### Bengali (25 examples)

| # | Text | Label | Split |
|---|------|-------|-------|
| 1 | Diye debo, chinta koro na boss | LIKELY_PAY | test |
| 2 | Honestly charges er complete breakdown pathao 🙂??? | DISPUTE | train |
| 3 | Ekhon uttor dite dite parbo na yaar??? | VAGUE | train |
| 4 | Ami ei call record korchi | HIGH_RISK | test |
| 5 | Aaj bikale transfr kore debo plz | LIKELY_PAY | train |
| 6 | Adha ekhon, baki ta Shukrobar er moddhe | LIKELY_PAY | train |
| 7 | Haan 5th er transaction check koro | DISPUTE | test |
| 8 | Pura taka diye debo agle shoptahe | LIKELY_PAY | train |
| 9 | Bolte parbo na shotti na? | VAGUE | val |
| 10 | Salary ashle tukni korbo asap | LIKELY_PAY | test |
| 11 | Ami responsible, payment korbo | LIKELY_PAY | train |
| 12 | Amar lawyer dekhbe | HIGH_RISK | train |
| 13 | KICHU KICHU EKTA 🙂 | VAGUE | train |
| 14 | Exact due amount bolo | NEEDS_REMINDER | train |
| 15 | Formal complaint korchi | DISPUTE | train |
| 16 | Janano r jonno dhonnobad, check korbo | NEEDS_REMINDER | train |
| 17 | Arey bhebhe dekhchi. | VAGUE | train |
| 18 | Suno media te jabo thanks | HIGH_RISK | train |
| 19 | Ok so cheshta korchi nijer dik theke | VAGUE | train |
| 20 | Honestly hmm | VAGUE | train |
| 21 | Look amI ei calL rEcoRd kOrchi yaar!! | HIGH_RISK | train |
| 22 | Dekho koto taka exactly? | NEEDS_REMINDER | train |
| 23 | Tomar system bhul data dekhacche | DISPUTE | train |
| 24 | Basically number change korechi, reminder asheni | NEEDS_REMINDER | train |
| 25 | 20th er transaction check koro | DISPUTE | train |

### Hinglish (25 examples)

| # | Text | Label | Split |
|---|------|-------|-------|
| 1 | I'll ruin your company reputation | HIGH_RISK | train |
| 2 | Haan i'm serious about this, will pay by friday | LIKELY_PAY | val |
| 3 | Last time bol raha hun | HIGH_RISK | train |
| 4 | already talked to bank, will come next week | LIKELY_PAY | train |
| 5 | Basically maybE ho jAYega!! | VAGUE | train |
| 6 | Actually remind remind me later please | NEEDS_REMINDER | test |
| 7 | Final answer: answer: no payment | HIGH_RISK | train |
| 8 | HAAN HAAN KARUNGA, AGLE HAFTE TAK PAKKA 🙂 | LIKELY_PAY | train |
| 9 | Suno maybe later sometime | VAGUE | train |
| 10 | Yaar 4 din aur de do, pakka payment | LIKELY_PAY | train |
| 11 | Madam haan haan karunga, agle hafte tak pakka | LIKELY_PAY | train |
| 12 | DETAILED STATEMENT DO, DO, TAB TAK NAHI DUNGA yaar | DISPUTE | train |
| 13 | Let me check balance, is weekend mein done asap | LIKELY_PAY | train |
| 14 | Leave me alone alone ya legal action lunga 🤷 | HIGH_RISK | test |
| 15 | Dekho social media pe viral karunga!! | HIGH_RISK | train |
| 16 | Yaar full amount de dunga this weekend!! | LIKELY_PAY | test |
| 17 | i'm serious about this, will pay this weekend | LIKELY_PAY | train |
| 18 | Wrong person ko call kar rahe ho | HIGH_RISK | train |
| 19 | Look it's not that simple yaar ok???? | VAGUE | train |
| 20 | bro tensiOn Mat le, i'll cLEAR it in 3 Days | LIKELY_PAY | train |
| 21 | You harass innocent log | HIGH_RISK | train |
| 22 | Haan tHANKS FOR LETTING ME KNOW, CHECKING NOW yaar | NEEDS_REMINDER | train |
| 23 | Dude Dude thoda time chahiye, but I will pay for sure ... | LIKELY_PAY | val |
| 24 | Haan I know, will pay in 3 days | LIKELY_PAY | train |
| 25 | I accept the amount, will pay this weekend ok? | LIKELY_PAY | train |

## 8. Edge Cases (50 examples)

| # | Text | Label | Language | Type | Concern |
|---|------|-------|----------|------|---------|
| 1 | Uncertain | VAGUE | English | short (<10 chars) | Too short for classification |
| 2 | Acha hmm | VAGUE | Hindi | short (<10 chars) | Too short for classification |
| 3 | Ke jane!! | VAGUE | Bengali | short (<10 chars) | Too short for classification |
| 4 | Jani na | VAGUE | Bengali | short (<10 chars) | Too short for classification |
| 5 | I'll try | VAGUE | English | short (<10 chars) | Too short for classification |
| 6 | Shayad | VAGUE | Hindi | short (<10 chars) | Too short for classification |
| 7 | Hmm ok??? | VAGUE | Hinglish | short (<10 chars) | Too short for classification |
| 8 | Maybe!! | VAGUE | English | short (<10 chars) | Too short for classification |
| 9 | Dure jao | HIGH_RISK | Bengali | short (<10 chars) | Too short for classification |
| 10 | Maybe sir | VAGUE | English | short (<10 chars) | Too short for classification |
| 11 | Jo bhi | VAGUE | Hindi | short (<10 chars) | Too short for classification |
| 12 | Hote pare | VAGUE | Bengali | short (<10 chars) | Too short for classification |
| 13 | Maybe | VAGUE | English | short (<10 chars) | Too short for classification |
| 14 | Theek hai | VAGUE | Hindi | short (<10 chars) | Too short for classification |
| 15 | Ok??? | VAGUE | English | short (<10 chars) | Too short for classification |
| 16 | Honestly ekhon taka taka nei, agle shoptahe porjonto wait koro boss | LIKELY_PAY | Bengali | long (>55 chars) | None — acceptable length |
| 17 | Basically my balance should be zero, I completed all payments 😢 | DISPUTE | English | long (>55 chars) | None — acceptable length |
| 18 | Basically my payment payment on 15th was not credited??? | DISPUTE | English | long (>55 chars) | None — acceptable length |
| 19 | Suno tumhari company seedhe logon ko pareshan karti hai thanks!! | HIGH_RISK | Hindi | long (>55 chars) | None — acceptable length |
| 20 | Basically i NeED an escalatION, This amount Is DiSputed!! | DISPUTE | English | long (>55 chars) | None — acceptable length |
| 21 | Bhai salary nahi aayi abhi, 3 din mein mein pakka kar dunga | LIKELY_PAY | Hinglish | long (>55 chars) | None — acceptable length |
| 22 | Sir i AM NOT AVOIDING PAYMENT, I WILL PAY WITHIN A WEEK thx | LIKELY_PAY | English | long (>55 chars) | None — acceptable length |
| 23 | I've already spoken to my bank, transfer will come this weekend | LIKELY_PAY | English | long (>55 chars) | None — acceptable length |
| 24 | Yaar will clear clear the pending amount before Tuesday!! | LIKELY_PAY | English | long (>55 chars) | None — acceptable length |
| 25 | Actually Actually ek aur chance do, shukravaar tak guaranteed | LIKELY_PAY | Hinglish | long (>55 chars) | None — acceptable length |
| 26 | I'LL PAY THE FULL AMOUNT WITHIN A WEEK | LIKELY_PAY | English | all-caps | May indicate anger or emphasis |
| 27 | NO COMMENT COMMENT BHAI | VAGUE | Hinglish | all-caps | May indicate anger or emphasis |
| 28 | WHO KNOWS!! | VAGUE | English | all-caps | May indicate anger or emphasis |
| 29 | EXACTLY KITNA HAI 😡 | NEEDS_REMINDER | Hinglish | all-caps | May indicate anger or emphasis |
| 30 | PEHLE PEHLE WIFE SE BAAT KARNA PADEGA!! | NEEDS_REMINDER | Hindi | all-caps | May indicate anger or emphasis |
| 31 | MY PAYMENT IS SCHEDULED FOR MONDAY | LIKELY_PAY | English | all-caps | May indicate anger or emphasis |
| 32 | I ACCEPT THE DUE AMOUNT, WILL PAY IN 3 DAYS | LIKELY_PAY | English | all-caps | May indicate anger or emphasis |
| 33 | AMI SERIOUS, MASH SHESHE PORJONTO PAKKA | LIKELY_PAY | Bengali | all-caps | May indicate anger or emphasis |
| 34 | I ACCEPT THE AMOUNT, WILL PAY WITHIN A WEEK!! | LIKELY_PAY | Hinglish | all-caps | May indicate anger or emphasis |
| 35 | YOU CAN'T DO DO ANYTHING TO ME 🙂 | HIGH_RISK | English | all-caps | May indicate anger or emphasis |
| 36 | manager manager se baat karao mujhe 🙂 | DISPUTE | Hindi | contains emoji | Model may not handle emoji well |
| 37 | Basically my balance should be zero, I completed all payments 😢 | DISPUTE | English | contains emoji | Model may not handle emoji well |
| 38 | Madam bhule gechilam, ekhon korchi 🤷 | LIKELY_PAY | Bengali | contains emoji | Model may not handle emoji well |
| 39 | Bhai ye amnt galat hai 😢??? | DISPUTE | Hinglish | contains emoji | Model may not handle emoji well |
| 40 | EXACTLY KITNA HAI 😡 | NEEDS_REMINDER | Hinglish | contains emoji | Model may not handle emoji well |
| 41 | Maybe shayad 🙏??? | VAGUE | Hinglish | contains emoji | Model may not handle emoji well |
| 42 | Boss situation check karna padega 🙏🙏 | VAGUE | Hinglish | contains emoji | Model may not handle emoji well |
| 43 | Bhai mera mera bonus aaya hai, paying today 🙏🙏 | LIKELY_PAY | Hinglish | contains emoji | Model may not handle emoji well |
| 44 | Well hoyto hoye jabe 😭 | VAGUE | Bengali | contains emoji | Model may not handle emoji well |
| 45 | See tum logon se baat khatam 🤷 | HIGH_RISK | Hindi | contains emoji | Model may not handle emoji well |
| 46 | Listen statement pawa jabe?!! | NEEDS_REMINDER | Bengali | aggressive punctuation | Emotional intensity marker |
| 47 | I wasn't aware it was overdue ok?!! | NEEDS_REMINDER | English | aggressive punctuation | Emotional intensity marker |
| 48 | Basically account number dao, ekhon transfer kori!! | LIKELY_PAY | Bengali | aggressive punctuation | Emotional intensity marker |
| 49 | Kichu debar nei amar yaar??? | HIGH_RISK | Bengali | aggressive punctuation | Emotional intensity marker |
| 50 | Haan pata hi nahi chala late ho gaya boss!! | NEEDS_REMINDER | Hindi | aggressive punctuation | Emotional intensity marker |

## 9. Quality Concerns

1. Template-based generation means some structural patterns repeat across examples
2. Romanized Bengali may not fully represent natural Bengali writing patterns
3. Hinglish code-mixing patterns are template-driven, not corpus-extracted

## 10. EDA Plots Generated

All plots saved successfully:
- `data/plots/class_distribution.png` — class distribution overall and by split
- `data/plots/language_distribution.png` — language distribution and language×class heatmap
- `data/plots/message_length_by_class.png` — boxplot and histogram of message lengths

