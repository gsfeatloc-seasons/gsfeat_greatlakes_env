# Results so far

We tested GSFeatLoc on 3 short stretches of North Campus. Each splat was trained on summer photos. We then asked GSFeatLoc to find where photos from summer, fall and winter were taken. It started from a guess about 1 meter off.

## The numbers

**"Worked"** means GSFeatLoc found its position, not just gave up. Higher is better.

| Stretch | What's there | Summer | Fall | Winter |
|---|---|---|---|---|
| **A** | Right next to buildings | **76%** | 54% | 42% |
| **B** | Mostly buildings, some trees | 32% | 13% | 3% |
| **C** | Buildings and lots of trees | 48% | 23% | 16% |

## What we learned

1. **It works best in summer, next to buildings (Stretch A).**
2. **Fall and winter are much harder.** The splat only knows what summer looks like.
3. **Stretch B was the surprise.** It has few trees but did the worst. B and C were trained on 4 drives through the same street, while A had 1. Our best guess is that the drives don't line up perfectly, so the splat came out blurry. We're testing this next.

---

## See it yourself (3 steps)

### 1. Look at the pictures (no terminal needed)

1. Go to https://greatlakes.arc-ts.umich.edu and log in.
2. Click **Files** at the top, then **Home Directory**.
3. Click **Go To...** and paste this:
   ```
   /scratch/rob498_rob598s002f26_class_root/rob498_rob598s002f26_class/nandann/gsfeat_greatlakes_env/results/gsfeatloc
   ```
4. Open a stretch folder, then the `vis` folder. Click any picture.

In each picture, the **left** side is the real photo and the **right** side is what the splat drew. **Green lines** connect the spots GSFeatLoc matched. More lines is better. No lines means it failed.

### 2. Get the numbers in your terminal

Only the first time: do "Start here" in the [README](README.md).

Then open a terminal on Great Lakes and paste this block:

```bash
cd /scratch/rob498_rob598s002f26_class_root/rob498_rob598s002f26_class/$USER/gsfeat_greatlakes_env
git pull
bash setup_shared.sh
source activate.sh
python nclt/compare_results.py
```

You'll see the table above, plus a few more columns, explained at the bottom of what it prints.

### 3. Stuck?

- **"No such file or directory"** on the first line: you haven't set up yet. Do "Start here" in the [README](README.md) first.
- **"Permission denied"**: ask Nandan to check that you're in the class group.
- Anything else: send a screenshot in the group chat.
