#!/bin/bash
# Downloads robot positions and camera calibration, then finds when each session passed through the stretch.
#SBATCH --job-name=nclt-1-prepare
#SBATCH --account=rob498_rob598s002f26_class
#SBATCH --partition=standard
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:45:00
#SBATCH --output=logs/%x-%j.log

set -eo pipefail
cd "$SLURM_SUBMIT_DIR"
source ./activate.sh
source nclt/config.sh

GT=data/nclt/ground_truth
CALIB=data/nclt/calib
mkdir -p "$GT" "$CALIB" "$STRETCH_DIR"

for session in $SESSIONS; do
    file="$GT/groundtruth_$session.csv"
    if [ ! -f "$file" ]; then
        curl -sS --fail -o "$file.tmp" "$NCLT_URL/ground_truth/groundtruth_$session.csv"
        mv "$file.tmp" "$file"
    fi
    # About 2 Hz is enough for finding where the robot was.
    awk -F, 'NR%50==1 && $2!="" && tolower($2)!="nan"' "$file" > "$GT/groundtruth_$session.2hz.txt"
done

if [ ! -f "$CALIB/K_cam1.csv" ]; then
    curl -sS --fail -o "$CALIB/cam_params.zip" "$NCLT_URL/ladybug3_calib/cam_params.zip"
    unzip -q -o "$CALIB/cam_params.zip" -d "$CALIB"
    rm "$CALIB/cam_params.zip"
fi
if [ ! -f "$CALIB/U2D_Cam1_1616X1232.txt" ]; then
    curl -sS --fail -o "$CALIB/U2D_ALL.tar.gz" "$NCLT_URL/ladybug3_calib/U2D_ALL_1616X1232.tar.gz"
    tar xzf "$CALIB/U2D_ALL.tar.gz" -C "$CALIB" --no-same-owner
    rm "$CALIB/U2D_ALL.tar.gz"
fi

python -u nclt/time_windows.py "nclt/stretch_$STRETCH.json" "$STRETCH_DIR" $SESSIONS
