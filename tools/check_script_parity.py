#!/usr/bin/env python3
"""雙平台腳本對等機械守護 — .sh / .ps1 三對腳本的 gate/step 清單一致性 + pytest 釘選一致性。

為何需要：bootstrap / integration_gate / local_ci_gate 三對腳本互稱「忠實對照」，
但閘門清單過去純靠人工雙改——單邊加減 step 不會有任何機械訊號。本腳本抽取兩版
的「step 標籤字串」逐一比對，不一致即 exit 1（供 root-infra-ci 與本機執行）。

抽取策略（依各對腳本的固定宣告 pattern）：
  1. tools/bootstrap.{sh,ps1}          — `[n/m]` 步驟標籤（echo / Write-Host 字面值）
  2. tools/integration_gate.{sh,ps1}   — `[n/m]` 段落標籤（run_section / Invoke-Section）
  3. AutoClaude/tools/local_ci_gate.{sh,ps1} — gate 名（run_gate '…' / Invoke-Gate '…'）

覆蓋範圍與侷限（docstring 即契約）：
  - `[n/m]` 標籤先剝除註解行（.sh/.ps1 整行 `#` 註解 + .ps1 `<# … #>` 區塊），再以
    regex 取「`[n/m]` + 其後至引號/反引號/$/反斜線/換行為止的字面文字」比對——
    變數插值（如 `$SDD_REQ` vs `$SddReq`）之後的差異不在比對範圍。
  - 只比對「標籤序列」（數量、順序、字面文字），不比對各 step 的實作內容是否
    語意對等——實作漂移仍靠人工審查與 ONBOARDING 對照表。
  - 內嵌字串裡的行內 `#` 不視為註解（僅剝除「首個非空白字元為 #」的整行）。

另含 pytest 釘選一致性（P3-2）：AutoClaude/pyproject.toml 與
AISDLC_SDD/AISDLC_SDD_v0.01/requirements-ci.txt 兩處 `pytest==X` 版本字串必須相等
（bootstrap 把兩者裝進同一 .venv，漂移時第二次安裝會靜默改版）。

使用：
  python3 tools/check_script_parity.py   # 於 repo 內任意 cwd；不一致印 diff 並 exit 1
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

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


def _check_pytest_pin() -> bool:
    pyproject = _REPO_ROOT / "AutoClaude" / "pyproject.toml"
    req_ci = _REPO_ROOT / "AISDLC_SDD" / "AISDLC_SDD_v0.01" / "requirements-ci.txt"
    m1 = re.search(r'"pytest==([^"]+)"', pyproject.read_text(encoding="utf-8"))
    m2 = re.search(r"(?m)^pytest==(\S+)", req_ci.read_text(encoding="utf-8"))
    if not m1 or not m2:
        print(f"❌ pytest 釘選：找不到 pytest== 釘選字串（{pyproject}：{bool(m1)}；"
              f"{req_ci}：{bool(m2)}）", file=sys.stderr)
        return False
    if m1.group(1) != m2.group(1):
        print(f"❌ pytest 釘選漂移：{pyproject.name}={m1.group(1)} vs "
              f"{req_ci.name}={m2.group(1)} — 兩處必須同版（同一 .venv 共裝）",
              file=sys.stderr)
        return False
    print(f"✅ pytest 釘選一致：兩處皆 pytest=={m1.group(1)}")
    return True


def main() -> int:
    ok = True

    marker_pairs = [
        ("bootstrap", "tools/bootstrap.sh", "tools/bootstrap.ps1"),
        ("integration_gate", "tools/integration_gate.sh", "tools/integration_gate.ps1"),
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
    print("\n✅ 雙平台腳本對等檢查通過（3 對腳本 + pytest 釘選）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
