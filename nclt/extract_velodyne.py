"""Keeps only the synced Velodyne scans inside the time windows from an archive on stdin.

Output files are named from the timestamp, never from archive paths.
"""
import json
import re
import sys
import tarfile
from pathlib import Path

MEMBER = re.compile(r"velodyne_sync/(\d+)\.bin$")


def main(pairs):
    """pairs: (windows json, output folder) per stretch, so one pass over the archive fills them all."""
    targets = [(json.loads(Path(w).read_text()), Path(o)) for w, o in pairs]
    for _, out in targets:
        out.mkdir(parents=True, exist_ok=True)
    scanned = kept = 0
    with tarfile.open(fileobj=sys.stdin.buffer, mode="r|") as archive:
        for member in archive:
            scanned += 1
            match = MEMBER.search(member.name)
            if not member.isfile() or match is None:
                continue
            utime = int(match.group(1))
            outs = [out for windows, out in targets if any(a <= utime <= b for a, b in windows)]
            if outs:
                data = archive.extractfile(member).read()
                for out in outs:
                    (out / f"{utime}.bin").write_bytes(data)
                kept += 1
    for _, out in targets:
        (out / ".done").write_text(f"{scanned} scanned, {len(list(out.glob('*.bin')))} kept\n")
    print(f"DONE scanned {scanned}, kept {kept}", flush=True)


if __name__ == "__main__":
    # Usage: extract_velodyne.py WINDOWS_JSON OUT_DIR [WINDOWS_JSON OUT_DIR ...] < archive.tar
    args = sys.argv[1:]
    if not args or len(args) % 2:
        sys.exit("Usage: extract_velodyne.py WINDOWS_JSON OUT_DIR [WINDOWS_JSON OUT_DIR ...]")
    main(list(zip(args[::2], args[1::2])))
