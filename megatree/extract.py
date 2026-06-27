import os, subprocess, shutil, glob
from .utils import run, which, human_size

EXTRACTORS = [
    ("erofs", ["fsck.erofs", "--extract"]),
    ("erofs_alt", ["extract.erofs", "-i"]),
    ("ext4_debugfs", ["debugfs", "-R"]),
    ("simg2img_debugfs", ["simg2img"]),
    ("raw_copy", []),
]

def extract_image(img_path, out_dir, timeout=180):
    if not os.path.isfile(img_path):
        return False, "not_found"
    name = os.path.basename(img_path).replace(".img", "")
    target = os.path.join(out_dir, name)
    os.makedirs(target, exist_ok=True)

    sz = os.path.getsize(img_path)
    if sz == 0:
        return False, "empty"
    if sz > 4 * 1024**3:
        return False, f"too_large:{human_size(sz)}"

    methods = []

    if which("fsck.erofs"):
        methods.append(("fsck.erofs", lambda: run(
            ["fsck.erofs", "--extract", target, img_path], timeout)))
    if which("extract.erofs"):
        methods.append(("extract.erofs", lambda: run(
            ["extract.erofs", "-i", img_path, "-o", target], timeout)))

    if which("debugfs"):
        methods.append(("debugfs", lambda: run(
            ["debugfs", "-R", f"rdump / {target}", img_path], timeout)))

    if which("simg2img") and which("debugfs"):
        def simg_method():
            raw = img_path + ".raw"
            r = run(["simg2img", img_path, raw], timeout)
            if r[0] != 0 or not os.path.isfile(raw):
                if os.path.isfile(raw):
                    os.unlink(raw)
                return (1, "", "simg2img failed")
            r2 = run(["debugfs", "-R", f"rdump / {target}", raw], timeout)
            if os.path.isfile(raw):
                os.unlink(raw)
            return r2
        methods.append(("simg2img+debugfs", simg_method))

    for mname, mfunc in methods:
        rc, out, err = mfunc()
        if rc == 0 and os.path.isdir(target) and os.listdir(target):
            return True, mname

    return False, "no_method"

def extract_all_images(dump_dir, extracted_dir, force=False):
    if not os.path.isdir(extracted_dir):
        os.makedirs(extracted_dir, exist_ok=True)

    results = {}
    imgs = glob.glob(os.path.join(dump_dir, "*.img"))
    imgs += glob.glob(os.path.join(dump_dir, "*.img.raw"))

    for img in sorted(set(imgs)):
        name = os.path.basename(img).replace(".img.raw", ".img").replace(".img", "")
        if name in ("super",):
            continue
        ok, method = extract_image(img, extracted_dir)
        results[name] = (ok, method)
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {name}: {method}")

    return results

def free_disk(path="/", target_gb=10):
    st = os.statvfs(path)
    free_gb = (st.f_frsize * st.f_bavail) / (1024**3)
    return free_gb
