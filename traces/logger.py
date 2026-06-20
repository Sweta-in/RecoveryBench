#!/usr/bin/env python3
"""
RecoveryBench — Trace Logger

Structured trace logging for all API requests and pipeline executions.
Each trace is a JSON file stored in traces/logs/ with full request/response
data, timing, and metadata.

Supports:
  - Direct logging via TraceLogger.log()
  - Decorator pattern via @trace_call for function-level tracing

Usage:
    from traces.logger import TraceLogger, trace_call

    # Direct logging
    logger = TraceLogger()
    logger.log(
        request_id="abc123",
        endpoint="/analyze/text",
        request_data={"borrower_message": "kal kar dunga"},
        response_data={"repayment_intent": "LIKELY_PAY"},
        latency_ms=342.5,
        status="success",
    )

    # Decorator pattern
    @trace_call(endpoint="pipeline.analyze_text")
    def my_function(text):
        return {"result": "ok"}
"""

import os
import json
import time
import uuid
import logging
import functools
from pathlib import Path
from datetime import datetime
from typing import Optional, Any, Callable

logger = logging.getLogger(__name__)

# Default trace directory
TRACE_DIR = Path(__file__).parent / "logs"


class TraceLogger:
    """
    Persistent trace logger.

    Each trace is saved as a JSON file in the traces/logs/ directory
    with a unique filename based on timestamp and request ID.
    """

    def __init__(self, trace_dir: Optional[str] = None):
        """
        Initialize the trace logger.

        Args:
            trace_dir: Custom directory for trace files. Defaults to traces/logs/.
        """
        self.trace_dir = Path(trace_dir) if trace_dir else TRACE_DIR
        self.trace_dir.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        request_id: str,
        endpoint: str,
        request_data: dict,
        response_data: dict,
        latency_ms: float,
        status: str = "success",
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Log a trace entry.

        Args:
            request_id: Unique request identifier.
            endpoint: The API endpoint or function traced.
            request_data: Input data (request body, arguments).
            response_data: Output data (response body, return value).
            latency_ms: Processing time in milliseconds.
            status: "success" or "error".
            metadata: Optional additional metadata.

        Returns:
            The trace file path.
        """
        timestamp = datetime.utcnow()
        trace_id = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{request_id}"

        trace_entry = {
            "trace_id": trace_id,
            "request_id": request_id,
            "timestamp": timestamp.isoformat(),
            "endpoint": endpoint,
            "status": status,
            "latency_ms": round(latency_ms, 2),
            "request": self._safe_serialize(request_data),
            "response": self._safe_serialize(response_data),
            "metadata": metadata or {},
        }

        # Write trace file
        trace_filename = f"{trace_id}.json"
        trace_path = self.trace_dir / trace_filename

        try:
            with open(trace_path, "w", encoding="utf-8") as f:
                json.dump(trace_entry, f, indent=2, ensure_ascii=False, default=str)
            logger.debug(f"Trace saved: {trace_path}")
        except Exception as e:
            logger.warning(f"Failed to save trace: {e}")

        return str(trace_path)

    def list_traces(self, limit: int = 50) -> list:
        """
        List recent trace files.

        Args:
            limit: Maximum number of traces to return (newest first).

        Returns:
            List of trace metadata dicts (without full request/response).
        """
        trace_files = sorted(
            self.trace_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        traces = []
        for trace_file in trace_files[:limit]:
            try:
                with open(trace_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                traces.append({
                    "trace_id": data.get("trace_id"),
                    "timestamp": data.get("timestamp"),
                    "endpoint": data.get("endpoint"),
                    "status": data.get("status"),
                    "latency_ms": data.get("latency_ms"),
                    "file": str(trace_file),
                })
            except Exception:
                continue

        return traces

    def get_trace(self, trace_id: str) -> Optional[dict]:
        """
        Load a specific trace by trace_id.

        Args:
            trace_id: The trace_id to look up.

        Returns:
            Full trace dict or None if not found.
        """
        for trace_file in self.trace_dir.glob("*.json"):
            if trace_id in trace_file.stem:
                try:
                    with open(trace_file, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    return None
        return None

    def get_stats(self) -> dict:
        """
        Compute aggregate statistics over all traces.

        Returns:
            Dict with counts, latency stats, error rate, endpoint breakdown.
        """
        trace_files = list(self.trace_dir.glob("*.json"))
        total = len(trace_files)

        if total == 0:
            return {
                "total_traces": 0,
                "success_count": 0,
                "error_count": 0,
                "error_rate": 0.0,
                "avg_latency_ms": 0.0,
                "min_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "endpoints": {},
            }

        success_count = 0
        error_count = 0
        latencies = []
        endpoints = {}

        for trace_file in trace_files:
            try:
                with open(trace_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                status = data.get("status", "unknown")
                if status == "success":
                    success_count += 1
                else:
                    error_count += 1

                latency = data.get("latency_ms", 0)
                latencies.append(latency)

                ep = data.get("endpoint", "unknown")
                if ep not in endpoints:
                    endpoints[ep] = {"count": 0, "avg_latency_ms": 0.0, "latencies": []}
                endpoints[ep]["count"] += 1
                endpoints[ep]["latencies"].append(latency)

            except Exception:
                continue

        # Compute stats
        latencies.sort()
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        p95_idx = int(len(latencies) * 0.95)
        p95_latency = latencies[min(p95_idx, len(latencies) - 1)] if latencies else 0

        # Per-endpoint stats
        for ep in endpoints:
            ep_lats = endpoints[ep]["latencies"]
            endpoints[ep]["avg_latency_ms"] = round(sum(ep_lats) / len(ep_lats), 2)
            del endpoints[ep]["latencies"]  # Don't include raw latencies

        return {
            "total_traces": total,
            "success_count": success_count,
            "error_count": error_count,
            "error_rate": round(error_count / total, 4) if total > 0 else 0.0,
            "avg_latency_ms": round(avg_latency, 2),
            "min_latency_ms": round(min(latencies), 2) if latencies else 0.0,
            "max_latency_ms": round(max(latencies), 2) if latencies else 0.0,
            "p95_latency_ms": round(p95_latency, 2),
            "endpoints": endpoints,
        }

    @staticmethod
    def _safe_serialize(data: Any) -> Any:
        """Make data JSON-serializable by converting non-standard types."""
        if isinstance(data, dict):
            return {k: TraceLogger._safe_serialize(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [TraceLogger._safe_serialize(v) for v in data]
        elif isinstance(data, (str, int, float, bool, type(None))):
            return data
        else:
            return str(data)


def trace_call(endpoint: str = "unknown", trace_dir: Optional[str] = None):
    """
    Decorator for automatic trace logging of function calls.

    Usage:
        @trace_call(endpoint="pipeline.analyze_text")
        def analyze_text(borrower_message, agent_response=None):
            ...

    The decorator captures:
      - Function arguments as request_data
      - Return value as response_data
      - Execution time as latency_ms
      - Exceptions as error traces
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            trace_logger = TraceLogger(trace_dir=trace_dir)
            request_id = str(uuid.uuid4())[:8]

            # Capture input
            request_data = {
                "args": [str(a) for a in args],
                "kwargs": {k: str(v) for k, v in kwargs.items()},
            }

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.time() - start_time) * 1000

                trace_logger.log(
                    request_id=request_id,
                    endpoint=endpoint,
                    request_data=request_data,
                    response_data=result if isinstance(result, dict) else {"result": str(result)},
                    latency_ms=elapsed_ms,
                    status="success",
                )
                return result

            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                trace_logger.log(
                    request_id=request_id,
                    endpoint=endpoint,
                    request_data=request_data,
                    response_data={"error": str(e), "type": type(e).__name__},
                    latency_ms=elapsed_ms,
                    status="error",
                )
                raise

        return wrapper
    return decorator
