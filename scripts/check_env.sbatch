#!/bin/bash
# Re-runs the environment check without reinstalling. Submit from the repo folder:
#   sbatch scripts/check_env.sbatch
#SBATCH --job-name=gsfeatloc-check
#SBATCH --account=rob498_rob598s002f26_class
#SBATCH --partition=gpu
#SBATCH --gpus=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:20:00
#SBATCH --output=check-%j.log

cd "$SLURM_SUBMIT_DIR"
source ./activate.sh
python scripts/check_env.py
