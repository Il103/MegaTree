import os, glob, shutil, re

RECOVERY_TYPES = {
    "twrp": {"file": "twrp.mk", "name": "TWRP", "fstab": "recovery.fstab"},
    "ofox": {"file": "ofox_{{CODENAME}}.mk", "name": "OrangeFox", "fstab": "recovery.fstab"},
    "shrp": {"file": "shrp.mk", "name": "SHRP", "fstab": "recovery.fstab"},
    "pbrp": {"file": "pbrp.mk", "name": "PBRP", "fstab": "recovery.fstab"},
}

PLATFORM_GPUS = {
    "mt6789": "mali-g57", "mt6895": "mali-g710", "mt6983": "mali-g710",
    "mt6877": "mali-g68", "mt6873": "mali-g57", "mt6853": "mali-g57",
    "mt6768": "mali-g52", "mt6765": "mali-g52",
    "sm8550": "adreno-740", "sm8475": "adreno-730", "sm8450": "adreno-730",
    "sm8350": "adreno-660", "sm8250": "adreno-650", "sm8150": "adreno-640",
    "kona": "adreno-650", "lito": "adreno-620", "lahaina": "adreno-660",
    "exynos2200": "xclipse-920", "exynos2100": "mali-g78",
    "exynos990": "mali-g77", "exynos9820": "mali-g76",
}

class RecoveryTreeGenerator:
    def __init__(self, info, dump_dir, rec_type="twrp"):
        self.info = info
        self.dump_dir = dump_dir
        self.rec_type = rec_type.lower()
        self.cfg = RECOVERY_TYPES.get(self.rec_type, RECOVERY_TYPES["twrp"])
        self.codename = info.codename or info.device or "unknown"
        self.mfr = info.manufacturer or "unknown"
        self.plat = info.platform or "unknown"
        self.dev_name = slug(self.codename)
        self.mfr_slug = slug(self.mfr)
        self.is_ab = info.is_ab
        self.fingerprint = info.fingerprint or "unknown"
        self.sdk = info.sdk or "35"
        self.arch = info.arch or "arm64"
        self.density = info.density or "420"
        self.gpu = info.gpu or PLATFORM_GPUS.get(self.plat, "")
        self.boot_ver = info.boot_header_version
        self.kernel_base = info.kernel_base
        self.kernel_pagesize = info.kernel_pagesize
        self.kernel_cmdline = info.kernel_cmdline or "bootopt=64S3,32N2,64N2"
        self.super_sz = info.super_size or 9126805504
        self.boot_sz = info.boot_partition_size or 67108864
        self.dtbo_sz = info.dtbo_partition_size or 8388608
        self.ramdisk_type = info.ramdisk_type

    def generate(self, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        self._boardconfig(output_dir)
        self._makefile(output_dir)
        self._android_mk(output_dir)
        self._fstab(output_dir)
        self._init_rc(output_dir)
        self._prebuilt(output_dir)
        self._props(output_dir)
        self._manifest(output_dir)
        print(f"  [{self.cfg['name']}] Complete tree: {output_dir}")
        return output_dir

    def _get_makefile_name(self):
        fname = self.cfg["file"]
        if "{{CODENAME}}" in fname:
            return fname.replace("{{CODENAME}}", self.dev_name.upper())
        return fname

    def _boardconfig(self, out):
        ab = "true" if self.is_ab else "false"
        header_ver = self.boot_ver
        base = self.kernel_base
        pagesize = self.kernel_pagesize
        cmdline = self.kernel_cmdline.strip()
        plat = self.plat
        gpu = self.gpu
        super_sz = self.super_sz
        dyn_sz = super_sz - 4194304 if super_sz > 4194304 else super_sz
        density = self.density
        mfr = self.mfr_slug
        dev = self.dev_name
        codename = self.codename

        content = f"""# BoardConfig.mk - MegaTree Auto-generated
# Device: {codename}  Platform: {plat}  Android: API {self.sdk}

DEVICE_PATH := device/{mfr}/{dev}

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
TARGET_BOOTLOADER_BOARD_NAME := {codename}
TARGET_NO_BOOTLOADER := true
TARGET_NO_RADIOIMAGE := true

# Platform
TARGET_BOARD_PLATFORM := {plat}
PLATFORM_VERSION := {self.sdk or '35'}

# Display
TARGET_SCREEN_DENSITY := {density}
TARGET_RECOVERY_PIXEL_FORMAT := BGRA_8888
TARGET_RECOVERY_PIXEL_FORMAT := RGBX_8888

# Kernel
BOARD_BOOT_HEADER_VERSION := {header_ver}
BOARD_KERNEL_BASE := {base}
BOARD_KERNEL_CMDLINE := {cmdline}
BOARD_KERNEL_PAGESIZE := {pagesize}
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
BOARD_BOOTIMAGE_PARTITION_SIZE := {self.boot_sz}
BOARD_DTBOIMG_PARTITION_SIZE := {self.dtbo_sz}
BOARD_VENDOR_BOOTIMAGE_PARTITION_SIZE := {self.boot_sz}

# Super/Dynamic partitions
BOARD_SUPER_PARTITION_SIZE := {super_sz}
BOARD_SUPER_PARTITION_GROUPS := {mfr}_dynamic_partitions
BOARD_{mfr.upper()}_DYNAMIC_PARTITIONS_PARTITION_LIST := \\
    system vendor product system_ext vendor_dlkm odm_dlkm
BOARD_{mfr.upper()}_DYNAMIC_PARTITIONS_SIZE := {dyn_sz}

# Recovery
TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/recovery.fstab
TARGET_RECOVERY_UI_LIB := libtwrpgui
TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := true
TARGET_USES_MKE2FS := true

# Verified Boot
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
"""
        if gpu:
            content += f"\n# GPU\nTARGET_BOARD_PLATFORM_GPU := {gpu}\n"
        if self.info.security_patch:
            content += f"\n# Security\nVENDOR_SECURITY_PATCH := {self.info.security_patch}\n"

        content += f"\n# Inherit vendor\n-include vendor/{mfr}/{dev}/BoardConfigVendor.mk\n"

        with open(os.path.join(out, "BoardConfig.mk"), "w") as f:
            f.write(content.strip() + "\n")

    def _makefile(self, out):
        fname = self._get_makefile_name()
        codename = self.dev_name
        ab = "true" if self.is_ab else "false"

        common = f"""LOCAL_PATH := $(call my-dir)

ifeq ($(TARGET_DEVICE),{codename})

TARGET_RECOVERY_FSTAB := $(LOCAL_PATH)/recovery.fstab
TARGET_SYSTEM_PROP += $(LOCAL_PATH)/system.prop

endif
"""

        twrp = f"""
# TWRP Configuration
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
TW_INCLUDE_FBE := {ab}
"""

        ofox = f"""
# OrangeFox Configuration
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
OF_DEFAULT_TIMEZONE := Africa/Cairo
OF_DONT_KEEP_LOG_HISTORY := 1
OF_ENABLE_LP3 := 1
OF_KEEP_DM_VERITY := 0
OF_KEEP_DM_VERITY_FORCED_ENCRYPTION := 1
OF_UNBIND_SDCARD_F := 1
OF_SKIP_ORANGEFOX_PROCESS := 0
OF_USE_LOCKSCREEN := 0
"""

        shrp = f"""
# SHRP Configuration
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
SHRP_AB := {ab}
SHRP_STATUSBAR_RIGHT_PADDING := 40
SHRP_STATUSBAR_LEFT_PADDING := 40
SHRP_OFFICIAL := true
"""

        pbrp = f"""
# PBRP Configuration
PB_DEVICE_CODE := {codename}
PB_MAINTAINER := MegaTree
PB_DYNAMIC_PARTITIONS := true
PB_SUPPORT_AB := {ab}
PB_RECOVERY_FSTAB := $(LOCAL_PATH)/recovery.fstab
PB_STATUS := official
PB_FLASHLIGHT_ENABLE := 1
PB_FLASHLIGHT_PATH := /sys/class/leds/torch/brightness
"""

        specifics = {"twrp": twrp, "ofox": ofox, "shrp": shrp, "pbrp": pbrp}
        with open(os.path.join(out, fname), "w") as f:
            f.write((common + specifics.get(self.rec_type, "")).strip() + "\n")

    def _android_mk(self, out):
        with open(os.path.join(out, "Android.mk"), "w") as f:
            f.write(f"LOCAL_PATH := $(call my-dir)\n\nifneq ($(filter {self.dev_name},$(TARGET_DEVICE)),)\ninclude $(call all-makefiles-under,$(LOCAL_PATH))\nendif\n")

    def _fstab(self, out):
        real = None
        for _, fp in self.info.fstabs:
            if os.path.isfile(fp):
                with open(fp, errors="ignore") as f:
                    real = f.read()
                break

        lines = [f"# recovery.fstab - MegaTree", f"# {self.codename} ({self.plat})", ""]
        seen = set()

        if real:
            for line in real.split("\n"):
                s = line.strip()
                if not s or s.startswith("#") or s.startswith("/") or "block" not in s:
                    continue
                if "# 1 " in s or "#define" in s or s.startswith("/*"):
                    continue
                parts = s.split()
                if len(parts) >= 4:
                    dev = parts[0]; mp = parts[1]; fs = parts[2]; opts = parts[3]
                    flags = " ".join(parts[4:]) if len(parts) > 4 else ""
                    if mp in seen: continue
                    seen.add(mp)
                    if fs in ("emmc", "mtd"):
                        lines.append(f"{dev}  {mp}  {fs}  defaults  {flags}")
                    else:
                        lines.append(f"{dev}  {mp}  {fs}  {opts}  {flags}")

        # Fill missing essential partitions
        essentials = {
            "/boot": f"/dev/block/by-name/boot        /boot           emmc    defaults",
            "/vendor_boot": "/dev/block/by-name/vendor_boot /vendor_boot emmc defaults",
            "/dtbo": "/dev/block/by-name/dtbo        /dtbo           emmc    defaults",
            "/vbmeta": "/dev/block/by-name/vbmeta     /vbmeta         emmc    defaults",
            "/system": "/dev/block/by-name/system     /system         erofs   ro,slotselect",
            "/vendor": "/dev/block/by-name/vendor     /vendor         erofs   ro,slotselect",
            "/product": "/dev/block/by-name/product    /product        erofs   ro,slotselect",
            "/system_ext": "/dev/block/by-name/system_ext /system_ext   erofs   ro,slotselect",
            "/data": "/dev/block/by-name/userdata    /data           f2fs    noatime,nosuid,nodev,discard,wait,check,formattable,quota,latemount",
            "/metadata": "/dev/block/by-name/metadata   /metadata       ext4    noatime,nosuid,nodev,discard,wait,check,formattable",
            "/cache": "/dev/block/by-name/cache       /cache          ext4    noatime,nosuid,nodev,noauto_da_alloc,discard,wait,check,formattable",
            "/misc": "/dev/block/by-name/misc         /misc           emmc    defaults",
            "/persist": "/dev/block/by-name/persist    /persist        ext4    noatime,nosuid,nodev,noauto_da_alloc,commit=1,nodelalloc,wait,check,formattable",
            "/nvram": "/dev/block/by-name/nvram       /nvram          emmc    defaults",
        }
        for mp, entry in essentials.items():
            if mp not in seen:
                lines.append(entry + "  defaults")
                seen.add(mp)

        with open(os.path.join(out, "recovery.fstab"), "w") as f:
            f.write("\n".join(lines) + "\n")

    def _init_rc(self, out):
        # Try to use actual init from dump
        src = None
        for p in [
            os.path.join(self.dump_dir, "trees", "recovery_tree", "init.recovery.rc"),
            os.path.join(self.dump_dir, "boot", "ramdisk", "init.recovery.rc"),
            os.path.join(self.dump_dir, "vendor_boot", "ramdisk", "init.recovery.rc"),
            os.path.join(self.dump_dir, "recovery", "root", "init.recovery.rc"),
        ]:
            if os.path.isfile(p):
                src = p; break

        if src:
            shutil.copy2(src, os.path.join(out, "init.recovery.rc"))
            return

        # Generate standard init
        with open(os.path.join(out, "init.recovery.rc"), "w") as f:
            f.write(f"""on early-init
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
""")

    def _prebuilt(self, out):
        pb = os.path.join(out, "prebuilt")
        os.makedirs(pb, exist_ok=True)

        # Kernel
        for src in [
            os.path.join(self.dump_dir, "boot", "kernel"),
            os.path.join(self.dump_dir, "kernel"),
        ]:
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(pb, "kernel"))
                break

        # DTB
        dtb_dir = os.path.join(self.dump_dir, "trees", "dtb")
        dtbs = sorted(glob.glob(os.path.join(dtb_dir, "*.dtb"))) if os.path.isdir(dtb_dir) else []
        if dtbs:
            with open(os.path.join(pb, "dtb.img"), "wb") as out_f:
                for d in dtbs:
                    with open(d, "rb") as in_f:
                        out_f.write(in_f.read())

        # DTBO
        for src in [os.path.join(self.dump_dir, "dtbo.img")]:
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(pb, "dtbo.img"))
                break

    def _props(self, out):
        with open(os.path.join(out, "system.prop"), "w") as f:
            for k in ["ro.build.fingerprint", "ro.build.version.sdk",
                       "ro.product.device", "ro.product.manufacturer",
                       "ro.product.model", "ro.board.platform",
                       "ro.sf.lcd_density", "ro.build.version.release"]:
                if k in self.info.all_props:
                    f.write(f"{k}={self.info.all_props[k]}\n")

        with open(os.path.join(out, "vendor.prop"), "w") as f:
            f.write(f"ro.vendor.build.fingerprint={self.fingerprint}\n")

    def _manifest(self, out):
        with open(os.path.join(out, "manifest.xml"), "w") as f:
            f.write("""<?xml version="1.0" encoding="utf-8"?>
<manifest version="1.0" type="device">
    <hal format="hidl">
        <name>android.hardware.boot</name>
        <transport>hwbinder</transport>
        <version>1.2</version>
        <interface>
            <name>IBootControl</name>
            <instance>default</instance>
        </interface>
    </hal>
</manifest>
""")

from ..analyze import DeviceInfo
from ..utils import slug
