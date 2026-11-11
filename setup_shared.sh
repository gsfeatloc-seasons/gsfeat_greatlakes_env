#!/bin/bash
# Connects this clone to the team's shared environment, corrected photos and trained splat.
# Nothing is downloaded or installed, and the shared files are read-only.
set -euo pipefail

SHARED=/scratch/rob498_rob598s002f26_class_root/rob498_rob598s002f26_class/nandann/gsfeat_greatlakes_env

cd "$(dirname "${BASH_SOURCE[0]}")"

if [ ! -x "$SHARED/.mamba/gsfeatloc/bin/python" ]; then
    echo "Can't read the shared folder: $SHARED" >&2
    echo "Ask the person who owns it to check that it still exists and that you are in the class group." >&2
    exit 1
fi

ln -sfn "$SHARED/.mamba" .mamba
ln -sfn "$SHARED/third_party" third_party
ln -sfn "$SHARED/data" data
mkdir -p logs results/splat
# Every trained splat in the shared folder (Stretch A, B, C, and other methods). Run this again to pick up new ones.
for splat in "$SHARED"/results/splat/*/; do
    target="results/splat/$(basename "$splat")"
    # Never touch a splat you trained yourself with the same name.
    if [ -e "$target" ] && [ ! -L "$target" ]; then continue; fi
    ln -sfn "${splat%/}" "$target"
done
# The owner's GSFeatLoc results, read-only. Your own runs still go in results/gsfeatloc/.
ln -sfn "$SHARED/results/gsfeatloc" shared_results

echo "Linked splats: $(ls results/splat | tr '\n' ' ')"
echo "Shared results: shared_results/"
echo "Done. Next:"
echo "  source activate.sh"
echo "  bash nclt/run_localize.sh"
