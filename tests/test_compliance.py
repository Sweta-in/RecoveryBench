#!/usr/bin/env python3
"""
RecoveryBench — Compliance Checker Tests (Phase 5)

Tests:
  - Rules load correctly from JSON
  - Known violations detected (4+ per category)
  - Known compliant messages pass
  - Severity ordering works
  - Suggested rewrites are present
  - Batch checking works
  - Edge cases: empty messages, very long messages, unicode
"""

import sys
from pathlib import Path

# Ensure project root is on path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import json
import pytest


@pytest.fixture(scope="module")
def checker():
    """Create a ComplianceChecker instance."""
    from pipeline.compliance import ComplianceChecker
    return ComplianceChecker()


@pytest.fixture(scope="module")
def rules_data():
    """Load raw rules JSON for validation."""
    rules_path = project_root / "rules" / "compliance_rules.json"
    with open(rules_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# Rule file validation
# ============================================================

class TestRulesFile:
    """Validate the rules JSON file structure and content."""

    def test_rules_file_exists(self):
        """compliance_rules.json exists in rules/ directory."""
        path = project_root / "rules" / "compliance_rules.json"
        assert path.exists(), f"Rules file not found at {path}"

    def test_valid_json(self, rules_data):
        """Rules file is valid JSON."""
        assert "rules" in rules_data

    def test_minimum_rule_count(self, rules_data):
        """At least 20 rules defined (governance requirement)."""
        assert len(rules_data["rules"]) >= 20, (
            f"Only {len(rules_data['rules'])} rules found, need >= 20"
        )

    def test_all_categories_present(self, rules_data):
        """All 5 required categories have at least 1 rule."""
        required = {"threats", "harassment", "abusive_language", "coercion", "false_claims"}
        present = set(r["category"] for r in rules_data["rules"])
        missing = required - present
        assert not missing, f"Missing categories: {missing}"

    def test_minimum_per_category(self, rules_data):
        """Each category has at least 5 rules (governance requirement)."""
        from collections import Counter
        counts = Counter(r["category"] for r in rules_data["rules"])
        for cat in ["threats", "harassment", "abusive_language", "coercion", "false_claims"]:
            assert counts.get(cat, 0) >= 5, (
                f"Category '{cat}' has only {counts.get(cat, 0)} rules, need >= 5"
            )

    def test_unique_rule_ids(self, rules_data):
        """All rule IDs are unique."""
        ids = [r["id"] for r in rules_data["rules"]]
        assert len(ids) == len(set(ids)), f"Duplicate rule IDs found: {ids}"

    def test_required_fields(self, rules_data):
        """Every rule has all required fields."""
        required = {"id", "category", "severity", "description", "patterns"}
        for rule in rules_data["rules"]:
            missing = required - set(rule.keys())
            assert not missing, f"Rule {rule.get('id', '?')} missing fields: {missing}"

    def test_valid_severities(self, rules_data):
        """All severities are valid values."""
        valid = {"minor", "moderate", "critical"}
        for rule in rules_data["rules"]:
            assert rule["severity"] in valid, (
                f"Rule {rule['id']} has invalid severity: {rule['severity']}"
            )

    def test_non_empty_patterns(self, rules_data):
        """Every rule has at least one pattern."""
        for rule in rules_data["rules"]:
            assert len(rule["patterns"]) > 0, (
                f"Rule {rule['id']} has no patterns"
            )


# ============================================================
# Checker initialization
# ============================================================

class TestCheckerInit:
    """Test ComplianceChecker initialization."""

    def test_checker_loads(self, checker):
        """Checker initializes without error."""
        assert checker is not None

    def test_rule_count(self, checker):
        """Checker loads at least 20 rules."""
        assert checker.get_rule_count() >= 20

    def test_categories(self, checker):
        """Checker has all required categories."""
        cats = checker.get_categories()
        for cat in ["threats", "harassment", "abusive_language", "coercion", "false_claims"]:
            assert cat in cats, f"Missing category: {cat}"

    def test_category_summary(self, checker):
        """Category summary returns valid structure."""
        summary = checker.get_category_summary()
        assert len(summary) >= 5
        for cat, info in summary.items():
            assert "count" in info
            assert "severities" in info
            assert info["count"] >= 1


# ============================================================
# Violation detection — threats category
# ============================================================

class TestThreatsDetection:
    """Test detection of threat-category violations."""

    def test_arrest_threat(self, checker):
        """Detects arrest threat."""
        result = checker.check("Pay now or we will arrest you")
        assert not result["compliant"]
        assert any(v["category"] == "threats" for v in result["violations"])

    def test_police_threat(self, checker):
        """Detects police threat."""
        result = checker.check("If you don't pay by tomorrow police will come to your house")
        assert not result["compliant"]
        assert result["severity"] == "critical"

    def test_jail_threat_hindi(self, checker):
        """Detects jail threat in Hindi."""
        result = checker.check("Agar payment nahi kiya toh jail ho jayega")
        assert not result["compliant"]

    def test_legal_action_threat(self, checker):
        """Detects legal action threat."""
        result = checker.check("We will file case against you in court")
        assert not result["compliant"]

    def test_home_visit_threat(self, checker):
        """Detects home visit intimidation."""
        result = checker.check("Hamare log ghar pe aayenge kal")
        assert not result["compliant"]


# ============================================================
# Violation detection — harassment category
# ============================================================

class TestHarassmentDetection:
    """Test detection of harassment-category violations."""

    def test_family_contact_threat(self, checker):
        """Detects threat to contact family."""
        result = checker.check("Hum aapke family ko bata denge")
        assert not result["compliant"]
        assert any(v["category"] == "harassment" for v in result["violations"])

    def test_public_shaming(self, checker):
        """Detects public shaming threat."""
        result = checker.check("We will post your name on social media pe daal denge")
        assert not result["compliant"]

    def test_excessive_calling(self, checker):
        """Detects threat of excessive calling."""
        result = checker.check("Jab tak pay nahi karoge har din call aayegi")
        assert not result["compliant"]

    def test_workplace_visit(self, checker):
        """Detects threat to visit workplace."""
        result = checker.check("Hum aapke office mein aayenge")
        assert not result["compliant"]
        assert result["severity"] == "critical"

    def test_neighbour_disclosure(self, checker):
        """Detects threat to tell neighbours."""
        result = checker.check("Padosiyon ko bolenge tumhare baare mein")
        assert not result["compliant"]


# ============================================================
# Violation detection — abusive language category
# ============================================================

class TestAbusiveLanguageDetection:
    """Test detection of abusive language violations."""

    def test_insult(self, checker):
        """Detects insulting language."""
        result = checker.check("Tum bewakoof ho, samajh nahi aata kya")
        assert not result["compliant"]
        assert any(v["category"] == "abusive_language" for v in result["violations"])

    def test_demeaning(self, checker):
        """Detects demeaning language."""
        result = checker.check("Tumse kuch nahi hoga, defaulter ho tum")
        assert not result["compliant"]

    def test_discriminatory(self, checker):
        """Detects discriminatory language."""
        result = checker.check("You people never pay on time")
        assert not result["compliant"]

    def test_sarcasm(self, checker):
        """Detects sarcastic/mocking tone."""
        result = checker.check("Loan lena aata hai pay karna nahi tumko")
        assert not result["compliant"]

    def test_gender_harassment(self, checker):
        """Detects gender-based harassment."""
        result = checker.check("Tell your husband to pay the loan")
        assert not result["compliant"]
        assert result["severity"] == "critical"


# ============================================================
# Violation detection — coercion category
# ============================================================

class TestCoercionDetection:
    """Test detection of coercion violations."""

    def test_immediate_payment_demand(self, checker):
        """Detects demand for immediate payment."""
        result = checker.check("Abhi ke abhi pay karo, last chance hai")
        assert not result["compliant"]
        assert any(v["category"] == "coercion" for v in result["violations"])

    def test_borrow_to_repay(self, checker):
        """Detects pressure to borrow from others."""
        result = checker.check("Kisi se udhar leke pay karo, humein koi matlab nahi")
        assert not result["compliant"]

    def test_emotional_manipulation(self, checker):
        """Detects emotional manipulation."""
        result = checker.check("Think of your children, bachon ka future kharab hoga")
        assert not result["compliant"]

    def test_account_freeze_threat(self, checker):
        """Detects unauthorized service threat."""
        result = checker.check("Bank account freeze kar denge agar nahi diya toh")
        assert not result["compliant"]

    def test_property_seizure(self, checker):
        """Detects unauthorized property seizure threat."""
        result = checker.check("Ghar chheen lenge tumhara, gaadi utha lenge")
        assert not result["compliant"]
        assert result["severity"] == "critical"


# ============================================================
# Violation detection — false claims category
# ============================================================

class TestFalseClaimsDetection:
    """Test detection of false claims violations."""

    def test_fake_court_order(self, checker):
        """Detects fake court order claims."""
        result = checker.check("Court order aaya hai tumhare naam ka")
        assert not result["compliant"]
        assert any(v["category"] == "false_claims" for v in result["violations"])

    def test_misrepresent_amount(self, checker):
        """Detects misrepresentation of amount owed."""
        result = checker.check("Penalty laga diya hai extra, ab amount badh gaya hai")
        assert not result["compliant"]

    def test_government_impersonation(self, checker):
        """Detects government impersonation."""
        result = checker.check("Hum government se hain, RBI ne bheja hai")
        assert not result["compliant"]

    def test_false_urgency(self, checker):
        """Detects fabricated deadline urgency."""
        result = checker.check("Aaj raat tak nahi kiya toh this is your last warning")
        assert not result["compliant"]

    def test_false_no_restructure(self, checker):
        """Detects false claim about restructuring."""
        result = checker.check("Ab kuch nahi ho sakta, settlement ka option khatam")
        assert not result["compliant"]


# ============================================================
# Compliant messages — must NOT trigger violations
# ============================================================

class TestCompliantMessages:
    """Messages that should be marked as compliant."""

    def test_polite_reminder(self, checker):
        """Polite reminder is compliant."""
        result = checker.check(
            "We understand you may be facing difficulties. "
            "Please contact us to discuss a repayment plan."
        )
        assert result["compliant"]
        assert result["severity"] == "none"
        assert len(result["violations"]) == 0

    def test_standard_emi_reminder(self, checker):
        """Standard EMI reminder is compliant."""
        result = checker.check(
            "Your EMI of Rs. 5,000 was due on June 1st. "
            "Please make the payment at your earliest convenience."
        )
        assert result["compliant"]

    def test_empathetic_followup(self, checker):
        """Empathetic follow-up is compliant."""
        result = checker.check(
            "We understand that circumstances can change. "
            "Would you like to discuss restructuring your EMI schedule?"
        )
        assert result["compliant"]

    def test_payment_confirmation(self, checker):
        """Payment confirmation is compliant."""
        result = checker.check(
            "Thank you for your payment. Your account has been updated. "
            "Please let us know if you have any questions."
        )
        assert result["compliant"]

    def test_option_offering(self, checker):
        """Offering payment options is compliant."""
        result = checker.check(
            "We have several payment plans available. "
            "Would you prefer a 3-month or 6-month EMI restructuring?"
        )
        assert result["compliant"]

    def test_hindi_polite(self, checker):
        """Polite Hindi message is compliant."""
        result = checker.check(
            "Aapka EMI overdue hai. Kripya jaldi se jaldi payment kar dein. "
            "Agar koi pareshani hai toh humse baat karein."
        )
        assert result["compliant"]

    def test_acknowledgment(self, checker):
        """Simple acknowledgment is compliant."""
        result = checker.check(
            "Thank you for informing us. We have noted your situation "
            "and will follow up in a few days."
        )
        assert result["compliant"]


# ============================================================
# Severity and structure
# ============================================================

class TestSeverityAndStructure:
    """Test severity levels and output structure."""

    def test_critical_severity(self, checker):
        """Critical violations produce critical severity."""
        result = checker.check("Jail ho jayega tumhara agar nahi diya")
        assert result["severity"] == "critical"

    def test_moderate_severity(self, checker):
        """Moderate violations produce moderate severity."""
        result = checker.check("Tumhara credit score kharab ho jayega bahut")
        assert result["severity"] == "moderate"

    def test_suggested_rewrite_present(self, checker):
        """Violations include a suggested rewrite."""
        result = checker.check("Police will come to your house tomorrow")
        assert not result["compliant"]
        assert result["suggested_rewrite"] is not None
        assert len(result["suggested_rewrite"]) > 10

    def test_multiple_violations(self, checker):
        """Message with multiple violations returns all of them."""
        result = checker.check(
            "Bewakoof, tum pagal ho. Police bhejenge aur ghar chheen lenge. "
            "Kisi se udhar leke pay karo."
        )
        assert not result["compliant"]
        assert len(result["violations"]) >= 3
        categories_found = set(v["category"] for v in result["violations"])
        assert len(categories_found) >= 2  # At least 2 different categories

    def test_violation_has_matched_text(self, checker):
        """Each violation includes the matched text."""
        result = checker.check("We will arrest you if payment is not made")
        assert not result["compliant"]
        for v in result["violations"]:
            assert "matched_text" in v
            assert len(v["matched_text"]) > 0

    def test_output_schema(self, checker):
        """Output has all required keys."""
        result = checker.check("Any message here")
        assert "compliant" in result
        assert "violations" in result
        assert "severity" in result
        assert "suggested_rewrite" in result
        assert isinstance(result["compliant"], bool)
        assert isinstance(result["violations"], list)


# ============================================================
# Edge cases
# ============================================================

class TestEdgeCases:
    """Edge case handling."""

    def test_empty_message(self, checker):
        """Empty message is compliant."""
        result = checker.check("")
        assert result["compliant"]
        assert result["severity"] == "none"

    def test_whitespace_only(self, checker):
        """Whitespace-only message is compliant."""
        result = checker.check("   \n\t  ")
        assert result["compliant"]

    def test_none_handling(self, checker):
        """None message is compliant (doesn't crash)."""
        result = checker.check(None)
        assert result["compliant"]

    def test_very_long_message(self, checker):
        """Long compliant message doesn't crash."""
        long_msg = "Thank you for your patience. " * 100
        result = checker.check(long_msg)
        assert result["compliant"]

    def test_unicode_message(self, checker):
        """Unicode characters don't crash the checker."""
        result = checker.check("আমি পরে দিব 🙏🙏🙏")
        assert result["compliant"]  # No violating patterns in this

    def test_case_insensitive(self, checker):
        """Pattern matching is case-insensitive."""
        result = checker.check("WILL ARREST YOU IF NOT PAID")
        assert not result["compliant"]

    def test_batch_check(self, checker):
        """Batch checking returns correct count."""
        messages = [
            "Police will come to your house",
            "Please pay at your convenience",
            "Bewakoof, pay now!",
        ]
        results = checker.check_batch(messages)
        assert len(results) == 3
        assert not results[0]["compliant"]  # police threat
        assert results[1]["compliant"]       # polite
        assert not results[2]["compliant"]   # abusive


# ============================================================
# Integration with analyzer pipeline expectations
# ============================================================

class TestPipelineIntegration:
    """Verify the checker output matches pipeline.analyzer expectations."""

    def test_compliant_output_schema(self, checker):
        """Compliant output matches what analyzer.py expects."""
        result = checker.check("Thank you for your payment.")
        assert result == {
            "compliant": True,
            "violations": [],
            "severity": "none",
            "suggested_rewrite": None,
        }

    def test_violation_output_has_required_fields(self, checker):
        """Violation output has all fields the analyzer needs."""
        result = checker.check("Jail ho jayega agar nahi diya")
        assert not result["compliant"]
        for v in result["violations"]:
            assert "rule_id" in v
            assert "category" in v
            assert "severity" in v
            assert "matched_text" in v
