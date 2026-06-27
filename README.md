# ⚡ MegaTree ⚡

> **Zero-effort recovery tree generator for any Android device**

<p align="center">
  <img src="https://img.shields.io/badge/TWRP-✔-red?style=flat-square">
  <img src="https://img.shields.io/badge/OrangeFox-✔-orange?style=flat-square">
  <img src="https://img.shields.io/badge/SHRP-✔-blueviolet?style=flat-square">
  <img src="https://img.shields.io/badge/PBRP-✔-blue?style=flat-square">
  <br>
  <img src="https://img.shields.io/badge/platform-MTK%20%7C%20Qualcomm%20%7C%20Exynos-brightgreen?style=flat-square">
  <img src="https://img.shields.io/badge/Android-8%20→%2015-success?style=flat-square">
  <img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square">
</p>

---

## 🚀 What is MegaTree?

**MegaTree** automatically builds a **complete, buildable recovery tree** from any Android ROM dump.  
Drop in a dump URL — get back a production-ready tree for **TWRP**, **OrangeFox**, **SHRP**, or **PBRP**.

No manual BoardConfig tweaks. No guessing kernel base or cmdline. **Everything comes from the actual dump.**

---

## ✨ Features

| | |
|---|---|
| 🔍 **Smart Analysis** | Parses `build.prop` + `boot.img` headers (v0–v4) to detect device, platform, A/B, kernel params |
| 🎯 **Universal** | Works on **any** device — MTK, Qualcomm, Exynos, old or new |
| ⚡ **Blazing Fast** | Extract partitions → scan DTBs → generate tree in minutes |
| 🛠 **Prebuilt Kernel** | Extracts kernel + DTB + DTBO straight from boot.img |
| 📦 **All Recoveries** | TWRP · OrangeFox · SHRP · PBRP — pick your poison |
| 🌐 **Any Input** | ZIP URLs · Git repos · gofile.io · individual file links |

---

## 📂 Generated Tree Structure

```
📁 megatree-output/manufacturer-codename/
└── 📁 recovery/
    ├── 📄 BoardConfig.mk          ← Kernel base, pagesize, cmdline from actual boot.img
    ├── 📄 twrp_X6886.mk           ← Recovery makefile (codename appended)
    ├── 📄 recovery.fstab           ← Real device fstab
    ├── 📄 init.recovery.rc         ← Init scripts
    ├── 📄 system.prop              ← Device properties
    ├── 📄 vendor.prop              ← Vendor properties
    ├── 📄 manifest.xml             ← VINTF manifest
    ├── 📄 Android.mk               ← Build inclusion
    └── 📁 prebuilt/
        ├── 📄 kernel               ← Stock kernel
        ├── 📄 dtb.img              ← Merged DTB
        └── 📄 dtbo.img             ← DTBO image
```

---

## 🛠 Usage

### CLI

```bash
# Analyze a dump
python3 -m megatree analyze /path/to/dump

# Generate a TWRP tree
python3 -m megatree generate /path/to/dump -r twrp

# Full pipeline: analyze → extract → DTB → generate + release ZIP
python3 -m megatree all /path/to/dump -r ofox --force-extract --release

# Download dump from URL
python3 -m megatree download https://example.com/dump.zip
```

### GitHub Action

1. Navigate to **Actions** → **MegaTree - Recovery Tree Generator**
2. Click **Run workflow**
3. Fill in:
   - `dump_url` — your ROM dump link (Git repo, ZIP, gofile.io)
   - `recovery_type` — `twrp`, `ofox`, `shrp`, or `pbrp`
4. Sit back ☕ — the action downloads, extracts, generates, and uploads the tree as an artifact + release

---

## 🔧 Supported Recoveries

| Recovery | Makefile | Config |
|----------|----------|--------|
| **TWRP** | `twrp_{{CODENAME}}.mk` | Full TWRP config with MTP, crypto, FBE |
| **OrangeFox** | `ofox_{{CODENAME}}.mk` | Fox config with all OF_ flags |
| **SHRP** | `shrp_{{CODENAME}}.mk` | SHRP with dynamic partitions |
| **PBRP** | `pbrp_{{CODENAME}}.mk` | PBRP official config |

---

## 🧠 How It Works

```
Dump URL → Download → Analyze device info
                      ↓
                 Extract partitions (erofs/ext4/sparse)
                      ↓
                 Scan DTBs from boot images
                      ↓
        ┌─────────────┴─────────────┐
        │     Recovery Tree Gen     │
        ├───────────────────────────┤
        │ • BoardConfig.mk          │
        │ • Recovery makefile       │
        │ • fstab from device       │
        │ • Init scripts            │
        │ • Prebuilt kernel + DTB   │
        │ • Props + manifest        │
        └───────────────────────────┘
                      ↓
            ✅ Buildable tree!
```

---

## 🏗 Building the Tree

After MegaTree generates the output, place it in your AOSP source:

```
device/manufacturer/codename/
```

Then build with:

```bash
source build/envsetup.sh
lunch twrp_codename-eng
mka recoveryimage
```

---

## 📜 License

**MIT** — do whatever you want, just don't blame us if your device catches fire 🔥

---

<p align="center">
  <sub>Made with ❤️ for the Android modding community</sub>
</p>
