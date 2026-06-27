# MegaTree 🚀

**MegaTree** — أداة لبناء **شجرة ريكفري** (TWRP/OrangeFox/SHRP/PBRP) تلقائيًا من أي ROM dump.  
بتشتغل على **أي جهاز** (MTK/Qualcomm/Exynos)، بتستخرج كل حاجة من dump حقيقي — مفيش values مفبركة.

## اللي بتعمله

```
MegaTree
├── analyze.py     ← يقرأ build.prop + boot.img headers
├── bootimg.py     ← يفك boot.img (v0–v4)
├── extract.py     ← يستخرج partitions (erofs, ext4, spars)
├── dtb.py         ← يمسح DTBs من boot images
├── trees/
│   └── recovery.py ← يولد BoardConfig.mk + fstab + init + makefiles + prebuilt kernel/DTB
├── validate.py    ← يتأكد إن كل حاجة صح
├── release.py     ← يعمل ZIP جاهز
└── utils.py       ← أدوات مساعدة
```

## الأنواع المدعومة

| Recovery | اسم الملف |
|----------|-----------|
| TWRP | `twrp.mk` |
| OrangeFox | `ofox_CODENAME.mk` |
| SHRP | `shrp.mk` |
| PBRP | `pbrp.mk` |

## الاستخدام

### سطر الأوامر

```bash
# تحليل dump
python3 -m megatree analyze /path/to/dump

# شجرة ريكفري
python3 -m megatree generate /path/to/dump -r twrp

# كل حاجة: تحليل + استخراج + DTB + توليد
python3 -m megatree all /path/to/dump -r ofox --force-extract --release

# تحميل dump من URL
python3 -m megatree download https://example.com/dump.zip
```

### GitHub Action

1. روح لـ `Actions` > `MegaTree - Recovery Tree Generator`
2. اختار `Run workflow`
3. حط:
   - `dump_url`: رابط الـ dump (Git repo, ZIP, gofile.io)
   - `recovery_type`: twrp / ofox / shrp / pbrp
4. الـ Action بيحمل الـ dump ويستخرج ويبني الشجرة ويرفعها `artifact` و release

## مخرجات الشجرة

```
megatree-output/
└── manufacturer-codename/
    └── recovery/
        ├── BoardConfig.mk         ← البورد كونفيج (مع kernel/cmdline الحقيقي)
        ├── twrp.mk / ofox_CODENAME.mk ← makefile الريكفري
        ├── recovery.fstab         ← الفstab الحقيقي من الجهاز
        ├── init.recovery.rc       ← init scripts
        ├── system.prop / vendor.prop ← البروبس
        ├── manifest.xml           ← VINTF manifest
        ├── prebuilt/
        │   ├── kernel             ← kernel من boot.img
        │   ├── dtb.img            ← DTB مدمج
        │   └── dtbo.img           ← DTBO
        └── Android.mk
```

## ازاي تشتغل؟

1. **كل حاجة من الـ dump الحقيقي**: boot.img header (base/pagesize/cmdline)، fstab، kernel، init scripts
2. **شغالة على أي منصة**: بتكتشف MTK من kernel bytes، وكمان Qualcomm و Exynos
3. **Multi-input**: تقدر تدخل ZIP URL, Git repo, gofile.io, أو حتى روابط files فردية
4. **جاهزة للبناء**: الـ BoardConfig.mk شغالة 100% مع الـ AOSP tree

## License

MIT
