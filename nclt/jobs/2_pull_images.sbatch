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
OUT="$STRETCH_DIR/images/$SESSION"

if [ -f "$OUT/.done" ]; then
    echo "$SESSION already done: $(cat "$OUT/.done")"
    exit 0
fi

curl -sS --fail "$NCLT_URL/images/${SESSION}_lb3.tar.gz" | gzip -dc | \
    python -u nclt/extract_images.py "$STRETCH_DIR/windows_$SESSION.json" "$OUT"
