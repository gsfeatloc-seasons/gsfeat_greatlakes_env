#!/bin/bash
#SBATCH --job-name=gsfeatloc-setup
#SBATCH --account=rob498_rob598s002f26_class
#SBATCH --partition=gpu
#SBATCH --gpus=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=setup-%j.log

cd "$SLURM_SUBMIT_DIR"
bash setup.sh
