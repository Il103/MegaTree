import os, struct

ANDROID_MAGIC = b"ANDROID!"

def parse_boot_image(path):
    if not os.path.isfile(path):
        return None
    sz = os.path.getsize(path)
    if sz < 2048:
        return None

    with open(path, "rb") as f:
        data = f.read()

    if data[:8] != ANDROID_MAGIC:
        # Not a boot image, check if it's a sparse image
        if data[:4] == b"\x3a\xff\x26\xed":  # SPARSE_HEADER_MAGIC
            return {"magic": "SPARSE", "header_version": 0}
        return None

    result = {"magic": "ANDROID!", "path": path, "size": sz}

    header_version = struct.unpack("<I", data[40:44])[0] if sz >= 44 else 0
    result["header_version"] = header_version

    if header_version <= 2:
        result["kernel_size"] = struct.unpack("<I", data[8:12])[0]
        result["kernel_addr"] = struct.unpack("<I", data[12:16])[0]
        result["ramdisk_size"] = struct.unpack("<I", data[16:20])[0]
        result["ramdisk_addr"] = struct.unpack("<I", data[20:24])[0]
        result["second_size"] = struct.unpack("<I", data[24:28])[0]
        result["second_addr"] = struct.unpack("<I", data[28:32])[0]
        result["tags_addr"] = struct.unpack("<I", data[32:36])[0]
        result["page_size"] = struct.unpack("<I", data[36:40])[0]
        result["os_version"] = struct.unpack("<I", data[44:48])[0]
        result["name"] = data[48:64].rstrip(b"\x00").decode(errors="replace")
        result["cmdline"] = data[64:576].rstrip(b"\x00").decode(errors="replace")
        result["sha"] = data[576:608].hex() if sz >= 608 else ""

        if header_version >= 1:
            result["recovery_dtbo_size"] = struct.unpack("<Q", data[608:616])[0]
            result["recovery_dtbo_offset"] = struct.unpack("<Q", data[616:624])[0]
            result["header_size"] = struct.unpack("<I", data[624:628])[0]
        if header_version >= 2:
            result["dtb_size"] = struct.unpack("<I", data[628:632])[0]
            result["dtb_addr"] = struct.unpack("<Q", data[632:640])[0]

    else:
        # v3/v4
        result["kernel_size"] = struct.unpack("<I", data[12:16])[0]
        result["kernel_addr"] = struct.unpack("<Q", data[16:24])[0]
        result["ramdisk_size"] = struct.unpack("<I", data[24:28])[0]
        result["ramdisk_addr"] = struct.unpack("<Q", data[28:36])[0]
        result["os_version"] = struct.unpack("<I", data[36:40])[0]
        result["header_size"] = struct.unpack("<I", data[40:44])[0]
        result["page_size"] = 4096  # v3/v4 always 4096
        cmdline_offset = 256 if header_version >= 3 else 64
        result["cmdline"] = data[cmdline_offset:cmdline_offset+896].rstrip(b"\x00").decode(errors="replace")

    # Extract kernel offset
    header_sz = result.get("header_size", (2048 if header_version <= 2 else 4096))
    result["kernel_offset"] = header_sz

    return result


def extract_kernel(boot_info, out_dir):
    if not boot_info or "kernel_offset" not in boot_info:
        return None
    kernel_sz = boot_info.get("kernel_size", 0)
    if kernel_sz == 0:
        return None
    page_sz = boot_info.get("page_size", 4096)
    offset = boot_info["kernel_offset"]

    kernel_path = os.path.join(out_dir, "kernel")
    with open(boot_info["path"], "rb") as f:
        f.seek(offset)
        kernel_data = f.read(kernel_sz)
    with open(kernel_path, "wb") as f:
        f.write(kernel_data)
    return kernel_path


def extract_ramdisk(boot_info, out_dir):
    if not boot_info or "ramdisk_size" not in boot_info:
        return None
    ramdisk_sz = boot_info.get("ramdisk_size", 0)
    if ramdisk_sz == 0:
        return None
    page_sz = boot_info.get("page_size", 4096)
    kernel_sz = boot_info.get("kernel_size", 0)
    # Align kernel to page size
    kernel_pages = (kernel_sz + page_sz - 1) // page_sz
    offset = boot_info["kernel_offset"] + (kernel_pages * page_sz)

    ramdisk_path = os.path.join(out_dir, "ramdisk.cpio")
    with open(boot_info["path"], "rb") as f:
        f.seek(offset)
        ramdisk_data = f.read(ramdisk_sz)
    with open(ramdisk_path, "wb") as f:
        f.write(ramdisk_data)
    return ramdisk_path


def detect_ramdisk_type(extracted_dir):
    """
    Detect whether the extracted ramdisk is:
    - recovery (has recovery-specific files)
    - vendor_boot (has vendor ramdisk structure)
    - boot (regular initramfs)
    """
    has_recovery_fstab = any("fstab" in f for f in os.listdir(extracted_dir)) if os.path.isdir(extracted_dir) else False
    has_sbin = os.path.isdir(os.path.join(extracted_dir, "sbin"))
    has_recovery_rc = os.path.isfile(os.path.join(extracted_dir, "init.recovery.rc"))
    has_vendor_prop = os.path.isfile(os.path.join(extracted_dir, "build.prop"))
    has_first_stage = os.path.isdir(os.path.join(extracted_dir, "first_stage_ramdisk"))

    if has_first_stage or has_vendor_prop:
        return "vendor_boot"
    if has_recovery_rc or (has_sbin and has_recovery_fstab):
        return "recovery"
    return "boot"
