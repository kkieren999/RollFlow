"""Run the native PostgreSQL launcher and verify protected school settings."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.request import urlopen
import time

from native import config_env, database, load, manage

ROOT = Path(__file__).resolve().parents[1]

def call(*args, **kwargs):
    subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, check=True, **kwargs)

def main():
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "instance"
        pg_bin = subprocess.check_output(["pg_config", "--bindir"], text=True).strip()
        call("-m", "deployment.native", "--state", state, "init", "--pg-bin", pg_bin, "--no-admin",
             "--db-port", "55432", "--web-port", "18080")
        cfg = load(state)
        with database(cfg):
            manage(cfg, "makemigrations", "--check", "--dry-run")
            # Dedicated test database needs CREATEDB; use cluster owner only for CI.
            # The application itself stays a restricted role.
            env = config_env(cfg)
            env.update(ROLLFLOW_DB_USER="rollflow_owner",
                       ROLLFLOW_DB_PASSWORD=(state / "database-owner.txt").read_text().strip())
            call("manage.py", "test", "accounts", env=env)
            child = subprocess.Popen([sys.executable, "-m", "deployment.serve_instance", str(state)],
                                     cwd=ROOT, env=config_env(cfg))
            try:
                for _ in range(40):
                    try:
                        with urlopen("http://localhost:18080/login/", timeout=2) as response:
                            assert response.status == 200
                        break
                    except OSError:
                        if child.poll() is not None:
                            raise RuntimeError("WSGI server exited")
                        time.sleep(.25)
                else:
                    raise RuntimeError("WSGI server did not answer")
            finally:
                child.terminate()
                child.wait(timeout=15)
            school = dict(cfg, mode="school", host="rollflow.school.example")
            env = config_env(school)
            call("manage.py", "check", env=env)
            call("manage.py", "check", "--deploy", env=env)
            call("manage.py", "shell", "-c",
                 "from django.test import Client; r=Client().get('/login/', secure=True, HTTP_HOST='rollflow.school.example'); assert r.status_code==200; assert 'connect-src' in r['Content-Security-Policy']; assert Client().get('/login/', HTTP_HOST='rollflow.school.example').status_code == 301; print('School security smoke passed')",
                 env=env)
            env["ROLLFLOW_DEBUG"] = "1"
            bad = subprocess.run([sys.executable, "manage.py", "check"], cwd=ROOT, env=env,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            assert bad.returncode != 0, "School configuration must reject debug"
        dump = Path(tmp) / "backup.dump"
        call("-m", "deployment.native", "--state", state, "backup", dump)
        assert dump.read_bytes().startswith(b"PGDMP")
        # Reopen an existing instance and verify migrations survive stop/start.
        call("-m", "deployment.native", "--state", state, "manage", "migrate", "--check")
        print("Native PostgreSQL initialization, restart, backup and HTTP smoke passed")

if __name__ == "__main__":
    main()
