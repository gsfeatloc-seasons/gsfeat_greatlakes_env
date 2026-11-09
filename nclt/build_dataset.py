"""Builds a COLMAP-format training dataset from one NCLT session on Stretch A.

  --stage preview   writes a lidar overlay and per-camera median images for checking
  --stage build     writes images/, sampling_masks/, sparse/0, train_list.txt, test_list.txt

All poses stay in NCLT's shared metric frame, so every session can be scored in it.
"""
import argparse
import json
import struct
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy.spatial.transform import Rotation, Slerp

sys.path.insert(0, str(Path(__file__).parent))
from undistort import load_map  # noqa: E402

ROOT = Path("data/nclt/stretch_A")
CALIB = Path("data/nclt/calib")
CAMERAS = [1, 2, 3, 4, 5]
FOCAL = 400.0
RAW_W, RAW_H = 1616, 1232
# NCLT paper, Table 4.
X_BODY_LB3 = [0.035, 0.002, -1.23, -179.93, -0.23, 0.50]
FRAME_SPACING_M = 0.8
TEST_EVERY = 8
VOXEL_M = 0.25
MAX_RANGE_M = 40.0
MIN_RANGE_M = 2.0


def ssc_to_homo(x, y, z, roll, pitch, heading):
    """Radians. Rotation order rotz(heading) * roty(pitch) * rotx(roll), as in the NCLT paper."""
    T = np.eye(4)
    T[:3, :3] = Rotation.from_euler("ZYX", [heading, pitch, roll]).as_matrix()
    T[:3, 3] = [x, y, z]
    return T


def ssc_degrees(values):
    return ssc_to_homo(*values[:3], *np.radians(values[3:]))


# Photos are stored sideways. This rotates camera axes so the image is upright.
T_CAM_UPRIGHT = np.eye(4)
T_CAM_UPRIGHT[:3, :3] = [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]


def t_body_cam(camera):
    x_lb3_c = np.loadtxt(CALIB / f"x_lb3_c{camera}.csv", delimiter=",")
    return ssc_degrees(X_BODY_LB3) @ ssc_degrees(list(x_lb3_c)) @ T_CAM_UPRIGHT


def raw_maps(camera, width, height):
    """Maps each pixel of the shared upright pinhole camera to a raw image pixel."""
    K = np.loadtxt(CALIB / f"K_cam{camera}.csv", delimiter=",")
    map_u, map_v = load_map(camera)
    us, vs = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))
    x_up = (us - width / 2) / FOCAL
    y_up = (vs - height / 2) / FOCAL
    x_cam, y_cam = y_up, -x_up
    u = (K[0, 0] * x_cam + K[0, 2]).astype(np.float32)
    v = (K[1, 1] * y_cam + K[1, 2]).astype(np.float32)
    raw_u = cv2.remap(map_u, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=-1)
    raw_v = cv2.remap(map_v, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=-1)
    valid = (raw_u > 3) & (raw_v > 3) & (raw_u < RAW_W - 3) & (raw_v < RAW_H - 3)
    return raw_u, raw_v, valid


def choose_size():
    """Largest centered rectangle that has valid pixels in every camera."""
    canvas_w, canvas_h = 1300, 1700
    all_valid = np.ones((canvas_h, canvas_w), bool)
    for camera in CAMERAS:
        all_valid &= raw_maps(camera, canvas_w, canvas_h)[2]
    integral = cv2.integral(all_valid.astype(np.uint8))
    best = (0, 0, 0)
    for width in range(1200, 400, -10):
        for height in range(1600, 400, -10):
            x0, y0 = (canvas_w - width) // 2, (canvas_h - height) // 2
            x1, y1 = x0 + width, y0 + height
            inside = integral[y1, x1] - integral[y0, x1] - integral[y1, x0] + integral[y0, x0]
            if inside == width * height and width * height > best[0] and height <= 1.5 * width:
                best = (width * height, width, height)
    return best[1], best[2]


def load_ground_truth(session, windows):
    a, b = windows[0][0] - 2_000_000, windows[-1][1] + 2_000_000
    rows = []
    with open(ROOT.parent / "ground_truth" / f"groundtruth_{session}.csv") as handle:
        for line in handle:
            parts = line.split(",")
            utime = int(parts[0])
            if a <= utime <= b:
                rows.append([utime, *map(float, parts[1:7])])
    rows = np.array(rows)
    return rows[np.isfinite(rows).all(axis=1)]


class Poses:
    def __init__(self, ground_truth):
        self.t = ground_truth[:, 0]
        self.xyz = ground_truth[:, 1:4]
        self.slerp = Slerp(self.t, Rotation.from_euler("ZYX", ground_truth[:, [6, 5, 4]]))

    def world_body(self, utime):
        T = np.eye(4)
        T[:3, :3] = self.slerp(utime).as_matrix()
        T[:3, 3] = [np.interp(utime, self.t, self.xyz[:, i]) for i in range(3)]
        return T


def load_scan(path):
    """Velodyne sync scans are in the body frame (NCLT paper, section 7.3)."""
    raw = np.fromfile(path, dtype=np.dtype([("x", "<u2"), ("y", "<u2"), ("z", "<u2"), ("i", "u1"), ("l", "u1")]))
    points = np.stack([raw["x"], raw["y"], raw["z"]], axis=1).astype(np.float64) * 0.005 - 100.0
    keep = np.linalg.norm(points, axis=1)
    return points[(keep > MIN_RANGE_M) & (keep < MAX_RANGE_M)]


def select_frames(session, poses, windows):
    images = ROOT / "images" / session
    times = sorted(
        set.intersection(*[{int(f.stem) for f in (images / f"Cam{c}").glob("*.tiff")} for c in CAMERAS])
    )
    times = [t for t in times if any(a <= t <= b for a, b in windows) and poses.t[0] <= t <= poses.t[-1]]
    kept, last = [], None
    for t in times:
        position = poses.world_body(t)[:3, 3]
        if last is None or np.linalg.norm(position - last) >= FRAME_SPACING_M:
            kept.append(t)
            last = position
    return kept


def project(points_world, world_cam, width, height):
    p = (np.linalg.inv(world_cam) @ np.c_[points_world, np.ones(len(points_world))].T).T[:, :3]
    front = p[:, 2] > 0.5
    u = FOCAL * p[:, 0] / np.where(front, p[:, 2], 1) + width / 2
    v = FOCAL * p[:, 1] / np.where(front, p[:, 2], 1) + height / 2
    inside = front & (u >= 0) & (v >= 0) & (u < width - 1) & (v < height - 1)
    return u, v, p[:, 2], inside


def preview(session, frames, poses, width, height, out):
    images = ROOT / "images" / session
    scans = ROOT / "velodyne" / session
    maps = {c: raw_maps(c, width, height) for c in CAMERAS}
    t = frames[len(frames) // 2]
    world_body = poses.world_body(t)
    scan = load_scan(scans / f"{t}.bin")
    points = (world_body @ np.c_[scan, np.ones(len(scan))].T).T[:, :3]
    tiles = []
    for camera in CAMERAS:
        raw = cv2.imread(str(images / f"Cam{camera}" / f"{t}.tiff"))
        image = cv2.remap(raw, maps[camera][0], maps[camera][1], cv2.INTER_LINEAR)
        u, v, depth, inside = project(points, world_body @ t_body_cam(camera), width, height)
        colors = cv2.applyColorMap(np.clip(depth[inside] * 6, 0, 255).astype(np.uint8)[:, None], cv2.COLORMAP_JET)[:, 0]
        for x, y, color in zip(u[inside].astype(int), v[inside].astype(int), colors):
            cv2.circle(image, (x, y), 2, tuple(int(c) for c in color), -1)
        tiles.append(cv2.resize(image, (320, int(320 * height / width))))
    medians = []
    picks = frames[:: max(1, len(frames) // 60)]
    for camera in CAMERAS:
        stack = [
            cv2.resize(cv2.remap(cv2.imread(str(images / f"Cam{camera}" / f"{p}.tiff")), maps[camera][0], maps[camera][1], cv2.INTER_LINEAR), (320, int(320 * height / width)))
            for p in picks
        ]
        medians.append(np.median(np.stack(stack), axis=0).astype(np.uint8))
    cv2.imwrite(str(out), np.vstack([np.hstack(tiles), np.hstack(medians)]), [cv2.IMWRITE_JPEG_QUALITY, 82])
    print(f"Preview uses frame {t}; wrote {out}")


def write_colmap(out, width, height, records, xyz, rgb, tracks):
    sparse = out / "sparse" / "0"
    sparse.mkdir(parents=True, exist_ok=True)
    with open(sparse / "cameras.bin", "wb") as f:
        f.write(struct.pack("<Q", 1))
        f.write(struct.pack("<iiQQ", 1, 1, width, height))
        f.write(struct.pack("<4d", FOCAL, FOCAL, width / 2, height / 2))

    per_image = {}
    for point_id, (image_id, x, y) in enumerate(tracks, 1):
        per_image.setdefault(image_id, []).append((x, y, point_id))

    point2d_index = {}
    with open(sparse / "images.bin", "wb") as f:
        f.write(struct.pack("<Q", len(records)))
        for image_id, name, world_cam in records:
            cam_world = np.linalg.inv(world_cam)
            qx, qy, qz, qw = Rotation.from_matrix(cam_world[:3, :3]).as_quat()
            f.write(struct.pack("<i4d3di", image_id, qw, qx, qy, qz, *cam_world[:3, 3], 1))
            f.write(name.encode() + b"\0")
            observed = per_image.get(image_id, [])
            f.write(struct.pack("<Q", len(observed)))
            for index, (x, y, point_id) in enumerate(observed):
                f.write(struct.pack("<ddq", x, y, point_id))
                point2d_index[point_id] = index

    with open(sparse / "points3D.bin", "wb") as f:
        f.write(struct.pack("<Q", len(xyz)))
        for point_id, (p, c, track) in enumerate(zip(xyz, rgb, tracks), 1):
            f.write(struct.pack("<Q3d3Bd", point_id, *p, *c, 1.0))
            f.write(struct.pack("<Qii", 1, track[0], point2d_index[point_id]))


def build(session, frames, poses, width, height, polygons, out):
    images = ROOT / "images" / session
    scans = ROOT / "velodyne" / session
    (out / "images").mkdir(parents=True, exist_ok=True)
    (out / "sampling_masks").mkdir(parents=True, exist_ok=True)
    maps = {c: raw_maps(c, width, height) for c in CAMERAS}

    masks = {}
    for camera in CAMERAS:
        mask = np.full((height, width), 255, np.uint8)
        for polygon in polygons.get(str(camera), []):
            cv2.fillPoly(mask, [np.round(np.array(polygon) * [width, height]).astype(np.int32)], 0)
        masks[camera] = mask

    records, train, test = [], [], []
    frame_images = {}
    image_id = 0
    for index, t in enumerate(frames):
        world_body = poses.world_body(t)
        for camera in CAMERAS:
            image_id += 1
            name = f"{t}_cam{camera}.png"
            if not (out / "images" / name).exists():
                raw = cv2.imread(str(images / f"Cam{camera}" / f"{t}.tiff"))
                image = cv2.remap(raw, maps[camera][0], maps[camera][1], cv2.INTER_LINEAR)
                cv2.imwrite(str(out / "images" / name), image)
            cv2.imwrite(str(out / "sampling_masks" / name), masks[camera])
            world_cam = world_body @ t_body_cam(camera)
            records.append((image_id, name, world_cam))
            frame_images.setdefault(t, []).append((image_id, camera, world_cam, name))
            (test if index % TEST_EVERY == 0 else train).append(name)

    cloud = []
    for t in frames:
        path = scans / f"{t}.bin"
        if path.exists():
            scan = load_scan(path)
            cloud.append((poses.world_body(t) @ np.c_[scan, np.ones(len(scan))].T).T[:, :3])
    cloud = np.vstack(cloud)
    _, unique = np.unique(np.floor(cloud / VOXEL_M).astype(np.int64), axis=0, return_index=True)
    cloud = cloud[unique]

    rgb = np.zeros((len(cloud), 3), np.uint8)
    tracks = [None] * len(cloud)
    best = np.full(len(cloud), np.inf)
    for t in frames:
        for image_id, camera, world_cam, name in frame_images[t]:
            u, v, depth, inside = project(cloud, world_cam, width, height)
            better = np.flatnonzero(inside & (depth < best) & (depth < 25))
            if len(better) == 0:
                continue
            image = cv2.imread(str(out / "images" / name))
            ui, vi = u[better].astype(int), v[better].astype(int)
            allowed = masks[camera][vi, ui] > 0
            better, ui, vi = better[allowed], ui[allowed], vi[allowed]
            rgb[better] = image[vi, ui][:, ::-1]
            best[better] = depth[better]
            for point, x, y in zip(better, ui, vi):
                tracks[point] = (image_id, float(x), float(y))
    colored = np.array([track is not None for track in tracks])
    cloud, rgb = cloud[colored], rgb[colored]
    tracks = [track for track in tracks if track is not None]

    write_colmap(out, width, height, records, cloud, rgb, tracks)
    (out / "train_list.txt").write_text("\n".join(train) + "\n")
    (out / "test_list.txt").write_text("\n".join(test) + "\n")
    print(f"Frames {len(frames)} | train images {len(train)} | test images {len(test)} | 3D points {len(cloud)}")


def queries(session, frames, poses, width, height):
    """Writes test photos and their true camera poses. Uses every TEST_EVERY-th frame."""
    images = ROOT / "images" / session
    out = ROOT / "queries" / session
    (out / "images").mkdir(parents=True, exist_ok=True)
    maps = {c: raw_maps(c, width, height) for c in CAMERAS}
    manifest = {}
    for t in frames[::TEST_EVERY]:
        world_body = poses.world_body(t)
        for camera in CAMERAS:
            name = f"{t}_cam{camera}.png"
            raw = cv2.imread(str(images / f"Cam{camera}" / f"{t}.tiff"))
            cv2.imwrite(str(out / "images" / name), cv2.remap(raw, maps[camera][0], maps[camera][1], cv2.INTER_LINEAR))
            manifest[name] = (world_body @ t_body_cam(camera)).tolist()
    (out / "poses.json").write_text(json.dumps({"width": width, "height": height, "focal": FOCAL, "poses": manifest}))
    print(f"{session}: {len(manifest)} query photos")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", default="2012-08-04")
    parser.add_argument("--stage", choices=["preview", "build", "queries"], required=True)
    parser.add_argument("--preview_out", default="data/nclt/stretch_A/preview.jpg")
    args = parser.parse_args()

    windows = json.loads((ROOT / f"windows_{args.session}.json").read_text())
    poses = Poses(load_ground_truth(args.session, windows))
    frames = select_frames(args.session, poses, windows)
    width, height = choose_size()
    print(f"Image size {width} x {height}, focal {FOCAL} | frames kept {len(frames)} x {len(CAMERAS)} cameras")

    if args.stage == "preview":
        preview(args.session, frames, poses, width, height, Path(args.preview_out))
    elif args.stage == "queries":
        queries(args.session, frames, poses, width, height)
    else:
        polygons = json.loads(Path("nclt/robot_masks.json").read_text())
        build(args.session, frames, poses, width, height, polygons, ROOT / "dataset" / args.session)


if __name__ == "__main__":
    main()
