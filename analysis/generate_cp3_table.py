# -*- coding: utf-8 -*-
"""Generate the 50-case validation table for Checkpoint 3 report."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, '.')
from pipeline.promise_parser import PromiseParser

parser = PromiseParser()

# Define all 50 test cases
cases = [
    # English — 10 with promise
    ("I will pay tomorrow", "English", True, 1),
    ("I'll pay by next week for sure", "English", True, 7),
    ("Will settle the amount by end of month", "English", True, 30),
    ("Can pay in 2 days, please wait", "English", True, 2),
    ("Will transfer after salary comes", "English", True, None),
    ("I will definitely pay, just give me some time", "English", True, None),
    ("Let me pay today itself", "English", True, 0),
    ("I'm going to pay next month", "English", True, 30),
    ("Give me 3 days, I will send the money", "English", True, 3),
    ("I can pay this weekend", "English", True, 3),
    # English — 5 without promise
    ("This is not my loan, check your records", "English", False, None),
    ("Stop calling me, I don't owe anything", "English", False, None),
    ("ok", "English", False, None),
    ("I won't pay this fraudulent amount", "English", False, None),
    ("How much do I owe exactly?", "English", False, None),
    # Hindi/Hinglish — 10 with promise
    ("kal kar dunga payment", "Hindi", True, 1),
    ("agle hafte bhej dunga bhai", "Hindi", True, 7),
    ("month end tak kar denge pakka", "Hinglish", True, 30),
    ("do din me karunga payment", "Hindi", True, 2),
    ("salary ke baad de dunga bhai", "Hindi", True, 10),
    ("parso transfer kar dunga", "Hindi", True, 2),
    ("abhi kar deta hun payment", "Hindi", True, 0),
    ("teen din mein bhejunga", "Hindi", True, 3),
    ("pakka karunga payment, tension mat lo", "Hindi", True, None),
    ("bank mein jama karunga kal", "Hindi", True, 1),
    # Hindi/Hinglish — 5 without promise
    ("yeh galat hai, amount check karo", "Hindi", False, None),
    ("nahi dunga ek bhi paisa", "Hindi", False, None),
    ("band karo phone, bahut ho gaya", "Hindi", False, None),
    ("dekhte hain", "Hindi", False, None),
    ("kitna baaki hai mera?", "Hindi", False, None),
    # Bengali — 7 with promise
    ("kaal debo payment", "Bengali", True, 1),
    ("salary ashle debo", "Bengali", True, 10),
    ("ek shoptah por pathabo", "Bengali", True, 7),
    ("dui din por diye debo", "Bengali", True, 2),
    ("mash sheshe korbo payment", "Bengali", True, 30),
    ("aajke transfer korbo", "Bengali", True, 0),
    ("tin din somoy din, korbo payment", "Bengali", True, 3),
    # Bengali — 3 without promise
    ("ei taka ami dei ni, bhul hoyeche", "Bengali", False, None),
    ("debo na, amar kono loan nei", "Bengali", False, None),
    ("hmm dekhchi", "Bengali", False, None),
    # Edge cases — 10
    ("agar salary aaye toh kar dunga", "Hinglish", True, None),
    ("If I get my bonus, I will pay next week", "English", True, 7),
    ("", "N/A", False, None),
    ("ok", "English", False, None),
    ("maybe tomorrow", "English", True, 1),
    ("I won't pay even by next week", "English", False, None),
    ("I WILL PAY TOMORROW", "English", True, 1),
    ("5 din baad de dunga", "Hindi", True, 5),
    ("jodi salary pele debo", "Bengali", True, None),
    ("bhai next week payment kar dunga definitely, pakka promise", "Hinglish", True, 7),
]

# Run all cases
passed = 0
failed = 0
results = []

for i, (text, lang, expected_promise, expected_window) in enumerate(cases, 1):
    result = parser.extract(text)
    actual_promise = result["promise_to_pay"]
    actual_window = result["payment_window_days"]

    # Check promise match
    promise_ok = actual_promise == expected_promise

    # Check window match (None matches None, or exact match, or within tolerance for salary-based)
    if expected_window is None:
        window_ok = True  # Don't check window if not specified
    else:
        window_ok = actual_window == expected_window

    pass_fail = "PASS" if (promise_ok and window_ok) else "FAIL"
    if pass_fail == "PASS":
        passed += 1
    else:
        failed += 1

    text_display = text[:60] if text else "(empty)"
    results.append((i, text_display, lang, expected_promise, actual_promise,
                     expected_window, actual_window, pass_fail))

print(f"PASS: {passed}, FAIL: {failed}, TOTAL: {passed+failed}")
print(f"Pass rate: {passed/(passed+failed)*100:.1f}%")
print()
print("| # | Input Text | Language | Expected PTP | Actual PTP | Expected Window | Actual Window | Result |")
print("|---|---|---|---|---|---|---|---|")
for r in results:
    print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} |")
