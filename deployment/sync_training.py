"""Copy/check only tracked public demo files from an explicit Git commit.

Run from the Windows source checkout after fetching origin/main. This never
reads a local school database, archive, settings, or browser profile.
"""
import argparse
import io
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "training"

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", help="Git source ref (default origin/main for write, pinned commit for check)")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    ref = args.ref or ((TARGET / "SOURCE_COMMIT.txt").read_text().strip() if args.check else "origin/main")
    commit = git("rev-parse", "--verify", ref+"^{commit}").decode().strip()
    archive = git("archive", "--format=zip", commit, "index.html", "design-system.html", "styles", "tests")
    expected = {"SOURCE_COMMIT.txt": (commit+"\n").encode()}
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        for info in z.infolist():
            if not info.is_dir():
                expected[info.filename] = z.read(info)
    if args.check:
        actual = {p.relative_to(TARGET).as_posix(): p.read_bytes() for p in TARGET.rglob("*") if p.is_file()}
        if actual != expected:
            raise SystemExit("Training files do not match pinned public Git commit.")
        print("Public training snapshot verified:", commit)
        return
    for name, content in expected.items():
        dest = TARGET / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
    # Never remove unrelated/untracked files automatically.
    print("Copied public training snapshot:", commit, "— review and commit the training directory.")

if __name__ == "__main__":
    main()
