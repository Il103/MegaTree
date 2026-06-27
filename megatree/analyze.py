import os, re
from .utils import run

class DeviceInfo:
    def __init__(self):
        self.manufacturer = ""
        self.device = ""
        model = ""
        self.codename = ""
        self.platform = ""
        self.brand = ""
        self.fingerprint = ""
        self.android = ""
        self.sdk = ""
        self.kernel = ""
        self.incremental = ""
        self.description = ""
        self.display = ""
        self.arch = "arm64"
        self.abi_list = "arm64-v8a,armeabi-v7a,armeabi"
        self.density = ""
        self.board = ""
        self.hardware = ""
        self.bootloader = ""
        self.security_patch = ""
        self.build_type = "user"
        self.build_tags = "release-keys"
        self.is_ab = True
        self.is_treble = True
        self.dynamic_partitions = True
        self.super_size = 0
        self.fstabs = []
        self.all_props = {}

    def from_build_prop(self, content, source=""):
        lines = content.split("\n")
        for line in lines:
            if "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip()
            self.all_props[k] = v

            m = {
                "ro.product.manufacturer": "manufacturer",
                "ro.product.device": "device",
                "ro.product.model": "model",
                "ro.product.name": "codename",
                "ro.product.board": "board",
                "ro.board.platform": "platform",
                "ro.mediatek.platform": "platform_mediatek",
                "ro.build.fingerprint": "fingerprint",
                "ro.build.version.release": "android",
                "ro.build.version.sdk": "sdk",
                "ro.build.description": "description",
                "ro.build.display.id": "display",
                "ro.build.product": "build_product",
                "ro.product.brand": "brand",
                "ro.hardware": "hardware",
                "ro.bootloader": "bootloader",
                "ro.build.version.security_patch": "security_patch",
                "ro.build.type": "build_type",
                "ro.build.tags": "build_tags",
                "ro.sf.lcd_density": "density",
            }
            if k in m:
                setattr(self, m[k], v)

        if self.platform_mediatek:
            self.platform = self.platform_mediatek

        if not self.codename or self.codename == self.device:
            self.codename = self.device or slug(self.model) if self.model else self.codename

    def from_dump(self, dump_dir):
        prop_paths = [
            "vendor/build.prop",
            "system/build.prop",
            "product/build.prop",
            "system/system/build.prop",
            "extracted/vendor/build.prop",
            "extracted/system/build.prop",
            "extracted/product/build.prop",
        ]
        for pp in prop_paths:
            fp = os.path.join(dump_dir, pp)
            if os.path.isfile(fp):
                with open(fp, errors="ignore") as f:
                    self.from_build_prop(f.read(), pp)

        fstab_paths = [
            "trees/recovery_tree/fstab.mt6789",
            "vendor/etc/fstab.mt6789",
            "vendor/etc/fstab.emmc",
            "recovery/root/fstab.mt6789",
            "extracted/vendor/etc/fstab.mt6789",
        ]
        for fp in fstab_paths:
            fsp = os.path.join(dump_dir, fp)
            if os.path.isfile(fsp):
                self.fstabs.append((fp, fsp))

        if not self.arch:
            if os.path.isdir(os.path.join(dump_dir, "system/lib64")):
                self.arch = "arm64"
            elif os.path.isdir(os.path.join(dump_dir, "system/lib")):
                self.arch = "arm"

        # Parse partition sizes from super
        super_img = os.path.join(dump_dir, "super.img")
        if os.path.isfile(super_img):
            try:
                sz = os.path.getsize(super_img)
                self.super_size = sz
            except:
                pass

    def summary(self):
        lines = [
            f"Manufacturer: {self.manufacturer or 'unknown'}",
            f"Device: {self.device or 'unknown'}",
            f"Codename: {self.codename or 'unknown'}",
            f"Model: {self.model or 'unknown'}",
            f"Platform: {self.platform or 'unknown'}",
            f"Android: {self.android or 'unknown'}",
            f"SDK: {self.sdk or 'unknown'}",
            f"Kernel: {self.kernel or 'unknown'}",
            f"Arch: {self.arch}",
            f"A/B: {self.is_ab}",
            f"Dynamic: {self.dynamic_partitions}",
            f"Display: {self.display or 'unknown'}",
            f"Fingerprint: {self.fingerprint or 'unknown'}",
        ]
        return "\n".join(lines)

def slug(s):
    return re.sub(r'[^a-zA-Z0-9._-]+', '-', s).strip('-').lower()
