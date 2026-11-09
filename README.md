# GSFeatLoc on Great Lakes

Tests whether [GSFeatLoc](https://github.com/jongwonjlee/gsfeatloc) can locate photos from different seasons in a summer 3D Gaussian splat of U-M North Campus, built from the [NCLT dataset](https://robots.engin.umich.edu/nclt/).

The test uses one 250 m building-heavy stretch of campus:

| Session | Conditions | Used for |
|---|---|---|
| 2012-08-04 | Morning, sunny, summer | Training the splat, and summer test photos it never trained on |
| 2012-11-04 | Morning, cloudy, no leaves | Fall test photos |
| 2012-02-12 | Midday, sunny, snow | Winter test photos |

## 1. Install

Takes about 40 minutes once the job starts. Uses 14 GB and about 70,000 files.

The class shares a limit of about 1 million files, so check it first:

```bash
scratch-quota rob498_rob598s002f26_class_root
```

Look at the `files` and `limit` columns on the right. The limit is 1,048,576. You need about 92,000 files free for the install and the full run.

Then install:

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

## 2. Run everything

From the `gsfeat_greatlakes_env` folder:

```bash
bash nclt/run_all.sh
```

This submits 6 jobs that run in order. Expect about 1.5 to 2 hours plus queue time. It uses about 15 GB and 22,000 files.

| Step | What it does | Time |
|---|---|---|
| 1. Prepare | Downloads positions and calibration | 1 min |
| 2. Pull images | Keeps only the photos from our stretch | 20 min per session |
| 3. Pull laser scans | Keeps only the scans from that stretch | 5 min |
| 4. Build dataset | Corrects and masks the photos | 15 min |
| 5. Train splat | Trains on the August 4 photos | 30 min |
| 6. Localize | Runs GSFeatLoc on all three seasons | 10 min |

### Check progress

```bash
squeue -u $USER
```

- `PENDING`: waiting for its turn or for the step before it
- `RUNNING`: working now
- Nothing listed: all done, or a step failed

See how the steps ended:

```bash
sacct -X -S today --format=JobName%20,State,Elapsed
```

Each step writes a log to `logs/`. To read the newest one:

```bash
tail -n 20 "logs/$(ls -t logs | head -1)"
```

The last step's log ends with `PIPELINE COMPLETE` when everything worked.

### If a step fails

The steps after it are cancelled. Read that step's log in `logs/`, fix the problem, and run `bash nclt/run_all.sh` again. Finished downloads and training are skipped.

## 3. See the results

Everything is in the `gsfeat_greatlakes_env` folder.

| What | Where |
|---|---|
| Results table | `python nclt/show_results.py` |
| Pictures of the matches | `results/gsfeatloc/stretch_A_2012-08-04/vis/` |
| Results as data | `results/gsfeatloc/stretch_A_2012-08-04/summary.json` |
| Results for every photo | `results/gsfeatloc/stretch_A_2012-08-04/SESSION_levelN.json` |
| Splat quality scores | `results/splat/stretch_A_2012-08-04/results-30000.json` |
| Splat renders and real photos | `results/splat/stretch_A_2012-08-04/predictions-30000.tar.gz` |
| Trained splat | `results/splat/stretch_A_2012-08-04/checkpoint-30000/` |
| Training photos | `data/nclt/stretch_A/dataset/2012-08-04/images/` |
| Test photos | `data/nclt/stretch_A/queries/SESSION/images/` |

In the per-photo files, level 0, 1 and 2 are the three starting errors in the table below.

### Results table

```bash
source activate.sh
python nclt/show_results.py
```

Each row is one season at one starting error. GSFeatLoc starts from a wrong camera position, and we measure how close it gets to the true one. For example, `start 3m 15deg` means 95% of starting positions are within 3 m and 15 degrees.

| Column | Meaning |
|---|---|
| Failed | Photos with too few good matches. These stay at their starting position |
| Start (m) | Typical position error before GSFeatLoc |
| Final (m) | Typical position error after GSFeatLoc. Lower is better |
| Final deg | Typical rotation error after GSFeatLoc. Lower is better |
| <0.25m | Photos within 0.25 m and 2 degrees |
| <0.5m | Photos within 0.5 m and 5 degrees |
| <1m | Photos within 1 m and 10 degrees |

"Typical" means the median. Failed photos are included in every column.

Your numbers should match these if you use the same data and settings. A newly trained splat will differ somewhat.

```
Run                                 Failed  Start (m)  Final (m) Final deg    <0.25m     <0.5m       <1m
2012-08-04 start 1m 5deg               24%       0.34       0.31       1.3       35%       77%       97%
2012-08-04 start 3m 15deg              36%       1.03       0.78       2.0       14%       36%       57%
2012-08-04 start 10m 30deg             58%       3.02       2.56       6.1        7%       17%       27%
2012-11-04 start 1m 5deg               46%       0.34       0.39       2.3       13%       63%       94%
2012-11-04 start 3m 15deg              57%       1.03       0.90       3.6        4%       21%       48%
2012-11-04 start 10m 30deg             78%       3.03       2.80       7.3        0%        9%       19%
2012-02-12 start 1m 5deg               58%       0.33       0.41       2.1       15%       58%       89%
2012-02-12 start 3m 15deg              66%       1.02       0.95       3.8        5%       22%       46%
2012-02-12 start 10m 30deg             79%       3.40       3.40       7.5        1%        8%       17%
```

### Pictures and other files

1. Open https://greatlakes.arc-ts.umich.edu and go to **Files**.
2. Click **Go To...** and enter:
   ```
   /scratch/rob498_rob598s002f26_class_root/rob498_rob598s002f26_class/YOUR_UNIQNAME/gsfeat_greatlakes_env
   ```
3. Open `results/gsfeatloc/stretch_A_2012-08-04/vis/`.

Each picture shows the real photo on the left and the splat render on the right. Green lines are accepted matches, and every third one is drawn. No lines means the photo failed. There are 3 pictures per season, all starting from up to 3 m and 15 degrees of error.

## Change something

- **Use other sessions:** edit `SESSIONS` in `nclt/config.sh`. The first one trains the splat.
- **Retrain the splat:** delete `results/splat/stretch_A_2012-08-04`, then run `bash nclt/run_all.sh`. To keep the old one, change `SPLAT_DIR` in `nclt/config.sh` instead.
- **Change training settings:** edit `nclt/jobs/5_train_splat.sbatch`.
- **Train a splat another way:** use `gsplat` through NerfBaselines, because GSFeatLoc needs depth.

Run `source activate.sh` in every new shell. Run anything that needs a GPU through Slurm, not on the login node. Don't use `watch` on `squeue`, because the cluster rules don't allow it.

## Check the install

- `sbatch scripts/check_env.sbatch` checks the GPU, gsplat and the matchers. It takes about a minute. The result is in `check-*.log` and should end with `ALL CHECKS PASSED`.
- `sbatch scripts/smoke_test.sbatch` trains a small sample scene and runs GSFeatLoc on it. It takes about 20 minutes. Results are at the end of `smoke-*.log`, with about 97% success.
