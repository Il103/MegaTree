import os, re

class Validator:
    def __init__(self, info, dump_dir):
        self.info = info
        self.dump_dir = dump_dir
        self.errors = []
        self.warnings = []

    def run(self):
        self._check_device_info()
        self._check_boot_files()
        self._check_recovery_tree()
        return len(self.errors), len(self.warnings)

    def _error(self, msg):
        self.errors.append(msg)
        print(f"  ERROR: {msg}")

    def _warn(self, msg):
        self.warnings.append(msg)
        print(f"  WARN: {msg}")

    def _check_device_info(self):
        if not self.info.device:
            self._error("Device codename not found")
        if not self.info.manufacturer:
            self._warn("Manufacturer not found")
        if not self.info.platform:
            self._warn("Platform not found")

    def _check_boot_files(self):
        boot_img = os.path.join(self.dump_dir, "boot.img")
        boot_dir = os.path.join(self.dump_dir, "boot")
        kernel = os.path.join(self.dump_dir, "kernel")
        kernel_boot = os.path.join(boot_dir, "kernel")
        if not (os.path.isfile(kernel) or os.path.isfile(kernel_boot) or os.path.isfile(boot_img)):
            self._error("No kernel or boot.img found")

    def _check_recovery_tree(self):
        rt = os.path.join(self.dump_dir, "trees", "recovery_tree")
        if not os.path.isdir(rt):
            self._warn("No recovery tree generated")
            return
        files = os.listdir(rt)
        needed = ["BoardConfig.mk", "recovery.fstab"]
        for n in needed:
            if n not in files:
                self._error(f"Missing {n}")
        prebuilt = os.path.join(rt, "prebuilt")
        if os.path.isdir(prebuilt):
            pk = os.path.join(prebuilt, "kernel")
            if not os.path.isfile(pk):
                self._warn("No prebuilt kernel")

    def summary(self):
        print(f"\n{'='*50}")
        print(f"Validation: {len(self.errors)} errors, {len(self.warnings)} warnings")
        if self.errors:
            for e in self.errors: print(f"  ERROR: {e}")
        if self.warnings:
            for w in self.warnings: print(f"  WARN: {w}")
        print(f"{'='*50}")
        return len(self.errors) == 0
