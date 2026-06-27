# AISDLC-SDD Releases

**用途**: 框架發布包管理目錄
**最後更新**: 2026-04-15

---

## 目錄結構

```
releases/
├── README.md              ← 本文件
├── backups/               ← 升版前備份
└── v0.01/                 ← v0.01 發布包
    ├── RELEASE_NOTES_v0.01.md
    └── [打包後放置 .tar.gz]
```

## 發布流程

升版時依 `AISDLC_SDD_UPGRADE_SOP.md` 階段 4 執行：
1. 建立 `releases/v[NEW]/` 目錄
2. 打包 `AISDLC_SDD_v[NEW]/` 為 `.tar.gz`
3. 生成 SHA256 校驗碼
4. 建立 `RELEASE_NOTES_v[NEW].md`

## 備份說明

升版前的備份放在 `releases/backups/`，命名格式：
```
AISDLC_SDD_v[OLD]_backup_YYYY-MM-DD.tar.gz
```
