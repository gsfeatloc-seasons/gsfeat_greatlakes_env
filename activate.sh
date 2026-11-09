# Load the environment in your current shell:  source activate.sh
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export REPO_DIR
export ENV_PREFIX="$REPO_DIR/.mamba/gsfeatloc"

module purge
module load mamba/py3.12
eval "$(conda shell.bash hook)"

# Everything large stays in this folder because home directories have little space.
export CONDA_PKGS_DIRS="$REPO_DIR/.cache/conda_pkgs"
export XDG_CACHE_HOME="$REPO_DIR/.cache"
# superpoint_superglue_deployment only looks for its weights in this folder (about 100 MB).
export TORCH_HOME="$HOME/.cache/torch"
export NERFBASELINES_PREFIX="$REPO_DIR/.cache/nerfbaselines"
export PIP_NO_CACHE_DIR=1
export PYTHONNOUSERSITE=1
export GSFEATLOC_BACKEND=python
export PYTHONPATH="$REPO_DIR/third_party/gsfeatloc${PYTHONPATH:+:$PYTHONPATH}"

if [ -d "$ENV_PREFIX/conda-meta" ]; then
    conda activate "$ENV_PREFIX"
    # The mamba module's libraries can shadow the ones inside the environment.
    module unload mamba/py3.12
    export CONDA_PKGS_DIRS="$REPO_DIR/.cache/conda_pkgs"
fi
