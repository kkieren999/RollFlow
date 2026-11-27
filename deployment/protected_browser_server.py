"""Start the real installed protected app for a disposable two-session browser test."""
import argparse,os,secrets,subprocess,sys,time
from pathlib import Path
from urllib.request import urlopen
from .native import ROOT,load,database,manage,config_env

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state",required=True,type=Path)
    args=parser.parse_args()
    state=args.state.resolve()
    cfg=load(state)
    if cfg["mode"]!="staging" or state.name!="rf-restored" or cfg["web_port"]!=18089:
        raise RuntimeError("Protected browser fixture requires the disposable restore state.")
    os.environ["RF_PROTECTED_BROWSER_FIXTURE"]="yes"
    os.environ["RF_PROTECTED_BROWSER_PASSWORD"]=secrets.token_urlsafe(32)
    url=f'http://localhost:{cfg["web_port"]}'
    with database(cfg):
        manage(cfg,"shell","-c","from deployment.protected_browser_fixture import seed; seed()")
        child=subprocess.Popen([sys.executable,"-m","deployment.serve_instance",str(state)],cwd=ROOT,env=config_env(cfg))
        try:
            for _ in range(80):
                try:
                    with urlopen(url+"/login/",timeout=2) as r:
                        if r.status==200:break
                except OSError:
                    if child.poll() is not None:raise RuntimeError("Protected server exited.")
                    time.sleep(.25)
            else:raise RuntimeError("Protected server did not become ready.")
            subprocess.run(["node",str(ROOT/"deployment"/"protected_browser_smoke.cjs")],cwd=ROOT,
                env={**os.environ,"RF_PROTECTED_BROWSER_URL":url},check=True,timeout=120)
            # Keep each batch below the shared-IP login limit. The guarded
            # reset is available only in this synthetic restore fixture.
            batches=("admin,principal,deputy,hod,ylc","business,office,teacher,swilliams","learning,aide,relief,guidance")
            for index,batch in enumerate(batches):
                manage(cfg,"shell","-c","from deployment.protected_browser_fixture import reset_test_login_windows; reset_test_login_windows()")
                subprocess.run(["node",str(ROOT/"deployment"/"protected_ui_parity.cjs")],cwd=ROOT,
                    env={**os.environ,"RF_PROTECTED_BROWSER_URL":url,"RF_UI_ACCOUNT_IDS":batch,
                         "RF_UI_BATCH":str(index)},check=True,timeout=180)
        finally:
            child.terminate()
            child.wait(timeout=15)

if __name__=="__main__":main()
