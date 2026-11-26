"""Compatibility command: the public and Windows training source are now identical.

No file copying between editions is required. Check the canonical tracked files.
"""
from pathlib import Path
import argparse
from deployment.public_assets import PUBLIC_FILES

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = PUBLIC_FILES

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.parse_args()
    for name in PUBLIC:
        if not (ROOT / name).is_file():
            raise SystemExit("Missing shared source: " + name)
    if (ROOT / "training" / "index.html").exists():
        raise SystemExit("Duplicate training source is no longer supported.")
    print("Single canonical public/Windows training source verified.")

if __name__ == "__main__":
    main()
