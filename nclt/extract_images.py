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


def main(windows_path, out_dir):
    windows = json.loads(Path(windows_path).read_text())
    out = Path(out_dir)
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
            if not any(a <= utime <= b for a, b in windows):
                continue
            data = archive.extractfile(member).read()
            (out / f"Cam{match.group(1)}" / f"{utime}.tiff").write_bytes(data)
            kept += 1

    (out / ".done").write_text(f"{scanned} scanned, {kept} kept\n")
    print(f"DONE scanned {scanned}, kept {kept}, {time.time() - start:.0f} s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
