import os, re, struct, glob
from .bootimg import parse_boot_image, detect_ramdisk_type

class DeviceInfo:
    def __init__(self):
        self.manufacturer = ""
        self.device = ""
        self.model = ""
        self.codename = ""
        self.platform = ""
        self.platform_mediatek = ""
        self.brand = ""
        self.fingerprint = ""
        self.android = ""
        self.sdk = ""
        self.kernel = ""
        self.incremental = ""
        self.density = ""
        self.security_patch = ""
        self.build_type = "user"
        self.arch = "arm64"
        self.abi_list = "arm64-v8a,armeabi-v7a,armeabi"
        self.is_ab = True
        self.super_size = 0
        self.boot_partition_size = 67108864
        self.dtbo_partition_size = 8388608
        self.dynamic_partition_group_size = 0
        self.fstabs = []
        self.all_props = {}
        self.boot_info = None
        self.ramdisk_type = "boot"
        self.gpu = ""
        self.kernel_base = "0x3fff8000"
        self.kernel_pagesize = 4096
        self.kernel_cmdline = ""
        self.boot_header_version = 4

    def from_build_prop(self, content, source=""):
        if content is None:
            return
        lines = content.split("\n")
        for line in lines:
            if "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip()
            if not k or not v:
                continue
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
                "ro.sf.lcd_density": "density",
            }
            if k in m:
                val = v.strip()
                setattr(self, m[k], val)

        if self.platform_mediatek and not self.platform:
            self.platform = self.platform_mediatek
        if not self.codename:
            self.codename = self.device or slug(self.model) if self.model else self.codename

    def from_dump(self, dump_dir):
        # Read build.prop files
        for pp in [
            "vendor/build.prop", "system/build.prop", "product/build.prop",
            "system/system/build.prop", "extracted/vendor/build.prop",
            "extracted/system/build.prop", "extracted/product/build.prop",
        ]:
            fp = os.path.join(dump_dir, pp)
            if os.path.isfile(fp):
                with open(fp, errors="ignore") as f:
                    self.from_build_prop(f.read(), pp)

        # Parse boot.img
        boot_img = None
        for bp in [os.path.join(dump_dir, "boot.img"),
                    os.path.join(dump_dir, "boot.img.raw")]:
            if os.path.isfile(bp):
                boot_img = bp
                break
        if boot_img:
            self.boot_info = parse_boot_image(boot_img)
            if self.boot_info:
                self._from_boot_info(self.boot_info)

        # Detect ramdisk type
        for rd in ["boot/ramdisk", "vendor_boot/ramdisk", "recovery/root"]:
            rd_path = os.path.join(dump_dir, rd)
            if os.path.isdir(rd_path):
                self.ramdisk_type = detect_ramdisk_type(rd_path)
                break

        # Parse super.img size
        super_img = os.path.join(dump_dir, "super.img")
        if os.path.isfile(super_img):
            sz = os.path.getsize(super_img)
            if sz > 1000000:
                self.super_size = sz

        # Detect platform from kernel
        if not self.platform:
            for kp in [
                os.path.join(dump_dir, "boot", "kernel"),
                os.path.join(dump_dir, "kernel"),
            ]:
                if os.path.isfile(kp):
                    self._detect_platform_from_kernel(kp)
                    break

        # Parse DT for GPU and more
        dts_dir = os.path.join(dump_dir, "trees", "dts")
        if os.path.isdir(dts_dir):
            self._parse_dts(dts_dir)

        # Read fstab files
        for fp in [
            "trees/recovery_tree/fstab.mt6789",
            "trees/recovery_tree/fstab.emmc",
            "vendor/etc/fstab.mt6789",
            "vendor/etc/fstab.emmc",
            "extracted/vendor/etc/fstab.mt6789",
            "extracted/vendor/etc/fstab.emmc",
        ]:
            fsp = os.path.join(dump_dir, fp)
            if os.path.isfile(fsp):
                self.fstabs.append((fp, fsp))

        # Auto fill from fstab
        if self.fstabs:
            with open(self.fstabs[0][1], errors="ignore") as f:
                content = f.read()
            self.is_ab = "slotselect" in content

        if not self.codename:
            self.codename = self.device or "unknown"
        if not self.manufacturer:
            self.manufacturer = "unknown"
        if not self.platform:
            self.platform = self._guess_platform()

    def _from_boot_info(self, bi):
        if "kernel_addr" in bi:
            addr = bi.get("kernel_addr", 0x3fff8000)
            if addr:
                self.kernel_base = hex(addr)
        if "page_size" in bi:
            self.kernel_pagesize = bi["page_size"]
        if "cmdline" in bi and bi["cmdline"]:
            self.kernel_cmdline = bi["cmdline"]
        if "header_version" in bi:
            self.boot_header_version = bi["header_version"]

    def _detect_platform_from_kernel(self, kpath):
        try:
            with open(kpath, "rb") as f:
                data = f.read(100000)
            text = data.decode(errors="ignore")
            # MTK platforms
            mtk = re.search(r'(mt[0-9]{4,6})', text, re.I)
            if mtk:
                self.platform = mtk.group(1).lower()
                return
            # QCOM platforms
            qcom = re.search(r'(sm[0-9]{4,5}|msm[0-9]{4}|sdm[0-9]{3,4}|kona|lito|lahaina)', text, re.I)
            if qcom:
                self.platform = qcom.group(1).lower()
                return
            # Exynos
            exynos = re.search(r'(exynos[0-9]{4})', text, re.I)
            if exynos:
                self.platform = exynos.group(1).lower()
        except:
            pass

    def _parse_dts(self, dts_dir):
        for fname in os.listdir(dts_dir):
            if not fname.endswith(".dts"):
                continue
            fpath = os.path.join(dts_dir, fname)
            try:
                with open(fpath, errors="ignore") as f:
                    content = f.read()
                m = re.search(r'gpu\s*=\s*"([^"]+)"', content)
                if m:
                    self.gpu = m.group(1)
                m = re.search(r'platform\s*=\s*"([^"]+)"', content)
                if m and not self.platform:
                    self.platform = m.group(1)
            except:
                pass

    def _guess_platform(self):
        if self.boot_info:
            cmdline = self.boot_info.get("cmdline", "")
            m = re.search(r'(mt[0-9]{4,6})', cmdline, re.I)
            if m:
                return m.group(1).lower()
        return "unknown"

    def summary(self):
        return "\n".join([
            f"Manufacturer: {self.manufacturer}",
            f"Device: {self.device}",
            f"Codename: {self.codename}",
            f"Model: {self.model}",
            f"Platform: {self.platform}",
            f"Android: {self.android} (SDK {self.sdk})",
            f"Arch: {self.arch} | GPU: {self.gpu}",
            f"A/B: {self.is_ab}",
            f"Ramdisk: {self.ramdisk_type}",
            f"Boot header v{self.boot_header_version}",
            f"Cmdline: {self.kernel_cmdline[:80]}...",
            f"Fingerprint: {self.fingerprint}",
        ])

def slug(s):
    return re.sub(r'[^a-zA-Z0-9._-]+', '-', str(s)).strip('-').lower()
