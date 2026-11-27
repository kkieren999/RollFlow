"""Offline release readiness inventory; does not approve or deploy a school."""
import argparse,json,re
from pathlib import Path
from rollflow.release_policy import VERSION,CHANNEL,OPEN_GATES


def report(bundle=None):
    result={"version":VERSION,"channel":CHANNEL,"production_approved":False,"school_startup":"blocked",
            "open_gates":[{"id":k,"requirement":v,"status":"open"} for k,v in OPEN_GATES],
            "bundle":None}
    if bundle:
        from deployment.bundle_integrity import verify
        bundle=bundle.resolve()
        info=json.loads((bundle/"BUILD-INFO.json").read_text(encoding="utf-8"))
        if info.get("version")!=VERSION or not re.fullmatch("[a-f0-9]{40}",info.get("source_commit","")):
            raise ValueError("Bundle version or source commit is not this release candidate.")
        result["bundle"]={"source_commit":info["source_commit"],"verified_files":verify(bundle),
                          "publisher_authenticity":"not established by checksums"}
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle",type=Path)
    p.add_argument("--json",action="store_true")
    p.add_argument("--require-production",action="store_true",help="Return nonzero for open release gates.")
    args=p.parse_args()
    try:data=report(args.bundle)
    except (ValueError,OSError,KeyError) as exc:p.exit(1,"Release inspection failed.\n")
    if args.json:print(json.dumps(data,indent=2))
    else:
        print("RollFlow",data["version"],"—",data["channel"])
        print("Production approval: BLOCKED")
        for gate in data["open_gates"]:print("OPEN:",gate["requirement"])
        if data["bundle"]:print("Manifest verified:",data["bundle"]["verified_files"],"files; publisher signature not established.")
    return 2 if args.require_production else 0

if __name__=="__main__":raise SystemExit(main())
