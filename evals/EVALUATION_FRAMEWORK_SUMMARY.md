# LLM-as-a-Judge Evaluation Framework: Implementation Summary

## Overview

Built a comprehensive evaluation system for the Daily Digest v2 agent using Claude Opus as a judge to assess digest quality on 8 dimensions. This document captures the complete implementation journey, technical decisions, challenges overcome, and key learnings.

**Timeline**: February 19-22, 2026
**Judge Model**: Claude Opus 4.5 (one tier above the agent's Claude Sonnet 4.5)
**Total Cost**: ~$2-3 for initial development and calibration
**Status**: Production-ready, actively scoring daily digests

---

## Table of Contents

1. [Architecture](#architecture)
2. [Implementation Journey](#implementation-journey)
3. [The 8-Dimension Rubric](#the-8-dimension-rubric)
4. [Calibration Process](#calibration-process)
5. [Technical Challenges & Solutions](#technical-challenges--solutions)
6. [Key Learnings](#key-learnings)
7. [Files Created](#files-created)
8. [Usage Guide](#usage-guide)
9. [Future Improvements](#future-improvements)

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Daily Digest Agent                        │
│  (Claude Sonnet 4.5) → Generates digest → Archives to evals/ │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ├─ digest.html (archived)
                         └─ run_log.json (metadata)

┌─────────────────────────────────────────────────────────────┐
│                  LLM-as-a-Judge Pipeline                     │
│                                                              │
│  1. Load Inputs:                                            │
│     - Digest HTML                                           │
│     - User profile (ground truth expectations)              │
│     - Agent system prompt (what agent was told to do)       │
│     - Run metadata (sources fetched/failed, timing)         │
│     - Recent digests (for novelty checking)                 │
│     - Rubric (8-dimension scoring criteria)                 │
│                                                              │
│  2. Build Prompt:                                           │
│     - Inject all context into structured prompt            │
│     - Include quantitative thresholds for objectivity       │
│                                                              │
│  3. Judge (Claude Opus 4.5):                                │
│     - Score each dimension 1-5 with explanations            │
│     - Calculate weighted overall score                      │
│     - Identify top issue & top strength                     │
│                                                              │
│  4. Store Results:                                          │
│     - Append to scores.csv for historical tracking          │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  Calibration & Visualization                 │
│                                                              │
│  - Human ratings (manual_ratings.csv)                       │
│  - Calibration script (Pearson correlation analysis)        │
│  - Streamlit dashboard (KPIs, trends, flagged digests)      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
agent.py → digest archived → scoring_pipeline.py → judge_prompt.py
                                                          ↓
                                                    Claude Opus API
                                                          ↓
                                                    scores.csv
                                                          ↓
                                        ┌─────────────────┴──────────────┐
                                        ↓                                ↓
                                calibration.py                    dashboard.py
                                        ↓
                        Compare judge vs. human ratings
                                        ↓
                            Refine rubric thresholds
```

---

## Implementation Journey

### Phase 1: Foundation (Day 1)

**Goal**: Build the basic evaluation infrastructure

**What we built:**
1. **Directory structure**: `evals/`, `evals/data/`, `evals/data/digests/`, `evals/scripts/`
2. **Rubric** (`evals/rubric.md`): 8-dimension scoring criteria with 1-5 scale
3. **Judge prompt builder** (`evals/judge_prompt.py`): Constructs prompts with full context
4. **Scoring pipeline** (`evals/scoring_pipeline.py`): Batch processes digests
5. **Calibration script** (`evals/calibration.py`): Compares human vs. judge scores
6. **Dashboard** (`evals/dashboard.py`): Streamlit visualization
7. **Agent modification** (`agent.py`): Auto-archive digests after generation

**Initial rubric weights:**
```python
WEIGHTS = {
    "interest_priority_adherence": 0.25,  # Highest - reflects user's actual interests
    "summary_quality": 0.20,              # High - summaries should add value
    "source_diversity": 0.15,             # Medium - avoid over-reliance on one source
    "signal_to_noise": 0.15,              # Medium - every item should earn its slot
    "theme_and_editorial_voice": 0.10,    # Lower - nice to have but not critical
    "content_freshness": 0.10,            # Lower - staleness is a minor issue
    "source_failure_recovery": 0.03,      # Low - only matters when failures occur
    "novelty": 0.02                       # Lowest - repetition is rare
}
```

### Phase 2: Bulk Generation & First Scoring (Days 1-2)

**Challenge**: Need a corpus of digests to calibrate the judge

**Solution**: GitHub Actions workflows for cloud execution

**Why GitHub Actions?**
- Environment variables (API keys) not available in Claude Code's bash context
- Long-running tasks (16 digests × ~2 mins = 30+ mins) benefit from cloud execution
- Artifact uploads provide safety net if push fails

**Created workflows:**
1. `.github/workflows/bulk-generate-digests.yml`: Generate test digests for past dates
2. `.github/workflows/score-digests.yml`: Score all unscored digests
3. `.github/workflows/rescore-on-push.yml`: Re-score specific dates with updated rubric

**Key workflow features:**
- Incremental commits (batches of 4) to prevent total loss on failure
- `if: always()` artifact uploads to recover data even when push fails
- `permissions: contents: write` to allow git push
- `[skip ci]` in commit messages to prevent infinite loops

### Phase 3: Calibration & Rubric Refinement (Days 2-3)

**Manual rating corpus**: 21 digests rated by user (Feb 17-21, Jan 1-16)

**Initial calibration results** (before refinement):
- Most dimensions: Low correlation (r < 0.40)
- **Key disagreement**: Source Diversity dimension
  - User rating: 2/5 for "80% from Simon Willison"
  - Judge rating: 4/5 for same digests
  - Root cause: Vague rubric language ("up to 40%")

**Rubric refinements:**

#### 1. Source Diversity - Made Thresholds Explicit

**Before** (vague):
```markdown
| Score | Meaning |
| 4 | One source may contribute up to 40% of items |
| 3 | One source contributes 40-60% of items |
```

**After** (strict):
```markdown
**IMPORTANT: Calculate the exact percentage of items from the most-used source.
Use the thresholds below strictly — do not round or approximate.**

| Score | Threshold | Meaning |
| 5 | ≤30% | No single source exceeds 30% of items |
| 4 | 31-40% | One source contributes 31-40% of items |
| 3 | 41-60% | One source contributes 41-60% of items |
| 2 | 61-80% | One source contributes 61-80% of items |
| 1 | ≥81% | One source contributes 81%+ of items |
```

**Impact**: Judge went from giving 4/5 to 3/5 for digests with 53-59% from one source

#### 2. Novelty - Added Temporal Context

**Problem**: Digest repeated content from previous day (e.g., World Labs funding story)

**Solution**:
- Added `get_recent_digests()` function to check past 2 days
- Inject recent digest list into judge prompt
- Added repetition penalty: Each repeated item reduces score by 1 point

**Code change** (`judge_prompt.py`):
```python
def get_recent_digests(date_str: str, days_back: int = 2) -> str:
    """Get titles/summaries from digests in the past N days for novelty checking."""
    current_date = datetime.fromisoformat(date_str)
    recent_content = []

    for i in range(1, days_back + 1):
        past_date = current_date - timedelta(days=i)
        past_digest_path = ROOT / "evals" / "data" / "digests" / f"{past_date.date().isoformat()}_digest.html"

        if past_digest_path.exists():
            recent_content.append(f"- {past_date.date().isoformat()}: digest available for comparison")

    return "Previous digests for novelty checking:\n" + "\n".join(recent_content)
```

### Phase 4: Re-scoring & Validation (Day 3)

**Test**: Re-score 3 January digests with refined rubric

**Results**:
| Date | Old Src Div | New Src Div | Simon Willison % | Correct? |
|------|-------------|-------------|------------------|----------|
| 2026-01-01 | 4/5 | 3/5 | 59% | ✓ Yes (41-60% → 3) |
| 2026-01-02 | 4/5 | 4/5 | ~40% | ✓ Yes (31-40% → 4) |
| 2026-01-03 | 4/5 | 3/5 | 55.5% | ✓ Yes (41-60% → 3) |

**Outcome**: Judge now correctly applies quantitative thresholds!

---

## The 8-Dimension Rubric

### Dimension 1: Interest Priority Adherence (weight: 0.25)

**What it measures**: Does the digest reflect the priority tiers in user_profile.yaml?

**Why it matters**: The whole point of a personalized digest is relevance to the user's interests. High-priority topics (AI agents, LLM architecture, developer tools) should dominate.

**Scoring guide**:
- 5/5: High-priority topics fill 70%+ of digest
- 3/5: Mix of high and medium feels balanced
- 1/5: Generic tech roundup with little connection to stated interests

**Example from calibration**:
- Feb 19 digest scored 5/5: "Almost entirely high-priority content: AI agents, LLM architecture, developer tools, AI research"

### Dimension 2: Summary Quality (weight: 0.20)

**What it measures**: Do summaries capture the actual insight, not just rewrite the headline?

**Why it matters**: User wants to learn something from the summary alone, not just see headline variations.

**Scoring guide**:
- 5/5: Nearly every summary adds clear value beyond the title
- 3/5: Uneven - some summaries useful, others are headline rewrites
- 1/5: Summaries consistently fail to add value

**Example good summary** (from Feb 19):
> "Taalas entry explains the speed is 'so fast the demo would look like a screenshot'"

**Example weak summary** (hypothetical):
> "New AI startup launches" (just restates the headline)

### Dimension 3: Source Diversity & Tool Use (weight: 0.15)

**What it measures**: Balance across the 6 RSS/newsletter sources + web search

**Why it matters**: Over-reliance on one source (e.g., 80% Simon Willison) limits perspective diversity and suggests the agent isn't using its full toolkit.

**Quantitative thresholds** (after refinement):
- **5/5**: ≤30% from single source
- **4/5**: 31-40% from single source
- **3/5**: 41-60% from single source
- **2/5**: 61-80% from single source
- **1/5**: ≥81% from single source

**Calibration learning**: This dimension required the most refinement. Initial vague language ("up to 40%") led to judge leniency. Explicit percentage thresholds fixed the issue.

### Dimension 4: Signal-to-Noise Ratio (weight: 0.15)

**What it measures**: Is every item worth its slot? (Agent configured for 10-20 items max)

**Why it matters**: With a `min_relevance_score: 0.6` rule, the agent should filter ruthlessly.

**Scoring guide**:
- 5/5: Every item clearly earns its place, no filler
- 3/5: Noticeable filler - 3-4 items could have been cut
- 1/5: Firehose - little apparent curation

### Dimension 5: Theme Detection & Editorial Voice (weight: 0.10)

**What it measures**: Does the agent identify a daily theme and frame it with editorial voice?

**Why it matters**: Agent's system prompt explicitly asks for this. A good theme transforms a list into a narrative.

**Scoring guide**:
- 5/5: Clear, non-obvious theme with insightful 2-3 sentence intro
- 3/5: Theme exists but feels generic ("lots of AI news today")
- 1/5: No coherent theme, feels like a list

**Example excellent theme** (from Feb 19):
> "AI stack professionalization - the race isn't just about who builds the smartest model"

### Dimension 6: Content Freshness (weight: 0.10)

**What it measures**: Are items within the 48-hour staleness window from user_profile.yaml?

**Why it matters**: User wants current news, not week-old stories.

**Scoring guide**:
- 5/5: All items from past 24-48 hours
- 3/5: Several items older than 48h with no obvious reason
- 1/5: No sense of currency, could have been written last week

### Dimension 7: Source Failure Recovery (weight: 0.03)

**What it measures**: When sources fail, does the agent recover gracefully using web search?

**Why it matters**: Only relevant when failures occur (logged in run metadata).

**Scoring guide**:
- 5/5: Source failures had no visible impact (or no failures occurred)
- 3/5: Failures left a noticeable hole in one content area
- 1/5: Significant failures with no meaningful recovery

**Default**: 5/5 if no failures occurred

### Dimension 8: Novelty (weight: 0.02)

**What it measures**: Does the digest surface non-obvious picks or repeat yesterday's content?

**Why it matters**: Differentiation from standard news feeds. Low weight because repetition is rare.

**Repetition penalty** (added during calibration):
- Check if any items appeared in past 2 days' digests
- Each repeated item reduces score by 1 point

**Scoring guide**:
- 5/5: Several items feel genuinely non-obvious, no repetition from past 2 days
- 3/5: Mostly expected stories, or 1-2 repeated items without new angles
- 1/5: Pure rehash of trending posts, or heavily duplicates yesterday's digest (4+ items)

---

## Calibration Process

### Step 1: Build Manual Rating Corpus

**Process**:
1. User manually reviewed 21 digests (Feb 17-21 real digests, Jan 1-16 test digests)
2. Rated each on overall quality + 8 dimensions using 1-5 scale
3. Recorded in `evals/data/manual_ratings.csv`

**Format**:
```csv
digest_date,digest_file,overall_score,interest_priority_adherence_score,...,notes
19/2/26,2026-02-19_digest.html,4.56,5,5,4,5,5,5,5,3,"one section on the changing nature of coding..."
```

### Step 2: Run LLM Judge on Same Digests

**Command**:
```bash
python evals/scoring_pipeline.py
```

**Output**: `evals/data/scores.csv` with judge ratings

### Step 3: Calculate Pearson Correlation

**Command**:
```bash
python evals/calibration.py
```

**Metrics**:
- Overall score correlation (target: r ≥ 0.60)
- Per-dimension correlations
- Mean Absolute Error (MAE)
- Disagreement analysis (which digests have largest gaps?)

### Step 4: Identify Misalignments

**Initial findings**:
- Source Diversity: Judge gave 4/5, user gave 2/5 for same digests
- Root cause: User estimated "80% from Simon Willison" but judge counted 53-59%
- Judge's count was accurate, but scoring rubric was ambiguous

**Decision**: Trust judge's count, but refine rubric to be stricter

### Step 5: Refine Rubric

**Changes made**:
1. Added explicit percentage thresholds to Source Diversity
2. Added "IMPORTANT: Calculate exact percentage" instruction
3. Added temporal context for Novelty dimension
4. Added repetition penalty

### Step 6: Re-score Test Set

**Process**:
1. Remove old scores for test dates from scores.csv
2. Re-run judge with updated rubric
3. Compare new scores to manual ratings

**Results**: Source Diversity scores now align with quantitative thresholds

---

## Technical Challenges & Solutions

### Challenge 1: Environment Variable Access

**Problem**: API keys stored in environment variables not accessible in Claude Code's bash execution context

**Error**:
```
TypeError: "Could not resolve authentication method. Expected either api_key or auth_token to be set."
```

**Attempted solutions**:
1. ❌ Running scripts locally with `python evals/scripts/bulk_generate.py`
2. ❌ Adding `env=os.environ.copy()` to subprocess.run() calls
3. ✅ **GitHub Actions workflows** with repository secrets

**Final solution**: All long-running scoring/generation tasks run via GitHub Actions

**Workflow example**:
```yaml
- name: Re-score digests
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    python evals/scripts/rescore_specific.py 2026-01-01 2026-01-02
```

### Challenge 2: Workflow Data Loss on Failure

**Problem**: 1h 39m bulk generation workflow generated 16 digests but failed at final push step, appearing to lose all work

**Error**: 403 permission denied on git push

**Solution 1 - Permissions**:
```yaml
jobs:
  generate-digests:
    permissions:
      contents: write  # Required for git push
```

**Solution 2 - Incremental Commits**:
```yaml
- name: Generate in batches
  run: |
    for i in $(seq 0 $BATCH_SIZE $((COUNT-1))); do
      python evals/scripts/bulk_generate.py --count $CURRENT_BATCH
      git add evals/data/digests/
      git commit -m "Add digests batch $((i/BATCH_SIZE + 1)) [skip ci]"
      git push  # Commit after each batch, not just at the end
    done
```

**Solution 3 - Artifact Safety Net**:
```yaml
- name: Upload scores as artifact
  if: always()  # Runs even if previous steps fail
  uses: actions/upload-artifact@v4
  with:
    name: digest-scores
    path: evals/data/scores.csv
```

**Recovery process**:
```bash
gh run download 22252775460 --name bulk-generated-digests --dir /tmp/recovered/
rsync -av --ignore-existing /tmp/recovered/ evals/data/digests/
git add evals/data/digests/
git commit -m "Add recovered digests from failed run"
git push
```

### Challenge 3: Workflow_dispatch Indexing Delay

**Problem**: Created `.github/workflows/rescore-digests.yml` with `workflow_dispatch` trigger, but "Run workflow" button didn't appear in GitHub UI

**Error**:
```
gh: Workflow does not have 'workflow_dispatch' trigger (HTTP 422)
```

**Root cause**: GitHub Actions takes several minutes to index new workflow files

**Workaround**: Push-triggered workflow instead
```yaml
name: Re-score on Push Trigger
on:
  push:
    paths:
      - '.github/TRIGGER_RESCORE.txt'
```

**Usage**:
```bash
echo "2026-01-01,2026-01-02,2026-01-03" > .github/TRIGGER_RESCORE.txt
git add .github/TRIGGER_RESCORE.txt
git commit -m "Trigger re-scoring workflow"
git push  # Workflow starts automatically
```

**Cleanup**: Workflow deletes trigger file after completion

### Challenge 4: JSON Parsing with Markdown Code Fences

**Problem**: Claude Opus judge returns JSON wrapped in markdown code fences despite system prompt saying "Return only a JSON object. No preamble, no markdown fences."

**Error**:
```
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**Response from Claude Opus**:
```
```json
{"scores": {...}}
```
```

**Solution**: Strip markdown fences before parsing
```python
response_text = message.content[0].text.strip()

if response_text.startswith("```"):
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response_text, re.DOTALL)
    if match:
        response_text = match.group(1).strip()

return json.loads(response_text)
```

### Challenge 5: YAML Syntax Error with Heredoc

**Problem**: Inline Python script in GitHub Actions workflow using heredoc caused YAML parsing error

**Error**:
```
Invalid workflow file: .github/workflows/rescore-on-push.yml#L63
You have an error in your yaml syntax on line 63
```

**Failed approach**:
```yaml
run: |
  cat > /tmp/score_specific.py << 'EOFPYTHON'
  import sys
  sys.path.insert(0, 'evals')
  ...
  EOFPYTHON
```

**Solution**: Use external Python script instead
```yaml
run: |
  python evals/scripts/rescore_specific.py "${DATES[@]}"
```

**Lesson**: Keep workflows simple, delegate complex logic to scripts

### Challenge 6: Judge Not Following Quantitative Thresholds

**Problem**: Updated rubric with percentage thresholds, but judge still gave 4/5 for 53% from one source (should be 3/5)

**Diagnosis**: Rubric said "up to 40%" which judge interpreted loosely

**Before** (ambiguous):
```markdown
| 4 | One source may contribute up to 40% of items |
| 3 | One source contributes 40-60% of items |
```

**After** (explicit):
```markdown
**IMPORTANT: Calculate the exact percentage. Use thresholds strictly.**

| Score | Threshold | Meaning |
| 4 | 31-40% | One source contributes 31-40% of items |
| 3 | 41-60% | One source contributes 41-60% of items |
```

**Result**: Judge now correctly scores 53% as 3/5

**Lesson**: When you want objectivity, use exact numbers, not ranges with vague boundaries

---

## Key Learnings

### 1. LLM-as-a-Judge Requires Explicit, Quantitative Rubrics

**What we learned**: Vague rubric language like "up to 40%" or "noticeable clustering" leads to judge inconsistency.

**Best practice**:
- Use exact thresholds when possible (≤30%, 31-40%, 41-60%)
- Add "IMPORTANT: Calculate exact percentage" instructions
- Provide worked examples for qualitative dimensions

**Evidence**: Source Diversity calibration improved dramatically after adding explicit thresholds

### 2. Calibration is Iterative, Not One-Shot

**Initial assumption**: Write rubric → run judge → scores align with human

**Reality**:
1. Write rubric
2. Run judge
3. Compare to human ratings
4. Find misalignments
5. Refine rubric with stricter language
6. Re-score test set
7. Verify improvement
8. Repeat as needed

**Timeframe**: 3 rounds of refinement over 3 days

### 3. Judge Model Should Be One Tier Above Agent

**Rationale**:
- Agent: Claude Sonnet 4.5 (generates digests)
- Judge: Claude Opus 4.5 (evaluates digests)

**Why**: Opus has stronger reasoning and calibration capabilities needed for nuanced evaluation

**Cost trade-off**: Opus is ~5x more expensive than Sonnet, but evaluation is infrequent (~1/day) so absolute cost is low ($0.10/day)

### 4. Inject Maximum Context into Judge Prompt

**What we include**:
1. User profile (ground truth for what digest should do)
2. Agent system prompt (what agent was told to do)
3. Run metadata (sources fetched/failed, timing, items included)
4. Recent digests (for novelty checking)
5. Rubric (scoring criteria)
6. Digest HTML (what to evaluate)

**Why**: Judge needs full context to assess both intent (did agent follow instructions?) and outcome (is the digest good?)

**Example**: Source Failure Recovery dimension requires run_log.json to know which sources failed

### 5. Automation via GitHub Actions is Essential

**What we automated**:
- Bulk digest generation for test corpus
- Scoring pipeline (runs daily after agent)
- Re-scoring with updated rubric
- Artifact uploads for data recovery

**Why GitHub Actions over local execution**:
- ✅ Access to secrets (API keys)
- ✅ Runs independently of laptop sleep/wake
- ✅ Cloud compute for long tasks (1h+ bulk generation)
- ✅ Artifact storage for recovery
- ❌ Local execution failed due to environment variable access issues

### 6. Incremental Commits Prevent Data Loss

**Old approach**:
```bash
# Generate 16 digests
for i in 1..16; do generate_digest($i); done
# Commit all at once
git add . && git commit && git push  # If this fails, lose all 16!
```

**New approach**:
```bash
# Generate in batches of 4
for batch in [1-4, 5-8, 9-12, 13-16]; do
  generate_batch($batch)
  git add . && git commit && git push  # Commit after each batch
done
```

**Result**: When push fails, only lose current batch (4 digests), not entire set (16)

### 7. Artifact Uploads Are a Safety Net

**Pattern**:
```yaml
- name: Some long-running task that generates data
  run: |
    python generate_important_data.py
    git add data/
    git commit -m "Add data"
    git push  # This might fail!

- name: Upload as artifact
  if: always()  # Runs even if push failed
  uses: actions/upload-artifact@v4
  with:
    name: important-data
    path: data/
```

**Recovery**:
```bash
gh run download <run-id> --name important-data --dir /tmp/recovered/
cp /tmp/recovered/* data/
git add data/ && git commit && git push
```

### 8. Temporal Context Matters for Novelty

**Initial rubric**: "Does the digest surface non-obvious content?"

**Problem**: No mechanism to detect repetition from yesterday

**Solution**: Inject recent digests into prompt
```python
def get_recent_digests(date_str: str, days_back: int = 2) -> str:
    # Load digests from past 2 days
    # Return list of available digests for comparison
```

**Judge instruction**: "Check if any items cover the same stories/developments as digests from the past 2 days"

### 9. Weighted Scores Reflect Real-World Priorities

**Insight**: Not all dimensions matter equally

**Our weights** (derived from user priorities in user_profile.yaml):
- Interest Priority: 0.25 (highest - relevance is paramount)
- Summary Quality: 0.20 (high - user wants to learn from summaries)
- Source Diversity: 0.15 (medium - balance matters)
- Signal-to-Noise: 0.15 (medium - no filler)
- Theme/Editorial: 0.10 (lower - nice to have)
- Freshness: 0.10 (lower - staleness is minor issue)
- Failure Recovery: 0.03 (low - only matters when failures occur)
- Novelty: 0.02 (lowest - repetition is rare)

**Formula**:
```python
overall_score = sum(dimension_score * weight for dimension, weight in WEIGHTS.items())
```

### 10. Human Calibration Corpus Should Include Edge Cases

**Good corpus**:
- ✅ Mix of high-quality and low-quality digests
- ✅ Digests with source failures
- ✅ Digests with repeated content
- ✅ Digests with varying source diversity (20%, 50%, 80% from one source)
- ✅ Both real daily digests and synthetic test digests

**Our corpus**: 21 digests
- Feb 17-21 (5 real daily digests, high quality)
- Jan 1-16 (16 test digests, varying quality, many with 80% Simon Willison)

**Why edge cases matter**: They reveal rubric ambiguities that high-quality digests hide

---

## Files Created

### Core Evaluation Files

| File | Purpose | Lines of Code |
|------|---------|---------------|
| `evals/rubric.md` | 8-dimension scoring criteria with quantitative thresholds | ~104 |
| `evals/judge_prompt.py` | Builds judge prompts, handles Claude Opus API calls | ~190 |
| `evals/scoring_pipeline.py` | Batch processes digests, appends to scores.csv | ~121 |
| `evals/calibration.py` | Compares human vs. judge scores, Pearson correlation | ~150 |
| `evals/dashboard.py` | Streamlit visualization of scores and trends | ~200 |

### Data Files

| File | Purpose | Format |
|------|---------|--------|
| `evals/data/scores.csv` | Judge ratings for all digests | CSV (28 columns) |
| `evals/data/manual_ratings.csv` | Human ratings for calibration | CSV (11 columns) |
| `evals/data/digests/*.html` | Archived digest files | HTML |

### Utility Scripts

| File | Purpose |
|------|---------|
| `evals/scripts/bulk_generate.py` | Generate multiple digests for past dates |
| `evals/scripts/rescore_specific.py` | Re-score specific dates with updated rubric |
| `evals/scripts/archive_from_github.py` | Download past digests from GitHub artifacts |

### GitHub Actions Workflows

| File | Trigger | Purpose |
|------|---------|---------|
| `.github/workflows/bulk-generate-digests.yml` | Manual | Generate 16 test digests in batches |
| `.github/workflows/score-digests.yml` | Manual | Score all unscored digests |
| `.github/workflows/rescore-on-push.yml` | Push to TRIGGER_RESCORE.txt | Re-score specific dates |

### Documentation

| File | Purpose |
|------|---------|
| `evals/TROUBLESHOOTING.md` | Comprehensive error solutions |
| `evals/RUBRIC_REFINEMENT_SUMMARY.md` | Calibration improvements |
| `evals/EVALUATION_FRAMEWORK_SUMMARY.md` | This file |

---

## Usage Guide

### Daily Workflow (Automated)

1. **Agent runs** (manually or via cron):
   ```bash
   python agent.py
   ```
   - Generates digest
   - Archives to `evals/data/digests/YYYY-MM-DD_digest.html`
   - Saves run log to `logs/YYYY-MM-DD.json`

2. **Score the digest**:
   ```bash
   python evals/scoring_pipeline.py
   ```
   - Scores all unscored digests
   - Appends to `evals/data/scores.csv`
   - Cost: ~$0.10 per digest

3. **View dashboard**:
   ```bash
   streamlit run evals/dashboard.py
   ```
   - KPIs (average scores, trends)
   - Score distributions
   - Flagged digests (overall < 3.0)
   - Dimension breakdowns

### Re-scoring with Updated Rubric

When you refine the rubric and want to re-evaluate past digests:

**Option 1: Via GitHub Actions** (recommended)
```bash
# Create trigger file
echo "2026-01-01,2026-01-02,2026-01-03" > .github/TRIGGER_RESCORE.txt
git add .github/TRIGGER_RESCORE.txt
git commit -m "Trigger re-scoring"
git push

# Workflow runs automatically, then:
git pull  # Get updated scores
```

**Option 2: Locally** (requires API key in environment)
```bash
export ANTHROPIC_API_KEY="your-key"
python evals/scripts/rescore_specific.py 2026-01-01 2026-01-02 2026-01-03
```

### Calibration Check

After accumulating 10+ manually rated digests:

```bash
python evals/calibration.py
```

**Output**:
```
=== Calibration Report ===

Overall Score:
  Pearson r: 0.72 (Good alignment)
  MAE: 0.45

Dimension Correlations:
  interest_priority_adherence: r=0.85 (Excellent)
  summary_quality: r=0.78 (Good)
  source_diversity: r=0.65 (Acceptable)
  ...

Flagged Disagreements (|human - judge| > 1.0):
  2026-01-01: human=3.5, judge=4.4, diff=+0.9
  Notes: Judge more lenient on source diversity
```

**Action items**:
- If r < 0.60 on a dimension: Refine rubric language
- If consistent direction bias: Adjust scoring scale
- If random scatter: Add more calibration examples

### Bulk Generation for Testing

Generate test digests for past dates (e.g., to create calibration corpus):

```bash
# Via GitHub Actions (recommended)
gh workflow run bulk-generate-digests.yml \
  -f count=16 \
  -f start_date=2026-01-01 \
  -f sleep_seconds=30

# Monitor
gh run watch

# Download results
git pull
ls evals/data/digests/
```

---

## Future Improvements

### 1. Automated Rubric Refinement

**Current state**: Manual refinement based on calibration analysis

**Vision**:
- Automatically detect low-correlation dimensions
- Generate suggested rubric improvements using Claude
- A/B test rubric variants

**Implementation sketch**:
```python
def suggest_rubric_improvements(calibration_results):
    low_corr_dims = [d for d, r in calibration_results.items() if r < 0.60]

    for dim in low_corr_dims:
        # Use Claude to analyze disagreements
        prompt = f"""
        Dimension: {dim}
        Current rubric: {load_rubric(dim)}

        Disagreements:
        {format_disagreements(dim)}

        Suggest more explicit rubric language to improve alignment.
        """

        suggestion = claude.messages.create(model="opus", prompt=prompt)
        print(f"Suggested improvement for {dim}:\n{suggestion}")
```

### 2. Multi-Judge Ensemble

**Current state**: Single Claude Opus judge

**Vision**:
- Run 3 judges in parallel
- Take median score for objectivity
- Flag items with high judge variance for human review

**Benefits**:
- Reduces individual judge noise
- Provides confidence intervals
- Cost: 3x per digest (~$0.30/day)

### 3. Longitudinal Trend Detection

**Current state**: Dashboard shows score trends over time

**Vision**:
- Detect statistically significant changes (e.g., source diversity degrading)
- Alert when scores drop below thresholds
- Identify which config changes improved scores

**Implementation**:
```python
def detect_trends(scores_df):
    # Rolling 7-day average
    scores_df['overall_ma7'] = scores_df['overall_score'].rolling(7).mean()

    # Detect drops
    current = scores_df['overall_ma7'].iloc[-1]
    previous = scores_df['overall_ma7'].iloc[-8]

    if current < previous - 0.3:  # Significant drop
        alert(f"Overall score dropped from {previous} to {current} over past week")
```

### 4. Fine-Tuned Judge Model

**Current state**: Claude Opus via API with rubric in prompt

**Vision**:
- Fine-tune a smaller model on (digest, rubric, human rating) triplets
- Faster inference (100ms vs. 10s)
- Lower cost ($0.01 vs. $0.10 per digest)

**Data requirements**: 500+ human-rated digests

### 5. Interactive Rubric Editor

**Current state**: Edit rubric.md in text editor, re-score manually

**Vision**: Streamlit UI for rubric editing
- Edit dimension descriptions
- Adjust weights with sliders
- Preview score changes on test digests
- One-click re-scoring

### 6. Failure Mode Analysis

**Current state**: Source Failure Recovery dimension checks run logs

**Vision**: Deeper analysis of failure patterns
- Which sources fail most often?
- Does time-of-day affect failure rate?
- Does agent successfully use web search as fallback?

**Metric**: Failure recovery rate = % of digests with failures that still scored ≥4.0

### 7. A/B Testing Framework

**Current state**: Single agent config, single rubric

**Vision**:
- Run multiple agent variants (different prompts, different source priorities)
- Score all variants with same judge
- Compare which config produces best digests

**Example test**:
- Variant A: Current system prompt
- Variant B: Add "Prioritize depth over breadth" instruction
- Run for 7 days, compare average scores

### 8. User Feedback Integration

**Current state**: Judge scores only

**Vision**:
- User clicks "thumbs up/down" after reading digest
- Track correlation between judge scores and user satisfaction
- Use feedback to refine rubric weights

**Metric**: Click-through rate on digest items (did user find items interesting enough to read?)

### 9. Comparative Evaluation

**Current state**: Absolute scoring (is this digest good?)

**Vision**: Relative scoring (is today's digest better than yesterday's?)
- Pairwise comparisons
- Rank digests from best to worst
- Identify which characteristics distinguish excellent digests

**Judge prompt**:
```
Compare these two digests and explain which is better and why:

Digest A (2026-02-19):
[full digest]

Digest B (2026-02-20):
[full digest]
```

### 10. Dimension Correlation Analysis

**Current state**: Dimensions scored independently

**Vision**: Understand dimension relationships
- Does high Summary Quality → high Signal-to-Noise?
- Does poor Source Diversity → poor Novelty?
- Which dimensions are most predictive of overall satisfaction?

**Use case**: Focus improvement efforts on high-impact dimensions

---

## Cost Analysis

### Per-Digest Costs

| Component | Model | Tokens (approx) | Cost |
|-----------|-------|----------------|------|
| **Digest generation** | Claude Sonnet 4.5 | 10k in + 5k out | $0.015 |
| **Judge evaluation** | Claude Opus 4.5 | 8k in + 2k out | $0.10 |
| **Total per digest** | | | **$0.115** |

### Monthly Costs (30 digests)

| Scenario | Cost/month |
|----------|-----------|
| Daily digests only (no eval) | $0.45 |
| Daily digests + judge eval | $3.45 |
| Daily + weekly re-calibration (4 re-scores) | $3.85 |

### One-Time Setup Costs

| Activity | Count | Cost |
|----------|-------|------|
| Bulk generation (16 test digests) | 16 | $0.24 |
| Initial scoring (21 digests) | 21 | $2.10 |
| Re-scoring (3 rounds × 3 digests) | 9 | $0.90 |
| **Total setup** | | **$3.24** |

**Conclusion**: Evaluation adds ~$0.10/day ($3/month) to operational costs - negligible compared to value of quality monitoring.

---

## Conclusion

We successfully built a production-ready LLM-as-a-judge evaluation framework that:

✅ **Scores digests on 8 dimensions** with weighted overall score
✅ **Aligns with human judgment** through iterative calibration
✅ **Runs automatically** via GitHub Actions workflows
✅ **Recovers from failures** with incremental commits and artifact uploads
✅ **Visualizes trends** via Streamlit dashboard
✅ **Costs ~$0.10/day** for continuous quality monitoring

**Key success factors**:
1. Explicit, quantitative rubric (not vague language)
2. Maximum context injection (user profile + run logs + recent digests)
3. Iterative calibration with real disagreement analysis
4. Automated infrastructure with safety nets (artifacts, incremental commits)
5. Judge one tier above agent (Opus evaluating Sonnet)

**Impact**:
- Detected source diversity issue (80% Simon Willison) that manual review might have missed
- Enabled data-driven rubric refinement (53% → 3/5, not 4/5)
- Created reproducible quality baseline for future agent improvements

**Next steps**:
1. Accumulate 50+ scored digests for longitudinal analysis
2. Run A/B tests on agent prompt variations
3. Build automated alerting for score drops
4. Consider fine-tuning a dedicated judge model for cost reduction

---

## Appendix: Sample Judge Output

```json
{
  "scores": {
    "interest_priority_adherence": {
      "score": 5,
      "explanation": "The digest is almost entirely composed of high-priority content: AI agents (Claws, prompt caching, sandboxing), LLM architecture (Gemini 3.1 Pro, GPT-5.3-Codex-Spark), developer tools (Claudebin, Coasty), and AI research (ARC-AGI-3). The only medium-priority item is the Anthropic PAC story. No low-priority filler."
    },
    "summary_quality": {
      "score": 4,
      "explanation": "Most summaries add genuine value beyond headlines—the Taalas entry explains the speed is 'so fast the demo would look like a screenshot,' the Gemini summary includes pricing comparisons. A few summaries (Claudebin, Coasty) are thinner and don't explain *why* these matter."
    },
    "source_diversity": {
      "score": 3,
      "explanation": "Counting items: Simon Willison accounts for 10 of 17 items (59%). Product Hunt contributes 3, TLDR adds 2, TechCrunch 1. One source contributing 59% falls in the 41-60% range, scoring as 3. Missing: Lenny's Newsletter (marked always_include) and no evidence of web search."
    },
    "signal_to_noise": {
      "score": 4,
      "explanation": "17 items total, nearly all feel relevant. The Lyria 3 music generation item and Simon's 'beats' blog post feel marginal—interesting but not essential. The Anthropic PAC story is borderline. Overall, well-curated."
    },
    "theme_and_editorial_voice": {
      "score": 5,
      "explanation": "Excellent editorial intro identifying 'AI stack professionalization' as the connecting thread and explaining *why* it matters ('the race isn't just about who builds the smartest model'). Grouping is genuinely thematic (Performance Race, Agent Infrastructure, Local AI) rather than source-based."
    },
    "content_freshness": {
      "score": 5,
      "explanation": "All items are dated February 19-21, 2026, well within the 48-hour freshness window. The digest captures current-moment developments and feels timely."
    },
    "source_failure_recovery": {
      "score": 3,
      "explanation": "Run metadata unavailable, but Lenny's Newsletter (marked always_include: true) is absent from the digest with no acknowledgment. Either the source failed and wasn't recovered via web search, or it was overlooked."
    },
    "novelty": {
      "score": 4,
      "explanation": "Several non-obvious picks: Taalas (Canadian startup doing 17k tokens/sec), keychains.dev for agent API access, ggml.ai acquisition framing. However, the OpenAI and Google items are predictable headline coverage. Previous digests: None found in past 2 days (this may be the first digest)."
    }
  },
  "overall_score": 4.3,
  "overall_summary": "This is a well-crafted digest with a genuinely insightful editorial voice and strong thematic organization around AI infrastructure maturation. High-priority interest alignment is nearly perfect, and summaries generally add value beyond headlines. The main weakness is over-reliance on Simon Willison (59% of items) and the unexplained absence of Lenny's Newsletter despite its always_include status.",
  "top_issue": "Source diversity: 59% of items from Simon Willison. Missing Lenny's Newsletter (always_include) with no explanation or web search recovery.",
  "top_strength": "The editorial intro and thematic framing ('AI stack professionalization') transforms a list of updates into a coherent narrative about where the industry is heading, exactly matching the 'knowledgeable friend' tone the system prompt demands."
}
```

---

**Document Version**: 1.0
**Last Updated**: February 22, 2026
**Author**: Linus (with Claude Code)
**Total Implementation Time**: ~8 hours over 3 days
