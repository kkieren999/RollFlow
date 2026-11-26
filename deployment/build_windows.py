"""Build an offline Windows x64 distribution from approved runtime ZIP contents."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--python-runtime", required=True, type=Path,
                   help="Extracted official CPython 3.14 x64 embeddable distribution")
    p.add_argument("--postgres-runtime", required=True, type=Path,
                   help="Extracted Windows x64 PostgreSQL binary distribution (bin/lib/share)")
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    if sys.platform != "win32" or sys.version_info[:2] != (3, 14) or struct.calcsize("P") != 8:
        p.error("Build using Windows x64 CPython 3.14.")
    out = args.output.resolve()
    if out.exists():
        p.error("Output directory already exists.")
    if not (args.python_runtime / "python314._pth").is_file():
        p.error("Expected official CPython 3.14 embeddable runtime.")
    if not all((args.postgres_runtime / name).is_dir() for name in ("bin", "lib", "share")):
        p.error("Expected PostgreSQL binary distribution.")
    out.mkdir(parents=True)
    shutil.copytree(args.python_runtime, out / "python")
    shutil.copytree(args.postgres_runtime, out / "postgres")
    app = out / "app"
    app.mkdir()
    # Only tracked application source; no local databases, secrets or exports.
    archive = subprocess.check_output(["git", "archive", "--format=zip", "HEAD",
                                        "accounts", "rollflow", "templates", "deployment",
                                        "manage.py", "index.html", "requirements.txt", "README.md", "training", "docs"], cwd=ROOT)
    import io
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        z.extractall(app)
    wheelhouse = out / "wheelhouse"
    subprocess.run([sys.executable, "-m", "pip", "download", "--only-binary=:all:",
                    "-r", str(app / "requirements.txt"), "-d", str(wheelhouse)], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "--no-index", "--find-links",
                    str(wheelhouse), "--only-binary=:all:", "--target",
                    str(out / "python" / "Lib" / "site-packages"),
                    "-r", str(app / "requirements.txt")], check=True)
    (out / "python" / "python314._pth").write_text(
        "python314.zip\n.\nLib/site-packages\n../app\nimport site\n", encoding="ascii")
    subprocess.run([str(out / "python" / "python.exe"), "-c",
                    "import django, psycopg, waitress, whitenoise, PIL, argon2; print(django.get_version())"],
                   cwd=out, check=True)
    if __package__:
        from .windows_launchers import write_launchers
    else:
        from windows_launchers import write_launchers
    write_launchers(out)
    (out / "BUILD-INFO.json").write_text(json.dumps({
        "version": "4.1.0-staging",
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "website_commit": (app / "training" / "SOURCE_COMMIT.txt").read_text().strip(),
        "website_mode": "exact offline public workspace; fictional data only",
        "protected_mode": "separate database-backed staging application",
        "channel": "unsigned staging"
    }, indent=2) + "\n", encoding="utf-8")
    (out / "READ FIRST.txt").write_text(
        "ROLLFLOW 4.1 - SCHOOL MANAGEMENT SYSTEM (STAGING)\n"
        "Extract the entire package to a new local folder before running it.\n"
        "Start RollFlow.cmd opens the protected database workspace menu.\n"
        "Open Training Demo.cmd opens the separate fictional offline website without database setup.\n"
        "Training accounts and records are fictional browser-local data, not secure school accounts.\n"
        "For protected database-backed testing, open Protected Workspace.cmd and follow its menu.\n"
        "NEW TEST DATABASE: First Setup Fresh.cmd, then Start Fresh Protected.cmd.\n"
        "EXISTING DATABASE: stop the old server, keep the previous extracted folder, run Upgrade Existing.cmd,\n"
        "then Start Existing Protected.cmd. Never initialise or delete an existing instance.\n"
        "Existing school staging data and the fresh database are not shared.\n"
        "Protected mode is not yet feature-equivalent to the public training workspace.\n"
        "See app/deployment/README.md and app/docs/v4.1-school-data.md. No real school data in staging.\n",
        encoding="utf-8")
    manifest = []
    for path in sorted(out.rglob("*")):
        if path.is_file():
            with path.open("rb") as f:
                digest = hashlib.file_digest(f, "sha256").hexdigest()
            manifest.append(digest + "  " + path.relative_to(out).as_posix())
    (out / "SHA256SUMS.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
