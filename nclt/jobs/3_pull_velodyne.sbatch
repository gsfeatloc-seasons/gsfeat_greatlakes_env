#!/bin/bash
# Keeps only the laser scans from the stretch, for the session used to train the splat.
#SBATCH --job-name=nclt-3-velodyne
#SBATCH --account=rob498_rob598s002f26_class
#SBATCH --partition=standard
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=03:00:00
#SBATCH --output=logs/%x-%j.log

set -eo pipefail
cd "$SLURM_SUBMIT_DIR"
source ./activate.sh
source nclt/config.sh

# PULL_STRETCHES (default: STRETCH) lists stretches to fill from one pass over the archive, e.g. "B C".
PAIRS=()
for stretch in ${PULL_STRETCHES:-$STRETCH}; do
    out="data/nclt/stretch_$stretch/velodyne/$MAP_SESSION"
    if [ -f "$out/.done" ]; then
        echo "Stretch $stretch, $MAP_SESSION already done: $(cat "$out/.done")"
    else
        PAIRS+=("data/nclt/stretch_$stretch/windows_$MAP_SESSION.json" "$out")
    fi
done
if [ ${#PAIRS[@]} -eq 0 ]; then
    exit 0
fi

curl -sS --fail "$NCLT_URL/velodyne_data/${MAP_SESSION}_vel.tar.gz" | gzip -dc | \
    python -u nclt/extract_velodyne.py "${PAIRS[@]}"
