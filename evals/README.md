# Daily Digest v2 — Evaluation System

This directory contains an LLM-as-a-judge evaluation framework for the Daily Digest v2 agent. The system scores each digest on 8 dimensions using Claude Opus as the judge, tracks scores over time, and provides calibration against human ratings.

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Bootstrap the calibration corpus

You have three options:

**Option A: Download past digests from GitHub Actions**

```bash
# One-time setup: authenticate with GitHub CLI
gh auth login

# Download all past digest artifacts
python evals/scripts/archive_from_github.py --repo sumoseah/daily-digest-v2
```

**Option B: Generate synthetic digests for calibration**

```bash
# Generate 25 digests with live content (takes ~20 minutes)
python evals/scripts/bulk_generate.py --count 25 --start-date 2026-01-01 --sleep 30

# Or just 10 to start
python evals/scripts/bulk_generate.py --count 10 --start-date 2026-01-01 --sleep 30
```

**Option C: Wait for real digests to accumulate**

Going forward, `agent.py` automatically archives each successful digest to `evals/data/digests/`. After 20+ runs, you'll have enough for calibration.

### 3. Score the digests

```bash
# Test the pipeline without spending API credits
python -m evals.scoring_pipeline --dry-run

# Score the first 5 digests
python -m evals.scoring_pipeline --limit 5

# Score all unscored digests
python -m evals.scoring_pipeline
```

Scores are appended to `evals/data/scores.csv`. The judge uses **claude-opus-4-5-20251101** and costs ~$0.10–0.30 per digest.

### 4. View the dashboard

```bash
streamlit run evals/dashboard.py
```

The dashboard shows:
- Overall score trends over time
- Per-dimension averages
- Flagged digests (overall score < 3.0)
- Full judge explanations for each dimension

### 5. Calibrate the judge (optional but recommended)

Before trusting the judge, manually rate 20–30 digests to verify it aligns with your preferences:

1. **Manually rate digests:** Open each digest HTML from `evals/data/digests/` and fill in `evals/data/manual_ratings.csv` with your 1–5 scores for each dimension.

2. **Run calibration:**
   ```bash
   python -m evals.calibration
   ```

3. **Review results:** The calibration report shows Pearson correlation (r) for each dimension. Target r ≥ 0.60 on all dimensions.

4. **Iterate if needed:** For dimensions with r < 0.60, read the judge's explanations in `scores.csv`, identify where your ratings diverged, and revise the rubric anchor language in `evals/rubric.md`. Then re-run the pipeline on the calibration set and re-check correlation.

## Directory Structure

```
evals/
├── __init__.py
├── judge_prompt.py              # Builds and sends judge prompts to Claude Opus
├── scoring_pipeline.py          # Batch orchestrator: load → judge → store
├── calibration.py               # Correlation checker (human vs judge)
├── dashboard.py                 # Streamlit reporting dashboard
├── rubric.md                    # 8-dimension scoring rubric
├── README.md                    # This file
├── data/
│   ├── digests/                 # Archived digest HTML files (one per run)
│   ├── scores.csv               # Judge scores (one row per digest)
│   └── manual_ratings.csv       # Your manual ratings (for calibration)
└── scripts/
    ├── archive_from_github.py   # Download past digests from GitHub Actions
    └── bulk_generate.py         # Generate synthetic digests for calibration
```

## Scoring Rubric

The judge scores 8 dimensions on a 1–5 scale:

1. **Interest Priority Adherence** (weight: 0.25) — Does the digest match user preferences in `config/user_profile.yaml`?
2. **Summary Quality** (weight: 0.20) — Do summaries add value beyond headlines?
3. **Source Diversity** (weight: 0.15) — Does the digest draw from varied sources?
4. **Signal-to-Noise** (weight: 0.15) — Is every item worth its slot?
5. **Theme & Editorial Voice** (weight: 0.10) — Is there a clear daily theme and strong editorial intro?
6. **Content Freshness** (weight: 0.10) — Are items recent (< 48 hours)?
7. **Source Failure Recovery** (weight: 0.03) — Did the agent recover gracefully from source failures?
8. **Novelty** (weight: 0.02) — Does the digest surface non-obvious finds?

See `evals/rubric.md` for full scoring criteria.

Weights are applied post-hoc in the pipeline and are **not** disclosed to the judge to prevent gaming.

## How It Works

### Judge Prompt

The judge receives four inputs for each digest:

1. **User profile** (`config/user_profile.yaml`) — The preference baseline
2. **System prompt** (`config/system_prompt.txt`) — What the agent was told to do
3. **Run metadata** (`logs/YYYY-MM-DD.json`) — Sources fetched/failed, items included, themes, etc.
4. **Digest HTML** — The actual digest to evaluate

The judge returns a structured JSON response with scores and explanations for each dimension, plus an overall score and top issue/strength.

### Archiving

Every successful digest run automatically archives the HTML to `evals/data/digests/YYYY-MM-DD_digest.html` (see `agent.py:184–190`).

### Logs

The agent already emits rich run metadata to `logs/YYYY-MM-DD.json`, including:
- `sources_fetched` / `sources_failed`
- `items_fetched` / `items_included`
- `themes`
- `tool_call_count`
- `duration_seconds`

The judge uses this metadata to score dimensions like Source Failure Recovery that aren't visible from the digest content alone.

## Calibration

**Why calibrate?** The rubric reflects your intent, but the judge's interpretation of "3 vs 4 on Interest Priority" may differ from yours. Calibration ensures you're optimizing against a metric you actually care about.

**Target:** Pearson r ≥ 0.60 on all dimensions between your manual ratings and the judge's scores.

**Iteration loop:**
1. Rate 20–30 digests manually
2. Run `python -m evals.calibration`
3. For dimensions with r < 0.60: read judge explanations, identify divergence, revise rubric anchors
4. Re-run pipeline on calibration set
5. Re-check calibration
6. Repeat until all r ≥ 0.60

## Cost

- **Judge model:** claude-opus-4-5-20251101
- **Cost per digest:** ~$0.10–0.30 (varies by digest length)
- **Evaluating 50 digests:** ~$5–15

## Notes

- The judge is one tier above the agent (Opus vs Sonnet) to prevent self-serving bias.
- If a run log doesn't exist for a digest, the judge defaults Source Failure Recovery to 5.
- HTML is sent as-is to the judge. Opus handles it well, but you can add a BeautifulSoup preprocessing step if needed.
- Weights can be adjusted in `scoring_pipeline.py` without changing the rubric.

---

*Generated from specification in `llm_judge_proposal.md` — February 2026*
