# GSFeatLoc on Great Lakes

Tests whether [GSFeatLoc](https://github.com/jongwonjlee/gsfeatloc) can locate photos from different seasons in a summer 3D Gaussian splat of U-M North Campus, built from the [NCLT dataset](https://robots.engin.umich.edu/nclt/).

The team shares one copy of the environment, corrected photos and trained splat. You don't install or download anything.

**Just want the results?** Read [RESULTS.md](RESULTS.md).

## Start here

```bash
cd /scratch/rob498_rob598s002f26_class_root/rob498_rob598s002f26_class/$USER
git clone https://github.com/gsfeatloc-seasons/gsfeat_greatlakes_env.git
cd gsfeat_greatlakes_env
bash setup_shared.sh
source activate.sh
```

Run `source activate.sh` from this folder in every new shell.

To run GSFeatLoc on the shared splat, which takes about 10 minutes once it starts:

```bash
bash nclt/run_localize.sh
```

Your results go in your own `results/` folder.

## Get the team's newest results (Stretch A, B and C)

Already set up before? Do these 3 steps in a terminal on Great Lakes. New here? Do "Start here" above first.

**1. Update your copy** (pulls new scripts and links new results):

```bash
cd /scratch/rob498_rob598s002f26_class_root/rob498_rob598s002f26_class/$USER/gsfeat_greatlakes_env
git pull
bash setup_shared.sh
source activate.sh
```

**2. See the numbers.** One command compares every stretch:

```bash
python nclt/compare_results.py
```

It explains its own columns at the bottom. For the full table of one stretch, change the letter:

```bash
python nclt/show_results.py shared_results/stretch_B_2012-08-04
```

**3. See the pictures.** In https://greatlakes.arc-ts.umich.edu, open **Files**, click **Go To...** and paste:

```
/scratch/rob498_rob598s002f26_class_root/rob498_rob598s002f26_class/nandann/gsfeat_greatlakes_env/results/gsfeatloc
```

Open a stretch folder, then `vis/`. Left is the real photo, right is the splat, green lines are matches.

The stretches:

| Stretch | What's there | Summer drives in training |
|---|---|---|
| A | Right next to buildings, almost no trees | 1 |
| B | Mostly buildings, some trees | 4 |
| C | Buildings with lots of trees | 4 |

To run GSFeatLoc yourself on a stretch, put the letter in front (your results go in your own `results/`):

```bash
STRETCH=B bash nclt/run_localize.sh
```

## Where the data is

After `setup_shared.sh`, these are in your folder. They are read-only.

| What | Where |
|---|---|
| **Corrected training photos (summer)** | `data/nclt/stretch_A/dataset/2012-08-04/images/` |
| Robot masks for those photos | `data/nclt/stretch_A/dataset/2012-08-04/sampling_masks/` |
| Camera positions and 3D points | `data/nclt/stretch_A/dataset/2012-08-04/sparse/0/` |
| Train and test photo lists | `data/nclt/stretch_A/dataset/2012-08-04/train_list.txt` and `test_list.txt` |
| **Corrected test photos** | `data/nclt/stretch_A/queries/SESSION/images/` |
| True camera position of each test photo | `data/nclt/stretch_A/queries/SESSION/poses.json` |
| Trained splat | `results/splat/stretch_A_2012-08-04/checkpoint-30000/` |
| Splat renders beside real photos | `results/splat/stretch_A_2012-08-04/predictions-30000.tar.gz` |

`SESSION` is one of these:

| Session | Conditions | Used for |
|---|---|---|
| 2012-08-04 | Morning, sunny, summer | Training, and summer test photos it never trained on |
| 2012-11-04 | Morning, cloudy, no leaves | Fall test photos |
| 2012-02-12 | Midday, sunny, snow | Winter test photos |

All photos are 780 x 1170 with one shared pinhole camera: focal length 400, center (390, 585). Positions are in meters in NCLT's frame, which is the same for every session.

## Train your own splat

Give it a new name, so you don't touch the shared one. In `nclt/config.sh`, change `SPLAT_DIR`:

```bash
SPLAT_DIR="results/splat/my_splat"
```

Then:

```bash
bash nclt/run_localize.sh
```

This trains on the shared summer photos (about 30 minutes), then runs GSFeatLoc on your splat. To also keep its results apart, change `RESULTS_DIR` the same way.

To change training settings, edit `nclt/jobs/5_train_splat.sbatch`. Use `gsplat` through NerfBaselines, because GSFeatLoc needs depth.

## Check progress

```bash
squeue -u $USER
```

- `PENDING`: waiting for its turn
- `RUNNING`: working now
- Nothing listed: finished or failed

See how your jobs ended:

```bash
sacct -X -S today --format=JobName%20,State,Elapsed
```

Each job writes a log to `logs/`. To read the newest one:

```bash
tail -n 20 "logs/$(ls -t logs | head -1)"
```

The GSFeatLoc log ends with `PIPELINE COMPLETE` when everything worked.

Run anything that needs a GPU through Slurm, not on the login node. Don't use `watch` on `squeue`, because the cluster rules don't allow it.

## See the results

```bash
python nclt/show_results.py
```

If you changed `RESULTS_DIR`, add that folder to the end of the command.

| What | Where |
|---|---|
| Pictures of the matches | `results/gsfeatloc/stretch_A_2012-08-04/vis/` |
| Results as data | `results/gsfeatloc/stretch_A_2012-08-04/summary.json` |
| Results for every photo | `results/gsfeatloc/stretch_A_2012-08-04/SESSION_levelN.json` |

In the per-photo files, level 0, 1 and 2 are the three starting errors below.

### Reading the table

GSFeatLoc starts from a wrong camera position, and we measure how close it gets to the true one. For example, `start 3m 15deg` means 95% of starting positions are within 3 m and 15 degrees.

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

With the shared splat, you should get these numbers:

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

### Viewing images in your browser

1. Open https://greatlakes.arc-ts.umich.edu and go to **Files**.
2. Click **Go To...** and enter:
   ```
   /scratch/rob498_rob598s002f26_class_root/rob498_rob598s002f26_class/YOUR_UNIQNAME/gsfeat_greatlakes_env
   ```
3. Open `results/gsfeatloc/stretch_A_2012-08-04/vis/`.

Each picture shows the real photo on the left and the splat render on the right. Green lines are accepted matches, and every third one is drawn. No lines means the photo failed.

## Rebuild everything from scratch

You only need this to use a different stretch of campus or different sessions, or if the shared folder is gone. Don't run `setup_shared.sh` first. It needs its own 29 GB and about 92,000 files, and the class shares a limit of about 1 million files:

```bash
scratch-quota rob498_rob598s002f26_class_root
```

Install, then wait for `SETUP COMPLETE` at the end of `setup-*.log`:

```bash
sbatch setup_greatlakes.sbatch
```

Run all 6 steps, which takes about 1.5 to 2 hours plus queue time:

```bash
bash nclt/run_all.sh
```

To use other sessions, edit `SESSIONS` in `nclt/config.sh`. The first one trains the splat.

To check an install, run `sbatch scripts/check_env.sbatch`. It should end with `ALL CHECKS PASSED` in `check-*.log`.
