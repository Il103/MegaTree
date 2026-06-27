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
