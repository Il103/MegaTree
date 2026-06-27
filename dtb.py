import os, struct, subprocess, glob, shutil
from .utils import run, which

DTB_MAGIC = b"\xd0\x0d\xfe\xed"

def find_dtbs_in_file(filepath, out_dir):
    results = []
    try:
        with open(filepath, "rb") as f:
            data = f.read()
    except:
        return results

    # Scan for DTB headers
    pos = 0
    count = 0
    while True:
        pos = data.find(DTB_MAGIC, pos)
        if pos == -1:
            break
        if pos + 12 <= len(data):
            total_size = struct.unpack(">I", data[pos+8:pos+12])[0]
            if 100 < total_size < 2000000:
                if pos + total_size <= len(data):
                    dtb_data = data[pos:pos+total_size]
                    base = os.path.basename(filepath).replace(".img", "")
                    dtb_path = os.path.join(out_dir, f"{base}_dtb_{count}.dtb")
                    with open(dtb_path, "wb") as f:
                        f.write(dtb_data)
                    results.append(dtb_path)
                    count += 1
        pos += 4

    # Also check aligned end of page
    for align in [0, 4, 8, 12]:
        check = len(data) - (len(data) % 4096) - align - 4
        if check > 0 and data[check:check+4] == DTB_MAGIC:
            total_size = struct.unpack(">I", data[check+8:check+12])[0]
            if 100 < total_size < 2000000 and check + total_size <= len(data):
                dtb_data = data[check:check+total_size]
                base = os.path.basename(filepath).replace(".img", "")
                dtb_path = os.path.join(out_dir, f"{base}_dtb_end_{count}.dtb")
                with open(dtb_path, "wb") as f:
                    f.write(dtb_data)
                results.append(dtb_path)
                count += 1

    return results

def decompile_dtb(dtb_path, dts_dir):
    base = os.path.basename(dtb_path).replace(".dtb", "")
    dts_path = os.path.join(dts_dir, f"{base}.dts")
    if which("dtc"):
        rc, out, err = run(["dtc", "-q", "-I", "dtb", "-O", "dts",
                          dtb_path, "-o", dts_path], timeout=30)
        if rc == 0 and os.path.getsize(dts_path) > 0:
            return dts_path
    return None

def scan_all_dtbs(dump_dir, dtb_out, dts_out):
    os.makedirs(dtb_out, exist_ok=True)
    os.makedirs(dts_out, exist_ok=True)

    all_dtbs = []

    # Scan boot images
    for pat in ["boot*.img", "vendor_boot*.img", "recovery*.img",
                "dtbo*.img", "init_boot*.img"]:
        for fpath in glob.glob(os.path.join(dump_dir, pat)):
            found = find_dtbs_in_file(fpath, dtb_out)
            all_dtbs.extend(found)

    # Copy existing .dtb files
    for root, dirs, files in os.walk(dump_dir):
        for f in files:
            if f.endswith(".dtb") and "dtb" not in root:
                src = os.path.join(root, f)
                dst = os.path.join(dtb_out, f)
                shutil.copy2(src, dst)
                all_dtbs.append(dst)

    # Decompile
    for dtb in all_dtbs:
        decompile_dtb(dtb, dts_out)

    return all_dtbs

def parse_dt_device_info(dts_dir):
    info = {}
    for fname in os.listdir(dts_dir):
        if not fname.endswith(".dts"):
            continue
        fpath = os.path.join(dts_dir, fname)
        try:
            with open(fpath, errors="ignore") as f:
                content = f.read()
            m = re.search(r'compatible\s*=\s*"([^"]+)"', content)
            if m:
                info["compatible"] = m.group(1)
            m = re.search(r'model\s*=\s*"([^"]+)"', content)
            if m:
                info["model"] = m.group(1)
        except:
            pass
    return info

import re
