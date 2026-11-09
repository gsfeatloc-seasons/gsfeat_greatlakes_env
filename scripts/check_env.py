"""Confirms that the environment can do each thing GSFeatLoc needs."""
import cv2
import numpy as np
import torch

print("torch", torch.__version__, "| CUDA available:", torch.cuda.is_available())
assert torch.cuda.is_available(), "No GPU found. Run this on a GPU node."
print("GPU:", torch.cuda.get_device_name(0))
print("OpenCV", cv2.__version__, "| NumPy", np.__version__)

from gsplat import csrc  # noqa: E402,F401
from gsplat.rendering import rasterization  # noqa: E402
import nerfbaselines  # noqa: E402
from nerfbaselines import load_checkpoint  # noqa: E402,F401
import simple_trainer  # noqa: E402,F401  (gsplat's trainer, used by NerfBaselines)

print("NerfBaselines", nerfbaselines.__version__)

# Importing this loads SuperPoint, SuperGlue and LoFTR and downloads any missing weights.
from gsfeatloc import feature_matcher  # noqa: E402,F401

device = "cuda"
n = 100
colors, _, _ = rasterization(
    means=torch.randn(n, 3, device=device),
    quats=torch.nn.functional.normalize(torch.randn(n, 4, device=device), dim=-1),
    scales=torch.full((n, 3), 0.05, device=device),
    opacities=torch.ones(n, device=device),
    colors=torch.rand(n, 3, device=device),
    viewmats=torch.tensor(
        [[[1.0, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 5], [0, 0, 0, 1]]], device=device
    ),
    Ks=torch.tensor([[[100.0, 0, 50], [0, 100.0, 50], [0, 0, 1]]], device=device),
    width=100,
    height=100,
    render_mode="RGB+ED",
)
assert colors.shape == (1, 100, 100, 4), colors.shape
print("Test render with depth: OK")
print("ALL CHECKS PASSED")
