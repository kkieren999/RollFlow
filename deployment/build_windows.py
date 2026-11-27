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
    p.add_argument("--client-output", type=Path, help="Separate lightweight staff workstation bundle")
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
    if args.client_output and (args.client_output.resolve().exists() or args.client_output.resolve().is_relative_to(out)):
        p.error("Client output must be a new separate directory.")
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
        "version": "5.0.0-rc.2.3",
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "website_commit": (app / "training" / "SOURCE_COMMIT.txt").read_text().strip(),
        "website_mode": "exact offline public workspace; fictional data only",
        "protected_mode": "database-backed staging with shared protected interface",
        "channel": "unsigned synthetic staging release candidate"
    }, indent=2) + "\n", encoding="utf-8")
    (out / "READ FIRST.txt").write_text(
        "ROLLFLOW 5.0 RC2.3 - SCHOOL MANAGEMENT SYSTEM (STAGING)\n"
        "Extract the entire package to a new local folder before running it.\n"
        "Start RollFlow.cmd opens the protected database workspace menu.\n"
        "Open Training Demo.cmd opens the separate fictional offline website without database setup.\n"
        "Training accounts and records are fictional browser-local data, not secure school accounts.\n"
        "For protected database-backed testing, open Protected Workspace.cmd and follow its menu.\n"
        "NEW TEST DATABASE: First Setup Fresh.cmd, then Start Fresh Protected.cmd.\n"
        "EXISTING DATABASE: stop the old server, keep the previous extracted folder, run Upgrade Existing.cmd,\n"
        "then Start Existing Protected.cmd. Never initialise or delete an existing instance.\n"
        "Existing school staging data and the fresh database are not shared.\n"
        "Protected teacher and student workflow alignment added; full workflow parity and production approval remain open.\n"
        "See app/deployment/README.md and app/docs/v5.0-release-candidate.md. No real school data in staging.\n",
        encoding="utf-8")
    (out / "Verify Package.cmd").write_text('@echo off\n"%~dp0python\\python.exe" -B -m deployment.bundle_integrity "%~dp0."\npause\n',encoding="ascii")
    if __package__:
        from .bundle_integrity import manifest
    else:
        from bundle_integrity import manifest
    (out / "Production Readiness.cmd").write_text('@echo off\n"%~dp0python\\python.exe" -B -m deployment.release_readiness\npause\n',encoding="ascii")
    manifest(out)
    if args.client_output:
        client=args.client_output.resolve()
        client.mkdir()
        shutil.copytree(args.python_runtime,client/"python")
        for name in ("workstation.py","bundle_integrity.py"):
            shutil.copyfile(ROOT/"deployment"/name,client/name)
        for name,cmd in (("Configure School Server.cmd","configure"),("Open School Server.cmd","open"),("School Connection Diagnostics.cmd","diagnose")):
            (client/name).write_text('@echo off\n"%~dp0python\\python.exe" -B "%~dp0workstation.py" '+cmd+'\nif errorlevel 1 pause\n'+('pause\n' if cmd!="open" else ''),encoding="ascii")
        (client/"BUILD-INFO.json").write_text(json.dumps({"version":"5.0.0-rc.2.3","channel":"unsigned synthetic staging release candidate","source_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"mode":"HTTPS browser launcher only"},indent=2),encoding="utf-8")
        (client/"READ FIRST.txt").write_text("Configure the exact school ICT-approved HTTPS server. No database, credentials or student records are stored by the launcher. Use your browser to sign in. Unsigned staging; no real records.\n",encoding="utf-8")
        manifest(client)


if __name__ == "__main__":
    main()
