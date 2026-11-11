# Settings shared by every NCLT step. The first session is used to train the splat.
SESSIONS="2012-08-04 2012-11-04 2012-02-12"
MAP_SESSION="${SESSIONS%% *}"
NCLT_URL="https://s3.us-east-2.amazonaws.com/nclt.perl.engin.umich.edu"
# Route stretch, from nclt/stretch_<letter>.json. Pick another per run:  STRETCH=B bash nclt/run_localize.sh
STRETCH="${STRETCH:-A}"
export STRETCH_DIR="data/nclt/stretch_$STRETCH"

# Splat method. Pick another one per run:  METHOD=wild-gaussians bash nclt/run_localize.sh
METHOD="${METHOD:-gsplat}"
if [ "$METHOD" = gsplat ]; then
    NAME="stretch_${STRETCH}_$MAP_SESSION"
    # gsplat lives in the main environment. Other methods run in their own (see nclt/jobs/install_method.sbatch).
    NB_BACKEND=python
else
    NAME="stretch_${STRETCH}_${MAP_SESSION}_$METHOD"
    NB_BACKEND=conda
    # NerfBaselines needs the conda command to start that environment. It goes last on PATH so it can't
    # replace this environment's python.
    case ":$PATH:" in *:/sw/pkgs/arc/mamba/py3.12/condabin:*) ;; *) export PATH="$PATH:/sw/pkgs/arc/mamba/py3.12/condabin" ;; esac
fi
SPLAT_DIR="results/splat/$NAME"
RESULTS_DIR="results/gsfeatloc/$NAME"

# The newest checkpoint folder in SPLAT_DIR, or nothing if training hasn't finished.
latest_checkpoint() {
    ls -d "$SPLAT_DIR"/checkpoint-* 2>/dev/null | sort -V | tail -1
}
