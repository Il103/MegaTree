import os, zipfile, tarfile
from datetime import datetime

def create_release_zip(trees_dir, info, output_path, compress=True):
    mfr = slug(info.manufacturer or "unknown")
    dev = slug(info.device or info.codename or "unknown")
    date = datetime.utcnow().strftime("%Y%m%d")
    default_name = f"megatree-{mfr}-{dev}-{date}.zip"

    if os.path.isdir(output_path):
        output_path = os.path.join(output_path, default_name)

    if output_path.endswith(".tar.gz") or output_path.endswith(".tgz"):
        return _create_tar(trees_dir, info, output_path)

    return _create_zip(trees_dir, info, output_path)

def _create_zip(trees_dir, info, output_path):
    mfr = slug(info.manufacturer or "unknown")
    dev = slug(info.device or info.codename or "unknown")
    prefix = f"megatree-{mfr}-{dev}/"

    total = 0
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(trees_dir):
            for f in files:
                fpath = os.path.join(root, f)
                arcname = prefix + os.path.relpath(fpath, trees_dir)
                zf.write(fpath, arcname)
                total += 1

    sz = os.path.getsize(output_path)
    from .utils import human_size
    print(f"  Release: {output_path} ({human_size(sz)}, {total} files)")
    return output_path

def _create_tar(trees_dir, info, output_path):
    mfr = slug(info.manufacturer or "unknown")
    dev = slug(info.device or info.codename or "unknown")
    prefix = f"megatree-{mfr}-{dev}/"

    total = 0
    with tarfile.open(output_path, "w:gz") as tf:
        for root, dirs, files in os.walk(trees_dir):
            for f in files:
                fpath = os.path.join(root, f)
                arcname = prefix + os.path.relpath(fpath, trees_dir)
                tf.add(fpath, arcname)
                total += 1

    sz = os.path.getsize(output_path)
    from .utils import human_size
    print(f"  Release: {output_path} ({human_size(sz)}, {total} files)")
    return output_path

from .utils import slug
