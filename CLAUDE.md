# Daily Digest v2 - Claude Code Assistant Guide

This document contains important context and troubleshooting information for working with this project.

## Project Overview

Daily Digest v2 is an agentic email digest system that:
- Runs daily via GitHub Actions at 15:00 UTC (7am PST)
- Uses Claude Sonnet 4.5 to curate personalized content
- Falls back to a simpler pipeline if the agent fails
- Sends digests via Resend API

**Key Files:**
- `agent.py` - Main agentic pipeline using Claude Agent SDK
- `fallback.py` - Simpler deterministic pipeline (v1.5-style)
- `config/system_prompt.txt` - Agent instructions
- `config/user_profile.yaml` - User interests and sources
- `.github/workflows/digest.yml` - Daily automation

## Common Issues & Solutions

### Issue: Agent fails to write files in GitHub Actions

**Symptoms:**
- Workflow shows "success" but fallback runs instead
- Logs show: "I need your permission to write the digest HTML file"
- Agent completes but `/tmp/digest-v2.html` not created

**Root Cause:**
The `permission_mode` setting in agent.py controls whether the agent can perform actions without asking. In GitHub Actions (non-interactive environment), permission prompts fail.

**Solution:**
In `agent.py`, ensure the ClaudeAgentOptions are set correctly:

```python
ClaudeAgentOptions(
    allowed_tools=["Bash", "Read", "Write"],
    permission_mode="bypassPermissions",  # NOT "acceptAll" or "acceptEdits"
    model=model,
    cwd=str(ROOT),
)
```

**Valid permission_mode values:**
- `"default"` - Ask for permission (interactive only)
- `"acceptEdits"` - Auto-accept edits but ask for other actions
- `"bypassPermissions"` - Skip all permission prompts (required for GitHub Actions)
- `"plan"` - Plan mode only

**Important:** `"acceptAll"` is NOT a valid value and will cause the error:
```
error: option '--permission-mode <mode>' argument 'acceptAll' is invalid
```

### Issue: How to diagnose failing digests

**Steps:**
1. Check recent workflow runs:
   ```bash
   gh run list --workflow="Daily Digest v2" --limit 5
   ```

2. View logs from a specific run:
   ```bash
   gh run view <RUN_ID> --log | grep -A5 -B5 "Agent failed\|Fallback"
   ```

3. Look for these patterns:
   - "Agent failed: Agent completed but /tmp/digest-v2.html was not created" → Permission issue
   - "Fallback email sent — status 200" → Fallback ran (agent failed)
   - "Digest HTML produced: /tmp/digest-v2.html" → Agent succeeded

4. Check local logs:
   ```bash
   ls -lt logs/*.json | head -5
   cat logs/YYYY-MM-DD.json
   ```

### Testing Locally

To generate a digest locally without sending:

```bash
ANTHROPIC_API_KEY="your-key" \
RESEND_API_KEY="dummy" \
GMAIL_ADDRESS="your-email" \
GMAIL_APP_PASS="your-pass" \
DIGEST_TO="recipient" \
EXA_API_KEY="your-key" \
python3.12 agent.py --dry-run
```

Check output:
- `/tmp/digest-v2.html` - Agent-generated digest
- `/tmp/fallback-digest.html` - Fallback digest (if agent failed)
- `logs/YYYY-MM-DD.json` - Run metadata

## API Cost Monitoring

**Daily Digest v2 costs:** ~$0.15/day (~$4.50/month)
- Model: claude-sonnet-4-5
- Input: ~8,000-15,000 tokens
- Output: ~4,000-6,000 tokens

**Check usage:**
- Console: https://platform.claude.com/settings/cost
- Shows breakdown by date, model, token counts

**LLM Judge Workflows (manual only):**
- Score Digests with LLM Judge
- Bulk Generate Digests for Calibration
- Re-score Digests with Updated Rubric

These only run when manually triggered - they do NOT consume credits automatically.

## Workflow Management

**Disable a workflow:**
```bash
gh workflow disable <WORKFLOW_ID> --repo linusseah/daily-digest-v2
```

**List all workflows:**
```bash
gh workflow list --repo linusseah/daily-digest-v2
```

## Architecture Notes

The system has two pipelines:

1. **Agent v2 (primary):** Agentic curation with Claude Agent SDK
   - Reads user profile
   - Fetches from multiple sources (RSS, email, web search)
   - Identifies themes and curates content
   - Generates editorial intro
   - Groups by theme (not source)
   - Writes HTML and sends email

2. **Fallback (backup):** Deterministic pipeline
   - Fetches from known sources
   - Simple summarization
   - Section-by-section format
   - Runs if agent fails or hits errors

The workflow always shows "success" even if agent fails, because fallback ensures a digest is sent.

## Previous Issues Resolved

**2026-03-06:** Fixed agent file writing in GitHub Actions
- Changed `permission_mode` from `"acceptEdits"` to `"bypassPermissions"`
- Added `"Write"` to allowed_tools list
- Commit: bde3ffa

**2026-03-06:** Disabled failing v1.5 digest
- Old digest (linusseah/daily-digest repo) was sending error emails
- OpenRouter 429 errors (rate limit)
- Workflow disabled using `gh workflow disable`
