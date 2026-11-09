#!/bin/bash
# End-to-end test with no display: downloads the small Blender "lego" scene, trains a
# 3DGS splat with gsplat, runs GSFeatLoc on it, and prints accuracy.
# Submit from the repo folder:  sbatch scripts/smoke_test.sbatch
#SBATCH --job-name=gsfeatloc-smoke
#SBATCH --account=rob498_rob598s002f26_class
#SBATCH --partition=gpu
#SBATCH --gpus=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:30:00
#SBATCH --output=smoke-%j.log

set -eo pipefail
cd "$SLURM_SUBMIT_DIR"
source ./activate.sh

# Force a true headless run, even if the job inherited a display.
unset DISPLAY WAYLAND_DISPLAY
export MPLBACKEND=Agg
export NERFBASELINES_BACKEND=python
echo "DISPLAY='${DISPLAY:-}' host=$(hostname)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

DATA=data/blender/lego
OUT=results/smoke/blender/lego

if [ ! -f "$DATA/transforms_test.json" ]; then
    echo "==> Downloading the lego scene"
    nerfbaselines download-dataset external://blender/lego -o "$DATA"
fi

if [ ! -d "$OUT/checkpoint-30000" ]; then
    echo "==> Training the splat"
    nerfbaselines train --method gsplat --data "$DATA" --output "$OUT" \
        --backend python --logger none --disable-output-artifact
fi

echo "==> Running GSFeatLoc"
python third_party/gsfeatloc/gsfeatloc_cli.py \
    --scene_path "$DATA" \
    --model_path "$OUT/checkpoint-30000" \
    --output_path "$OUT/gsfeatloc" \
    --delta_rot 12.10 --delta_trs 0.87 \
    --axis_mode random --magnitude_mode gaussian

echo "==> Results"
python scripts/summarize_results.py "$OUT/gsfeatloc/results.json"
echo "SMOKE TEST COMPLETE"
