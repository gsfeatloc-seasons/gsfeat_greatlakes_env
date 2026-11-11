#!/bin/bash
# Runs GSFeatLoc using data that is already prepared. Trains the splat first only if it doesn't exist yet.
# Run from anywhere:  bash nclt/run_localize.sh
# Another splat method:  METHOD=wild-gaussians bash nclt/run_localize.sh
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p logs
source nclt/config.sh

echo "Method: $METHOD   Splat: $SPLAT_DIR"
if [ -n "$(latest_checkpoint)" ]; then
    localize=$(sbatch --parsable nclt/jobs/6_localize.sbatch)
else
    train=$(sbatch --parsable nclt/jobs/5_train_splat.sbatch)
    localize=$(sbatch --parsable --kill-on-invalid-dep=yes --dependency="afterok:$train" nclt/jobs/6_localize.sbatch)
fi

echo "Submitted. The last job is $localize."
echo "Check progress:  squeue -u \$USER"
echo "Logs are in:     logs/"
echo "See results:     python nclt/show_results.py"
