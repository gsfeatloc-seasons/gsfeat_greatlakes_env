# GSFeatLoc on Great Lakes

Sets up [GSFeatLoc](https://github.com/jongwonjlee/gsfeatloc) on the U-M Great Lakes cluster.

**Status:** work in progress. Install checks pass. The full test on a real splat is still being verified.

## Install

The install takes about 40 minutes once the job starts. It uses 14 GB and about 80,000 files.

```bash
cd /scratch/rob498_rob598s002f26_class_root/rob498_rob598s002f26_class/$USER
git clone https://github.com/gsfeatloc-seasons/gsfeat_greatlakes_env.git
cd gsfeat_greatlakes_env
sbatch setup_greatlakes.sbatch
```

Check the job with `squeue -u $USER`. When it's gone from the list, run:

```bash
tail setup-*.log
```

The last line should say `SETUP COMPLETE`.

The class shares a limit on the number of files. Check it before installing:

```bash
scratch-quota rob498_rob598s002f26_class_root
```

## Use

Run this in every new shell or job:

```bash
source activate.sh
```

Run anything that needs a GPU through Slurm, not on the login node.

## Train a splat

Use `gsplat`. GSFeatLoc needs depth, and this method provides it.

```bash
nerfbaselines train --method gsplat --backend python --data DATA_FOLDER --output OUTPUT_FOLDER
```

## Run GSFeatLoc

```bash
python third_party/gsfeatloc/gsfeatloc_cli.py \
    --scene_path DATA_FOLDER \
    --model_path OUTPUT_FOLDER/checkpoint-30000 \
    --output_path RESULTS_FOLDER
```

## Test the setup

This trains a splat on a small sample scene and runs GSFeatLoc on it:

```bash
sbatch scripts/smoke_test.sbatch
```

Results are at the end of `smoke-*.log`.
