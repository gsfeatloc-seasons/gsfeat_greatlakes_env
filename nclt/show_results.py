"""Prints a GSFeatLoc NCLT summary.json as a table.

Usage: python nclt/show_results.py [results folder]
"""
import json
import sys
from pathlib import Path

folder = Path(sys.argv[1] if len(sys.argv) > 1 else "results/gsfeatloc/stretch_A_2012-08-04")
summary = json.loads((folder / "summary.json").read_text())

columns = "{:<34}{:>8}{:>11}{:>11}{:>10}{:>10}{:>10}{:>10}"
print(columns.format("Run", "Failed", "Start (m)", "Final (m)", "Final deg", "<0.25m", "<0.5m", "<1m"))
for run, r in summary.items():
    print(columns.format(
        run,
        f"{r['failed_pct']:.0f}%",
        f"{r['median_start_m']:.2f}",
        f"{r['median_m']:.2f}",
        f"{r['median_deg']:.1f}",
        f"{r['within_0.25m_2deg_pct']:.0f}%",
        f"{r['within_0.5m_5deg_pct']:.0f}%",
        f"{r['within_1.0m_10deg_pct']:.0f}%",
    ))
print("\nStart, Final and Final deg are medians. The last three columns also require 2, 5 and 10 degrees.")
