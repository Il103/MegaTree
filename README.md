# MegaTree 🔥

**Ultimate Device Tree Generator from Stock ROM Dumps**

MegaTree takes any Android stock ROM dump and automatically generates complete, production-ready device trees, recovery trees (TWRP/OrangeFox/SHRP/PBRP), and vendor trees.

## Features

- **Universal**: Works with any Android device (old or new)
- **Smart Extraction**: erofs → ext4 → sparse → raw (auto-detects)
- **Real Data**: Reads everything from the actual dump — never fabricates values
- **Correct Codenames**: Gets device codename from build.prop automatically
- **DTB Scanner**: Finds and decompiles all DTBs from boot images
- **Multiple Recovery Types**: TWRP, OrangeFox (`ofox_CODENAME.mk`), SHRP, PBRP
- **Full Validation**: Validates fstab, kernel, partitions, props
- **Release Zip**: Packages everything into a ready-to-use zip

## Usage

### Via GitHub Actions (recommended)

1. Go to **Actions** tab
2. Select **MegaTree - Ultimate Device Tree Generator**
3. Click **Run workflow**
4. Enter your ROM dump URL (Git repo or direct download link)
5. Choose recovery type
6. Wait for completion — download the artifact or release

### Local Usage

```bash
# Clone
git clone https://github.com/Il103/MegaTree.git
cd MegaTree

# Full pipeline
python3 run-megatree.py all /path/to/dump --recovery twrp --release ./output

# Generate trees only
python3 run-megatree.py generate /path/to/dump --recovery ofox

# Analyze a dump
python3 run-megatree.py analyze /path/to/dump --json

# Validate dump
python3 run-megatree.py validate /path/to/dump
```

### Recovery Types

| Type | Command | Output File |
|------|---------|-------------|
| TWRP | `--recovery twrp` | `twrp.mk` |
| OrangeFox | `--recovery ofox` | `ofox_CODENAME.mk` |
| SHRP | `--recovery shrp` | `shrp.mk` |
| PBRP | `--recovery pbrp` | `pbrp.mk` |

## Output Structure

```
megatree-output/
├── device_tree/          # BoardConfig.mk, device.mk, props, rootdir
│   ├── BoardConfig.mk
│   ├── device.mk
│   ├── AndroidProducts.mk
│   ├── system.prop / vendor.prop / product.prop
│   ├── manifest.xml
│   ├── extract-files.py / setup-makefiles.py
│   └── rootdir/etc/      # fstab + all init .rc files
├── recovery/             # Recovery tree
│   ├── twrp.mk / ofox_CODENAME.mk
│   ├── twrp.fstab
│   ├── init.recovery.rc
│   └── *.rc              # All device init scripts
└── vendor/               # Vendor tree
    ├── proprietary-files.txt
    ├── BoardConfigVendor.mk
    └── CODENAME-vendor.mk
```

## Requirements

- Python 3.8+
- `erofs-utils`, `e2fsprogs`, `f2fs-tools`, `squashfs-tools`
- `device-tree-compiler` (dtc)
- `android-sdk-libsparse-utils` (simg2img)
