"""Generate a public Pages artifact from the same allowlist as Windows training."""
import argparse
from pathlib import Path
import shutil
from .public_assets import PUBLIC_FILES

ROOT = Path(__file__).resolve().parents[1]

def build(output):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Choose a new empty output path; refusing to overwrite.")
    output.mkdir(parents=True)
    for name in PUBLIC_FILES:
        source = ROOT / name
        if not source.is_file() or source.is_symlink() or ROOT not in source.resolve().parents:
            raise ValueError("Invalid public source: " + name)
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    (output / ".nojekyll").write_text("", encoding="utf-8")
    return output

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print("Public-only Pages artifact:", build(args.output))

if __name__ == "__main__":
    main()
