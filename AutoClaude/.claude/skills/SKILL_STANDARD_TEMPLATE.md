---
name: skill-name-kebab
description: （動詞開頭）以 {角色} 角色執行 {動作}，在 SDD {階段} 階段產出 {文件}
user-invocable: true
disable-model-invocation: false
argument-hint: "<必填參數> [選填參數]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# {Skill Title}（SDD 原生）

{一句話說明此 Skill 在 SDD 生命週期中的定位，包含對應 SCG 閘門}

---

## 觸發方式

```bash
/{command}                    # 預設執行
/{command} {arg}              # 帶參數執行
```

---

## 前置條件（SDD Spec-First）

> 執行本 Skill 前，下列 SCG 閘門必須已通過：

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-N | {說明} | `/sdd-gate SCG-N` |

> 若閘門尚未通過，請先執行 `/sdd-gate SCG-N` 確認後再繼續。

---

## 執行流程

### 階段 1：{名稱}

1. {步驟說明}
2. {步驟說明}

🔴 **確認點**：{需確認的內容}

---

### 階段 2：{名稱}

1. {步驟說明}
2. {步驟說明}

---

### 階段 N：文件產出與 RTM 更新 🔴

1. 將產出文件存入正確路徑（見「強制產出」）
2. 執行 `/rtm-generate` 更新 RTM 追溯矩陣
3. 執行 `/spec-compliance-check` 驗證文件格式
4. 🔴 確認點：{需人工確認的內容}

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| {文件名} | `docs/{path}/{FILE}-{System}.md` | SCG-N |

---

## 後置動作

完成本 Skill 後：
```
/{next-skill} 或 /sdd-gate SCG-N
```

🔷 **本 Skill 協助通過**：SCG-N（{名稱}）

---

## 相關 Skill

- `/{related}` — {說明}

---

**基於**: AISDLC-SDD v0.30
**對應 Agent**: `{NN}.{role}-zh.yaml`
**對應 SDD Enhancement**: `scenarios/{scenario}/SDD_{SCENARIO}_ENHANCEMENT.md`

---

## 新 Skill 撰寫檢查清單

在提交新 Skill 前，確認以下項目全部完成：

- [ ] 符合「SDD 原生 Skill 新標準結構」
- [ ] 有明確「前置條件（SCG）」表格
- [ ] 執行流程各階段嵌入 SCG/RTM/Spec 步驟（非末尾附加）
- [ ] 所有產出路徑對齊 `docs/` 分層結構
- [ ] 最後步驟包含 `/rtm-generate` + `/spec-compliance-check`
- [ ] 有明確「後置動作」聲明協助通過哪個 SCG
- [ ] `argument-hint` 清楚標示必填/選填參數
- [ ] `allowed-tools` 列表最小化（只列實際使用的工具）
- [ ] description 動詞開頭，含 SDD 關鍵字
