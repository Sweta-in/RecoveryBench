#!/usr/bin/env python3
"""
RecoveryBench — Compliance Checker (Phase 5)

Detects RBI Fair Practices Code violations in debt collection agent messages.
Rules are loaded from rules/compliance_rules.json — logic and rules are fully separated.

Usage:
    from pipeline.compliance import ComplianceChecker

    checker = ComplianceChecker()
    result = checker.check("If you don't pay by tomorrow police will come to your house")
    # result = {
    #     "compliant": False,
    #     "violations": [...],
    #     "severity": "critical",
    #     "suggested_rewrite": "..."
    # }
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Resolve rules file path relative to this module
_PROJECT_ROOT = Path(__file__).parent.parent
_RULES_PATH = _PROJECT_ROOT / "rules" / "compliance_rules.json"

# Severity ordering for determining overall severity
_SEVERITY_ORDER = {
    "none": 0,
    "minor": 1,
    "moderate": 2,
    "critical": 3,
}


class ComplianceChecker:
    """
    Checks agent messages for RBI Fair Practices Code compliance violations.

    Rules are loaded from `rules/compliance_rules.json`. Each rule defines:
      - id: unique rule identifier (e.g. RBI_001)
      - category: violation category (threats, harassment, abusive_language, coercion, false_claims)
      - severity: critical | moderate | minor
      - description: human-readable description of the rule
      - patterns: list of substring patterns to match against the agent message
      - suggested_rewrite: a compliant alternative to the violating message

    The checker performs case-insensitive substring matching against all patterns.
    If any pattern matches, the corresponding rule is flagged as a violation.
    """

    def __init__(self, rules_path: Optional[str] = None):
        """
        Initialize the compliance checker.

        Args:
            rules_path: Optional override path to rules JSON file.
                        Defaults to rules/compliance_rules.json relative to project root.

        Raises:
            FileNotFoundError: If the rules file does not exist.
            ValueError: If the rules file is malformed or contains no rules.
        """
        self._rules_path = Path(rules_path) if rules_path else _RULES_PATH

        if not self._rules_path.exists():
            raise FileNotFoundError(
                f"Compliance rules file not found: {self._rules_path}\n"
                f"Expected at: {_RULES_PATH}"
            )

        self._rules = self._load_rules()
        self._compiled_patterns = self._compile_patterns()
        logger.info(
            "ComplianceChecker loaded: %d rules across %d categories",
            len(self._rules),
            len(self.get_categories()),
        )

    def _load_rules(self) -> List[Dict]:
        """Load and validate rules from JSON file."""
        with open(self._rules_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        rules = data.get("rules", [])
        if not rules:
            raise ValueError(
                f"No rules found in {self._rules_path}. "
                "Expected a 'rules' array with at least one rule."
            )

        # Validate required fields
        required_fields = {"id", "category", "severity", "description", "patterns"}
        for i, rule in enumerate(rules):
            missing = required_fields - set(rule.keys())
            if missing:
                raise ValueError(
                    f"Rule at index {i} is missing required fields: {missing}"
                )
            if not rule["patterns"]:
                raise ValueError(
                    f"Rule {rule['id']} has no patterns defined."
                )
            if rule["severity"] not in _SEVERITY_ORDER:
                raise ValueError(
                    f"Rule {rule['id']} has invalid severity '{rule['severity']}'. "
                    f"Must be one of: {list(_SEVERITY_ORDER.keys())}"
                )

        return rules

    def _compile_patterns(self) -> List[Dict]:
        """
        Pre-compile regex patterns for each rule for efficient matching.

        Each pattern string is compiled as a case-insensitive regex that matches
        the pattern as a substring anywhere in the text.
        """
        compiled = []
        for rule in self._rules:
            compiled_patterns = []
            for pattern in rule["patterns"]:
                try:
                    # Escape regex special characters, then compile for case-insensitive match
                    escaped = re.escape(pattern)
                    compiled_patterns.append(re.compile(escaped, re.IGNORECASE))
                except re.error as e:
                    logger.warning(
                        "Failed to compile pattern '%s' in rule %s: %s",
                        pattern, rule["id"], e,
                    )
            compiled.append({
                "rule": rule,
                "patterns": compiled_patterns,
            })
        return compiled

    def check(self, agent_message: str) -> Dict:
        """
        Check an agent message for compliance violations.

        Args:
            agent_message: The text of the agent's message to check.

        Returns:
            dict with keys:
                - compliant (bool): True if no violations found
                - violations (list): List of violation dicts, each with:
                    - rule_id (str)
                    - category (str)
                    - severity (str)
                    - description (str)
                    - matched_text (str): the pattern that matched
                - severity (str): overall severity ("none", "minor", "moderate", "critical")
                - suggested_rewrite (str | None): suggested compliant alternative
        """
        if not agent_message or not agent_message.strip():
            return {
                "compliant": True,
                "violations": [],
                "severity": "none",
                "suggested_rewrite": None,
            }

        violations = []
        max_severity = "none"
        suggested_rewrites = []

        for entry in self._compiled_patterns:
            rule = entry["rule"]
            for pattern in entry["patterns"]:
                match = pattern.search(agent_message)
                if match:
                    violation = {
                        "rule_id": rule["id"],
                        "category": rule["category"],
                        "severity": rule["severity"],
                        "description": rule["description"],
                        "matched_text": match.group(),
                    }
                    violations.append(violation)

                    # Track highest severity
                    if _SEVERITY_ORDER.get(rule["severity"], 0) > _SEVERITY_ORDER.get(max_severity, 0):
                        max_severity = rule["severity"]

                    # Collect suggested rewrites
                    rewrite = rule.get("suggested_rewrite")
                    if rewrite and rewrite not in suggested_rewrites:
                        suggested_rewrites.append(rewrite)

                    # Only match first pattern per rule (avoid duplicate violations from same rule)
                    break

        # Pick the rewrite from the highest-severity violation
        suggested_rewrite = None
        if suggested_rewrites:
            # Sort violations by severity descending, use first rewrite
            for v in sorted(
                violations,
                key=lambda x: _SEVERITY_ORDER.get(x["severity"], 0),
                reverse=True,
            ):
                rule_data = self._get_rule_by_id(v["rule_id"])
                if rule_data and rule_data.get("suggested_rewrite"):
                    suggested_rewrite = rule_data["suggested_rewrite"]
                    break

        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "severity": max_severity,
            "suggested_rewrite": suggested_rewrite,
        }

    def check_batch(self, messages: List[str]) -> List[Dict]:
        """
        Check multiple agent messages for compliance violations.

        Args:
            messages: List of agent message strings.

        Returns:
            List of compliance check results, one per message.
        """
        return [self.check(msg) for msg in messages]

    def get_categories(self) -> List[str]:
        """Return sorted list of unique rule categories."""
        return sorted(set(rule["category"] for rule in self._rules))

    def get_rules_by_category(self, category: str) -> List[Dict]:
        """Return all rules for a given category."""
        return [r for r in self._rules if r["category"] == category]

    def get_rule_count(self) -> int:
        """Return total number of loaded rules."""
        return len(self._rules)

    def get_category_summary(self) -> Dict[str, Dict]:
        """
        Return a summary of rules by category.

        Returns:
            Dict mapping category name to {count, severities} dict.
        """
        summary = {}
        for rule in self._rules:
            cat = rule["category"]
            if cat not in summary:
                summary[cat] = {"count": 0, "severities": {}}
            summary[cat]["count"] += 1
            sev = rule["severity"]
            summary[cat]["severities"][sev] = summary[cat]["severities"].get(sev, 0) + 1
        return summary

    def _get_rule_by_id(self, rule_id: str) -> Optional[Dict]:
        """Look up a rule by its ID."""
        for rule in self._rules:
            if rule["id"] == rule_id:
                return rule
        return None

    def get_all_rules(self) -> List[Dict]:
        """Return all loaded rules."""
        return self._rules.copy()

    def __repr__(self) -> str:
        return (
            f"ComplianceChecker(rules={len(self._rules)}, "
            f"categories={self.get_categories()})"
        )
