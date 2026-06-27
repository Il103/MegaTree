import os, sys, shutil, struct, subprocess, json, re, hashlib, urllib.request
from pathlib import Path
from datetime import datetime

VERSION = "1.0.0"

INFO = {}
INFO["version"] = VERSION
INFO["generated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

def run(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except FileNotFoundError:
        return -2, "", f"Command not found: {cmd[0]}"

def which(exe):
    return shutil.which(exe) is not None

def human_size(n):
    for unit in ("B","KB","MB","GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

def slug(s):
    return re.sub(r'[^a-zA-Z0-9._-]+', '-', s).strip('-').lower()

def fmt_now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

def free_disk(path="/"):
    try:
        st = os.statvfs(path)
        return (st.f_frsize * st.f_bavail) / (1024**3)
    except:
        return 0

def download(url, dest, timeout=300):
    """Download a URL to dest. Supports gofile.io, direct links, GitHub releases."""
    import urllib.request
    url = url.strip()
    # gofile.io
    if "gofile.io" in url or "gofile" in url:
        return _download_gofile(url, dest)
    # Regular URL
    print(f"Downloading {url} -> {dest}")
    urllib.request.urlretrieve(url, dest)
    return dest

def _download_gofile(url, dest):
    """Handle gofile.io links."""
    import json, urllib.request
    # Extract content ID
    cid = url.rstrip("/").split("/")[-1]
    api = f"https://api.gofile.io/servers"
    r = urllib.request.urlopen(api)
    data = json.loads(r.read())
    server = data["data"]["servers"][0]["name"]
    dl_url = f"https://{server}.gofile.io/download/{cid}"
    print(f"gofile: {dl_url} -> {dest}")
    urllib.request.urlretrieve(dl_url, dest)
    return dest

def list_partitions(dump_dir):
    """List available partition images in dump directory."""
    exts = (".img", ".img.raw", ".bin")
    parts = {}
    for f in os.listdir(dump_dir):
        fp = os.path.join(dump_dir, f)
        if not os.path.isfile(fp) or not f.endswith(exts):
            continue
        name = f.replace(".img.raw", ".img").replace(".img", "").replace(".bin", "")
        parts[name] = fp
    return parts
