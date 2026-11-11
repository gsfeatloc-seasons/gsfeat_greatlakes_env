#!/bin/bash
# Runs the whole pipeline for extra route stretches, downloading each NCLT archive only once for all of them.
# Run from anywhere:  bash nclt/run_stretches.sh B C
# Each stretch needs nclt/stretch_<letter>.json. METHOD works here too (default gsplat).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p logs
source nclt/config.sh

STRETCHES=("$@")
if [ ${#STRETCHES[@]} -eq 0 ]; then
    echo "Usage: bash nclt/run_stretches.sh B C" >&2
    exit 1
fi
for stretch in "${STRETCHES[@]}"; do
    [ -f "nclt/stretch_$stretch.json" ] || { echo "Missing nclt/stretch_$stretch.json" >&2; exit 1; }
done
export PULL_STRETCHES="${STRETCHES[*]}"
dep() { echo "--kill-on-invalid-dep=yes --dependency=afterok:$1"; }

# Finding each stretch's time windows. One after another, because they share the ground truth files.
prepare=""
for stretch in "${STRETCHES[@]}"; do
    prepare=$(STRETCH=$stretch sbatch --parsable ${prepare:+$(dep "$prepare")} nclt/jobs/1_prepare.sbatch)
done

# One pass over each archive fills every stretch.
count=$(wc -w <<< "$SESSIONS")
images=$(sbatch --parsable $(dep "$prepare") --array="0-$((count - 1))" nclt/jobs/2_pull_images.sbatch)
velodyne=$(sbatch --parsable $(dep "$prepare") nclt/jobs/3_pull_velodyne.sbatch)

for stretch in "${STRETCHES[@]}"; do
    dataset=$(STRETCH=$stretch sbatch --parsable $(dep "$images:$velodyne") nclt/jobs/4_build_dataset.sbatch)
    train=$(STRETCH=$stretch sbatch --parsable $(dep "$dataset") nclt/jobs/5_train_splat.sbatch)
    localize=$(STRETCH=$stretch sbatch --parsable $(dep "$train") nclt/jobs/6_localize.sbatch)
    echo "Stretch $stretch: build $dataset, train $train, localize $localize"
done

echo "Downloads: images $images, laser $velodyne"
echo "Check progress:  squeue -u \$USER"
echo "See results:     python nclt/show_results.py results/gsfeatloc/stretch_<letter>_$MAP_SESSION"
