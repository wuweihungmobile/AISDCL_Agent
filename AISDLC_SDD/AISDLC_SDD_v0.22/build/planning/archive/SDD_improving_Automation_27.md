# SDD_improving_Automation_27 — 結案證據強制重推導 hook（DEF-20-001 反幻覺機械閘門）

**主題**：把「反幻覺紀律」（結案宣稱的 pytest passed / commit hash / push / tag 只能來自
真實 repo 狀態，不可編造）由「agent 跨 session 自律」升級為 **AISDLC_SDD 框架機械可驗閘門**。
**徵用**：DEF-20-001（P2, 治理閉環誠信缺口）；無新 R-9.x（見決策 §3）。
**建立日期**：2026-06-16｜**驅動**：AutoSDD_improving_21（軌道① B 軌 dogfooding）
**前置基線**：v0.11 凍結，AutoClaude pytest 3112 / ci-gate 雙軌 exit 0（v0.01:1478 / v0.11:1555 / scripts:25）
**落地版本**：AISDLC_SDD_v0.12（Copy-on-Evolve v0.11→v0.12）

---

## §1 問題（DEF-20-001 根因）

improving_20 曾發生「幻覺工具輸出」事故：前 session 編造整套結案四件套（pytest passed、
commit hash、push 成功、三鏡 PASS、潔淨度數字皆虛構，HEAD 實停 947f1d9）。根因之一：框架
**無任何機制要求結案數字必須由獨立驗證者就當前 repo 真實狀態重新推導後才接受**。反幻覺紀律
僅存於 agent 跨 session 記憶（`no-fabricated-tool-output`）與 `AutoSDD_ZeroTrust_Audit_NN.md`
敘事，**未落為框架 hook/SCG 閘門** → 換 session 仍可能重演。

佐證：`.claude/hooks/`（`session_start.py`/`context_ledger_*`/`post_commit_drift.py`）皆無
「結案宣稱數字 vs repo 真實狀態」交叉核對；SCG-4/5 依賴人工填寫，無機械重推導門。

## §2 提案（落地於 v0.12）

新增 git post-commit advisory hook `closure_evidence_verify.py`（thin）+ 純函式邏輯模組
`closure_evidence.py`，兩層驗證：

- **廉價層（git 事實，永遠真重推導，fail-closed 硬核）**：對 improving_NN.md 末尾
  `closure-evidence` 契約宣稱的 `claimed_commits`/`claimed_tag`，以 `git cat-file -e` +
  `merge-base --is-ancestor` + `rev-parse --verify` 就 monorepo 根真實狀態重推導；任一無法
  重推導 → verdict=FAIL（直擊「編造 commit/push/tag」）。輸入經白名單正則消毒（shell=False）。
- **昂貴層（pytest passed / ci-gate floors，不在 hook budget 重跑）**：驗「綁定當前 HEAD 的
  rederive 證書」（`--rederive` 模式 stamp HEAD 產生）；契約 base_sha != HEAD 或證書缺失/數字
  不符 → INCONCLUSIVE（fail-closed 不綠勾，比照 embodied_grounding 零觀測語意，絕不假綠）。

verdict（VERIFIED / INCONCLUSIVE / FAIL）寫 `.git/CLOSURE_EVIDENCE_VERDICT`（advisory flag，
供 CI / 人複核消費）+ `build/reports/closure/VERDICT-<sha>.yaml`。**永遠 exit 0、<2s budget、
fail-soft、不阻擋 commit**（同 post_commit_drift / Rule 9.17.1 精神；fail-closed 體現在 flag
標記與 CI 消費，非 block commit）。安裝走 `tools/install_hooks/install_post_commit.*`（opt-in，
與 drift hook 串接，不經 settings.json deny 層）。

## §3 決策

- **不新增 R-9.x 治理規則**（舵手 signoff scope = 兩項 W；hook 為 advisory 不需規則承載即可
  運作；開 R-9.39 牽動 RULES_INDEX/ID_REGISTRY 取號與五軌 reachable，同 DEF-10-002「不另開
  R-9.x 而用既有機制」前例 + Rule 2）。治理規則承載 + catch 覆蓋面推進 → routed 未來輪。
- **不動 FSM**：hook 不新增狀態/轉換、不寫 FSM-STATE.yaml → 不觸 `_HAPPY_PATH`/`*.tla` →
  **免五軌 TLC**（Rule 9.18.1 不啟動）。
- **closure verdict 接入 SCG-4/5 機械閘門**（需動 FSM）→ routed 未來輪。

## §4 落地清單（v0.12）

| 構件 | 路徑 |
|------|------|
| 純函式邏輯 | `tools/fsm_runtime/closure_evidence.py` |
| thin hook | `.claude/hooks/closure_evidence_verify.py` |
| 測試（19 case） | `tools/fsm_runtime/tests/test_closure_evidence.py` |
| 安裝腳本串接 | `tools/install_hooks/install_post_commit.{sh,ps1}` |
| 結案契約 schema | `docs/04_planning/AutoSDD_improving_NN.md` 末尾 ```yaml ``closure-evidence`` 區塊 |

## §5 dogfooding 衍生缺陷

- **DEF-21-001**（P3, fixed@improving_21）：improving_NN.md 多 `closure-evidence` yaml 區塊
  （schema 範例 + 真實契約）致解析歧義 → parse 改 last-match（對齊 DEF-02-002 紀律）+ schema
  fence 改 ```text。

## §6 狀態

提案 → 決策（本 RFC）→ 落地 v0.12（improving_21 階段三）→ 驗證（階段四）→ 決策後 archive。
