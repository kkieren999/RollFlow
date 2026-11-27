"""Detect corruption in an offline bundle; not a substitute for Authenticode."""
import argparse
import hashlib
from pathlib import Path,PurePosixPath
import re


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()


def manifest(root,name="SHA256SUMS.txt"):
    root=Path(root)
    target=root/name
    if target.exists():
        raise ValueError("Manifest already exists.")
    lines=[]
    seen=set()
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            raise ValueError("Unexpected symbolic link.")
        if p.is_file():
            relative=p.relative_to(root).as_posix()
            if relative.casefold() in seen:raise ValueError("Case-colliding bundle path.")
            seen.add(relative.casefold())
            lines.append(digest(p)+"  "+relative)
    target.write_text("\n".join(lines)+"\n",encoding="utf-8")


def verify(root,name="SHA256SUMS.txt",strict=False):
    root=Path(root).resolve()
    target=root/name
    if not target.is_file() or target.is_symlink():
        raise ValueError("Manifest missing.")
    seen=set()
    for line in target.read_text(encoding="utf-8").splitlines():
        match=re.fullmatch(r"([a-f0-9]{64})  (.+)",line)
        if not match:raise ValueError("Invalid manifest entry.")
        expected,relative=match.groups()
        parts=PurePosixPath(relative)
        if (parts.is_absolute() or ".." in parts.parts or "\\" in relative or ":" in relative
                or relative!=parts.as_posix() or relative.casefold() in seen or relative==name):
            raise ValueError("Unsafe or duplicate manifest path.")
        seen.add(relative.casefold())
        p=root.joinpath(*parts.parts)
        if not p.is_file() or any(a.is_symlink() for a in [p,*p.parents] if a!=root and root in a.parents) or not p.resolve().is_relative_to(root):
            raise ValueError("Missing or unsafe manifested file: "+relative)
        if digest(p)!=expected:raise ValueError("Checksum mismatch: "+relative)
    if not seen:raise ValueError("Empty manifest.")
    if strict:
        actual=set()
        for p in root.rglob("*"):
            if p.is_symlink():raise ValueError("Unexpected symbolic link.")
            if p.is_file() and p!=target:
                relative=p.relative_to(root).as_posix().casefold()
                if relative in actual:raise ValueError("Case-colliding bundle path.")
                actual.add(relative)
            elif not p.is_dir() and p!=target:raise ValueError("Unexpected bundle entry.")
        if actual!=seen:raise ValueError("Unexpected or missing files.")
    return len(seen)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("root",type=Path)
    p.add_argument("--strict",action="store_true")
    args=p.parse_args()
    try:
        print("Verified manifested files:",verify(args.root,strict=args.strict))
        print("Checksums detect corruption; trust the distribution source and digital signature separately.")
    except (OSError,ValueError) as e:
        p.exit(1,"Verification failed: "+str(e)+"\n")

if __name__=="__main__":main()
