"""
Runs the agent --dry-run N times and archives each output as a sequentially dated
digest file. Used to build a calibration corpus when fewer than 20 real digests exist.

Usage:
    python evals/scripts/bulk_generate.py --count 25 --start-date 2026-01-01

Each run fetches live content from your real sources. The agent makes independent
LLM decisions each time, producing meaningful variation across runs.
"""

import subprocess
import shutil
import sys
import os
import time
import argparse
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent  # daily-digest-v2/
DIGESTS_DIR = ROOT / "evals" / "data" / "digests"
HTML_OUTPUT  = Path("/tmp/digest-v2.html")
LOG_DIR      = ROOT / "logs"


def run_agent_dry_run() -> bool:
    """Run agent.py --dry-run. Returns True if HTML was produced."""
    if HTML_OUTPUT.exists():
        HTML_OUTPUT.unlink()  # Clear previous output

    result = subprocess.run(
        [sys.executable, str(ROOT / "agent.py"), "--dry-run"],
        cwd=str(ROOT),
        env=os.environ.copy(),  # Pass environment variables to subprocess
        timeout=600,  # 10-minute ceiling matches agent constraint
    )
    return result.returncode == 0 and HTML_OUTPUT.exists()


def run(count: int, start_date: date, sleep_seconds: int) -> None:
    DIGESTS_DIR.mkdir(parents=True, exist_ok=True)

    generated = 0
    current_date = start_date

    # Skip dates that already have a digest archived
    existing_dates = {p.stem.replace("_digest", "") for p in DIGESTS_DIR.glob("*_digest.html")}

    for i in range(count):
        date_str = current_date.isoformat()

        if date_str in existing_dates:
            print(f"  [{i+1}/{count}] {date_str}: already exists, skipping")
            current_date += timedelta(days=1)
            continue

        print(f"  [{i+1}/{count}] {date_str}: running agent --dry-run...", flush=True)

        try:
            success = run_agent_dry_run()
        except subprocess.TimeoutExpired:
            print(f"    TIMEOUT on run {i+1}, skipping")
            current_date += timedelta(days=1)
            continue

        if not success:
            print(f"    Agent did not produce output on run {i+1}, skipping")
            current_date += timedelta(days=1)
            continue

        dest = DIGESTS_DIR / f"{date_str}_digest.html"
        shutil.copy(HTML_OUTPUT, dest)
        generated += 1
        print(f"    Saved to {dest.name}")

        current_date += timedelta(days=1)

        # Brief pause between runs to avoid rate limits on external sources
        if i < count - 1:
            print(f"    Waiting {sleep_seconds}s before next run...")
            time.sleep(sleep_seconds)

    print(f"\nDone. {generated} digests generated in {DIGESTS_DIR}")
    print("Note: these digests contain live content fetched today, with synthetic dates for calibration.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count",      type=int, default=25,
                        help="Number of digests to generate (default: 25)")
    parser.add_argument("--start-date", type=date.fromisoformat, default=date(2026, 1, 1),
                        help="First synthetic date to use (default: 2026-01-01)")
    parser.add_argument("--sleep",      type=int, default=30,
                        help="Seconds to wait between runs (default: 30)")
    args = parser.parse_args()
    run(args.count, args.start_date, args.sleep)
