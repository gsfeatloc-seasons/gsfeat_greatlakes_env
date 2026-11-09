"""Keeps only the synced Velodyne scans inside the time windows from an archive on stdin.

Output files are named from the timestamp, never from archive paths.
"""
import json
import re
import sys
import tarfile
from pathlib import Path

MEMBER = re.compile(r"velodyne_sync/(\d+)\.bin$")


def main(windows_path, out_dir):
    windows = json.loads(Path(windows_path).read_text())
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    scanned = kept = 0
    with tarfile.open(fileobj=sys.stdin.buffer, mode="r|") as archive:
        for member in archive:
            scanned += 1
            match = MEMBER.search(member.name)
            if not member.isfile() or match is None:
                continue
            utime = int(match.group(1))
            if any(a <= utime <= b for a, b in windows):
                (out / f"{utime}.bin").write_bytes(archive.extractfile(member).read())
                kept += 1
    (out / ".done").write_text(f"{scanned} scanned, {kept} kept\n")
    print(f"DONE scanned {scanned}, kept {kept}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
