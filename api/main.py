#!/usr/bin/env python3
"""
RecoveryBench — FastAPI Backend

Production API for the RecoveryBench debt collection analysis platform.

Endpoints:
    GET  /health        → Health check with version
    GET  /metrics       → Model metadata, uptime, request counts
    POST /analyze/text  → Analyze borrower text + optional agent response
    POST /analyze/audio → Analyze audio file (multipart upload)

Usage:
    uvicorn api.main:app --host 0.0.0.0 --port 8000
"""

import sys
import os
import time
import uuid
import logging
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime

# Ensure project root is on path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# ── Logging Setup ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("recoverybench.api")

# ── App Metadata ───────────────────────────────────────────────────────
APP_VERSION = "1.0.0"
APP_START_TIME = time.time()

# ── FastAPI App ────────────────────────────────────────────────────────
app = FastAPI(
    title="RecoveryBench API",
    description=(
        "Multilingual AI debt collection agent evaluation platform. "
        "Analyze borrower messages, score agent responses, and check "
        "RBI compliance."
    ),
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request/Response Models ────────────────────────────────────────────

class TextAnalysisRequest(BaseModel):
    """Request body for POST /analyze/text."""
    borrower_message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The borrower's message text (1–1000 characters).",
        examples=["kal kar dunga bhai"],
    )
    agent_response: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional agent response to evaluate.",
        examples=["Please pay immediately."],
    )

    @field_validator("borrower_message")
    @classmethod
    def validate_borrower_message(cls, v: str) -> str:
        """Ensure borrower_message is not just whitespace."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("borrower_message must not be empty or whitespace-only")
        return stripped

    @field_validator("agent_response")
    @classmethod
    def validate_agent_response(cls, v: Optional[str]) -> Optional[str]:
        """Strip agent_response if provided."""
        if v is not None:
            stripped = v.strip()
            return stripped if stripped else None
        return v


class HealthResponse(BaseModel):
    """Response for GET /health."""
    status: str
    version: str
    timestamp: str


class MetricsResponse(BaseModel):
    """Response for GET /metrics."""
    uptime_seconds: float
    requests_served: int
    text_analyses: int
    audio_analyses: int
    version: str
    components: dict
    timestamp: str


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    code: int
    request_id: str


# ── Metrics State ──────────────────────────────────────────────────────

class _Metrics:
    """Simple in-memory metrics counter."""
    def __init__(self):
        self.requests_served = 0
        self.text_analyses = 0
        self.audio_analyses = 0

metrics = _Metrics()

# ── Analyzer Singleton ─────────────────────────────────────────────────

_analyzer = None


def get_analyzer():
    """Lazy-load the RecoveryBenchAnalyzer singleton."""
    global _analyzer
    if _analyzer is None:
        from pipeline.analyzer import RecoveryBenchAnalyzer
        _analyzer = RecoveryBenchAnalyzer()
        logger.info(f"RecoveryBenchAnalyzer initialized: {_analyzer}")
    return _analyzer


# ── Trace Integration ──────────────────────────────────────────────────

def _try_log_trace(request_id: str, endpoint: str, request_data: dict,
                   response_data: dict, latency_ms: float, status: str):
    """Attempt to log a trace — non-blocking if trace system unavailable."""
    try:
        from traces.logger import TraceLogger
        trace_logger = TraceLogger()
        trace_logger.log(
            request_id=request_id,
            endpoint=endpoint,
            request_data=request_data,
            response_data=response_data,
            latency_ms=latency_ms,
            status=status,
        )
    except ImportError:
        pass  # Trace system not yet built — skip silently
    except Exception as e:
        logger.debug(f"Trace logging failed (non-blocking): {e}")


# ── Middleware: Request ID ─────────────────────────────────────────────

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Attach a unique request ID to each request."""
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    metrics.requests_served += 1

    logger.info(
        f"[{request_id}] {request.method} {request.url.path}"
    )

    start = time.time()
    response = await call_next(request)
    elapsed_ms = (time.time() - start) * 1000

    logger.info(
        f"[{request_id}] → {response.status_code} ({elapsed_ms:.0f}ms)"
    )

    response.headers["X-Request-ID"] = request_id
    return response


# ── Endpoints ──────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse,
         summary="Health check",
         description="Returns API health status and version.")
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version=APP_VERSION,
        timestamp=datetime.utcnow().isoformat(),
    )


@app.get("/metrics", response_model=MetricsResponse,
         summary="API metrics",
         description="Returns uptime, request counts, and loaded components.")
async def get_metrics():
    """Metrics endpoint showing API statistics."""
    analyzer = get_analyzer()
    components = {
        "intent_classifier": analyzer._intent_classifier is not None,
        "promise_parser": analyzer._promise_parser is not None,
        "risk_scorer": analyzer._risk_scorer is not None,
        "compliance_checker": analyzer._compliance_checker is not None,
        "evaluator": analyzer._evaluator is not None,
    }

    return MetricsResponse(
        uptime_seconds=round(time.time() - APP_START_TIME, 2),
        requests_served=metrics.requests_served,
        text_analyses=metrics.text_analyses,
        audio_analyses=metrics.audio_analyses,
        version=APP_VERSION,
        components=components,
        timestamp=datetime.utcnow().isoformat(),
    )


@app.post("/analyze/text",
          summary="Analyze borrower text",
          description="Analyze a borrower message and optionally evaluate an agent response.")
async def analyze_text(
    request: Request,
    body: TextAnalysisRequest,
    evaluator: Optional[str] = Query(
        default=None,
        description="Override evaluator backend: 'rule_based', 'groq', or omit for default chain.",
    ),
):
    """
    Full text analysis pipeline:
      1. Language detection
      2. Intent classification
      3. Promise extraction
      4. Risk scoring
      5. Compliance check (if agent_response provided)
      6. Agent evaluation (if agent_response provided)

    Optional query param `evaluator` overrides the agent evaluator backend.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    start_time = time.time()

    try:
        analyzer = get_analyzer()

        # ── Evaluator override ──────────────────────────────────
        original_backend = None
        original_model = None
        if evaluator and analyzer._evaluator:
            original_backend = analyzer._evaluator.backend
            original_model = analyzer._evaluator.backend_model

            if evaluator == "rule_based":
                analyzer._evaluator.backend = "rule_based"
                analyzer._evaluator.backend_model = "deterministic_v1"
                logger.info(f"[{request_id}] Evaluator override: rule_based")
            elif evaluator == "groq":
                # Attempt to activate Groq for this request
                if not hasattr(analyzer._evaluator, '_groq_client') or analyzer._evaluator._groq_client is None:
                    # Try to initialize Groq on-the-fly
                    if analyzer._evaluator._check_groq():
                        logger.info(f"[{request_id}] Evaluator override: groq (initialized on demand)")
                    else:
                        logger.warning(f"[{request_id}] Groq requested but unavailable (no GROQ_API_KEY or groq package). Using default.")
                        # Restore original since _check_groq may have modified state
                        analyzer._evaluator.backend = original_backend
                        analyzer._evaluator.backend_model = original_model
                else:
                    analyzer._evaluator.backend = "groq"
                    analyzer._evaluator.backend_model = "llama-3.1-8b-instant"
                    logger.info(f"[{request_id}] Evaluator override: groq")

        result = analyzer.analyze_text(
            borrower_message=body.borrower_message,
            agent_response=body.agent_response,
        )

        # ── Restore original evaluator backend ──────────────────
        if original_backend is not None and analyzer._evaluator:
            analyzer._evaluator.backend = original_backend
            analyzer._evaluator.backend_model = original_model

        metrics.text_analyses += 1

        latency_ms = (time.time() - start_time) * 1000

        # Log trace
        _try_log_trace(
            request_id=request_id,
            endpoint="/analyze/text",
            request_data={
                "borrower_message": body.borrower_message,
                "agent_response": body.agent_response,
            },
            response_data=result,
            latency_ms=latency_ms,
            status="success",
        )

        return result

    except Exception as e:
        logger.error(f"[{request_id}] Analysis failed: {e}", exc_info=True)

        latency_ms = (time.time() - start_time) * 1000
        _try_log_trace(
            request_id=request_id,
            endpoint="/analyze/text",
            request_data={
                "borrower_message": body.borrower_message,
                "agent_response": body.agent_response,
            },
            response_data={"error": str(e)},
            latency_ms=latency_ms,
            status="error",
        )

        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "code": 500, "request_id": request_id},
        )


@app.post("/analyze/audio",
          summary="Analyze audio file",
          description="Upload an audio file (.wav, .mp3) for transcription and full analysis.")
async def analyze_audio(request: Request, file: UploadFile = File(...)):
    """
    Full audio analysis pipeline:
      1. Transcribe audio (Whisper ASR)
      2. Diarize speakers (Agent / Borrower)
      3. Run text analysis on extracted turns
    """
    request_id = getattr(request.state, "request_id", "unknown")
    start_time = time.time()

    # Validate file type
    allowed_extensions = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".webm"}
    if file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(allowed_extensions))}",
                    "code": 400,
                    "request_id": request_id,
                },
            )

    # Save uploaded file to temp location
    tmp_dir = project_root / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    suffix = Path(file.filename).suffix if file.filename else ".mp3"
    tmp_path = tmp_dir / f"upload_{request_id}{suffix}"

    try:
        content = await file.read()
        if not content:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Uploaded file is empty.",
                    "code": 400,
                    "request_id": request_id,
                },
            )

        with open(tmp_path, "wb") as f:
            f.write(content)

        analyzer = get_analyzer()
        result = analyzer.analyze_audio(str(tmp_path))
        metrics.audio_analyses += 1

        latency_ms = (time.time() - start_time) * 1000

        _try_log_trace(
            request_id=request_id,
            endpoint="/analyze/audio",
            request_data={
                "filename": file.filename,
                "size_bytes": len(content),
            },
            response_data=result,
            latency_ms=latency_ms,
            status="success",
        )

        return result

    except HTTPException:
        raise
    except RuntimeError as e:
        # Voice pipeline not available
        raise HTTPException(
            status_code=503,
            detail={
                "error": str(e),
                "code": 503,
                "request_id": request_id,
            },
        )
    except Exception as e:
        logger.error(f"[{request_id}] Audio analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Audio analysis failed: {str(e)}",
                "code": 500,
                "request_id": request_id,
            },
        )
    finally:
        # Clean up temp file
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


# ── Error Handlers ─────────────────────────────────────────────────────

@app.exception_handler(422)
async def validation_error_handler(request: Request, exc):
    """Return clean JSON for validation errors."""
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error — check request format and field constraints.",
            "code": 422,
            "request_id": request_id,
            "details": str(exc),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler — never leak tracebacks to clients."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"[{request_id}] Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "code": 500,
            "request_id": request_id,
        },
    )


# ── Run Directly ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False,
    )
