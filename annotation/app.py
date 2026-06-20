#!/usr/bin/env python3
"""
RecoveryBench — Human Annotation Interface

Gradio-based tool for human annotators to label and evaluate
debt collection conversations for inter-annotator agreement studies.

Usage:
    python annotation/app.py

Launches on http://localhost:7861
"""

import sys
import json
import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import gradio as gr
except ImportError:
    raise ImportError("Gradio required: pip install gradio>=4.0.0")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recoverybench.annotation")

# ── Paths ──────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
REPORTS_DIR = Path(__file__).parent / "reports"
ANNOTATIONS_FILE = DATA_DIR / "annotations.json"
CONVERSATIONS_FILE = PROJECT_ROOT / "simulator" / "data" / "synthetic_conversations.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Intent and Compliance Labels ───────────────────────────────────────
INTENT_LABELS = [
    "LIKELY_PAY", "NEEDS_REMINDER", "DISPUTE",
    "HIGH_RISK", "VAGUE", "ALREADY_PAID",
]
COMPLIANCE_LABELS = ["Compliant", "Non-compliant"]
SEVERITY_LABELS = ["None", "Minor", "Moderate", "Critical"]
TONE_LABELS = [
    "Professional", "Empathetic", "Neutral",
    "Aggressive", "Threatening", "Abusive",
]


# ── Data Management ────────────────────────────────────────────────────

def load_conversations():
    """Load conversations for annotation."""
    if CONVERSATIONS_FILE.exists():
        with open(CONVERSATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_annotations():
    """Load existing annotations."""
    if ANNOTATIONS_FILE.exists():
        with open(ANNOTATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_annotation(annotation):
    """Save a single annotation to the annotations file."""
    annotations = load_annotations()
    annotations.append(annotation)
    with open(ANNOTATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(annotations, f, indent=2, ensure_ascii=False)
    return len(annotations)


# ── State ──────────────────────────────────────────────────────────────
_conversations = []
_current_index = 0


def get_conversation(index):
    """Get a conversation by index."""
    global _conversations
    if not _conversations:
        _conversations = load_conversations()
    if 0 <= index < len(_conversations):
        return _conversations[index]
    return None


def format_conversation(conv):
    """Format a conversation for display."""
    if not conv:
        return "No conversations loaded. Generate them with:\n`python simulator/generate_conversation_dataset.py`"

    lines = [
        f"**Conversation ID:** {conv.get('conversation_id', 'N/A')}",
        f"**Language:** {conv.get('language', 'Unknown')}",
        f"**Expected Intent:** {conv.get('expected_intent', 'N/A')}",
        "",
        "---",
        "",
    ]
    for turn in conv.get("turns", []):
        speaker = turn["speaker"].upper()
        msg = turn["message"]
        if speaker == "AGENT":
            lines.append(f"🤖 **AGENT:** {msg}")
        else:
            lines.append(f"👤 **BORROWER:** {msg}")
        lines.append("")
    return "\n".join(lines)


# ── Interface Functions ────────────────────────────────────────────────

def load_next(annotator_id, current_idx):
    """Load the next unannotated conversation."""
    global _conversations, _current_index

    if not _conversations:
        _conversations = load_conversations()

    if not _conversations:
        return (
            "No conversations available. Generate with:\n`python simulator/generate_conversation_dataset.py`",
            0,
            f"0 / 0",
        )

    idx = int(current_idx) if current_idx else 0
    idx = min(idx, len(_conversations) - 1)
    _current_index = idx

    conv = _conversations[idx]
    display = format_conversation(conv)
    progress = f"{idx + 1} / {len(_conversations)}"

    return display, idx, progress


def submit_annotation(
    annotator_id, current_idx,
    intent_label, intent_confidence,
    compliance_label, severity_label,
    tone_label, tone_score,
    agent_quality_score,
    notes,
):
    """Submit an annotation for the current conversation."""
    if not annotator_id or not annotator_id.strip():
        return "⚠️ Please enter your annotator ID first.", current_idx, ""

    global _conversations
    if not _conversations:
        _conversations = load_conversations()

    idx = int(current_idx) if current_idx else 0
    if idx >= len(_conversations):
        return "⚠️ No conversation to annotate.", idx, ""

    conv = _conversations[idx]

    annotation = {
        "annotation_id": f"ann-{datetime.now().strftime('%Y%m%d%H%M%S')}-{idx}",
        "annotator_id": annotator_id.strip(),
        "timestamp": datetime.now().isoformat(),
        "conversation_id": conv.get("conversation_id", f"conv-{idx}"),
        "conversation_index": idx,
        "language": conv.get("language", "Unknown"),
        "labels": {
            "intent": intent_label,
            "intent_confidence": float(intent_confidence) if intent_confidence else 0.5,
            "compliance": compliance_label,
            "severity": severity_label,
            "tone": tone_label,
            "tone_score": float(tone_score) if tone_score else 5,
            "agent_quality_score": float(agent_quality_score) if agent_quality_score else 5,
        },
        "notes": notes.strip() if notes else "",
        "expected_intent": conv.get("expected_intent", ""),
        "agreement_with_expected": intent_label == conv.get("expected_intent", ""),
    }

    count = save_annotation(annotation)

    # Move to next
    next_idx = min(idx + 1, len(_conversations) - 1)
    next_conv = _conversations[next_idx]
    next_display = format_conversation(next_conv)
    progress = f"{next_idx + 1} / {len(_conversations)}"

    status = f"✅ Annotation #{count} saved for conversation {conv.get('conversation_id', idx)}. Moving to next."

    return status, next_idx, progress, next_display


def go_to_conversation(target_idx):
    """Navigate to a specific conversation."""
    global _conversations
    if not _conversations:
        _conversations = load_conversations()

    idx = int(target_idx) if target_idx else 0
    idx = max(0, min(idx, len(_conversations) - 1))

    conv = _conversations[idx]
    display = format_conversation(conv)
    progress = f"{idx + 1} / {len(_conversations)}"

    return display, idx, progress


def get_annotation_stats():
    """Get annotation statistics."""
    annotations = load_annotations()
    if not annotations:
        return "No annotations yet."

    annotators = set(a.get("annotator_id", "") for a in annotations)
    intents = {}
    agreements = 0

    for a in annotations:
        intent = a.get("labels", {}).get("intent", "?")
        intents[intent] = intents.get(intent, 0) + 1
        if a.get("agreement_with_expected", False):
            agreements += 1

    agreement_rate = agreements / len(annotations) * 100

    lines = [
        f"**Total Annotations:** {len(annotations)}",
        f"**Annotators:** {len(annotators)} ({', '.join(sorted(annotators))})",
        f"**Agreement with Expected:** {agreement_rate:.1f}%",
        "",
        "**Intent Distribution:**",
    ]
    for intent, count in sorted(intents.items()):
        lines.append(f"  - {intent}: {count}")

    return "\n\n".join(lines)


# ── Build Interface ────────────────────────────────────────────────────

def build_annotation_app():
    """Build the annotation Gradio interface."""
    with gr.Blocks(
        title="RecoveryBench — Annotation Tool",
        theme=gr.themes.Soft(
            primary_hue="teal",
            secondary_hue="cyan",
            neutral_hue="slate",
        ),
    ) as app:
        gr.HTML("""
        <div style="text-align:center; padding: 16px 0;">
            <h1 style="font-size:1.8em; color:#14b8a6;">🏷️ RecoveryBench Annotation Tool</h1>
            <p style="color:#94a3b8;">Human evaluation interface for inter-annotator agreement</p>
        </div>
        """)

        with gr.Row():
            annotator_id = gr.Textbox(
                label="Annotator ID",
                placeholder="e.g., annotator_A",
                scale=1,
                elem_id="annotator_id",
            )
            current_idx = gr.Number(
                value=0, label="Current Index",
                visible=False,
            )
            progress_text = gr.Textbox(
                label="Progress",
                value="0 / 0",
                interactive=False,
                scale=1,
            )

        with gr.Row():
            load_btn = gr.Button("📂 Load Conversations", variant="secondary")
            prev_btn = gr.Button("⬅️ Previous")
            next_btn = gr.Button("Next ➡️")

        # Conversation display
        conversation_display = gr.Markdown(
            value="Click 'Load Conversations' to begin.",
            label="Conversation",
            elem_id="conversation_display",
        )

        gr.Markdown("### Annotation Labels")

        with gr.Row():
            with gr.Column():
                intent_label = gr.Dropdown(
                    choices=INTENT_LABELS,
                    label="Borrower Intent",
                    value="LIKELY_PAY",
                    elem_id="intent_label",
                )
                intent_confidence = gr.Slider(
                    minimum=0, maximum=1, value=0.8, step=0.05,
                    label="Intent Confidence",
                    elem_id="intent_confidence",
                )
            with gr.Column():
                compliance_label = gr.Dropdown(
                    choices=COMPLIANCE_LABELS,
                    label="Agent Compliance",
                    value="Compliant",
                    elem_id="compliance_label",
                )
                severity_label = gr.Dropdown(
                    choices=SEVERITY_LABELS,
                    label="Violation Severity",
                    value="None",
                    elem_id="severity_label",
                )

        with gr.Row():
            with gr.Column():
                tone_label = gr.Dropdown(
                    choices=TONE_LABELS,
                    label="Agent Tone",
                    value="Professional",
                    elem_id="tone_label",
                )
                tone_score = gr.Slider(
                    minimum=1, maximum=10, value=7, step=0.5,
                    label="Tone Score (1-10)",
                    elem_id="tone_score",
                )
            with gr.Column():
                agent_quality_score = gr.Slider(
                    minimum=1, maximum=10, value=7, step=0.5,
                    label="Overall Agent Quality (1-10)",
                    elem_id="agent_quality_score",
                )

        notes = gr.Textbox(
            label="Notes (optional)",
            placeholder="Any observations about this conversation...",
            lines=2,
            elem_id="annotation_notes",
        )

        submit_btn = gr.Button(
            "✅ Submit Annotation & Next",
            variant="primary",
            size="lg",
            elem_id="submit_btn",
        )

        status_output = gr.Textbox(
            label="Status",
            interactive=False,
            elem_id="status_output",
        )

        # Stats section
        with gr.Accordion("📊 Annotation Statistics", open=False):
            stats_output = gr.Markdown(elem_id="stats_output")
            refresh_stats_btn = gr.Button("🔄 Refresh Stats")
            refresh_stats_btn.click(
                fn=get_annotation_stats,
                outputs=[stats_output],
            )

        # Navigation actions
        load_btn.click(
            fn=load_next,
            inputs=[annotator_id, current_idx],
            outputs=[conversation_display, current_idx, progress_text],
        )

        def go_prev(idx):
            return go_to_conversation(max(0, int(idx) - 1))

        def go_next(idx):
            return go_to_conversation(int(idx) + 1)

        prev_btn.click(
            fn=go_prev,
            inputs=[current_idx],
            outputs=[conversation_display, current_idx, progress_text],
        )

        next_btn.click(
            fn=go_next,
            inputs=[current_idx],
            outputs=[conversation_display, current_idx, progress_text],
        )

        submit_btn.click(
            fn=submit_annotation,
            inputs=[
                annotator_id, current_idx,
                intent_label, intent_confidence,
                compliance_label, severity_label,
                tone_label, tone_score,
                agent_quality_score,
                notes,
            ],
            outputs=[status_output, current_idx, progress_text, conversation_display],
        )

    return app


if __name__ == "__main__":
    app = build_annotation_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7861,
        share=False,
        show_error=True,
    )
