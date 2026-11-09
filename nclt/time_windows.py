"""Finds when the robot was on the stretch in each NCLT session.

Usage: time_windows.py STRETCH_JSON OUT_DIR SESSION [SESSION ...]
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

GT_DIR = Path("data/nclt/ground_truth")
MAX_DISTANCE_M = 8.0
MERGE_GAP_S = 2.0
MIN_SEGMENT_S = 3.0
PAD_S = 1.0


def main(stretch_path, out_dir, sessions):
    stretch = np.array(json.loads(Path(stretch_path).read_text()))
    tree = cKDTree(stretch)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for session in sessions:
        rows = np.genfromtxt(GT_DIR / f"groundtruth_{session}.2hz.txt", delimiter=",", usecols=(0, 1, 2))
        rows = rows[np.isfinite(rows).all(axis=1)]
        t = rows[:, 0] / 1e6
        on_stretch = tree.query(rows[:, 1:3])[0] <= MAX_DISTANCE_M

        segments = []
        for time in t[on_stretch]:
            if segments and time - segments[-1][1] <= MERGE_GAP_S:
                segments[-1][1] = float(time)
            else:
                segments.append([float(time), float(time)])
        segments = [[a - PAD_S, b + PAD_S] for a, b in segments if b - a >= MIN_SEGMENT_S]

        seconds = sum(b - a for a, b in segments)
        coverage = (cKDTree(rows[on_stretch, 1:3]).query(stretch)[0] <= MAX_DISTANCE_M).mean() if on_stretch.any() else 0.0
        print(f"{session}: {len(segments)} passes, {seconds:.0f} s, covers {100 * coverage:.0f}% of the stretch")
        (out_dir / f"windows_{session}.json").write_text(json.dumps(
            [[int(a * 1e6), int(b * 1e6)] for a, b in segments]
        ))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
