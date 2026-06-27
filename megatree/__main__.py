#!/usr/bin/env python3
import os, sys, argparse, json
from .utils import VERSION, slug, fmt_now, human_size, free_disk
from .analyze import DeviceInfo
from .extract import extract_all_images
from .dtb import scan_all_dtbs
from .trees.device import DeviceTreeGenerator
from .trees.recovery import RecoveryTreeGenerator, RECOVERY_TYPES
from .trees.vendor import VendorTreeGenerator
from .validate import Validator
from .release import create_release_zip

def banner():
    print(f"MegaTree v{VERSION} - Ultimate Device Tree Generator")

def cmd_analyze(args):
    info = DeviceInfo(); info.from_dump(args.dump)
    if args.json:
        import json; print(json.dumps({k:v for k,v in info.__dict__.items() if not k.startswith('_')}, indent=2, default=str))
    else:
        print(info.summary())

def cmd_extract(args):
    dump = args.dump; ext = os.path.join(args.output or dump, "extracted")
    if not os.path.isdir(ext) or args.force:
        r = extract_all_images(dump, ext); ok = sum(1 for v in r.values() if v[0])
        print(f"Done: {ok} OK, {len(r)-ok} failed")
    else:
        print("Already extracted, use --force")

def cmd_dtb(args):
    dump = args.dump; dtb = os.path.join(args.output or dump, "trees","dtb"); dts = os.path.join(args.output or dump, "trees","dts")
    print(f"Found {len(scan_all_dtbs(dump, dtb, dts))} DTBs")

def cmd_generate(args):
    info = DeviceInfo(); info.from_dump(args.dump)
    mfr = slug(info.manufacturer or "unknown"); dev = slug(info.codename or info.device or "unknown")
    base = os.path.join(args.output or args.dump, "megatree-output", f"{mfr}-{dev}")
    os.makedirs(base, exist_ok=True)
    DeviceTreeGenerator(info, args.dump).generate(os.path.join(base, "device_tree"))
    RecoveryTreeGenerator(info, args.dump, args.recovery).generate(os.path.join(base, "recovery"))
    if not args.no_vendor: VendorTreeGenerator(info, args.dump).generate(os.path.join(base, "vendor"))
    print(f"Output: {base} | {mfr}/{dev} | {info.platform}")

def cmd_validate(args):
    info = DeviceInfo(); info.from_dump(args.dump)
    v = Validator(info, args.dump); v.run(); return 0 if v.summary() else 1

def cmd_all(args):
    dump = args.dump; banner()
    free = free_disk(dump)
    if free < 2 and not args.force: print("Low disk, use --force"); return
    info = DeviceInfo(); info.from_dump(dump); print(info.summary())
    ext = os.path.join(dump, "extracted")
    if not os.path.isdir(ext) or args.force_extract: extract_all_images(dump, ext)
    scan_all_dtbs(dump, os.path.join(dump,"trees","dtb"), os.path.join(dump,"trees","dts"))
    mfr = slug(info.manufacturer or "unknown"); dev = slug(info.codename or info.device or "unknown")
    base = os.path.join(args.output or dump, "megatree-output", f"{mfr}-{dev}")
    os.makedirs(base, exist_ok=True)
    DeviceTreeGenerator(info, dump).generate(os.path.join(base, "device_tree"))
    RecoveryTreeGenerator(info, dump, args.recovery).generate(os.path.join(base, "recovery"))
    VendorTreeGenerator(info, dump).generate(os.path.join(base, "vendor"))
    v = Validator(info, dump); v.run(); v.summary()
    if args.release:
        rp = args.release
        if os.path.isdir(rp): rp = os.path.join(rp, f"megatree-{mfr}-{dev}.zip")
        create_release_zip(base, info, rp)
    print(f"\nMegaTree complete! Output: {base}")

def main():
    p = argparse.ArgumentParser(description=f"MegaTree v{VERSION}")
    p.add_argument("--version", action="version", version=VERSION)
    sub = p.add_subparsers(dest="cmd")
    for c,h in [("analyze","Show device info"),("extract","Extract images"),("dtb","Scan DTBs"),
                ("generate","Generate trees"),("validate","Validate dump"),("all","Full pipeline"),("info","Device info JSON")]:
        s = sub.add_parser(c, help=h)
        s.add_argument("dump")
        if c in ("extract","dtb","generate","all"): s.add_argument("-o","--output")
        if c in ("generate","all"): s.add_argument("-r","--recovery",choices=list(RECOVERY_TYPES.keys()),default="twrp")
        if c=="generate": s.add_argument("--no-vendor",action="store_true")
        if c=="extract": s.add_argument("--force",action="store_true")
        if c=="all": s.add_argument("--force-extract",action="store_true"); s.add_argument("--force",action="store_true"); s.add_argument("--release",nargs="?",const="./releases")
        if c in ("analyze","info"): s.add_argument("--json",action="store_true")
    a = p.parse_args()
    if not a.cmd: p.print_help(); return
    globals()[f"cmd_{a.cmd}"](a)

if __name__ == "__main__":
    sys.exit(main())
