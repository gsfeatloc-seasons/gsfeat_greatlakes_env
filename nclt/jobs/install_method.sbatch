#!/bin/bash
# Builds the separate environment a splat method needs. gsplat doesn't need this.
# Usage:  METHOD=wild-gaussians sbatch nclt/jobs/install_method.sbatch
#SBATCH --job-name=nclt-install-method
#SBATCH --account=rob498_rob598s002f26_class
#SBATCH --partition=gpu
#SBATCH --gpus=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=logs/%x-%j.log

set -eo pipefail
cd "$SLURM_SUBMIT_DIR"
source ./activate.sh
: "${METHOD:?Set METHOD, for example METHOD=wild-gaussians}"
# The method's install script needs conda itself, which activate.sh unloads.
module load mamba/py3.12
# Great Lakes GPUs: V100 (7.0) and A100 (8.0).
export TORCH_CUDA_ARCH_LIST="7.0;8.0"
export MAMBA_ALWAYS_YES=true CONDA_ALWAYS_YES=true CONDA_SOLVER=libmamba
mkdir -p "$NERFBASELINES_CONDA_ENVIRONMENTS"

# Same as "nerfbaselines install --backend conda", but without a login shell. A login shell runs
# ~/.bashrc, which can switch to an older conda whose package solver takes hours.
"$ENV_PREFIX/bin/python" - "$METHOD" > .cache/install-$METHOD.sh <<'PY'
import os, sys
from nerfbaselines import get_method_spec
from nerfbaselines.backends._conda import conda_get_install_script
import nerfbaselines
package_path = os.path.dirname(os.path.dirname(os.path.abspath(nerfbaselines.__file__)))
print(conda_get_install_script(get_method_spec(sys.argv[1])["conda"], package_path=package_path))
PY
bash .cache/install-$METHOD.sh
echo "INSTALL COMPLETE"
