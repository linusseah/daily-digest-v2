"""
Daily Digest v2 — Agentic pipeline using the Claude Agent SDK.

The agent receives the system prompt, user profile, and access to CLI tools
via the Bash built-in. It autonomously decides what to fetch, how to curate,
and how to format the digest.

Usage:
    python agent.py [--dry-run] [--model MODEL]

Env vars required:
    ANTHROPIC_API_KEY
    GMAIL_ADDRESS, GMAIL_APP_PASS     (for IMAP fetching)
    RESEND_API_KEY                    (for email sending)
    DIGEST_TO                         (recipient, optional — defaults to GMAIL_ADDRESS)
    BRAVE_SEARCH_API_KEY              (optional — falls back to DuckDuckGo)
"""

import asyncio
import os
import sys
import json
import datetime
import argparse
import subprocess
import shutil
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent
SYSTEM_PROMPT_PATH = ROOT / "config" / "system_prompt.txt"
LOG_DIR = ROOT / "logs"
HTML_OUTPUT = Path("/tmp/digest-v2.html")


def validate_env() -> None:
    required = ["ANTHROPIC_API_KEY", "GMAIL_ADDRESS", "GMAIL_APP_PASS", "RESEND_API_KEY"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"ERROR: Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)


def load_system_prompt(dry_run: bool) -> str:
    prompt = SYSTEM_PROMPT_PATH.read_text()
    if dry_run:
        # Patch send command to use --dry-run flag
        prompt = prompt.replace(
            'python tools/send_email.py /tmp/digest-v2.html',
            'python tools/send_email.py /tmp/digest-v2.html --dry-run /tmp/digest-v2.html',
        )
        prompt += "\n\nIMPORTANT: This is a DRY RUN. Pass --dry-run to send_email.py. Do not actually send the email."
    return prompt


# ---------------------------------------------------------------------------
# Agent runner
# ---------------------------------------------------------------------------

async def run_agent(system_prompt: str, model: str) -> tuple[str, list[dict]]:
    """
    Launch the agent and stream its output.
    Returns (final_text, tool_calls) where tool_calls is a log of Bash invocations.
    """
    tool_calls: list[dict] = []
    output_parts: list[str] = []

    print(f"  Launching agent ({model})...")

    async for message in query(
        prompt=system_prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Bash", "Read", "Write"],
            permission_mode="acceptAll",
            model=model,
            cwd=str(ROOT),
        ),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text") and block.text:
                    text = block.text.strip()
                    if text:
                        print(f"  [agent] {text[:120]}{'...' if len(text) > 120 else ''}")
                        output_parts.append(text)
                # Track tool use for logging
                if hasattr(block, "type") and block.type == "tool_use":
                    tool_name = getattr(block, "name", "")
                    tool_input = getattr(block, "input", {})
                    if tool_name == "Bash":
                        cmd = tool_input.get("command", "")
                        tool_calls.append({
                            "tool": "Bash",
                            "command": cmd,
                            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                        })
                        print(f"  [tool] Bash: {cmd[:100]}{'...' if len(cmd) > 100 else ''}")

        elif isinstance(message, ResultMessage):
            status = getattr(message, "subtype", "unknown")
            print(f"  Agent finished: {status}")

    return "\n".join(output_parts), tool_calls


# ---------------------------------------------------------------------------
# Run logging
# ---------------------------------------------------------------------------

def write_run_log(tool_calls: list[dict], success: bool, error: str | None,
                  start_time: datetime.datetime, dry_run: bool) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    duration_s = (datetime.datetime.utcnow() - start_time).total_seconds()

    log = {
        "version": "2.0",
        "date": datetime.date.today().isoformat(),
        "timestamp": start_time.isoformat() + "Z",
        "duration_seconds": round(duration_s, 1),
        "dry_run": dry_run,
        "success": success,
        "error": error,
        "tool_calls": tool_calls,
        "tool_call_count": len(tool_calls),
        "bash_commands": [tc["command"] for tc in tool_calls if tc["tool"] == "Bash"],
    }

    log_path = LOG_DIR / f"{datetime.date.today().isoformat()}.json"
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)
    print(f"  Log written to {log_path}")


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------

def run_fallback(dry_run: bool) -> int:
    """Invoke the v1.5-style deterministic fallback pipeline."""
    print("  Running fallback pipeline (fallback.py)...")
    cmd = [sys.executable, str(ROOT / "fallback.py")]
    if dry_run:
        cmd.append("--dry-run")
    result = subprocess.run(cmd, env=os.environ.copy())
    return result.returncode


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Daily Digest v2 — Agentic pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Skip actual email send")
    parser.add_argument("--model",   default="claude-sonnet-4-5", help="Claude model to use")
    args = parser.parse_args()

    validate_env()

    start_time = datetime.datetime.utcnow()
    today = datetime.date.today().strftime("%A, %B %-d, %Y")
    print(f"Daily Digest v2 — {today}{' [DRY RUN]' if args.dry_run else ''}")

    system_prompt = load_system_prompt(dry_run=args.dry_run)

    tool_calls: list[dict] = []
    success = False
    error_msg = None

    try:
        _, tool_calls = asyncio.run(run_agent(system_prompt, args.model))

        # Check the HTML output was produced
        if HTML_OUTPUT.exists():
            print(f"  Digest HTML produced: {HTML_OUTPUT} ({HTML_OUTPUT.stat().st_size} bytes)")
            success = True

            # Archive digest for evals
            EVAL_DIGESTS_DIR = ROOT / "evals" / "data" / "digests"
            EVAL_DIGESTS_DIR.mkdir(parents=True, exist_ok=True)

            archive_path = EVAL_DIGESTS_DIR / f"{datetime.date.today().isoformat()}_digest.html"
            shutil.copy(HTML_OUTPUT, archive_path)
            print(f"  Digest archived to {archive_path}")
        else:
            raise RuntimeError(f"Agent completed but {HTML_OUTPUT} was not created")

    except Exception as e:
        error_msg = str(e)
        print(f"  Agent failed: {e}", file=sys.stderr)
        print("  Attempting fallback...")
        rc = run_fallback(dry_run=args.dry_run)
        if rc != 0:
            print("  Fallback also failed.", file=sys.stderr)
        else:
            print("  Fallback succeeded.")

    finally:
        write_run_log(tool_calls, success, error_msg, start_time, dry_run=args.dry_run)

    if not success and error_msg:
        sys.exit(1)


if __name__ == "__main__":
    main()
