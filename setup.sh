#!/bin/bash
# Builds the GSFeatLoc environment. Run it through setup_greatlakes.sbatch, because
# gsplat compiles CUDA code and should be built on a GPU node.
set -eo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
source ./activate.sh

GSFEATLOC_COMMIT=66e87c9
GSPLAT_COMMIT=cc800d7750a891ab8684eac4ddbcf90b79d16295
OPENCV_REQ_FILTER='^opencv-python'

export MAMBA_ALWAYS_YES=true CONDA_ALWAYS_YES=true
mkdir -p "$CONDA_PKGS_DIRS" third_party locks

if [ ! -d "$ENV_PREFIX/conda-meta" ]; then
    echo "==> Creating the mamba environment"
    mamba env create -p "$ENV_PREFIX" -f environment.yml
fi
source ./activate.sh

echo "==> Fetching GSFeatLoc and applying the Great Lakes patch"
if [ ! -d third_party/gsfeatloc/.git ]; then
    git clone -q https://github.com/jongwonjlee/gsfeatloc.git third_party/gsfeatloc
    git -C third_party/gsfeatloc checkout -q "$GSFEATLOC_COMMIT"
    git -C third_party/gsfeatloc apply "$REPO_DIR/patches/gsfeatloc-greatlakes.patch"
fi

echo "==> Fetching gsplat"
if [ ! -d third_party/gsplat/.git ]; then
    git clone -q https://github.com/nerfstudio-project/gsplat.git third_party/gsplat
    git -C third_party/gsplat checkout -q "$GSPLAT_COMMIT"
    git -C third_party/gsplat submodule update --init --recursive
fi

echo "==> Installing Python packages"
pip install torch==2.3.0 torchvision==0.18.0 numpy==1.24.4 \
    --index-url https://download.pytorch.org/whl/cu118
pip install -U pip 'setuptools<70.0.0' wheel==0.43.0

# Both opencv-python and the headless build provide cv2, so only headless is installed.
grep -v "$OPENCV_REQ_FILTER" third_party/gsplat/examples/requirements.txt > .cache/gsplat-requirements.txt
pip install opencv-python-headless==4.10.0.84 \
    -r .cache/gsplat-requirements.txt \
    numpy==1.24.4 plyfile==0.8.1 mediapy==1.1.2 scikit-image==0.21.0 tqdm==4.66.2 \
    importlib_metadata==8.5.0 typing_extensions==4.12.2 wandb==0.19.1 click==8.1.8 \
    Pillow==11.1.0 matplotlib==3.9.4 tensorboard==2.18.0 scipy==1.13.1 \
    sympy kornia==0.8.1 loguru
pip install --no-deps nerfbaselines==1.2.9 superpoint_superglue_deployment==0.0.3

echo "==> Compiling gsplat"
export LIBRARY_PATH="$CONDA_PREFIX/lib/stubs"
ln -sf "$CC" "$CONDA_PREFIX/bin/gcc"
ln -sf "$CXX" "$CONDA_PREFIX/bin/g++"
export CPATH="$CONDA_PREFIX/x86_64-conda-linux-gnu/sysroot/usr/include${CPATH:+:$CPATH}"
(cd third_party/gsplat && MAX_JOBS="${SLURM_CPUS_PER_TASK:-8}" pip install -e . --use-pep517 --no-build-isolation)

# NerfBaselines imports modules from gsplat's examples folder.
SITE_PACKAGES="$(python -c 'import site; print(site.getsitepackages()[0])')"
echo "$REPO_DIR/third_party/gsplat/examples" > "$SITE_PACKAGES/gsplat_examples.pth"

echo "==> Recording exact versions"
pip freeze --exclude-editable > locks/pip-freeze.txt
conda list --explicit > locks/conda-explicit.txt

echo "==> Removing the download cache"
rm -rf "$CONDA_PKGS_DIRS"

echo "==> Checking the environment"
python scripts/check_env.py

echo "Files in environment: $(find "$ENV_PREFIX" -xdev | wc -l)"
echo "Size of environment: $(du -sh "$ENV_PREFIX" | cut -f1)"
echo "SETUP COMPLETE"
