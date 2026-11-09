"""Optional: ranks stretches of the NCLT route by how building-heavy they are.

Stretch A is already saved in nclt/stretch_A.json, so the pipeline does not need this.
Needs the 2 Hz ground truth files from step 1. Writes data/nclt/map/candidates.json.
"""
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from matplotlib.path import Path as Polygon
from scipy.ndimage import binary_dilation, distance_transform_edt
from scipy.spatial import cKDTree

GT_DIR = Path("data/nclt/ground_truth")
MAP_DIR = Path("data/nclt/map")
MAP_SESSION = "2012-08-04"
OTHER_SESSIONS = ["2012-11-04", "2012-02-12"]
WINDOW_M = 250.0
STEP_M = 25.0
COVER_M = 5.0
NEAR_BUILDING_M = 20.0
NEAR_TREE_M = 10.0
MIN_OUTDOOR = 0.97
MIN_COVER = 0.90
OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

# NCLT paper, Table 3.
LAT0, LON0 = math.radians(42.293227), math.radians(-83.709657)
RE, RP = 6378135.0, 6356750.0
_d = (RE * math.cos(LAT0)) ** 2 + (RP * math.sin(LAT0)) ** 2
RNS = (RE * RP) ** 2 / _d ** 1.5
REW = RE ** 2 / math.sqrt(_d)


def to_local(lat, lon):
    """Degrees to NCLT north, east in metres."""
    north = np.sin(np.radians(lat) - LAT0) * RNS
    east = np.sin(np.radians(lon) - LON0) * REW * math.cos(LAT0)
    return north, east


def to_latlon(north, east):
    lat = math.asin(north / RNS) + LAT0
    lon = math.asin(east / (REW * math.cos(LAT0))) + LON0
    return math.degrees(lat), math.degrees(lon)


def load_path(session):
    rows = np.genfromtxt(GT_DIR / f"groundtruth_{session}.2hz.txt", delimiter=",", usecols=(0, 1, 2))
    rows = rows[np.isfinite(rows).all(axis=1)]
    return rows[:, 0] / 1e6, rows[:, 1:3]


def fetch_osm(bounds):
    cache = MAP_DIR / "osm.json"
    if cache.exists():
        return json.loads(cache.read_text())
    south, west = to_latlon(bounds[0], bounds[2])
    north, east = to_latlon(bounds[1], bounds[3])
    bbox = f"{south:.6f},{west:.6f},{north:.6f},{east:.6f}"
    query = (
        f"[out:json][timeout:90];("
        f'way["building"]({bbox});relation["building"]({bbox});'
        f'node["natural"="tree"]({bbox});way["natural"="tree_row"]({bbox});'
        f'way["natural"="wood"]({bbox});way["landuse"="forest"]({bbox});'
        f");out geom;"
    )
    last_error = None
    for server in OVERPASS_SERVERS:
        request = urllib.request.Request(
            server,
            data=urllib.parse.urlencode({"data": query}).encode(),
            headers={"User-Agent": "nclt-stretch-selection/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                text = response.read().decode()
            data = json.loads(text)
            cache.write_text(text)
            print(f"Map data from {server}: {len(data['elements'])} features")
            return data
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            print(f"{server} failed: {error}")
            last_error = error
            time.sleep(5)
    raise RuntimeError(f"All map servers failed: {last_error}")


def ring(geometry):
    return np.array([to_local(p["lat"], p["lon"]) for p in geometry])


def main():
    MAP_DIR.mkdir(parents=True, exist_ok=True)
    t, path = load_path(MAP_SESSION)
    others = {s: load_path(s)[1] for s in OTHER_SESSIONS}
    every = np.vstack([path, *others.values()])
    pad = 60.0
    bounds = (every[:, 0].min() - pad, every[:, 0].max() + pad, every[:, 1].min() - pad, every[:, 1].max() + pad)
    osm = fetch_osm(bounds)

    buildings, tree_rings, tree_points = [], [], []
    for element in osm["elements"]:
        tags = element.get("tags", {})
        if "building" in tags:
            if element["type"] == "way" and "geometry" in element:
                buildings.append(ring(element["geometry"]))
            elif element["type"] == "relation":
                for member in element.get("members", []):
                    if member.get("role") == "outer" and "geometry" in member:
                        buildings.append(ring(member["geometry"]))
        elif element["type"] == "node":
            tree_points.append(to_local(element["lat"], element["lon"]))
        elif "geometry" in element:
            r = ring(element["geometry"])
            if tags.get("natural") == "tree_row":
                tree_points.extend(map(tuple, r))
            else:
                tree_rings.append(r)

    # 1 m raster. Rows are north, columns are east.
    n0, e0 = bounds[0], bounds[2]
    rows, cols = int(bounds[1] - n0) + 1, int(bounds[3] - e0) + 1
    grid_e, grid_n = np.meshgrid(np.arange(cols) + e0, np.arange(rows) + n0)
    cells = np.c_[grid_n.ravel(), grid_e.ravel()]

    def rasterize(polygons):
        mask = np.zeros((rows, cols), bool)
        for polygon in polygons:
            lo, hi = polygon.min(axis=0), polygon.max(axis=0)
            box = np.all((cells >= lo) & (cells <= hi), axis=1)
            if box.any():
                inside = Polygon(polygon).contains_points(cells[box])
                mask.ravel()[np.flatnonzero(box)[inside]] = True
        return mask

    building_mask = rasterize(buildings)
    tree_mask = rasterize(tree_rings)
    for north, east in tree_points:
        i, j = int(north - n0), int(east - e0)
        if 0 <= i < rows and 0 <= j < cols:
            tree_mask[i, j] = True
    building_distance = distance_transform_edt(~building_mask)
    tree_distance = distance_transform_edt(~tree_mask) if tree_mask.any() else np.full((rows, cols), 1e6)
    indoor_mask = binary_dilation(building_mask, iterations=2)

    def sample(grid, points):
        i = np.clip((points[:, 0] - n0).astype(int), 0, rows - 1)
        j = np.clip((points[:, 1] - e0).astype(int), 0, cols - 1)
        return grid[i, j]

    outdoor = ~sample(indoor_mask, path)
    d_building = sample(building_distance, path)
    d_tree = sample(tree_distance, path)
    covers = {s: cKDTree(p).query(path, k=1)[0] <= COVER_M for s, p in others.items()}

    arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    print(f"Route length {arc[-1]:.0f} m | buildings {len(buildings)} | tree features {len(tree_points) + len(tree_rings)}")
    print(f"Route samples inside a building footprint: {100 * (~outdoor).mean():.1f}%")

    windows = []
    for start in np.arange(0, arc[-1] - WINDOW_M, STEP_M):
        a, b = np.searchsorted(arc, [start, start + WINDOW_M])
        if b - a < 20 or (t[b - 1] - t[a]) > 900:
            continue
        cover = {s: float(c[a:b].mean()) for s, c in covers.items()}
        near_building = float((d_building[a:b] <= NEAR_BUILDING_M).mean())
        near_tree = float((d_tree[a:b] <= NEAR_TREE_M).mean())
        out = float(outdoor[a:b].mean())
        windows.append({
            "start_m": float(start), "a": int(a), "b": int(b),
            "t_start": float(t[a]), "t_end": float(t[b - 1]),
            "outdoor": out, "near_building": near_building, "near_tree": near_tree,
            "mean_building_distance_m": float(d_building[a:b].mean()),
            "cover": cover, "min_cover": min(cover.values()),
            "score": near_building - 0.5 * near_tree,
            "valid": out >= MIN_OUTDOOR and min(cover.values()) >= MIN_COVER,
        })

    valid = sorted((w for w in windows if w["valid"]), key=lambda w: -w["score"])
    print(f"Windows: {len(windows)} | meeting outdoor and coverage rules: {len(valid)}")

    chosen = []
    for window in valid:
        points = path[window["a"]:window["b"]]
        if all((cKDTree(path[c["a"]:c["b"]]).query(points)[0] <= 30).mean() < 0.3 for c in chosen):
            chosen.append(window)
        if len(chosen) == 3:
            break

    for rank, window in enumerate(chosen, 1):
        print(
            f"#{rank} start {window['start_m']:.0f} m | score {window['score']:.2f} | near buildings "
            f"{100 * window['near_building']:.0f}% | near mapped trees {100 * window['near_tree']:.0f}% | "
            f"mean building distance {window['mean_building_distance_m']:.1f} m | outdoor {100 * window['outdoor']:.0f}% | "
            f"coverage {[round(100 * v) for v in window['cover'].values()]}% | "
            f"{window['t_end'] - window['t_start']:.0f} s"
        )

    (MAP_DIR / "candidates.json").write_text(json.dumps({
        "chosen": chosen,
        "bounds": bounds,
        "route": path[::4].round(1).tolist(),
        "chosen_paths": [path[c["a"]:c["b"]].round(1).tolist() for c in chosen],
        "others": {s: p[::6].round(1).tolist() for s, p in others.items()},
        "buildings": [b.round(1).tolist() for b in buildings],
        "tree_points": np.array(tree_points).round(1).tolist() if tree_points else [],
        "tree_rings": [r.round(1).tolist() for r in tree_rings],
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
