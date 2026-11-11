#!/bin/bash
# Prepares test photos for each session, runs GSFeatLoc on the splat, and prints the results.
#SBATCH --job-name=nclt-6-localize
#SBATCH --account=rob498_rob598s002f26_class
#SBATCH --partition=gpu
#SBATCH --gpus=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=logs/%x-%j.log

set -eo pipefail
cd "$SLURM_SUBMIT_DIR"
source ./activate.sh
source nclt/config.sh
unset DISPLAY WAYLAND_DISPLAY
export MPLBACKEND=Agg

for session in $SESSIONS; do
    if [ ! -f "$STRETCH_DIR/queries/$session/poses.json" ]; then
        python -u nclt/build_dataset.py --stage queries --session "$session"
    fi
done

python -u nclt/localize.py --checkpoint "$(latest_checkpoint)" --backend "$NB_BACKEND" --sessions $SESSIONS --output "$RESULTS_DIR"
python nclt/show_results.py "$RESULTS_DIR"
echo "PIPELINE COMPLETE"
