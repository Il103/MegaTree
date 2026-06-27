import os, glob, shutil, re

RECOVERY_TYPES = {
    "twrp": {"file": "twrp.mk", "name": "TWRP", "fstab": "recovery.fstab"},
    "ofox": {"file": "ofox_{{CODENAME}}.mk", "name": "OrangeFox", "fstab": "recovery.fstab"},
    "shrp": {"file": "shrp.mk", "name": "SHRP", "fstab": "recovery.fstab"},
    "pbrp": {"file": "pbrp.mk", "name": "PBRP", "fstab": "recovery.fstab"},
}

class RecoveryTreeGenerator:
    def __init__(self, info, dump_dir, rec_type="twrp"):
        self.info = info
        self.dump_dir = dump_dir
        self.rec_type = rec_type.lower()
        self.cfg = RECOVERY_TYPES.get(self.rec_type, RECOVERY_TYPES["twrp"])
        self.codename = info.codename or info.device or "unknown"
        self.mfr = info.manufacturer or "unknown"
        self.plat = info.platform or "mt6789"
        self.dev_name = slug(self.codename)
        self.mfr_slug = slug(self.mfr)
        self.is_ab = info.is_ab
        self.fingerprint = info.fingerprint or "unknown"
        self.sdk = info.sdk or "35"
        self.arch = info.arch or "arm64"
        self.density = info.density or "420"

    def generate(self, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        self._boardconfig(output_dir)
        self._makefile(output_dir)
        self._android_mk(output_dir)
        self._fstab(output_dir)
        self._init_rc(output_dir)
        self._init_scripts(output_dir)
        self._system_prop(output_dir)
        self._kernel_prebuilt(output_dir)
        print(f"  [{self.cfg['name']}] Complete recovery tree: {output_dir}")
        return output_dir

    def _get_makefile_name(self):
        fname = self.cfg["file"]
        if "{{CODENAME}}" in fname:
            return fname.replace("{{CODENAME}}", self.dev_name.upper())
        return fname

    def _boardconfig(self, out):
        ab = "true" if self.is_ab else "false"
        content = f"""# BoardConfig.mk - Complete Recovery Tree
# Device: {self.codename}  Manufacturer: {self.mfr}  Platform: {self.plat}

DEVICE_PATH := device/{self.mfr_slug}/{self.dev_name}

# A/B
AB_OTA_UPDATER := {ab}
BOARD_USES_RECOVERY_AS_BOOT := {ab}

# Architecture
TARGET_ARCH := {self.arch}
TARGET_ARCH_VARIANT := armv8-a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_VARIANT := generic
TARGET_CPU_VARIANT_RUNTIME := cortex-a55

TARGET_2ND_ARCH := arm
TARGET_2ND_ARCH_VARIANT := armv7-a-neon
TARGET_2ND_CPU_ABI := armeabi-v7a
TARGET_2ND_CPU_ABI2 := armeabi

# Bootloader
TARGET_BOOTLOADER_BOARD_NAME := {self.codename}
TARGET_NO_BOOTLOADER := true
TARGET_NO_RADIOIMAGE := true

# Platform
TARGET_BOARD_PLATFORM := {self.plat}
TARGET_BOARD_PLATFORM_GPU := mali-g57

# Display
TARGET_SCREEN_DENSITY := {self.density}
TARGET_RECOVERY_PIXEL_FORMAT := RGBX_8888
TARGET_RECOVERY_PIXEL_FORMAT := BGRA_8888

# Kernel
BOARD_BOOT_HEADER_VERSION := 4
BOARD_KERNEL_BASE := 0x3fff8000
BOARD_KERNEL_CMDLINE := bootopt=64S3,32N2,64N2
BOARD_KERNEL_PAGESIZE := 4096
BOARD_KERNEL_IMAGE_NAME := Image
BOARD_MKBOOTIMG_ARGS += --header_version $(BOARD_BOOT_HEADER_VERSION)
BOARD_INCLUDE_DTB_IN_BOOTIMG := true
BOARD_KERNEL_SEPARATED_DTBO := true

# Prebuilt kernel
TARGET_FORCE_PREBUILT_KERNEL := true
TARGET_PREBUILT_KERNEL := $(DEVICE_PATH)/prebuilt/kernel
TARGET_PREBUILT_DTB := $(DEVICE_PATH)/prebuilt/dtb.img
BOARD_MKBOOTIMG_ARGS += --dtb $(TARGET_PREBUILT_DTB)
BOARD_PREBUILT_DTBOIMAGE := $(DEVICE_PATH)/prebuilt/dtbo.img

# Partitions
BOARD_FLASH_BLOCK_SIZE := 262144
BOARD_BOOTIMAGE_PARTITION_SIZE := 67108864
BOARD_DTBOIMG_PARTITION_SIZE := 8388608
BOARD_VENDOR_BOOTIMAGE_PARTITION_SIZE := 67108864
BOARD_SUPER_PARTITION_SIZE := 9126805504
BOARD_SUPER_PARTITION_GROUPS := {self.mfr_slug}_dynamic_partitions
BOARD_{self.mfr_slug.upper()}_DYNAMIC_PARTITIONS_PARTITION_LIST := \\
    system vendor product system_ext vendor_dlkm odm_dlkm
BOARD_{self.mfr_slug.upper()}_DYNAMIC_PARTITIONS_SIZE := 9122611200

# Recovery
TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/recovery.fstab
TARGET_RECOVERY_UI_LIB := libtwrpgui
TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := true
TARGET_USES_MKE2FS := true

# AVB
BOARD_AVB_ENABLE := true
BOARD_AVB_MAKE_VBMETA_IMAGE_ARGS += --flags 3
BOARD_AVB_VENDOR_BOOT_KEY_PATH := external/avb/test/data/testkey_rsa4096.pem
BOARD_AVB_VENDOR_BOOT_ALGORITHM := SHA256_RSA4096
BOARD_AVB_VENDOR_BOOT_ROLLBACK_INDEX := 1
BOARD_AVB_VENDOR_BOOT_ROLLBACK_INDEX_LOCATION := 1

# Properties
TARGET_SYSTEM_PROP += $(DEVICE_PATH)/system.prop
TARGET_VENDOR_PROP += $(DEVICE_PATH)/vendor.prop

# VINTF
DEVICE_MANIFEST_FILE += $(DEVICE_PATH)/manifest.xml

# Inherit vendor
-include vendor/{self.mfr_slug}/{self.dev_name}/BoardConfigVendor.mk
"""
        with open(os.path.join(out, "BoardConfig.mk"), "w") as f:
            f.write(content.strip() + "\n")

    def _makefile(self, out):
        fname = self._get_makefile_name()
        codename = self.dev_name
        ab = "true" if self.is_ab else "false"

        common = f"""# {self.cfg['name']} Recovery Device Tree
# Device: {self.codename}  Manufacturer: {self.mfr}
LOCAL_PATH := $(call my-dir)

ifeq ($(TARGET_DEVICE),{codename})

# Inherit from main device tree
$(call inherit-product, $(LOCAL_PATH)/../device.mk)

# Recovery-specific
TARGET_RECOVERY_FSTAB := $(LOCAL_PATH)/recovery.fstab

# Properties
TARGET_SYSTEM_PROP += $(LOCAL_PATH)/system.prop

endif
"""

        twrp_specific = f"""
# TWRP Specific Configuration
TW_THEME := portrait_hdpi
TW_EXCLUDE_DEFAULT_USB_INIT := true
TW_EXTRA_LANGUAGES := true
TW_INCLUDE_NTFS_3G := true
TW_INCLUDE_FUSE_EXFAT := true
TW_INCLUDE_FUSE_NTFS := true
TW_HAS_MTP := true
TW_MTP_DEVICE := /dev/mtp_usb
TW_INPUT_BLACKLIST := hbtp_vm
TW_BRIGHTNESS_PATH := /sys/class/leds/lcd-backlight/brightness
TW_MAX_BRIGHTNESS := 2047
TW_DEFAULT_BRIGHTNESS := 1200
TW_Y_OFFSET := 0
TW_H_OFFSET := 0
TW_NO_REBOOT_BOOTLOADER := false
TW_HAS_DOWNLOAD_MODE := true
TW_INCLUDE_CRYPTO := true
TW_USE_TOOLBOX := true
TW_INCLUDE_RESETPROP := true
TW_INCLUDE_LIBRESETPROP := true
TW_EXCLUDE_TWRPAPP := true
TW_DEVICE_VERSION := $(shell date +%Y%m%d)
TARGET_RECOVERY_UI_LIB := libtwrpgui
TW_USE_NEW_MINADBD := true
"""

        ofox_specific = f"""
# OrangeFox Specific Configuration
FOX_TARGET_DEVICES := {self.mfr_slug},{codename}
OF_TARGET_DEVICE := {codename}
TARGET_DEVICE_ALT := {self.mfr_slug}
FOX_VERSION := R11.1_1
OF_FLASHLIGHT_ENABLE := 1
OF_FL_PATH1 := /sys/class/leds/torch/brightness
OF_FL_PATH2 := /sys/class/leds/torch/max_brightness
OF_TWRP_COMPATIBILITY_MODE := 1
OF_AB_DEVICE := {ab}
OF_SUPPORT_VBMETA := 1
OF_DONT_PATCH_ENCRYPTED_DEVICE := 1
OF_USE_MAGISKBOOT := 1
OF_USE_MAGISKBOOT_FOR_ALL_PATCHES := 1
OF_NO_TREBLE_REQUIRED := 0
OF_FBE_METADATA_MOUNT_DEVICE := /metadata
OF_SKIP_FBE_DECRYPTION := 1
OF_QUICK_BACKUP_LIST := /boot;/data;/system_image;/vendor_image;
OF_MAINTAINER := MegaTree
OF_DISABLE_EXTRA_ABOUT_PAGE := 0
OF_SUPPORT_ALL_BLOCK_OTA_UPDATES := 1
OF_FIX_OTA_UPDATE_MANUAL_FLASH_ERROR := 1
OF_NO_ADDITIONAL_MIUI_PROPS_CHECK := 1
OF_NO_MIUI_OTA_VENDOR_CHECK := 1
OF_CHECK_ATSP_AND_GSID := 1
OF_DISABLE_MIUI_OTA_BY_DEFAULT := 1
OF_KEEP_FORCED_ENCRYPTION := 1
OF_SUPPORT_VBMETA_V2 := 1
OF_SUPPORT_PREBUILT_KERNEL := 1
TARGET_RECOVERY_UI_LIB := libtwrpgui
"""

        shrp_specific = f"""
# SHRP Specific Configuration
SHRP_DEVICE_CODE := {codename}
SHRP_MAINTAINER := MegaTree
SHRP_REC_TYPE := Treble
SHRP_DEVICE_TYPE := A{'+' if self.is_ab else 'B'}
SHRP_DYNAMIC_PARTITIONS := true
SHRP_RECOVERY_FSTAB := $(LOCAL_PATH)/recovery.fstab
SHRP_FLASH := 1
SHRP_CUSTOM_FLASHLIGHT := true
SHRP_FLASH_PATH := /sys/class/leds/torch/brightness
SHRP_FLASH_MAX := 2047
"""

        pbrp_specific = f"""
# PBRP Specific Configuration
PB_DEVICE_CODE := {codename}
PB_MAINTAINER := MegaTree
PB_DYNAMIC_PARTITIONS := true
PB_SUPPORT_AB := {ab}
PB_RECOVERY_FSTAB := $(LOCAL_PATH)/recovery.fstab
"""

        specifics = {
            "twrp": twrp_specific,
            "ofox": ofox_specific,
            "shrp": shrp_specific,
            "pbrp": pbrp_specific,
        }

        content = common + specifics.get(self.rec_type, "")
        with open(os.path.join(out, fname), "w") as f:
            f.write(content.strip() + "\n")

    def _android_mk(self, out):
        content = f"""LOCAL_PATH := $(call my-dir)

ifneq ($(filter {self.codename},$(TARGET_DEVICE)),)

include $(call all-makefiles-under,$(LOCAL_PATH))

endif
"""
        with open(os.path.join(out, "Android.mk"), "w") as f:
            f.write(content)

    def _fstab(self, out):
        fname = self.cfg["fstab"]
        lines = [f"# {fname} - Generated from actual device fstab", f"# Device: {self.codename}  Platform: {self.plat}", ""]

        real_fstab = None
        for key, full in self.info.fstabs:
            if os.path.isfile(full):
                with open(full, errors="ignore") as f:
                    real_fstab = f.read()
                break

        if real_fstab:
            for line in real_fstab.split("\n"):
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or stripped.startswith("\\"):
                    continue
                if "# 1 " in stripped or "#define" in stripped or stripped.startswith("/*"):
                    continue
                parts = stripped.split()
                if len(parts) >= 4:
                    device = parts[0]
                    mount = parts[1]
                    fstype = parts[2]
                    opts = parts[3] if len(parts) > 3 else "defaults"
                    flags = " ".join(parts[4:]) if len(parts) > 4 else ""

                    if fstype == "emmc":
                        lines.append(f"{device}  {mount}  emmc  defaults  {flags}")
                    elif fstype == "mtd":
                        lines.append(f"{device}  {mount}  mtd  defaults  {flags}")
                    else:
                        lines.append(f"{device}  {mount}  {fstype}  {opts}  {flags}")

        if not real_fstab:
            lines.extend([
                "# Boot/Recovery partitions",
                "/dev/block/by-name/boot        /boot           emmc    defaults        defaults",
                "/dev/block/by-name/vendor_boot /vendor_boot    emmc    defaults        defaults",
                "/dev/block/by-name/dtbo        /dtbo           emmc    defaults        defaults",
                "/dev/block/by-name/vbmeta      /vbmeta         emmc    defaults        defaults",
                "/dev/block/by-name/vbmeta_system /vbmeta_system emmc  defaults        defaults",
                "/dev/block/by-name/vbmeta_vendor /vbmeta_vendor emmc  defaults        defaults",
                "",
                "# Dynamic partitions",
                "/dev/block/by-name/system      /system         erofs   ro,slotselect   defaults",
                "/dev/block/by-name/vendor      /vendor         erofs   ro,slotselect   defaults",
                "/dev/block/by-name/product     /product        erofs   ro,slotselect   defaults",
                "/dev/block/by-name/system_ext  /system_ext     erofs   ro,slotselect   defaults",
                "",
                "# Data",
                "/dev/block/by-name/userdata    /data           f2fs    noatime,nosuid,nodev,discard,wait,check,formattable,quota,reservedsize=128m,latemount",
                "/dev/block/by-name/metadata    /metadata       ext4    noatime,nosuid,nodev,discard,wait,check,formattable,first_stage_mount",
                "",
                "# Cache (if present)",
                "/dev/block/by-name/cache       /cache          ext4    noatime,nosuid,nodev,noauto_da_alloc,discard,wait,check,formattable",
                "",
                "# Misc",
                "/dev/block/by-name/misc        /misc           emmc    defaults        defaults",
                "/dev/block/by-name/persist     /persist        ext4    noatime,nosuid,nodev,noauto_da_alloc,commit=1,nodelalloc,wait,check,formattable",
                "/dev/block/by-name/protect1    /mnt/vendor/protect_f ext4 noatime,nosuid,nodev,noauto_da_alloc,commit=1,nodelalloc,wait,check,formattable",
                "/dev/block/by-name/protect2    /mnt/vendor/protect_s ext4 noatime,nosuid,nodev,noauto_da_alloc,commit=1,nodelalloc,wait,check,formattable",
                "/dev/block/by-name/nvdata      /mnt/vendor/nvdata   ext4 noatime,nosuid,nodev,noauto_da_alloc,commit=1,nodelalloc,wait,check,formattable",
                "/dev/block/by-name/nvcfg       /mnt/vendor/nvcfg    ext4 noatime,nosuid,nodev,noauto_da_alloc,commit=1,nodelalloc,wait,check,formattable",
                "",
                "# Transsion specific (Infinix/Tecno/Itel)",
                "/dev/block/by-name/tranfs      /tranfs         ext4    noatime,nosuid,nodev,noauto_da_alloc,discard wait,check,formattable,nofail",
                "",
                "# SD card / USB OTG",
                "/devices/platform/soc/11240000.mmc* auto auto defaults voldmanaged=sdcard1:auto,encryptable=userdata",
                "/devices/platform/soc/mt_usb*   auto vfat defaults voldmanaged=usbotg:auto",
            ])

        with open(os.path.join(out, fname), "w") as f:
            f.write("\n".join(lines) + "\n")

    def _init_rc(self, out):
        content = f"""on early-init
    start ueventd

on init
    export PATH /sbin:/system/sbin:/system/bin:/system/xbin
    export ANDROID_ROOT /system
    export ANDROID_DATA /data
    export EXTERNAL_STORAGE /sdcard

on fs
    mount_all recovery.fstab

on boot
    class_start core

service ueventd /sbin/ueventd
    critical
    seclabel u:r:ueventd:s0

on property:ro.build.fingerprint=*
    setprop ro.build.fingerprint {self.fingerprint}

on property:persist.sys.usb.config=*
    write /sys/class/android_usb/android0/enable 0
    write /sys/class/android_usb/android0/idVendor 2717
    write /sys/class/android_usb/android0/idProduct FF10
    write /sys/class/android_usb/android0/functions ${{persist.sys.usb.config}}
    write /sys/class/android_usb/android0/enable 1
"""
        with open(os.path.join(out, "init.recovery.rc"), "w") as f:
            f.write(content)

    def _init_scripts(self, out):
        etc = os.path.join(out, "etc")
        os.makedirs(etc, exist_ok=True)

        copied = 0
        for src_dir in [
            os.path.join(self.dump_dir, "trees", "recovery_tree"),
            os.path.join(self.dump_dir, "vendor_boot", "ramdisk"),
            os.path.join(self.dump_dir, "boot", "ramdisk"),
            os.path.join(self.dump_dir, "recovery"),
        ]:
            if not os.path.isdir(src_dir):
                continue
            for fname in os.listdir(src_dir):
                if fname.endswith(".rc") or fname.endswith(".sh"):
                    dst = os.path.join(etc, fname)
                    shutil.copy2(os.path.join(src_dir, fname), dst)
                    copied += 1

        # Also copy from extracted vendor
        for src_dir in [
            os.path.join(self.dump_dir, "extracted", "vendor", "etc", "init"),
            os.path.join(self.dump_dir, "vendor", "etc", "init"),
        ]:
            if os.path.isdir(src_dir):
                for fname in os.listdir(src_dir):
                    if fname.endswith(".rc"):
                        dst = os.path.join(etc, fname)
                        shutil.copy2(os.path.join(src_dir, fname), dst)
                        copied += 1

        print(f"    Init scripts copied: {copied}")

    def _system_prop(self, out):
        props = {}
        for key in ["ro.build.fingerprint", "ro.build.version.sdk",
                     "ro.product.device", "ro.product.manufacturer",
                     "ro.product.model", "ro.board.platform",
                     "ro.sf.lcd_density", "ro.build.version.release"]:
            if key in self.info.all_props:
                props[key] = self.info.all_props[key]

        with open(os.path.join(out, "system.prop"), "w") as f:
            for k, v in props.items():
                f.write(f"{k}={v}\n")

        with open(os.path.join(out, "vendor.prop"), "w") as f:
            f.write(f"ro.vendor.build.fingerprint={self.fingerprint}\n")

    def _kernel_prebuilt(self, out):
        prebuilt = os.path.join(out, "prebuilt")
        os.makedirs(prebuilt, exist_ok=True)

        # Copy kernel
        kernel_sources = [
            os.path.join(self.dump_dir, "boot", "kernel"),
            os.path.join(self.dump_dir, "kernel"),
        ]
        kernel_dst = os.path.join(prebuilt, "kernel")
        for src in kernel_sources:
            if os.path.isfile(src):
                shutil.copy2(src, kernel_dst)
                print(f"    Kernel: {os.path.getsize(src)} bytes")
                break

        # Copy dtb
        dtb_dir = os.path.join(self.dump_dir, "trees", "dtb")
        dtb_files = sorted(glob.glob(os.path.join(dtb_dir, "*.dtb"))) if os.path.isdir(dtb_dir) else []
        if dtb_files:
            with open(os.path.join(prebuilt, "dtb.img"), "wb") as out_f:
                for dtb in dtb_files:
                    with open(dtb, "rb") as in_f:
                        out_f.write(in_f.read())
            print(f"    DTB: {len(dtb_files)} blobs merged")

        # Copy dtbo
        for src in [
            os.path.join(self.dump_dir, "dtbo.img"),
            os.path.join(self.dump_dir, "dtbo", "dtbo.img"),
        ]:
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(prebuilt, "dtbo.img"))
                print(f"    DTBO: present")
                break

    def _get_makefile_name(self):
        fname = self.cfg["file"]
        if "{{CODENAME}}" in fname:
            return fname.replace("{{CODENAME}}", self.dev_name.upper())
        return fname

from ..analyze import DeviceInfo
from ..utils import slug
