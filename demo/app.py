#!/usr/bin/env python3
"""
RecoveryBench — Gradio Demo Application

Interactive demo with 3 tabs:
  Tab 1: Text Analysis — analyze borrower messages & agent responses
  Tab 2: Audio Analysis — upload audio for end-to-end analysis
  Tab 3: Agent Leaderboard — batch-score conversations and rank

Usage:
    python demo/app.py

Launches on http://localhost:7860
"""

import sys
import json
import os
import csv
import io
import logging
from pathlib import Path
from datetime import datetime

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recoverybench.demo")

# ── Import pipeline ────────────────────────────────────────────────────
try:
    import gradio as gr
except ImportError:
    raise ImportError(
        "Gradio is required. Install with: pip install gradio>=4.0.0"
    )

# Lazy-load analyzer
_analyzer = None


def get_analyzer():
    """Lazy-load the RecoveryBenchAnalyzer singleton."""
    global _analyzer
    if _analyzer is None:
        from pipeline.analyzer import RecoveryBenchAnalyzer
        _analyzer = RecoveryBenchAnalyzer()
        logger.info(f"Analyzer loaded: {_analyzer}")
    return _analyzer


# ── Helper Functions ───────────────────────────────────────────────────

def format_risk_level(score):
    """Convert risk score to human-readable level with emoji."""
    if score is None:
        return "N/A"
    if score < 0.3:
        return f"🟢 Low ({score:.2f})"
    elif score < 0.6:
        return f"🟡 Medium ({score:.2f})"
    elif score < 0.8:
        return f"🟠 High ({score:.2f})"
    else:
        return f"🔴 Critical ({score:.2f})"


def format_compliance(compliance):
    """Format compliance result for display."""
    if not compliance:
        return "N/A"
    if compliance.get("compliant", True):
        return "✅ Compliant — No violations detected"
    violations = compliance.get("violations", [])
    severity = compliance.get("severity", "unknown")
    lines = [f"❌ Non-Compliant — Severity: {severity.upper()}"]
    for v in violations[:5]:
        rule_id = v.get("rule_id", "?")
        category = v.get("category", "?")
        matched = v.get("matched_text", "")[:60]
        lines.append(f"  • [{rule_id}] {category}: \"{matched}\"")
    return "\n".join(lines)


def format_agent_eval(eval_result):
    """Format agent evaluation for display."""
    if not eval_result:
        return "N/A (no agent response provided)"
    lines = []
    lines.append(f"📊 Overall Score: **{eval_result.get('overall_score', 'N/A')}/10**")
    lines.append("")
    rubrics = [
        ("🎯 Intent Accuracy", "intent_accuracy"),
        ("🗣️ Tone Score", "tone_score"),
        ("⚖️ Compliance Score", "compliance_score"),
        ("📈 Escalation Score", "escalation_score"),
    ]
    for label, key in rubrics:
        val = eval_result.get(key, "N/A")
        if isinstance(val, (int, float)):
            bar = "#" * int(val) + "-" * (10 - int(val))
            lines.append(f"{label}: {val:.1f}/10  [{bar}]")
        else:
            lines.append(f"{label}: {val}")
    suggestion = eval_result.get("suggested_improvement", "")
    if suggestion:
        lines.append(f"\n💡 **Suggestion:** {suggestion}")
    return "\n".join(lines)


def create_risk_gauge_html(score):
    """Create an HTML risk gauge visualization."""
    if score is None:
        return "<div style='text-align:center;color:#888;'>No risk score available</div>"

    pct = int(score * 100)
    if score < 0.3:
        color = "#22c55e"
        label = "LOW RISK"
    elif score < 0.6:
        color = "#eab308"
        label = "MEDIUM RISK"
    elif score < 0.8:
        color = "#f97316"
        label = "HIGH RISK"
    else:
        color = "#ef4444"
        label = "CRITICAL"

    html = f"""
    <div style="
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        font-family: 'Inter', 'Segoe UI', sans-serif;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        border: 1px solid rgba(255,255,255,0.08);
    ">
        <div style="
            font-size: 14px;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 12px;
        ">Risk Score</div>
        <div style="
            font-size: 48px;
            font-weight: 800;
            color: {color};
            text-shadow: 0 0 20px {color}40;
            margin-bottom: 8px;
        ">{pct}%</div>
        <div style="
            width: 100%;
            height: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 12px;
        ">
            <div style="
                width: {pct}%;
                height: 100%;
                background: linear-gradient(90deg, #22c55e, #eab308, #f97316, #ef4444);
                border-radius: 4px;
                transition: width 0.5s ease;
            "></div>
        </div>
        <div style="
            font-size: 16px;
            font-weight: 700;
            color: {color};
            letter-spacing: 1px;
        ">{label}</div>
    </div>
    """
    return html


# ── Tab 1: Text Analysis ──────────────────────────────────────────────

def analyze_text(borrower_message, agent_response, language_hint):
    """Run text analysis pipeline."""
    if not borrower_message or not borrower_message.strip():
        return (
            "⚠️ Please enter a borrower message.",
            "",
            "",
            "",
            "<div style='text-align:center;color:#888;'>Enter a message to see risk gauge</div>",
            ""
        )

    analyzer = get_analyzer()
    agent_resp = agent_response.strip() if agent_response and agent_response.strip() else None

    try:
        result = analyzer.analyze_text(
            borrower_message=borrower_message.strip(),
            agent_response=agent_resp,
        )
    except Exception as e:
        error_msg = f"❌ Analysis failed: {str(e)}"
        return error_msg, "", "", "", "", ""

    # Format summary
    intent = result.get("repayment_intent", "UNKNOWN")
    confidence = result.get("intent_confidence", 0)
    risk = result.get("risk_score")
    promise = result.get("promise_to_pay", False)
    window = result.get("payment_window_days")
    lang = result.get("language", "Unknown")
    sentiment = result.get("sentiment", "neutral")
    action = result.get("recommended_action", "review manually")

    summary_lines = [
        f"**🌐 Language:** {lang}",
        f"**🎯 Intent:** {intent} (confidence: {confidence:.2f})",
        f"**📊 Risk:** {format_risk_level(risk)}",
        f"**🤝 Promise to Pay:** {'Yes' if promise else 'No'}"
        + (f" — within {window} days" if window else ""),
        f"**😊 Sentiment:** {sentiment}",
        f"**📋 Recommended Action:** {action}",
    ]
    summary = "\n\n".join(summary_lines)

    # Compliance
    compliance_str = format_compliance(result.get("compliance"))

    # Agent eval
    eval_str = format_agent_eval(result.get("agent_eval"))

    # JSON output
    json_output = json.dumps(result, indent=2, ensure_ascii=False, default=str)

    # Risk gauge
    risk_gauge = create_risk_gauge_html(risk)

    return summary, compliance_str, eval_str, json_output, risk_gauge, ""


# ── Tab 2: Audio Analysis ─────────────────────────────────────────────

def analyze_audio(audio_file):
    """Run audio analysis pipeline."""
    if audio_file is None:
        return "⚠️ Please upload an audio file.", "", ""

    analyzer = get_analyzer()

    try:
        result = analyzer.analyze_audio(str(audio_file))
    except RuntimeError as e:
        return f"❌ Voice pipeline not available: {e}", "", ""
    except Exception as e:
        return f"❌ Audio analysis failed: {e}", "", ""

    # Transcript
    transcript = result.get("transcript", "No transcript available")

    # Summary
    intent = result.get("repayment_intent", "UNKNOWN")
    confidence = result.get("intent_confidence", 0)
    risk = result.get("risk_score")
    summary = (
        f"**🎯 Intent:** {intent} (confidence: {confidence:.2f})\n\n"
        f"**📊 Risk:** {format_risk_level(risk)}\n\n"
        f"**🌐 Language:** {result.get('language', 'Unknown')}"
    )

    json_output = json.dumps(result, indent=2, ensure_ascii=False, default=str)

    return transcript, summary, json_output


# ── Tab 3: Agent Leaderboard ───────────────────────────────────────────

def score_conversations(conversation_text):
    """Score multiple conversations and build leaderboard."""
    if not conversation_text or not conversation_text.strip():
        return "⚠️ Please paste conversation logs.", "", ""

    analyzer = get_analyzer()

    # Parse conversations — expect JSON array or newline-separated JSON objects
    conversations = []
    text = conversation_text.strip()

    try:
        # Try JSON array first
        parsed = json.loads(text)
        if isinstance(parsed, list):
            conversations = parsed
        elif isinstance(parsed, dict):
            conversations = [parsed]
    except json.JSONDecodeError:
        # Try newline-separated JSON
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                conversations.append(obj)
            except json.JSONDecodeError:
                continue

    if not conversations:
        return (
            "⚠️ Could not parse conversations. Expected JSON array or newline-separated JSON objects.\n\n"
            "Format: `[{\"borrower_message\": \"...\", \"agent_response\": \"...\"}]`",
            "",
            ""
        )

    # Score each conversation
    results = []
    for i, conv in enumerate(conversations):
        borrower_msg = conv.get("borrower_message", conv.get("borrower", ""))
        agent_resp = conv.get("agent_response", conv.get("agent", ""))
        conv_id = conv.get("id", conv.get("conversation_id", f"Conv-{i+1:03d}"))

        if not borrower_msg:
            continue

        try:
            analysis = analyzer.analyze_text(
                borrower_message=borrower_msg,
                agent_response=agent_resp if agent_resp else None,
            )
            eval_result = analysis.get("agent_eval") or {}
            results.append({
                "id": str(conv_id),
                "borrower_message": borrower_msg[:60],
                "intent": analysis.get("repayment_intent", "?"),
                "risk_score": analysis.get("risk_score", 0),
                "overall_score": eval_result.get("overall_score", 0),
                "tone_score": eval_result.get("tone_score", 0),
                "compliance_score": eval_result.get("compliance_score", 0),
                "intent_accuracy": eval_result.get("intent_accuracy", 0),
                "improvement": eval_result.get("suggested_improvement", ""),
            })
        except Exception as e:
            logger.warning(f"Failed to score conversation {conv_id}: {e}")

    if not results:
        return "⚠️ No conversations could be scored.", "", ""

    # Sort by overall_score descending
    results.sort(key=lambda x: x.get("overall_score", 0), reverse=True)

    # Build leaderboard table
    header = "| Rank | ID | Intent | Risk | Overall | Tone | Compliance | Suggestion |"
    sep = "|------|-------|--------|------|---------|------|------------|-----------|"
    rows = [header, sep]
    for rank, r in enumerate(results, 1):
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}"
        rows.append(
            f"| {medal} | {r['id']} | {r['intent']} | "
            f"{r['risk_score']:.2f} | **{r['overall_score']:.1f}** | "
            f"{r['tone_score']:.1f} | {r['compliance_score']:.1f} | "
            f"{r['improvement'][:50]}... |"
        )
    leaderboard = "\n".join(rows)

    # Statistics
    avg_overall = sum(r["overall_score"] for r in results) / len(results)
    avg_compliance = sum(r["compliance_score"] for r in results) / len(results)
    stats = (
        f"📊 **Scored:** {len(results)} conversations\n\n"
        f"**Mean Overall:** {avg_overall:.2f}/10\n\n"
        f"**Mean Compliance:** {avg_compliance:.2f}/10\n\n"
        f"**Best Agent Response:** {results[0]['id']} ({results[0]['overall_score']:.1f}/10)\n\n"
        f"**Worst Agent Response:** {results[-1]['id']} ({results[-1]['overall_score']:.1f}/10)"
    )

    # CSV export
    csv_buf = io.StringIO()
    writer = csv.DictWriter(csv_buf, fieldnames=[
        "rank", "id", "intent", "risk_score", "overall_score",
        "tone_score", "compliance_score", "intent_accuracy", "improvement"
    ])
    writer.writeheader()
    for rank, r in enumerate(results, 1):
        writer.writerow({"rank": rank, **r})
    csv_text = csv_buf.getvalue()

    return leaderboard, stats, csv_text


# ── Build Gradio Interface ────────────────────────────────────────────

def build_demo():
    """Build the Gradio demo interface."""
    custom_css = """
    .gradio-container {
        max-width: 1200px !important;
        margin: auto !important;
        font-family: 'Inter', 'Segoe UI', -apple-system, sans-serif !important;
    }
    .main-header {
        text-align: center;
        padding: 20px 0 10px 0;
    }
    .main-header h1 {
        font-size: 2.2em;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    .tab-nav button {
        font-size: 16px !important;
        font-weight: 600 !important;
    }
    """

    with gr.Blocks(
        title="RecoveryBench — AI Debt Collection Evaluator",
        css=custom_css,
        theme=gr.themes.Soft(
            primary_hue="indigo",
            secondary_hue="purple",
            neutral_hue="slate",
        ),
    ) as demo:
        # Header
        gr.HTML("""
        <div class="main-header">
            <h1>📊 RecoveryBench</h1>
            <p style="color: #94a3b8; font-size: 1.1em; margin-top: 4px;">
                Multilingual AI Debt Collection Agent Evaluation Platform
            </p>
            <p style="color: #64748b; font-size: 0.9em;">
                Built for Riverline, Gnani.ai, Skit.ai, Bolna, Ringg, Exotel, WordWorks AI
            </p>
        </div>
        """)

        with gr.Tabs() as tabs:
            # ── Tab 1: Text Analysis ──
            with gr.TabItem("📝 Text Analysis", id="text_tab"):
                gr.Markdown("### Analyze a borrower message and optionally evaluate an agent response")
                with gr.Row():
                    with gr.Column(scale=1):
                        borrower_input = gr.Textbox(
                            label="Borrower Message",
                            placeholder="e.g., Bhai salary nahi aayi, agle hafte kar dunga payment",
                            lines=3,
                            elem_id="borrower_input",
                        )
                        agent_input = gr.Textbox(
                            label="Agent Response (optional)",
                            placeholder="e.g., Your EMI is 15 days overdue. Please pay immediately.",
                            lines=3,
                            elem_id="agent_input",
                        )
                        language_select = gr.Dropdown(
                            label="Language Hint",
                            choices=["Auto-detect", "English", "Hindi", "Bengali", "Hinglish"],
                            value="Auto-detect",
                            elem_id="language_select",
                        )
                        analyze_btn = gr.Button(
                            "🔍 Analyze",
                            variant="primary",
                            size="lg",
                            elem_id="analyze_btn",
                        )

                    with gr.Column(scale=1):
                        risk_gauge = gr.HTML(
                            value="<div style='text-align:center;color:#888;padding:40px;'>Enter a message to see risk gauge</div>",
                            label="Risk Gauge",
                        )

                with gr.Row():
                    with gr.Column():
                        summary_output = gr.Markdown(
                            label="Analysis Summary",
                            elem_id="summary_output",
                        )
                    with gr.Column():
                        compliance_output = gr.Textbox(
                            label="Compliance Check",
                            lines=5,
                            interactive=False,
                            elem_id="compliance_output",
                        )

                with gr.Row():
                    eval_output = gr.Markdown(
                        label="Agent Evaluation",
                        elem_id="eval_output",
                    )

                with gr.Accordion("📄 Full JSON Output", open=False):
                    json_output = gr.Code(
                        language="json",
                        label="Raw JSON",
                        elem_id="json_output",
                    )

                error_output = gr.Textbox(visible=False)

                analyze_btn.click(
                    fn=analyze_text,
                    inputs=[borrower_input, agent_input, language_select],
                    outputs=[summary_output, compliance_output, eval_output,
                             json_output, risk_gauge, error_output],
                )

                # Example inputs
                gr.Examples(
                    examples=[
                        ["kal kar dunga payment bhai", "Your EMI is 15 days overdue. Pay immediately or legal action will be taken.", "Auto-detect"],
                        ["I already paid last week via UPI", "Please pay the outstanding amount.", "Auto-detect"],
                        ["ye galat amount hai, maine itna loan nahi liya", "", "Auto-detect"],
                        ["police ko bulao, mujhe fark nahi padta", "", "Auto-detect"],
                        ["haan yaad dilana next week", "We understand. We'll follow up next week.", "Auto-detect"],
                    ],
                    inputs=[borrower_input, agent_input, language_select],
                    label="Try these examples",
                )

            # ── Tab 2: Audio Analysis ──
            with gr.TabItem("🎤 Audio Analysis", id="audio_tab"):
                gr.Markdown("### Upload an audio file for transcription and full analysis")
                gr.Markdown(
                    "Supported formats: `.mp3`, `.wav`, `.flac`, `.ogg`, `.m4a`"
                )

                with gr.Row():
                    with gr.Column():
                        audio_input = gr.Audio(
                            label="Upload Audio",
                            type="filepath",
                            elem_id="audio_input",
                        )
                        audio_btn = gr.Button(
                            "🎙️ Transcribe & Analyze",
                            variant="primary",
                            size="lg",
                            elem_id="audio_analyze_btn",
                        )

                with gr.Row():
                    with gr.Column():
                        transcript_output = gr.Textbox(
                            label="Transcript",
                            lines=6,
                            interactive=False,
                            elem_id="transcript_output",
                        )
                    with gr.Column():
                        audio_summary = gr.Markdown(
                            label="Analysis Summary",
                            elem_id="audio_summary",
                        )

                with gr.Accordion("📄 Full JSON Output", open=False):
                    audio_json = gr.Code(
                        language="json",
                        label="Raw JSON",
                        elem_id="audio_json",
                    )

                audio_btn.click(
                    fn=analyze_audio,
                    inputs=[audio_input],
                    outputs=[transcript_output, audio_summary, audio_json],
                )

            # ── Tab 3: Agent Leaderboard ──
            with gr.TabItem("🏆 Agent Leaderboard", id="leaderboard_tab"):
                gr.Markdown("### Paste multiple conversation logs to score and rank agent responses")
                gr.Markdown(
                    "Format: JSON array of objects with `borrower_message` and `agent_response` fields."
                )

                with gr.Row():
                    conv_input = gr.Textbox(
                        label="Conversation Logs (JSON)",
                        placeholder='[\n  {"borrower_message": "kal payment karunga", "agent_response": "Please pay now."},\n  {"borrower_message": "galat amount hai", "agent_response": "We\'ll verify."}\n]',
                        lines=10,
                        elem_id="conv_input",
                    )

                score_btn = gr.Button(
                    "🏆 Score & Rank",
                    variant="primary",
                    size="lg",
                    elem_id="score_btn",
                )

                with gr.Row():
                    with gr.Column(scale=2):
                        leaderboard_output = gr.Markdown(
                            label="Leaderboard",
                            elem_id="leaderboard_output",
                        )
                    with gr.Column(scale=1):
                        stats_output = gr.Markdown(
                            label="Statistics",
                            elem_id="stats_output",
                        )

                with gr.Accordion("📥 Export CSV", open=False):
                    csv_output = gr.Code(
                        language=None,
                        label="CSV Data",
                        elem_id="csv_output",
                    )

                score_btn.click(
                    fn=score_conversations,
                    inputs=[conv_input],
                    outputs=[leaderboard_output, stats_output, csv_output],
                )

                # Example
                gr.Examples(
                    examples=[
                        ['[\n  {"id": "agent-A", "borrower_message": "kal payment kar dunga bhai", "agent_response": "Thank you for your commitment. We will follow up next week."},\n  {"id": "agent-B", "borrower_message": "kal payment kar dunga bhai", "agent_response": "Pay immediately or legal action will be taken against you."},\n  {"id": "agent-C", "borrower_message": "kal payment kar dunga bhai", "agent_response": "OK"}\n]'],
                    ],
                    inputs=[conv_input],
                    label="Try this example",
                )

        # Footer
        gr.HTML("""
        <div style="text-align: center; padding: 20px 0; color: #64748b; font-size: 0.85em; border-top: 1px solid rgba(255,255,255,0.1); margin-top: 20px;">
            <p>RecoveryBench v1.0.0 — Built by <strong>Sweta Jha</strong>, IEM Kolkata</p>
            <p>Powered by scikit-learn, XGBoost, Whisper, Gradio</p>
        </div>
        """)

    return demo


# ── Entry point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    demo = build_demo()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )
