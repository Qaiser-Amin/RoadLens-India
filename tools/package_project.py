"""Package repository sources, verified data and built UI; omit ignored local files."""

import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    names = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
        )
        .decode()
        .split("\0")
    )
    target = ROOT / "data/tableau/roadlens-project.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(set(names)):
            if not name or name.endswith(".zip"):
                continue
            path = ROOT / name
            if path.is_file():
                archive.write(path, Path("RoadLens-India") / name)
    print(target, "—", target.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
