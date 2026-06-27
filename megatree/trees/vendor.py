import os

class VendorTreeGenerator:
    def __init__(self, info, dump_dir):
        self.info = info
        self.dump_dir = dump_dir
        self.mfr = slug(info.manufacturer or "unknown")
        self.dev = slug(info.codename or info.device or "unknown")

    def generate(self, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        self._proprietary_files(output_dir)
        self._boardconfig_vendor(output_dir)
        self._vendor_mk(output_dir)
        self._kernel_modules(output_dir)
        return output_dir

    def _proprietary_files(self, out):
        blobs = set()
        vendor_dirs = [
            os.path.join(self.dump_dir, "extracted", "vendor"),
            os.path.join(self.dump_dir, "vendor"),
        ]
        for vd in vendor_dirs:
            if os.path.isdir(vd):
                for root, dirs, files in os.walk(vd):
                    for f in files:
                        rel = os.path.relpath(os.path.join(root, f), vd)
                        if not any(excl in rel for excl in [".git", "lost+found"]):
                            blobs.add(rel)

        with open(os.path.join(out, "proprietary-files.txt"), "w") as f:
            f.write(f"# proprietary-files.txt - Auto-generated for {self.dev}\n")
            f.write("# Board: {}\n".format(self.info.platform or "unknown"))
            f.write("# Build fingerprint: {}\n".format(self.info.fingerprint or "unknown"))
            f.write("\n")
            for blob in sorted(blobs):
                f.write(blob + "\n")
        print(f"  vendor: {len(blobs)} proprietary files listed")

    def _boardconfig_vendor(self, out):
        kmods = []
        for km_dir in ["vendor_dlkm/lib/modules", "vendor/lib/modules",
                       "extracted/vendor_dlkm/lib/modules",
                       "extracted/vendor/lib/modules"]:
            d = os.path.join(self.dump_dir, km_dir)
            if os.path.isdir(d):
                for root, dirs, files in os.walk(d):
                    for f in files:
                        if f.endswith(".ko"):
                            rel = os.path.relpath(os.path.join(root, f), d)
                            kmods.append(("$(VENDOR_PATH)/proprietary/lib/modules/" + rel, f))

        with open(os.path.join(out, "BoardConfigVendor.mk"), "w") as f:
            f.write(f"# BoardConfigVendor.mk - Auto-generated for {self.dev}\n")
            for fullpath, fname in sorted(kmods):
                f.write(f"KERNEL_MODULES += {fullpath}\n")
            if not kmods:
                f.write("# No kernel modules found\n")
        print(f"  vendor: {len(kmods)} kernel modules listed")

    def _vendor_mk(self, out):
        content = f"""# Vendor makefile - Auto-generated
# Device: {self.dev}  Manufacturer: {self.mfr}

$(call inherit-product, vendor/{self.mfr}/{self.dev}/proprietary-files.txt)

PRODUCT_PACKAGES += \\
    init.insmod.sh \\
    init.mf_nowb.sh

PRODUCT_COPY_FILES += \\
    $(LOCAL_PATH)/proprietary-files.txt:$(TARGET_OUT_VENDOR)/etc/proprietary-files.txt

-include $(LOCAL_PATH)/BoardConfigVendor.mk
"""
        with open(os.path.join(out, f"{self.dev}-vendor.mk"), "w") as f:
            f.write(content.strip() + "\n")

    def _kernel_modules(self, out):
        pass

from ..utils import slug
