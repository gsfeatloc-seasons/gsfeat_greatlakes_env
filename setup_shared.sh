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
ln -sfn "$SHARED/results/splat/stretch_A_2012-08-04" results/splat/stretch_A_2012-08-04

echo "Done. Next:"
echo "  source activate.sh"
echo "  bash nclt/run_localize.sh"
