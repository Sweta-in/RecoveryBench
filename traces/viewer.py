#!/usr/bin/env python3
"""
RecoveryBench — Trace Viewer CLI

CLI tool for inspecting API traces.

Subcommands:
    list    — List recent traces (newest first)
    inspect — Show full details of a specific trace
    stats   — Show aggregate statistics

Usage:
    python traces/viewer.py list [--limit N]
    python traces/viewer.py inspect <trace_id>
    python traces/viewer.py stats
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional

# Ensure project root is on path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from traces.logger import TraceLogger


def cmd_list(args):
    """List recent traces."""
    trace_logger = TraceLogger(trace_dir=args.trace_dir)
    traces = trace_logger.list_traces(limit=args.limit)

    if not traces:
        print("No traces found.")
        return

    print(f"\n{'='*80}")
    print(f"  RECENT TRACES ({len(traces)} of {len(list(Path(args.trace_dir).glob('*.json')))} total)")
    print(f"{'='*80}\n")

    # Table header
    print(f"  {'#':<4} {'Timestamp':<22} {'Endpoint':<22} {'Status':<9} {'Latency':<10}")
    print(f"  {'─'*4} {'─'*22} {'─'*22} {'─'*9} {'─'*10}")

    for i, trace in enumerate(traces, 1):
        ts = trace.get("timestamp", "?")[:19]
        ep = trace.get("endpoint", "?")[:20]
        status = trace.get("status", "?")
        latency = trace.get("latency_ms", 0)

        status_icon = "✓" if status == "success" else "✗"
        print(f"  {i:<4} {ts:<22} {ep:<22} {status_icon} {status:<6} {latency:>7.1f}ms")

    print(f"\n  Use 'viewer.py inspect <trace_id>' for details.\n")

    # Show trace IDs for reference
    print(f"  Trace IDs:")
    for trace in traces[:10]:
        tid = trace.get("trace_id", "?")
        print(f"    {tid}")
    print()


def cmd_inspect(args):
    """Inspect a specific trace."""
    trace_logger = TraceLogger(trace_dir=args.trace_dir)
    trace = trace_logger.get_trace(args.trace_id)

    if trace is None:
        print(f"Trace not found: {args.trace_id}")
        sys.exit(1)

    print(f"\n{'='*80}")
    print(f"  TRACE: {trace.get('trace_id', '?')}")
    print(f"{'='*80}\n")

    # Summary
    print(f"  Timestamp:  {trace.get('timestamp', '?')}")
    print(f"  Request ID: {trace.get('request_id', '?')}")
    print(f"  Endpoint:   {trace.get('endpoint', '?')}")
    print(f"  Status:     {trace.get('status', '?')}")
    print(f"  Latency:    {trace.get('latency_ms', 0):.2f} ms")
    print()

    # Request
    print(f"  ── REQUEST {'─'*66}")
    request_data = trace.get("request", {})
    print(json.dumps(request_data, indent=4, ensure_ascii=False, default=str))
    print()

    # Response
    print(f"  ── RESPONSE {'─'*65}")
    response_data = trace.get("response", {})
    print(json.dumps(response_data, indent=4, ensure_ascii=False, default=str))
    print()

    # Metadata
    metadata = trace.get("metadata", {})
    if metadata:
        print(f"  ── METADATA {'─'*65}")
        print(json.dumps(metadata, indent=4, ensure_ascii=False, default=str))
        print()


def cmd_stats(args):
    """Show aggregate statistics."""
    trace_logger = TraceLogger(trace_dir=args.trace_dir)
    stats = trace_logger.get_stats()

    print(f"\n{'='*60}")
    print(f"  TRACE STATISTICS")
    print(f"{'='*60}\n")

    print(f"  Total traces:     {stats['total_traces']}")
    print(f"  Successful:       {stats['success_count']}")
    print(f"  Errors:           {stats['error_count']}")
    print(f"  Error rate:       {stats['error_rate']*100:.1f}%")
    print()
    print(f"  ── LATENCY {'─'*46}")
    print(f"  Average:          {stats['avg_latency_ms']:.1f} ms")
    print(f"  Min:              {stats['min_latency_ms']:.1f} ms")
    print(f"  Max:              {stats['max_latency_ms']:.1f} ms")
    print(f"  P95:              {stats['p95_latency_ms']:.1f} ms")
    print()

    endpoints = stats.get("endpoints", {})
    if endpoints:
        print(f"  ── ENDPOINTS {'─'*44}")
        for ep, ep_stats in endpoints.items():
            print(f"  {ep}")
            print(f"    Count:        {ep_stats['count']}")
            print(f"    Avg latency:  {ep_stats['avg_latency_ms']:.1f} ms")
    print()


def main():
    """Main CLI entry point."""
    default_trace_dir = str(Path(__file__).parent / "logs")

    parser = argparse.ArgumentParser(
        prog="traces/viewer.py",
        description="RecoveryBench Trace Viewer — inspect API traces and statistics.",
    )
    parser.add_argument(
        "--trace-dir",
        default=default_trace_dir,
        help=f"Trace directory (default: {default_trace_dir})",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list
    list_parser = subparsers.add_parser("list", help="List recent traces")
    list_parser.add_argument("--limit", type=int, default=20, help="Number of traces to show")
    list_parser.set_defaults(func=cmd_list)

    # inspect
    inspect_parser = subparsers.add_parser("inspect", help="Inspect a specific trace")
    inspect_parser.add_argument("trace_id", help="Trace ID to inspect")
    inspect_parser.set_defaults(func=cmd_inspect)

    # stats
    stats_parser = subparsers.add_parser("stats", help="Show aggregate statistics")
    stats_parser.set_defaults(func=cmd_stats)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
