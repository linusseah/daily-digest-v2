# evals/judge_prompt.py

import json
import anthropic
from pathlib import Path

JUDGE_MODEL = "claude-opus-4-5-20251101"
ROOT = Path(__file__).parent.parent  # daily-digest-v2/

SYSTEM_PROMPT = """You are an expert editorial evaluator. You assess the quality of a daily AI-generated newsletter digest using a structured rubric.

Score each dimension 1-5. Be calibrated: 3 = average (not good, not bad). Reserve 5 for genuinely excellent and 1 for clear failures.

Your explanations are more important than your scores. Each explanation must be specific enough to drive improvement — say *what exactly* was good or bad and *why*. Vague explanations like "summaries were decent" are not acceptable.

Return only a JSON object. No preamble, no markdown fences."""


def load_run_log(date_str: str) -> dict | None:
    """Load the agent's run log for a given date (YYYY-MM-DD)."""
    log_path = ROOT / "logs" / f"{date_str}.json"
    if log_path.exists():
        return json.loads(log_path.read_text())
    return None


def format_log_context(log: dict | None) -> str:
    """Format run log metadata for injection into the judge prompt."""
    if not log:
        return "Run log: not available for this digest."

    lines = [
        f"- Sources successfully fetched: {', '.join(log.get('sources_fetched', [])) or 'none logged'}",
        f"- Sources that failed: {', '.join(log.get('sources_failed', [])) or 'none'}",
        f"- Web searches run: {log.get('web_searches', [])}",
        f"- Total items fetched: {log.get('items_fetched', 'unknown')}",
        f"- Items included in digest: {log.get('items_included', 'unknown')}",
        f"- Themes identified by agent: {log.get('themes', [])}",
        f"- Agent's editorial intro summary: {log.get('editorial_intro_summary', 'not logged')}",
        f"- Run duration: {log.get('duration_seconds', 'unknown')}s",
        f"- Agent used fallback: {not log.get('success', True)}",
    ]
    return "\n".join(lines)


def build_judge_prompt(
    user_profile: str,
    system_prompt_txt: str,
    rubric: str,
    digest_html: str,
    run_log: dict | None,
) -> str:
    log_context = format_log_context(run_log)

    return f"""## 1. User Profile (source of truth for what this digest should do)

<user_profile>
{user_profile}
</user_profile>

---

## 2. Agent Instructions (what the agent was told to do)

<agent_system_prompt>
{system_prompt_txt}
</agent_system_prompt>

---

## 3. Run Metadata (from agent's log file)

<run_metadata>
{log_context}
</run_metadata>

---

## 4. Scoring Rubric

<rubric>
{rubric}
</rubric>

---

## 5. Digest to Evaluate

<digest>
{digest_html}
</digest>

---

## Instructions

Evaluate the digest against each rubric dimension. Use the run metadata to inform dimensions like Source Failure Recovery (Dimension 7). Return this exact JSON structure:

{{
  "scores": {{
    "interest_priority_adherence": {{"score": <1-5>, "explanation": "<2-3 specific sentences>"}},
    "summary_quality": {{"score": <1-5>, "explanation": "<2-3 specific sentences>"}},
    "source_diversity": {{"score": <1-5>, "explanation": "<2-3 specific sentences>"}},
    "signal_to_noise": {{"score": <1-5>, "explanation": "<2-3 specific sentences>"}},
    "theme_and_editorial_voice": {{"score": <1-5>, "explanation": "<2-3 specific sentences>"}},
    "content_freshness": {{"score": <1-5>, "explanation": "<2-3 specific sentences>"}},
    "source_failure_recovery": {{"score": <1-5>, "explanation": "<2-3 specific sentences>"}},
    "novelty": {{"score": <1-5>, "explanation": "<2-3 specific sentences>"}}
  }},
  "overall_score": <weighted avg, float to 1dp — use weights: interest_priority=0.25, summary=0.20, source_diversity=0.15, signal_noise=0.15, theme=0.10, freshness=0.10, failure_recovery=0.03, novelty=0.02>,
  "overall_summary": "<3-4 sentence narrative: biggest strength, biggest weakness, and one concrete thing to fix>",
  "top_issue": "<single most impactful thing to fix — be specific>",
  "top_strength": "<single biggest strength — be specific>"
}}"""


def run_judge(date_str: str) -> dict:
    """Judge the digest for a given date. Returns parsed JSON result."""
    user_profile = (ROOT / "config" / "user_profile.yaml").read_text()
    system_prompt_txt = (ROOT / "config" / "system_prompt.txt").read_text()
    rubric = (ROOT / "evals" / "rubric.md").read_text()

    digest_path = ROOT / "evals" / "data" / "digests" / f"{date_str}_digest.html"
    digest_html = digest_path.read_text()

    run_log = load_run_log(date_str)

    prompt = build_judge_prompt(user_profile, system_prompt_txt, rubric, digest_html, run_log)

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    import json
    import re

    # Extract JSON from the response, handling markdown code fences
    response_text = message.content[0].text.strip()

    # Remove markdown code fences if present
    if response_text.startswith("```"):
        # Extract content between code fences
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response_text, re.DOTALL)
        if match:
            response_text = match.group(1).strip()

    return json.loads(response_text)
