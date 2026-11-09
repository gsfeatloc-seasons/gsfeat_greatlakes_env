#!/bin/bash
# Submits the whole NCLT pipeline as a chain of Slurm jobs. Each job starts when the one before it succeeds.
# Run from anywhere:  bash nclt/run_all.sh
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p logs
source nclt/config.sh

count=$(wc -w <<< "$SESSIONS")
prepare=$(sbatch --parsable nclt/jobs/1_prepare.sbatch)
images=$(sbatch --parsable --kill-on-invalid-dep=yes --dependency="afterok:$prepare" --array="0-$((count - 1))" nclt/jobs/2_pull_images.sbatch)
velodyne=$(sbatch --parsable --kill-on-invalid-dep=yes --dependency="afterok:$prepare" nclt/jobs/3_pull_velodyne.sbatch)
dataset=$(sbatch --parsable --kill-on-invalid-dep=yes --dependency="afterok:$images:$velodyne" nclt/jobs/4_build_dataset.sbatch)
train=$(sbatch --parsable --kill-on-invalid-dep=yes --dependency="afterok:$dataset" nclt/jobs/5_train_splat.sbatch)
localize=$(sbatch --parsable --kill-on-invalid-dep=yes --dependency="afterok:$train" nclt/jobs/6_localize.sbatch)

echo "Submitted 6 steps. The last job is $localize."
echo "Check progress:  squeue -u \$USER"
echo "Logs are in:     logs/"
echo "See results:     python nclt/show_results.py"
