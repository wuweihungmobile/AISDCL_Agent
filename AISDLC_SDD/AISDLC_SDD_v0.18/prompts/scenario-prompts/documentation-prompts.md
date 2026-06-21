# AISDLC-SDD Documentation 指令集

**情境**: Documentation — SDD 文件維護與 Living Documentation
**版本**: v0.01（SDD 版）
**最後更新**: 2026-04-15

---

## 🚀 標準啟動

```
我需要補齊/維護系統文件，使用 SDD Documentation 情境。

載入：AISDLC_SDD_v0.01/scenarios/documentation/SDD_DOCUMENTATION_ENHANCEMENT.md

目標：
- 系統：[系統名稱]
- 文件需求：[補齊缺失文件 / ADR 回補 / Living Doc 策略 / RTM 補齊]
```

## 📊 階段推進

### 文件盤點
```
請對現有文件進行盤點。

系統路徑：[路徑]
文件目錄：[docs/ 路徑]

盤點項目：
- 已有哪些文件？
- 缺少哪些 SDD 必要文件？（PRD/FRD/SRD/C4/ADR/RTM）
- 哪些文件需要更新？

產出：文件盤點清單（含優先補充建議）
```

### ADR Archaeology（補回架構決策）
```
請執行 ADR Archaeology，補回歷史架構決策。

系統：[名稱]
需要重建的決策記錄：
- 資料庫選型（為什麼選 [DB]？）
- 框架選型（為什麼選 [框架]？）
- [其他關鍵決策]

方法：從代碼/git history/團隊訪談中重建決策脈絡。
```

### Living Documentation 策略
```
請為系統建立 Living Documentation 策略。

系統：[名稱]
當前問題：[文件與代碼脫節/更新頻率低/無人維護]

請產出：docs/05_development/Living-Doc-Strategy-[System].md
包含：
- 哪些文件需要隨代碼更新
- 自動化更新策略
- 維護責任分配
```

### RTM 補齊
```
系統缺少 RTM，請從現有文件重建。

FRD 路徑：[路徑]（若無 FRD，請先逆向建立）
測試案例：[路徑]

目標：建立 F-XXX → TC-XXX 完整追蹤鏈（SCG-5 標準）
```

## 🔄 常見變體

### 快速補 ADR（單一決策）
```
請為以下決策生成 ADR。

決策：[描述]
背景：[為什麼需要做這個決策]
選項：[選項 A / B / C]
決策：[最終選擇和理由]

格式：ADR-[NNN]-[kebab-title].md
存放：docs/02_architecture/adr/
```

### 文檔健康度報告
```
請生成文檔健康度報告。

系統：[名稱]
評估維度：
- 完整性（必要文件是否存在）
- 時效性（文件是否與代碼同步）
- 可追蹤性（RTM 覆蓋率）
- ADR 覆蓋率（主要架構決策是否有記錄）
```
