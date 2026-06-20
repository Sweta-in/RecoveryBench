#!/usr/bin/env python3
"""
RecoveryBench — Promise Parser

Extracts payment promises and timelines from borrower messages.
Rule-based approach — no ML required.

Supports: English, Hindi/Hinglish, Bengali (romanized)

Usage:
    from pipeline.promise_parser import PromiseParser

    parser = PromiseParser()
    result = parser.extract("kal kar dunga payment")
    # {'promise_to_pay': True, 'payment_window_days': 1, 'raw_expression': 'kal'}
"""

import re
import logging
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PromiseParser:
    """
    Extract payment promises and timelines from borrower text.

    Strategy:
    1. Check for promise intent keywords (commitment language)
    2. Match temporal expressions from multilingual dictionary
    3. Fall back to dateparser for English date extraction
    4. Return structured promise result
    """

    # Temporal expression map: pattern -> payment_window_days
    TEMPORAL_MAP = {
        # English
        "tomorrow": 1,
        "day after tomorrow": 2,
        "next week": 7,
        "this weekend": 3,
        "this week": 5,
        "end of week": 5,
        "end of month": 30,
        "month end": 30,
        "next month": 30,
        "in 2 days": 2,
        "in two days": 2,
        "in 3 days": 3,
        "in three days": 3,
        "in a week": 7,
        "in a few days": 4,
        "within a week": 7,
        "within 2 days": 2,
        "within 3 days": 3,
        "by friday": 4,
        "by monday": 3,
        "by next friday": 7,
        "by next week": 7,
        "by end of month": 30,
        "by month end": 30,
        "after salary": 10,
        "when i get paid": 10,
        "after payday": 10,
        "next salary": 30,
        "today": 0,
        "tonight": 0,
        "this evening": 0,
        # Hindi / Hinglish
        "kal": 1,
        "aaj": 0,
        "parso": 2,
        "parson": 2,
        "is hafte": 7,
        "is week": 7,
        "agle hafte": 7,
        "agley hafte": 7,
        "next hafte": 7,
        "agle week": 7,
        "mahine mein": 30,
        "mahine me": 30,
        "month end tak": 30,
        "mahine ke end tak": 30,
        "month end pe": 30,
        "2 din mein": 2,
        "2 din me": 2,
        "do din mein": 2,
        "do din me": 2,
        "do din": 2,
        "teen din": 3,
        "teen din mein": 3,
        "3 din mein": 3,
        "3 din me": 3,
        "char din": 4,
        "4 din": 4,
        "ek hafte mein": 7,
        "ek hafte me": 7,
        "ek hafta": 7,
        "salary aane do": 10,
        "salary aane de": 10,
        "salary aaye": 10,
        "salary ke baad": 10,
        "salary milne pe": 10,
        "salary milegi": 10,
        "salary aayegi": 10,
        "jab salary aayegi": 10,
        "salary ashle": 10,
        "tankhwah aane do": 10,
        "tankhwah ke baad": 10,
        "weekend tak": 3,
        "weekend pe": 3,
        "weekend mein": 3,
        "abhi": 0,
        "abhi kar deta hun": 0,
        "aaj hi": 0,
        "aaj raat": 0,
        # Bengali (romanized)
        "kaal": 1,
        "aajke": 0,
        "ajke": 0,
        "porshuddin": 2,
        "shoptahe": 7,
        "shoptah e": 7,
        "agle shoptah": 7,
        "agami shoptah": 7,
        "mash sheshe": 30,
        "mash er shesh e": 30,
        "maas sheshe": 30,
        "month sheshe": 30,
        "dui din": 2,
        "dui din por": 2,
        "tin din": 3,
        "tin din por": 3,
        "char din por": 4,
        "ek shoptah": 7,
        "ek shoptah por": 7,
        "salary ashle": 10,
        "salary pele": 10,
        "salary aashle": 10,
        "beton pele": 10,
        "beton ashle": 10,
        "mash sesh e": 30,
        "shighroi": 2,
        "khub tara tari": 1,
        "porshu": 2,
        "agami maas": 30,
        # Hindi additions (approval notes)
        "agli salary": 30,
        "ek do din": 2,
        "jab paisa aayega": 10,
    }

    # Promise intent keywords — these indicate a commitment to pay
    PROMISE_KEYWORDS = [
        # English
        r"\bwill pay\b",
        r"\bi('|')?ll pay\b",
        r"\bgoing to pay\b",
        r"\bpromise to pay\b",
        r"\bwill settle\b",
        r"\bwill clear\b",
        r"\bwill transfer\b",
        r"\bwill send\b",
        r"\bwill deposit\b",
        r"\bcan pay\b",
        r"\bwill definitely pay\b",
        r"\blet me pay\b",
        r"\bi will do it\b",
        r"\bpay you\b",
        r"\bpay it\b",
        r"\bpay back\b",
        r"\brepay\b",
        r"\bwill make the payment\b",
        r"\bwill make payment\b",
        r"\bgive me time\b",
        r"\bgive me some time\b",
        r"\bneed some time\b",
        r"\bneed time\b",
        r"\bjust give me\b",
        # Hindi / Hinglish
        r"\bkar dunga\b",
        r"\bkarunga\b",
        r"\bkar denge\b",
        r"\bkarenge\b",
        r"\bkar deta hun\b",
        r"\bkar deta hoon\b",
        r"\bkar deti hun\b",
        r"\bkar deti hoon\b",
        r"\bbhej dunga\b",
        r"\bbhejunga\b",
        r"\bbhej denge\b",
        r"\btransfer kar dunga\b",
        r"\btransfer karunga\b",
        r"\bpayment kar dunga\b",
        r"\bpayment karunga\b",
        r"\bde dunga\b",
        r"\bdena hai\b",
        r"\bde denge\b",
        r"\bde deta hun\b",
        r"\bjama kar dunga\b",
        r"\bjama karunga\b",
        r"\bthoda time\b",
        r"\bthoda waqt\b",
        r"\btime do\b",
        r"\bwaqt do\b",
        r"\bpakka\b",
        r"\bpakka kar dunga\b",
        r"\bzaroor\b",
        # Bengali (romanized)
        r"\bdebo\b",
        r"\bkorbo\b",
        r"\bpathabo\b",
        r"\bpathiye debo\b",
        r"\bdiye debo\b",
        r"\btransfer korbo\b",
        r"\bpayment korbo\b",
        r"\bkore debo\b",
        r"\bkore dibo\b",
        r"\bpathiye dibo\b",
        r"\bjoma korbo\b",
        r"\bdiye dibo\b",
        r"\bsamay din\b",
        r"\bsamay dao\b",
        r"\bokthuku somoy\b",
        # Added via Checkpoint 3 approval notes
        r"\bho jayega\b",
        r"\bdal dunga\b",
    ]

    # Negative / negation patterns that cancel a promise
    NEGATION_PATTERNS = [
        r"\bwon'?t pay\b",
        r"\bwill not pay\b",
        r"\bnot going to pay\b",
        r"\bcan'?t pay\b",
        r"\bcannot pay\b",
        r"\brefuse to pay\b",
        r"\bnahi dunga\b",
        r"\bnahi karunga\b",
        r"\bnahi denge\b",
        r"\bnahi karenge\b",
        r"\bkabhi nahi\b",
        r"\bnever pay\b",
        r"\bdebo na\b",
        r"\bkorbo na\b",
        r"\bpay nahi\b",
        r"\bnot paying\b",
        r"\bdon'?t want to pay\b",
    ]

    # Conditional patterns — indicate conditional promise (still a promise but weaker)
    CONDITIONAL_PATTERNS = [
        r"\bagar\b.*\b(dunga|karunga|denge|karenge)\b",
        r"\bif\b.*\b(pay|transfer|send)\b",
        r"\bjab\b.*\b(aayegi|milegi|aaye)\b",
        r"\bwhen\b.*\b(get paid|salary|receive)\b",
        r"\bjodi\b.*\b(debo|korbo|pele)\b",
        r"\byodi\b.*\b(debo|korbo)\b",
        r"\bagar salary\b",
        r"\bif salary\b",
        r"\bjab salary\b",
    ]

    def __init__(self):
        """Initialize PromiseParser."""
        # Sort temporal patterns by length (longest first) for greedy matching
        self._temporal_patterns = sorted(
            self.TEMPORAL_MAP.items(),
            key=lambda x: len(x[0]),
            reverse=True,
        )

        # Pre-compile regex patterns
        self._promise_regexes = [re.compile(p, re.IGNORECASE) for p in self.PROMISE_KEYWORDS]
        self._negation_regexes = [re.compile(p, re.IGNORECASE) for p in self.NEGATION_PATTERNS]
        self._conditional_regexes = [re.compile(p, re.IGNORECASE) for p in self.CONDITIONAL_PATTERNS]

        # Try to import dateparser for English date fallback
        self._dateparser = None
        try:
            import dateparser
            self._dateparser = dateparser
            logger.debug("dateparser available for English date fallback")
        except ImportError:
            logger.debug("dateparser not available — using dictionary-only temporal extraction")

    def extract(self, text: str) -> dict:
        """
        Extract payment promise and timeline from borrower message.

        Args:
            text: Borrower message text.

        Returns:
            dict with keys:
                - promise_to_pay: bool
                - payment_window_days: int | None
                - raw_expression: str | None
        """
        if not text or not text.strip():
            return {
                "promise_to_pay": False,
                "payment_window_days": None,
                "raw_expression": None,
            }

        text_clean = text.strip()
        text_lower = text_clean.lower()

        # Step 1: Check for negation (cancels any promise)
        has_negation = any(r.search(text_lower) for r in self._negation_regexes)
        if has_negation:
            return {
                "promise_to_pay": False,
                "payment_window_days": None,
                "raw_expression": None,
            }

        # Step 2: Check for promise intent
        has_promise = any(r.search(text_lower) for r in self._promise_regexes)

        # Step 3: Check for conditional promise
        is_conditional = any(r.search(text_lower) for r in self._conditional_regexes)
        if is_conditional and not has_promise:
            has_promise = True

        # Step 4: Extract temporal expression
        temporal_days, raw_expr = self._extract_temporal(text_lower)

        # Step 5: Dateparser fallback for English dates
        if temporal_days is None and self._dateparser:
            dp_days, dp_expr = self._dateparser_fallback(text_clean)
            if dp_days is not None:
                temporal_days = dp_days
                raw_expr = dp_expr

        # Step 6: If temporal found but no explicit promise keyword,
        # still mark as promise (temporal implies intent)
        if temporal_days is not None and not has_promise:
            has_promise = True

        # Cap payment window at 90 days
        if temporal_days is not None and temporal_days > 90:
            temporal_days = 90

        return {
            "promise_to_pay": has_promise,
            "payment_window_days": temporal_days,
            "raw_expression": raw_expr,
        }

    def _extract_temporal(self, text_lower: str) -> tuple:
        """
        Match temporal expressions from the dictionary.

        Returns:
            (payment_window_days, raw_expression) or (None, None)
        """
        text_lower = text_lower.lower()
        for pattern, days in self._temporal_patterns:
            # Use word boundary-aware search
            # Build a regex that ensures we match the pattern as words
            escaped = re.escape(pattern)
            regex = re.compile(r'\b' + escaped + r'\b', re.IGNORECASE)
            match = regex.search(text_lower)
            if match:
                return days, match.group()

        # Also check for "N din/days/dino" patterns
        numeric_patterns = [
            (r'(\d+)\s*(?:din|dino?)\s*(?:mein|me|mai|baad|por)?', 'din'),
            (r'(\d+)\s*(?:days?)\s*(?:later|from now)?', 'days'),
            (r'(\d+)\s*(?:hafte|hafta|haftey)\s*(?:mein|me|mai|baad)?', 'weeks'),
            (r'(\d+)\s*(?:weeks?)\s*(?:later|from now)?', 'weeks'),
            (r'(\d+)\s*(?:mahine|mahiney|months?)\s*(?:mein|me|mai|baad)?', 'months'),
            (r'(\d+)\s*(?:shoptah)\s*(?:por)?', 'weeks'),
        ]
        for pat, unit in numeric_patterns:
            match = re.search(pat, text_lower)
            if match:
                num = int(match.group(1))
                if unit == 'weeks':
                    num *= 7
                elif unit == 'months':
                    num *= 30
                return num, match.group()

        return None, None

    def _dateparser_fallback(self, text: str) -> tuple:
        """
        Use dateparser to extract dates from English text.

        Returns:
            (payment_window_days, raw_expression) or (None, None)
        """
        try:
            result = self._dateparser.parse(
                text,
                settings={
                    'PREFER_DATES_FROM': 'future',
                    'RELATIVE_BASE': datetime.now(),
                }
            )
            if result is not None:
                delta = result - datetime.now()
                days = max(0, delta.days)
                if days <= 90:  # Only accept reasonable windows
                    return days, f"dateparser:{result.strftime('%Y-%m-%d')}"
            else:
                # dateparser returned None — text is not a recognizable date
                pass
        except Exception as e:
            logger.debug(f"dateparser failed: {e}")

        return None, None
