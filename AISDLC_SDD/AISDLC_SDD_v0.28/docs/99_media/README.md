# Media Store — 多模態 Spec artifact 統一存放

**ACT**: ACT-031（Phase F M3 D-31.8）
**對應 Anchor**: [SPEC-ANCHOR-TEMPLATE.md](../../docs_template/sdd/architecture/SPEC-ANCHOR-TEMPLATE.md)
**版本控管**: Git LFS（OPEN-F.4 RESOLVED 2026-04-24）

---

## 用途

放置 FRD / SRD anchor 引用的非文字 artifact：UI mockup、UML 截圖、C4 圖匯出檔、ER 圖、流程圖等。

`multimodal_validator` 會讀取此目錄，與 markdown 規格的 `<!-- anchor:*:* -->` 進行雙向驗證。

---

## 子目錄結構

```
docs/99_media/
├── ui/        # UI mockup（HTML / PNG / SVG / Figma export）
├── flow/      # 流程圖（Mermaid 來源 + PNG）
├── erd/       # ER 圖
└── arch/      # 系統架構圖（已 export 的 C4 PNG）
```

> 所有子目錄使用 **kebab-case** 檔名，對應 anchor id（PascalCase）— 例如 `<!-- anchor:ui:LoginScreen -->` ↔ `ui/login-screen.html`。

---

## 規範

| 項目 | 規則 |
|------|------|
| 檔案大小 | < 500 KB（OPEN-F.4 硬上限），CI warn ≥ 300 KB；強制 lint：[`tools/fsm_runtime/media_size_check.py`](../../tools/fsm_runtime/media_size_check.py)（QA Round-2 P1 補件）|
| 命名 | kebab-case；對應 anchor id 自動轉換（`OrderFlow` → `order-flow`）|
| 格式 | UI: `.html` / `.png` / `.svg`；ERD/C4: `.mmd` / `.puml` / `.png`|
| Git LFS | `*.png` / `*.svg` / `*.jpg` 已自動透過 `.gitattributes` 走 LFS |
| PII | 嚴禁包含真實客戶資料；多模態 LLM backend 呼叫前須經 anonymizer（HUB-GOVERNANCE §4.2）|

---

## CI/CD 對接

`SDD_CICD_BASE_LAYER.md` 的 **Multimodal SpecTrace** step 會：
1. 讀取所有 FRD/SRD 內的 `<!-- anchor:* -->`
2. 對應到 `docs/99_media/<modality>/` 檔案
3. 缺檔即 fail（CI gate）；存在但不一致 → advisory（SLV-008~011 為 proposed trust_level）

---

## 注意

- 此目錄只放**規格用** artifact，不放生產資源（圖示、icons 等請在前端專案維護）
- 大型截圖建議用 `< 800px` 寬度截取，避免 LFS 體積膨脹
- 機密資料（內部網址、Email、客戶名稱）截圖時務必先打碼
