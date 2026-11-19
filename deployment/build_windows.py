"""Build an offline Windows x64 distribution from approved runtime ZIP contents."""
import argparse
import hashlib
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
                                        "manage.py", "index.html", "requirements.txt", "README.md"], cwd=ROOT)
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
    for name, command in {
        "First Setup.cmd": "init",
        "Start RollFlow.cmd": "start",
        "Manage RollFlow.cmd": "manage",
        "Backup RollFlow.cmd": "backup",
    }.items():
        (out / name).write_text('@echo off\n"%~dp0python\\python.exe" -m deployment.native ' +
                                command + ' %*\nif errorlevel 1 pause\n', encoding="ascii")
    (out / "READ FIRST.txt").write_text(
        "V3.5 engineering staging bundle. Fictional data only.\n"
        "Copy to a local controlled directory. Run First Setup.cmd once, then Start RollFlow.cmd.\n"
        "Open http://localhost:8080/. No internet is required at runtime.\n"
        "See app/deployment/README.md for ICT restrictions, supported prerequisites and backup steps.\n",
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
