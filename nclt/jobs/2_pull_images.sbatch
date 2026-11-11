#!/bin/bash
# Streams one session's image archive and keeps only the photos from the stretch.
# run_all.sh submits this as an array, with one task per session.
#SBATCH --job-name=nclt-2-images
#SBATCH --account=rob498_rob598s002f26_class
#SBATCH --partition=standard
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=08:00:00
#SBATCH --output=logs/%x-%A_%a.log

set -eo pipefail
cd "$SLURM_SUBMIT_DIR"
source ./activate.sh
source nclt/config.sh

read -r -a ALL_SESSIONS <<< "$SESSIONS"
SESSION="${ALL_SESSIONS[$SLURM_ARRAY_TASK_ID]}"
# PULL_STRETCHES (default: STRETCH) lists stretches to fill from one pass over the archive, e.g. "B C".
PAIRS=()
for stretch in ${PULL_STRETCHES:-$STRETCH}; do
    out="data/nclt/stretch_$stretch/images/$SESSION"
    if [ -f "$out/.done" ]; then
        echo "Stretch $stretch, $SESSION already done: $(cat "$out/.done")"
    else
        PAIRS+=("data/nclt/stretch_$stretch/windows_$SESSION.json" "$out")
    fi
done
if [ ${#PAIRS[@]} -eq 0 ]; then
    exit 0
fi

curl -sS --fail "$NCLT_URL/images/${SESSION}_lb3.tar.gz" | gzip -dc | \
    python -u nclt/extract_images.py "${PAIRS[@]}"
