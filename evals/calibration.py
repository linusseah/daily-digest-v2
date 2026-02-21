# evals/calibration.py

import csv
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).parent.parent
MANUAL = ROOT / "evals" / "data" / "manual_ratings.csv"
JUDGE  = ROOT / "evals" / "data" / "scores.csv"

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

DIMENSION_LABELS = {
    "interest_priority_adherence": "Interest Priority Adherence",
    "summary_quality": "Summary Quality",
    "source_diversity": "Source Diversity",
    "signal_to_noise": "Signal-to-Noise",
    "theme_and_editorial_voice": "Theme & Editorial Voice",
    "content_freshness": "Content Freshness",
    "source_failure_recovery": "Source Failure Recovery",
    "novelty": "Novelty",
}


def load_csv(path: Path) -> dict[str, dict]:
    with open(path) as f:
        return {row["digest_file"]: row for row in csv.DictReader(f)}


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return float("nan")
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denom = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
    return num / denom if denom else float("nan")


def run_calibration() -> None:
    manual = load_csv(MANUAL)
    judge  = load_csv(JUDGE)
    overlap = set(manual) & set(judge)

    if not overlap:
        print("No overlap between manual ratings and judge scores. Rate some digests first.")
        return

    print(f"Calibration report — {len(overlap)} digests in common\n")
    print(f"{'Dimension':<35} {'Pearson r':>10} {'Human avg':>10} {'Judge avg':>10}  Status")
    print("-" * 80)

    issues = []
    for dim in DIMENSIONS:
        col = f"{dim}_score"
        try:
            human = [float(manual[f][col]) for f in overlap if manual[f].get(col)]
            judge_scores = [float(judge[f][col]) for f in overlap if judge[f].get(col)]
        except (KeyError, ValueError):
            print(f"  {DIMENSION_LABELS[dim]:<33} {'N/A':>10}")
            continue

        r = pearson(human, judge_scores)
        h_avg = mean(human) if human else float("nan")
        j_avg = mean(judge_scores) if judge_scores else float("nan")
        ok = r >= 0.60
        status = "✅" if ok else "⚠️  NEEDS WORK"
        if not ok:
            issues.append(dim)
        print(f"  {DIMENSION_LABELS[dim]:<33} {r:>10.2f} {h_avg:>10.1f} {j_avg:>10.1f}  {status}")

    print()
    if issues:
        print("Dimensions needing rubric refinement:")
        for d in issues:
            print(f"  - {DIMENSION_LABELS[d]}: read judge explanations for this dimension, clarify the 3-point anchor in rubric.md, re-run")
    else:
        print("All dimensions calibrated. Judge is ready for automated use.")


if __name__ == "__main__":
    run_calibration()
