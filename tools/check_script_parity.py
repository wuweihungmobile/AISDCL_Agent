#!/usr/bin/env python3
"""雙平台腳本對等機械守護 — .sh / .ps1 四對腳本的 gate/step 清單一致性 + pytest 釘選一致性。

🔴 本工具的邊界（務必先讀）：本工具只機械比對「標籤序列」（數量、順序、字面文字），
**不比對、也無能力比對**各 step 背後的實作內容是否語意對等。**本工具通過（exit 0）
不代表兩份腳本（.sh/.ps1）行為完全一致——只代表兩邊宣告的 step 名字對得上**；
實作漂移（同名 step 做了不同事）仍需人工審查，不可把本工具的綠燈當成雙平台
行為等價的證明。詳見下方「覆蓋範圍與侷限」。

為何需要：bootstrap / integration_gate / local_ci_gate / run_act 四對腳本的兩側宣稱對等，
但閘門清單過去純靠人工雙改——單邊加減 step 不會有任何機械訊號。本腳本抽取兩版
的「step 標籤字串」逐一比對，不一致即 exit 1（供 root-infra-ci 與本機執行）。

抽取策略（依各對腳本的固定宣告 pattern）：
  1. tools/bootstrap.{sh,ps1}          — `[n/m]` 步驟標籤（echo / Write-Host 字面值）
  2. tools/integration_gate.{sh,ps1}   — `[n/m]` 段落標籤（run_section / Invoke-Section）
  3. AutoClaude/tools/local_ci_gate.{sh,ps1} — gate 名（run_gate '…' / Invoke-Gate '…'）
  4. AutoClaude/tools/run_act.{sh,ps1} — `[n/m]` 段落標籤（echo / Write-Host 字面值，
     比照 bootstrap 樣式；R4 複審 Architect P2 補上，原六段僅靠純數字 `# ---- N. ----`
     註解對齊、無機械訊號）

覆蓋範圍與侷限（docstring 即契約）：
  - `[n/m]` 標籤先剝除註解行（.sh/.ps1 整行 `#` 註解 + .ps1 `<# … #>` 區塊），再以
    regex 取「`[n/m]` + 其後至引號/反引號/$/反斜線/換行為止的字面文字」比對——
    變數插值（如 `$SDD_REQ` vs `$SddReq`）之後的差異不在比對範圍。
  - 只比對「標籤序列」（數量、順序、字面文字），不比對各 step 的實作內容是否
    語意對等——實作漂移仍靠人工審查與 ONBOARDING 對照表。
  - 內嵌字串裡的行內 `#` 不視為註解（僅剝除「首個非空白字元為 #」的整行）。
  - 抽取數量另設下限釘選 `_MIN_EXTRACT_COUNTS`（R9 跨平台複審）：宣告 pattern 被
    兩側同步改寫時，step 會靜默退出守護範圍且無 diff 訊號——數量低於釘選即紅燈；
    刻意刪減 step 時須同步更新釘選值。

另含 pytest 釘選一致性（P3-2；R4 複審 SA P2 擴充至三處）：AutoClaude/pyproject.toml、
AISDLC_SDD/AISDLC_SDD_v0.01/requirements-ci.txt（凍結基線）與 AISDLC_SDD 下動態解析
出的 LATEST 演化版（R10 DEF-101-133 起委派 AISDLC_SDD/scripts/sdd_version.py 單一真相源，
不再各語言重寫「等價邏輯」）三處 `pytest==X` 版本字串必須相等
（bootstrap 把 AutoClaude 與 v0.01 裝進同一 .venv；`AISDLC_SDD/scripts/ci-gate.sh` 跑
LATEST 版 fsm_runtime 測試時沿用同一共用 venv 的 pytest，從未依 LATEST 自己的
requirements-ci.txt 重新安裝——LATEST 宣告的版本號若漂移即為從未生效的假象）。

已評估但暫緩納入的候選（R4 複審 QA P3）：AutoClaude/tools/install_git_hooks.{sh,ps1}、
AISDLC_SDD/scripts/install-hooks.{sh,ps1} 四支腳本。評估結論：這四支腳本本質是「單一
動作、無多階段」的線性流程（assert worktree → 取 hooks dir → 驗證存在 → git config →
驗證安裝結果），並非像 run_act 那樣有六個語意獨立的段落；真正曾經重複的判定邏輯已於
DEF-101-082 抽出至 `tools/git_hooks_install_common.py` 單一真相源，兩份呼叫端現僅剩
各自平台原生的薄殼呈現層（見 DEF-101-070/080/082），對這四支腳本加 `[n/m]` 標籤會是
為了湊格式而做的形式主義。行為層已由 windows/macos-compat-ci.yml 的安裝/解除/worktree
拒絕三情境實測覆蓋（QA 判定風險低）。決策記事見缺陷帳本 DEF-101-088（closed-by-decision，
本輪暫緩，不排入 marker_pairs）。

使用：
  python3 tools/check_script_parity.py   # 於 repo 內任意 cwd；不一致印 diff 並 exit 1
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌/⚠) 防崩潰保護

_REPO_ROOT = Path(__file__).resolve().parents[1]

# `[n/m]` + 其後字面文字（至引號/反引號/$/反斜線/換行為止），rstrip 收尾空白
_MARKER_RE = re.compile(r"\[\d+/\d+\][^\"'`$\\\n]*")
_PS1_BLOCK_COMMENT_RE = re.compile(r"<#.*?#>", re.DOTALL)


def _strip_comments(text: str, is_ps1: bool) -> str:
    if is_ps1:
        text = _PS1_BLOCK_COMMENT_RE.sub("", text)
    kept = [line for line in text.splitlines() if not line.lstrip().startswith("#")]
    return "\n".join(kept)


def _extract_markers(path: Path) -> list[str]:
    text = _strip_comments(
        path.read_text(encoding="utf-8-sig"), is_ps1=path.suffix == ".ps1"
    )
    return [m.rstrip() for m in _MARKER_RE.findall(text)]


def _extract_gate_calls(path: Path, call_name: str) -> list[str]:
    """抽取 `run_gate '…'`／`Invoke-Gate "…"` 的 gate 名——單/雙引號皆接受。

    R9 跨平台複審：舊版只認單引號，兩側**同步**改成雙引號時該 gate 會靜默退出
    守護範圍（雙邊一致故 _compare 也不會有 diff 訊號），守護悄悄變窄。"""
    text = path.read_text(encoding="utf-8-sig")
    pairs = re.findall(
        rf"^\s*{call_name}\s+(?:'([^']+)'|\"([^\"]+)\")", text, re.MULTILINE
    )
    return [single or double for single, double in pairs]


# 抽取數量下限釘選（R9 跨平台複審）：抽取全靠固定宣告 pattern，pattern 被改寫
# （如兩側同步換引號風格/換函式名）時 step 會「靜默退出守護範圍」且雙邊一致、
# _compare 不會有任何 diff 訊號。以「抽取數量不得低於釘選值」補上機械訊號；
# 釘選值＝2026-07-16 工具實跑輸出（bootstrap 3 / integration_gate 5 / run_act 6 /
# local_ci_gate 9）。刻意刪減 step 時須同步更新本表（工具會在訊息中指路）。
_MIN_EXTRACT_COUNTS = {
    "bootstrap": 3,
    "integration_gate": 5,
    "run_act": 6,
    "local_ci_gate": 9,
}


def _check_extract_floor(label: str, sh_items: list[str], ps1_items: list[str]) -> bool:
    floor = _MIN_EXTRACT_COUNTS[label]
    if len(sh_items) >= floor and len(ps1_items) >= floor:
        return True
    print(f"❌ {label}：抽取數量（.sh {len(sh_items)} / .ps1 {len(ps1_items)}）低於"
          f"釘選下限 {floor} — 最可能是宣告 pattern 被改寫、step 靜默退出守護範圍；"
          f"若確為刻意刪減 step，請同步更新本腳本 _MIN_EXTRACT_COUNTS['{label}'] 釘選值",
          file=sys.stderr)
    return False


def _compare(label: str, sh_items: list[str], ps1_items: list[str]) -> bool:
    if sh_items == ps1_items:
        print(f"✅ {label}：{len(sh_items)} 個 step 標籤一致")
        return True
    print(f"❌ {label}：step 標籤不一致（.sh {len(sh_items)} vs .ps1 {len(ps1_items)}）",
          file=sys.stderr)
    width = max(len(sh_items), len(ps1_items))
    for i in range(width):
        a = sh_items[i] if i < len(sh_items) else "（缺）"
        b = ps1_items[i] if i < len(ps1_items) else "（缺）"
        mark = " " if a == b else "≠"
        print(f"  {mark} .sh: {a!r}\n  {mark} .ps1: {b!r}", file=sys.stderr)
    return False


def _find_latest_sdd_version(aisdlc_sdd_dir: Path) -> Path | None:
    """委派 LATEST 解析 SSOT（AISDLC_SDD/scripts/sdd_version.py，R10 DEF-101-133）。

    歷史：本函式曾以 pathlib 重寫 ci-gate.sh glob 的「等價邏輯」——正是 R10 ARCH-3
    指出的多語言多實作漂移面（bash 未錨定/掃磁碟 vs 此處錨定/掃磁碟，語意已分歧）。
    改為 subprocess 呼叫 SSOT（tracked 過濾＋錨定＋數值排序），解析失敗回傳 None
    （維持原「找不到→None」語意，由呼叫端決定後果）。"""
    resolver = aisdlc_sdd_dir / "scripts" / "sdd_version.py"
    if not resolver.is_file():
        return None
    try:
        proc = subprocess.run(
            [sys.executable, str(resolver), "--sdd-root", str(aisdlc_sdd_dir)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    name = proc.stdout.strip()
    if proc.stderr.strip():
        print(proc.stderr.strip(), file=sys.stderr)  # SSOT 警告（未 tracked 目錄等）直通
    if not name:
        return None
    return aisdlc_sdd_dir / name


def _check_pytest_pin() -> bool:
    pyproject = _REPO_ROOT / "AutoClaude" / "pyproject.toml"
    req_ci_frozen = _REPO_ROOT / "AISDLC_SDD" / "AISDLC_SDD_v0.01" / "requirements-ci.txt"
    latest_dir = _find_latest_sdd_version(_REPO_ROOT / "AISDLC_SDD")

    targets: list[tuple[str, Path]] = [("v0.01 凍結基線", req_ci_frozen)]
    if latest_dir is not None and latest_dir.name != "AISDLC_SDD_v0.01":
        targets.append((f"LATEST（{latest_dir.name}）", latest_dir / "requirements-ci.txt"))

    m1 = re.search(r'"pytest==([^"]+)"', pyproject.read_text(encoding="utf-8"))
    if not m1:
        print(f"❌ pytest 釘選：找不到 pytest== 釘選字串（{pyproject}）", file=sys.stderr)
        return False

    ok = True
    for label, req_ci in targets:
        if not req_ci.is_file():
            print(f"❌ pytest 釘選：{label} 找不到 requirements-ci.txt（{req_ci}）",
                  file=sys.stderr)
            ok = False
            continue
        m2 = re.search(r"(?m)^pytest==(\S+)", req_ci.read_text(encoding="utf-8"))
        if not m2:
            print(f"❌ pytest 釘選：{label}（{req_ci}）找不到 pytest== 釘選字串",
                  file=sys.stderr)
            ok = False
            continue
        if m1.group(1) != m2.group(1):
            print(f"❌ pytest 釘選漂移：{pyproject.name}={m1.group(1)} vs "
                  f"{label} {req_ci.name}={m2.group(1)} — 三處必須同版（同一 .venv 共裝）",
                  file=sys.stderr)
            ok = False

    if ok:
        print(f"✅ pytest 釘選一致：三處皆 pytest=={m1.group(1)}")
    return ok


# ── 成對腳本註冊完整性（enrollment 發現鎖）— R10 拍板案(a)，DEF-101-134 ────────
# 過去「新增一對同名 .sh/.ps1 而不掛任何守門」零機械訊號（marker_pairs 與 thinness
# 釘選對象皆硬編碼清單，磁碟上長出新對子沒人發現）。此檢查掃描宣告目錄（非遞迴）
# 下的同名 .sh/.ps1 對，斷言每一對必屬 {parity 標籤比對, thinness hash 釘選,
# 明文豁免（附決策依據）} 之一；並反向檢查註冊清單無 stale 條目（防清單腐化）。
_MARKER_PAIRS = [
    ("bootstrap", "tools/bootstrap.sh", "tools/bootstrap.ps1"),
    ("integration_gate", "tools/integration_gate.sh", "tools/integration_gate.ps1"),
    ("run_act", "AutoClaude/tools/run_act.sh", "AutoClaude/tools/run_act.ps1"),
]
_PAIR_SCAN_DIRS = ("tools", "AutoClaude/tools", "AISDLC_SDD/scripts")
_THINNESS_ENROLLED = {"tools/dev_start"}  # tools/check_wrapper_thinness.py hash 釘選
_EXEMPT_PAIRS = {
    "AutoClaude/tools/install_git_hooks": (
        "DEF-101-088 closed-by-decision：判定邏輯已下沉 tools/git_hooks_install_common.py "
        "單一真相源，殼層無標籤錨點"
    ),
    "AISDLC_SDD/scripts/install-hooks": "DEF-101-088 closed-by-decision：同 install_git_hooks",
    "AISDLC_SDD/scripts/ci-gate": (
        "ci-gate.ps1 為薄委派殼（Find-GitBash → bash ci-gate.sh 單一真相源），非第二實作"
    ),
}


def _enrolled_pairs() -> set[str]:
    parity = {sh_rel[: -len(".sh")] for _label, sh_rel, _ps1 in _MARKER_PAIRS}
    parity.add("AutoClaude/tools/local_ci_gate")  # gate-call 抽取比對（非 [n/m] 標籤）
    return parity | _THINNESS_ENROLLED | set(_EXEMPT_PAIRS)


def _discover_pairs() -> list[str]:
    pairs: list[str] = []
    for rel_dir in _PAIR_SCAN_DIRS:
        d = _REPO_ROOT / rel_dir
        if not d.is_dir():
            continue
        for sh in sorted(d.glob("*.sh")):
            if (d / f"{sh.stem}.ps1").is_file():
                pairs.append(f"{rel_dir}/{sh.stem}")
    return pairs


def _check_pair_enrollment() -> bool:
    known = _enrolled_pairs()
    pairs = _discover_pairs()
    unknown = [p for p in pairs if p not in known]
    stale = sorted(known - set(pairs))
    ok = True
    for p in unknown:
        print(
            f"❌ 未註冊的成對腳本：{p}.sh / {p}.ps1 —— 新增成對腳本必須擇一納管："
            f"(1) 有標籤錨點 → 加入 _MARKER_PAIRS；(2) 薄殼 → 掛 check_wrapper_thinness "
            f"hash 釘選；(3) 決策豁免 → 加入 _EXEMPT_PAIRS 並附缺陷帳本依據",
            file=sys.stderr,
        )
        ok = False
    for p in stale:
        print(
            f"❌ 註冊清單 stale：{p} 已不存在同名 .sh/.ps1 對 —— 請自對應清單移除",
            file=sys.stderr,
        )
        ok = False
    if ok:
        print(f"✅ 成對腳本註冊完整性：{len(pairs)} 對皆已納管（掃描 {len(_PAIR_SCAN_DIRS)} 目錄）")
    return ok


def main() -> int:
    ok = True

    for label, sh_rel, ps1_rel in _MARKER_PAIRS:
        sh_items = _extract_markers(_REPO_ROOT / sh_rel)
        ps1_items = _extract_markers(_REPO_ROOT / ps1_rel)
        if not sh_items or not ps1_items:
            print(f"❌ {label}：抽取到空標籤清單（.sh {len(sh_items)} / .ps1 "
                  f"{len(ps1_items)}）— 宣告 pattern 可能已改，請同步本腳本",
                  file=sys.stderr)
            ok = False
            continue
        ok = _check_extract_floor(label, sh_items, ps1_items) and ok
        ok = _compare(label, sh_items, ps1_items) and ok

    gate_sh = _extract_gate_calls(
        _REPO_ROOT / "AutoClaude" / "tools" / "local_ci_gate.sh", "run_gate")
    gate_ps1 = _extract_gate_calls(
        _REPO_ROOT / "AutoClaude" / "tools" / "local_ci_gate.ps1", "Invoke-Gate")
    if not gate_sh or not gate_ps1:
        print(f"❌ local_ci_gate：抽取到空 gate 清單（.sh {len(gate_sh)} / .ps1 "
              f"{len(gate_ps1)}）— 宣告 pattern 可能已改，請同步本腳本",
              file=sys.stderr)
        ok = False
    else:
        ok = _check_extract_floor("local_ci_gate", gate_sh, gate_ps1) and ok
        ok = _compare("local_ci_gate", gate_sh, gate_ps1) and ok

    ok = _check_pytest_pin() and ok
    ok = _check_pair_enrollment() and ok

    if not ok:
        print("\n❌ 雙平台腳本對等檢查未通過 — .sh/.ps1 必須同步修改（見上列 diff）",
              file=sys.stderr)
        return 1
    print("\n✅ 雙平台腳本對等檢查通過（4 對腳本 + pytest 釘選 + 對子註冊完整性）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
