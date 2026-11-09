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

OUT="$STRETCH_DIR/velodyne/$MAP_SESSION"
if [ -f "$OUT/.done" ]; then
    echo "$MAP_SESSION already done: $(cat "$OUT/.done")"
    exit 0
fi

curl -sS --fail "$NCLT_URL/velodyne_data/${MAP_SESSION}_vel.tar.gz" | gzip -dc | \
    python -u nclt/extract_velodyne.py "$STRETCH_DIR/windows_$MAP_SESSION.json" "$OUT"
