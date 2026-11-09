"""Prints accuracy from a GSFeatLoc results.json, using the paper's success criterion."""
import json
import sys

import numpy as np

results = json.load(open(sys.argv[1]))
rot = np.array([r["rotation_error"] for r in results])
trs = np.array([r["translation_error"] for r in results])
secs = np.array([r["seconds_per_frame"] for r in results])

gt_positions = np.array([np.array(r["T_gt"])[:3, 3] for r in results])
radius = np.linalg.norm(gt_positions - gt_positions.mean(axis=0), axis=1).mean()
trs_norm = trs / radius

# On failure the CLI returns the starting pose, so these frames must be counted separately.
unchanged = np.array([np.allclose(r["T_pred"], r["T_init"]) for r in results])

print(f"Frames: {len(results)}")
print(f"Trajectory radius: {radius:.3f}")
print(f"Mean rotation error: {rot.mean():.2f} deg | median {np.median(rot):.2f} deg")
print(f"Mean normalized translation error: {trs_norm.mean():.3f} | median {np.median(trs_norm):.3f}")
print(f"Success (rotation < 5 deg and normalized translation < 0.05): {100 * np.mean((rot < 5) & (trs_norm < 0.05)):.2f}%")
print(f"Frames where pose estimation failed: {unchanged.sum()}")
print(f"Mean seconds per frame: {secs.mean():.3f}")
