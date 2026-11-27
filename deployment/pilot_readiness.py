"""Print a blank fictional rehearsal checklist and optional local bundle evidence.

This is a read-only inspection tool, not an approval workflow or deployment command.
"""
import argparse
import json
import re
from pathlib import Path
from rollflow.pilot_plan import plan
from deployment.release_readiness import report


def inspect(bundle=None, expected_commit=None):
    result=plan()
    if expected_commit is not None:
        if not re.fullmatch(r"[a-f0-9]{40}",expected_commit) or bundle is None:
            raise ValueError("Expected commit requires a bundle and exact full Git SHA.")
    result["bundle"]=report(bundle)["bundle"] if bundle is not None else None
    if expected_commit is not None and result["bundle"]["source_commit"]!=expected_commit:
        raise ValueError("Bundle source commit differs from expected checkout.")
    result["bundle_matches_expected_commit"] = True if expected_commit is not None else None
    result["evidence_notice"]="Record actual rehearsal outcomes privately. No test or approval is inferred by this report."
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle",type=Path)
    parser.add_argument("--expected-commit")
    parser.add_argument("--json",action="store_true")
    args=parser.parse_args()
    try:data=inspect(args.bundle,args.expected_commit)
    except (ValueError,OSError,KeyError):parser.exit(1,"Pilot inspection failed; review bundle and expected commit.\n")
    if args.json:
        print(json.dumps(data,indent=2))
    else:
        print("RollFlow",data["version"],"— fictional staging rehearsal only")
        print("Production approval: BLOCKED")
        if data["bundle"]:
            print("Bundle commit:",data["bundle"]["source_commit"])
            print("Manifest verified:",data["bundle"]["verified_files"],"files; publisher authenticity not established")
        for item in data["scenarios"]:
            print(item["id"],item["title"],"—",item["status"])
        for gate in data["gates"]:
            print("OPEN:",gate["id"],gate["owner_role"],"—",gate["requirement"])
        print(data["evidence_notice"])
    return 0

if __name__=="__main__":raise SystemExit(main())
