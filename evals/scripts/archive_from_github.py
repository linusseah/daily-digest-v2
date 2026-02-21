"""
Downloads all past digest HTML artifacts from GitHub Actions into evals/data/digests/.

Prerequisites:
    gh auth login   (one-time setup)
    pip install PyGithub  (or just use gh CLI subprocess calls)

Usage:
    python evals/scripts/archive_from_github.py --repo sumoseah/daily-digest-v2
"""

import subprocess
import json
import shutil
import tempfile
import argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent  # daily-digest-v2/
DIGESTS_DIR = ROOT / "evals" / "data" / "digests"


def list_workflow_runs(repo: str) -> list[dict]:
    """Return all completed workflow runs using gh CLI."""
    result = subprocess.run(
        ["gh", "run", "list", "--repo", repo, "--status", "completed",
         "--limit", "100", "--json", "databaseId,createdAt,conclusion"],
        capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def download_artifact(repo: str, run_id: int, dest_path: Path) -> bool:
    """
    Download artifacts for a given run ID directly to dest_path.
    The digest artifact is named 'digest-html' in the workflow.
    Returns True if successful, False otherwise.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            ["gh", "run", "download", str(run_id),
             "--repo", repo, "--dir", tmpdir],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return False  # No artifact for this run (e.g. fallback ran instead)

        # Find the HTML file in the downloaded artifact
        html_files = list(Path(tmpdir).rglob("*.html"))
        if not html_files:
            return False

        # Copy the HTML file to the destination before tmpdir is cleaned up
        shutil.copy(html_files[0], dest_path)
        return True


def run(repo: str) -> None:
    DIGESTS_DIR.mkdir(parents=True, exist_ok=True)
    runs = list_workflow_runs(repo)
    print(f"Found {len(runs)} completed runs on {repo}")

    archived = 0
    for run in runs:
        run_id = run["databaseId"]
        # Parse date from createdAt: "2026-02-15T07:03:12Z" -> "2026-02-15"
        date_str = run["createdAt"][:10]
        dest_path = DIGESTS_DIR / f"{date_str}_digest.html"

        if dest_path.exists():
            print(f"  {date_str}: already archived, skipping")
            continue

        if run["conclusion"] != "success":
            print(f"  {date_str}: run {run_id} did not succeed ({run['conclusion']}), skipping")
            continue

        success = download_artifact(repo, run_id, dest_path)
        if not success:
            print(f"  {date_str}: no HTML artifact found for run {run_id}")
            continue

        print(f"  {date_str}: archived from run {run_id}")
        archived += 1

    print(f"\nDone. {archived} new digests archived to {DIGESTS_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="sumoseah/daily-digest-v2")
    args = parser.parse_args()
    run(args.repo)
