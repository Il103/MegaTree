#!/usr/bin/env python3
import os, sys, argparse, subprocess, zipfile
from .utils import VERSION, slug, free_disk, download
from .analyze import DeviceInfo
from .extract import extract_all_images
from .dtb import scan_all_dtbs
from .trees.recovery import RecoveryTreeGenerator, RECOVERY_TYPES
from .release import create_release_zip

def banner():
    print(f"MegaTree v{VERSION} - Recovery Tree Generator")

def cmd_analyze(args):
    info = DeviceInfo(); info.from_dump(args.dump)
    if args.json:
        import json; print(json.dumps({k:v for k,v in info.__dict__.items() if not k.startswith('_')}, indent=2, default=str))
    else:
        print(info.summary())

def cmd_extract(args):
    ext = os.path.join(args.output or args.dump, "extracted")
    if not os.path.isdir(ext) or args.force:
        r = extract_all_images(args.dump, ext); ok = sum(1 for v in r.values() if v[0])
        print(f"Done: {ok} OK, {len(r)-ok} failed")
    else:
        print("Already extracted, use --force")

def cmd_dtb(args):
    dtb = os.path.join(args.output or args.dump, "dtb")
    dts = os.path.join(args.output or args.dump, "dts")
    print(f"Found {len(scan_all_dtbs(args.dump, dtb, dts))} DTBs")

def cmd_generate(args):
    info = DeviceInfo(); info.from_dump(args.dump)
    mfr = slug(info.manufacturer or "unknown"); dev = slug(info.codename or info.device or "unknown")
    base = os.path.join(args.output or args.dump, "megatree-output", f"{mfr}-{dev}")
    os.makedirs(base, exist_ok=True)
    RecoveryTreeGenerator(info, args.dump, args.recovery).generate(os.path.join(base, "recovery"))
    print(f"Output: {base} | {mfr}/{dev} | {info.platform}")

def cmd_all(args):
    dump = args.dump; banner()
    info = DeviceInfo(); info.from_dump(dump); print(info.summary())
    ext = os.path.join(dump, "extracted")
    if not os.path.isdir(ext) or args.force_extract:
        extract_all_images(dump, ext)
    scan_all_dtbs(dump, os.path.join(dump, "dtb"), os.path.join(dump, "dts"))
    mfr = slug(info.manufacturer or "unknown"); dev = slug(info.codename or info.device or "unknown")
    base = os.path.join(args.output or dump, "megatree-output", f"{mfr}-{dev}")
    os.makedirs(base, exist_ok=True)
    RecoveryTreeGenerator(info, dump, args.recovery).generate(os.path.join(base, "recovery"))
    if args.release:
        rp = args.release
        if os.path.isdir(rp): rp = os.path.join(rp, f"megatree-{mfr}-{dev}.zip")
        create_release_zip(base, info, rp)
    print(f"\nMegaTree complete! Recovery tree: {base}")

def cmd_download(args):
    out = args.output or os.path.join(os.getcwd(), "dump")
    os.makedirs(out, exist_ok=True)
    url = args.url.strip()
    if url.endswith(".zip") or "gofile" in url:
        zip_path = os.path.join(out, "dump.zip")
        download(url, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(out)
        os.remove(zip_path)
    elif any(x in url for x in ("github", "gitlab", "gitgud")):
        subprocess.run(["git", "clone", "--depth=1", url, out], check=True)
    else:
        download(url, out)
    print(f"Dump at: {out}")

def main():
    p = argparse.ArgumentParser(description=f"MegaTree v{VERSION} - Recovery Tree Generator")
    p.add_argument("--version", action="version", version=VERSION)
    sub = p.add_subparsers(dest="cmd")
    for c, h in [("analyze","Analyze dump device info"),
                  ("extract","Extract partition images"),
                  ("dtb","Scan DTBs from boot images"),
                  ("generate","Generate recovery tree"),
                  ("all","Full pipeline: analyze+extract+dtb+generate"),
                  ("download","Download dump from URL")]:
        s = sub.add_parser(c, help=h)
        if c == "download":
            s.add_argument("url"); s.add_argument("-o","--output")
        else:
            s.add_argument("dump")
            if c in ("extract","generate","all"): s.add_argument("-o","--output")
        if c in ("generate","all"):
            s.add_argument("-r","--recovery", choices=list(RECOVERY_TYPES.keys()), default="twrp")
        if c == "extract":
            s.add_argument("--force", action="store_true")
        if c == "all":
            s.add_argument("--force-extract", action="store_true")
            s.add_argument("--release", nargs="?", const="./releases")
        if c == "analyze":
            s.add_argument("--json", action="store_true")
    a = p.parse_args()
    if not a.cmd: p.print_help(); return
    globals()[f"cmd_{a.cmd}"](a)

if __name__ == "__main__":
    sys.exit(main())
