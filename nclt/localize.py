"""Runs GSFeatLoc on NCLT query photos against one splat, at several starting-pose errors.

Differences from upstream gsfeatloc_cli.py, needed for outdoor, metric scenes:
- depth scale comes from the checkpoint's world normalization
- matches on sky, the robot, or invalid depth are removed before PnP
- RANSAC runs 1000 iterations
- a failed frame is recorded as failed, and still scored at its starting pose
"""
import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from nerfbaselines import camera_model_to_int, load_checkpoint, new_cameras
from scipy.spatial.transform import Rotation

from gsfeatloc.feature_matcher import do_feature_matching_SPSG
from gsfeatloc.pose_estimator import compute_3d_points, estimate_camera_pose, get_2d_feature_points
from gsfeatloc.utils import get_world_frame_difference

ROOT = Path("data/nclt/stretch_A/queries")
# Starting-pose error: 95% of samples fall within (metres, degrees).
LEVELS = [(1.0, 5.0), (3.0, 15.0), (10.0, 30.0)]
THRESHOLDS = [(0.25, 2), (0.5, 5), (1.0, 10)]
MIN_DEPTH_M, MAX_DEPTH_M = 2.0, 80.0
MIN_ACCUMULATION = 0.5
MIN_INLIERS = 12
VIS_LEVEL = 1
VIS_COUNT = 3


def checkpoint_depth_scale(checkpoint):
    transform = json.loads((Path(checkpoint) / "parser.json").read_text())["transform"]
    return 1.0 / float(np.linalg.norm(np.array(transform)[0, :3]))


def robot_masks(width, height):
    polygons = json.loads(Path("nclt/robot_masks.json").read_text())
    masks = {}
    for camera, shapes in polygons.items():
        mask = np.ones((height, width), np.uint8)
        for shape in shapes:
            cv2.fillPoly(mask, [np.round(np.array(shape) * [width, height]).astype(np.int32)], 0)
        masks[int(camera)] = mask.astype(bool)
    return masks


def perturb(world_cam, trans_95, rot_95, rng):
    axis = rng.normal(size=3)
    axis /= np.linalg.norm(axis)
    direction = rng.normal(size=3)
    direction /= np.linalg.norm(direction)
    delta = np.eye(4)
    delta[:3, :3] = Rotation.from_rotvec(axis * np.radians(abs(rng.normal(0, rot_95 / 1.96)))).as_matrix()
    delta[:3, 3] = direction * abs(rng.normal(0, trans_95 / 1.96))
    return world_cam @ delta


def localize(model, query, world_init, K, width, height, depth_scale, mask):
    camera = new_cameras(
        poses=world_init,
        intrinsics=np.array([K[0, 0], K[1, 1], K[0, 2], K[1, 2]], dtype=np.float32),
        image_sizes=np.array([width, height], dtype=np.int32),
        camera_models=np.array(camera_model_to_int("pinhole"), dtype=np.int32),
    )
    outputs = model.render(camera=camera, options={
        "outputs": "depth,accumulation",
        "output_type_dtypes": {"color": "uint8", "depth": "float32"},
    })
    render, depth, accumulation = outputs["color"], outputs["depth"], outputs.get("accumulation")
    kp_query, kp_render, matches = do_feature_matching_SPSG(query, render, do_visualize=False)
    result = {"matches": len(matches), "valid": 0, "inliers": 0, "failed": True}
    empty = np.zeros((0, 2), np.float32)
    vis = (render, empty, empty)
    if len(matches) < 4:
        return world_init, result, vis

    pts_query, pts_render, _, _ = get_2d_feature_points(matches, kp_query, kp_render)
    row, col = pts_render[:, 1].astype(int), pts_render[:, 0].astype(int)
    real_depth = depth[row, col] * depth_scale
    keep = np.isfinite(real_depth) & (real_depth > MIN_DEPTH_M) & (real_depth < MAX_DEPTH_M)
    if accumulation is not None:
        keep &= np.squeeze(accumulation)[row, col] > MIN_ACCUMULATION
    if mask is not None:
        keep &= mask[pts_query[:, 1].astype(int), pts_query[:, 0].astype(int)]
    pts_query, pts_render = pts_query[keep], pts_render[keep]
    result["valid"] = int(keep.sum())
    if len(pts_query) < 6:
        return world_init, result, vis

    world_points, _ = compute_3d_points(pts_render.copy(), depth, K, world_init, depth_scale=depth_scale)
    rvec, tvec, inliers = estimate_camera_pose(world_points, pts_query, K, reprojection_error=5.0, iterations=1000)
    if inliers is None or len(inliers) < MIN_INLIERS:
        result["inliers"] = 0 if inliers is None else int(len(inliers))
        return world_init, result, vis

    cam_world = np.eye(4)
    cam_world[:3, :3] = Rotation.from_rotvec(rvec.flatten()).as_matrix()
    cam_world[:3, 3] = tvec.flatten()
    result.update(inliers=int(len(inliers)), failed=False)
    idx = inliers.flatten()
    return np.linalg.inv(cam_world), result, (render, pts_query[idx], pts_render[idx])


def save_vis(path, query, render, pts_query, pts_render):
    canvas = np.hstack([query, render])[..., ::-1].copy()
    width = query.shape[1]
    for (x0, y0), (x1, y1) in zip(pts_query[::3].astype(int), pts_render[::3].astype(int)):
        cv2.line(canvas, (int(x0), int(y0)), (int(x1) + width, int(y1)), (60, 230, 90), 1, cv2.LINE_AA)
    cv2.imwrite(str(path), cv2.resize(canvas, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 80])


def summarize(records):
    rot = np.array([r["rotation_error"] for r in records])
    trs = np.array([r["translation_error"] for r in records])
    init_rot = np.array([r["init_rotation_error"] for r in records])
    init_trs = np.array([r["init_translation_error"] for r in records])
    failed = np.array([r["failed"] for r in records])
    summary = {
        "frames": len(records),
        "failed_pct": float(100 * failed.mean()),
        "median_start_m": float(np.median(init_trs)),
        "median_start_deg": float(np.median(init_rot)),
        "median_m": float(np.median(trs)),
        "median_deg": float(np.median(rot)),
        "median_matches": float(np.median([r["matches"] for r in records])),
        "median_inliers": float(np.median([r["inliers"] for r in records])),
        "seconds_per_frame": float(np.mean([r["seconds"] for r in records])),
    }
    for metres, degrees in THRESHOLDS:
        summary[f"within_{metres}m_{degrees}deg_pct"] = float(100 * np.mean((trs < metres) & (rot < degrees)))
        summary[f"start_within_{metres}m_{degrees}deg_pct"] = float(100 * np.mean((init_trs < metres) & (init_rot < degrees)))
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--sessions", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    out = Path(args.output)
    (out / "vis").mkdir(parents=True, exist_ok=True)
    depth_scale = checkpoint_depth_scale(args.checkpoint)
    print(f"Depth scale from checkpoint: {depth_scale:.3f}")

    all_summaries = {}
    with load_checkpoint(args.checkpoint, backend="python") as (model, _):
        for session in args.sessions:
            meta = json.loads((ROOT / session / "poses.json").read_text())
            width, height, focal = meta["width"], meta["height"], meta["focal"]
            K = np.array([[focal, 0, width / 2], [0, focal, height / 2], [0, 0, 1]], dtype=np.float32)
            masks = robot_masks(width, height)
            names = sorted(meta["poses"])
            vis_at = {names[int(len(names) * (i + 0.5) / VIS_COUNT)] for i in range(VIS_COUNT)}

            for level, (trans_95, rot_95) in enumerate(LEVELS):
                rng = np.random.default_rng(level)
                records = []
                for name in names:
                    world_gt = np.array(meta["poses"][name], dtype=np.float64)
                    camera = int(name.rsplit("cam", 1)[1].split(".")[0])
                    query = cv2.cvtColor(cv2.imread(str(ROOT / session / "images" / name)), cv2.COLOR_BGR2RGB)
                    world_init = perturb(world_gt, trans_95, rot_95, rng)
                    start = time.time()
                    world_pred, result, vis = localize(model, query, world_init, K, width, height, depth_scale, masks.get(camera))
                    rot_init, trs_init = get_world_frame_difference(world_gt, world_init)
                    rot_pred, trs_pred = get_world_frame_difference(world_gt, world_pred)
                    result.update(
                        name=name, rotation_error=float(rot_pred), translation_error=float(trs_pred),
                        init_rotation_error=float(rot_init), init_translation_error=float(trs_init),
                        seconds=time.time() - start,
                    )
                    records.append(result)
                    if level == VIS_LEVEL and name in vis_at:
                        save_vis(out / "vis" / f"{session}_{name[:-4]}.jpg", query, *vis)
                key = f"{session} start {trans_95:g}m {rot_95:g}deg"
                (out / f"{session}_level{level}.json").write_text(json.dumps(records))
                all_summaries[key] = summarize(records)
                print("RESULT", key, json.dumps(all_summaries[key]), flush=True)

    (out / "summary.json").write_text(json.dumps(all_summaries, indent=2))
    print("LOCALIZATION COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
