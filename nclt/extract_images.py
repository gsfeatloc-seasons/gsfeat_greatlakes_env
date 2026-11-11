"""Keeps only the chosen camera frames from an NCLT image archive streamed on stdin.

Output files are named from the camera number and timestamp, never from archive paths.
"""
import json
import re
import sys
import tarfile
import time
from pathlib import Path

MEMBER = re.compile(r"^[^/]+/lb3/Cam([1-5])/(\d+)\.tiff$")


def main(pairs):
    """pairs: (windows json, output folder) per stretch, so one pass over the archive fills them all."""
    targets = [(json.loads(Path(w).read_text()), Path(o)) for w, o in pairs]
    for _, out in targets:
        for camera in range(1, 6):
            (out / f"Cam{camera}").mkdir(parents=True, exist_ok=True)

    scanned = kept = 0
    start = time.time()
    with tarfile.open(fileobj=sys.stdin.buffer, mode="r|") as archive:
        for member in archive:
            scanned += 1
            if scanned % 20000 == 0:
                print(f"scanned {scanned}, kept {kept}, {time.time() - start:.0f} s", flush=True)
            match = MEMBER.match(member.name)
            if not member.isfile() or match is None:
                continue
            utime = int(match.group(2))
            outs = [out for windows, out in targets if any(a <= utime <= b for a, b in windows)]
            if not outs:
                continue
            data = archive.extractfile(member).read()
            for out in outs:
                (out / f"Cam{match.group(1)}" / f"{utime}.tiff").write_bytes(data)
            kept += 1

    for _, out in targets:
        (out / ".done").write_text(f"{scanned} scanned, {len(list(out.glob('Cam*/*.tiff')))} kept\n")
    print(f"DONE scanned {scanned}, kept {kept}, {time.time() - start:.0f} s", flush=True)


if __name__ == "__main__":
    # Usage: extract_images.py WINDOWS_JSON OUT_DIR [WINDOWS_JSON OUT_DIR ...] < archive.tar
    args = sys.argv[1:]
    if not args or len(args) % 2:
        sys.exit("Usage: extract_images.py WINDOWS_JSON OUT_DIR [WINDOWS_JSON OUT_DIR ...]")
    main(list(zip(args[::2], args[1::2])))
