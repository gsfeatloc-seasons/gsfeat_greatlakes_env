"""Confirms NerfBaselines can load a built dataset, and prints its geometry."""
import sys

from nerfbaselines.datasets import load_dataset

FEATURES = frozenset(("points3D_xyz", "points3D_rgb", "color", "images_points3D_indices"))

path = sys.argv[1]
for split in ("train", "test"):
    dataset = load_dataset(path, split=split, features=FEATURES, load_features=False)
    print(
        split,
        "| images", len(dataset["image_paths"]),
        "| points", len(dataset["points3D_xyz"]),
        "| masks", dataset.get("sampling_mask_paths") is not None,
        "| size", dataset["cameras"].image_sizes[0],
        "| intrinsics", dataset["cameras"].intrinsics[0],
    )
points = dataset["points3D_xyz"]
positions = dataset["cameras"].poses[:, :3, 3]
print("Point extent (m):", points.min(0).round(1), points.max(0).round(1))
print("Camera extent (m):", positions.min(0).round(1), positions.max(0).round(1))
print("DATASET LOADS OK")
