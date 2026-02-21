# evals/scoring_pipeline.py

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path so we can import judge_prompt
sys.path.insert(0, str(Path(__file__).parent))
from judge_prompt import run_judge

ROOT = Path(__file__).parent.parent
DIGESTS_DIR = ROOT / "evals" / "data" / "digests"
SCORES_CSV = ROOT / "evals" / "data" / "scores.csv"

DIMENSIONS = [
    "interest_priority_adherence",
    "summary_quality",
    "source_diversity",
    "signal_to_noise",
    "theme_and_editorial_voice",
    "content_freshness",
    "source_failure_recovery",
    "novelty",
]

CSV_HEADERS = (
    ["digest_date", "digest_file", "overall_score", "top_issue", "top_strength", "overall_summary"]
    + [f"{d}_score" for d in DIMENSIONS]
    + [f"{d}_explanation" for d in DIMENSIONS]
    + ["sources_fetched", "sources_failed", "items_fetched", "items_included", "judged_at"]
)


def load_already_scored() -> set[str]:
    if not SCORES_CSV.exists():
        return set()
    with open(SCORES_CSV) as f:
        return {row["digest_file"] for row in csv.DictReader(f)}


def load_log_metadata(date_str: str) -> dict:
    """Load key fields from the agent's run log for a given date."""
    log_path = ROOT / "logs" / f"{date_str}.json"
    if not log_path.exists():
        return {}
    log = json.loads(log_path.read_text())
    return {
        "sources_fetched": "|".join(log.get("sources_fetched", [])),
        "sources_failed": "|".join(log.get("sources_failed", [])),
        "items_fetched": log.get("items_fetched", ""),
        "items_included": log.get("items_included", ""),
    }


def append_score(row: dict) -> None:
    file_exists = SCORES_CSV.exists()
    with open(SCORES_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def run_pipeline(limit: int | None = None, dry_run: bool = False) -> None:
    already_scored = load_already_scored()
    digest_files = sorted(DIGESTS_DIR.glob("*_digest.html"))

    if limit:
        digest_files = digest_files[:limit]

    for digest_file in digest_files:
        if digest_file.name in already_scored:
            print(f"  Skipping {digest_file.name} (already scored)")
            continue

        # Extract date from filename: 2026-01-15_digest.html → 2026-01-15
        date_str = digest_file.stem.replace("_digest", "")
        print(f"  Judging {date_str}...", end=" ", flush=True)

        if dry_run:
            print("[dry-run, skipped]")
            continue

        try:
            result = run_judge(date_str)
        except Exception as e:
            print(f"ERROR: {e}")
            continue

        log_meta = load_log_metadata(date_str)

        row = {
            "digest_date": date_str,
            "digest_file": digest_file.name,
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

        append_score(row)
        print(f"overall={result['overall_score']:.1f}/5")

    print("Pipeline complete.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Max digests to judge")
    parser.add_argument("--dry-run", action="store_true", help="Validate setup without calling API")
    args = parser.parse_args()
    run_pipeline(limit=args.limit, dry_run=args.dry_run)
