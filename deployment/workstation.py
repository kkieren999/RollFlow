"""Staff workstation launcher: HTTPS browser only, no local database or credentials."""
import argparse
import json
import os
from pathlib import Path
import re
import ssl
import tempfile
from urllib.parse import urlsplit
from urllib.request import build_opener,HTTPSHandler,HTTPRedirectHandler,Request
from urllib.error import HTTPError,URLError
import webbrowser

CONFIG=Path(os.environ.get("LOCALAPPDATA",str(Path.home())))/"RollFlow-Workstation"/"server.json"


def approved_url(raw):
    if not isinstance(raw,str) or len(raw)>300 or not raw.isascii() or any(ord(c)<=32 or ord(c)==127 for c in raw):
        raise ValueError("Enter an exact HTTPS school hostname.")
    url=urlsplit(raw)
    host=url.hostname or ""
    labels=host.split(".")
    if (url.scheme!="https" or url.username is not None or url.password is not None or url.port not in (None,443)
        or url.path not in ("","/") or url.query or url.fragment or len(labels)<2 or len(host)>253
        or not re.fullmatch(r"[a-zA-Z]{2,63}",labels[-1])
        or any(not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?",x) for x in labels)):
        raise ValueError("Use https:// followed by the ICT-approved DNS hostname; no credentials, custom port, path or query.")
    return "https://"+host.lower()+"/"


def configure(path,raw):
    url=approved_url(raw)
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix="server-",suffix=".tmp")
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump({"server":url},f)
        os.replace(tmp,path)
    finally:
        Path(tmp).unlink(missing_ok=True)
    return url


def load(path):
    return approved_url(json.loads(path.read_text(encoding="utf-8"))["server"])


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None


def diagnose(url):
    opener=build_opener(HTTPSHandler(context=ssl.create_default_context()),NoRedirect())
    try:
        with opener.open(Request(url+"login/",headers={"User-Agent":"RollFlow-Workstation-Diagnostic"}),timeout=10) as r:
            return "HTTPS response: "+str(r.status)
    except HTTPError as e:
        return "HTTPS response: "+str(e.code)+". Redirects were not followed."
    except (URLError,OSError):
        return "HTTPS connection failed. Contact ICT; certificate checks have not been bypassed."


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("command",choices=["configure","open","diagnose"])
    args=p.parse_args()
    try:
        if args.command=="configure":
            raw=input("Enter your ICT-approved school server URL (https://...): ").strip()
            url=approved_url(raw)
            print("Selected server:",url)
            if input("Confirm ICT approved this exact server (type YES): ")!="YES":
                raise ValueError("Configuration not changed.")
            configure(CONFIG,url)
            print("Server saved. No passwords or school records stored by this launcher.")
            return
        url=load(CONFIG)
        if args.command=="diagnose":
            print(diagnose(url))
        else:
            if not webbrowser.open(url):
                raise ValueError("Could not open default browser.")
    except (OSError,ValueError,KeyError,TypeError) as exc:
        p.exit(1,"Workstation setup required or invalid. Check with ICT. "+("Configure the approved HTTPS server first.\n" if isinstance(exc,OSError) else "No connection opened.\n"))


if __name__=="__main__":main()
