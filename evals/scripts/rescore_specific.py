#!/usr/bin/env python3
"""Re-score specific digests by date."""

import sys
import csv
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from judge_prompt import run_judge
from scoring_pipeline import load_log_metadata, DIMENSIONS, SCORES_CSV, CSV_HEADERS
from datetime import datetime


def remove_scores_for_dates(dates: list[str]) -> None:
    """Remove existing scores for the given dates."""
    if not SCORES_CSV.exists():
        return

    with open(SCORES_CSV) as f:
        reader = csv.DictReader(f)
        rows = [row for row in reader if row["digest_date"] not in dates]

    with open(SCORES_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Removed existing scores for: {', '.join(dates)}")


def score_digest(date_str: str) -> None:
    """Score a specific digest by date."""
    print(f"Scoring {date_str}...", flush=True)

    try:
        result = run_judge(date_str)
        log_meta = load_log_metadata(date_str)

        row = {
            "digest_date": date_str,
            "digest_file": f"{date_str}_digest.html",
            "overall_score": result["overall_score"],
            "top_issue": result["top_issue"],
            "top_strength": result["top_strength"],
            "overall_summary": result["overall_summary"],
            "judged_at": datetime.utcnow().isoformat(),
            **log_meta,
        }
        for dim in DIMENSIONS:
            row[f"{dim}_score"] = result["scores"][dim]["score"]
            row[f"{dim}_explanation"] = result["scores"][dim]["explanation"]

        # Append to CSV
        with open(SCORES_CSV, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writerow(row)

        print(f"✓ {date_str}: overall={result['overall_score']:.1f}/5, source_diversity={result['scores']['source_diversity']['score']}/5")
    except Exception as e:
        print(f"✗ Failed to score {date_str}: {e}")
        raise


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python rescore_specific.py DATE1 [DATE2 ...]")
        print("Example: python rescore_specific.py 2026-01-01 2026-01-02 2026-01-03")
        sys.exit(1)

    dates = sys.argv[1:]
    print(f"Re-scoring {len(dates)} digest(s) with updated rubric...")
    print()

    remove_scores_for_dates(dates)
    print()

    for date in dates:
        score_digest(date)
        print()

    print("✓ Re-scoring complete!")
