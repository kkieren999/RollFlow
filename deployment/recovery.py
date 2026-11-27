"""Private consistent snapshot and isolated staging recovery, never in-place restore."""
import json,os,shutil,subprocess
from pathlib import Path
from types import SimpleNamespace
from .bundle_integrity import manifest,verify,digest
from .native import database,pg,backup,run,manage,config_env,harden_windows_acl,write_private,init


def stopped(cfg):
    state=Path(cfg["state"])
    status=subprocess.run([str(pg(cfg,"pg_ctl")),"-D",str(state/"postgres"),"status"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if status.returncode!=3:raise RuntimeError("Stop the database and web server before this operation.")


def private_dir(path):
    path.mkdir(mode=0o700,parents=False)
    if os.name=="nt":harden_windows_acl(path,directory=True)


def copy_private(source,target):
    if source.is_symlink() or not source.is_file():raise ValueError("Unsafe source file.")
    shutil.copyfile(source,target)
    if os.name=="nt":harden_windows_acl(target)
    else:target.chmod(0o600)
    if digest(source)!=digest(target):raise ValueError("Backup copy checksum mismatch.")


def copy_archive(src,dst):
    archive,key=src/"oneschool-imports",src/"oneschool-import.key"
    if archive.is_symlink() or key.is_symlink():raise ValueError("Unexpected archive symlink.")
    if archive.exists():
        if not archive.is_dir():raise ValueError("Invalid archive directory.")
        if any(archive.iterdir()) and not key.is_file():raise ValueError("Archive key missing.")
        private_dir(dst/"oneschool-imports")
        for f in archive.iterdir():
            if f.suffix!=".rfenc":raise ValueError("Unexpected archive file.")
            copy_private(f,dst/"oneschool-imports"/f.name)
    if key.exists():copy_private(key,dst/key.name)


def seal(path,mode):
    write_private(path/"SNAPSHOT.json",json.dumps({"format":1,"mode":mode,"contains_private_data":True})+"\n")
    manifest(path,"SNAPSHOT-SHA256.txt")
    verify(path,"SNAPSHOT-SHA256.txt",strict=True)


def snapshot(cfg,dest):
    stopped(cfg)
    state=Path(cfg["state"])
    dest=dest.resolve()
    if dest.exists() or dest.is_relative_to(state/"postgres"):
        raise ValueError("Choose a new backup folder outside database storage.")
    lock=state/"upgrade-in-progress.lock"
    write_private(lock,"Private snapshot in progress.\n")
    try:
        private_dir(dest)
        copy_archive(state,dest)
        with database(cfg):
            backup(cfg,dest/"rollflow.dump")
            run([pg(cfg,"pg_restore"),"--list",dest/"rollflow.dump"],stdout=subprocess.DEVNULL)
        seal(dest,cfg["mode"])
        print("Verified private snapshot created. Store on approved encrypted storage.")
    finally:
        lock.unlink(missing_ok=True)


def restore(snapshot_path,state,pg_bin,db_port,web_port):
    """Only synthetic staging recovery, into a new directory with separate ports."""
    snap=snapshot_path.resolve()
    if state.exists() or state.is_relative_to(snap):
        raise ValueError("Restore only into a new independent state directory.")
    verify(snap,"SNAPSHOT-SHA256.txt",strict=True)
    # No arbitrary files, nested paths or partial archives in a recovery snapshot.
    allowed={"SNAPSHOT.json","SNAPSHOT-SHA256.txt","rollflow.dump","oneschool-import.key","oneschool-imports"}
    if any(p.name not in allowed for p in snap.iterdir()):
        raise ValueError("Unexpected snapshot entry.")
    archive=snap/"oneschool-imports"
    if archive.exists() and (not archive.is_dir() or any(not p.is_file() or p.is_symlink() or p.suffix!=".rfenc" for p in archive.iterdir())):
        raise ValueError("Invalid snapshot archive.")
    if archive.is_dir() and any(archive.iterdir()) and not (snap/"oneschool-import.key").is_file():
        raise ValueError("Snapshot archive key missing.")
    meta=json.loads((snap/"SNAPSHOT.json").read_text(encoding="utf-8"))
    if meta!={"format":1,"mode":"staging","contains_private_data":True}:
        raise ValueError("Only staging snapshots supported by this recovery tool.")
    if not (snap/"rollflow.dump").is_file():
        raise ValueError("Snapshot dump missing.")
    with (snap/"rollflow.dump").open("rb") as stream:
        if stream.read(5)!=b"PGDMP":raise ValueError("Invalid PostgreSQL dump.")
    # Reject structurally unreadable dumps before creating destination state.
    from .native import BUNDLE,EXE
    runtime=(pg_bin or BUNDLE/"postgres"/"bin").resolve()
    run([runtime/("pg_restore"+EXE),"--list",snap/"rollflow.dump"],stdout=subprocess.DEVNULL)
    init(SimpleNamespace(mode="staging",host=None,pg_bin=runtime,db_port=db_port,web_port=web_port,no_admin=True),state)
    from .native import load
    cfg=load(state)
    marker=state/"recovery-required.lock"
    write_private(marker,"Isolated restore not yet validated.\n")
    with database(cfg):
        import psycopg
        with psycopg.connect(host="127.0.0.1",port=db_port,dbname="rollflow",user="rollflow_app",password=cfg["db_password"],autocommit=True) as conn:
            # This is the new, just-initialised destination only.
            conn.execute("DROP SCHEMA public CASCADE")
            conn.execute("CREATE SCHEMA public")
        env=config_env(cfg)
        env["PGPASSWORD"]=cfg["db_password"]
        run([pg(cfg,"pg_restore"),"--exit-on-error","--single-transaction","--no-owner","--no-privileges","-h","127.0.0.1","-p",db_port,"-U","rollflow_app","-d","rollflow",snap/"rollflow.dump"],env=env)
        copy_archive(snap,state)
        manage(cfg,"migrate","--noinput")
        manage(cfg,"shell","-c","from django.contrib.sessions.models import Session; Session.objects.all().delete()")
        manage(cfg,"check")
        manage(cfg,"collectstatic","--noinput")
    marker.unlink()
    print("Isolated staging restore validated. Original state was not changed.")


def diagnostics(cfg):
    print("Mode:",cfg.get("mode","unknown"))
    print("Database runtime present:",pg(cfg,"pg_ctl").is_file())
    print("Recovery marker present:",(Path(cfg["state"])/"recovery-required.lock").exists())
    print("Native operation lock present:",(Path(cfg["state"])/"native-operation.lock").exists())
    print("Upgrade lock present:",(Path(cfg["state"])/"upgrade-in-progress.lock").exists())
    print("No credentials, student records or database logs included.")
