#!/usr/bin/env python3
"""ONBOARDING.md §7「live 基線格」產生器 ＋ 新鮮度稽核（generate + --check 慣例）。

WHY 存在（R60 SD-R60-09）：
  R60 為 §7 的 LOC 那一格加了新鮮度鎖，但**只有 `--check` 半邊、沒有產生器**——
  於是「任何動到 `AutoClaude/autoclaude/` 行數的變更」都直接接成根層閘門紅燈 ＋
  必須手工回填一份文件，而本 repo 對「機器可算出來的數字」的既有形狀是
  **產生器 ＋ `--check`**（`AutoClaude/CLAUDE.md` 的 `[Architecture Snapshot]` ↔
  `AutoClaude/tools/snapshot_sync.py`，CI job `claude-md-budget`）。本檔補上缺的
  那半邊：`--write` 一鍵回填，`--check` 供閘門與測試消費，兩者共用同一份取值邏輯，
  不可能一邊算出 A、另一邊算出 B。

守什麼（受管的 live 格；擴充只需在 `_SPECS` 加一筆，判定邏輯不用改）：
  1. `loc-baseline-live:`      → `AutoClaude/tools/check_loc_budget.py --json`
                                 的 `total` / `cap` / `violations`
  2. `rootunit-baseline-live:` → `tools/run_root_unittests.py` 的 `MIN_TESTS`
                                 （§7 那一格的「N tests OK」）

R60 round 3 補的兩件事（四方複審 round 2 全數 REJECT 的兩個根因）：
  A. **受鎖行的散文也要受管**（ARCH-R60R2-03／SA-R60R2-02／SD-R60-R2-03／QA2-R60-02，
     四方獨立全數命中）：round 1 落地本產生器後，受鎖行的 token 已是 845，而**同一行的
     散文仍寫「R60=756」**。⇒ **產生器 ＋ `--check` 只保證「被抽取的那個 token」新鮮，
     完全不保證同一行的散文新鮮**——這是本 repo 對「機械鎖已落地」的認定門檻必須修正的
     地方（DEF-101-562）。兩道判準（見 `prose_problems()`）：
       (1) **受管值不得在受鎖行出現第二次**（≥3 位數才判，見該函式的位數門檻 WHY）：
           散文裡複製一份當輪值，下一次變動時它就是新的 stale 站點。
       (2) **`R<輪號>=<數字>` 形態的同量宣稱**：值 ≠ live 者必須登記進 `Spec.historical`
           並附 WHY，否則紅。歷史值放行、當輪值一律不得寫進散文。
  B. **表②（dated snapshot）從「靠人記得」升為「一條指令 ＋ 因果式 stale 觸發器」**
     （ARCH-R60R2-02③／SA-R60R2-02②）：round 1 填了 v0.30=1736，round 2 動了 v0.30
     測試樹使實測變 1747，**沒人記得回填**，而表頭同時宣稱「四格皆經獨立覆核」⇒ 假宣稱。
       - `--write --with-slow`：實跑 ci-gate（解析其 `逐軌計數：vX:N` 自證行）＋ AutoClaude
         pytest，四格一次填完（`_SLOW_SPECS`）。
       - `--check-snapshot`：重算四套**測試樹內容指紋**與文件記載比對，指紋一變即判
         presumed stale。判準是**因果的**（計數只可能因測試樹變動而變），同
         `ADR-SD09-011`「把證據從日曆解綁、改綁源碼變動」的既有先例。
       - 接線刻意只到 **pre-push**（收輪＝push 時點付這個代價才合理），**不**接根層 unittest
         閘門——那支每輪跑數十次，會養成忽略紅燈的習慣。
     🔴 **對 ARCH-R60R2-06（護欄層成長過快）的正面回應**：本次擴充**零新增鎖檔、零新增
     測試檔**——全部落在本檔既有 `_SPECS` 機制與既有
     `tools/tests/test_doc_loc_baseline_freshness_r60.py` 內，且淨效果是**把表② 那 4 格
     「零機制」的欄位收進既有機制** ⇒ 未受檢面淨減少。這是對「禁止新增鎖、只准合併」
     的遵守，不是規避。

🔴 判準邊界（誠實劃界）：
  - **只管帶錨點的那一行**。§7／§9 其他地方的數字是有標日期的歷史快照（如 R57 註的
    `total=20356`），依本 repo「時代快照不納管」慣例（見
    `tools/check_pytest_baseline_sites.py` docstring）刻意不回填、也刻意不鎖。
  - **指紋只覆蓋測試樹**（`*.py` 內容）。生產碼變動改變 `parametrize` 來源、docker daemon
    可用性、平台差異都能改變計數而指紋不動 ⇒ 它是 stale 的**充分觸發器、非必要條件**
    （會漏、不會冤）。要它變成必要條件就得付整套重測的代價，那正是表②沒有 live 鎖的原因。
  - 每個欄位的正則在受鎖行上必須**恰好命中一次**：0 次＝敘述被改寫成抽不到的形態、
    ≥2 次＝抽錯欄（例如同一列 macOS 欄與 Windows 欄都寫了 `total=`），兩者皆
    fail-loud。這一條是 R60 SA-R60-01 的直接教訓：原鎖用 `search()` 取第一個命中，
    讀到的其實是 macOS 欄，而它恰好與 Windows 欄同值，所以看不出來。
  - `skipped=N`（根層測試那格的另一半）與 `8 kept / 0 broken`（lint-imports）
    **不在管理範圍**：前者無現場取值來源、後者要另跑 import-linter。如實揭露，
    未來要納管就在該處加新錨點 ＋ 在 `_SPECS` 補一筆。
  - **`--check` 不是 LOC 閘門**：`check_loc_budget.py --json` 在 LOC 破線時回 rc=1
    但**仍會印出完整 JSON**，本檔照樣解析並比對，且當 `violations > 0` 時訊息會明說
    「這是 LOC 閘門自己紅、不是文件 stale」，避免錯誤定位（SD-R60-09 附帶項）。

用法：
  python tools/sync_onboarding_baselines.py                  # --check（預設，表①）；stale 即 exit 1
  python tools/sync_onboarding_baselines.py --write          # 一鍵回填表①（bytes 層 LF 寫入）
  python tools/sync_onboarding_baselines.py --check-snapshot # 表② 指紋比對（毫秒級，pre-push 消費）
  python tools/sync_onboarding_baselines.py --write --with-slow  # 表①＋表②＋指紋全回填（分鐘級）
  python tools/sync_onboarding_baselines.py --json           # 機讀報表（含表② 與指紋）
測試：tools/tests/test_doc_loc_baseline_freshness_r60.py
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ONBOARDING = _REPO_ROOT / "ONBOARDING.md"
_LOC_TOOL = _REPO_ROOT / "AutoClaude" / "tools" / "check_loc_budget.py"


@dataclass(frozen=True)
class Field:
    """一個受管數字：抽取正則（必須恰一群組）＋ 回填時的字面樣板。"""

    name: str
    pattern: re.Pattern[str]
    template: str  # 以 {v} 帶入實測值


@dataclass(frozen=True)
class Spec:
    """一個受管的 live 格：錨點 → 欄位集合 ＋ 取值來源 ＋ 散文歷史值白名單。"""

    anchor: str
    fields: tuple[Field, ...]
    source: str  # 人讀的取值來源說明（訊息用）
    # 受鎖行散文裡允許出現的 `R<輪號>=<數字>` 同量歷史宣稱。鍵＝輪號字串、值＝(數字, WHY)。
    # 判準見 prose_problems()：不在此表且 ≠ live 值者一律紅。
    historical: tuple[tuple[str, int, str], ...] = ()


# 受管值在受鎖行重複出現的判定門檻（位數）。
# WHY 3：`violations=0`／`8 kept` 這類 1~2 位數在散文裡是無關的巧合同值（「8 支 pgid」
# 「1 支 symlink」），對它們硬判會製造大量誤紅，而它們 stale 的危害近零。3 位數以上
# （845 tests／20361 total）才是真正會誤導讀者的量。門檻寫在這裡而非散文裡（本檔自己也
# 受「不得把可機械算出的數字寫進散文」那條紀律管）。
_PROSE_DUP_MIN_DIGITS = 3

# 散文裡的「R<輪號>=<數字>」同量宣稱形態（`**` 是 markdown 強調包裝）。
_PROSE_ROUND_CLAIM_RE = re.compile(r"R(\d+)\s*=\s*\*{0,2}(\d+)")


_SPECS: tuple[Spec, ...] = (
    Spec(
        anchor="loc-baseline-live:",
        fields=(
            Field("total", re.compile(r"total=(\d+)"), "total={v}"),
            Field("cap", re.compile(r"cap=(\d+)"), "cap={v}"),
            Field("violations", re.compile(r"violations=(\d+)"), "violations={v}"),
        ),
        source="AutoClaude/tools/check_loc_budget.py --json",
    ),
    Spec(
        anchor="rootunit-baseline-live:",
        fields=(Field("tests", re.compile(r"(\d+) tests OK"), "{v} tests OK"),),
        source="tools/run_root_unittests.py 的 MIN_TESTS",
        historical=(
            ("57", 616, "R57 macOS 實機量測（ONBOARDING §7 表① macOS 欄同值）"),
            ("59", 661, "R59 收尾實測，見 DEF-101-519"),
        ),
    ),
)


class BaselineToolError(AssertionError):
    """取值來源本身壞掉（非「文件 stale」）——必須與 stale 分開回報。"""


# ─────────────────────────── 文件側（純函式） ───────────────────────────


def anchored_line(text: str, anchor: str) -> str:
    """取唯一帶錨點的行；0 行或多行皆 fail-loud（文件改組須同步本案）。"""
    lines = [line for line in text.splitlines() if anchor in line]
    if len(lines) != 1:
        raise AssertionError(
            f"ONBOARDING.md 的基線錨點「{anchor}」命中 {len(lines)} 行（預期恰 1）"
            f"——錨點被刪除或被複製都會讓本鎖失去鑑別力，故此處 fail-loud；"
            f"若刻意改組 §7，請把錨點註解搬到新的基線格上"
        )
    return lines[0]


def parse_documented(line: str, spec: Spec) -> dict[str, int]:
    """從受鎖行抽出文件字面值；欄位缺席或重複命中皆 fail-loud。"""
    values: dict[str, int] = {}
    problems: list[str] = []
    for field in spec.fields:
        found = field.pattern.findall(line)
        if len(found) != 1:
            problems.append(f"{field.name}（命中 {len(found)} 次，預期恰 1）")
        else:
            values[field.name] = int(found[0])
    if problems:
        raise AssertionError(
            f"受鎖行（錨點 {spec.anchor}）的欄位抽取失敗：{problems}。\n"
            f"  0 次＝敘述被改寫成本鎖抽不到的形態；≥2 次＝同一列有多個同形數字"
            f"（例如 macOS 欄與 Windows 欄都寫了同一個欄位）⇒ 會抽錯欄。\n"
            f"  兩者都不得靜默放行（R60 SA-R60-01：原鎖取第一個命中，讀到的其實是"
            f"macOS 欄）。\n  行文：{line.strip()[:200]}"
        )
    return values


def prose_problems(line: str, spec: Spec, live: dict[str, int]) -> list[str]:
    """受鎖行的**散文**新鮮度判準（R60 round 3，DEF-101-562）。純函式，供測試以合成行驅動。

    兩道判準（WHY 見檔頭 A）：
      (1) 受管值不得在受鎖行出現第二次（≥ `_PROSE_DUP_MIN_DIGITS` 位數才判）。
      (2) `R<輪號>=<數字>` 形態的同量宣稱，值 ≠ live 者必須在 `spec.historical` 登記。
    """
    problems: list[str] = []

    for field in spec.fields:
        value = live[field.name]
        digits = str(value)
        if len(digits) < _PROSE_DUP_MIN_DIGITS:
            continue
        occurrences = len(re.findall(rf"(?<!\d){re.escape(digits)}(?!\d)", line))
        if occurrences > 1:
            problems.append(
                f"受管值 {field.name}={value} 在受鎖行出現 {occurrences} 次（預期恰 1）"
                f"——第二次就是下一個 stale 站點：本鎖只會回填被抽取的那一個 token，"
                f"散文裡那一份下次變動時不會被更新。\n"
                f"    處置：把散文那份改成指向左欄的寫法（例「見本格 live 值」「見左欄」）；"
                f"若確為無關的巧合同值，同樣改寫散文使其字面不同（本鎖刻意不設個別豁免——"
                f"豁免表本身就是下一個 stale 站點）"
            )

    allowed = {(rnd, val) for rnd, val, _why in spec.historical}
    live_values = set(live.values())
    for rnd, raw in _PROSE_ROUND_CLAIM_RE.findall(line):
        val = int(raw)
        if val in live_values or (rnd, val) in allowed:
            continue
        problems.append(
            f"受鎖行散文有同量宣稱「R{rnd}={val}」，但它既不等於任何 live 值"
            f" {sorted(live_values)}、也不在 Spec.historical 白名單內。\n"
            f"    這正是 R60 round 2 四方全數命中的形態：受鎖 token 已回填為當輪實測，"
            f"而散文仍留著同輪的較舊宣稱（DEF-101-562）。\n"
            f"    處置：歷史值 → 在 `_SPECS` 的 `historical` 登記 (輪號, 值, WHY)；"
            f"當輪值 → **不要寫進散文**，改寫成「見本格 live 值」"
        )
    return problems


def render(text: str, measured: dict[str, dict[str, int]]) -> str:
    """把受鎖行的數字就地換成實測值，回傳新文件內容（不寫檔）。"""
    lines = text.split("\n")
    for spec in _SPECS:
        values = measured[spec.anchor]
        target = anchored_line(text, spec.anchor)
        parse_documented(target, spec)  # 先確認可抽取（含恰一次），再改寫
        idx = next(i for i, line in enumerate(lines) if spec.anchor in line)
        new_line = lines[idx]
        for field in spec.fields:
            new_line = field.pattern.sub(
                field.template.format(v=values[field.name]), new_line, count=1
            )
        lines[idx] = new_line
    return "\n".join(lines)


# ─────────────────────────── 取值來源側 ───────────────────────────


def measure_loc() -> dict[str, int]:
    """實跑 check_loc_budget.py --json。rc=1（LOC 破線）仍會有完整 JSON，照樣解析。

    violations 的算式刻意鏡射該工具純文字輸出的 `violations=` 欄位
    （absolute + tier + special + total 破線，見 check_loc_budget.check()），
    這樣文件裡照抄工具輸出的人不會被本鎖誤殺。
    """
    proc = subprocess.run(
        [sys.executable, str(_LOC_TOOL), "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(_REPO_ROOT),
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise BaselineToolError(
            f"check_loc_budget.py --json 沒有印出可解析的 JSON（rc={proc.returncode}）"
            f"——這是**取值來源壞掉**，不是文件 stale；請先修那件事。\n"
            f"stdout: {proc.stdout[-800:]}\nstderr: {proc.stderr[-800:]}"
        ) from exc
    return {
        "total": int(payload["total"]),
        "cap": int(payload["cap"]),
        "violations": (
            len(payload["absolute_violations"])
            + len(payload["tier_violations"])
            + len(payload["special_violations"])
            + (1 if payload["total_violation"] else 0)
        ),
    }


def measure_rootunit() -> dict[str, int]:
    """讀 tools/run_root_unittests.py 的 MIN_TESTS（同一份 repo 的既成 SSOT）。

    刻意用 import 而非重跑整套 unittest：MIN_TESTS 就是「收輪時填實測值」的釘選
    （見該檔第 38 行的重釘紀律），文件與它必須是同一個數字——R60 SA-R60-01 抓到的
    正是「MIN_TESTS 已重釘 756 而 §7 仍寫 661」這種同 repo 兩種說法。
    """
    import run_root_unittests  # noqa: PLC0415  # 延後 import：避免 CLI 未用到時付代價

    return {"tests": int(run_root_unittests.MIN_TESTS)}


_MEASURERS = {
    "loc-baseline-live:": measure_loc,
    "rootunit-baseline-live:": measure_rootunit,
}


def measure_all() -> dict[str, dict[str, int]]:
    return {spec.anchor: _MEASURERS[spec.anchor]() for spec in _SPECS}


# ──────────────── 表②（dated snapshot）：一條指令回填 ＋ 指紋觸發器 ────────────────
# WHY 分成 _SLOW_SPECS 而非塞進 _SPECS：這四格要實跑整套測試（分鐘級），不能進根層
# unittest 閘門的預設路徑。詳見檔頭 B。

_FINGERPRINT_ANCHOR = "snapshot-fingerprints:"
_FP_LEN = 12  # sha256 前 12 hex；碰撞機率對「偵測有人改了測試樹」這個用途遠足夠

# 指紋覆蓋的測試樹：鍵＝文件裡的欄位名，值＝(相對路徑, glob)。
_FINGERPRINT_TREES: tuple[tuple[str, str, str], ...] = (
    ("v001", "AISDLC_SDD/AISDLC_SDD_v0.01/tools/fsm_runtime/tests", "*.py"),
    ("v030", "AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/tests", "*.py"),
    ("scripts", "AISDLC_SDD/scripts/tests", "*.py"),
    ("autoclaude", "AutoClaude/tests", "**/*.py"),
)


@dataclass(frozen=True)
class SlowSpec:
    """一個表② 的格：錨點 → 欄位 ＋ 該格的量測器鍵。"""

    anchor: str
    fields: tuple[Field, ...]
    measurer: str
    source: str


_SLOW_SPECS: tuple[SlowSpec, ...] = (
    SlowSpec(
        anchor="autoclaude-pytest-snapshot:",
        fields=(
            # 以 `**` 包裝限定在 Windows 欄；macOS 欄同形但不加粗（實測恰一次命中）。
            # 🔴 兩個欄位在同一段字上，故一律用**零寬斷言**框定上下文、只替換數字本身：
            # 若把 `**` 或 ` passed / N skipped**` 納入 match，第一次 sub 就會吃掉第二個
            # 欄位所需的上下文 ⇒ 第二次 sub 命中 0 次而 fail-loud（本檔的斷言當場抓到過）。
            Field("passed", re.compile(r"(?<=\*\*)(\d+)(?= passed / \d+ skipped\*\*)"), "{v}"),
            Field("skipped", re.compile(r"(?<= passed / )(\d+)(?= skipped\*\*)"), "{v}"),
        ),
        measurer="autoclaude_pytest",
        source="cd AutoClaude && python -m pytest tests/ -q（plain 形態）",
    ),
    SlowSpec(
        anchor="cigate-v001-snapshot:",
        fields=(Field("passed", re.compile(r"\*\*(\d+)\*\*"), "**{v}**"),),
        measurer="cigate_v001",
        source="bash AISDLC_SDD/scripts/ci-gate.sh 的『逐軌計數』自證行",
    ),
    SlowSpec(
        anchor="cigate-v030-snapshot:",
        fields=(Field("passed", re.compile(r"\*\*(\d+)\*\*"), "**{v}**"),),
        measurer="cigate_v030",
        source="bash AISDLC_SDD/scripts/ci-gate.sh 的『逐軌計數』自證行",
    ),
    SlowSpec(
        anchor="cigate-scripts-snapshot:",
        fields=(Field("passed", re.compile(r"\*\*(\d+)\*\*"), "**{v}**"),),
        measurer="cigate_scripts",
        source="bash AISDLC_SDD/scripts/ci-gate.sh 的『逐軌計數』自證行",
    ),
)


def tree_fingerprint(rel_dir: str, pattern: str) -> str:
    """測試樹內容指紋：sha256(排序後的 相對路徑 + 檔案 bytes)。

    刻意**不用 git**：`git rev-parse HEAD:<path>` 只看 HEAD，untracked／未 commit 的新測試
    檔不算進去 ⇒ 一輪內新增測試會漏觸發（本 repo 已有「worktree 隔離看不到未 commit 修改」
    這條踩過的教訓）。純檔案內容雜湊對 tracked／untracked 一視同仁。
    """
    root = _REPO_ROOT / rel_dir
    if not root.is_dir():
        raise BaselineToolError(
            f"指紋來源目錄不存在：{rel_dir}——目錄被搬動時必須同步 `_FINGERPRINT_TREES`，"
            f"故此處 fail-loud 而非靜默回傳空指紋"
        )
    digest = hashlib.sha256()
    for path in sorted(root.glob(pattern)):
        if not path.is_file():
            continue
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:_FP_LEN]


def measure_fingerprints() -> dict[str, str]:
    return {name: tree_fingerprint(rel, pat) for name, rel, pat in _FINGERPRINT_TREES}


def parse_fingerprints(text: str) -> dict[str, str]:
    """從錨點行抽出文件記載的指紋；欄位缺席即 fail-loud。"""
    line = anchored_line(text, _FINGERPRINT_ANCHOR)
    values: dict[str, str] = {}
    missing: list[str] = []
    for name, _rel, _pat in _FINGERPRINT_TREES:
        found = re.findall(rf"{re.escape(name)}=([0-9a-zA-Z]+)", line)
        if len(found) != 1:
            missing.append(f"{name}（命中 {len(found)} 次，預期恰 1）")
        else:
            values[name] = found[0]
    if missing:
        raise AssertionError(
            f"`{_FINGERPRINT_ANCHOR}` 行的指紋欄位抽取失敗：{missing}\n"
            f"  一鍵回填：python tools/sync_onboarding_baselines.py --write --with-slow\n"
            f"  行文：{line.strip()[:240]}"
        )
    return values


def check_snapshot(text: str) -> list[str]:
    """表② 的 presumed-stale 判準：測試樹指紋一變即紅。純函式（讀磁碟算指紋）。"""
    documented = parse_fingerprints(text)
    live = measure_fingerprints()
    problems: list[str] = []
    for name, _rel, _pat in _FINGERPRINT_TREES:
        if documented[name] != live[name]:
            problems.append(
                f"[{name}] 測試樹指紋 {documented[name]} → {live[name]}"
                f"（測試樹已變動）⇒ ONBOARDING.md §7 表② 該格判定 **presumed stale**。\n"
                f"    這是因果判準：測試計數只可能因測試樹變動而變。"
                f"R60 round 1 填了 v0.30 的當時值、round 2 動了該測試樹使實測改變而沒人回填，"
                f"就是本觸發器要擋的形態（DEF-101-563；具體數字見帳本該列，此處刻意不寫死）。\n"
                f"    回填：python tools/sync_onboarding_baselines.py --write --with-slow"
            )
    return problems


def render_fingerprints(text: str, live: dict[str, str]) -> str:
    line = anchored_line(text, _FINGERPRINT_ANCHOR)
    new_line = line
    for name, _rel, _pat in _FINGERPRINT_TREES:
        new_line = re.sub(
            rf"{re.escape(name)}=[0-9a-zA-Z]+", f"{name}={live[name]}", new_line, count=1
        )
    return text.replace(line, new_line, 1)


def _run_cigate() -> dict[str, int]:
    """實跑 ci-gate 並解析它自己的『逐軌計數』自證行（DEF-06-001 就是為取證而加的）。

    刻意解析那一行而非自己數 pytest 輸出：它是 ci-gate 的 SSOT，若格式改了要 fail-loud，
    不要在這裡另造一份計數邏輯（否則就是同一個量兩個算法＝本輪一直在治的病）。
    """
    # 🔴 **不得寫裸 `"bash"`**（R60 round 3 主控自己踩到，DEF-101-588）：本機 PATH 上
    # `bash` 解析到的是 **WSL 的 `C:\\Windows\\System32\\bash.exe`**，不是 Git Bash。
    # 用它跑 repo 的 `.sh` 會進 Linux 子系統，`python` 解析成 `/mnt/c/.../pyenv-win/shims/python`
    # ——那是一支 CRLF 的 Windows 批次腳本，於是報 `/bin/sh^M: bad interpreter`、rc=126。
    # 這與同輪 Pkg-P10 在 `Find-GitBash.ps1` 修掉的是**同一個缺陷**，而我在新寫的程式碼裡
    # 又犯了一次 ⇒ 一律走既有 SSOT `integration_gate_core.find_git_bash()`，不自寫第二份。
    import integration_gate_core  # noqa: PLC0415  # 延後 import：CLI 未用到時不付代價

    bash = integration_gate_core.find_git_bash()
    if not bash:
        raise BaselineToolError(
            "找不到 Git Bash（`integration_gate_core.find_git_bash()` 回 None）——"
            "這是**取值來源壞掉**，不是文件 stale。ci-gate.sh 必須以 Git Bash 執行；"
            "PATH 上的 `bash` 在本機可能是 WSL 佔位（System32），用它會進 Linux 子系統。"
        )
    proc = subprocess.run(
        [bash, "scripts/ci-gate.sh"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(_REPO_ROOT / "AISDLC_SDD"),
    )
    match = re.search(r"逐軌計數：(.+)", proc.stdout)
    if proc.returncode != 0 or not match:
        raise BaselineToolError(
            f"ci-gate.sh 未成功或找不到『逐軌計數：』自證行（rc={proc.returncode}）"
            f"——這是**取值來源壞掉**，不是文件 stale；請先修那件事。\n"
            f"stdout 尾段: {proc.stdout[-1200:]}\nstderr 尾段: {proc.stderr[-600:]}"
        )
    counts: dict[str, int] = {}
    for token in match.group(1).split():
        key, _, val = token.rpartition(":")
        if key and val.isdigit():
            counts[key] = int(val)
    wanted = {
        "cigate_v001": "AISDLC_SDD_v0.01",
        "cigate_v030": "AISDLC_SDD_v0.30",
        "cigate_scripts": "scripts/tests",
    }
    missing = [k for k in wanted.values() if k not in counts]
    if missing:
        raise BaselineToolError(
            f"『逐軌計數』行缺少軌道 {missing}（實得 {counts}）——ci-gate 的軌道組成變了，"
            f"請同步本檔的 `wanted` 對照表"
        )
    return {name: counts[track] for name, track in wanted.items()}


def _run_autoclaude_pytest() -> dict[str, int]:
    """plain 形態實跑 AutoClaude 全套（與 §7 表② 該格宣告的量測形態逐字一致）。

    ⚠️ 刻意**不加** `PYTHONDONTWRITEBYTECODE=1 -p no:cacheprovider`：加了會量到不同的數字
    （ARCH-R60-04 的整個爭點），而該格自陳「以 plain 形態量得」。形態與宣告必須同一件事。
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(_REPO_ROOT / "AutoClaude"),
    )
    match = re.search(r"(\d+) passed, (\d+) skipped", proc.stdout)
    if proc.returncode != 0 or not match:
        raise BaselineToolError(
            f"AutoClaude pytest 未全綠或找不到『N passed, M skipped』（rc={proc.returncode}）"
            f"——取值來源壞掉，不是文件 stale。\nstdout 尾段: {proc.stdout[-1200:]}"
        )
    return {"passed": int(match.group(1)), "skipped": int(match.group(2))}


def measure_slow() -> dict[str, dict[str, int]]:
    """跑一次 ci-gate ＋ 一次 AutoClaude pytest，餵滿全部 `_SLOW_SPECS`（分鐘級）。"""
    cigate = _run_cigate()
    pytest_counts = _run_autoclaude_pytest()
    by_measurer: dict[str, dict[str, int]] = {
        "autoclaude_pytest": pytest_counts,
        "cigate_v001": {"passed": cigate["cigate_v001"]},
        "cigate_v030": {"passed": cigate["cigate_v030"]},
        "cigate_scripts": {"passed": cigate["cigate_scripts"]},
    }
    return {spec.anchor: by_measurer[spec.measurer] for spec in _SLOW_SPECS}


def render_slow(text: str, measured: dict[str, dict[str, int]]) -> str:
    """把表② 四格的數字就地換成實測值（與 render() 同形，共用 Field 樣板機制）。"""
    lines = text.split("\n")
    for spec in _SLOW_SPECS:
        values = measured[spec.anchor]
        anchored_line(text, spec.anchor)  # 錨點唯一性斷言（0 或 ≥2 行皆 fail-loud）
        idx = next(i for i, line in enumerate(lines) if spec.anchor in line)
        new_line = lines[idx]
        for field in spec.fields:
            found = field.pattern.findall(new_line)
            if len(found) != 1:
                raise AssertionError(
                    f"表② 受管欄位 {spec.anchor}/{field.name} 在該行命中 {len(found)} 次"
                    f"（預期恰 1）——0 次＝敘述改成抽不到的形態；≥2 次＝會抽錯欄"
                    f"（例如歸因散文也寫了一份加粗數字）。\n  行文：{new_line.strip()[:240]}"
                )
            new_line = field.pattern.sub(
                field.template.format(v=values[field.name]), new_line, count=1
            )
        lines[idx] = new_line
    return "\n".join(lines)


def slow_documented(text: str) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for spec in _SLOW_SPECS:
        line = anchored_line(text, spec.anchor)
        values: dict[str, int] = {}
        for field in spec.fields:
            found = field.pattern.findall(line)
            if len(found) != 1:
                raise AssertionError(
                    f"表② 受管欄位 {spec.anchor}/{field.name} 命中 {len(found)} 次（預期恰 1）"
                )
            values[field.name] = int(found[0])
        out[spec.anchor] = values
    return out


# ─────────────────────────── 稽核 / CLI ───────────────────────────


def check(text: str, measured: dict[str, dict[str, int]]) -> list[str]:
    """回傳不符項訊息清單（空清單＝新鮮）。純函式，供測試以合成文本驅動。"""
    problems: list[str] = []
    for spec in _SPECS:
        line = anchored_line(text, spec.anchor)
        documented = parse_documented(line, spec)
        live = measured[spec.anchor]
        problems.extend(f"[{spec.anchor}] {p}" for p in prose_problems(line, spec, live))
        if documented != live:
            note = ""
            if live.get("violations", 0) > 0:
                note = (
                    "\n  ⚠️ 實測 violations>0 ⇒ **這是 LOC 閘門自己紅、不是文件 stale**，"
                    "請先修 LOC 預算，不要為了讓本鎖轉綠而把破線值填進文件"
                )
            problems.append(
                f"[{spec.anchor}] 文件 {documented} ≠ 實測 {live}（來源：{spec.source}）"
                f"{note}\n  一鍵回填：python tools/sync_onboarding_baselines.py --write"
            )
    return problems


def _write_onboarding(new_text: str) -> int:
    """bytes 層 LF 寫入 ＋ 落地後零 CR 斷言（共用，避免兩條寫入路徑各寫一份）。

    🔴 .gitattributes 宣告 `*.md text eol=lf`，而 Path.write_text() 在 Windows 會把 \\n
    譯成 CRLF（DEF-101-528 的原始形態，本輪已被咬過一次）。
    """
    _ONBOARDING.write_bytes(new_text.encode("utf-8"))
    if b"\r" in _ONBOARDING.read_bytes():
        print("❌ 落地後偵測到 CR，行尾被寫壞", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    text = _ONBOARDING.read_text(encoding="utf-8-sig")

    # `--check-snapshot`：只算指紋（毫秒級），不碰 live 格的量測器。pre-push 消費的就是這條。
    if "--check-snapshot" in argv:
        problems = check_snapshot(text)
        if problems:
            print("❌ ONBOARDING.md §7 表② presumed stale：", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            return 1
        live = measure_fingerprints()
        print(f"✅ §7 表② 指紋相符（{', '.join(f'{k}={v}' for k, v in live.items())}）")
        for spec in _SLOW_SPECS:
            print(f"   [{spec.anchor}] {slow_documented(text)[spec.anchor]}")
        return 0

    measured = measure_all()

    if "--with-slow" in argv:
        if "--write" not in argv:
            print("❌ --with-slow 只在 --write 下有意義（它是回填模式）", file=sys.stderr)
            return 2
        print("⏳ 實跑 ci-gate ＋ AutoClaude pytest（分鐘級）…", file=sys.stderr)
        slow = measure_slow()
        measured_fp = measure_fingerprints()
        new_text = render_fingerprints(render_slow(render(text, measured), slow), measured_fp)
        rc = _write_onboarding(new_text)
        if rc:
            return rc
        for spec in _SPECS:
            print(f"✅ 已回填 [{spec.anchor}] → {measured[spec.anchor]}")
        for spec in _SLOW_SPECS:
            print(f"✅ 已回填 [{spec.anchor}] → {slow[spec.anchor]}（來源：{spec.source}）")
        print(f"✅ 已回填 [{_FINGERPRINT_ANCHOR}] → {measured_fp}")
        return 0

    if "--json" in argv:
        print(
            json.dumps(
                {
                    "measured": measured,
                    "documented": {
                        s.anchor: parse_documented(anchored_line(text, s.anchor), s)
                        for s in _SPECS
                    },
                    "problems": check(text, measured),
                    "snapshot_documented": slow_documented(text),
                    "snapshot_fingerprints_documented": parse_fingerprints(text),
                    "snapshot_fingerprints_live": measure_fingerprints(),
                    "snapshot_problems": check_snapshot(text),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 1 if check(text, measured) or check_snapshot(text) else 0

    if "--write" in argv:
        new_text = render(text, measured)
        if new_text == text:
            print("✅ ONBOARDING.md §7 live 基線格已是最新，未變更")
            return 0
        rc = _write_onboarding(new_text)
        if rc:
            return rc
        for spec in _SPECS:
            print(f"✅ 已回填 [{spec.anchor}] → {measured[spec.anchor]}")
        return 0

    problems = check(text, measured)
    if problems:
        print("❌ ONBOARDING.md §7 live 基線格 stale：", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    for spec in _SPECS:
        print(f"✅ [{spec.anchor}] {measured[spec.anchor]}（來源：{spec.source}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
