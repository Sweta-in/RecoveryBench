# RecoveryBench — Decision Log

## Phase 1 — Dataset Generation (2026-06-09)

### What was built
- Template-based multilingual dataset generator (`data/generate_data.py`)
- 1,000 unique templates across 5 classes × 4 languages (50 per combination)
- Comprehensive augmentation pipeline: casing, WhatsApp-style prefixes/suffixes, typo injection, punctuation variation
- Quality pipeline: exact dedup (MD5), near-dedup (SequenceMatcher, threshold=0.92), length filtering, language validation (langdetect)
- Stratified train/val/test split (70/15/15) by class × language
- EDA visualization script (`data/eda.py`) with 3 plot types
- Dataset card (`data/dataset_card.md`)

### Key decisions
1. **Template-based over LLM-generated:** No local Ollama available and no paid APIs allowed in core pipeline. Template-based approach with 50 diverse templates per class×language provides deterministic, reproducible generation.
2. **Near-duplicate threshold raised to 0.92:** Original threshold of 0.85 was too aggressive for template-generated data, removing 56% of records. At 0.92, removal rate is ~30% — still catches true duplicates but preserves legitimate template variations.
3. **Target of 300 per class×language:** Over-generates to survive dedup pipeline. Final yield: 3,268 rows from 6,000 generated.
4. **Language validation flags but doesn't remove:** langdetect is unreliable for Romanized Hindi/Bengali and Hinglish code-mixing. Flagged rows are kept but logged for review.
5. **Augmentation strategy:** Mimics real WhatsApp message patterns — typos, emoji, casing variation, filler words. This increases surface diversity even from a template base.

### Metrics
- **Total rows:** 3,268 (target: 4,000+)
- **Train:** 2,279 | **Val:** 480 | **Test:** 509
- **Class balance:** 16.7%–24.8% (DISPUTE lowest, VAGUE highest)
- **Language balance:** 24.2%–26.7% (Hindi lowest, Bengali highest)
- **All classes have 100+ per language in train** ✓

### Known limitations
- Total below 4,000 target due to near-duplicate removal rate
- VAGUE class has more surviving templates (shorter messages pass dedup more easily)
- Synthetic data — does not capture real borrower communication patterns
- Romanized Bengali is a simplification

---

## Checkpoint 2 Approval — ALREADY_PAID Downstream Rule (2026-06-10)

### Decision
Checkpoint 2 APPROVED WITH NOTES. The model is treated as a **5-class classifier**. ALREADY_PAID will NOT be retrained — instead, it will be handled as a **downstream rule in the pipeline analyzer**.

### Rule specification
If the borrower message contains past-tense payment confirmation keywords, override the classifier output to ALREADY_PAID:
- English: `"already paid"`, `"payment was"`, `"transferred"`, `"paid already"`
- Hindi/Hinglish: `"kar diya"`, `"de diya"`, `"bhej diya"`, `"transfer ho gaya"`, `"jama ho gaya"`
- Bengali: `"diye diyechi"`, `"kore diyechi"`, `"transfer korechi"`

### Rationale
- The ALREADY_PAID class was absent from training data (Checkpoint 1 dataset issue)
- The model achieves ~0.90 macro F1 on the 5 trained classes
- Retraining is blocked by governance rules (dataset must not be touched)
- A keyword-based override is deterministic, auditable, and handles the most common ALREADY_PAID patterns

### Impact
- `pipeline/analyzer.py` will apply this override between intent classification (step 2) and promise extraction (step 3)
- The override fires only when keyword match confidence is high (exact substring match)
- If override fires, `intent_confidence` is set to 1.0 to indicate rule-based classification

---

## Phase 3 — Promise Parser (2026-06-10)

### What was built
- `pipeline/promise_parser.py` — rule-based promise and timeline extraction
- `tests/test_promise_parser.py` — 50 validation examples + 5 basic tests (55 total)

### Key decisions
1. **Rule-based over ML:** Promise extraction is a pattern-matching problem. Temporal expressions are finite and language-specific. A dictionary-based approach with regex promise detection is more reliable, interpretable, and maintainable than a trained model.
2. **Three-layer extraction strategy:**
   - Layer 1: Negation check (cancels any promise immediately)
   - Layer 2: Promise intent keywords (commitment language like "kar dunga", "will pay", "debo")
   - Layer 3: Temporal expression matching (dictionary + numeric pattern extraction)
3. **Temporal implies promise:** If a temporal expression is found (e.g., "kal", "tomorrow") even without an explicit promise keyword, we mark `promise_to_pay: True`. Rationale: if a borrower mentions a timeframe in response to a payment reminder, it implies commitment.
4. **Conditional promises count as promises:** "agar salary aaye toh kar dunga" is marked as a promise. The conditional nature is captured in the temporal window (salary-contingent = 10 days).
5. **dateparser as fallback:** Used for English date expressions that aren't in the dictionary (e.g., "by June 15th"). Falls back gracefully if dateparser is unavailable.
6. **Payment window capped at 90 days:** Any temporal expression resolving to > 90 days is capped to prevent unrealistic windows.

### Metrics
- **Test pass rate:** 55/55 = **100%** (50 validation + 5 basic tests)
- **All 3 governance verify commands:** PASSED
- **Temporal dictionary:** 95+ entries across English, Hindi/Hinglish, Bengali
- **Promise keywords:** 45+ patterns across 3 language families
- **Negation patterns:** 17 patterns for explicit refusals

### Checkpoint 3 Approval Notes (2026-06-10)
Added per reviewer direction:
- **5 temporal patterns:** `porshu` (2), `agami maas` (30), `agli salary` (30), `ek do din` (2), `jab paisa aayega` (10)
- **2 promise keywords:** `ho jayega`, `dal dunga`

### Known limitations
- Romanized Bengali has high spelling variation — not all variants are covered
- dateparser can be over-eager on English text (may extract dates from non-temporal contexts)
- No handling of relative date arithmetic ("next Tuesday" → depends on current day)
- Conditional promises are treated the same as unconditional ones
- **Third-person "will pay" false positive risk:** The pattern `\bwill pay\b` matches regardless of subject pronoun. Input like "they will pay, not me" would incorrectly trigger `promise_to_pay: True`. This is a known limitation — not blocking for Checkpoint 4, but should be addressed if production data shows frequent third-person messages.

---

## Phase 4 — Risk Scorer (2026-06-10)

### What was built
- `pipeline/risk_scorer.py` — XGBoost regressor producing 0–1 risk scores from 9 conversation features
- `tests/test_risk_scorer.py` — 28 tests covering ordering, bands, feature extraction, batch scoring, edge cases
- `models/risk_scorer/xgb_model.json` — trained model (161.3 KB)
- `models/risk_scorer/shap_importance.png` — feature importance plot (XGBoost fallback)
- `models/risk_scorer/shap_summary.json` — feature importance values

### Key decisions
1. **Intent-encoded as ordinal feature:** LIKELY_PAY=0, NEEDS_REMINDER=1, VAGUE=2, DISPUTE=3, HIGH_RISK=4. This ordinal encoding naturally maps to increasing risk and dominates model behavior (74.7% importance).
2. **Synthetic training labels:** Base risk scores per class (0.15–0.92) with ±0.08 Gaussian noise and feature-based adjustments. This is sufficient for a first-pass scorer but would need real-world calibration data for production.
3. **XGBoost over linear model:** Tree-based model captures non-linear interactions between features (e.g., hostile_keywords amplifies risk more for HIGH_RISK than LIKELY_PAY).
4. **SHAP fallback:** SHAP 0.49.x has a known incompatibility with the installed XGBoost version. The importance plot is generated from XGBoost's native `feature_importances_` (gain-based) instead. Functionally equivalent for tree models.
5. **Public `train()` method added:** Enables on-demand retraining to regenerate model artifacts.

### Checkpoint 4 Approval Notes (2026-06-10)

Per reviewer direction:

1. **Risk scorer is intent-dominant (74.7% weight on `intent_encoded`).** The compliance engine and all downstream components MUST treat the risk score as correlated with intent, NOT as an independent signal. If the intent classifier is wrong, the risk score will also be wrong.

2. **ALREADY_PAID hardcoded risk override:** When the ALREADY_PAID keyword rule fires in `pipeline/analyzer.py`, set `risk_score = 0.05` hardcoded — do NOT pass through the XGBoost scorer. Rationale: XGBoost has no ALREADY_PAID training signal (maps to LIKELY_PAY encoding=0, but the semantic meaning is different).

3. **SHAP incompatibility acknowledged — not blocking.** Do not attempt to fix in future checkpoints. The XGBoost importance plot is functionally equivalent.

### Metrics
- **28 tests:** all passed
- **Ordering check:** LIKELY_PAY (0.078) < NEEDS_REMINDER (0.406) < VAGUE (0.611) < DISPUTE (0.712) < HIGH_RISK (1.000)
- **No failure cases:** no LIKELY_PAY above 0.5, no HIGH_RISK below 0.5
- **Training data:** 2,279 samples from train.csv

### Known limitations
- Feature dominance: intent_encoded accounts for 74.7%, next two features (hostile_keywords 12.2%, has_promise 10.6%) account for most of the rest. The remaining 6 features collectively contribute only 2.5%.
- Synthetic labels — not calibrated against real-world outcomes
- ALREADY_PAID requires hardcoded override (no training signal)

---

## Phase 5 — Compliance Engine (2026-06-10)

### What was built
- `rules/compliance_rules.json` — 25 rules with 233 patterns across 5 categories, all grounded in RBI Fair Practices Code
- `pipeline/compliance.py` — ComplianceChecker engine with case-insensitive substring matching, pre-compiled regex, batch support
- `tests/test_compliance.py` — 60 tests covering rules validation, violation detection (all 5 categories), compliant messages, severity, edge cases, pipeline integration

### Key decisions
1. **Substring matching over semantic similarity:** Pattern-based matching is deterministic, auditable, and zero-cost. Semantic approaches (embedding similarity) would improve recall but add ML dependencies and non-determinism. Pattern-based is correct for Phase 5; semantic can be layered later.
2. **Pre-compiled regex for patterns:** Each pattern string is `re.escape()`d and compiled with `re.IGNORECASE` at init time. This avoids repeated compilation on every `check()` call.
3. **One match per rule, first match wins:** If multiple patterns from the same rule match, only the first is reported. This prevents a single rule from dominating the violations list.
4. **Highest-severity rewrite returned:** When multiple rules are violated, the suggested rewrite from the highest-severity violation is returned. Composite rewrites are deferred to future work.
5. **Rules fully separated from logic:** All patterns, descriptions, and rewrites live in `compliance_rules.json`. The Python engine is pure logic — no hardcoded patterns. This allows rule updates without code changes.
6. **5 categories, 5 rules each (minimum):** Matches the governance spec requirement. Categories: threats, harassment, abusive_language, coercion, false_claims.

### Metrics
- **25 rules** across 5 categories (governance minimum: 20 ✓)
- **233 patterns** total across all rules
- **60 tests** — all passed
- **Both governance verify commands** — PASSED
- **0 false positives** on compliant message suite
- **Suggested rewrites** — all 25 rules have usable rewrites

### Known limitations
- Substring matching cannot detect semantic paraphrasing (e.g., "accidents happen" as an implicit threat)
- Single-message analysis only — cannot detect escalation patterns across conversation turns
- Romanized Hindi/Bengali spelling variants are not exhaustively covered
- "cibil" variants missing from credit score rule (RBI_004 uses "credit score kharab" but agents commonly say "cibil")
- No multi-turn context — repeated borderline messages that collectively constitute harassment are not detected

---

## Phase 6 — Agent Evaluator (2026-06-10)

### What was built
- `pipeline/evaluator.py` — multi-backend LLM-as-judge evaluator (Ollama → HuggingFace → Claude → rule-based fallback)
- `prompts/agent_eval_prompt.txt` — structured evaluation prompt template
- `tests/test_evaluator.py` — 95+ tests covering all backends, parsing, consistency
- `scripts/run_consistency_test.py` — variance analysis tool

### Key decisions
1. **Rule-based fallback always available:** Deterministic evaluator using keyword matching, compliance cross-check, and heuristics. Zero cost, zero latency, always works.
2. **Weighted rubric:** intent_accuracy (30%), compliance_score (30%), tone_score (25%), escalation_score (15%). Compliance weighted equally with intent accuracy to enforce RBI compliance.
3. **Intent-aware scoring:** Each intent class has its own set of "good" and "bad" response patterns. A response that escalates a LIKELY_PAY borrower is penalized, while the same escalation for HIGH_RISK is rewarded.
4. **Consistency testing built in:** `run_consistency_test()` runs N evaluations and computes variance per rubric. Flags any rubric with variance > 1.5.

---

## Checkpoint 7 — RecoveryBench-100 Benchmark Suite (2026-06-12)

### What was built
- `benchmarks/generate_benchmark.py` — hand-crafted 100 benchmark scenarios
- `benchmarks/recoverybench_100.json` — the benchmark dataset (45.7 KB)
- `benchmarks/run_benchmark.py` — full pipeline benchmark runner with 3 output formats
- `benchmarks/results/benchmark_scores.json` — per-scenario results
- `benchmarks/results/benchmark_summary.json` — aggregate statistics
- `benchmarks/results/benchmark_report.md` — human-readable report

### Key decisions
1. **Hand-crafted over LLM-generated:** All 100 scenarios are manually written to ensure precise intent labeling and scenario category coverage. LLM generation would introduce label noise.
2. **15 scenario categories:** Covering straightforward, temporal/conditional promises, language switching, emotional distress, aggressive refusal, legitimate/evasion disputes, vague non-committal, already-paid claims, partial payment, short messages, formal English, colloquial Hindi, romanized Bengali.
3. **Component-level benchmarking:** Runner loads each pipeline component independently and benchmarks them separately (intent accuracy, promise accuracy, risk bands, compliance, agent eval). This isolates failures.
4. **Markdown report alongside JSON:** Added `benchmark_report.md` generation for human review without parsing JSON.

### Results
- **Intent accuracy:** 82% overall (LIKELY_PAY: 100%, HIGH_RISK: 85%, VAGUE: 85%, DISPUTE: 75%, NEEDS_REMINDER: 65%)
- **Promise accuracy:** 85% (window close match: 100%)
- **Hardest category:** short_message (40%) — inherently ambiguous
- **18 misclassifications** — dominated by NEEDS_REMINDER↔VAGUE confusion on short messages

### Known issues
- Language distribution not perfectly balanced (English: 38, Hindi: 31, Hinglish: 21, Bengali: 10)
- ALREADY_PAID keyword rule conflicts with 2 DISPUTE benchmark labels (RB-054, RB-060)
- NEEDS_REMINDER vs VAGUE boundary is genuinely ambiguous for short messages

---

## Phase 7 — Voice Pipeline (2026-06-12)

### What was built
- `voice/diarize.py` — speaker diarization with pyannote primary backend and sentence-alternation fallback
- `voice/pipeline.py` — end-to-end orchestrator: audio → ASR → diarize → RecoveryBenchAnalyzer.analyze_text()
- `tests/test_audio.mp3` — gTTS-generated Hindi test audio
- `docs/checkpoints/checkpoint_8_voice_review.md` — checkpoint report

### Key decisions
1. **Whisper `base` model (139MB):** Balances accuracy vs. resource consumption on CPU. The `small` (460MB) and `medium` (1.5GB) options are available via constructor parameter but `base` is the default for CPU-only environments.
2. **Fallback diarization with prominent warning:** pyannote.audio is not installed on this machine and requires a HuggingFace token. Rather than failing, the diarizer falls back to sentence-alternation heuristic with a `warnings.warn()` + logger warning on every instantiation. The warning is impossible to miss.
3. **First speaker = Agent convention:** In pyannote mode, the first detected speaker is mapped to "Agent" (debt collector initiates the call). This is a reasonable assumption for outbound collection calls but would need reversal for inbound.
4. **Single-speaker graceful handling:** If diarization produces no "Borrower" turns (e.g., single-speaker test audio), the full transcript is treated as borrower input. This prevents pipeline crashes on mono audio.
5. **ffmpeg as system dependency:** Whisper requires ffmpeg for audio decoding. Installed via `winget install Gyan.FFmpeg` on this Windows machine. Documented in checkpoint report setup steps.

### Metrics
- **End-to-end latency:** 1.94s for 4.5s audio (0.43x realtime on CPU)
- **Extrapolated 30s latency:** ~13s
- **Transcript accuracy:** Whisper correctly transcribed Hindi gTTS audio
- **Intent classification:** LIKELY_PAY with 96.5% confidence (correct)
- **Both governance verify commands:** PASSED

### Known limitations
- Diarization is in fallback mode (heuristic) — speaker attribution is unreliable
- Promise parser has case-sensitivity issue with Whisper output ("Aagle" vs "agle")
- Single-speaker test audio — cannot validate two-speaker diarization alignment
- CPU-only Whisper — production workloads with long audio would benefit from GPU

---

## Post-Completion Enhancement — Custom Frontend (2026-06-18)

### What was built
- `frontend/index.html` — single-page application with semantic HTML5, Inter + JetBrains Mono fonts, SVG risk gauge
- `frontend/styles.css` — dark-mode design system (17 KB) with CSS custom properties, glassmorphism cards, micro-animations
- `frontend/app.js` — vanilla JavaScript (no framework) connecting to FastAPI backend at `localhost:8000`

### Key decisions
1. **Vanilla HTML/CSS/JS over framework:** No React/Vue/Svelte overhead. The frontend is a static analysis dashboard with one API call — a framework would add complexity without benefit. Ship as 3 files that work by opening `index.html` in a browser.
2. **Dark-mode-first design:** Dark theme with `#0f172a` base, indigo/purple gradients, and glassmorphism card effects. Color palette uses HSL-tuned values (`--good: #22c55e`, `--warn: #f59e0b`, `--risk: #ef4444`) for accessibility-aware red/yellow/green semantics.
3. **SVG risk gauge:** Custom SVG ring gauge using `stroke-dashoffset` animation. Fills proportionally to `risk_score` with dynamic color transitions (green → amber → red → critical).
4. **Pipeline trace animation:** Sequential reveal of 6 pipeline steps during the API call, running in parallel with `fetch()`. Gives visual feedback even before results arrive.
5. **Evaluator selector in header:** Dropdown to override evaluator backend via `?evaluator=` query param. Options: Auto (default chain), Groq (Llama 3.1 8B), Rule-based (deterministic).
6. **Example chips:** 4 pre-built example conversations (Likely Pay + Threat, Dispute, Needs Reminder, High Risk + Good Agent) for instant demo without typing.

### Architecture
- Frontend is purely static — no build step, no bundler, no node_modules
- Communicates with FastAPI via CORS-enabled `POST /analyze/text`
- All DOM references use `getElementById()` with unique, descriptive IDs
- State management: 3 states (empty, error, results) toggled via `.hidden` class

### Known limitations
- Hardcoded `API_BASE = "http://localhost:8000"` — would need env injection for production
- No audio analysis tab (text-only for now)
- No offline mode — requires running API backend

---

## Post-Completion Enhancement — Groq LLM Backend (2026-06-18)

### What was built
- Extended `pipeline/evaluator.py` with `_check_groq()` and `_evaluate_groq()` methods
- Added Groq to the backend priority chain: Ollama → HuggingFace → Claude → **Groq** → rule-based
- `api/main.py` — added `?evaluator=groq` query param override with on-demand initialization
- `tests/test_groq_evaluator.py` — 17 tests covering backend discovery, availability, evaluation flow, cost reporting, API override, and CORS
- `requirements.txt` — added `groq>=1.0.0`

### Key decisions
1. **Groq after Claude in priority order:** Groq's free tier is excellent for development but has rate limits. In production, Ollama (local) and HuggingFace (free API) should be tried first. Claude (paid but highly reliable) comes before Groq. Groq is the last LLM option before rule-based fallback.
2. **Model choice: `llama-3.1-8b-instant`:** Groq hosts several models; Llama 3.1 8B is the fastest on their infrastructure and performs well as a judge for this rubric-based evaluation task.
3. **System prompt injection:** Unlike other backends that use a single user prompt, the Groq path uses a system message ("You are a senior quality analyst...") + user message pattern. This improves structured JSON output reliability.
4. **Graceful fallback on Groq failure:** If the Groq API call fails (rate limit, network, etc.), the evaluator falls back to rule-based with a warning log. No user-visible error.
5. **On-demand initialization in API:** The `?evaluator=groq` query param can activate Groq even if it wasn't the default backend at startup. The API calls `_check_groq()` on first groq-override request if the client hasn't been initialized yet.

### Cost
- Groq free tier: $0.00 — 14,400 requests/day, 30 requests/minute
- No paid API keys required for Groq (free sign-up at console.groq.com)

### Test coverage
- 17 new tests in `test_groq_evaluator.py`
- All use mocks for the Groq client (no real API key needed in CI)
- Total test count after this addition: **236 passing**

---

## Post-Completion Enhancement — CORS Middleware (2026-06-18)

### What was built
- Added `CORSMiddleware` to `api/main.py` with permissive development settings
- 3 CORS-specific tests in `test_groq_evaluator.py`

### Key decisions
1. **`allow_origins=["*"]`:** Required for the static frontend (opened via `file://` or a local dev server) to communicate with the FastAPI backend on `localhost:8000`. In production, this should be restricted to the actual frontend origin.
2. **`allow_methods=["*"]`, `allow_headers=["*"]`:** Full permissiveness for development. The frontend only uses POST with `Content-Type: application/json`, but allowing all methods prevents CORS preflight issues during development.
3. **`allow_credentials=True`:** Not strictly needed now (no auth), but included for forward compatibility if session-based auth is added later.

### Security note
- The `*` origin policy is appropriate for local development and demo environments
- For any public deployment, restrict `allow_origins` to the specific frontend domain


