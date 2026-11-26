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
        pg_bin = "/usr/lib/postgresql/16/bin"
        call("-m", "deployment.native", "--state", state, "init", "--pg-bin", pg_bin, "--no-admin",
             "--db-port", "55432", "--web-port", "18080")
        cfg = load(state)
        with database(cfg):
            manage(cfg, "makemigrations", "--check", "--dry-run")
            # Permit creation of the isolated Django test database only during CI.
            import psycopg
            with psycopg.connect(host="127.0.0.1", port=cfg["db_port"], dbname="postgres",
                                 user="rollflow_owner", password=(state / "database-owner.txt").read_text().strip(),
                                 autocommit=True) as conn:
                conn.execute("ALTER ROLE rollflow_app CREATEDB")
                try:
                    call("manage.py", "test", "accounts", env={**config_env(cfg), "ROLLFLOW_PROTECTED_WORKSPACE": "0"})
                finally:
                    conn.execute("ALTER ROLE rollflow_app NOCREATEDB")
                assert conn.execute("SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = 'rollflow_app'").fetchone() == (False, False, False)
            import secrets
            env = config_env(cfg)
            env.update(DJANGO_SUPERUSER_USERNAME="ci_local_admin", DJANGO_SUPERUSER_EMAIL="ci@example.invalid",
                       DJANGO_SUPERUSER_PASSWORD=secrets.token_urlsafe(32))
            call("manage.py", "createsuperuser", "--noinput", env=env)
            call("manage.py", "shell", "-c", "import os; from django.test import Client; from django.contrib.auth import get_user_model; from django.contrib.auth.hashers import identify_hasher; u=get_user_model().objects.get(username='ci_local_admin'); assert identify_hasher(u.password).algorithm == 'argon2'; assert Client().login(username=u.username,password=os.environ['DJANGO_SUPERUSER_PASSWORD']); c=Client(HTTP_HOST='localhost'); assert c.login(username=u.username,password=os.environ['DJANGO_SUPERUSER_PASSWORD']); response=c.get('/'); assert response.status_code == 302, response.status_code; assert response['Location'] == '/live/'; assert c.get('/live/').status_code == 200; print('Local hashed accounts and protected workspace verified')", env=env)
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
        call("-m", "deployment.native", "--state", state, "manage", "shell", "-c",
             "from django.contrib.auth import get_user_model; assert get_user_model().objects.filter(username='ci_local_admin',is_superuser=True).exists()")
        print("Native PostgreSQL initialization, restart, backup and HTTP smoke passed")

if __name__ == "__main__":
    main()
