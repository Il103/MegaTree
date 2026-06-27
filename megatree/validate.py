import os, re

class Validator:
    def __init__(self, info, dump_dir):
        self.info = info
        self.dump_dir = dump_dir
        self.errors = []
        self.warnings = []

    def run(self):
        self._check_device_info()
        self._check_fstabs()
        self._check_boot_files()
        self._check_props()
        self._check_trees()
        return len(self.errors), len(self.warnings)

    def _error(self, msg):
        self.errors.append(msg)
        print(f"  ERROR: {msg}")

    def _warn(self, msg):
        self.warnings.append(msg)
        print(f"  WARN: {msg}")

    def _check_device_info(self):
        if not self.info.device:
            self._error("Device codename not found in build.prop")
        if not self.info.manufacturer:
            self._warn("Manufacturer not found in build.prop")
        if not self.info.platform:
            self._warn("Platform not found in build.prop")
        if not self.info.fingerprint:
            self._warn("Build fingerprint not found")
        if self.info.device and not re.match(r'^[a-zA-Z0-9_-]+$', self.info.device):
            self._warn(f"Device codename may be invalid: {self.info.device}")

    def _check_fstabs(self):
        if not self.info.fstabs:
            self._warn("No fstab files found in dump")

        has_recovery_fstab = False
        for key, fpath in self.info.fstabs:
            if os.path.isfile(fpath):
                sz = os.path.getsize(fpath)
                if sz < 100:
                    self._warn(f"fstab too small: {fpath} ({sz} bytes)")
                with open(fpath, errors="ignore") as f:
                    content = f.read()
                if "/system" in content:
                    has_recovery_fstab = True
                if "/data" not in content:
                    self._warn(f"fstab missing /data mount: {key}")

        if not has_recovery_fstab:
            self._warn("No fstab with /system mount found")

    def _check_boot_files(self):
        boot_img = os.path.join(self.dump_dir, "boot.img")
        boot_dir = os.path.join(self.dump_dir, "boot")
        kernel = os.path.join(self.dump_dir, "kernel")
        kernel_boot = os.path.join(boot_dir, "kernel")

        if os.path.isfile(boot_img):
            sz = os.path.getsize(boot_img)
            if sz < 1024 * 1024:
                self._warn(f"boot.img suspiciously small: {sz} bytes")
        if os.path.isfile(kernel) or os.path.isfile(kernel_boot):
            pass
        else:
            self._error("No kernel found in dump")

        dtbo_img = os.path.join(self.dump_dir, "dtbo.img")
        if not os.path.isfile(dtbo_img):
            self._warn("No dtbo.img found")

    def _check_props(self):
        if self.info.build_type not in ("user", "userdebug", "eng"):
            self._warn(f"Unusual build type: {self.info.build_type}")
        if self.info.sdk:
            try:
                sdk = int(self.info.sdk)
                if sdk < 30:
                    self._warn(f"Old Android SDK: {sdk}")
            except ValueError:
                pass

    def _check_trees(self):
        trees_dir = os.path.join(self.dump_dir, "trees")
        if not os.path.isdir(trees_dir):
            self._warn("No trees directory found")
            return

        for tree in ["device_tree", "recovery_tree", "vendor_tree"]:
            tdir = os.path.join(trees_dir, tree)
            if not os.path.isdir(tdir):
                self._warn(f"Missing {tree}")
                continue

            files = os.listdir(tdir)
            if not files:
                self._warn(f"Empty {tree}")

            if tree == "device_tree":
                if "BoardConfig.mk" not in files:
                    self._error("device_tree missing BoardConfig.mk")
                if "device.mk" not in files:
                    self._error("device_tree missing device.mk")

        aosp_dt = os.path.join(self.dump_dir, "aosp-device-tree")
        if not os.path.isdir(aosp_dt):
            self._warn("No aosp-device-tree (aospdtgen not run)")

    def summary(self):
        print(f"\n{'='*50}")
        print(f"Validation: {len(self.errors)} errors, {len(self.warnings)} warnings")
        if self.errors:
            print(f"Errors:")
            for e in self.errors:
                print(f"  - {e}")
        if self.warnings:
            print(f"Warnings:")
            for w in self.warnings:
                print(f"  - {w}")
        print(f"{'='*50}")
        return len(self.errors) == 0
