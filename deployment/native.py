"""V3.5 portable instance runner. No package downloads at installation time."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT.parent
EXE = ".exe" if os.name == "nt" else ""
DEFAULT_STATE = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "RollFlow-Staging"

def run(args, **kw):
    return subprocess.run([str(a) for a in args], check=True, **kw)

def write_private(path, content):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)

def harden_windows_acl(path, *, directory=False):
    """Restrict an NTFS path to the invoking user, not the Administrators group.

    PostgreSQL's Windows initdb can run with a restricted token which cannot
    depend on group-only access inherited from a temporary parent directory.
    Resolve the user's SID rather than a possibly localised account name.
    """
    import csv
    import io

    identity = subprocess.check_output(
        ["whoami.exe", "/user", "/fo", "csv", "/nh"],
        text=True, errors="replace",
    )
    rows = [row for row in csv.reader(io.StringIO(identity)) if row]
    if len(rows) != 1 or len(rows[0]) != 2:
        raise RuntimeError("Could not determine the Windows user SID.")
    sid = rows[0][1].strip()
    if not re.fullmatch(r"S-\d+(?:-\d+)+", sid):
        raise RuntimeError("Invalid Windows user SID; refusing to loosen access.")

    # Remove inherited access (which can be group-only on CI runners), and
    # grant this user's SID explicitly. Never grant Everyone/Users access.
    access = "(OI)(CI)F" if directory else "F"
    run(["icacls.exe", path, "/inheritance:r", "/grant:r",
         f"*{sid}:{access}"], stdout=subprocess.DEVNULL)


def pg(cfg, name):
    return Path(cfg["pg_bin"]) / (name + EXE)

def control(cfg, action):
    args = [pg(cfg, "pg_ctl"), "-D", Path(cfg["state"]) / "postgres", "-w"]
    if action == "start":
        args += ["-l", Path(cfg["state"]) / "postgres.log"]
    elif action == "stop":
        args += ["-m", "fast"]
    run(args + [action])

@contextmanager
def database(cfg):
    status = subprocess.run([str(pg(cfg, "pg_ctl")), "-D",
                             str(Path(cfg["state"]) / "postgres"), "status"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if status.returncode not in (0, 3):
        raise RuntimeError("Cannot determine database status; verify the instance.")
    started = status.returncode == 3
    if started:
        control(cfg, "start")
    try:
        yield
    finally:
        if started:
            control(cfg, "stop")

def config_env(cfg):
    # Do not inherit settings for another RollFlow instance.
    env = {k: v for k, v in os.environ.items() if not k.startswith("ROLLFLOW_")}
    school = cfg["mode"] == "school"
    env.update({
        "ROLLFLOW_DEBUG": "0" if school else "1",
        "ROLLFLOW_PROTECTED_WORKSPACE": "1",
        "ROLLFLOW_SCHOOL_MODE": "1" if school else "0",
        "ROLLFLOW_LIVE_TIMETABLE": "1" if school else "0",
        "ROLLFLOW_TRUST_HTTPS_PROXY": "1" if school else "0",
        "ROLLFLOW_SECRET_KEY": cfg["secret"],
        "ROLLFLOW_ALLOWED_HOSTS": cfg["host"],
        "ROLLFLOW_DB_NAME": "rollflow",
        "ROLLFLOW_DB_USER": "rollflow_app",
        "ROLLFLOW_DB_PASSWORD": cfg["db_password"],
        "ROLLFLOW_DB_HOST": "127.0.0.1",
        "ROLLFLOW_DB_PORT": str(cfg["db_port"]),
        "ROLLFLOW_DATA_DIR": cfg["state"],
        "ROLLFLOW_STATIC_ROOT": str(Path(cfg["state"]) / "static"),
    })
    return env

def manage(cfg, *args):
    run([sys.executable, ROOT / "manage.py", *args], cwd=ROOT, env=config_env(cfg))

def load(state):
    cfg = json.loads((state / "instance.json").read_text(encoding="utf-8"))
    if cfg["state"] != str(state):
        raise RuntimeError("Instance moved. Restore into a new configured installation instead.")
    return cfg

def init(args, state):
    if state.exists():
        raise RuntimeError("Instance directory already exists; refusing to overwrite it.")
    if args.mode == "school" and not args.host:
        raise RuntimeError("School mode needs the exact ICT-approved HTTPS hostname.")
    host = args.host or "localhost"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}", host) or ".." in host:
        raise RuntimeError("Specify a single DNS hostname, without protocol, port or wildcard.")
    if args.mode == "staging" and host != "localhost":
        raise RuntimeError("Synthetic staging is restricted to localhost.")
    pg_bin = (args.pg_bin or BUNDLE / "postgres" / "bin").resolve()
    for name in ("initdb", "pg_ctl", "postgres", "pg_dump"):
        if not (pg_bin / (name + EXE)).is_file():
            raise RuntimeError("Missing PostgreSQL runtime: " + name)
    state.mkdir(mode=0o700, parents=True)
    if os.name == "nt":
        harden_windows_acl(state, directory=True)
    cfg = dict(state=str(state), pg_bin=str(pg_bin), mode=args.mode, host=host,
               db_port=args.db_port, web_port=args.web_port,
               secret=secrets.token_urlsafe(64), db_password=secrets.token_urlsafe(40))
    admin_password = secrets.token_urlsafe(40)
    pwfile = state / "initial-password.txt"
    try:
        write_private(pwfile, admin_password + "\n")
        if os.name == "nt":
            harden_windows_acl(pwfile)
        run([pg(cfg, "initdb"), "-D", state / "postgres", "--encoding=UTF8",
             "--locale=C", "--username=rollflow_owner", "--auth=scram-sha-256",
             "--pwfile=" + str(pwfile)])
    finally:
        pwfile.unlink(missing_ok=True)
    # Keep database administration separate from the application's restricted role.
    write_private(state / "database-owner.txt", admin_password + "\n")
    with (state / "postgres" / "postgresql.conf").open("a", encoding="utf-8") as f:
        f.write("\nlisten_addresses = '127.0.0.1'\nport = " + str(args.db_port) + "\n")
        if os.name != "nt":
            f.write("unix_socket_directories = ''\n")
    with database(cfg):
        import psycopg
        from psycopg import sql
        with psycopg.connect(host="127.0.0.1", port=args.db_port, dbname="postgres",
                             user="rollflow_owner", password=admin_password,
                             autocommit=True) as conn:
            conn.execute(sql.SQL("CREATE ROLE rollflow_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}")
                         .format(sql.Literal(cfg["db_password"])))
            conn.execute("CREATE DATABASE rollflow OWNER rollflow_app")
        manage(cfg, "migrate", "--noinput")
        manage(cfg, "collectstatic", "--noinput")
        manage(cfg, "check")
        if not args.no_admin:
            manage(cfg, "createsuperuser")
    write_private(state / "instance.json", json.dumps(cfg, indent=2) + "\n")
    print("Instance initialised:", state)
    print("Synthetic staging only." if args.mode == "staging" else
          "ICT must configure the approved HTTPS proxy and access controls before use.")

def serve(cfg):
    # Waitress is deliberately bound to loopback in both profiles.
    os.environ.update(config_env(cfg))
    os.environ["DJANGO_SETTINGS_MODULE"] = "rollflow.settings"
    from waitress import serve as waitress_serve
    from rollflow.wsgi import application
    options = dict(host="127.0.0.1", port=cfg["web_port"])
    if cfg["mode"] == "school":
        options.update(trusted_proxy="127.0.0.1", trusted_proxy_headers={"x-forwarded-proto"})
    waitress_serve(application, **options)

def backup(cfg, output):
    output = output.resolve()
    if output.exists():
        raise RuntimeError("Backup already exists; refusing to replace it.")
    env = config_env(cfg)
    env["PGPASSWORD"] = cfg["db_password"]
    # Create with restrictive permissions, even when called outside the state directory.
    write_private(output, "")
    try:
        if os.name == "nt":
            harden_windows_acl(output)
        run([pg(cfg, "pg_dump"), "-h", "127.0.0.1", "-p", cfg["db_port"],
             "-U", "rollflow_app", "-Fc", "-f", output, "rollflow"], env=env)
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    print("Database backup created. Keep it on approved encrypted storage:", output)

def upgrade(cfg):
    """Back up a stopped existing instance before additive schema migration.

    Never initialise, replace instance.json, move PostgreSQL, rotate keys or
    delete archive data. Old PostgreSQL binaries must remain installed.
    """
    import hashlib
    import shutil
    from datetime import datetime, timezone

    state = Path(cfg["state"])
    status = subprocess.run([str(pg(cfg, "pg_ctl")), "-D", str(state / "postgres"), "status"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if status.returncode != 3:
        raise RuntimeError("Stop the existing RollFlow instance and PostgreSQL before upgrading.")
    lock = state / "upgrade-in-progress.lock"
    write_private(lock, "Existing-instance upgrade in progress.\n")
    try:
        root = state / "upgrade-backups"
        if root.is_symlink():
            raise RuntimeError("Upgrade backup directory cannot be a symbolic link.")
        root.mkdir(mode=0o700, exist_ok=True)
        if os.name == "nt":
            harden_windows_acl(root, directory=True)
        dest = root / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        dest.mkdir(mode=0o700)
        if os.name == "nt":
            harden_windows_acl(dest, directory=True)
        archive, key = state / "oneschool-imports", state / "oneschool-import.key"
        if archive.is_symlink() or key.is_symlink():
            raise RuntimeError("Archive paths cannot be symbolic links.")
        if archive.exists() and any(archive.iterdir()) and not key.is_file():
            raise RuntimeError("Original archive key is missing; recover it before upgrading.")
        def copy_verified(source, target):
            if source.is_symlink() or not source.is_file():
                raise RuntimeError("Unexpected archive entry; upgrade stopped.")
            shutil.copyfile(source, target)
            if os.name == "nt":
                harden_windows_acl(target)
            else:
                target.chmod(0o600)
            with source.open("rb") as a, target.open("rb") as b:
                if hashlib.file_digest(a, "sha256").digest() != hashlib.file_digest(b, "sha256").digest():
                    raise RuntimeError("Backup file verification failed.")
        if archive.exists():
            target = dest / "oneschool-imports"
            target.mkdir(mode=0o700)
            if os.name == "nt":
                harden_windows_acl(target, directory=True)
            for item in archive.iterdir():
                copy_verified(item, target / item.name)
        if key.exists():
            copy_verified(key, dest / key.name)
        with database(cfg):
            backup(cfg, dest / "rollflow.dump")
            run([pg(cfg, "pg_restore"), "--list", dest / "rollflow.dump"],
                stdout=subprocess.DEVNULL)
            print("Verified pre-upgrade backup:", dest)
            manage(cfg, "migrate", "--noinput")
            manage(cfg, "migrate", "--check")
            manage(cfg, "check")
            manage(cfg, "collectstatic", "--noinput")
        print("Upgrade complete. Keep the original installation and backup; start the new code.")
    finally:
        lock.unlink(missing_ok=True)


def main():
    if os.name != "nt":
        os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init")
    p.add_argument("--mode", choices=["staging", "school"], default="staging")
    p.add_argument("--host")
    p.add_argument("--pg-bin", type=Path)
    p.add_argument("--db-port", type=int, default=55432)
    p.add_argument("--web-port", type=int, default=8080)
    p.add_argument("--no-admin", action="store_true", help="Create admin separately with manage.")
    sub.add_parser("start")
    sub.add_parser("upgrade", help="Back up and migrate an existing stopped instance")
    m = sub.add_parser("manage")
    m.add_argument("args", nargs=argparse.REMAINDER)
    b = sub.add_parser("backup")
    b.add_argument("output", type=Path)
    args = parser.parse_args()
    state = args.state.expanduser().resolve()
    if args.command == "init":
        if not all(1024 <= p <= 65535 for p in (args.db_port, args.web_port)) or args.db_port == args.web_port:
            parser.error("Choose different, unprivileged TCP ports.")
        init(args, state)
        return
    cfg = load(state)
    if args.command == "upgrade":
        upgrade(cfg)
        return
    if (state / "upgrade-in-progress.lock").exists():
        raise RuntimeError("Upgrade in progress. Do not start or manage the instance.")
    with database(cfg):
        if args.command == "start":
            manage(cfg, "migrate", "--check")
            # Child starts with a clean environment and can import from the application root.
            run([sys.executable, "-m", "deployment.serve_instance", str(state)],
                cwd=ROOT, env=config_env(cfg))
        elif args.command == "manage":
            manage(cfg, *args.args)
        elif args.command == "backup":
            backup(cfg, args.output)

if __name__ == "__main__":
    main()
