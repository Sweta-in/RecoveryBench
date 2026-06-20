#!/usr/bin/env python3
"""
RecoveryBench — Agent Evaluator (Phase 6)

LLM-as-judge scoring of agent responses in debt collection conversations.
Uses a multi-backend architecture: Ollama → HuggingFace → Claude → Rule-based fallback.

Usage:
    from pipeline.evaluator import AgentEvaluator

    evaluator = AgentEvaluator()
    result = evaluator.evaluate(
        borrower_message="Bhai salary nahi aayi abhi, next week kar dunga",
        intent="LIKELY_PAY",
        confidence=0.88,
        agent_response="Your account is seriously overdue. Pay immediately or legal action will be taken."
    )
    print(result)
"""

import json
import logging
import os
import re
import statistics
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Project paths
_PROJECT_ROOT = Path(__file__).parent.parent
_PROMPT_PATH = _PROJECT_ROOT / "prompts" / "agent_eval_prompt.txt"

# Rubric weights for overall_score calculation
RUBRIC_WEIGHTS = {
    "intent_accuracy": 0.30,
    "tone_score": 0.25,
    "compliance_score": 0.30,
    "escalation_score": 0.15,
}

# Rubric names for iteration
RUBRIC_NAMES = list(RUBRIC_WEIGHTS.keys())

# Backend priority order
BACKENDS = ["ollama", "huggingface", "claude", "groq", "rule_based"]

# --- Threat / violation keywords used by rule-based scorer ---
_THREAT_KEYWORDS = [
    "legal action", "police", "arrest", "jail", "fir karenge",
    "court", "lawyer", "sue", "warrant", "prosecution",
    "jail ho jayega", "police will come", "will arrest",
    "criminal case", "legal proceedings", "ghar aa jayenge",
]
_HARASSMENT_KEYWORDS = [
    "final warning", "last chance", "no more excuses",
    "don't test", "we know where you live", "your family",
    "employer", "neighbours", "shame", "publicly",
    "sabko bata denge", "ghar walo ko", "office mein",
]
_ABUSIVE_KEYWORDS = [
    "fraud", "cheat", "liar", "thief", "chor", "bewakoof",
    "idiot", "stupid", "useless", "shameless", "beiman",
    "pagal", "nalayak", "dhokhebaaz", "badmaash",
]
_COERCION_KEYWORDS = [
    "borrow from someone", "borrow from your", "sell your", "mortgage",
    "take a loan", "no choice", "must pay now",
    "immediately or", "right now or", "kisi se le lo",
    "abhi ke abhi", "fori taur pe", "relatives se",
    "friends se", "family se le",
]
_EMPATHY_KEYWORDS = [
    "understand", "appreciate", "difficult", "challenges",
    "help", "support", "flexible", "payment plan", "restructure",
    "samajhte", "madad", "sahuliyat", "mushkil",
]
_ESCALATION_APPROPRIATE = {
    "HIGH_RISK": ["senior", "specialist", "resolution", "supervisor", "manager"],
    "DISPUTE": ["dispute", "verification", "review", "investigate", "resolution"],
}


class AgentEvaluator:
    """
    LLM-as-judge evaluator for debt collection agent responses.

    Backends (tried in order):
      1. Ollama (local, free) — checks localhost:11434
      2. HuggingFace Inference API (free tier)
      3. Claude API (paid, last resort)
      4. Rule-based fallback (deterministic, always available)

    Attributes:
        backend (str): Name of the active backend.
        backend_model (str): Specific model name being used.
    """

    def __init__(self):
        """Initialize the evaluator, selecting the best available backend."""
        self._prompt_template = self._load_prompt()
        self.backend = None
        self.backend_model = None
        self._api_call_count = 0
        self._total_cost = 0.0

        # Try backends in priority order
        self._select_backend()

    def _load_prompt(self) -> str:
        """Load the evaluation prompt template from disk."""
        if not _PROMPT_PATH.exists():
            raise FileNotFoundError(
                f"Evaluation prompt not found: {_PROMPT_PATH}\n"
                "Expected at: prompts/agent_eval_prompt.txt"
            )
        return _PROMPT_PATH.read_text(encoding="utf-8")

    def _select_backend(self):
        """Try each backend in priority order and select the first available."""
        # 1. Try Ollama
        if self._check_ollama():
            return

        # 2. Try HuggingFace
        if self._check_huggingface():
            return

        # 3. Try Claude
        if self._check_claude():
            return

        # 4. Try Groq
        if self._check_groq():
            return

        # 5. Fall back to rule-based
        self.backend = "rule_based"
        self.backend_model = "deterministic_v1"
        logger.info(
            "No LLM backend available. Using rule-based evaluator. "
            "For LLM-based evaluation, start Ollama, set HF_TOKEN, set ANTHROPIC_API_KEY, or set GROQ_API_KEY."
        )

    def _check_ollama(self) -> bool:
        """Check if Ollama is running and has a suitable model."""
        try:
            import urllib.request
            import urllib.error

            url = "http://localhost:11434/api/tags"
            req = urllib.request.Request(url, method="GET")
            req.add_header("Accept", "application/json")

            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())

            models = [m.get("name", "") for m in data.get("models", [])]
            logger.info(f"Ollama available. Models: {models}")

            # Prefer these models in order
            preferred = [
                "qwen2.5:7b", "qwen2.5:latest", "qwen2.5",
                "phi3:mini", "phi3:latest", "phi3",
                "llama3.1:8b", "llama3.1:latest",
                "mistral:latest", "mistral:7b",
            ]
            for pref in preferred:
                for model in models:
                    if pref in model or model.startswith(pref.split(":")[0]):
                        self.backend = "ollama"
                        self.backend_model = model
                        logger.info(f"Selected Ollama model: {model}")
                        return True

            # Use any available model
            if models:
                self.backend = "ollama"
                self.backend_model = models[0]
                logger.info(f"Selected Ollama model (first available): {models[0]}")
                return True

            logger.debug("Ollama running but no models available")
            return False

        except Exception as e:
            logger.debug(f"Ollama not available: {e}")
            return False

    def _check_huggingface(self) -> bool:
        """Check if HuggingFace Inference API is available."""
        token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        if not token:
            logger.debug("No HuggingFace token found (HF_TOKEN or HUGGING_FACE_HUB_TOKEN)")
            return False

        try:
            from huggingface_hub import InferenceClient
            client = InferenceClient(token=token)
            # Quick test to verify the token works
            self.backend = "huggingface"
            self.backend_model = "Qwen/Qwen2.5-7B-Instruct"
            self._hf_client = client
            logger.info(f"HuggingFace Inference API available. Model: {self.backend_model}")
            return True
        except ImportError:
            logger.debug("huggingface_hub not installed")
            return False
        except Exception as e:
            logger.debug(f"HuggingFace API check failed: {e}")
            return False

    def _check_claude(self) -> bool:
        """Check if Claude API is available."""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.debug("No ANTHROPIC_API_KEY found")
            return False

        try:
            import anthropic
            self._anthropic_client = anthropic.Anthropic(api_key=api_key)
            self.backend = "claude"
            self.backend_model = "claude-haiku-3"
            logger.warning(
                "⚠️  Using PAID Claude API as evaluator backend. "
                "Cost: ~$0.25/1000 input + $1.25/1000 output tokens. "
                "Consider starting Ollama for free evaluation."
            )
            return True
        except ImportError:
            logger.debug("anthropic package not installed")
            return False
        except Exception as e:
            logger.debug(f"Claude API check failed: {e}")
            return False

    def _check_groq(self) -> bool:
        """Check if Groq API is available (free tier, fast inference)."""
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            logger.debug("No GROQ_API_KEY found")
            return False

        try:
            from groq import Groq
            self._groq_client = Groq(api_key=api_key)
            self.backend = "groq"
            self.backend_model = "llama-3.1-8b-instant"
            logger.info(
                f"Groq API available. Model: {self.backend_model}. "
                "Free tier — fast inference via Groq cloud."
            )
            return True
        except ImportError:
            logger.debug("groq package not installed (pip install groq)")
            return False
        except Exception as e:
            logger.debug(f"Groq API check failed: {e}")
            return False

    def _format_prompt(
        self,
        borrower_message: str,
        intent: str,
        confidence: float,
        agent_response: str,
    ) -> str:
        """Format the evaluation prompt with conversation context."""
        return self._prompt_template.format(
            borrower_message=borrower_message,
            intent=intent,
            confidence=confidence,
            agent_response=agent_response,
        )

    def evaluate(
        self,
        borrower_message: str,
        intent: str,
        confidence: float,
        agent_response: str,
    ) -> Dict:
        """
        Evaluate an agent response.

        Args:
            borrower_message: The borrower's message.
            intent: Detected intent class (e.g., 'LIKELY_PAY').
            confidence: Intent classification confidence (0-1).
            agent_response: The agent's response to evaluate.

        Returns:
            Dict with keys:
                - intent_accuracy (float, 0-10)
                - tone_score (float, 0-10)
                - compliance_score (float, 0-10)
                - escalation_score (float, 0-10)
                - overall_score (float, 0-10)
                - suggested_improvement (str)
        """
        if self.backend == "ollama":
            return self._evaluate_ollama(borrower_message, intent, confidence, agent_response)
        elif self.backend == "huggingface":
            return self._evaluate_huggingface(borrower_message, intent, confidence, agent_response)
        elif self.backend == "claude":
            return self._evaluate_claude(borrower_message, intent, confidence, agent_response)
        elif self.backend == "groq":
            return self._evaluate_groq(borrower_message, intent, confidence, agent_response)
        else:
            return self._evaluate_rule_based(borrower_message, intent, confidence, agent_response)

    # ─── LLM Backend Implementations ─────────────────────────────────────

    def _evaluate_ollama(self, borrower_message, intent, confidence, agent_response) -> Dict:
        """Evaluate using local Ollama."""
        import urllib.request

        prompt = self._format_prompt(borrower_message, intent, confidence, agent_response)
        payload = json.dumps({
            "model": self.backend_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 512},
        }).encode()

        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            method="POST",
        )
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
            raw_response = data.get("response", "")
            self._api_call_count += 1
            return self._parse_llm_response(raw_response, borrower_message, intent, confidence, agent_response)
        except Exception as e:
            logger.warning(f"Ollama evaluation failed: {e}. Falling back to rule-based.")
            return self._evaluate_rule_based(borrower_message, intent, confidence, agent_response)

    def _evaluate_huggingface(self, borrower_message, intent, confidence, agent_response) -> Dict:
        """Evaluate using HuggingFace Inference API."""
        prompt = self._format_prompt(borrower_message, intent, confidence, agent_response)

        try:
            response = self._hf_client.text_generation(
                prompt,
                model=self.backend_model,
                max_new_tokens=512,
                temperature=0.1,
            )
            self._api_call_count += 1
            return self._parse_llm_response(response, borrower_message, intent, confidence, agent_response)
        except Exception as e:
            logger.warning(f"HuggingFace evaluation failed: {e}. Falling back to rule-based.")
            return self._evaluate_rule_based(borrower_message, intent, confidence, agent_response)

    def _evaluate_claude(self, borrower_message, intent, confidence, agent_response) -> Dict:
        """Evaluate using Claude API (paid)."""
        prompt = self._format_prompt(borrower_message, intent, confidence, agent_response)

        try:
            message = self._anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=512,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            )
            raw_response = message.content[0].text
            self._api_call_count += 1
            # Estimate cost: ~500 input tokens + ~200 output tokens
            input_cost = 500 * 0.25 / 1_000_000
            output_cost = 200 * 1.25 / 1_000_000
            self._total_cost += input_cost + output_cost
            logger.info(
                f"Claude API call #{self._api_call_count}. "
                f"Estimated total cost: ${self._total_cost:.4f}"
            )
            return self._parse_llm_response(raw_response, borrower_message, intent, confidence, agent_response)
        except Exception as e:
            logger.warning(f"Claude evaluation failed: {e}. Falling back to rule-based.")
            return self._evaluate_rule_based(borrower_message, intent, confidence, agent_response)

    def _evaluate_groq(self, borrower_message, intent, confidence, agent_response) -> Dict:
        """Evaluate using Groq API (Llama 3.1 8B, free tier, ultra-fast)."""
        prompt = self._format_prompt(borrower_message, intent, confidence, agent_response)

        try:
            chat_completion = self._groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a senior quality analyst at a debt collection company. Respond ONLY with valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                model=self.backend_model,
                temperature=0.1,
                max_tokens=512,
            )
            raw_response = chat_completion.choices[0].message.content
            self._api_call_count += 1
            return self._parse_llm_response(raw_response, borrower_message, intent, confidence, agent_response)
        except Exception as e:
            logger.warning(f"Groq evaluation failed: {e}. Falling back to rule-based.")
            return self._evaluate_rule_based(borrower_message, intent, confidence, agent_response)

    # ─── Response Parsing ────────────────────────────────────────────────

    def _parse_llm_response(
        self,
        raw_response: str,
        borrower_message: str,
        intent: str,
        confidence: float,
        agent_response: str,
    ) -> Dict:
        """Parse LLM response into structured scores. Falls back to rule-based on failure."""
        try:
            # Try to extract JSON from response (may have preamble text)
            json_match = re.search(r'\{[^{}]*\}', raw_response, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON object found in response")

            result = json.loads(json_match.group())

            # Validate required fields
            required = {"intent_accuracy", "tone_score", "compliance_score",
                        "escalation_score", "overall_score", "suggested_improvement"}
            missing = required - set(result.keys())
            if missing:
                raise ValueError(f"Missing fields: {missing}")

            # Clamp scores to [0, 10]
            for key in RUBRIC_NAMES:
                result[key] = max(0.0, min(10.0, float(result[key])))

            # Recalculate overall_score using our weights (don't trust LLM arithmetic)
            result["overall_score"] = round(
                sum(result[k] * w for k, w in RUBRIC_WEIGHTS.items()), 2
            )

            return result

        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}. Raw: {raw_response[:200]}")
            return self._evaluate_rule_based(borrower_message, intent, confidence, agent_response)

    # ─── Rule-Based Evaluator ────────────────────────────────────────────

    def _evaluate_rule_based(
        self,
        borrower_message: str,
        intent: str,
        confidence: float,
        agent_response: str,
    ) -> Dict:
        """
        Deterministic rule-based evaluator — always available, zero cost.

        Uses keyword matching, compliance checking, and heuristics to produce
        scores. Designed to be conservative and align with the rubric definitions.
        """
        response_lower = agent_response.lower().strip() if agent_response else ""
        borrower_lower = borrower_message.lower().strip() if borrower_message else ""

        # ── Handle edge cases first ──
        if not response_lower:
            return {
                "intent_accuracy": 1.0,
                "tone_score": 1.0,
                "compliance_score": 1.0,
                "escalation_score": 1.0,
                "overall_score": 1.0,
                "suggested_improvement": "Agent response is empty. Provide a substantive response addressing the borrower's message.",
            }

        if len(response_lower.split()) <= 1:
            return {
                "intent_accuracy": 2.0,
                "tone_score": 2.0,
                "compliance_score": 5.0,  # One word is unlikely to violate anything
                "escalation_score": 2.0,
                "overall_score": round(2.0 * 0.3 + 2.0 * 0.25 + 5.0 * 0.3 + 2.0 * 0.15, 2),
                "suggested_improvement": "One-word responses are insufficient. Provide a detailed, empathetic response that addresses the borrower's specific situation.",
            }

        # ── Compliance scoring ──
        compliance_score = 10.0
        violations_found = []

        for keyword in _THREAT_KEYWORDS:
            if keyword in response_lower:
                compliance_score = min(compliance_score, 2.0)
                violations_found.append(f"threat: '{keyword}'")

        for keyword in _HARASSMENT_KEYWORDS:
            if keyword in response_lower:
                compliance_score = min(compliance_score, 3.0)
                violations_found.append(f"harassment: '{keyword}'")

        for keyword in _ABUSIVE_KEYWORDS:
            if keyword in response_lower:
                compliance_score = min(compliance_score, 2.5)
                violations_found.append(f"abusive_language: '{keyword}'")

        for keyword in _COERCION_KEYWORDS:
            if keyword in response_lower:
                compliance_score = min(compliance_score, 3.5)
                violations_found.append(f"coercion: '{keyword}'")

        # Cross-check with ComplianceChecker if available
        try:
            from pipeline.compliance import ComplianceChecker
            checker = ComplianceChecker()
            compliance_result = checker.check(agent_response)
            if not compliance_result["compliant"]:
                severity = compliance_result["severity"]
                severity_scores = {"critical": 1.5, "moderate": 3.5, "minor": 5.0}
                checker_score = severity_scores.get(severity, 4.0)
                compliance_score = min(compliance_score, checker_score)
                for v in compliance_result["violations"]:
                    violations_found.append(f"{v['category']}: {v.get('matched_text', v['rule_id'])}")
        except Exception as e:
            logger.debug(f"ComplianceChecker not available for cross-check: {e}")

        # ── Tone scoring ──
        tone_score = 6.0  # Start at slightly above adequate

        empathy_count = sum(1 for kw in _EMPATHY_KEYWORDS if kw in response_lower)
        if empathy_count >= 3:
            tone_score = min(tone_score + 3.0, 10.0)
        elif empathy_count >= 1:
            tone_score = min(tone_score + 1.5, 10.0)

        # Threatening/aggressive language reduces tone
        if compliance_score < 5:
            tone_score = min(tone_score, 3.0)

        # ALL CAPS detection
        caps_ratio = sum(1 for c in agent_response if c.isupper()) / max(len(agent_response), 1)
        if caps_ratio > 0.5 and len(agent_response) > 10:
            tone_score = max(tone_score - 3.0, 1.0)

        # Exclamation abuse
        if agent_response.count("!") >= 3:
            tone_score = max(tone_score - 1.5, 1.0)

        # Language mismatch penalty
        # Simple check: if borrower uses Hindi/Hinglish words but agent is pure English formal
        hindi_indicators = ["bhai", "kal", "dunga", "kar", "nahi", "abhi", "haan", "diya"]
        borrower_has_hindi = any(w in borrower_lower for w in hindi_indicators)
        agent_has_hindi = any(w in response_lower for w in hindi_indicators)
        if borrower_has_hindi and not agent_has_hindi and len(response_lower) > 20:
            # Mild penalty — not addressing in borrower's language context
            tone_score = max(tone_score - 0.5, 1.0)

        # ── Intent accuracy scoring ──
        intent_accuracy = 5.0  # Start at adequate

        # Check if response acknowledges key elements of borrower's message
        intent_response_alignment = {
            "LIKELY_PAY": {
                "good": ["thank", "noted", "follow", "confirm", "appreciate", "commitment", "noted your"],
                "bad": ["escalat", "legal", "final warning", "immediate", "serious"],
                "context": ["pay", "payment", "amount", "emi", "due"],
            },
            "NEEDS_REMINDER": {
                "good": ["remind", "details", "amount", "due date", "outstanding", "emi"],
                "bad": ["legal", "threat", "escalat", "final"],
                "context": ["due", "amount", "payment", "date"],
            },
            "DISPUTE": {
                "good": ["verify", "check", "review", "investigation", "look into", "records", "resolve"],
                "bad": ["pay immediately", "must pay", "no dispute", "ignore"],
                "context": ["dispute", "verify", "review", "records"],
            },
            "HIGH_RISK": {
                "good": ["understand", "frustration", "senior", "specialist", "resolution", "help"],
                "bad": ["don't care", "your problem"],
                "context": ["escalat", "senior", "specialist", "help"],
            },
            "VAGUE": {
                "good": ["clarif", "option", "specific", "plan", "help", "payment options"],
                "bad": ["legal", "threat", "must"],
                "context": ["option", "plan", "amount", "payment"],
            },
            "ALREADY_PAID": {
                "good": ["verify", "check", "confirm", "receipt", "records", "noted"],
                "bad": ["pay again", "must pay", "overdue", "immediately"],
                "context": ["payment", "confirm", "receipt", "records"],
            },
        }

        alignment = intent_response_alignment.get(intent, {})
        good_words = alignment.get("good", [])
        bad_words = alignment.get("bad", [])
        context_words = alignment.get("context", [])

        good_matches = sum(1 for w in good_words if w in response_lower)
        bad_matches = sum(1 for w in bad_words if w in response_lower)
        context_matches = sum(1 for w in context_words if w in response_lower)

        if good_matches >= 2:
            intent_accuracy = min(intent_accuracy + 3.0, 10.0)
        elif good_matches >= 1:
            intent_accuracy = min(intent_accuracy + 1.5, 10.0)

        if bad_matches >= 2:
            intent_accuracy = max(intent_accuracy - 4.0, 1.0)
        elif bad_matches >= 1:
            intent_accuracy = max(intent_accuracy - 2.0, 1.0)

        if context_matches >= 2:
            intent_accuracy = min(intent_accuracy + 1.0, 10.0)

        # ── Escalation scoring ──
        escalation_score = 6.0  # Start slightly above adequate

        escalation_words = ["escalat", "senior", "supervisor", "specialist", "manager",
                            "legal team", "resolution team", "higher authority"]
        has_escalation = any(w in response_lower for w in escalation_words)

        if intent in ("HIGH_RISK",):
            if has_escalation:
                escalation_score = 9.0
            else:
                escalation_score = 4.0  # Should have escalated

        elif intent in ("DISPUTE",):
            dispute_routing = any(w in response_lower for w in ["dispute", "verification", "review", "investigate"])
            if dispute_routing:
                escalation_score = 8.0
            elif has_escalation:
                escalation_score = 7.0
            else:
                escalation_score = 5.0

        elif intent in ("LIKELY_PAY", "ALREADY_PAID"):
            if has_escalation:
                escalation_score = 3.0  # Over-escalation
            else:
                follow_up = any(w in response_lower for w in ["follow", "noted", "reminder", "confirm"])
                if follow_up:
                    escalation_score = 9.0
                else:
                    escalation_score = 6.0

        elif intent == "NEEDS_REMINDER":
            if has_escalation:
                escalation_score = 4.0  # Over-escalation
            else:
                escalation_score = 7.0

        elif intent == "VAGUE":
            escalation_score = 6.0

        # ── Calculate overall score ──
        overall_score = round(
            intent_accuracy * RUBRIC_WEIGHTS["intent_accuracy"]
            + tone_score * RUBRIC_WEIGHTS["tone_score"]
            + compliance_score * RUBRIC_WEIGHTS["compliance_score"]
            + escalation_score * RUBRIC_WEIGHTS["escalation_score"],
            2,
        )

        # ── Generate improvement suggestion ──
        suggestion = self._generate_improvement(
            intent, compliance_score, tone_score, intent_accuracy,
            escalation_score, violations_found, borrower_message,
        )

        return {
            "intent_accuracy": round(intent_accuracy, 1),
            "tone_score": round(tone_score, 1),
            "compliance_score": round(compliance_score, 1),
            "escalation_score": round(escalation_score, 1),
            "overall_score": round(overall_score, 2),
            "suggested_improvement": suggestion,
        }

    def _generate_improvement(
        self,
        intent: str,
        compliance_score: float,
        tone_score: float,
        intent_accuracy: float,
        escalation_score: float,
        violations: List[str],
        borrower_message: str,
    ) -> str:
        """Generate a specific, actionable improvement suggestion."""
        suggestions = []

        if compliance_score < 5:
            violation_types = set(v.split(":")[0].strip() for v in violations)
            if "threat" in violation_types:
                suggestions.append(
                    "Remove all threats of legal action, police, or arrest — "
                    "these violate RBI Fair Practices Code and should be replaced "
                    "with constructive alternatives like offering a revised payment plan."
                )
            elif "harassment" in violation_types:
                suggestions.append(
                    "Remove references to contacting family, employer, or using shame tactics. "
                    "Focus the response on the borrower's account and available options."
                )
            elif "coercion" in violation_types:
                suggestions.append(
                    "Remove coercive language that pressures the borrower unduly. "
                    "Offer flexible payment options instead of demanding immediate payment."
                )
            else:
                suggestions.append(
                    "Review the response for potential compliance violations and remove "
                    "any threatening or inappropriate language."
                )

        if not suggestions and tone_score < 5:
            suggestions.append(
                "Adopt a more empathetic tone — acknowledge the borrower's situation "
                "before stating payment expectations. For example, start with "
                "'We understand...' or 'We appreciate you reaching out...'"
            )

        if not suggestions and intent_accuracy < 5:
            intent_tips = {
                "LIKELY_PAY": "Acknowledge the borrower's commitment to pay and confirm the timeline instead of restating the overdue amount.",
                "NEEDS_REMINDER": "Provide specific EMI details (amount, due date, account) to help the borrower take action.",
                "DISPUTE": "Acknowledge the dispute and offer to verify records instead of insisting on payment.",
                "HIGH_RISK": "De-escalate by acknowledging frustration and offering to connect with a senior resolution specialist.",
                "VAGUE": "Ask a specific clarifying question about payment capability instead of giving a generic reminder.",
                "ALREADY_PAID": "Offer to verify payment records and confirm receipt instead of treating as unpaid.",
            }
            tip = intent_tips.get(intent, "Tailor the response more specifically to the borrower's stated intent.")
            suggestions.append(tip)

        if not suggestions and escalation_score < 5:
            if intent in ("HIGH_RISK", "DISPUTE"):
                suggestions.append(f"For {intent} cases, consider routing to a specialist or senior agent for proper resolution.")
            else:
                suggestions.append("The escalation level seems inappropriate for this intent — adjust routing accordingly.")

        if not suggestions:
            # Response is good — give a refinement suggestion
            suggestions.append(
                "Consider adding a specific next-step or follow-up date to make the response more actionable."
            )

        return suggestions[0]

    # ─── Consistency Testing ─────────────────────────────────────────────

    def run_consistency_test(
        self,
        test_cases: List[Dict],
        runs: int = 3,
    ) -> Dict:
        """
        Run the same inputs multiple times and analyze score variance.

        Args:
            test_cases: List of dicts with keys:
                borrower_message, intent, confidence, agent_response
            runs: Number of evaluation runs per test case.

        Returns:
            Dict with:
                - per_case_results: list of {input, runs: list of scores, variance_per_rubric}
                - aggregate_variance: mean variance across all cases per rubric
                - flags: list of cases where variance > 1.5
        """
        results = []
        all_variances = {r: [] for r in RUBRIC_NAMES}

        for i, tc in enumerate(test_cases):
            run_scores = []
            for r in range(runs):
                score = self.evaluate(
                    borrower_message=tc["borrower_message"],
                    intent=tc["intent"],
                    confidence=tc["confidence"],
                    agent_response=tc["agent_response"],
                )
                run_scores.append(score)

            # Compute per-rubric variance
            variance = {}
            for rubric in RUBRIC_NAMES:
                values = [s[rubric] for s in run_scores]
                if len(values) > 1:
                    var = statistics.variance(values)
                else:
                    var = 0.0
                variance[rubric] = round(var, 4)
                all_variances[rubric].append(var)

            # Overall variance
            overall_values = [s["overall_score"] for s in run_scores]
            variance["overall_score"] = round(
                statistics.variance(overall_values) if len(overall_values) > 1 else 0.0, 4
            )

            results.append({
                "case_index": i,
                "input_summary": f"{tc['intent']} — {tc['borrower_message'][:50]}",
                "runs": run_scores,
                "variance_per_rubric": variance,
            })

        # Aggregate variance
        agg_variance = {}
        for rubric in RUBRIC_NAMES:
            vals = all_variances[rubric]
            agg_variance[rubric] = round(statistics.mean(vals) if vals else 0.0, 4)

        # Flag high-variance cases
        flags = []
        for res in results:
            variance_data = res.get("variance_per_rubric", {})
            if not isinstance(variance_data, dict):
                logger.warning(f"variance_per_rubric is not a dict for case {res.get('case_index')}, skipping")
                continue
            for rubric, var in variance_data.items():
                if var > 1.5:
                    flags.append({
                        "case_index": res["case_index"],
                        "rubric": rubric,
                        "variance": var,
                        "input_summary": res["input_summary"],
                    })

        return {
            "per_case_results": results,
            "aggregate_variance": agg_variance,
            "flags": flags,
            "backend": self.backend,
            "runs_per_case": runs,
        }

    # ─── Utility Methods ─────────────────────────────────────────────────

    def get_stats(self) -> Dict:
        """Return evaluator statistics."""
        return {
            "backend": self.backend,
            "backend_model": self.backend_model,
            "api_calls": self._api_call_count,
            "estimated_cost": round(self._total_cost, 4) if self._total_cost > 0 else 0,
        }

    def get_cost_per_1000(self) -> str:
        """Return estimated cost per 1000 evaluations."""
        if self.backend == "claude":
            return "$0.375 per 1000 evaluations (estimated)"
        elif self.backend in ("ollama", "rule_based"):
            return "$0.00 (free)"
        elif self.backend == "huggingface":
            return "$0.00 (free tier)"
        elif self.backend == "groq":
            return "$0.00 (free tier — Groq cloud)"
        return "Unknown"

    def __repr__(self) -> str:
        return (
            f"AgentEvaluator(backend={self.backend}, "
            f"model={self.backend_model}, "
            f"calls={self._api_call_count})"
        )


# ─── Module-level convenience ────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    e = AgentEvaluator()
    print(f"Backend: {e.backend} ({e.backend_model})")

    # Test evaluation
    result = e.evaluate(
        borrower_message="Bhai salary nahi aayi abhi, next week kar dunga",
        intent="LIKELY_PAY",
        confidence=0.88,
        agent_response="Your account is seriously overdue. Pay immediately or legal action will be taken.",
    )
    print("\nEvaluation result:")
    print(json.dumps(result, indent=2))

    assert "overall_score" in result
    assert result["compliance_score"] < 5, f"Expected compliance_score < 5, got {result['compliance_score']}"
    print("\n✓ Evaluator check: PASS")
