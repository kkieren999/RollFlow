"""Offline RC4 evidence inventory for CI-produced staging packages, never approval."""
import argparse
import json
import re
from pathlib import Path
from deployment.bundle_integrity import digest, verify
from rollflow.release_policy import VERSION, CHANNEL, OPEN_GATES


def require(condition, message):
    if not condition:
        raise ValueError(message)


def qualify(installer_dir, local_lab, workstation, expected_commit):
    require(bool(re.fullmatch(r"[a-f0-9]{40}",expected_commit or "")),"Exact checkout SHA required.")
    result={"version":VERSION,"channel":CHANNEL,"source_commit":expected_commit,
            "production_approved":False,"school_startup":"blocked",
            "open_gates":[key for key,_ in OPEN_GATES],
            "scope":"package identity and integrity only; independent pilot and release approvals outstanding",
            "packages":[]}
    for kind,root in (("LocalLab",local_lab),("Workstation",workstation)):
        root=Path(root)
        count=verify(root,strict=True)
        info=json.loads((root/"BUILD-INFO.json").read_text(encoding="utf-8"))
        require(info.get("version")==VERSION and info.get("source_commit")==expected_commit,
                "Bundle version or checkout mismatch.")
        require(info.get("channel")==CHANNEL,"Unexpected release channel.")
        if kind=="LocalLab":
            require((root/"app"/"manage.py").is_file() and (root/"postgres"/"bin"/"postgres.exe").is_file(),
                    "Local Lab server payload missing.")
            require((root/"Pilot Readiness.cmd").is_file(),"Pilot inspection launcher missing.")
            docs=root/"app"/"docs"
        else:
            require(not any((root/p).exists() for p in ("app","postgres","wheelhouse")),
                    "Unexpected local server in Workstation.")
            require((root/"workstation.py").is_file(),"Workstation launcher missing.")
            docs=root/"pilot-docs"
        for name in ("v5.0-rc4-release-qualification.md","v5.0-rc4-ict-handover.md",
                     "v5.0-rc3-pilot-readiness.md","v5.0-rc3-acceptance-record.md"):
            require((docs/name).is_file(),"Missing handover document.")
        name=f"RollFlow-V{VERSION}-{kind}-x64-STAGING-Setup.exe"
        installer=Path(installer_dir)/name
        sidecar=installer.with_name(name+".sha256")
        require(installer.is_file() and not installer.is_symlink() and installer.stat().st_size>0,
                "Installer missing or empty.")
        expected=sidecar.read_text(encoding="utf-8-sig").strip()
        require(bool(re.fullmatch(r"[a-f0-9]{64}  "+re.escape(name),expected)),
                "Invalid installer checksum sidecar.")
        actual=digest(installer)
        require(expected==actual+"  "+name,"Installer checksum mismatch.")
        result["packages"].append({"kind":kind,"filename":name,"sha256":actual,
            "bytes":installer.stat().st_size,"manifested_files":count,
            "publisher_authenticity":"not established; signing approval outstanding"})
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--installers",required=True,type=Path)
    p.add_argument("--local-lab",required=True,type=Path)
    p.add_argument("--workstation",required=True,type=Path)
    p.add_argument("--expected-commit",required=True)
    args=p.parse_args()
    try:data=qualify(args.installers,args.local_lab,args.workstation,args.expected_commit)
    except (OSError,ValueError,KeyError):p.exit(1,"Release qualification failed: review exact packages and hashes.\n")
    print(json.dumps(data,indent=2))
    return 0

if __name__=="__main__":raise SystemExit(main())
