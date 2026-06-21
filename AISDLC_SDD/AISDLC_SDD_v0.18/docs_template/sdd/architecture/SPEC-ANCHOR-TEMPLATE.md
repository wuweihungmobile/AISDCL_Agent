# SPEC-ANCHOR-TEMPLATE — 多模態規格錨點 Schema

**ACT**: ACT-031（Phase F M3 D-31.7）
**對應規格**: `build/planning/active/SDD_improving_Automation_05.md` §伍 5.3
**驗證引擎**: `tools/fsm_runtime/multimodal_validator.py`（D-31.1）
**規則庫**: `.claude/skills/spec-logical-validator/rules/SLV-008..011.yaml`

---

## 壹、目的

讓文字規格（FRD / SRD / OpenAPI）能宣告依賴的非文字 artifact（UI mockup / DB schema / C4 diagram），由 multimodal_validator 雙向驗證一致性。

---

## 貳、Anchor 語法

Anchor 為 HTML comment，置於 markdown 規格檔的 AC / 模組 / 端點段落內：

```markdown
<!-- anchor:<modality>:<id> -->
```

| Modality | 對應 artifact | id 慣例 | 範例 |
|----------|--------------|---------|------|
| `ui` | UI mockup（PNG/HTML/Figma export） | PascalCase 畫面名 | `<!-- anchor:ui:LoginScreen -->` |
| `api` | OpenAPI endpoint | `<METHOD> <PATH>` | `<!-- anchor:api:POST /auth/login -->` |
| `db` | DB schema（SQL DDL/YAML） | table 名 | `<!-- anchor:db:users -->` |
| `c4` | C4 diagram component | component 名 | `<!-- anchor:c4:OrderService -->` |

> **驗證器只認 HTML comment**：純文字 `anchor:ui:Foo` 不視為 anchor，避免誤觸。

---

## 參、Anchor target 解析規則

| Modality | target 路徑 | 找不到時 |
|----------|------------|---------|
| `ui:<id>` | `docs/99_media/ui/<kebab-case-of-id>.{png,html,svg,md}`（任一存在即 OK） | `missing_anchor_target` |
| `api:<METHOD> <PATH>` | `docs/02_architecture/api/*.yaml` 內 `paths.<PATH>.<method>` | `missing_anchor_target` |
| `db:<table>` | `docs/07_design/db/schema.sql`（CREATE TABLE）或 `docs/07_design/db/*.yaml`（top-level table 名） | `missing_anchor_target` |
| `c4:<component>` | `docs/02_architecture/C4-*.md` 或 `*.puml` / `*.mmd` 內 component 宣告 | `missing_anchor_target` |

**id → kebab-case 規則**：`LoginScreen` → `login-screen`；`OrderService` → `order-service`；空白替為 `-`。

---

## 肆、Spec 範例

### 4.1 FRD-Auth.md（含 4 種 anchor）

```markdown
## F-010 登入流程

**AC-010-1**: 用戶輸入 Email + 密碼，點擊「登入」後導向首頁。

<!-- anchor:ui:LoginScreen -->
<!-- anchor:api:POST /auth/login -->
<!-- anchor:db:users -->

**AC-010-2**: 連續 5 次失敗鎖定 5 分鐘。
<!-- anchor:db:login_attempts -->
```

### 4.2 SRD-Order.md（C4 anchor）

```markdown
### 模組 OrderService

承接訂單建立、查詢、取消三類業務動作。

<!-- anchor:c4:OrderService -->
```

---

## 伍、驗證流程（multimodal_validator）

```
Step 1  scan markdown for `<!-- anchor:* -->`
Step 2  group by modality
Step 3  for each anchor:
          - resolve target path
          - if missing → emit MissingAnchorTarget
          - else dispatch to {ui, api, db, c4}_adapter
Step 4  adapter returns ConsistencyReport
          {consistent: bool, missing_widget/field/column/component: [...]}
Step 5  collect all reports → MultimodalReport
```

---

## 陸、規則對應（SLV-008~011）

| Rule | Trigger condition | trust_level（M3 起）|
|------|-------------------|----------------|
| SLV-008 | UI anchor 與 FRD AC 不一致 | proposed（advisory）|
| SLV-009 | API anchor 與 UI anchor 操作不對齊 | proposed |
| SLV-010 | DB anchor 與 FRD 資料需求欄位缺漏 | proposed |
| SLV-011 | C4 anchor 與 SRD 模組宣告不對齊 | proposed |

> M4 末 `phase-f-final` 後，使用者可手動 review 升 verified（沿用 ACT-028 / ACT-030 promote 機制）。

---

## 柒、限制（M3/M4 範圍）

- **不支援**：Figma 直連 API（需 token 與外連）— 當前要求使用者 export PNG 後置入 `docs/99_media/ui/`
- **不支援**：影片 / 音訊 anchor
- **支援**的 UI 解析格式：HTML、Markdown widget table、PNG（透過 LLM Backend，僅 claude-api / minimax 可用；session backend 對 PNG 僅檢查檔案存在）

---

## 捌、檔案命名

| 文件類型 | 範例 |
|---------|------|
| UI mockup | `docs/99_media/ui/login-screen.html` 或 `.png` |
| DB schema | `docs/07_design/db/schema.sql`（合併）或 `users.yaml` |
| C4 diagram | `docs/02_architecture/C4-OrderSystem.md`（含內嵌 Mermaid）|
| OpenAPI | `docs/02_architecture/api/auth.yaml` |

---

**作者**: Architect（Phase F 單人 RACI）
**版本**: v1（M3 草案，M4 隨整合驗收同步收斂）
**對應 Issue**: [#2 ACT-031](https://github.com/wuweihungmobile/AISDLC_SDD/issues/2)
