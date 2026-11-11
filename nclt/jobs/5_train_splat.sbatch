#!/bin/bash
# Trains the splat with METHOD (default gsplat). Skips training if this splat already exists.
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

if [ -n "$(latest_checkpoint)" ]; then
    echo "Splat already exists in $SPLAT_DIR. Skipping training."
    exit 0
fi

case "$METHOD" in
    gsplat) METHOD_ARGS=(--set app_opt=True --set pose_opt=True) ;;
    *) METHOD_ARGS=() ;;
esac

nerfbaselines train --method "$METHOD" --data "$STRETCH_DIR/dataset/$MAP_SESSION" --output "$SPLAT_DIR" \
    --backend "$NB_BACKEND" --logger none --disable-output-artifact "${METHOD_ARGS[@]}"
