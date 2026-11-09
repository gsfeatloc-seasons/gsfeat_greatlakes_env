#!/bin/bash
# Corrects and masks the photos, adds laser points, and checks that the dataset loads.
#SBATCH --job-name=nclt-4-dataset
#SBATCH --account=rob498_rob598s002f26_class
#SBATCH --partition=standard
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=01:30:00
#SBATCH --output=logs/%x-%j.log

set -eo pipefail
cd "$SLURM_SUBMIT_DIR"
source ./activate.sh
source nclt/config.sh
export MPLBACKEND=Agg

python -u nclt/build_dataset.py --stage build --session "$MAP_SESSION"
python nclt/check_dataset.py "$STRETCH_DIR/dataset/$MAP_SESSION"
