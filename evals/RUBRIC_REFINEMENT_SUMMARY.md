# Rubric Refinement Summary

## Calibration Issues Identified

Based on manual ratings in `evals/data/manual_ratings.csv`, we found significant misalignment between human and judge scores on two dimensions:

### 1. Source Diversity (Dimension 3)
- **Problem**: Judge gave 4/5 for digests with 80% content from Simon Willison
- **User rating**: 2/5 for same digests
- **User feedback**: "80% of the content was just taken from Simon Willison. The other 20% from product hunt and tech crunch"

### 2. Novelty (Dimension 8)
- **Problem**: No mechanism to detect repeated content across consecutive days
- **User feedback**: "perhaps we should raise the novelty score slightly. Might also be better if agent is able to reference past digests within the last 2 days to check if any material that was previously curated is repeated in the current digest (in this case things like world lab raising funds was repeated from the previous day)"

## Changes Made

### Source Diversity Rubric (evals/rubric.md lines 29-42)
Added **quantitative thresholds** based on percentage from single source:

| Score | Threshold |
|-------|-----------|
| 5 | No single source exceeds 30% of items |
| 4 | One source contributes up to 40% of items |
| 3 | One source contributes 40-60% of items |
| 2 | One source contributes 60-80% of items |
| 1 | One source contributes 80%+ of items |

This change makes the rubric objective and aligns with user's intuition that 80% from one source = 2/5.

### Novelty Rubric (evals/rubric.md lines 91-103)
Added **repetition penalty**:
- Check if any items (same story/development) appeared in past 2 days' digests
- Each repeated item reduces the score by 1 point
- Updated scoring table to reference repetition explicitly

### Judge Prompt (evals/judge_prompt.py)
1. **Added `get_recent_digests()` function** (lines 46-69):
   - Retrieves digests from past 2 days for novelty comparison
   - Returns simple list of available digest dates

2. **Updated `build_judge_prompt()`** (lines 72-152):
   - Injects recent digests context into Section 4
   - Adds explicit instruction: "For Dimension 8 (Novelty), check if any items in today's digest cover the same stories/developments as the digests from the past 2 days"

3. **Updated `run_judge()`** (line 166):
   - Now passes `date_str` parameter to enable temporal context

## Testing the Updated Rubric

Created `.github/workflows/rescore-digests.yml` for targeted re-scoring:

```bash
# Via GitHub Actions UI:
# 1. Go to Actions → "Re-score Digests with Updated Rubric"
# 2. Click "Run workflow"
# 3. Enter dates: 2026-01-01,2026-01-02,2026-01-03
```

The workflow:
- Removes old scores for specified dates
- Re-runs judge with updated rubric
- Commits new scores
- Uploads artifact as backup

## Next Steps

### Option 1: Re-score all January digests (~$1.50-2.00)
Re-score all 13 Jan digests to get full calibration data with new rubric:
```bash
gh workflow run rescore-digests.yml -f dates="2026-01-01,2026-01-02,2026-01-03,2026-01-04,2026-01-05,2026-01-07,2026-01-08,2026-01-09,2026-01-11,2026-01-12,2026-01-14,2026-01-15,2026-01-16"
```

Then run calibration:
```bash
python evals/calibration.py
```

### Option 2: Test with 2-3 digests first (~$0.30)
Re-score just the problematic ones to verify rubric changes work:
```bash
gh workflow run rescore-digests.yml -f dates="2026-01-01,2026-01-02,2026-01-03"
```

Check if source_diversity_score drops from 4 to ~2 for 80% Simon Willison content.

### Option 3: Wait for new daily digests
Let the updated rubric apply naturally to new digests going forward. The Feb 19-21 digests already show better diversity (4-5 sources), so calibration should improve automatically.

## Expected Impact

**Source Diversity dimension:**
- Digests with 80% Simon Willison should now score 1/5 (was 4/5)
- This will significantly lower overall scores for Jan 1-16 test digests
- Feb 17-21 real digests should maintain high scores (already diverse)

**Novelty dimension:**
- Judge can now detect and penalize repeated stories
- Example: World Labs funding repeated on consecutive days
- Scores will better reflect discovery value vs. rehashing

**Overall calibration:**
- Pearson correlation for Source Diversity should improve from current low values
- Weighted overall scores for Jan digests should drop closer to user's manual ratings (~3.54)
- Feb digest scores should remain high (~4.5) since they already have good diversity

## Files Modified

1. `evals/rubric.md` - Added quantitative thresholds and repetition penalty
2. `evals/judge_prompt.py` - Added temporal context for novelty checking
3. `.github/workflows/rescore-digests.yml` - Created targeted re-scoring workflow
4. `evals/RUBRIC_REFINEMENT_SUMMARY.md` - This document

## Cost Estimates

- Re-scoring 1 digest: ~$0.10 (Claude Opus)
- Re-scoring 3 digests: ~$0.30
- Re-scoring 13 digests: ~$1.50-2.00
- Daily scoring going forward: ~$0.10/day

All estimates assume ~2000 token prompts + 500 token responses per judgment.
