import os

class DeviceTreeGenerator:
    def __init__(self, info, dump_dir):
        self.info = info
        self.dump_dir = dump_dir
        self.device_path = f"device/{slug(info.manufacturer or 'unknown')}/{slug(info.device or info.codename or 'unknown')}"
        self.codename = slug(info.codename or info.device or "unknown")
        self.mfr = slug(info.manufacturer or "unknown")
        self.dts_dir = os.path.join(dump_dir, "trees", "dts")

    def generate(self, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        self._boardconfig(output_dir)
        self._device_mk(output_dir)
        self._products(output_dir)
        self._system_prop(output_dir)
        self._vendor_prop(output_dir)
        self._product_prop(output_dir)
        self._system_ext_prop(output_dir)
        self._odm_prop(output_dir)
        self._manifest(output_dir)
        self._extract_files(output_dir)
        self._setup_makefiles(output_dir)
        self._rootdir(output_dir)
        return output_dir

    def _boardconfig(self, out):
        mfr = self.mfr
        dev = self.codename
        plat = self.info.platform or "mt6789"
        arch = self.info.arch or "arm64"
        ab = "true" if self.info.is_ab else "false"
        super_sz = self.info.super_size or 9126805504
        dyn_sz = super_sz - 4194304 if super_sz > 4194304 else super_sz
        density = self.info.density or "420"

        content = f"""DEVICE_PATH := device/{mfr}/{dev}

# A/B
AB_OTA_UPDATER := {ab}
AB_OTA_PARTITIONS += \\
    boot \\
    vendor \\
    system \\
    product \\
    system_ext \\
    odm_dlkm \\
    vendor_dlkm

# Architecture
TARGET_ARCH := {arch}
TARGET_ARCH_VARIANT := armv8-a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_VARIANT := generic
TARGET_CPU_VARIANT_RUNTIME := cortex-a55

TARGET_2ND_ARCH := arm
TARGET_2ND_ARCH_VARIANT := armv7-a-neon
TARGET_2ND_CPU_ABI := armeabi-v7a
TARGET_2ND_CPU_ABI2 := armeabi
TARGET_2ND_CPU_VARIANT := generic
TARGET_2ND_CPU_VARIANT_RUNTIME := cortex-a55

# Bootloader
TARGET_BOOTLOADER_BOARD_NAME := {dev}
TARGET_NO_BOOTLOADER := true

# Display
TARGET_SCREEN_DENSITY := {density}

# Kernel
BOARD_BOOT_HEADER_VERSION := 4
BOARD_KERNEL_BASE := 0x3fff8000
BOARD_KERNEL_CMDLINE := bootopt=64S3,32N2,64N2
BOARD_KERNEL_PAGESIZE := 4096
BOARD_MKBOOTIMG_ARGS += --header_version $(BOARD_BOOT_HEADER_VERSION)
BOARD_KERNEL_IMAGE_NAME := Image
BOARD_INCLUDE_DTB_IN_BOOTIMG := true
BOARD_KERNEL_SEPARATED_DTBO := true
TARGET_KERNEL_SOURCE := kernel/{mfr}/{dev}

# Partitions
BOARD_FLASH_BLOCK_SIZE := 262144
BOARD_BOOTIMAGE_PARTITION_SIZE := 67108864
BOARD_DTBOIMG_PARTITION_SIZE := 8388608
BOARD_VENDOR_BOOTIMAGE_PARTITION_SIZE := 67108864
BOARD_SUPER_PARTITION_SIZE := {super_sz}
BOARD_SUPER_PARTITION_GROUPS := {mfr}_dynamic_partitions
BOARD_{mfr.upper()}_DYNAMIC_PARTITIONS_PARTITION_LIST := \\
    vendor \\
    system \\
    product \\
    system_ext \\
    vendor_dlkm \\
    odm_dlkm
BOARD_{mfr.upper()}_DYNAMIC_PARTITIONS_SIZE := {dyn_sz}

# Platform
TARGET_BOARD_PLATFORM := {plat}

# Properties
TARGET_SYSTEM_PROP += $(DEVICE_PATH)/system.prop
TARGET_VENDOR_PROP += $(DEVICE_PATH)/vendor.prop
TARGET_PRODUCT_PROP += $(DEVICE_PATH)/product.prop
TARGET_SYSTEM_EXT_PROP += $(DEVICE_PATH)/system_ext.prop
TARGET_ODM_PROP += $(DEVICE_PATH)/odm.prop
TARGET_VENDOR_DLKM_PROP += $(DEVICE_PATH)/vendor_dlkm.prop

# Recovery
TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/rootdir/etc/fstab.{plat}
TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := true

# Verified Boot
BOARD_AVB_ENABLE := true
BOARD_AVB_MAKE_VBMETA_IMAGE_ARGS += --flags 3
BOARD_AVB_VENDOR_BOOT_KEY_PATH := external/avb/test/data/testkey_rsa4096.pem
BOARD_AVB_VENDOR_BOOT_ALGORITHM := SHA256_RSA4096
BOARD_AVB_VENDOR_BOOT_ROLLBACK_INDEX := 1
BOARD_AVB_VENDOR_BOOT_ROLLBACK_INDEX_LOCATION := 1

# VINTF
DEVICE_MANIFEST_FILE += $(DEVICE_PATH)/manifest.xml

# Inherit vendor
-include vendor/{mfr}/{dev}/BoardConfigVendor.mk
"""
        if self.info.security_patch:
            content += f"\nVENDOR_SECURITY_PATCH := {self.info.security_patch}\n"

        with open(os.path.join(out, "BoardConfig.mk"), "w") as f:
            f.write(content.strip() + "\n")

    def _device_mk(self, out):
        mfr = self.mfr
        dev = self.codename
        fingerprint = self.info.fingerprint or ""
        content = f"""$(call inherit-product, $(SRC_TARGET_DIR)/product/updatable_apex.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota.mk)

PRODUCT_PACKAGES += \\
    android.hardware.boot@1.2-impl \\
    android.hardware.boot@1.2-impl.recovery \\
    android.hardware.boot@1.2-service

PRODUCT_PACKAGES += \\
    update_engine \\
    update_engine_sideload \\
    update_verifier

AB_OTA_POSTINSTALL_CONFIG += \\
    RUN_POSTINSTALL_system=true \\
    POSTINSTALL_PATH_system=system/bin/otapreopt_script \\
    FILESYSTEM_TYPE_system=erofs \\
    POSTINSTALL_OPTIONAL_system=true

AB_OTA_POSTINSTALL_CONFIG += \\
    RUN_POSTINSTALL_vendor=true \\
    POSTINSTALL_PATH_vendor=bin/checkpoint_gc \\
    FILESYSTEM_TYPE_vendor=erofs \\
    POSTINSTALL_OPTIONAL_vendor=true

PRODUCT_PACKAGES += \\
    checkpoint_gc \\
    otapreopt_script

PRODUCT_SHIPPING_API_LEVEL := {self.info.sdk or "35"}

PRODUCT_PACKAGES += \\
    android.hardware.fastboot@1.1-impl-mock \\
    fastbootd

PRODUCT_PACKAGES += \\
    android.hardware.health@2.1-impl \\
    android.hardware.health@2.1-service

PRODUCT_ENFORCE_RRO_TARGETS := *
PRODUCT_USE_DYNAMIC_PARTITIONS := true
PRODUCT_CHARACTERISTICS := default

PRODUCT_DEVICE := {dev}
PRODUCT_NAME := {dev}
PRODUCT_BRAND := {self.info.brand or mfr}
PRODUCT_MODEL := {self.info.model or dev}
PRODUCT_MANUFACTURER := {mfr}
PRODUCT_BOARD := {self.info.platform or "unknown"}
PRODUCT_FINGERPRINT := "{fingerprint}"

$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/emulated_storage.mk)
$(call inherit-product, vendor/{mfr}/{dev}/{dev}-vendor.mk)
"""
        with open(os.path.join(out, "device.mk"), "w") as f:
            f.write(content.strip() + "\n")

    def _products(self, out):
        with open(os.path.join(out, "AndroidProducts.mk"), "w") as f:
            f.write(f"PRODUCT_MAKEFILES := $(LOCAL_DIR)/device.mk\n")

    def _prop_file(self, out, name, source_props):
        props = {}
        for key in source_props:
            if key in self.info.all_props:
                props[key] = self.info.all_props[key]
        with open(os.path.join(out, name), "w") as f:
            for k, v in props.items():
                f.write(f"{k}={v}\n")
            if not props:
                f.write(f"# {name} - auto generated\n")

    def _system_prop(self, out):
        self._prop_file(out, "system.prop", [
            "ro.build.fingerprint", "ro.build.version.sdk",
            "ro.product.first_api_level",
        ])

    def _vendor_prop(self, out):
        self._prop_file(out, "vendor.prop", [
            "ro.vendor.build.fingerprint", "vendor.build.fingerprint",
        ])

    def _product_prop(self, out):
        self._prop_file(out, "product.prop", [
            "ro.product.build.fingerprint",
        ])

    def _system_ext_prop(self, out):
        self._prop_file(out, "system_ext.prop", [])

    def _odm_prop(self, out):
        self._prop_file(out, "odm.prop", [])

    def _manifest(self, out):
        path = os.path.join(self.dump_dir, "aosp-device-tree", "manifest.xml")
        if os.path.isfile(path):
            import shutil
            shutil.copy2(path, os.path.join(out, "manifest.xml"))
        else:
            with open(os.path.join(out, "manifest.xml"), "w") as f:
                f.write('<?xml version="1.0" encoding="utf-8"?>\n')
                f.write('<manifest version="1.0" type="device">\n')
                f.write(f'  <hal format="hidl">\n')
                f.write(f'    <name>android.hardware.boot</name>\n')
                f.write(f'    <transport>hwbinder</transport>\n')
                f.write(f'    <version>1.2</version>\n')
                f.write(f'    <interface>\n')
                f.write(f'      <name>IBootControl</name>\n')
                f.write(f'      <instance>default</instance>\n')
                f.write(f'    </interface>\n')
                f.write(f'  </hal>\n')
                f.write('</manifest>\n')

    def _extract_files(self, out):
        content = """#!/usr/bin/env python3
import os, sys, subprocess, shutil

VENDOR_MK = "vendor/{mfr}/{dev}/proprietary-files.txt"
DEVICE_DIR = "device/{mfr}/{dev}"

def main():
    if not os.path.isfile(VENDOR_MK):
        print("Error: vendor tree not set up")
        sys.exit(1)
    extract_path = shutil.which("extract-files.sh")
    if extract_path:
        subprocess.run([extract_path], cwd=DEVICE_DIR)
    else:
        print("extract-files.sh not found")

if __name__ == "__main__":
    main()
""".format(mfr=self.mfr, dev=self.codename)
        with open(os.path.join(out, "extract-files.py"), "w") as f:
            f.write(content)

    def _setup_makefiles(self, out):
        content = """#!/usr/bin/env python3
import os, sys

DEVICE_DIR = "device/{mfr}/{dev}"
VENDOR_DIR = "vendor/{mfr}/{dev}"

def main():
    if not os.path.isdir(VENDOR_DIR):
        print(f"Error: {{VENDOR_DIR}} not found")
        sys.exit(1)
    print("Setup makefiles for", DEVICE_DIR)

if __name__ == "__main__":
    main()
""".format(mfr=self.mfr, dev=self.codename)
        with open(os.path.join(out, "setup-makefiles.py"), "w") as f:
            f.write(content)

    def _rootdir(self, out):
        rootdir = os.path.join(out, "rootdir", "etc")
        os.makedirs(rootdir, exist_ok=True)

        # Copy fstab from dump
        copied = False
        for fstab_path_key, fstab_full in self.info.fstabs:
            if os.path.isfile(fstab_full):
                fname = f"fstab.{self.info.platform or 'mt6789'}"
                shutil.copy2(fstab_full, os.path.join(rootdir, fname))
                copied = True
                break

        if not copied:
            with open(os.path.join(rootdir, f"fstab.{self.info.platform or 'mt6789'}"), "w") as f:
                f.write("# fstab - auto generated\n")

        # Copy init .rc files from recovery tree
        rec_tree = os.path.join(self.dump_dir, "trees", "recovery_tree")
        if os.path.isdir(rec_tree):
            for f in os.listdir(rec_tree):
                if f.endswith(".rc") or f.endswith(".sh"):
                    shutil.copy2(os.path.join(rec_tree, f), rootdir)

        # Copy from vendor etc/init
        for init_dir in ["extracted/vendor/etc/init", "vendor/etc/init",
                         "extracted/vendor/etc", "vendor/etc"]:
            d = os.path.join(self.dump_dir, init_dir)
            if os.path.isdir(d):
                for f in os.listdir(d):
                    if f.endswith(".rc"):
                        shutil.copy2(os.path.join(d, f), rootdir)

    def _odm_dlkm_prop(self, out):
        self._prop_file(out, "odm_dlkm.prop", [])

    def _vendor_dlkm_prop(self, out):
        self._prop_file(out, "vendor_dlkm.prop", [])

import shutil as shutil
from ..analyze import DeviceInfo
from ..utils import slug
