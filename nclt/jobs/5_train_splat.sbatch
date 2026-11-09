#!/bin/bash
# Trains the 3DGS splat. Skips training if this splat already exists.
# To retrain, delete the folder named by SPLAT_DIR in nclt/config.sh.
#SBATCH --job-name=nclt-5-train
#SBATCH --account=rob498_rob598s002f26_class
#SBATCH --partition=gpu
#SBATCH --gpus=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=04:00:00
#SBATCH --output=logs/%x-%j.log

set -eo pipefail
cd "$SLURM_SUBMIT_DIR"
source ./activate.sh
source nclt/config.sh
unset DISPLAY WAYLAND_DISPLAY
export MPLBACKEND=Agg
export NERFBASELINES_BACKEND=python

if [ -d "$SPLAT_DIR/checkpoint-30000" ]; then
    echo "Splat already exists in $SPLAT_DIR. Skipping training."
    exit 0
fi

nerfbaselines train --method gsplat --data "$STRETCH_DIR/dataset/$MAP_SESSION" --output "$SPLAT_DIR" \
    --backend python --logger none --disable-output-artifact \
    --set app_opt=True --set pose_opt=True
