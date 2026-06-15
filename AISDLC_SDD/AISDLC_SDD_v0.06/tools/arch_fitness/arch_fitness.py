#!/usr/bin/env python3
"""arch_fitness — AISDLC-SDD 框架演化式架構適應度函式（Evolutionary Architecture Fitness Functions）。

設計依據（Building Evolutionary Architectures, Ford/Parsons/Kua）：
把「架構特性」轉成**可自動量測、確定性、會回歸**的守門函式，讓架構能隨 AI 演進
而不漂移。本工具是 `workflow/sdd-self-evolution/SDD_SELF_EVOLUTION.md` 動態工作流的
SENSE（感測）與 VERIFY（驗收）量測入口，亦可獨立在 CI / 本機執行。

十七個 fitness function（FF-1~FF-17 全數實作；FF-9 含動態 Scaffold-ROI，其 0-fire 偵測經
runtime 資料門檻啟動。FF 檢查皆唯讀、無網路、無副作用；唯 `--trend` 旗標寫趨勢檔）：

  FF-1  FSM 三源狀態宇宙一致性（roadmap R2：真三源）
        ① transition_rules._HAPPY_PATH ∪ _EMERGENCY_TARGETS（Python，唯一實作真實來源）
           必須等於 formal/SDD_FSM.tla 的 States。
        ② 每個 canonical 狀態必須記載於 SDD_FSM_ENGINE.md（第三源，人類可讀）。
        ③ MD 轉換表來源欄不得含 stale/typo token（advisory）。
        複用 fsm_md_parser（與 test_md_python_sync 共用單一 MD 解析器）。守 Rule 9.18.1。

  FF-2  Governance 漸進揭露遷移健康度（advisory）
        對照 CLAUDE.md 的 `### 9.x` 規則章節數 vs governance/rules/R-*.yaml 已抽出條數。
        量化 Phase H ACT-051「CLAUDE.md ≤1 頁摘要、細節入 registry」設計意圖 vs 現實的
        差距。永遠 advisory（遷移為漸進式，不阻擋）。

  FF-3  孤兒 / 損毀 FSM 持久化檔偵測
        掃描 build/reports/fsm/，找出洩漏的 *.tmp / *.bak.tmp、巢狀重複路徑垃圾檔
        （例：FSM-STATE-build/reports/fsm/...yaml.yaml.tmp）、以及 PyYAML 解析失敗的
        state 檔。守 state_loader.save_state 的 P2-08 reap 契約不被路徑誤用繞過。

  FF-4  觀測態分類跨源同位（parity）
        transition_rules.OBSERVATION_STATES（Python）vs SDD_FSM.tla ObservationStates。
        並驗 OBSERVATION_STATES 與 Terminals / _EMERGENCY_TARGETS 互斥（Rule 9.18.4 鏡像）。
        集合差異預設 advisory（可能為刻意設計，如 AUTO_RECOVERY_ATTEMPT），但與 Terminals
        相交則為 structural fail。

  FF-5  CLAUDE.md Rule 9 區塊頁數守門 + 憲法摘要引用完整性（Phase 2 2b）
        §9 區塊 ≤1.2 頁（advisory warn），且摘要引用的 R-9.x 必須存在（structural fail）。

  FF-6  文件相對連結完整性（roadmap R3，advisory）
        掃描 AISDLC_SDD_INIT.md + workflow/**/*.md 的 markdown 相對連結，偵測死連結。
        每條死連結獨立穩定 fingerprint，使 SELF_EVOLUTION 收斂閘可逐條單調遞減。

  FF-7  Agent↔Workflow↔Skill 引用健康度（advisory）
        (a) INIT.md 數量摘要宣稱 vs 磁碟實況的漂移；(b) auto_load_config 的 quoted
        相對 path 引用完整性。守 measurement blindness 與單一真實來源。

  FF-8  Governance 規則 → 強制執行測試 可追溯性（roadmap R7）
        閉環健全性的前提：每條 active 治理規則（governance/rules/R-*.yaml）都必須接上
        一個確實會停機的測試（`test_ref`）。本 FF 守三道 structural 不變量 + 一道
        advisory：①缺 test_ref（fail，critical guard 無宣告強制 = governance theater）
        ②test_ref dangling（fail，指向磁碟不存在的測試 = 改名/刪除漂移使強制失效）
        ③test_ref 無 `def test_`（fail，指向非測試/stub）④強制測試未反向引用規則 id
        （advisory，rule→test 單向、缺可 grep 錨點）。守 SELF_EVOLUTION 自陳的根因
        脆弱點「治理規則本身的熵增無收斂閘」，並使「圖靈完備閉環」的每條 guard ↔
        halting test 連結可被靜態稽核（呼應 Rule 9.18 形式化停機驗證精神）。

  FF-10 Governance 規則 trigger_states 可達性（死規則偵測，roadmap R8）
        一條規則只有在 FSM 進入其 trigger_states 之一時才會被 rule_loader 注入。若 trigger
        指向不存在於 39 態 canonical 宇宙的「幽靈狀態」（typo / 狀態改名/移除未同步）或
        trigger_states 為空，該規則永不觸發 = 死規則（規則存在卻從不生效，governance theater
        的另一變體）。structural fail。與 FF-1 互補：FF-1 守宇宙本身三源一致，FF-10 守
        「規則 → 宇宙」的引用完整。（FF-9 預留給動態 Scaffold-ROI，不在此靜態工具範圍。）

  FF-11 Skill frontmatter 結構完整性（roadmap R9）
        42 個 .claude/skills/<name>/SKILL.md 是框架能力的調用入口；harness 靠其 YAML
        frontmatter 的 name/description 註冊與顯示 skill。若某 SKILL.md 缺 frontmatter，
        harness 只能退化成佔位字串（Skill 層 measurement blindness：skill 存在卻無法被
        正確識別/調用）。structural fail。注意：name≠目錄名為刻意短別名設計
        （ba-analyst→ba-validate 等），故不檢查 name-vs-dir 相等以免假陽性。

  FF-12 critical 規則治理錯置（severity↔trigger 一致性，roadmap R10）
        severity=critical = CLAUDE.md「違反即停機」。但 OBSERVATION_STATES 為非阻塞瞬態
        觀測窗（Rule 9.17.2 等）；critical 規則若 trigger ⊆ OBSERVATION_STATES，則它只在
        非阻塞窗觸發、永遠無法真正停機 = critical-in-name-only 的治理錯置。structural fail。
        （§7.2 草擬版「critical 必掛 happy-path」會誤報 R-9.5/R-9.14——刻意掛 ESCALATION/
        TERMINATED 緊急態正是其關鍵性所在——故精煉為「critical 不得 observation-only」。）

  FF-13 Agent YAML schema 完整性（roadmap R11，advisory）
        25 個 agent/**/*.yaml 是 Runtime 依 auto_load_config 載入的能力定義。agent 由
        Runtime/LLM 以「文字」載入，故嚴格 YAML 失效不會即時崩潰——這正是 Agent 層
        measurement blindness：縮排錯置、誤插 `---`、未引號特殊字元會讓檔案非嚴格合法卻
        無人察覺。FF-13 以 safe_load_all 掃描，聚合回報非嚴格合法檔 + 缺頂層 agent 鍵。
        永遠 advisory（agent 為核心 artifact，修復走 Rule 8 人工閘，不阻擋收斂；鏡像 FF-2
        漸進式哲學）。與 FF-11（Skill 層）對稱，補齊「能力定義層」的結構守門。

  FF-9  Scaffold-ROI 代謝（roadmap R14；structural schema + data-gated 0-fire advisory）
        每條 active 規則須有完整 scaffold_roi 計數基座（fire/catch/false_positive 三整數，
        structural fail）——Rule 9.20 GAE / sdd-gc 退役過時鷹架的資料底層。動態部分：當全
        系統 aggregate fire_count ≥ 門檻（env SDD_FF9_STALE_MIN_AGGREGATE，預設 20）時，對
        長期 0-fire 規則發 advisory（過時鷹架候選）；資料不足則 gate 關閉、不誤報，隨 runtime
        累積自動啟動。

  FF-14 CI workflow → 工具模組引用一致性（roadmap R13）
        .github/workflows/*.yml 以 `python -m tools.*` 呼叫的**專案**模組必須可解析；改名/
        移除未同步會讓 CI step runtime 失敗（structural fail）。僅驗 `tools.*` 自有命名空間，
        pip / pytest 等外部工具略過以免假陽性。與 FF-6/FF-7 同屬「引用完整性」家族延伸至 CI 層。

  FF-15 docs_template 索引 ↔ 磁碟一致性（roadmap R15）
        INIT.md「SDD 模板索引」是 docs_template（框架第三大 artifact 家族）的導覽樞紐。
        (A) 索引引用的模板必須在磁碟存在（structural fail，dangling = 場景複製靜默失敗，與
        FF-7/10/14 引用完整性家族同源）；(B) 索引宣稱數 / 涵蓋面 vs 磁碟漂移（advisory，未索引
        模板 = 樞紐量測盲區，鏡像 FF-7 數量漂移）。與 FF-11（Skill）/ FF-13（Agent）對稱，補齊
        artifact 三支柱結構守門。

  FF-16 具身評估器 & 鷹架代謝工具鏈接地完整性（Phase X / roadmap R16）
        Phase H（ACT-045~055）已建好具身評估器（sdd-evaluator + sandbox_runner + observability_query
        + output_quality_scorer + EXECUTION_EVALUATION）與常駐鷹架 GC（sdd-gc + scaffold_gc +
        SCAFFOLD_GC），但 Phase L~W 近 8 個 meta phase 的自我演化全押在合成算子代數，使這條具身鏈
        在元迴圈層被晾置、GC 0-fire。
        (A) structural fail — sdd-evaluator / sdd-gc 宣告依賴的 runtime 模組必須在磁碟存在，且其綁定的
            FSM 狀態（EXECUTION_EVALUATION / SCAFFOLD_GC）必須存在於 canonical 宇宙；dangling = 具身/
            代謝能力 governance-theater（與 FF-7/10/14/15 引用完整性家族同源）。
        (B) advisory — 元迴圈生成器零引用具身工具鏈（GAP-X1 未接地）、GC 從未產出退役提案（GAP-X2 代謝
            肌肉從未收縮）；把病灶轉為被追蹤 backlog（鏡像 FF-2/9/13 漸進哲學，不阻擋收斂）。

  FF-17 Copy-on-Evolve 演化版必納官方閘門（DEF-10-002b 固化；引用完整性家族延伸）
        DEF-03-001 曾發現官方閘門 scripts/ci-gate.sh FW_DIR 寫死 v0.01 → 演化版從不進 CI；
        improving_04 以「凍結基線 + 自動偵測最新版」雙軌點修。本 FF 把該不變量固化為結構守門：
        斷言 ci-gate.sh 含動態最新版偵測慣用語（ls -d AISDLC_SDD_v0.0* | sort -V | tail -1 併入
        FW_VERSIONS）→ 最新演化版恆被官方閘門涵蓋；退回靜態寫死 = structural fail（DEF-03-001
        回歸）。與 FF-14 同源：靜態讀 CI 腳本文字、純讀無副作用、跨平台（不執行 shell）。

退出碼語意（呼應框架 advisory vs blocking 哲學，Rule 9.11.3）：
  0  全通過（含 advisory 警告）
  1  有 advisory 警告（CI 仍視為綠；--strict 不影響 warn）
  2  有 structural 失敗（FF-1 不一致 / FF-3 孤兒 / FF-4 ∩Terminals / FF-8 規則無有效強制測試 /
     FF-9 scaffold_roi 基座缺漏 / FF-10 死規則 / FF-11 skill frontmatter 不全 /
     FF-12 critical 規則錯置 / FF-14 workflow 引用不存在的工具模組 / FF-15 索引引用不存在的模板 /
     FF-16 具身/代謝 agent 宣告的 runtime 模組或 FSM 狀態不存在 /
     FF-17 官方閘門未動態涵蓋最新演化版〔DEF-03-001 回歸〕）；
     唯 --strict 時回傳
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# 路徑解析（檔案位置：<framework>/tools/arch_fitness/arch_fitness.py）
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
FRAMEWORK_ROOT = _THIS.parents[2]          # AISDLC_SDD_v0.01/
PROJECT_ROOT = _THIS.parents[3]            # 專案根（CLAUDE.md 所在）
TLA_PATH = FRAMEWORK_ROOT / "tools" / "fsm_runtime" / "formal" / "SDD_FSM.tla"
FSM_MD_PATH = FRAMEWORK_ROOT / "workflow" / "sdd-fsm-engine" / "SDD_FSM_ENGINE.md"
GOV_RULES_DIR = FRAMEWORK_ROOT / "governance" / "rules"
FSM_STATE_DIR = FRAMEWORK_ROOT / "build" / "reports" / "fsm"
# FF-17：官方 CI 閘門腳本（PROJECT_ROOT＝CLAUDE.md 所在＝AISDLC_SDD/，scripts/ 為 versioned
# 目錄外的共享 CI infra，免 Copy-on-Evolve；DEF-03-001 雙軌修復即落於此）。
CI_GATE_PATH = PROJECT_ROOT / "scripts" / "ci-gate.sh"

# 確保可 import tools.fsm_runtime（namespace package，repo root 需在 sys.path）
if str(FRAMEWORK_ROOT) not in sys.path:
    sys.path.insert(0, str(FRAMEWORK_ROOT))

SEVERITY_INFO = "info"
SEVERITY_WARN = "warn"
SEVERITY_FAIL = "fail"


@dataclass
class Finding:
    ff: str                       # 適應度函式代碼，如 "FF-1"
    severity: str                 # info / warn / fail
    fingerprint: str              # 收斂偵測用的穩定指紋（同一問題跨輪相同）
    title: str
    detail: str
    evidence: List[str] = field(default_factory=list)


@dataclass
class FitnessReport:
    findings: List[Finding] = field(default_factory=list)

    def add(self, f: Finding) -> None:
        self.findings.append(f)

    @property
    def fails(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == SEVERITY_FAIL]

    @property
    def warns(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == SEVERITY_WARN]

    def score(self) -> int:
        """加權缺陷分數：fail=10、warn=1。收斂閘以此單調遞減判定（越低越健康）。"""
        return 10 * len(self.fails) + len(self.warns)


# ---------------------------------------------------------------------------
# TLA 集合解析
# ---------------------------------------------------------------------------
def _parse_tla_set(tla_text: str, name: str) -> Set[str]:
    """擷取 `Name == { "A", "B", ... }` 中所有大寫狀態 token。

    這些集合不含巢狀 brace，故以非貪婪 DOTALL 擷取首個 {...} 即可。
    """
    m = re.search(rf"{name}\s*==\s*\{{(.*?)\}}", tla_text, re.DOTALL)
    if not m:
        return set()
    return set(re.findall(r'"([A-Z_]+)"', m.group(1)))


def _tla_state_universe(tla_text: str) -> Dict[str, Set[str]]:
    return {
        "HappyStates": _parse_tla_set(tla_text, "HappyStates"),
        "ObservationStates": _parse_tla_set(tla_text, "ObservationStates"),
        "EmergencyStates": _parse_tla_set(tla_text, "EmergencyStates"),
        "Terminals": _parse_tla_set(tla_text, "Terminals"),
    }


# ---------------------------------------------------------------------------
# FF-1：FSM 三源狀態宇宙一致性
# ---------------------------------------------------------------------------
def check_ff1_fsm_state_universe(report: FitnessReport) -> None:
    try:
        from tools.fsm_runtime import transition_rules as tr  # type: ignore
    except Exception as exc:  # pragma: no cover - import 防護
        report.add(Finding(
            ff="FF-1", severity=SEVERITY_FAIL, fingerprint="ff1-import",
            title="無法 import transition_rules",
            detail=f"Python 真實來源不可載入：{exc}",
        ))
        return

    py_states: Set[str] = set(tr._HAPPY_PATH.keys()) | set(tr._EMERGENCY_TARGETS)

    if not TLA_PATH.exists():
        report.add(Finding(
            ff="FF-1", severity=SEVERITY_FAIL, fingerprint="ff1-no-tla",
            title="找不到 SDD_FSM.tla",
            detail=f"預期路徑不存在：{TLA_PATH}",
        ))
        return

    tla_sets = _tla_state_universe(TLA_PATH.read_text(encoding="utf-8"))
    tla_states: Set[str] = set().union(*tla_sets.values()) if any(tla_sets.values()) else set()

    only_py = sorted(py_states - tla_states)
    only_tla = sorted(tla_states - py_states)
    two_source_ok = not only_py and not only_tla
    if not two_source_ok:
        report.add(Finding(
            ff="FF-1", severity=SEVERITY_FAIL, fingerprint="ff1-mismatch",
            title="FSM 狀態宇宙不一致（破 Rule 9.18.1）",
            detail="Python _HAPPY_PATH∪_EMERGENCY_TARGETS 與 SDD_FSM.tla States 不相等。",
            evidence=[
                f"僅存在於 Python：{only_py or '—'}",
                f"僅存在於 TLA  ：{only_tla or '—'}",
            ],
        ))

    # R2：第三源 SDD_FSM_ENGINE.md —— 由雙源升級為真三源一致性。
    md_clean = _check_ff1_md_third_source(report, py_states)

    if two_source_ok and md_clean:
        report.add(Finding(
            ff="FF-1", severity=SEVERITY_INFO, fingerprint="ff1-ok",
            title=f"FSM 三源狀態宇宙一致（{len(py_states)} 態：Python ⇄ TLA ⇄ MD）",
            detail="transition_rules ∪ == SDD_FSM.tla States；且全部狀態均見於 "
                   "SDD_FSM_ENGINE.md、轉換表來源欄無 stale token。守 Rule 9.18.1 三源一致性。",
        ))


def _check_ff1_md_third_source(report: FitnessReport, py_states: Set[str]) -> bool:
    """R2：以 SDD_FSM_ENGINE.md 為第三源做一致性檢查，回傳是否完全乾淨。

    複用 `fsm_md_parser`（與 test_md_python_sync 共用的單一 MD 解析器），不另寫
    第二份 parser——那本身就是 FF-1 型（多源手動同步）脆弱點。
    """
    if not FSM_MD_PATH.exists():
        report.add(Finding(
            ff="FF-1", severity=SEVERITY_WARN, fingerprint="ff1-no-md",
            title="找不到 SDD_FSM_ENGINE.md（降級為雙源比對）",
            detail=f"預期路徑不存在：{FSM_MD_PATH}。",
        ))
        return False
    try:
        from tools.fsm_runtime import fsm_md_parser as mp  # type: ignore
        md_src = mp.md_source_states(FSM_MD_PATH)
    except Exception as exc:  # pragma: no cover - 解析防護
        report.add(Finding(
            ff="FF-1", severity=SEVERITY_FAIL, fingerprint="ff1-md-parse",
            title="SDD_FSM_ENGINE.md 狀態轉換表解析失敗",
            detail=f"fsm_md_parser 無法解析：{exc}",
        ))
        return False

    text = FSM_MD_PATH.read_text(encoding="utf-8")
    clean = True

    # (1) 覆蓋（structural fail）：每個 canonical 狀態必須在 MD 有記載（文字提及即可，
    #     避免終態 / 抽象來源造成假陽性）。
    undocumented = sorted(s for s in py_states if s not in text)
    if undocumented:
        report.add(Finding(
            ff="FF-1", severity=SEVERITY_FAIL, fingerprint="ff1-md-undocumented",
            title=f"{len(undocumented)} 個狀態在 Python/TLA 但 SDD_FSM_ENGINE.md 未記載",
            detail="三源破口：MD 為人類可讀第三源，canonical 狀態缺漏會誤導讀者並破 "
                   "Rule 9.18.1；新增狀態時須同步補進 MD。",
            evidence=undocumented,
        ))
        clean = False

    # (2) 來源欄有效性（advisory warn）：轉換表來源欄 token 應全為真實狀態。
    #     來源欄結構單一、噪音低，故僅查來源欄（避免 dst 複合 cell 假陽性）。
    stale = sorted(md_src - py_states)
    if stale:
        report.add(Finding(
            ff="FF-1", severity=SEVERITY_WARN, fingerprint="ff1-md-stale-source",
            title=f"MD 轉換表來源欄含 {len(stale)} 個非真實狀態 token",
            detail="來源欄出現不存在於 Python/TLA 的狀態（stale/typo）；建議校正或補狀態。",
            evidence=stale,
        ))
        clean = False

    return clean


# ---------------------------------------------------------------------------
# FF-2：Governance 漸進揭露遷移健康度（advisory）
# ---------------------------------------------------------------------------
def check_ff2_governance_migration(report: FitnessReport) -> None:
    claude_md = PROJECT_ROOT / "CLAUDE.md"
    if not claude_md.exists():
        # 不視為失敗：某些部署可能無 root CLAUDE.md
        report.add(Finding(
            ff="FF-2", severity=SEVERITY_INFO, fingerprint="ff2-no-claudemd",
            title="略過 governance 遷移檢查",
            detail=f"未找到 {claude_md}（可能為下游採用情境）。",
        ))
        return

    text = claude_md.read_text(encoding="utf-8")
    sections = sorted(set(re.findall(r"^###\s+9\.(\d+)\b", text, re.MULTILINE)),
                      key=lambda s: int(s))
    n_sections = len(sections)

    extracted = sorted(GOV_RULES_DIR.glob("R-*.yaml")) if GOV_RULES_DIR.exists() else []
    n_extracted = len(extracted)

    # Phase 2 2c 後：CLAUDE.md §9 已裁剪為憲法摘要、不再有 `### 9.x` 編號子標題
    # → 分母歸零。此時 registry 即權威來源；§9 頁數/引用完整性改由 FF-5 守門。
    if n_sections == 0:
        report.add(Finding(
            ff="FF-2", severity=SEVERITY_INFO, fingerprint="ff2-coverage",
            title=f"CLAUDE.md §9 已裁剪；registry 權威持有 {n_extracted} 條規則",
            detail=(
                "Phase 2 2c 完成：CLAUDE.md §9 不再 eager-load 編號子規則，細節以 "
                "governance/rules/R-*.yaml 為權威來源、由 rule_loader 逐態注入。"
                "§9 頁數與引用完整性改由 FF-5 守門。"
            ),
            evidence=[f"已抽出 R-*.yaml：{n_extracted} 檔"],
        ))
        return

    coverage = (n_extracted / n_sections) if n_sections else 1.0
    # 粗估 Rule 9 區塊的「頁數」：以 9.1 第一個標題到檔尾的字元數 / 3000 字元每頁。
    first = re.search(r"^###\s+9\.1\b", text, re.MULTILINE)
    rule9_chars = len(text) - (first.start() if first else len(text))
    approx_pages = round(rule9_chars / 3000, 1)

    severity = SEVERITY_WARN if coverage < 0.5 else SEVERITY_INFO
    if coverage >= 1.0:
        # Phase 1（抽取）完成 — 但 CLAUDE.md 是否已裁剪是 Phase 2 的獨立關注點。
        detail = (
            f"Phase 1 抽取完成：CLAUDE.md 全部 {n_sections} 條 Rule 9.x 已遷入 "
            f"governance/rules/R-*.yaml（共 {n_extracted} 檔，含 R-SELF-STRIDE），"
            "由 test_rules_index_sync.py 守同步。"
            f"Phase 2（待辦，advisory）：CLAUDE.md Rule 9 區塊約 {approx_pages} 頁仍為權威全文、"
            "尚未裁剪為 ≤1 頁摘要 + registry 指標；該裁剪動到 always-loaded 指令檔，"
            "須獨立 PR 謹慎 review 後執行。"
        )
    else:
        detail = (
            "Phase H ACT-051 設計：CLAUDE.md 應僅留 ≤1 頁禁令摘要，Rule 9.x 細節遷入 "
            "governance/rules/R-*.yaml 由 rule_loader 依狀態 lazy-load。"
            f"目前 CLAUDE.md Rule 9 區塊約 {approx_pages} 頁，"
            "仍 eager-load 全文，與設計意圖偏離。建議由 SELF_EVOLUTION 工作流逐條抽出。"
        )
    report.add(Finding(
        ff="FF-2", severity=severity, fingerprint="ff2-coverage",
        title=f"Governance 抽取覆蓋率 {coverage:.0%}"
              f"（{n_extracted} 檔 / {n_sections} 條 Rule 9.x）",
        detail=detail,
        evidence=[
            f"CLAUDE.md `### 9.x` 章節：{n_sections} 條",
            f"已抽出 R-*.yaml：{n_extracted} 檔",
        ],
    ))


# ---------------------------------------------------------------------------
# FF-3：孤兒 / 損毀 FSM 持久化檔偵測
# ---------------------------------------------------------------------------
def check_ff3_orphan_state_files(report: FitnessReport) -> None:
    if not FSM_STATE_DIR.exists():
        report.add(Finding(
            ff="FF-3", severity=SEVERITY_INFO, fingerprint="ff3-no-dir",
            title="FSM state 目錄不存在", detail=f"{FSM_STATE_DIR}（首次執行前正常）。",
        ))
        return

    orphans: List[str] = []
    nested: List[str] = []
    corrupt: List[str] = []

    for p in sorted(FSM_STATE_DIR.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(FSM_STATE_DIR).as_posix()
        name = p.name
        # 洩漏的暫存檔（save_state 正常路徑應 reap）
        if name.endswith(".tmp") or name.endswith(".bak.tmp"):
            orphans.append(rel)
            continue
        # 巢狀重複路徑垃圾（project 被誤傳整段路徑造成）
        if "FSM-STATE-build" in name or ".yaml.yaml" in name or "/" in rel.split("/", 1)[-1] and "FSM-STATE-" in rel and rel.count("FSM-STATE-") > 1:
            nested.append(rel)
            continue

    # 巢狀偵測補強：任何含重複 FSM-STATE- 片段者
    for p in sorted(FSM_STATE_DIR.rglob("FSM-STATE-*")):
        rel = p.relative_to(FSM_STATE_DIR).as_posix()
        if rel.count("FSM-STATE-") > 1 and rel not in nested:
            nested.append(rel)

    # 損毀 state 檔（排除 TEMPLATE、.bak、.tmp）
    try:
        from tools.fsm_runtime.state_loader import _classify_state_file  # type: ignore
        for p in sorted(FSM_STATE_DIR.glob("FSM-STATE-*.yaml")):
            if "TEMPLATE" in p.name:
                continue
            doc, reason = _classify_state_file(p)
            if doc is None:
                corrupt.append(f"{p.name} ({reason})")
    except Exception:  # pragma: no cover
        pass

    if not orphans and not nested and not corrupt:
        report.add(Finding(
            ff="FF-3", severity=SEVERITY_INFO, fingerprint="ff3-ok",
            title="無孤兒 / 損毀 FSM 持久化檔",
            detail="build/reports/fsm/ 乾淨；save_state reap 契約完整。",
        ))
        return

    if orphans:
        report.add(Finding(
            ff="FF-3", severity=SEVERITY_FAIL, fingerprint="ff3-orphan-tmp",
            title=f"偵測到 {len(orphans)} 個洩漏暫存檔（.tmp/.bak.tmp）",
            detail="save_state 的 P2-08 reap 僅清當前 target 路徑；路徑誤用會留下無法回收的孤兒。",
            evidence=orphans,
        ))
    if nested:
        report.add(Finding(
            ff="FF-3", severity=SEVERITY_FAIL, fingerprint="ff3-nested-path",
            title=f"偵測到 {len(nested)} 個巢狀重複路徑垃圾檔",
            detail="project 參數被誤傳為整段相對路徑，使 _default_state_path 產生巢狀檔名。",
            evidence=nested,
        ))
    if corrupt:
        report.add(Finding(
            ff="FF-3", severity=SEVERITY_FAIL, fingerprint="ff3-corrupt",
            title=f"偵測到 {len(corrupt)} 個無法解析的 state 檔",
            detail="PyYAML 無法解析；恢復需走 .bak fallback（Rule 9.9.3）。",
            evidence=corrupt,
        ))


# ---------------------------------------------------------------------------
# FF-4：觀測態分類跨源同位
# ---------------------------------------------------------------------------
# 已知刻意分歧的允許清單（避免 advisory 噪音）。新增者須附理由。
FF4_INTENTIONAL_DIVERGENCE: Dict[str, str] = {
    "AUTO_RECOVERY_ATTEMPT":
        "TLA 視為 observation（1-shot bounded window）；Python OBSERVATION_STATES 未列入，"
        "因其受 recovery 計數有界治理而非純觀測。屬已知設計分歧，advisory 追蹤。",
}


def check_ff4_observation_parity(report: FitnessReport) -> None:
    try:
        from tools.fsm_runtime import transition_rules as tr  # type: ignore
    except Exception as exc:  # pragma: no cover
        report.add(Finding(
            ff="FF-4", severity=SEVERITY_FAIL, fingerprint="ff4-import",
            title="無法 import transition_rules", detail=str(exc),
        ))
        return

    py_obs: Set[str] = set(tr.OBSERVATION_STATES)
    emergency: Set[str] = set(tr._EMERGENCY_TARGETS)

    if not TLA_PATH.exists():
        return
    tla_sets = _tla_state_universe(TLA_PATH.read_text(encoding="utf-8"))
    tla_obs = tla_sets["ObservationStates"]
    terminals = tla_sets["Terminals"]

    # 硬規則：觀測態不可與 Terminals / Emergency 相交（Rule 9.18.4）
    bad_terminal = sorted(py_obs & terminals)
    bad_emergency = sorted(py_obs & emergency)
    if bad_terminal or bad_emergency:
        report.add(Finding(
            ff="FF-4", severity=SEVERITY_FAIL, fingerprint="ff4-invariant",
            title="觀測態與 Terminal/Emergency 集合相交（破 Rule 9.18.4）",
            detail="OBSERVATION_STATES 必須與吸收態 / 阻塞態互斥。",
            evidence=[f"∩Terminals={bad_terminal}", f"∩Emergency={bad_emergency}"],
        ))

    # 軟規則：跨源集合差異（扣除允許清單）
    raw_only_tla = (tla_obs - py_obs)
    raw_only_py = (py_obs - tla_obs)
    only_tla = sorted(s for s in raw_only_tla if s not in FF4_INTENTIONAL_DIVERGENCE)
    only_py = sorted(s for s in raw_only_py if s not in FF4_INTENTIONAL_DIVERGENCE)
    allowed = sorted((raw_only_tla | raw_only_py) & set(FF4_INTENTIONAL_DIVERGENCE))

    if only_tla or only_py:
        report.add(Finding(
            ff="FF-4", severity=SEVERITY_WARN, fingerprint="ff4-parity",
            title="觀測態跨源分類分歧（未列入允許清單）",
            detail="Python OBSERVATION_STATES 與 TLA ObservationStates 不一致；"
                   "請確認是刻意設計（補入允許清單）或漏同步（補齊集合）。",
            evidence=[f"僅 TLA：{only_tla or '—'}", f"僅 Python：{only_py or '—'}"],
        ))
    elif not (bad_terminal or bad_emergency):
        report.add(Finding(
            ff="FF-4", severity=SEVERITY_INFO, fingerprint="ff4-ok",
            title=f"觀測態分類同位通過（{len(py_obs)} 態 + {len(allowed)} 已知分歧）",
            detail=f"Terminal/Emergency 互斥成立；已知分歧：{allowed or '無'}。",
        ))


# ---------------------------------------------------------------------------
# FF-5：CLAUDE.md Rule 9 區塊頁數守門 + 憲法摘要引用完整性（Phase 2 2b）
# ---------------------------------------------------------------------------
FF5_PAGE_BUDGET = 1.2  # ≤1 頁目標，留 0.2 容忍


def _rule9_block(text: str) -> Optional[str]:
    """擷取 CLAUDE.md 的 `## Rule 9` level-2 區塊（到下一個 level-2 標題為止）。"""
    heads = list(re.finditer(r"^##\s+.*$", text, re.MULTILINE))
    for i, m in enumerate(heads):
        if "Rule 9" in m.group(0):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
            return text[m.start():end]
    return None


def check_ff5_claudemd_rule9_size(report: FitnessReport) -> None:
    claude_md = PROJECT_ROOT / "CLAUDE.md"
    if not claude_md.exists():
        report.add(Finding(
            ff="FF-5", severity=SEVERITY_INFO, fingerprint="ff5-no-claudemd",
            title="略過 CLAUDE.md §9 頁數檢查", detail=f"未找到 {claude_md}。",
        ))
        return
    block = _rule9_block(claude_md.read_text(encoding="utf-8"))
    if block is None:
        report.add(Finding(
            ff="FF-5", severity=SEVERITY_INFO, fingerprint="ff5-no-section",
            title="CLAUDE.md 無 Rule 9 區塊", detail="找不到 `## Rule 9` level-2 標題。",
        ))
        return

    pages = round(len(block) / 3000, 1)

    # 引用完整性：憲法摘要提到的 R-9.x 必須存在對應規則檔（裁剪後才會有 R- 引用）。
    referenced = sorted(set(re.findall(r"R-9\.\d+", block)))
    missing = [ref for ref in referenced
               if not list(GOV_RULES_DIR.glob(f"{ref}-*.yaml"))]
    if missing:
        report.add(Finding(
            ff="FF-5", severity=SEVERITY_FAIL, fingerprint="ff5-dangling-ref",
            title=f"CLAUDE.md §9 引用 {len(missing)} 條不存在的規則",
            detail="憲法摘要引用的 R-9.x 必須在 governance/rules/ 有對應檔。",
            evidence=missing,
        ))

    if pages > FF5_PAGE_BUDGET:
        report.add(Finding(
            ff="FF-5", severity=SEVERITY_WARN, fingerprint="ff5-oversize",
            title=f"CLAUDE.md §9 約 {pages} 頁 > {FF5_PAGE_BUDGET} 頁目標",
            detail=(
                "Phase 2 2c 待裁剪：Rule 9 區塊仍為 eager-load 全文。"
                "細節已在 governance/rules/R-*.yaml，建議裁剪為 ≤1 頁憲法摘要 + registry 指標"
                "（見 build/planning/active/PHASE2-CLAUDEMD-TRIM-PLAN.md）。"
            ),
            evidence=[f"區塊約 {len(block)} 字元 ≈ {pages} 頁"],
        ))
    else:
        report.add(Finding(
            ff="FF-5", severity=SEVERITY_INFO, fingerprint="ff5-ok",
            title=f"CLAUDE.md §9 已精簡（≈{pages} 頁 ≤ {FF5_PAGE_BUDGET}）",
            detail=f"憲法摘要引用 {len(referenced)} 條 R-9.x，全部存在。",
        ))


# ---------------------------------------------------------------------------
# FF-6：文件相對連結完整性（roadmap R3）
# ---------------------------------------------------------------------------
# 掃描導覽骨幹（INIT.md + workflow/**/*.md）的 markdown 相對連結，偵測死連結。
# 一條死連結 = 下游 agent 依 INIT 載入時的隱形失敗點。永遠 advisory（warn），
# 每條死連結一個獨立穩定 fingerprint，使 SELF_EVOLUTION 收斂閘可逐條單調遞減。
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
# 跳過：外部 URL / 純錨點 / mailto / 協定相對
_SKIP_LINK_PREFIXES = ("http://", "https://", "mailto:", "tel:", "//", "#")
# 含 glob / 模板佔位符的連結是示意用法，非真實路徑
_LINK_TEMPLATE_CHARS = ("*", "{", "}", "<", ">", "$")


def _fp(*parts: str) -> str:
    """跨輪穩定指紋（同一 (來源, 目標) 永遠相同）。"""
    return hashlib.sha1("::".join(parts).encode("utf-8")).hexdigest()[:8]


def _strip_code_fences(md_text: str) -> str:
    """移除 ``` / ~~~ fenced code 區塊（含縮排 fence）。

    fence 內的 markdown 連結是教學/範例內容（如 workflow 指南示範產出檔命名），
    非框架實時導覽連結，計入會造成假陽性洪水（永不收斂）。
    """
    out: List[str] = []
    fence: Optional[str] = None  # 當前 fence 標記（``` 或 ~~~），None=不在 fence 內
    for line in md_text.splitlines():
        stripped = line.lstrip()
        if fence is None:
            if stripped.startswith("```") or stripped.startswith("~~~"):
                fence = stripped[:3]
                continue
            out.append(line)
        else:
            if stripped.startswith(fence):
                fence = None
    return "\n".join(out)


def _doc_link_targets(md_text: str) -> List[str]:
    out: List[str] = []
    for m in _MD_LINK_RE.finditer(_strip_code_fences(md_text)):
        raw = m.group(1).strip()
        if not raw:
            continue
        target = raw.split()[0]  # ](url "title") → 取首 token
        if target.lower().startswith(_SKIP_LINK_PREFIXES):
            continue
        if any(c in target for c in _LINK_TEMPLATE_CHARS):
            continue
        out.append(target)
    return out


def _scan_dead_links(md_file: Path) -> List[Tuple[str, str]]:
    """回傳 md_file 內所有無法解析的相對連結 [(source_rel, target), ...]。"""
    out: List[Tuple[str, str]] = []
    try:
        text = md_file.read_text(encoding="utf-8")
    except Exception:  # pragma: no cover - 讀檔防護
        return out
    base = md_file.parent
    src_rel = md_file.relative_to(FRAMEWORK_ROOT).as_posix()
    for target in _doc_link_targets(text):
        clean = target.split("#", 1)[0].split("?", 1)[0]  # 去錨點 / query
        if clean and not (base / clean).resolve().exists():
            out.append((src_rel, target))
    return out


def check_ff6_doc_link_integrity(report: FitnessReport) -> None:
    """兩層分離：樞紐硬訊號（per-link）+ 內容文件軟訊號（聚合，防假陽性洪水）。

    INIT.md 是框架唯一導覽樞紐，其連結若斷 = 下游載入失敗，必須全綠並逐條收斂；
    workflow/ 內容文件多為教學/繼承材料，連結衛生為軟指標，聚合成單一 advisory，
    避免淹沒樞紐硬訊號、也讓 SELF_EVOLUTION 收斂閘的分數維持有界。
    """
    # Tier 1：INIT.md 導覽樞紐（硬訊號，per-link，必須全綠）
    init = FRAMEWORK_ROOT / "AISDLC_SDD_INIT.md"
    hub_broken = _scan_dead_links(init) if init.exists() else []
    for src_rel, target in hub_broken:
        report.add(Finding(
            ff="FF-6", severity=SEVERITY_WARN, fingerprint=f"ff6-hub-{_fp(src_rel, target)}",
            title=f"INIT 樞紐死連結：{target}",
            detail=f"{src_rel} 指向磁碟不存在的路徑（導覽樞紐必須全綠；roadmap R3）。",
            evidence=[f"來源：{src_rel}", f"目標：{target}"],
        ))

    # Tier 2：workflow 內容文件連結衛生（軟訊號，聚合 1 條 advisory）
    wf = FRAMEWORK_ROOT / "workflow"
    content_broken: List[Tuple[str, str]] = []
    if wf.exists():
        for f in sorted(wf.rglob("*.md")):
            content_broken.extend(_scan_dead_links(f))
    if content_broken:
        sample = [f"{s} → {t}" for s, t in content_broken[:8]]
        if len(content_broken) > 8:
            sample.append(f"…另有 {len(content_broken) - 8} 條")
        report.add(Finding(
            ff="FF-6", severity=SEVERITY_WARN, fingerprint="ff6-workflow-linkrot",
            title=f"workflow 文件連結衛生：{len(content_broken)} 條未解析相對連結",
            detail="多為 v0.09 繼承文件註腳引用（相對深度寫錯或檔名更名）；聚合為單一 "
                   "advisory，建議批次清理（非樞紐、不阻擋收斂）。",
            evidence=sample,
        ))

    if not hub_broken and not content_broken:
        report.add(Finding(
            ff="FF-6", severity=SEVERITY_INFO, fingerprint="ff6-ok",
            title="文件相對連結完整",
            detail="INIT.md 樞紐 + workflow/ 內容文件無死連結。",
        ))
    elif not hub_broken:
        report.add(Finding(
            ff="FF-6", severity=SEVERITY_INFO, fingerprint="ff6-hub-ok",
            title="INIT.md 導覽樞紐連結完整（0 死連結）",
            detail="樞紐全綠；workflow 內容文件連結衛生見上方聚合 advisory。",
        ))


# ---------------------------------------------------------------------------
# FF-7：Agent↔Workflow↔Skill 引用健康度（advisory）
# ---------------------------------------------------------------------------
# (a) 數量宣稱漂移：INIT.md 文字摘要宣稱數 vs 磁碟實況（守 measurement blindness）。
# (b) auto_load_config 引用完整性：每個 quoted 相對 path 必須在磁碟存在，
#     否則下游 Runtime 依 INIT 載入該 agent / 場景檔時會失敗。
def _count_dirs(path: Path) -> int:
    return sum(1 for p in path.iterdir() if p.is_dir()) if path.exists() else 0


def _count_glob(path: Path, pat: str) -> int:
    return len(list(path.glob(pat))) if path.exists() else 0


# (fingerprint 尾碼, 擷取宣稱數的 regex, 人類標籤, 磁碟計數函式)
_INIT_COUNT_CLAIMS = [
    ("core-agents", r"Core Agents（(\d+)\s*個）", "Core Agents",
     lambda: _count_glob(FRAMEWORK_ROOT / "agent" / "core", "*.yaml")),
    ("specialized-agents", r"Specialized Agents（(\d+)\s*個）", "Specialized Agents",
     lambda: _count_glob(FRAMEWORK_ROOT / "agent" / "specialized", "*.yaml")),
    ("skills", r"Skills 完整清單（(\d+)\s*個）", "Skills",
     lambda: _count_dirs(FRAMEWORK_ROOT / ".claude" / "skills")),
]

_CONFIG_PATH_RE = re.compile(r'(?:path|sdd_enhancement|sop_path|cicd_spec):\s*"([^"]+)"')


def check_ff7_agent_workflow_skill_refs(report: FitnessReport) -> None:
    init = FRAMEWORK_ROOT / "AISDLC_SDD_INIT.md"
    if not init.exists():
        report.add(Finding(
            ff="FF-7", severity=SEVERITY_INFO, fingerprint="ff7-no-init",
            title="略過引用健康度檢查", detail="找不到 AISDLC_SDD_INIT.md。",
        ))
        return

    text = init.read_text(encoding="utf-8")
    n_before = len(report.findings)

    # (a) 數量宣稱漂移
    for fp_id, pat, label, counter in _INIT_COUNT_CLAIMS:
        m = re.search(pat, text)
        if not m:
            continue
        claimed, actual = int(m.group(1)), counter()
        if claimed != actual:
            report.add(Finding(
                ff="FF-7", severity=SEVERITY_WARN, fingerprint=f"ff7-count-{fp_id}",
                title=f"{label} 數量漂移：INIT 宣稱 {claimed}，磁碟 {actual}",
                detail="INIT.md 摘要與磁碟實況不符（measurement blindness；advisory）。",
                evidence=[f"宣稱={claimed}", f"磁碟={actual}", f"差={actual - claimed:+d}"],
            ))

    # (b) auto_load_config 引用完整性
    seen: Set[str] = set()
    for m in _CONFIG_PATH_RE.finditer(text):
        rel = m.group(1)
        if rel in seen or any(c in rel for c in _LINK_TEMPLATE_CHARS):
            continue
        seen.add(rel)
        if not (FRAMEWORK_ROOT / rel).exists():
            report.add(Finding(
                ff="FF-7", severity=SEVERITY_WARN, fingerprint=f"ff7-ref-{_fp(rel)}",
                title=f"auto_load_config 引用不存在：{rel}",
                detail="INIT.md 引用磁碟不存在的檔案，下游載入會失敗。",
                evidence=[rel],
            ))

    if len(report.findings) == n_before:
        report.add(Finding(
            ff="FF-7", severity=SEVERITY_INFO, fingerprint="ff7-ok",
            title="Agent↔Workflow↔Skill 引用健康",
            detail="數量宣稱與 auto_load_config 引用均與磁碟一致。",
        ))


# ---------------------------------------------------------------------------
# FF-8：Governance 規則 → 強制執行測試 可追溯性（roadmap R7）
# ---------------------------------------------------------------------------
# 整個框架的圖靈完備閉環論述，全靠 Rule 9.x 被「強制執行」而非僅「宣告」。每條規則以
# `test_ref` 宣告強制它的測試 —— 但此連結先前無任何守門：test 被改名/刪除（dangling）
# 或規則漏填 test_ref，沒有 FF 或同步測試會發現，規則悄然降格為 governance theater。
# FF-8 補上這道「治理規則本身熵增」的收斂閘，分四級（呼應 advisory vs blocking 哲學）。
_RULE_ID_RE = re.compile(r"^id:\s*(\S+)", re.MULTILINE)
_RULE_MATURITY_RE = re.compile(r"^maturity:\s*(\S+)", re.MULTILINE)
_RULE_TESTREF_RE = re.compile(r"^test_ref:\s*(.+)$", re.MULTILINE)


def check_ff8_rule_enforcement_traceability(report: FitnessReport) -> None:
    if not GOV_RULES_DIR.exists():
        report.add(Finding(
            ff="FF-8", severity=SEVERITY_INFO, fingerprint="ff8-no-rules",
            title="略過規則強制可追溯性檢查", detail=f"未找到 {GOV_RULES_DIR}。",
        ))
        return

    rule_files = sorted(GOV_RULES_DIR.glob("R-*.yaml"))
    n_active = 0
    missing_ref: List[str] = []
    dangling: List[Tuple[str, str]] = []
    no_test_fn: List[Tuple[str, str]] = []
    no_backref: List[str] = []

    for y in rule_files:
        text = y.read_text(encoding="utf-8")
        id_m = _RULE_ID_RE.search(text)
        rid = id_m.group(1).strip() if id_m else y.stem
        mat_m = _RULE_MATURITY_RE.search(text)
        maturity = mat_m.group(1).strip() if mat_m else "active"
        # 退役 / audit-only 規則不再要求強制測試（鏡像 rule_loader maturity 語意，
        # 避免對刻意停用的鷹架規則誤報）。
        if maturity != "active":
            continue
        n_active += 1

        ref_m = _RULE_TESTREF_RE.search(text)
        if not ref_m:
            missing_ref.append(rid)
            continue
        ref = ref_m.group(1).strip()
        test_path = FRAMEWORK_ROOT / ref
        if not test_path.exists():
            dangling.append((rid, ref))
            continue
        try:
            test_text = test_path.read_text(encoding="utf-8", errors="replace")
        except Exception:  # pragma: no cover - 讀檔防護
            no_test_fn.append((rid, ref))
            continue
        if "def test_" not in test_text:
            no_test_fn.append((rid, ref))
            continue
        # 反向引用（advisory）：測試須以規則 id 字面為錨點，使 rule⇄test 雙向可 grep。
        if rid not in test_text:
            no_backref.append(rid)

    if missing_ref:
        report.add(Finding(
            ff="FF-8", severity=SEVERITY_FAIL, fingerprint="ff8-missing-testref",
            title=f"{len(missing_ref)} 條 active 規則缺 test_ref（未宣告強制執行）",
            detail="治理規則未宣告強制它的測試 = governance theater；違反規則時無測試會停機，"
                   "破閉環健全性。每條 active 規則須填 test_ref 指向其強制測試。",
            evidence=missing_ref,
        ))
    for rid, ref in dangling:
        report.add(Finding(
            ff="FF-8", severity=SEVERITY_FAIL, fingerprint=f"ff8-dangling-{_fp(rid, ref)}",
            title=f"{rid} 的 test_ref 指向不存在的測試",
            detail="規則→測試連結斷裂（測試被改名/刪除但規則未同步），該規則強制執行已失效。",
            evidence=[f"{rid} → {ref}"],
        ))
    for rid, ref in no_test_fn:
        report.add(Finding(
            ff="FF-8", severity=SEVERITY_FAIL, fingerprint=f"ff8-no-testfn-{_fp(rid, ref)}",
            title=f"{rid} 的 test_ref 無任何 def test_",
            detail="test_ref 指向非測試 / stub 檔，pytest 不會執行任何斷言來強制此規則。",
            evidence=[f"{rid} → {ref}"],
        ))
    if no_backref:
        sample = list(no_backref[:12])
        if len(no_backref) > 12:
            sample.append(f"…另有 {len(no_backref) - 12} 條")
        report.add(Finding(
            ff="FF-8", severity=SEVERITY_WARN, fingerprint="ff8-weak-backref",
            title=f"{len(no_backref)} 條規則的強制測試未反向引用規則 id（弱可追溯）",
            detail="rule→test 為單向：測試內無 `R-9.x` 字面錨點，重構/刪改測試時無法回溯它在"
                   "守哪條規則。建議於測試檔頂加 `# enforces (governance rules): <rule-id>` "
                   "錨點，使可追溯性雙向且可 grep（非樞紐、不阻擋收斂，advisory）。",
            evidence=sample,
        ))

    if not (missing_ref or dangling or no_test_fn or no_backref):
        report.add(Finding(
            ff="FF-8", severity=SEVERITY_INFO, fingerprint="ff8-ok",
            title=f"全部 {n_active} 條 active 治理規則皆接上有效且雙向可追溯的強制測試",
            detail="每條 active 規則 test_ref 存在、含 def test_、且測試反向引用規則 id；"
                   "guard ↔ halting test 連結完整可稽核。",
        ))


# ---------------------------------------------------------------------------
# FF-10：Governance 規則 trigger_states 可達性（死規則偵測，roadmap R8）
# ---------------------------------------------------------------------------
# 規則靠 rule_loader.load_for_state(state) 依當前 FSM 狀態注入；trigger_states 是它與
# 39 態 canonical 宇宙的唯一連結。若 trigger 指向幽靈狀態或為空，規則永不觸發 = 死規則。
# 與 FF-8 互補：FF-8 守「規則 → 強制測試」，FF-10 守「規則 → 觸發狀態」，兩者夾住一條
# active 規則生效的兩個前提（會被注入 ∧ 被注入後有測試強制）。
def check_ff10_rule_trigger_reachability(report: FitnessReport) -> None:
    if not GOV_RULES_DIR.exists():
        report.add(Finding(
            ff="FF-10", severity=SEVERITY_INFO, fingerprint="ff10-no-rules",
            title="略過規則 trigger 可達性檢查", detail=f"未找到 {GOV_RULES_DIR}。",
        ))
        return
    try:
        from tools.fsm_runtime import transition_rules as tr  # type: ignore
    except Exception as exc:  # pragma: no cover - import 防護
        report.add(Finding(
            ff="FF-10", severity=SEVERITY_FAIL, fingerprint="ff10-import",
            title="無法 import transition_rules", detail=str(exc),
        ))
        return
    try:
        import yaml  # PyYAML（框架既有相依）
    except Exception as exc:  # pragma: no cover - 退化路徑
        report.add(Finding(
            ff="FF-10", severity=SEVERITY_INFO, fingerprint="ff10-no-yaml",
            title="略過（PyYAML 不可用）", detail=str(exc),
        ))
        return

    universe: Set[str] = set(tr._HAPPY_PATH.keys()) | set(tr._EMERGENCY_TARGETS)
    ghost_map: Dict[str, List[str]] = {}
    empty_trigger: List[str] = []
    n_active = 0
    for y in sorted(GOV_RULES_DIR.glob("R-*.yaml")):
        try:
            data = yaml.safe_load(y.read_text(encoding="utf-8")) or {}
        except Exception:
            continue  # YAML 解析失敗由 test_rules_index_sync 守，FF-10 不重複報
        if not isinstance(data, dict):
            continue
        if str(data.get("maturity", "active")) != "active":
            continue  # 退役 / audit-only 規則不要求可達（鏡像 rule_loader maturity 語意）
        n_active += 1
        rid = str(data.get("id") or y.stem)
        ts = data.get("trigger_states") or []
        if isinstance(ts, str):
            ts = [ts]
        if not ts:
            empty_trigger.append(rid)
            continue
        ghosts = sorted(s for s in ts if s != "*" and s not in universe)
        if ghosts:
            ghost_map[rid] = ghosts

    for rid, ghosts in sorted(ghost_map.items()):
        report.add(Finding(
            ff="FF-10", severity=SEVERITY_FAIL, fingerprint=f"ff10-ghost-{_fp(rid, *ghosts)}",
            title=f"{rid} 的 trigger_states 含 {len(ghosts)} 個幽靈狀態（永不觸發 = 死規則）",
            detail="trigger 指向不存在於 FSM canonical 宇宙的狀態（typo 或狀態改名/移除未同步）；"
                   "rule_loader 永不會在該狀態注入此規則，規則形同失效。新增狀態須同步 FF-1 三源。",
            evidence=[f"{rid} → 幽靈狀態：{ghosts}"],
        ))
    for rid in empty_trigger:
        report.add(Finding(
            ff="FF-10", severity=SEVERITY_FAIL, fingerprint=f"ff10-empty-{_fp(rid)}",
            title=f"{rid} 的 trigger_states 為空（永不觸發 = 死規則）",
            detail="無任何觸發狀態，rule_loader.load_for_state 永遠不會載入此規則。",
            evidence=[rid],
        ))
    if not ghost_map and not empty_trigger:
        report.add(Finding(
            ff="FF-10", severity=SEVERITY_INFO, fingerprint="ff10-ok",
            title=f"全部 {n_active} 條 active 規則 trigger_states 皆可達（無死規則）",
            detail=f"每條規則 trigger ⊆ FSM {len(universe)} 態 canonical 宇宙（或 * 萬用）；"
                   "守規則→狀態引用完整性，與 FF-1 三源宇宙一致互補。",
        ))


# ---------------------------------------------------------------------------
# FF-11：Skill frontmatter 結構完整性（roadmap R9）
# ---------------------------------------------------------------------------
# Skill 是框架能力的調用入口（FF-7 守數量/引用，FF-11 守每個 SKILL.md 的內部結構）。
# harness 靠 frontmatter 的 name/description 註冊 skill；缺 frontmatter 會退化成佔位字串。
# 不檢查 name-vs-dir 相等——12 個刻意短別名（ba-analyst→ba-validate 等）會造成假陽性。
SKILLS_DIR = FRAMEWORK_ROOT / ".claude" / "skills"
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def check_ff11_skill_frontmatter(report: FitnessReport) -> None:
    if not SKILLS_DIR.exists():
        report.add(Finding(
            ff="FF-11", severity=SEVERITY_INFO, fingerprint="ff11-no-dir",
            title="略過 Skill frontmatter 檢查", detail=f"未找到 {SKILLS_DIR}。",
        ))
        return

    skill_dirs = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())
    no_md: List[str] = []
    no_fm: List[str] = []
    no_name: List[str] = []
    no_desc: List[str] = []
    for d in skill_dirs:
        md = d / "SKILL.md"
        if not md.exists():
            no_md.append(d.name)
            continue
        text = md.read_text(encoding="utf-8", errors="replace")
        m = _FRONTMATTER_RE.match(text)
        if not m:
            no_fm.append(d.name)
            continue
        fm = m.group(1)
        if not re.search(r"^name:\s*\S", fm, re.MULTILINE):
            no_name.append(d.name)
        if not re.search(r"^description:\s*\S", fm, re.MULTILINE):
            no_desc.append(d.name)

    for label, items, fp in (
        ("缺 SKILL.md", no_md, "ff11-missing-md"),
        ("SKILL.md 缺 YAML frontmatter", no_fm, "ff11-no-frontmatter"),
        ("frontmatter 缺 name", no_name, "ff11-no-name"),
        ("frontmatter 缺 description", no_desc, "ff11-no-description"),
    ):
        if items:
            report.add(Finding(
                ff="FF-11", severity=SEVERITY_FAIL, fingerprint=fp,
                title=f"{len(items)} 個 skill {label}",
                detail="skill 是框架能力調用入口；frontmatter 不全 = harness 無法正確註冊/"
                       "顯示該 skill（Skill 層 measurement blindness）。",
                evidence=sorted(items),
            ))

    if not (no_md or no_fm or no_name or no_desc):
        report.add(Finding(
            ff="FF-11", severity=SEVERITY_INFO, fingerprint="ff11-ok",
            title=f"全部 {len(skill_dirs)} 個 skill frontmatter 結構完整",
            detail="每個 SKILL.md 皆有合法 YAML frontmatter 含 name + description。",
        ))


# ---------------------------------------------------------------------------
# FF-12：critical 規則治理錯置（severity↔trigger 一致性，roadmap R10）
# ---------------------------------------------------------------------------
# critical = 違反即停機。OBSERVATION_STATES 為非阻塞瞬態觀測窗；critical 規則若 trigger
# 全落在觀測態，它永遠無法在阻塞點觸發 = 形同失效的關鍵規則。與 FF-10 互補：FF-10 守
# 「trigger 可達」，FF-12 守「critical 的 trigger 落在能真正停機的狀態」。
def check_ff12_severity_placement(report: FitnessReport) -> None:
    if not GOV_RULES_DIR.exists():
        report.add(Finding(
            ff="FF-12", severity=SEVERITY_INFO, fingerprint="ff12-no-rules",
            title="略過 critical 規則錯置檢查", detail=f"未找到 {GOV_RULES_DIR}。",
        ))
        return
    try:
        from tools.fsm_runtime import transition_rules as tr  # type: ignore
    except Exception as exc:  # pragma: no cover - import 防護
        report.add(Finding(
            ff="FF-12", severity=SEVERITY_FAIL, fingerprint="ff12-import",
            title="無法 import transition_rules", detail=str(exc),
        ))
        return
    try:
        import yaml  # PyYAML（框架既有相依）
    except Exception as exc:  # pragma: no cover - 退化路徑
        report.add(Finding(
            ff="FF-12", severity=SEVERITY_INFO, fingerprint="ff12-no-yaml",
            title="略過（PyYAML 不可用）", detail=str(exc),
        ))
        return

    observation: Set[str] = set(tr.OBSERVATION_STATES)
    misplaced: Dict[str, List[str]] = {}
    n_critical = 0
    for y in sorted(GOV_RULES_DIR.glob("R-*.yaml")):
        try:
            data = yaml.safe_load(y.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if str(data.get("maturity", "active")) != "active":
            continue
        if str(data.get("severity")) != "critical":
            continue
        n_critical += 1
        rid = str(data.get("id") or y.stem)
        ts = data.get("trigger_states") or []
        if isinstance(ts, str):
            ts = [ts]
        if not ts:
            continue  # 空 trigger 由 FF-10 守，不在此重複報
        # 能真正停機的 trigger：* 萬用，或任何非觀測態（含緊急/終端/主幹狀態）。
        blocking_reach = [t for t in ts if t == "*" or t not in observation]
        if not blocking_reach:
            misplaced[rid] = sorted(ts)

    for rid, ts in sorted(misplaced.items()):
        report.add(Finding(
            ff="FF-12", severity=SEVERITY_FAIL, fingerprint=f"ff12-misplaced-{_fp(rid)}",
            title=f"{rid}（critical）的 trigger 全為觀測態（永不停機 = 治理錯置）",
            detail="severity=critical 宣稱違反即停機，但其 trigger_states ⊆ OBSERVATION_STATES "
                   "（非阻塞瞬態觀測窗），規則永遠不會在阻塞點觸發；應改掛阻塞狀態或降 severity。",
            evidence=[f"{rid} → 觀測態 only：{ts}"],
        ))

    if not misplaced:
        report.add(Finding(
            ff="FF-12", severity=SEVERITY_INFO, fingerprint="ff12-ok",
            title=f"全部 {n_critical} 條 critical 規則 trigger 落點正確（無治理錯置）",
            detail="每條 critical 規則至少有一個能真正停機的 trigger（* 或非觀測態）；"
                   "severity 與觸發落點一致。",
        ))


# ---------------------------------------------------------------------------
# FF-13：Agent YAML schema 完整性（roadmap R11，advisory）
# ---------------------------------------------------------------------------
# FF-7 守 agent 的「數量/引用」，FF-13 守每個 agent YAML 的「內部嚴格合法性」，與 FF-11
# （Skill 層）對稱。agent 由 Runtime/LLM 以文字載入，故 YAML 失效不會即時崩潰 → advisory
# （非阻擋，鏡像 FF-2）。修復屬核心 artifact 變更，走 Rule 8 人工閘，不在工具 commit 硬修。
AGENT_DIR = FRAMEWORK_ROOT / "agent"


def check_ff13_agent_yaml_schema(report: FitnessReport) -> None:
    if not AGENT_DIR.exists():
        report.add(Finding(
            ff="FF-13", severity=SEVERITY_INFO, fingerprint="ff13-no-dir",
            title="略過 Agent YAML schema 檢查", detail=f"未找到 {AGENT_DIR}。",
        ))
        return
    try:
        import yaml  # PyYAML（框架既有相依）
    except Exception as exc:  # pragma: no cover - 退化路徑
        report.add(Finding(
            ff="FF-13", severity=SEVERITY_INFO, fingerprint="ff13-no-yaml",
            title="略過（PyYAML 不可用）", detail=str(exc),
        ))
        return

    files = sorted(AGENT_DIR.rglob("*.yaml"))
    invalid: List[Tuple[str, str]] = []
    missing_key: List[str] = []
    for f in files:
        rel = f.relative_to(FRAMEWORK_ROOT).as_posix()
        try:
            docs = list(yaml.safe_load_all(f.read_text(encoding="utf-8")))
        except Exception as exc:
            prob = getattr(exc, "problem", None) or str(exc).splitlines()[0]
            mark = getattr(exc, "problem_mark", None)
            loc = f"line {mark.line + 1}" if mark is not None else "?"
            invalid.append((rel, f"{loc}: {prob}"))
            continue
        dict_docs = [d for d in docs if isinstance(d, dict)]
        if not any("agent" in d for d in dict_docs):
            missing_key.append(rel)

    if invalid:
        sample = [f"{rel} ({why})" for rel, why in invalid[:8]]
        if len(invalid) > 8:
            sample.append(f"…另有 {len(invalid) - 8} 條")
        report.add(Finding(
            ff="FF-13", severity=SEVERITY_WARN, fingerprint="ff13-yaml-invalid",
            title=f"{len(invalid)} 個 agent YAML 非嚴格合法（PyYAML 無法解析）",
            detail="agent 由 Runtime/LLM 以文字載入故未即時崩潰，但嚴格 YAML 失效是 Agent 層 "
                   "measurement blindness（縮排錯置 / 誤插 --- / 未引號特殊字元）。聚合為單一 "
                   "advisory；修復屬核心 artifact 變更，走 Rule 8 人工閘，不阻擋收斂。",
            evidence=sample,
        ))
    if missing_key:
        report.add(Finding(
            ff="FF-13", severity=SEVERITY_WARN, fingerprint="ff13-missing-agent-key",
            title=f"{len(missing_key)} 個 agent YAML 缺頂層 `agent` 定義鍵",
            detail="可解析但無 agent 定義根鍵；下游依 auto_load_config 套用 agent 規則時無內容。",
            evidence=sorted(missing_key)[:12],
        ))

    if not invalid and not missing_key:
        report.add(Finding(
            ff="FF-13", severity=SEVERITY_INFO, fingerprint="ff13-ok",
            title=f"全部 {len(files)} 個 agent YAML 嚴格合法且具 agent 定義鍵",
            detail="每個 agent/**/*.yaml 皆通過 safe_load_all 且含頂層 agent 鍵。",
        ))


# ---------------------------------------------------------------------------
# FF-9：Scaffold-ROI 代謝（roadmap R14；structural schema + data-gated 0-fire advisory）
# ---------------------------------------------------------------------------
# scaffold_roi 是 Rule 9.20 GAE / sdd-gc 判斷「規則鷹架是否該退役」的計數基座。靜態守
# 基座完整（每條 active 規則須有 fire/catch/false_positive 三整數）；動態部分僅在系統
# 已被充分運行（aggregate fire ≥ 門檻）時才把長期 0-fire 規則標為過時鷹架候選（advisory），
# 否則 gate 關閉避免「全 0 → 全部誤報」。隨 runtime 累積自動啟動。
_FF9_ROI_KEYS = ("fire_count", "catch_count", "false_positive_count")
FF9_STALE_MIN_AGGREGATE = int(os.environ.get("SDD_FF9_STALE_MIN_AGGREGATE", "20"))


def check_ff9_scaffold_roi(report: FitnessReport) -> None:
    if not GOV_RULES_DIR.exists():
        report.add(Finding(ff="FF-9", severity=SEVERITY_INFO, fingerprint="ff9-no-rules",
                           title="略過 Scaffold-ROI 檢查", detail=f"未找到 {GOV_RULES_DIR}。"))
        return
    try:
        import yaml  # PyYAML（框架既有相依）
    except Exception as exc:  # pragma: no cover - 退化路徑
        report.add(Finding(ff="FF-9", severity=SEVERITY_INFO, fingerprint="ff9-no-yaml",
                           title="略過（PyYAML 不可用）", detail=str(exc)))
        return

    missing: List[str] = []
    malformed: List[str] = []
    per_rule_fire: Dict[str, int] = {}
    for y in sorted(GOV_RULES_DIR.glob("R-*.yaml")):
        try:
            data = yaml.safe_load(y.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        if not isinstance(data, dict) or str(data.get("maturity", "active")) != "active":
            continue
        rid = str(data.get("id") or y.stem)
        sr = data.get("scaffold_roi")
        if not isinstance(sr, dict):
            missing.append(rid)
            continue
        if not all(isinstance(sr.get(k), int) and sr.get(k, -1) >= 0 for k in _FF9_ROI_KEYS):
            malformed.append(rid)
            continue
        per_rule_fire[rid] = sr["fire_count"]

    if missing:
        report.add(Finding(ff="FF-9", severity=SEVERITY_FAIL, fingerprint="ff9-missing-roi",
            title=f"{len(missing)} 條 active 規則缺 scaffold_roi 計數基座",
            detail="Rule 9.20 GAE / sdd-gc 需 scaffold_roi 計數才能判斷鷹架退役；缺基座 = ROI 治理失效。",
            evidence=sorted(missing)))
    if malformed:
        report.add(Finding(ff="FF-9", severity=SEVERITY_FAIL, fingerprint="ff9-malformed-roi",
            title=f"{len(malformed)} 條 active 規則 scaffold_roi 結構不良",
            detail="fire_count / catch_count / false_positive_count 須為非負整數。",
            evidence=sorted(malformed)))

    aggregate = sum(per_rule_fire.values())
    stale = sorted(rid for rid, fc in per_rule_fire.items() if fc == 0)
    gate_open = aggregate >= FF9_STALE_MIN_AGGREGATE
    if gate_open and stale:
        report.add(Finding(ff="FF-9", severity=SEVERITY_WARN, fingerprint="ff9-stale-scaffold",
            title=f"{len(stale)} 條規則長期 0-fire（過時鷹架候選）",
            detail=f"全系統已觸發 {aggregate} 次（≥門檻 {FF9_STALE_MIN_AGGREGATE}），但這些規則從未攔截；"
                   "建議經 sdd-gc / set_maturity 人工 review 退役（Rule 9.20，advisory 不阻擋）。",
            evidence=stale[:12]))

    if not missing and not malformed and not (gate_open and stale):
        gate_note = (f"aggregate fire={aggregate} ≥ 門檻 {FF9_STALE_MIN_AGGREGATE}，0-fire 偵測啟動且無過時鷹架"
                     if gate_open else
                     f"aggregate fire={aggregate} < 門檻 {FF9_STALE_MIN_AGGREGATE}，0-fire 偵測待 runtime 資料（gate 關閉）")
        report.add(Finding(ff="FF-9", severity=SEVERITY_INFO, fingerprint="ff9-ok",
            title=f"全部 {len(per_rule_fire)} 條 active 規則 scaffold_roi 基座完整",
            detail=f"三整數計數齊備；{gate_note}。"))


# ---------------------------------------------------------------------------
# FF-14：CI workflow → 工具模組引用一致性（roadmap R13）
# ---------------------------------------------------------------------------
# workflow 以 `python -m tools.*` 呼叫專案模組；模組改名/移除未同步會讓 CI step runtime
# 失敗。僅驗專案自有命名空間（tools.*），pip / pytest 等外部工具略過以免假陽性。
WORKFLOW_DIRS = [PROJECT_ROOT / ".github" / "workflows",
                 FRAMEWORK_ROOT / ".github" / "workflows"]
_PY_M_RE = re.compile(r"python[0-9]?\s+-m\s+([A-Za-z_][\w.]+)")
_PROJECT_MODULE_PREFIX = "tools"


def _module_resolves(mod: str) -> bool:
    p = FRAMEWORK_ROOT.joinpath(*mod.split("."))
    return p.with_suffix(".py").exists() or (p / "__init__.py").exists()


def check_ff14_workflow_module_refs(report: FitnessReport) -> None:
    refs: Dict[str, Set[str]] = {}
    for wd in WORKFLOW_DIRS:
        if not wd.exists():
            continue
        for y in sorted(list(wd.glob("*.yml")) + list(wd.glob("*.yaml"))):
            try:
                text = y.read_text(encoding="utf-8")
            except Exception:  # pragma: no cover
                continue
            for mod in _PY_M_RE.findall(text):
                top = mod.split(".", 1)[0]
                if top == _PROJECT_MODULE_PREFIX:
                    refs.setdefault(mod, set()).add(y.name)

    if not refs:
        report.add(Finding(ff="FF-14", severity=SEVERITY_INFO, fingerprint="ff14-no-refs",
            title="無 CI workflow 引用專案工具模組", detail="未發現 python -m tools.* 引用。"))
        return

    broken = {m: s for m, s in refs.items() if not _module_resolves(m)}
    for mod, files in sorted(broken.items()):
        report.add(Finding(ff="FF-14", severity=SEVERITY_FAIL, fingerprint=f"ff14-missing-{_fp(mod)}",
            title=f"CI workflow 引用不存在的工具模組：{mod}",
            detail="workflow 以 python -m 呼叫的專案模組無法解析（改名/移除未同步），CI step 會 runtime 失敗。",
            evidence=[f"{mod} ← {sorted(files)}"]))

    if not broken:
        report.add(Finding(ff="FF-14", severity=SEVERITY_INFO, fingerprint="ff14-ok",
            title=f"全部 {len(refs)} 個 CI workflow 工具模組引用皆可解析",
            detail="每個 python -m tools.* 引用均對應磁碟上存在的模組／套件。"))


# ---------------------------------------------------------------------------
# FF-15：docs_template 索引 ↔ 磁碟一致性（artifact 第三支柱結構守門，roadmap R15）
# ---------------------------------------------------------------------------
# FF-11 守 Skill 層、FF-13 守 Agent 層結構完整性；docs_template（框架第三大 artifact
# 家族）先前無任何結構守門。INIT.md「SDD 模板索引」是模板的導覽樞紐：場景依它把模板複製
# 到 docs/ 填寫。本 FF 補上兩道，與既有家族同源：
#   (A) 索引引用的模板必須在磁碟存在（structural fail）——dangling index = 場景複製時
#       靜默失敗；改名/刪除模板未同步索引即觸發（與 FF-7/10/14 引用完整性家族同源）。
#   (B) 索引宣稱數 / 涵蓋面 vs 磁碟漂移（advisory）——未索引模板 = 樞紐量測盲區，讀者
#       無從發現較新模板（鏡像 FF-7 數量漂移；歷史上 Phase 09 曾手動修 18→51，此後再
#       漂移無守門，FF-15 把反覆人工對賬轉為自動回歸閘）。
DOCS_TEMPLATE_SDD_DIR = FRAMEWORK_ROOT / "docs_template" / "sdd"
_TEMPLATE_INDEX_HEAD_RE = re.compile(r"##\s*SDD 模板索引（(\d+)\s*個）")
# 索引表「模板檔案」欄為反引號包裹的檔名（含連字號，故不能只用 \w）。
_TEMPLATE_FILE_RE = re.compile(r"`([A-Za-z0-9][\w.\-]+\.(?:md|yaml))`")


def _template_index_section(init_text: str) -> Optional[Tuple[int, str]]:
    """擷取 INIT.md「## SDD 模板索引（NN 個）」section（到下一個 level-2 標題或 --- 為止）。

    回傳 (claimed_count, section_text)；找不到回 None。邊界用 `^## ` 或 `^---`，
    `### 子標題` 不會誤切（^##\\s 要求 ## 後接空白，### 第三字為 # 不符）。
    """
    m = _TEMPLATE_INDEX_HEAD_RE.search(init_text)
    if not m:
        return None
    rest = init_text[m.end():]
    end_m = re.search(r"^##\s|\n---\s*\n", rest, re.MULTILINE)
    section = rest[:end_m.start()] if end_m else rest
    return int(m.group(1)), section


def check_ff15_docs_template_index(report: FitnessReport) -> None:
    init = FRAMEWORK_ROOT / "AISDLC_SDD_INIT.md"
    if not init.exists() or not DOCS_TEMPLATE_SDD_DIR.exists():
        report.add(Finding(
            ff="FF-15", severity=SEVERITY_INFO, fingerprint="ff15-no-input",
            title="略過 docs_template 索引檢查",
            detail="找不到 AISDLC_SDD_INIT.md 或 docs_template/sdd/。",
        ))
        return

    parsed = _template_index_section(init.read_text(encoding="utf-8"))
    if parsed is None:
        report.add(Finding(
            ff="FF-15", severity=SEVERITY_INFO, fingerprint="ff15-no-section",
            title="INIT.md 無 SDD 模板索引 section",
            detail="找不到「## SDD 模板索引（NN 個）」標題。",
        ))
        return
    claimed, section = parsed

    # 磁碟實況：docs_template/sdd 下所有 .md / .yaml 模板（basename，跨子目錄唯一）。
    disk: Set[str] = set()
    for ext in ("*.md", "*.yaml"):
        disk |= {p.name for p in DOCS_TEMPLATE_SDD_DIR.rglob(ext)}
    disk_count = len(disk)

    indexed: Set[str] = set(_TEMPLATE_FILE_RE.findall(section))

    # (A) structural：索引引用磁碟不存在的模板 = dangling（場景複製靜默失敗）。
    dangling = sorted(f for f in indexed if f not in disk)
    if dangling:
        report.add(Finding(
            ff="FF-15", severity=SEVERITY_FAIL, fingerprint="ff15-dangling-index",
            title=f"SDD 模板索引引用 {len(dangling)} 個磁碟不存在的模板",
            detail="索引列出但 docs_template/sdd/ 無對應檔；場景依索引複製模板到 docs/ 時會"
                   "靜默失敗。改名/刪除模板須同步索引（與 FF-7/10/14 引用完整性家族同源）。",
            evidence=dangling,
        ))

    # (B) advisory：宣稱數 / 涵蓋面 vs 磁碟漂移（未索引模板 = 樞紐量測盲區）。
    unindexed = sorted(f for f in disk if f not in indexed)
    if claimed != disk_count or unindexed:
        sample = unindexed[:12]
        if len(unindexed) > 12:
            sample.append(f"…另有 {len(unindexed) - 12} 個")
        report.add(Finding(
            ff="FF-15", severity=SEVERITY_WARN, fingerprint="ff15-index-drift",
            title=f"模板索引漂移：宣稱 {claimed} 個，磁碟 {disk_count} 個"
                  f"（{len(unindexed)} 個未索引）",
            detail="INIT.md「SDD 模板索引」是模板導覽樞紐；未索引模板使讀者無從發現較新模板"
                   "（measurement blindness，鏡像 FF-7 數量漂移）。建議補入索引並校正宣稱數"
                   "（advisory，不阻擋收斂）。",
            evidence=[f"宣稱={claimed}", f"磁碟={disk_count}"] + sample,
        ))

    if not dangling and claimed == disk_count and not unindexed:
        report.add(Finding(
            ff="FF-15", severity=SEVERITY_INFO, fingerprint="ff15-ok",
            title=f"SDD 模板索引與磁碟一致（{disk_count} 個模板全索引、全可解析）",
            detail="索引引用全部解析至磁碟，且宣稱數與涵蓋面與 docs_template/sdd/ 一致；"
                   "完成 Skill（FF-11）/ Agent（FF-13）/ Template（FF-15）三支柱 artifact 結構守門。",
        ))


# ---------------------------------------------------------------------------
# FF-16：具身評估器 & 鷹架代謝工具鏈接地完整性（Phase X / roadmap R16）
# ---------------------------------------------------------------------------
# Phase H（ACT-045~055）建好「具身評估器 + 運行時可觀測性 + 常駐鷹架 GC」，但 Phase L~W
# 近 8 個 meta phase 的自我演化全押在合成算子代數，使這條具身鏈在元迴圈層被晾置、GC 0-fire。
# FF-16 把這個漂移盲區轉為靜態守門，與 FF-7/10/14/15 引用完整性家族同源：
#   (A) structural — sdd-evaluator / sdd-gc 宣告依賴的 runtime 模組必須在磁碟存在，且其綁定的
#       FSM 狀態必須存在於 canonical 宇宙；dangling = 具身/代謝能力 governance-theater（宣稱能力、
#       無 backing code）。因四模組 + 兩狀態現皆存在 → 綠燈鎖，ENFORCING 未來 bit-rot/誤刪被擋下。
#   (B) advisory — 元迴圈生成器是否零引用具身工具鏈（GAP-X1 未接地）、GC 是否從未產出退役提案
#       （GAP-X2 代謝肌肉從未收縮）；把病灶轉為被追蹤 backlog（鏡像 FF-2/9/13 漸進哲學，不阻擋）。

# 每組 = (agent 相對路徑, [宣告依賴的 runtime 模組（dotted）...], 綁定的 FSM 狀態)
EMBODIED_AGENT_SPECS = (
    ("agent/specialized/sdd-evaluator-zh.yaml",
     ["tools.fsm_runtime.sandbox_runner",
      "tools.fsm_runtime.output_quality_scorer",
      "tools.fsm_runtime.observability_query"],
     "EXECUTION_EVALUATION"),
    ("agent/specialized/sdd-gc-zh.yaml",
     ["tools.fsm_runtime.scaffold_gc"],
     "SCAFFOLD_GC"),
)
# 元迴圈生成器模組（相對 FRAMEWORK_ROOT）：自我演化判定的「生成」端。
META_LOOP_GENERATOR_RELPATHS = (
    "tools/fsm_runtime/operator_genesis.py",
    "tools/fsm_runtime/operator_recursion_genesis.py",
    "tools/fsm_runtime/dimension_necessity_oracle.py",
)
# 具身評估器工具鏈的可 grep 模組名（元迴圈若接地，生成/評估端應引用其一）。
EMBODIED_TOOLCHAIN_NAMES = ("sandbox_runner", "observability_query", "output_quality_scorer")
GC_REPORTS_DIR = FRAMEWORK_ROOT / "build" / "reports" / "gc"


def check_ff16_embodied_evaluator_grounding(report: FitnessReport) -> None:
    # (A) structural：具身/代謝能力引用接地完整 -----------------------------------
    try:
        from tools.fsm_runtime import transition_rules as tr  # type: ignore
        universe: Set[str] = set(tr._HAPPY_PATH.keys()) | set(tr._EMERGENCY_TARGETS)
    except Exception as exc:  # pragma: no cover - import 防護
        report.add(Finding(
            ff="FF-16", severity=SEVERITY_FAIL, fingerprint="ff16-import",
            title="無法 import transition_rules（具身狀態宇宙不可解析）", detail=str(exc),
        ))
        universe = set()

    structural_ok = True
    for agent_rel, modules, bound_state in EMBODIED_AGENT_SPECS:
        if not (FRAMEWORK_ROOT / agent_rel).exists():
            structural_ok = False
            report.add(Finding(
                ff="FF-16", severity=SEVERITY_FAIL,
                fingerprint=f"ff16-agent-missing-{_fp(agent_rel)}",
                title=f"具身能力 agent 不存在：{agent_rel}",
                detail="宣告具身評估/鷹架代謝能力的系統級 agent 檔缺失；能力無載入入口 = 接地斷裂。",
                evidence=[agent_rel]))
            continue
        for mod in modules:
            if not _module_resolves(mod):
                structural_ok = False
                report.add(Finding(
                    ff="FF-16", severity=SEVERITY_FAIL,
                    fingerprint=f"ff16-module-missing-{_fp(agent_rel, mod)}",
                    title=f"{agent_rel} 宣告的 runtime 模組不存在：{mod}",
                    detail="agent 宣告依賴的具身/代謝模組無磁碟 backing code = governance-theater"
                           "（宣稱能力、無實作）。改名/移除模組須同步 agent 宣告與本 FF。",
                    evidence=[f"{agent_rel} → {mod}"]))
        if universe and bound_state not in universe:
            structural_ok = False
            report.add(Finding(
                ff="FF-16", severity=SEVERITY_FAIL,
                fingerprint=f"ff16-state-missing-{_fp(agent_rel, bound_state)}",
                title=f"{agent_rel} 綁定的 FSM 狀態不存在於 canonical 宇宙：{bound_state}",
                detail="具身評估/代謝 agent 綁定的 FSM 狀態（EXECUTION_EVALUATION / SCAFFOLD_GC）須存在於"
                       "transition_rules canonical 宇宙；缺失 = 該 agent 永不會被觸發（與 FF-10 死規則同源）。",
                evidence=[f"{agent_rel} → {bound_state}"]))

    # (B) advisory：具身接地 / 代謝行使漂移（surface GAP-X1 / GAP-X2） -------------
    # (B-i) 元迴圈生成器是否零引用具身工具鏈（GAP-X1 未接地）。
    existing: List[str] = []
    grounded: List[str] = []
    for rel in META_LOOP_GENERATOR_RELPATHS:
        p = FRAMEWORK_ROOT / rel
        if not p.exists():
            continue
        existing.append(rel)
        try:
            src = p.read_text(encoding="utf-8")
        except Exception:  # pragma: no cover
            continue
        # 只看程式碼部分（剝除每行 `#` 之後的註解），避免「註解提及但未真引用」的假陰性。
        code_only = "\n".join(line.split("#", 1)[0] for line in src.splitlines())
        if any(name in code_only for name in EMBODIED_TOOLCHAIN_NAMES):
            grounded.append(rel)
    if existing and not grounded:
        report.add(Finding(
            ff="FF-16", severity=SEVERITY_WARN, fingerprint="ff16-meta-loop-ungrounded",
            title=f"元迴圈 {len(existing)} 個生成器模組零引用具身評估器工具鏈（GAP-X1 未接地）",
            detail="META_FSM 自我演化判定只引用合成語料 oracle，從不啟動沙箱 / 查真實日誌 / 跑真 App；"
                   "生成-評估分離在元迴圈層未接地（advisory，鏡像 FF-2/13 漸進哲學，不阻擋收斂）。",
            evidence=existing[:12] + [f"具身工具鏈={list(EMBODIED_TOOLCHAIN_NAMES)}"]))

    # (B-ii) GC 是否從未產出退役提案（GAP-X2 代謝肌肉從未收縮）。
    gc_proposals = sorted(GC_REPORTS_DIR.glob("SCAFFOLD-ROI-*.md")) if GC_REPORTS_DIR.exists() else []
    if not gc_proposals:
        report.add(Finding(
            ff="FF-16", severity=SEVERITY_WARN, fingerprint="ff16-gc-never-fired",
            title="鷹架代謝 GC 從未產出退役 ROI 提案（GAP-X2 代謝肌肉從未收縮）",
            detail="sdd-gc / scaffold_gc 制度齊備但 build/reports/gc/ 無 SCAFFOLD-ROI 提案；"
                   "「大膽移除冗餘鷹架」（Anthropic）寫在憲法（Rule 9.20）卻從未行使（advisory，不阻擋）。",
            evidence=[str(GC_REPORTS_DIR)]))

    if structural_ok:
        report.add(Finding(
            ff="FF-16", severity=SEVERITY_INFO, fingerprint="ff16-ok",
            title=f"具身評估器 & 鷹架代謝工具鏈引用接地完整（{len(EMBODIED_AGENT_SPECS)} 組）",
            detail="系統級 agent 宣告的 runtime 模組 + FSM 狀態皆解析；鎖住具身/代謝鷹架不被 bit-rot/"
                   "誤刪（structural pass，nightly-strict ENFORCING）。advisory(B) 另記元迴圈接地 backlog。",
        ))


# ---------------------------------------------------------------------------
# FF-17：Copy-on-Evolve 演化版必納官方閘門（DEF-10-002b 固化；引用完整性家族延伸）
# ---------------------------------------------------------------------------
# 背景（DEF-03-001）：官方 CI 閘門 `scripts/ci-gate.sh` 過去 FW_DIR 寫死 v0.01 →
# 永遠只測凍結基線，實際承載演化的最新版（EVOLUTION_LOG「可修改版本」）從不進
# CI/pre-push，與「地端 = CI = ubuntu-latest 同一組檢查」初衷相違。improving_04 以
# 「凍結基線 + 自動偵測最新演化版」雙軌點修。DEF-10-002(b) 要求把該不變量「固化」為
# fitness function，取代逐輪點修——本 FF 即此固化：以結構守門斷言官方閘門**動態涵蓋
# 磁碟最新演化版**，若有人把 ci-gate.sh 退回寫死單版（DEF-03-001 回歸）即 structural fail。
#
# 與 FF-14（CI workflow→工具模組引用一致性）同源：皆靜態讀 CI 腳本文字、純讀無副作用、
# 跨平台（不執行 shell，避免引入新 subprocess 攻擊面與 OS 相依）。
_CI_GATE_LATEST_GLOB_RE = re.compile(r"ls\s+-d\s+AISDLC_SDD_v0\.0\*")
_CI_GATE_SORT_V_RE = re.compile(r"sort\s+-V")
_CI_GATE_TAIL_RE = re.compile(r"tail\s+-1")
_CI_GATE_APPEND_LATEST_RE = re.compile(r"FW_VERSIONS\+=\([^)]*LATEST")


def _latest_version_dir() -> Optional[str]:
    """回傳磁碟上語意版本最高的 AISDLC_SDD_v0.0* 目錄名（無則 None）。"""
    dirs = sorted((p.name for p in PROJECT_ROOT.glob("AISDLC_SDD_v0.0*") if p.is_dir()),
                  key=lambda n: [int(x) if x.isdigit() else x
                                 for x in re.split(r"[._]", n)])
    return dirs[-1] if dirs else None


def check_ff17_evolution_version_gate_coverage(report: FitnessReport) -> None:
    if not CI_GATE_PATH.exists():
        report.add(Finding(
            ff="FF-17", severity=SEVERITY_INFO, fingerprint="ff17-no-gate",
            title="略過演化版閘門涵蓋檢查", detail=f"未找到官方閘門腳本 {CI_GATE_PATH}。"))
        return

    latest = _latest_version_dir()
    if latest is None:
        report.add(Finding(
            ff="FF-17", severity=SEVERITY_INFO, fingerprint="ff17-no-versions",
            title="略過演化版閘門涵蓋檢查", detail="磁碟上無 AISDLC_SDD_v0.0* 版本目錄。"))
        return

    try:
        gate = CI_GATE_PATH.read_text(encoding="utf-8", errors="replace")
    except Exception:  # pragma: no cover - 讀檔防護
        report.add(Finding(
            ff="FF-17", severity=SEVERITY_FAIL, fingerprint="ff17-unreadable",
            title="官方閘門腳本無法讀取", detail=f"{CI_GATE_PATH} 存在但讀取失敗。",
            evidence=[str(CI_GATE_PATH)]))
        return

    # 動態最新版偵測慣用語（DEF-03-001 雙軌）：ls -d AISDLC_SDD_v0.0* | sort -V | tail -1
    # 併入 FW_VERSIONS。四個錨點皆在 = 最新演化版恆被官方閘門涵蓋（即便磁碟新增 v0.0(X+1)
    # 也自動納入，無需改腳本）。任一缺失 = 退回靜態寫死風險 → DEF-03-001 回歸。
    missing = []
    if not _CI_GATE_LATEST_GLOB_RE.search(gate):
        missing.append("動態版本 glob（ls -d AISDLC_SDD_v0.0*）")
    if not _CI_GATE_SORT_V_RE.search(gate):
        missing.append("語意版本排序（sort -V）")
    if not _CI_GATE_TAIL_RE.search(gate):
        missing.append("取最高版（tail -1）")
    if not _CI_GATE_APPEND_LATEST_RE.search(gate):
        missing.append("最新版併入版本陣列（FW_VERSIONS+=(…LATEST…)）")

    if missing:
        report.add(Finding(
            ff="FF-17", severity=SEVERITY_FAIL, fingerprint="ff17-static-pin",
            title="官方閘門未動態涵蓋最新演化版（DEF-03-001 回歸風險）",
            detail=f"最新演化版為 {latest}，但 {CI_GATE_PATH.name} 缺動態偵測慣用語 → "
                   "演化版恐被排除於官方 CI/pre-push 外（與「地端=CI 同一組檢查」相違）。"
                   "應恢復「凍結基線 + 自動偵測最新版」雙軌（見 DEF-03-001/DEF-10-002b）。",
            evidence=missing))
        return

    report.add(Finding(
        ff="FF-17", severity=SEVERITY_INFO, fingerprint="ff17-ok",
        title=f"官方閘門動態涵蓋最新演化版（{latest}）",
        detail=f"{CI_GATE_PATH.name} 以「凍結基線 + 動態偵測最新版」雙軌恆納入最新演化版；"
               "新增 v0.0(X+1) 自動入閘，DEF-03-001 點修已固化為結構不變量。"))


# ---------------------------------------------------------------------------
# 執行器
# ---------------------------------------------------------------------------
ALL_CHECKS = {
    "FF-1": check_ff1_fsm_state_universe,
    "FF-2": check_ff2_governance_migration,
    "FF-3": check_ff3_orphan_state_files,
    "FF-4": check_ff4_observation_parity,
    "FF-5": check_ff5_claudemd_rule9_size,
    "FF-6": check_ff6_doc_link_integrity,
    "FF-7": check_ff7_agent_workflow_skill_refs,
    "FF-8": check_ff8_rule_enforcement_traceability,
    "FF-9": check_ff9_scaffold_roi,
    "FF-10": check_ff10_rule_trigger_reachability,
    "FF-11": check_ff11_skill_frontmatter,
    "FF-12": check_ff12_severity_placement,
    "FF-13": check_ff13_agent_yaml_schema,
    "FF-14": check_ff14_workflow_module_refs,
    "FF-15": check_ff15_docs_template_index,
    "FF-16": check_ff16_embodied_evaluator_grounding,
    "FF-17": check_ff17_evolution_version_gate_coverage,
}


def write_trend(report: FitnessReport, path: Path) -> None:
    """R4：把本次 score 追加進趨勢檔（YAML list）。

    唯此函式有副作用 —— 所有 FF 檢查本身保持唯讀、無副作用。僅 `--trend` 旗標
    觸發，讓 SELF_EVOLUTION 可量化框架架構熵的長期趨勢（score_before/after）。
    """
    import datetime

    entry = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "score": report.score(),
        "n_fail": len(report.fails),
        "n_warn": len(report.warns),
        "fingerprints": sorted(f.fingerprint for f in report.findings
                               if f.severity != SEVERITY_INFO),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import yaml  # PyYAML（框架既有相依）
        existing = []
        if path.exists():
            loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                existing = loaded
        existing.append(entry)
        path.write_text(yaml.safe_dump(existing, allow_unicode=True, sort_keys=False),
                        encoding="utf-8")
    except Exception:  # pragma: no cover - 退化路徑：不阻擋主流程
        with path.with_suffix(".jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run_fitness(only: Optional[List[str]] = None) -> FitnessReport:
    report = FitnessReport()
    for ff_id, fn in ALL_CHECKS.items():
        if only and ff_id not in only:
            continue
        fn(report)
    return report


_ICON = {SEVERITY_INFO: "✅", SEVERITY_WARN: "🟡", SEVERITY_FAIL: "🔴"}


def render_text(report: FitnessReport) -> str:
    lines = ["# 架構適應度報告（arch_fitness）", ""]
    lines.append(f"加權缺陷分數（越低越健康）：**{report.score()}**　"
                 f"｜ 🔴 fail={len(report.fails)}　🟡 warn={len(report.warns)}")
    lines.append("")
    for f in report.findings:
        lines.append(f"{_ICON.get(f.severity, '•')} **[{f.ff}] {f.title}**")
        lines.append(f"    {f.detail}")
        for e in f.evidence:
            lines.append(f"      - {e}")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="AISDLC-SDD 架構適應度函式")
    ap.add_argument("--json", metavar="PATH", help="將結構化結果寫入 JSON 檔")
    ap.add_argument("--only", nargs="*", choices=list(ALL_CHECKS),
                    help="僅執行指定 FF（預設全部）")
    ap.add_argument("--strict", action="store_true",
                    help="有 structural fail 時回傳 exit 2（CI 阻擋用）")
    ap.add_argument("--quiet", action="store_true", help="僅輸出 JSON，不印報告")
    ap.add_argument("--trend", nargs="?", const="build/reports/fse/TREND.yaml",
                    metavar="PATH",
                    help="將本次 score 追加進趨勢檔（R4，預設 build/reports/fse/TREND.yaml）")
    args = ap.parse_args(argv)

    # Windows 主控台預設 cp950/cp1252 無法輸出 emoji / 中文 — 強制 UTF-8。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - 舊版 / 非 TextIO
            pass

    report = run_fitness(only=args.only)

    if args.json:
        payload = {
            "score": report.score(),
            "n_fail": len(report.fails),
            "n_warn": len(report.warns),
            "findings": [asdict(f) for f in report.findings],
        }
        Path(args.json).write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                   encoding="utf-8")

    if args.trend:
        tp = Path(args.trend)
        if not tp.is_absolute():
            tp = FRAMEWORK_ROOT / tp
        write_trend(report, tp)

    if not args.quiet:
        print(render_text(report))

    if args.strict and report.fails:
        return 2
    if report.warns:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
