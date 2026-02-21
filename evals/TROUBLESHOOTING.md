# Evaluation System - Troubleshooting & Lessons Learned

This document captures common issues encountered and their solutions when working with the Daily Digest evaluation system.

## Table of Contents
1. [Environment Variables](#environment-variables)
2. [GitHub Actions Workflows](#github-actions-workflows)
3. [Scoring Pipeline Issues](#scoring-pipeline-issues)
4. [Data Management](#data-management)
5. [Best Practices](#best-practices)

---

## Environment Variables

### Issue: Missing API Keys When Running Scripts Locally

**Problem:**
```
ERROR: Missing required environment variables: ANTHROPIC_API_KEY, GMAIL_ADDRESS, GMAIL_APP_PASS, RESEND_API_KEY
```

**Root Cause:**
Scripts like `bulk_generate.py` and `scoring_pipeline.py` require environment variables that aren't available in the bash/terminal session.

**Solution:**
✅ **Use GitHub Actions workflows instead of running locally**
- Bulk generation: Use `.github/workflows/bulk-generate-digests.yml`
- Scoring: Use `.github/workflows/score-digests.yml`
- GitHub secrets are automatically available in workflows

**Why This Works:**
- GitHub secrets (ANTHROPIC_API_KEY, etc.) are configured once in repository settings
- Workflows have access to these secrets automatically
- No need to manage environment variables locally

**Alternative (If You Must Run Locally):**
Create a `.env` file (already in `.gitignore`):
```bash
ANTHROPIC_API_KEY=your-key
GMAIL_ADDRESS=your-email
GMAIL_APP_PASS=your-password
RESEND_API_KEY=your-key
```

Then load it before running:
```bash
export $(cat .env | xargs)
python -m evals.scoring_pipeline
```

---

## GitHub Actions Workflows

### Issue 1: Workflow Failed with 403 Permission Error

**Problem:**
```
fatal: unable to access 'https://github.com/...': The requested URL returned error: 403
##[error]Process completed with exit code 128
```

**Root Cause:**
GitHub Actions default token doesn't have write permissions to push commits back to the repository.

**Solution:**
✅ **Add permissions to workflow file:**
```yaml
jobs:
  your-job-name:
    runs-on: ubuntu-latest
    permissions:
      contents: write  # Allow pushing commits
```

**Files Fixed:**
- `.github/workflows/bulk-generate-digests.yml`
- `.github/workflows/score-digests.yml`

---

### Issue 2: Lost All Progress When Workflow Failed

**Problem:**
Workflow ran for 1.5 hours generating 16 digests, then failed at the push step. All work appeared lost.

**Root Cause:**
Original workflow only committed/pushed at the very end after generating all digests.

**Solution:**
✅ **Implement incremental commits:**
- Generate in batches (e.g., 4 digests at a time)
- Commit and push after each batch
- Always upload artifacts as backup

**Implementation:**
```yaml
- name: Generate in batches
  run: |
    for i in $(seq 0 4 $((COUNT-1))); do
      # Generate batch
      python script.py --count 4 --offset $i

      # Commit this batch
      git add output/
      git commit -m "Batch $i"
      git push
    done
```

**Artifacts as Fallback:**
Even if push fails, artifacts can be recovered:
```yaml
- name: Upload artifacts
  if: always()  # Run even if previous steps fail
  uses: actions/upload-artifact@v4
  with:
    name: generated-files
    path: output/*.html
    retention-days: 90
```

**Recovery from Failed Run:**
```bash
gh run download <run-id> --name artifact-name --dir /tmp/recovered/
rsync -av --ignore-existing /tmp/recovered/ evals/data/digests/
```

---

### Issue 3: Workflow Didn't Process All Files

**Problem:**
Workflow completed successfully but only processed 4 out of 18 digests.

**Root Cause:**
Files weren't committed to the repository, so the workflow couldn't see them.

**Solution:**
✅ **Always commit generated files before running dependent workflows:**

```bash
# After generating digests locally or recovering from artifacts
git add evals/data/digests/
git commit -m "Add digests"
git push

# THEN run the scoring workflow
```

**Checklist Before Running Scoring:**
- [ ] All digest files are in `evals/data/digests/`
- [ ] Files are committed and pushed to GitHub
- [ ] Run `git status` to verify nothing is uncommitted
- [ ] Check GitHub repo to confirm files are there

---

## Scoring Pipeline Issues

### Issue 1: JSON Parsing Errors

**Problem:**
```
Judging 2026-02-17... ERROR: Expecting value: line 1 column 1 (char 0)
```

**Root Cause:**
Claude Opus sometimes returns JSON wrapped in markdown code fences despite instructions not to:
```
```json
{"scores": {...}}
```
```

**Solution:**
✅ **Strip markdown code fences before parsing:**

```python
import re

response_text = message.content[0].text.strip()

# Remove markdown code fences if present
if response_text.startswith("```"):
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response_text, re.DOTALL)
    if match:
        response_text = match.group(1).strip()

return json.loads(response_text)
```

**File Fixed:**
- `evals/judge_prompt.py:138-151`

---

### Issue 2: Some Digests Can't Be Scored

**Problem:**
Certain digests consistently fail during scoring.

**Potential Causes:**
1. **Missing log files** - Digest has no corresponding `logs/YYYY-MM-DD.json`
2. **Malformed HTML** - Digest HTML is corrupted or invalid
3. **Token limit exceeded** - Digest + rubric + profile is too large

**Solutions:**

**For Missing Logs:**
The judge handles this gracefully - logs are optional. Dimension 7 (Source Failure Recovery) defaults to 5/5 when no log exists.

**For Large Digests:**
Increase max_tokens in `judge_prompt.py`:
```python
message = client.messages.create(
    model=JUDGE_MODEL,
    max_tokens=4096,  # Increased from 2048
    ...
)
```

**For Debugging:**
Add verbose error logging to `scoring_pipeline.py`:
```python
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()  # Full error trace
    continue
```

---

## Data Management

### Issue: Digest Files Not Syncing

**Problem:**
Generated digests exist locally but workflows don't see them.

**Root Cause:**
Files aren't committed to git.

**Solution:**
✅ **Verification checklist:**
```bash
# 1. Check local files exist
ls -la evals/data/digests/*.html

# 2. Check git status
git status

# 3. Add and commit if needed
git add evals/data/digests/
git commit -m "Add digests"
git push

# 4. Verify on GitHub
# Visit: https://github.com/[user]/daily-digest-v2/tree/main/evals/data/digests
```

---

### Issue: Duplicate or Missing Scores

**Problem:**
Scoring pipeline skips digests that should be scored, or scores them twice.

**How Skipping Works:**
```python
def load_already_scored() -> set[str]:
    with open(SCORES_CSV) as f:
        return {row["digest_file"] for row in csv.DictReader(f)}
```

**To Re-score a Digest:**
1. Remove its row from `evals/data/scores.csv`
2. Run the scoring pipeline again

**To Force Re-score All:**
```bash
# Backup current scores
cp evals/data/scores.csv evals/data/scores.backup.csv

# Keep only header
head -n 1 evals/data/scores.csv > evals/data/scores.new.csv
mv evals/data/scores.new.csv evals/data/scores.csv

# Re-run scoring
# (via GitHub Actions workflow)
```

---

## Best Practices

### 1. Always Use GitHub Actions for Long-Running Tasks

**Do:**
- ✅ Use workflows for bulk generation
- ✅ Use workflows for scoring
- ✅ Let workflows handle commits/pushes
- ✅ Use artifacts as backup

**Don't:**
- ❌ Run `bulk_generate.py` locally
- ❌ Run `scoring_pipeline.py` locally
- ❌ Manually set environment variables
- ❌ Keep laptop open for long tasks

---

### 2. Incremental Commits > Batch Commits

**Principle:**
Commit and push frequently to avoid losing work.

**Implementation:**
- Generate/process in small batches (4-5 items)
- Commit after each batch
- Use `if: always()` for artifact uploads
- Add `[skip ci]` to commit messages to avoid triggering other workflows

---

### 3. Recovery Strategy

**Before Running Expensive Operations:**
```bash
# 1. Check current state
git status
ls -la evals/data/digests/
wc -l evals/data/scores.csv

# 2. Verify GitHub sync
git pull
git push --dry-run

# 3. Document intent
echo "About to run scoring on 18 digests, expect ~$5 API cost"
```

**After Workflow Failures:**
```bash
# 1. Check artifacts
gh run view <run-id>
gh run download <run-id>

# 2. Check partial commits
git log --oneline -10

# 3. Recover what succeeded
# (artifacts, partial commits, etc.)
```

---

### 4. Cost Management

**Judge Costs (Claude Opus):**
- ~$0.10-0.30 per digest
- 20 digests = ~$2-6
- 100 digests = ~$10-30

**Best Practices:**
1. Start with `--limit 5` to test
2. Review first 5 results before scoring all
3. Monitor costs in Anthropic console
4. Use `--dry-run` for pipeline testing

**Testing Without Cost:**
```bash
# Test the pipeline without calling API
python -m evals.scoring_pipeline --dry-run
```

---

### 5. Workflow Monitoring

**During Workflow Execution:**
1. Click on the running workflow
2. Expand "Generate/Score" step
3. Watch real-time logs
4. Look for:
   - "Judging X... overall=Y/5" (success)
   - "ERROR:" (failure)
   - "Skipping X (already scored)" (expected)

**After Completion:**
```bash
# Check latest run
gh run list --workflow=score-digests.yml --limit 1

# View logs
gh run view <run-id> --log

# Download artifacts
gh run download <run-id>
```

---

## Quick Reference

### Common Commands

```bash
# Pull latest scores
git pull

# Check digest inventory
ls -1 evals/data/digests/*.html | wc -l

# Check scored count
wc -l evals/data/scores.csv

# Find unscored digests
python3 -c "
import csv
from pathlib import Path
scored = set()
with open('evals/data/scores.csv') as f:
    scored = {row['digest_file'] for row in csv.DictReader(f)}
all_digests = [d.name for d in Path('evals/data/digests').glob('*.html')]
unscored = [d for d in all_digests if d not in scored]
print(f'Unscored: {len(unscored)}')
for d in unscored: print(f'  {d}')
"

# View dashboard
streamlit run evals/dashboard.py

# Download artifacts from failed run
gh run download <run-id> --name bulk-generated-digests
```

---

### Workflow URLs

- **Bulk Generate:** https://github.com/linusseah/daily-digest-v2/actions/workflows/bulk-generate-digests.yml
- **Score Digests:** https://github.com/linusseah/daily-digest-v2/actions/workflows/score-digests.yml
- **Daily Digest:** https://github.com/linusseah/daily-digest-v2/actions/workflows/digest.yml

---

## When Things Go Wrong

### Checklist

1. **Check git status**
   ```bash
   git status
   git log --oneline -5
   ```

2. **Check file inventory**
   ```bash
   ls -la evals/data/digests/
   ls -la evals/data/*.csv
   ```

3. **Check GitHub sync**
   ```bash
   git pull
   git push --dry-run
   ```

4. **Check workflow status**
   ```bash
   gh run list --limit 5
   ```

5. **Check for artifacts**
   ```bash
   gh run view <run-id>
   ```

6. **Review this document** for similar issues

---

## Future Improvements

### Potential Enhancements

1. **Auto-retry on JSON parse errors**
   - Catch parsing errors and retry with adjusted prompt
   - Add explicit "return ONLY JSON, no markdown" emphasis

2. **Progress notifications**
   - Send Slack/email notifications when workflows complete
   - Post summary to GitHub issue/PR

3. **Cost tracking**
   - Log API costs to CSV
   - Add budget alerts

4. **Automated calibration**
   - Compare new scores against calibration set
   - Alert if correlation drops below threshold

5. **Streaming scores**
   - Commit each score individually
   - Real-time dashboard updates

---

*Last Updated: 2026-02-21*
*Maintainer: Linus Seah*
