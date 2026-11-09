"""Undistorts NCLT Ladybug3 images using the dataset's per-pixel maps."""
import re
from pathlib import Path

import cv2
import numpy as np

CALIB_DIR = Path("data/nclt/calib")


def load_map(camera):
    """Returns (map_u, map_v) for cv2.remap, caching the parsed text file."""
    cache = CALIB_DIR / f"U2D_Cam{camera}.npz"
    if cache.exists():
        data = np.load(cache)
        return data["map_u"], data["map_v"]
    path = next(CALIB_DIR.rglob(f"U2D_Cam{camera}_*.txt"))
    with open(path) as handle:
        numbers = re.sub(r"[^0-9,]", "", handle.readline()).split(",")
    width, height = int(numbers[0]), int(numbers[1])
    rows = np.loadtxt(path, skiprows=1, dtype=np.float32)
    map_u = np.zeros((height, width), np.float32)
    map_v = np.zeros((height, width), np.float32)
    row, col = rows[:, 0].astype(int), rows[:, 1].astype(int)
    map_u[row, col] = rows[:, 3]
    map_v[row, col] = rows[:, 2]
    np.savez(cache, map_u=map_u, map_v=map_v)
    return map_u, map_v


def undistort(image, camera):
    map_u, map_v = load_map(camera)
    return cv2.remap(image, map_u, map_v, cv2.INTER_LINEAR)
