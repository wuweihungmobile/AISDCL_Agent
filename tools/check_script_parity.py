#!/usr/bin/env python3
"""雙平台腳本對等機械守護 — .sh / .ps1 四對腳本的 gate/step 清單一致性 + pytest 釘選一致性。

🔴 本工具的邊界（務必先讀）：本工具只機械比對「標籤序列」（數量、順序、字面文字），
**不比對、也無能力比對**各 step 背後的實作內容是否語意對等。**本工具通過（exit 0）
不代表兩份腳本（.sh/.ps1）行為完全一致——只代表兩邊宣告的 step 名字對得上**；
實作漂移（同名 step 做了不同事）仍需人工審查，不可把本工具的綠燈當成雙平台
行為等價的證明。詳見下方「覆蓋範圍與侷限」。

為何需要：bootstrap / integration_gate / local_ci_gate 三對腳本互稱「忠實對照」，
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

另含 pytest 釘選一致性（P3-2；R4 複審 SA P2 擴充至三處）：AutoClaude/pyproject.toml、
AISDLC_SDD/AISDLC_SDD_v0.01/requirements-ci.txt（凍結基線）與 AISDLC_SDD 下動態解析
出的 LATEST 演化版（比照 AISDLC_SDD/scripts/ci-gate.sh 的 `sort -V | tail -1` 版本解析
邏輯，於 Python 端以 pathlib 重寫等價邏輯）三處 `pytest==X` 版本字串必須相等
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
    text = path.read_text(encoding="utf-8-sig")
    return re.findall(rf"^\s*{call_name}\s+'([^']+)'", text, re.MULTILINE)


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


_SDD_VERSION_DIR_RE = re.compile(r"^AISDLC_SDD_v(\d+)\.(\d+)$")


def _find_latest_sdd_version(aisdlc_sdd_dir: Path) -> Path | None:
    """比照 AISDLC_SDD/scripts/ci-gate.sh 第 40 行的版本解析邏輯
    （`ls -d AISDLC_SDD_v0.0* AISDLC_SDD_v0.[1-9]* AISDLC_SDD_v[1-9]* | sort -V | tail -1`），
    於 Python 端以 pathlib 重寫等價邏輯：列出 AISDLC_SDD/ 下符合 `AISDLC_SDD_v\\d+\\.\\d+`
    的目錄名，用可比較的 version tuple 排序取最大者。找不到任何符合目錄回傳 None。"""
    best: tuple[int, int] | None = None
    best_path: Path | None = None
    if not aisdlc_sdd_dir.is_dir():
        return None
    for child in aisdlc_sdd_dir.iterdir():
        if not child.is_dir():
            continue
        m = _SDD_VERSION_DIR_RE.match(child.name)
        if not m:
            continue
        version = (int(m.group(1)), int(m.group(2)))
        if best is None or version > best:
            best = version
            best_path = child
    return best_path


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


def main() -> int:
    ok = True

    marker_pairs = [
        ("bootstrap", "tools/bootstrap.sh", "tools/bootstrap.ps1"),
        ("integration_gate", "tools/integration_gate.sh", "tools/integration_gate.ps1"),
        ("run_act", "AutoClaude/tools/run_act.sh", "AutoClaude/tools/run_act.ps1"),
    ]
    for label, sh_rel, ps1_rel in marker_pairs:
        sh_items = _extract_markers(_REPO_ROOT / sh_rel)
        ps1_items = _extract_markers(_REPO_ROOT / ps1_rel)
        if not sh_items or not ps1_items:
            print(f"❌ {label}：抽取到空標籤清單（.sh {len(sh_items)} / .ps1 "
                  f"{len(ps1_items)}）— 宣告 pattern 可能已改，請同步本腳本",
                  file=sys.stderr)
            ok = False
            continue
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
        ok = _compare("local_ci_gate", gate_sh, gate_ps1) and ok

    ok = _check_pytest_pin() and ok

    if not ok:
        print("\n❌ 雙平台腳本對等檢查未通過 — .sh/.ps1 必須同步修改（見上列 diff）",
              file=sys.stderr)
        return 1
    print("\n✅ 雙平台腳本對等檢查通過（4 對腳本 + pytest 釘選）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
