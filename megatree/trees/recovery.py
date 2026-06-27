import os, glob, shutil

RECOVERY_TYPES = {
    "twrp": {
        "file": "twrp.mk",
        "name": "TWRP",
        "fstab": "twrp.fstab",
        "init": "init.recovery.rc",
    },
    "ofox": {
        "file": "ofox_{{CODENAME}}.mk",
        "name": "OrangeFox",
        "fstab": "twrp.fstab",
        "init": "init.recovery.rc",
    },
    "shrp": {
        "file": "shrp.mk",
        "name": "SHRP",
        "fstab": "shrp.fstab",
        "init": "init.recovery.rc",
    },
    "pbrp": {
        "file": "pbrp.mk",
        "name": "PBRP",
        "fstab": "pbrp.fstab",
        "init": "init.recovery.rc",
    },
}

class RecoveryTreeGenerator:
    def __init__(self, info, dump_dir, rec_type="twrp"):
        self.info = info
        self.dump_dir = dump_dir
        self.rec_type = rec_type.lower()
        self.cfg = RECOVERY_TYPES.get(self.rec_type, RECOVERY_TYPES["twrp"])
        self.codename = info.codename or "unknown"
        self.mfr = info.manufacturer or "unknown"
        self.plat = info.platform or "mt6789"
        self.device_path = f"device/{slug(self.mfr)}/{slug(self.codename)}"
        self.is_ab = info.is_ab

    def generate(self, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        self._makefile(output_dir)
        self._fstab(output_dir)
        self._init_rc(output_dir)
        self._copy_init_scripts(output_dir)
        self._boardconfig(output_dir)
        print(f"  [{self.cfg['name']}] Generated at {output_dir}")
        return output_dir

    def _get_makefile_name(self):
        fname = self.cfg["file"]
        if "{{CODENAME}}" in fname:
            return fname.replace("{{CODENAME}}", self.codename.upper())
        return fname

    def _makefile(self, out):
        fname = self._get_makefile_name()
        is_ofox = self.rec_type == "ofox"
        is_twrp = self.rec_type == "twrp"
        codename = self.codename
        mfr = slug(self.mfr)
        plat = self.plat
        ab = "true" if self.is_ab else "false"

        lines = []
        if is_ofox:
            lines.append(f"# OrangeFox Recovery - Auto-generated for {codename}")
            lines.append(f"FOX_TARGET_DEVICES := {mfr},{codename}")
            lines.append(f"OF_TARGET_DEVICE := {codename}")
            lines.append(f"")
            lines.append(f"TARGET_DEVICE_ALT := {mfr}")
            lines.append(f"FOX_VERSION := R11.1")
            lines.append(f"OF_FLASHLIGHT_ENABLE := 1")
            lines.append(f"OF_FL_PATH1 := /sys/class/leds/torch/brightness")
            lines.append(f"OF_FL_PATH2 := /sys/class/leds/torch/max_brightness")
            lines.append(f"OF_TWRP_COMPATIBILITY_MODE := 1")
            lines.append(f"")
            lines.append(f"# Inherit TWRP base")
            lines.append(f"$(call inherit-product, $(LOCAL_PATH)/twrp.mk)")
        elif is_twrp:
            lines.append(f"# TWRP Recovery - Auto-generated for {codename}")
            lines.append(f"TARGET_DEVICE := {codename}")
            lines.append(f"")
        else:
            lines.append(f"# {self.cfg['name']} Recovery - Auto-generated for {codename}")
            lines.append(f"TARGET_DEVICE := {codename}")

        # Common flags
        lines.extend([
            f"",
            f"TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/recovery/{self.cfg['fstab']}",
            f"TARGET_RECOVERY_PIXEL_FORMAT := RGBX_8888",
            f"TARGET_USERIMAGES_USE_EXT4 := true",
            f"TARGET_USERIMAGES_USE_F2FS := true",
            f"",
            f"# Platform",
            f"TARGET_BOARD_PLATFORM := {plat}",
            f"TARGET_BOARD_PLATFORM_GPU := mali-g57",
            f"",
            f"# Architecture",
            f"TARGET_ARCH := arm64",
            f"TARGET_ARCH_VARIANT := armv8-a",
            f"TARGET_CPU_ABI := arm64-v8a",
            f"TARGET_CPU_VARIANT := generic",
            f"TARGET_2ND_ARCH := arm",
            f"TARGET_2ND_ARCH_VARIANT := armv7-a-neon",
            f"TARGET_2ND_CPU_ABI := armeabi-v7a",
            f"TARGET_2ND_CPU_ABI2 := armeabi",
            f"",
            f"# Boot",
            f"BOARD_BOOT_HEADER_VERSION := 4",
            f"BOARD_KERNEL_BASE := 0x3fff8000",
            f"BOARD_KERNEL_PAGESIZE := 4096",
            f"BOARD_VENDOR_BOOTIMAGE_HEADER_VERSION := 4",
            f"",
            f"# Partitions",
            f"BOARD_FLASH_BLOCK_SIZE := 262144",
            f"BOARD_BOOTIMAGE_PARTITION_SIZE := 67108864",
            f"BOARD_SUPER_PARTITION_SIZE := 9126805504",
            f"BOARD_SUPER_PARTITION_GROUPS := {mfr}_dynamic_partitions",
            f"BOARD_{mfr.upper()}_DYNAMIC_PARTITIONS_PARTITION_LIST := \\",
            f"    system vendor product system_ext vendor_dlkm odm_dlkm",
            f"BOARD_{mfr.upper()}_DYNAMIC_PARTITIONS_SIZE := 9122611200",
            f"",
        ])

        if is_ofox:
            lines.extend([
                f"# OrangeFox specific",
                f"OF_AB_DEVICE := {ab}",
                f"OF_SUPPORT_VBMETA := 1",
                f"OF_DONT_PATCH_ENCRYPTED_DEVICE := 1",
                f"OF_USE_MAGISKBOOT := 1",
                f"OF_USE_MAGISKBOOT_FOR_ALL_PATCHES := 1",
                f"OF_NO_TREBLE_REQUIRED := 0",
                f"OF_FBE_METADATA_MOUNT_DEVICE := /metadata",
                f"OF_SKIP_FBE_DECRYPTION := 1",
                f"OF_QUICK_BACKUP_LIST := /boot;/data;/system_image;/vendor_image;",
                f"OF_MAINTAINER := Megatree",
                f"OF_MAINTAINER_AVATAR := $(DEVICE_PATH)/recovery/maintainer.png",
                f"",
            ])
        elif is_twrp:
            lines.extend([
                f"# TWRP specific",
                f"TW_THEME := portrait_hdpi",
                f"TW_EXCLUDE_DEFAULT_USB_INIT := true",
                f"TW_EXTRA_LANGUAGES := true",
                f"TW_INCLUDE_NTFS_3G := true",
                f"TW_INCLUDE_FUSE_EXFAT := true",
                f"TW_INCLUDE_FUSE_NTFS := true",
                f"TW_HAS_MTP := true",
                f"TW_MTP_DEVICE := /dev/mtp_usb",
                f"TW_INPUT_BLACKLIST := hbtp_vm",
                f"TW_BRIGHTNESS_PATH := /sys/class/leds/lcd-backlight/brightness",
                f"TW_MAX_BRIGHTNESS := 2047",
                f"TW_DEFAULT_BRIGHTNESS := 1200",
                f"TW_Y_OFFSET := 0",
                f"TW_H_OFFSET := 0",
                f"TW_NO_REBOOT_BOOTLOADER := false",
                f"TW_HAS_DOWNLOAD_MODE := true",
                f"TW_INCLUDE_CRYPTO := true",
                f"TW_USE_TOOLBOX := true",
                f"",
            ])

        with open(os.path.join(out, fname), "w") as f:
            f.write("\n".join(lines))

    def _fstab(self, out):
        fname = self.cfg["fstab"]
        fstab_path = os.path.join(out, fname)

        content = []
        content.append(f"# {fname} - Auto-generated for {self.codename}")
        content.append(f"# Recovery fstab")
        content.append("")

        # First try to read real fstab from dump
        real_fstab = None
        for fstab_key, fstab_full in self.info.fstabs:
            if os.path.isfile(fstab_full):
                with open(fstab_full) as f:
                    real_fstab = f.read()
                break

        if real_fstab:
            for line in real_fstab.split("\n"):
                line = line.strip()
                if line.startswith("#") or not line or line.startswith("/"):
                    content.append(line)
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    content.append(line)
        else:
            content.extend([
                "# Boot"
                "/dev/block/by-name/boot        /boot           emmc    defaults        defaults",
                "/dev/block/by-name/vendor_boot /vendor_boot    emmc    defaults        defaults",
                "/dev/block/by-name/dtbo        /dtbo           emmc    defaults        defaults",
                "",
                "# Dynamic partitions",
                "/dev/block/by-name/system      /system         erofs   ro,slotselect   defaults",
                "/dev/block/by-name/vendor      /vendor         erofs   ro,slotselect   defaults",
                "/dev/block/by-name/product     /product        erofs   ro,slotselect   defaults",
                "",
                "# Data",
                "/dev/block/by-name/userdata    /data           f2fs    noatime,nosuid,nodev,discard,wait,check,formattable,quota,reservedsize=128m,latemount",
                "/dev/block/by-name/metadata    /metadata       ext4    noatime,nosuid,nodev,discard,wait,check,formattable,first_stage_mount",
                "",
                "# Misc",
                "/dev/block/by-name/misc        /misc           emmc    defaults        defaults",
                "/dev/block/by-name/cache       /cache          ext4    noatime,nosuid,nodev,noauto_da_alloc,discard,wait,check,formattable",
                "/dev/block/by-name/persist     /persist        ext4    noatime,nosuid,nodev,noauto_da_alloc,commit=1,nodelalloc,wait,check,formattable",
            ])

        # Validate fstab entries
        validated = []
        seen = set()
        for line in content:
            line = line.strip()
            if not line or line.startswith("#"):
                validated.append(line)
                continue
            parts = line.split()
            if len(parts) >= 4:
                mount_point = parts[1]
                if mount_point in seen:
                    continue
                seen.add(mount_point)
            validated.append(line)

        with open(fstab_path, "w") as f:
            f.write("\n".join(validated) + "\n")

    def _init_rc(self, out):
        rec_tree = os.path.join(self.dump_dir, "trees", "recovery_tree")
        orig_init = os.path.join(rec_tree, "init.recovery.rc")

        if os.path.isfile(orig_init):
            shutil.copy2(orig_init, os.path.join(out, "init.recovery.rc"))
            return

        plat = self.plat
        fstab_name = self.cfg["fstab"]
        content = f"""on early-init
    start ueventd

on init
    export PATH /sbin:/system/sbin:/system/bin:/system/xbin
    export ANDROID_ROOT /system
    export ANDROID_DATA /data
    export EXTERNAL_STORAGE /sdcard

on fs
    mount_all {fstab_name}

on boot
    class_start core

service ueventd /sbin/ueventd
    critical
    seclabel u:r:ueventd:s0

on property:ro.build.fingerprint=*
    setprop ro.build.fingerprint {self.info.fingerprint or "unknown"}

on property:persist.sys.usb.config=*
    write /sys/class/android_usb/android0/enable 0
    write /class/android_usb/android0/idVendor 2717
    write /sys/class/android_usb/android0/idProduct FF10
    write /sys/class/android_usb/android0/functions ${{persist.sys.usb.config}}
    write /sys/class/android_usb/android0/enable 1
"""
        with open(os.path.join(out, "init.recovery.rc"), "w") as f:
            f.write(content)

    def _copy_init_scripts(self, out):
        rec_tree = os.path.join(self.dump_dir, "trees", "recovery_tree")
        if not os.path.isdir(rec_tree):
            return

        for fname in os.listdir(rec_tree):
            if fname.endswith(".rc") and fname != "init.recovery.rc":
                shutil.copy2(os.path.join(rec_tree, fname), out)
            if "fstab" in fname:
                shutil.copy2(os.path.join(rec_tree, fname), out)

    def _boardconfig(self, out):
        if self.rec_type != "twrp":
            return
        content = f"""# BoardConfig.mk for TWRP
LOCAL_PATH := $(call my-dir)

ifeq ($(TARGET_DEVICE),{self.codename})
include $(call all-makefiles-under,$(LOCAL_PATH))
endif
"""
        with open(os.path.join(out, "BoardConfig.mk"), "w") as f:
            f.write(content)

from ..analyze import DeviceInfo
from ..utils import slug
