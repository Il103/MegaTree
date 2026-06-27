import os, glob, shutil, re, json

RECOVERY_TYPES = {
    "twrp": {"file": "twrp_{{CODENAME}}.mk", "name": "TWRP"},
    "ofox": {"file": "ofox_{{CODENAME}}.mk", "name": "OrangeFox"},
    "shrp": {"file": "shrp_{{CODENAME}}.mk", "name": "SHRP"},
    "pbrp": {"file": "pbrp_{{CODENAME}}.mk", "name": "PBRP"},
}

PLATFORM_GPUS = {
    "mt6789": "mali-g52 mc1", "mt6895": "mali-g710",
    "mt6983": "mali-g710", "mt6877": "mali-g68",
    "mt6873": "mali-g57", "mt6853": "mali-g57",
    "mt6768": "mali-g52", "mt6765": "mali-g52",
    "sm8550": "adreno-740", "sm8475": "adreno-730",
    "sm8450": "adreno-730", "sm8350": "adreno-660",
    "sm8250": "adreno-650", "sm8150": "adreno-640",
    "kona": "adreno-650", "lito": "adreno-620",
    "lahaina": "adreno-660",
}

class RecoveryTreeGenerator:
    def __init__(self, info, dump_dir, rec_type="twrp"):
        self.info = info
        self.dump_dir = dump_dir
        self.rec_type = rec_type.lower()
        self.cfg = RECOVERY_TYPES.get(self.rec_type, RECOVERY_TYPES["twrp"])
        self.codename = info.codename or info.device or "unknown"
        self.device_name = info.device or self.codename
        self.mfr = info.manufacturer or "unknown"
        self.plat = info.platform or "unknown"
        self.dev_name = slug(self.codename)
        self.dev_name_hyphen = self.device_name.replace("_", "-")
        self.mfr_slug = slug(self.mfr)
        self.is_ab = info.is_ab
        self.fingerprint = info.fingerprint or "unknown"
        self.sdk = info.sdk or "35"
        self.arch = info.arch or "arm64"
        self.density = info.density or "420"
        self.gpu = info.gpu or PLATFORM_GPUS.get(self.plat, "")
        self.boot_ver = info.boot_header_version
        self.kernel_base = info.kernel_base or "0x40078000"
        self.kernel_pagesize = info.kernel_pagesize or 4096
        self.kernel_cmdline = info.kernel_cmdline or "bootopt=64S3,32N2,64N2"
        self.super_sz = info.super_size or 9126805504
        self.boot_sz = info.boot_partition_size or 67108864
        self.dtbo_sz = info.dtbo_partition_size or 8388608
        self.ramdisk_type = info.ramdisk_type
        self.android = info.android or "15"
        self.model = info.model or f"Infinix {self.codename.upper()}"
        self.brand = info.brand or "Infinix"

    def generate(self, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        self._boardconfig(output_dir)
        self._device_mk(output_dir)
        self._android_mk(output_dir)
        self._android_products(output_dir)
        self._makefile(output_dir)
        self._system_prop(output_dir)
        self._prebuilt(output_dir)
        self._recovery_root(output_dir)
        print(f"  [{self.cfg['name']}] Complete: {output_dir}")
        return output_dir

    def _get_makefile_name(self):
        return self.cfg["file"].replace("{{CODENAME}}", self.dev_name.upper())

    def _boardconfig(self, out):
        ab = "true" if self.is_ab else "false"
        plat = self.plat
        gpu = self.gpu
        dev_path = f"device/{self.mfr_slug}/{self.dev_name}"
        cmdline = self.kernel_cmdline.strip()
        sdk = self.sdk
        super_sz = self.super_sz
        super_group_sz = super_sz - 4194304 if super_sz > 4194304 else super_sz

        content = f"""DEVICE_PATH := {dev_path}

# Architecture
TARGET_ARCH := {self.arch}
TARGET_ARCH_VARIANT := armv8-a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_ABI2 := armv8-a
TARGET_CPU_VARIANT := generic
TARGET_CPU_VARIANT_RUNTIME := cortex-a55

TARGET_2ND_ARCH := arm
TARGET_2ND_ARCH_VARIANT := armv8-a
TARGET_2ND_CPU_ABI := armeabi-v7a
TARGET_2ND_CPU_ABI2 := armeabi
TARGET_2ND_CPU_VARIANT := generic

# Bootloader
TARGET_BOOTLOADER_BOARD_NAME := {plat}
TARGET_NO_BOOTLOADER := true

# Platform
TARGET_BOARD_PLATFORM := {plat}"""
        if gpu:
            content += f"\nTARGET_BOARD_PLATFORM_GPU := {gpu}"

        content += f"""

# Kernel
BOARD_KERNEL_CMDLINE := {cmdline}
BOARD_KERNEL_BASE := {self.kernel_base}
BOARD_KERNEL_OFFSET := 0x00008000
BOARD_KERNEL_PAGESIZE := {self.kernel_pagesize}
BOARD_KERNEL_TAGS_OFFSET := 0x07c08000
BOARD_RAMDISK_OFFSET := 0x11088000
BOARD_DTB_OFFSET := 0x07c08000
BOARD_BOOT_HEADER_VERSION := {self.boot_ver}
BOARD_KERNEL_IMAGE_NAME := Image.gz

TARGET_PREBUILT_KERNEL := $(DEVICE_PATH)/prebuilt/kernel
BOARD_PREBUILT_DTBIMAGE_DIR := $(DEVICE_PATH)/prebuilt/dtb
BOARD_INCLUDE_DTB_IN_BOOTIMG := true
BOARD_MKBOOTIMG_ARGS += --header_version $(BOARD_BOOT_HEADER_VERSION)
BOARD_MKBOOTIMG_ARGS += --ramdisk_offset $(BOARD_RAMDISK_OFFSET)
BOARD_MKBOOTIMG_ARGS += --tags_offset $(BOARD_KERNEL_TAGS_OFFSET)
BOARD_MKBOOTIMG_ARGS += --dtb_offset $(BOARD_DTB_OFFSET)

# Vendor boot
BOARD_VENDOR_BOOTIMAGE_PARTITION_SIZE := {self.boot_sz}
TARGET_RECOVERY_RAMDISK_OUT := $(OUT_DIR)/vendor_ramdisk

# A/B
AB_OTA_UPDATER := {ab}
AB_OTA_PARTITIONS += \\
    boot \\
    dtbo \\
    lk \\
    odm \\
    odm_dlkm \\
    product \\
    system \\
    system_ext \\
    vbmeta_system \\
    vbmeta_vendor \\
    vendor \\
    vendor_boot \\
    vendor_dlkm

# AVB
BOARD_AVB_ENABLE := true
BOARD_AVB_MAKE_VBMETA_IMAGE_ARGS += --flags 3
BOARD_AVB_VBMETA_SYSTEM := system system_ext product
BOARD_AVB_VBMETA_SYSTEM_ALGORITHM := SHA256_RSA2048
BOARD_AVB_VBMETA_SYSTEM_KEY_PATH := external/avb/test/data/testkey_rsa2048.pem
BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX := $(PLATFORM_SECURITY_PATCH_TIMESTAMP)
BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX_LOCATION := 1
BOARD_AVB_VBMETA_VENDOR := vendor
BOARD_AVB_VBMETA_VENDOR_ALGORITHM := SHA256_RSA2048
BOARD_AVB_VBMETA_VENDOR_KEY_PATH := external/avb/test/data/testkey_rsa2048.pem
BOARD_AVB_VBMETA_VENDOR_ROLLBACK_INDEX := $(PLATFORM_SECURITY_PATCH_TIMESTAMP)
BOARD_AVB_VBMETA_VENDOR_ROLLBACK_INDEX_LOCATION := 2

# Partitions
BOARD_FLASH_BLOCK_SIZE := 262144
BOARD_SUPER_PARTITION_SIZE := {super_sz}
BOARD_SUPER_PARTITION_GROUPS := main
BOARD_MAIN_SIZE := {super_group_sz}
BOARD_MAIN_PARTITION_LIST := system system_ext vendor product odm odm_dlkm vendor_dlkm

BOARD_SYSTEMIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_SYSTEM_EXTIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_PRODUCTIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_ODMIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_ODM_DLKMIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_VENDOR_DLKMIMAGE_FILE_SYSTEM_TYPE := erofs

# Dynamic partitions
BOARD_DYNAMIC_PARTITION_ENABLE := true

# Virtual A/B
BOARD_VIRTUAL_AB_ENABLE := true
BOARD_VIRTUAL_AB_COMPRESSION := true

# Userdata
BOARD_USERDATAIMAGE_FILE_SYSTEM_TYPE := f2fs

# Recovery
TARGET_RECOVERY_PIXEL_FORMAT := RGBX_8888
TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := true

# Copy out paths
TARGET_COPY_OUT_VENDOR := vendor
TARGET_COPY_OUT_PRODUCT := product
TARGET_COPY_OUT_SYSTEM := system
TARGET_COPY_OUT_SYSTEM_EXT := system_ext
TARGET_COPY_OUT_ODM := odm
TARGET_COPY_OUT_ODM_DLKM := odm_dlkm
TARGET_COPY_OUT_VENDOR_DLKM := vendor_dlkm

# TWRP / Recovery specific
TW_THEME := portrait_hdpi
TW_EXTRA_LANGUAGES := true
TW_SCREEN_BLANK_ON_BOOT := true
TW_INPUT_BLACKLIST := "hbtp_vm"
TW_USE_TOOLBOX := true
TW_INCLUDE_REPACKTOOLS := true
TW_INCLUDE_RESETPROP := true
TW_INCLUDE_LIBRESETPROP := true
TW_HAS_NO_RECOVERY_PARTITION := true
TW_FORCE_CPUINFO_FOR_BATTERY := true
RECOVERY_SDCARD_ON_DATA := true
TW_BRIGHTNESS_PATH := "/sys/class/leds/lcd-backlight/brightness"
TW_DEFAULT_BRIGHTNESS := 10
TW_MAX_BRIGHTNESS := 255

# Flashlight Support
TW_FLASH_LIGHT_PATH := "/sys/class/leds/torch-light/brightness"

# Settings Persistence
TW_DATA_RECOVERY := true

# FRP Addon
TW_INCLUDE_FRP := true

# KernelSU
TW_INCLUDE_KERNELSU := true

# Crypto
TW_INCLUDE_CRYPTO := true
TW_INCLUDE_CRYPTO_FBE := true
TW_INCLUDE_FBE_METADATA_DECRYPT := true
BOARD_USES_METADATA_PARTITION := true
TW_CRYPTO_USE_SYSTEM_VOLD := true
TW_CRYPTO_USE_FBE := true
BOARD_SUPPRESS_SECURE_ERASE := true
TW_CRYPTO_SYSTEM_VOLD := true
PLATFORM_VERSION := 16.1.0
PLATFORM_SECURITY_PATCH := 2099-12-31
VENDOR_SECURITY_PATCH := 2099-12-31

# Debug
TWRP_INCLUDE_LOGCAT := true
TARGET_USES_LOGD := true
"""
        if self.info.security_patch:
            content += f"\nVENDOR_SECURITY_PATCH := {self.info.security_patch}\n"

        with open(os.path.join(out, "BoardConfig.mk"), "w") as f:
            f.write(content.strip() + "\n")

    def _device_mk(self, out):
        dev_name_h = self.dev_name_hyphen
        content = f"""#
# Copyright (C) 2024 The LineageOS Project
#
# SPDX-License-Identifier: Apache-2.0
#

$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit_only.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/base.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/gsi_keys.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/emulated_storage.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota/launch_with_vendor_ramdisk.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota/compression.mk)

ENABLE_VIRTUAL_AB := true
AB_OTA_UPDATER := true

AB_OTA_PARTITIONS += \\
    boot \\
    dtbo \\
    lk \\
    odm \\
    odm_dlkm \\
    product \\
    system \\
    system_ext \\
    vbmeta_system \\
    vbmeta_vendor \\
    vendor \\
    vendor_boot \\
    vendor_dlkm

AB_OTA_POSTINSTALL_CONFIG += \\
    RUN_POSTINSTALL_system=true \\
    POSTINSTALL_PATH_system=system/bin/mtk_plpath_utils \\
    FILESYSTEM_TYPE_system=ext4 \\
    POSTINSTALL_OPTIONAL_system=true

AB_OTA_POSTINSTALL_CONFIG += \\
    RUN_POSTINSTALL_vendor=true \\
    POSTINSTALL_PATH_vendor=bin/checkpoint_gc \\
    FILESYSTEM_TYPE_vendor=ext4 \\
    POSTINSTALL_OPTIONAL_vendor=true

PRODUCT_PACKAGES += \\
    otapreopt_script \\
    cppreopts.sh

PRODUCT_PROPERTY_OVERRIDES += ro.twrp.vendor_boot=true

PRODUCT_USE_DYNAMIC_PARTITIONS := true
PRODUCT_SHIPPING_API_LEVEL := {self.sdk}
PRODUCT_TARGET_VNDK_VERSION := {self.sdk}

PRODUCT_PACKAGES += \\
    android.hardware.boot@1.2-mtkimpl \\
    android.hardware.boot@1.2-mtkimpl.recovery

PRODUCT_PACKAGES_DEBUG += bootctl

PRODUCT_PACKAGES += \\
    android.hardware.fastboot@1.0-impl-mock \\
    fastbootd

PRODUCT_PACKAGES += \\
    android.hardware.health@2.1-impl \\
    android.hardware.health@2.1-service

PRODUCT_PACKAGES += \\
    android.hardware.keymaster@4.1

PRODUCT_PACKAGES += \\
    android.system.keystore2

PRODUCT_PACKAGES += \\
    mtk_plpath_utils \\
    mtk_plpath_utils.recovery

PRODUCT_PACKAGES += \\
    android.hardware.security.keymint \\
    android.hardware.security.secureclock \\
    android.hardware.security.sharedsecret

PRODUCT_PACKAGES += \\
    update_engine \\
    update_engine_sideload \\
    update_verifier

PRODUCT_PACKAGES_DEBUG += update_engine_client

TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += \\
    $(TARGET_OUT_SHARED_LIBRARIES)/android.hardware.keymaster@4.1

TARGET_RECOVERY_DEVICE_MODULES += \\
    android.hardware.keymaster@4.1
"""
        with open(os.path.join(out, "device.mk"), "w") as f:
            f.write(content.strip() + "\n")

    def _android_mk(self, out):
        content = f"""#
# Copyright (C) 2024 The LineageOS Project
#
# SPDX-License-Identifier: Apache-2.0
#

LOCAL_PATH := $(call my-dir)

ifeq ($(TARGET_DEVICE), {self.dev_name_hyphen})

include $(call all-subdir-makefiles,$(LOCAL_PATH))

endif
"""
        with open(os.path.join(out, "Android.mk"), "w") as f:
            f.write(content.strip() + "\n")

    def _android_products(self, out):
        mk = self._get_makefile_name()
        prod = mk.replace(".mk", "")
        content = f"""#
# Copyright (C) 2024 The LineageOS Project
#
# SPDX-License-Identifier: Apache-2.0
#

PRODUCT_MAKEFILES := \\
    $(LOCAL_DIR)/{mk}

COMMON_LUNCH_CHOICES := \\
    {prod}-eng \\
    {prod}-userdebug \\
    {prod}-user
"""
        with open(os.path.join(out, "AndroidProducts.mk"), "w") as f:
            f.write(content.strip() + "\n")

    def _makefile(self, out):
        fname = self._get_makefile_name()
        codename = self.dev_name
        codename_h = self.dev_name_hyphen
        brand = self.brand
        model = self.model
        rec_name = self.cfg["name"]
        rec_lower = self.rec_type
        prod_name = fname.replace(".mk", "")
        ofox_ver = "R12.1"

        common = f"""#
# Copyright (C) 2024 The LineageOS Project
#
# SPDX-License-Identifier: Apache-2.0
#

$(call inherit-product, $(DEVICE_PATH)/device.mk)

PRODUCT_NAME := {prod_name}
PRODUCT_DEVICE := {self.device_name}
PRODUCT_BRAND := {brand}
PRODUCT_MODEL := {model}
PRODUCT_MANUFACTURER := {self.mfr.upper()}

PRODUCT_GMS_CLIENTID_BASE := android-{self.mfr_slug}
"""
        ofox_specific = f"""
PRODUCT_PROPERTY_OVERRIDES += \\
    ro.ofox.version={ofox_ver} \\
    ro.ofox.build_type=Team-BERU \\
    ro.ofox.maintainer=BERU \\
    ro.ofox.device={codename}
"""
        content = common + (ofox_specific if self.rec_type == "ofox" else "")
        with open(os.path.join(out, fname), "w") as f:
            f.write(content.strip() + "\n")

    def _system_prop(self, out):
        content = f"""# MegaTree - Auto-generated system.prop

# Fstab
ro.postinstall.fstab.prefix=/system

# USB MTP
ro.sys.usb.storage.type=mtp

# Crypto
ro.crypto.volume.filenames_mode=aes-256-cts
ro.crypto.type=file

# FRP
ro.frp.pst=/dev/block/by-name/frp

# Display
ro.surface_flinger.max_fps=144
ro.surface_flinger.refresh_rate=144
debug.sf.hw=1
debug.egl.hw=1

# Gatekeeper
ro.hardware.gatekeeper=trustonic

# TEE
ro.vendor.mtk_tee_gp_support=1
ro.vendor.mtk_trustonic_tee_support=1

keymaster_ver=4.1
"""
        with open(os.path.join(out, "system.prop"), "w") as f:
            f.write(content.strip() + "\n")

    def _prebuilt(self, out):
        pb = os.path.join(out, "prebuilt")
        os.makedirs(pb, exist_ok=True)
        dtb_dir = os.path.join(pb, "dtb")
        os.makedirs(dtb_dir, exist_ok=True)

        # Kernel
        for src in [
            os.path.join(self.dump_dir, "boot", "kernel"),
            os.path.join(self.dump_dir, "kernel"),
        ]:
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(pb, "kernel"))
                break

        # DTB files (raw dtbs into dtb/ directory)
        dts_dir = os.path.join(self.dump_dir, "trees", "dts") if os.path.isdir(os.path.join(self.dump_dir, "trees", "dts")) else None
        if dts_dir:
            for fname in sorted(os.listdir(dts_dir)):
                if fname.endswith(".dts"):
                    fpath = os.path.join(dts_dir, fname)
                    output_dtb = os.path.join(dtb_dir, fname.replace(".dts", ".dtb"))
                    import subprocess
                    try:
                        subprocess.run(["dtc", "-@", "-I", "dts", "-O", "dtb", "-o", output_dtb, fpath],
                                       capture_output=True, timeout=30)
                    except: pass

        # DTBO
        for src in [os.path.join(self.dump_dir, "dtbo.img")]:
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(pb, "dtbo.img"))
                break

    def _recovery_root(self, out):
        root = os.path.join(out, "recovery", "root")
        os.makedirs(root, exist_ok=True)
        self._first_stage_ramdisk(root)
        self._init_rc(root)
        self._init_tee_rc(root)
        self._init_usb_rc(root)
        self._init_vibrator_rc(root)
        self._ueventd_plat(root)
        self._system_etc(root)
        self._vendor(root)
        self._kernel_modules(root)

    def _first_stage_ramdisk(self, root):
        fsr = os.path.join(root, "first_stage_ramdisk")
        os.makedirs(fsr, exist_ok=True)
        # Copy original vendor fstab if available
        src = None
        for p in [
            os.path.join(self.dump_dir, "vendor/etc/fstab.{}".format(self.plat)),
            os.path.join(self.dump_dir, "extracted/vendor/etc/fstab.{}".format(self.plat)),
            os.path.join(self.dump_dir, "vendor/etc/fstab.emmc"),
        ]:
            if os.path.isfile(p):
                src = p; break
        if src:
            shutil.copy2(src, os.path.join(fsr, "fstab.{}".format(self.plat)))
        else:
            with open(os.path.join(fsr, "fstab.{}".format(self.plat)), "w") as f:
                f.write("# fstab.{}\n".format(self.plat))

    def _init_rc(self, root):
        # Try platform-specific from dump
        src = None
        for fname in ["init.recovery.{}.rc".format(self.plat), "init.recovery.rc"]:
            for p in [
                os.path.join(self.dump_dir, "boot/ramdisk", fname),
                os.path.join(self.dump_dir, "vendor_boot/ramdisk", fname),
                os.path.join(self.dump_dir, "recovery/root", fname),
            ]:
                if os.path.isfile(p):
                    src = p; break
            if src: break

        if src:
            shutil.copy2(src, os.path.join(root, "init.recovery.{}.rc".format(self.plat)))
        else:
            with open(os.path.join(root, "init.recovery.{}.rc".format(self.plat)), "w") as f:
                f.write(self._default_init_rc())

    def _default_init_rc(self):
        return """import /init.tee.rc
import /init.device.rc

on init
    setprop sys.usb.configfs 1
    setprop sys.usb.controller "musb-hdrc"
    setprop sys.usb.ffs.aio_compat 0
    export LD_LIBRARY_PATH /system/lib64:/vendor/lib64:/vendor/lib64/hw
    setprop crypto.ready 1

on fs
    wait /dev/block/platform/soc/11270000.ufshci
    symlink /dev/block/platform/soc/11270000.ufshci /dev/block/bootdevice
    install_keyring

on boot
    setprop sys.usb.config adb
    setprop debug.sf.hw 1
    setprop debug.egl.hw 1

on post-fs-data
    start health-hal-2-1

on property:ro.crypto.state=encrypted && property:ro.boot.dynamic_partitions=true
    start mobicore
    start vendor.gatekeeper-1-0
    start vendor.keymint-trustonic

service vendor.gatekeeper-1-0 /vendor/bin/hw/android.hardware.gatekeeper@1.0-service
    interface android.hardware.gatekeeper@1.0::IGatekeeper default
    user root
    group root
    disabled
    seclabel u:r:recovery:s0

service vendor.keymint-trustonic /vendor/bin/hw/android.hardware.security.keymint-service.trustonic
    class early_hal
    interface android.hardware.keymaster@4.0::IKeymasterDevice default
    interface android.hardware.keymaster@4.1::IKeymasterDevice default
    user nobody
    seclabel u:r:recovery:s0

on property:servicemanager.ready=true
    setprop sys.boot_completed 1
"""

    def _init_tee_rc(self, root):
        content = """service mobicore /vendor/bin/mcDriverDaemon
    class core
    user root
    group root
    oneshot

on boot
    start mobicore
"""
        with open(os.path.join(root, "init.tee.rc"), "w") as f:
            f.write(content.strip() + "\n")

    def _init_usb_rc(self, root):
        content = """on init
    write /sys/class/android_usb/android0/iManufacturer ${{ro.product.manufacturer}}
    write /sys/class/android_usb/android0/iProduct ${{ro.product.model}}
    write /sys/class/android_usb/android0/iSerial ${{ro.serialno}}

on boot
    write /sys/class/android_usb/android0/enable 0
    write /sys/class/android_usb/android0/idVendor 2717
    write /sys/class/android_usb/android0/idProduct FF10
    write /sys/class/android_usb/android0/bcdDevice 0404
    write /sys/class/android_usb/android0/functions mtp,adb
    write /sys/class/android_usb/android0/enable 1
"""
        with open(os.path.join(root, "init.recovery.usb.rc"), "w") as f:
            f.write(content.strip() + "\n")

    def _init_vibrator_rc(self, root):
        content = """on boot
    write /sys/class/timed_output/vibrator/enable 100
"""
        with open(os.path.join(root, "init.vibrator.rc"), "w") as f:
            f.write(content.strip() + "\n")

    def _ueventd_plat(self, root):
        content = """# eMMC only
/dev/block/mmcblk0                               0660    root    system
/dev/block/mmcblk0boot0                          0660    root    system
/dev/block/mmcblk0boot1                          0660    root    system
/dev/misc-sd                                     0660    root    system

# UFS only
/dev/block/sda                                   0660    root    system
/dev/block/sdb                                   0660    root    system
/dev/block/sdc                                   0660    root    system

# Common block
/dev/block/by-name/boot      0640    root    system
/dev/block/by-name/recovery  0640    root    system
/dev/block/by-name/nvram     0660    root    system
/dev/block/by-name/frp       0660    root    system

# Connectivity
/dev/stpwmt               0660   system     system
/dev/conninfra_dev        0660   system     system

# Mali
/dev/mali0                0666   system     graphics

# ION
/dev/ion                  0666   system     graphics

# DMA heaps
/dev/dma_heap/system              0444   system     system
/dev/dma_heap/system-uncached     0444   system     system
/dev/dma_heap/mtk_mm              0444   system     system
/dev/dma_heap/mtk_mm-uncached     0444   system     system

# Trustonic TEE
/dev/mobicore             0600   system     system
/dev/mobicore-user        0666   system     system
/dev/t-base-tui           0666   system     system

# Touch
/dev/touch                0660   root       system
"""
        with open(os.path.join(root, "ueventd.{}.rc".format(self.plat)), "w") as f:
            f.write(content.strip() + "\n")

    def _system_etc(self, root):
        sec = os.path.join(root, "system", "etc")
        os.makedirs(sec, exist_ok=True)

        # recovery.fstab
        self._recovery_fstab(sec)

        # twrp.flags
        self._twrp_flags(sec)

        # ueventd.rc
        self._ueventd_rc(sec)

        # cgroups.json
        with open(os.path.join(sec, "cgroups.json"), "w") as f:
            json.dump({"Cgroups2": {"Path": "/sys/fs/cgroup", "Mode": "0755", "UID": "root", "GID": "root"}}, f, indent=2)

        # vintf manifest
        vintf = os.path.join(sec, "vintf")
        os.makedirs(vintf, exist_ok=True)
        with open(os.path.join(vintf, "manifest.xml"), "w") as f:
            f.write("""<?xml version="1.0" encoding="utf-8"?>
<manifest version="4.0" type="framework">
    <hal format="hidl">
        <name>android.hidl.manager</name>
        <transport>hwbinder</transport>
        <version>1.2</version>
        <interface>
            <name>IServiceManager</name>
            <instance>default</instance>
        </interface>
    </hal>
    <hal format="hidl">
        <name>android.hidl.memory</name>
        <transport arch="32+64">passthrough</transport>
        <version>1.0</version>
        <interface>
            <name>IMapper</name>
            <instance>ashmem</instance>
        </interface>
    </hal>
    <hal format="hidl">
        <name>android.hidl.token</name>
        <transport>hwbinder</transport>
        <version>1.0</version>
        <interface>
            <name>ITokenManager</name>
            <instance>default</instance>
        </interface>
    </hal>
    <system-sdk>
        <version>28</version>
        <version>29</version>
        <version>30</version>
        <version>31</version>
        <version>32</version>
        <version>33</version>
    </system-sdk>
</manifest>
""")

    def _recovery_fstab(self, sec):
        # Try to get real fstab from dump
        real = None
        for _, fp in self.info.fstabs:
            if os.path.isfile(fp):
                with open(fp, errors="ignore") as f:
                    content = f.read()
                # Check if it has proper recovery-style entries
                if any(x in content for x in ["/system", "/data", "slotselect"]):
                    real = content
                    break

        # Also try the system/etc/recovery.fstab from dump
        for p in [
            os.path.join(self.dump_dir, "recovery/root/system/etc/recovery.fstab"),
            os.path.join(self.dump_dir, "boot/ramdisk/system/etc/recovery.fstab"),
        ]:
            if os.path.isfile(p):
                with open(p, errors="ignore") as f:
                    real = f.read()
                break

        # Use parsed fstab entries + generate complete one
        content = """# Android fstab file.
# MegaTree Auto-generated

#<src>\t\t\t<mnt_point>\t\t<type>\t\t<mnt_flags>\t\t<fs_mgr_flags>

# Logical partitions
system\t\t\t/system\t\t\terofs\t\tro\t\t\t\t\t\t\t\twait,slotselect,logical
system\t\t\t/system\t\t\text4\t\tro\t\t\t\t\t\t\t\twait,slotselect,logical
vendor\t\t\t/vendor\t\t\terofs\t\tro\t\t\t\t\t\t\t\twait,slotselect,logical
vendor\t\t\t/vendor\t\t\text4\t\tro\t\t\t\t\t\t\t\twait,slotselect,logical
product\t\t\t/product\t\terofs\t\tro\t\t\t\t\t\t\t\twait,slotselect,logical
product\t\t\t/product\t\text4\t\tro\t\t\t\t\t\t\t\twait,slotselect,logical
system_ext\t\t/system_ext\t\terofs\t\tro\t\t\t\t\t\t\t\twait,slotselect,logical
system_ext\t\t/system_ext\t\text4\t\tro\t\t\t\t\t\t\t\twait,slotselect,logical
vendor_dlkm\t\t/vendor_dlkm\terofs\t\tro\t\t\t\t\t\t\t\twait,slotselect,logical
vendor_dlkm\t\t/vendor_dlkm\text4\t\tro\t\t\t\t\t\t\t\twait,slotselect,logical
odm_dlkm\t\t/odm_dlkm\t\terofs\t\tro\t\t\t\t\t\t\t\twait,slotselect,logical
odm_dlkm\t\t/odm_dlkm\t\text4\t\tro\t\t\t\t\t\t\t\twait,slotselect,logical

# Userdata
/dev/block/by-name/metadata\t/metadata\t\text4\t\tnoatime,nosuid,nodev,discard\t\t\t\t\t\twait,check,formattable
/dev/block/by-name/userdata\t/data\t\t\tf2fs\t\tnoatime,nosuid,nodev,discard,noflush_merge,fsync_mode=nobarrier,reserve_root=134217,resgid=1065,inlinecrypt\t\t\t\twait,check,formattable,quota,fileencryption=aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized,keydirectory=/metadata/vold/metadata_encryption

# Misc
/dev/block/by-name/misc\t\t/misc\t\t\temmc\t\tdefaults\t\t\t\t\t\t\t\tdefaults

# Cache
/dev/block/by-name/tranfs\t/cache\t\t\text4\t\tnoatime,nosuid,nodev,discard\t\t\t\t\t\twait,check,formattable
"""
        with open(os.path.join(sec, "recovery.fstab"), "w") as f:
            f.write(content.strip() + "\n")

    def _twrp_flags(self, sec):
        content = """# TWRP Partition Flags
# MegaTree Auto-generated

# mount point\t\tfs\t\tdevice\t\t\t\t\tdevice2\t\t\t device3\t\t\tflags

# Boot
/boot\t\t\temmc\t\t/dev/block/by-name/boot\t\t\t\t\t\t\t\t\t\t\tflags=display=boot;slotselect;backup;flashimg
/vendor_boot\t\t\temmc\t\t/dev/block/by-name/vendor_boot\t\t\t\t\t\t\t\t\tflags=display=vendor_boot;slotselect;backup;flashimg
/vbmeta\t\t\temmc\t\t/dev/block/by-name/vbmeta\t\t\t\t\t\t\t\t\t\tflags=display=vbmeta;slotselect;backup;flashimg
/vbmeta_system\t\t\temmc\t\t/dev/block/by-name/vbmeta_system\t\t\t\t\t\t\t\t\tflags=display=vbmeta_system;slotselect;backup;flashimg
/vbmeta_vendor\t\t\temmc\t\t/dev/block/by-name/vbmeta_vendor\t\t\t\t\t\t\t\t\tflags=display=vbmeta_vendor;slotselect;backup;flashimg

# Firmware
/dtbo\t\t\temmc\t\t/dev/block/by-name/dtbo\t\t\t\t\t\t\t\t\t\tflags=display=dtbo;slotselect;backup
/metadata\t\t\t\text4\t\t/dev/block/by-name/metadata\t\t\t\t\t\t\t\t\t\tflags=display=metadata;backup
/misc\t\t\temmc\t\t/dev/block/by-name/misc\t\t\t\t\t\t\t\t\t\tflags=display=misc;backup

# Sensitive Data
/nvcfg\t\t\text4\t\t/dev/block/by-name/nvcfg\t\t\t\t\t\t\t\t\t\tflags=display=nvcfg;backup
/persist_image\t\t\temmc\t\t/dev/block/by-name/persist\t\t\t\t\t\t\t\t\tflags=display=persist;backup
/persistent\t\t\temmc\t\t/dev/block/by-name/frp\t\t\t\t\t\t\t\t\t\tflags=display=persistent;backup
/nvdata\t\t\text4\t\t/dev/block/by-name/nvdata\t\t\t\t\t\t\t\t\t\tflags=display=nvdata;backup
/protect_f\t\t\text4\t\t/dev/block/by-name/protect1\t\t\t\t\t\t\t\t\tflags=display=protect_f;backup
/protect_s\t\t\text4\t\t/dev/block/by-name/protect2\t\t\t\t\t\t\t\t\tflags=display=protect_s;backup
/nvram\t\t\temmc\t\t/dev/block/by-name/nvram\t\t\t\t\t\t\t\t\t\tflags=display=nvram;backup

# Standard MTK partitions
/expdb\t\t\temmc\t\t/dev/block/by-name/expdb\t\t\t\t\t\t\t\t\tflags=display=expdb
/logo\t\t\temmc\t\t/dev/block/by-name/logo\t\t\t\t\t\t\t\t\t\tflags=display=logo;slotselect;backup
/otp\t\t\temmc\t\t/dev/block/by-name/otp\t\t\t\t\t\t\t\t\t\tflags=display=otp
/seccfg\t\t\temmc\t\t/dev/block/by-name/seccfg\t\t\t\t\t\t\t\t\tflags=display=seccfg
/spmfw\t\t\temmc\t\t/dev/block/by-name/spmfw\t\t\t\t\t\t\t\t\tflags=display=spmfw;slotselect
/tee1\t\t\temmc\t\t/dev/block/by-name/tee1\t\t\t\t\t\t\t\t\t\tflags=display=tee1
/tee2\t\t\temmc\t\t/dev/block/by-name/tee2\t\t\t\t\t\t\t\t\t\tflags=display=tee2

# Removable Storage
/external_sd\t\t\tauto\t\t/dev/block/mmcblk1p1\t\t\t/dev/block/mmcblk0p1\t\t\t\t\tflags=display="Micro SD Card";storage;wipeingui;removable;backup=0
/usb_otg\t\t\tauto\t\t/dev/block/sda1\t\t\t\t/dev/block/sda\t\t/dev/block/sdd1\t\t\tflags=display="USB-OTG";storage;wipeingui;removable;backup=0

# Flashable logical partitions
/system_image\t\t\temmc\t\t/dev/block/bootdevice/by-name/system\t\t\t\t\t\t\t\tflags=backup;flashimg
/vendor_image\t\t\temmc\t\t/dev/block/bootdevice/by-name/vendor\t\t\t\t\t\t\t\tflags=backup;flashimg
/system_ext_image\t\t\temmc\t\t/dev/block/bootdevice/by-name/system_ext\t\t\t\t\t\t\tflags=display="System_EXT Image";backup;flashimg
/product_image\t\t\temmc\t\t/dev/block/bootdevice/by-name/product\t\t\t\t\t\t\t\tflags=display="Product Image";backup;flashimg
/vendor_dlkm_image\t\t\temmc\t\t/dev/block/bootdevice/by-name/vendor_dlkm\t\t\t\t\t\t\tflags=display="VendorDLKM Image";backup;flashimg
"""
        with open(os.path.join(sec, "twrp.flags"), "w") as f:
            f.write(content.strip() + "\n")

    def _ueventd_rc(self, sec):
        content = """import /vendor/etc/ueventd.rc
import /odm/etc/ueventd.rc

firmware_directories /etc/firmware/ /odm/firmware/ /vendor/firmware/ /firmware/image/
uevent_socket_rcvbuf_size 16M

subsystem graphics
    devname uevent_devpath
    dirname /dev/graphics

subsystem drm
    devname uevent_devpath
    dirname /dev/dri

subsystem input
    devname uevent_devpath
    dirname /dev/input

subsystem sound
    devname uevent_devpath
    dirname /dev/snd

subsystem dma_heap
   devname uevent_devpath
   dirname /dev/dma_heap

/dev/null                 0666   root       root
/dev/zero                 0666   root       root
/dev/full                 0666   root       root
/dev/ptmx                 0666   root       root
/dev/tty                  0666   root       root
/dev/random               0666   root       root
/dev/urandom              0666   root       root
/dev/ashmem*              0666   root       root
/dev/binder               0666   root       root
/dev/hwbinder             0666   root       root
/dev/vndbinder            0666   root       root

/dev/pmsg0                0222   root       log
/dev/dma_heap/system      0444   system     system
/dev/dma_heap/system-uncached      0444   system     system
/dev/dma_heap/system-secure        0444   system     system

/dev/dri/*                0666   root       graphics

/dev/uhid                 0660   uhid       uhid
/dev/uinput               0660   uhid       uhid
/dev/rtc0                 0640   system     system
/dev/tty0                 0660   root       system
/dev/graphics/*           0660   root       graphics
/dev/input/*              0660   root       input
/dev/snd/*                0660   system     audio
/dev/bus/usb/*            0660   root       usb
/dev/mtp_usb              0660   root       mtp
/dev/usb_accessory        0660   root       usb
/dev/tun                  0660   system     vpn

/sys/devices/platform/trusty.*      trusty_version        0440  root   log
/sys/devices/virtual/input/input*   enable      0660  root   input
/sys/devices/virtual/input/input*   poll_delay  0660  root   input
/sys/devices/virtual/usb_composite/*   enable      0664  root   system
"""
        with open(os.path.join(sec, "ueventd.rc"), "w") as f:
            f.write(content.strip() + "\n")

    def _vendor(self, root):
        v = os.path.join(root, "vendor")
        # vendor/etc/vintf/manifest.xml
        vintf = os.path.join(v, "etc", "vintf")
        os.makedirs(vintf, exist_ok=True)
        with open(os.path.join(vintf, "manifest.xml"), "w") as f:
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
    <hal format="hidl">
        <name>android.hardware.health</name>
        <transport>hwbinder</transport>
        <version>2.1</version>
        <interface>
            <name>IHealth</name>
            <instance>default</instance>
        </interface>
    </hal>
</manifest>
""")
        # Copy firmware from dump
        for src_dir in [
            os.path.join(self.dump_dir, "vendor/firmware"),
            os.path.join(self.dump_dir, "extracted/vendor/firmware"),
        ]:
            if os.path.isdir(src_dir):
                fw = os.path.join(v, "firmware")
                os.makedirs(fw, exist_ok=True)
                for fname in os.listdir(src_dir):
                    if os.path.isfile(os.path.join(src_dir, fname)):
                        shutil.copy2(os.path.join(src_dir, fname), os.path.join(fw, fname))

    def _kernel_modules(self, root):
        modules_dest = os.path.join(root, "lib", "modules")
        os.makedirs(modules_dest, exist_ok=True)

        # Copy from dump's boot ramdisk modules
        for src_dir in [
            os.path.join(self.dump_dir, "boot/ramdisk/lib/modules"),
            os.path.join(self.dump_dir, "lib/modules"),
        ]:
            if os.path.isdir(src_dir):
                for fname in os.listdir(src_dir):
                    fpath = os.path.join(src_dir, fname)
                    if os.path.isfile(fpath) and (fname.endswith(".ko") or fname.startswith("modules.")):
                        shutil.copy2(fpath, os.path.join(modules_dest, fname))

        # Also vendor lib/modules
        for src_dir in [
            os.path.join(self.dump_dir, "vendor/lib/modules"),
            os.path.join(self.dump_dir, "extracted/vendor/lib/modules"),
        ]:
            if os.path.isdir(src_dir):
                vmod = os.path.join(root, "vendor", "lib", "modules")
                os.makedirs(vmod, exist_ok=True)
                for fname in os.listdir(src_dir):
                    fpath = os.path.join(src_dir, fname)
                    if os.path.isfile(fpath) and (fname.endswith(".ko") or fname.startswith("modules.")):
                        shutil.copy2(fpath, os.path.join(vmod, fname))

from ..analyze import DeviceInfo
from ..utils import slug
