#!/usr/bin/env python3
"""
RecoveryBench — Promise Parser Tests

50 validation examples across all languages:
- 15 English (10 with promise, 5 without)
- 15 Hindi/Hinglish (10 with promise, 5 without)
- 10 Bengali (7 with promise, 3 without)
- 10 Edge cases (ambiguous, partial, conditional)
"""

import sys
from pathlib import Path

# Ensure project root is on path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
from pipeline.promise_parser import PromiseParser


@pytest.fixture
def parser():
    return PromiseParser()


# ============================================================
# ENGLISH — 15 examples (10 with promise, 5 without)
# ============================================================

class TestEnglishPromises:
    """English promise extraction tests."""

    # --- 10 with promise ---

    def test_en_01_will_pay_tomorrow(self, parser):
        """E01: Clear promise with temporal."""
        result = parser.extract("I will pay tomorrow")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 1

    def test_en_02_pay_by_next_week(self, parser):
        """E02: Promise with 'by next week'."""
        result = parser.extract("I'll pay by next week for sure")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 7

    def test_en_03_end_of_month(self, parser):
        """E03: Promise with 'end of month'."""
        result = parser.extract("Will settle the amount by end of month")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 30

    def test_en_04_in_two_days(self, parser):
        """E04: Promise with 'in 2 days'."""
        result = parser.extract("Can pay in 2 days, please wait")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 2

    def test_en_05_after_salary(self, parser):
        """E05: Promise contingent on salary."""
        result = parser.extract("Will transfer after salary comes")
        assert result["promise_to_pay"] is True

    def test_en_06_definitely_pay(self, parser):
        """E06: Strong promise intent, no specific date."""
        result = parser.extract("I will definitely pay, just give me some time")
        assert result["promise_to_pay"] is True

    def test_en_07_today(self, parser):
        """E07: Same-day payment promise."""
        result = parser.extract("Let me pay today itself")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 0

    def test_en_08_next_month(self, parser):
        """E08: Promise with 'next month'."""
        result = parser.extract("I'm going to pay next month")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 30

    def test_en_09_three_days(self, parser):
        """E09: Numeric days pattern."""
        result = parser.extract("Give me 3 days, I will send the money")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 3

    def test_en_10_weekend(self, parser):
        """E10: Promise with 'this weekend'."""
        result = parser.extract("I can pay this weekend")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 3

    # --- 5 without promise ---

    def test_en_11_no_promise_dispute(self, parser):
        """E11: Dispute, no promise."""
        result = parser.extract("This is not my loan, check your records")
        assert result["promise_to_pay"] is False

    def test_en_12_no_promise_hostile(self, parser):
        """E12: Hostile, no promise."""
        result = parser.extract("Stop calling me, I don't owe anything")
        assert result["promise_to_pay"] is False

    def test_en_13_no_promise_vague(self, parser):
        """E13: Vague response."""
        result = parser.extract("ok")
        assert result["promise_to_pay"] is False

    def test_en_14_no_promise_refusal(self, parser):
        """E14: Explicit refusal."""
        result = parser.extract("I won't pay this fraudulent amount")
        assert result["promise_to_pay"] is False

    def test_en_15_no_promise_question(self, parser):
        """E15: Question, no commitment."""
        result = parser.extract("How much do I owe exactly?")
        assert result["promise_to_pay"] is False


# ============================================================
# HINDI/HINGLISH — 15 examples (10 with promise, 5 without)
# ============================================================

class TestHindiHinglishPromises:
    """Hindi and Hinglish promise extraction tests."""

    # --- 10 with promise ---

    def test_hi_01_kal_kar_dunga(self, parser):
        """H01: Classic Hinglish promise."""
        result = parser.extract("kal kar dunga payment")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 1

    def test_hi_02_agle_hafte(self, parser):
        """H02: Next week in Hindi."""
        result = parser.extract("agle hafte bhej dunga bhai")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 7

    def test_hi_03_month_end_tak(self, parser):
        """H03: Month end commitment."""
        result = parser.extract("month end tak kar denge pakka")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 30

    def test_hi_04_do_din(self, parser):
        """H04: Two days in Hindi."""
        result = parser.extract("do din me karunga payment")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 2

    def test_hi_05_salary_ke_baad(self, parser):
        """H05: After salary commitment."""
        result = parser.extract("salary ke baad de dunga bhai")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 10

    def test_hi_06_parso(self, parser):
        """H06: Day after tomorrow."""
        result = parser.extract("parso transfer kar dunga")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 2

    def test_hi_07_abhi(self, parser):
        """H07: Right now promise."""
        result = parser.extract("abhi kar deta hun payment")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 0

    def test_hi_08_teen_din(self, parser):
        """H08: Three days in Hindi."""
        result = parser.extract("teen din mein bhejunga")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 3

    def test_hi_09_pakka_promise(self, parser):
        """H09: 'Pakka' as strong promise signal."""
        result = parser.extract("pakka karunga payment, tension mat lo")
        assert result["promise_to_pay"] is True

    def test_hi_10_jama_karunga(self, parser):
        """H10: 'Deposit' promise in Hindi."""
        result = parser.extract("bank mein jama karunga kal")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 1

    # --- 5 without promise ---

    def test_hi_11_no_promise_galat(self, parser):
        """H11: Dispute in Hindi."""
        result = parser.extract("yeh galat hai, amount check karo")
        assert result["promise_to_pay"] is False

    def test_hi_12_no_promise_nahi(self, parser):
        """H12: Refusal in Hindi."""
        result = parser.extract("nahi dunga ek bhi paisa")
        assert result["promise_to_pay"] is False

    def test_hi_13_no_promise_hostile(self, parser):
        """H13: Hostile in Hinglish."""
        result = parser.extract("band karo phone, bahut ho gaya")
        assert result["promise_to_pay"] is False

    def test_hi_14_no_promise_vague(self, parser):
        """H14: Vague Hindi response."""
        result = parser.extract("dekhte hain")
        assert result["promise_to_pay"] is False

    def test_hi_15_no_promise_question(self, parser):
        """H15: Question in Hinglish."""
        result = parser.extract("kitna baaki hai mera?")
        assert result["promise_to_pay"] is False


# ============================================================
# BENGALI — 10 examples (7 with promise, 3 without)
# ============================================================

class TestBengaliPromises:
    """Bengali (romanized) promise extraction tests."""

    # --- 7 with promise ---

    def test_bn_01_kaal_debo(self, parser):
        """B01: Tomorrow promise in Bengali."""
        result = parser.extract("kaal debo payment")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 1

    def test_bn_02_salary_ashle(self, parser):
        """B02: After salary in Bengali."""
        result = parser.extract("salary ashle debo")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 10

    def test_bn_03_shoptahe(self, parser):
        """B03: Within a week in Bengali."""
        result = parser.extract("ek shoptah por pathabo")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 7

    def test_bn_04_dui_din(self, parser):
        """B04: Two days in Bengali."""
        result = parser.extract("dui din por diye debo")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 2

    def test_bn_05_mash_sheshe(self, parser):
        """B05: Month end in Bengali."""
        result = parser.extract("mash sheshe korbo payment")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 30

    def test_bn_06_transfer_korbo(self, parser):
        """B06: Transfer promise in Bengali."""
        result = parser.extract("aajke transfer korbo")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 0

    def test_bn_07_tin_din(self, parser):
        """B07: Three days in Bengali."""
        result = parser.extract("tin din somoy din, korbo payment")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 3

    # --- 3 without promise ---

    def test_bn_08_no_promise_dispute(self, parser):
        """B08: Dispute in Bengali."""
        result = parser.extract("ei taka ami dei ni, bhul hoyeche")
        assert result["promise_to_pay"] is False

    def test_bn_09_no_promise_refusal(self, parser):
        """B09: Refusal in Bengali."""
        result = parser.extract("debo na, amar kono loan nei")
        assert result["promise_to_pay"] is False

    def test_bn_10_no_promise_vague(self, parser):
        """B10: Vague Bengali response."""
        result = parser.extract("hmm dekhchi")
        assert result["promise_to_pay"] is False


# ============================================================
# EDGE CASES — 10 examples
# ============================================================

class TestEdgeCases:
    """Edge cases: ambiguous, partial, conditional promises."""

    def test_edge_01_conditional_agar(self, parser):
        """EC01: Conditional promise (agar salary aaye)."""
        result = parser.extract("agar salary aaye toh kar dunga")
        assert result["promise_to_pay"] is True
        # Conditional still counts as promise

    def test_edge_02_conditional_if(self, parser):
        """EC02: Conditional in English."""
        result = parser.extract("If I get my bonus, I will pay next week")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 7

    def test_edge_03_empty_string(self, parser):
        """EC03: Empty input."""
        result = parser.extract("")
        assert result["promise_to_pay"] is False
        assert result["payment_window_days"] is None

    def test_edge_04_very_short(self, parser):
        """EC04: Very short message."""
        result = parser.extract("ok")
        assert result["promise_to_pay"] is False

    def test_edge_05_mixed_signal(self, parser):
        """EC05: Temporal expression without promise words."""
        result = parser.extract("maybe tomorrow")
        assert result["promise_to_pay"] is True
        # Temporal implies promise
        assert result["payment_window_days"] == 1

    def test_edge_06_negation_with_temporal(self, parser):
        """EC06: Negation overrides temporal."""
        result = parser.extract("I won't pay even by next week")
        assert result["promise_to_pay"] is False

    def test_edge_07_all_caps(self, parser):
        """EC07: All caps input."""
        result = parser.extract("I WILL PAY TOMORROW")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 1

    def test_edge_08_numeric_days(self, parser):
        """EC08: Numeric pattern '5 din'."""
        result = parser.extract("5 din baad de dunga")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 5

    def test_edge_09_conditional_bengali(self, parser):
        """EC09: Conditional in Bengali."""
        result = parser.extract("jodi salary pele debo")
        assert result["promise_to_pay"] is True

    def test_edge_10_code_mixed(self, parser):
        """EC10: Heavy code-mixing."""
        result = parser.extract("bhai next week payment kar dunga definitely, pakka promise")
        assert result["promise_to_pay"] is True
        assert result["payment_window_days"] == 7


# ============================================================
# Additional validation tests
# ============================================================

class TestPromiseParserBasics:
    """Basic functionality tests."""

    def test_parser_init(self, parser):
        """Parser initializes without error."""
        assert parser is not None

    def test_none_input(self, parser):
        """None input should not crash."""
        result = parser.extract(None)
        assert result["promise_to_pay"] is False

    def test_whitespace_input(self, parser):
        """Whitespace-only input."""
        result = parser.extract("   ")
        assert result["promise_to_pay"] is False

    def test_result_keys(self, parser):
        """Output has all required keys."""
        result = parser.extract("some text")
        assert "promise_to_pay" in result
        assert "payment_window_days" in result
        assert "raw_expression" in result

    def test_window_cap_at_90(self, parser):
        """Payment window should not exceed 90 days."""
        result = parser.extract("I will pay in 120 days")
        if result["payment_window_days"] is not None:
            assert result["payment_window_days"] <= 90
