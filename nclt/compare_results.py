"""Compares GSFeatLoc results across stretches and methods in one short table.

Usage: python nclt/compare_results.py [results folder]
Uses shared_results/ if it exists (the team's shared runs), otherwise results/gsfeatloc/.
"""
import json
import sys
from pathlib import Path

SEASONS = {"2012-08-04": "summer", "2012-11-04": "fall", "2012-02-12": "winter"}
LEVEL = "start 1m 5deg"

if len(sys.argv) > 1:
    root = Path(sys.argv[1])
else:
    root = Path("shared_results") if Path("shared_results").is_dir() else Path("results/gsfeatloc")

runs = sorted(p for p in root.iterdir() if (p / "summary.json").is_file())
if not runs:
    sys.exit(f"No results in {root}/ yet.")

print(f"Results from {root}/, starting guess about 1 m and 5 degrees off.\n")
row = "{:<34}{:<8}{:>8}{:>16}{:>21}"
print(row.format("Run", "Season", "Worked", "Typical error", "Very close (<25cm)"))
print(row.format("", "", "", "", "before -> after"))
for run in runs:
    summary = json.loads((run / "summary.json").read_text())
    for session, season in SEASONS.items():
        r = summary.get(f"{session} {LEVEL}")
        if r is None:
            continue
        print(row.format(
            run.name, season,
            f"{100 - r['failed_pct']:.0f}%",
            f"{r['median_m']:.2f} m",
            f"{r['start_within_0.25m_2deg_pct']:.0f}% -> {r['within_0.25m_2deg_pct']:.0f}%",
        ))
    print()

print("Worked:        photos where GSFeatLoc found enough matches. Higher is better.")
print("Typical error: median distance from the true position after GSFeatLoc. Lower is better.")
print("Very close:    photos within 25 cm and 2 degrees, before and after GSFeatLoc. A bigger jump is better.")
print("\nFull tables for one run:  python nclt/show_results.py " + str(root / "RUN_NAME"))
