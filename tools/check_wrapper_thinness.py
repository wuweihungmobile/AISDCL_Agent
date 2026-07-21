#!/usr/bin/env python3
"""薄殼 wrapper 退化守門 — 正規化內容 hash 釘選（R10 拍板案(a)，DEF-101-134）。

背景：tools/dev_start.py 是本 repo 首個貫徹「薄殼 + Python 核心」模式的範例
—— tools/dev_start.sh / tools/dev_start.ps1 依其自身 docstring 只做「選直譯器
→ 轉呼叫核心（dev_start.py）→ 視需要啟用 venv」三件事，業務邏輯全部收斂在
dev_start.py。R12（DEF-101-070 ② 收斂案）AutoClaude/tools/local_ci_gate 對子
亦收斂為同模式（核心＝AutoClaude/tools/local_ci_gate.py，薄殼只做「確認直譯器
→ 參數映射 → 轉呼叫核心」）。本工具守護「已經薄殼化」的對子不再退化回去長
業務邏輯。

守門策略演進（R10 拍板案(a)）：
  初版為「業務邏輯樣板關鍵字黑名單」——但列舉惡意是不可判定的軍備競賽，
  三輪複審接連被繞（`for(` 無空格、`python3 -c` 前綴、`.ForEach(` 方法呼叫，
  見 _FORBIDDEN 內逐條史料）。薄殼的本質是「幾乎永不變動」，適合白名單化：
  1. 【權威判定】正規化內容 sha256 釘選（_PINNED_SHA256）：剝除整行註解
     （.ps1 另剝 `<# … #>` 區塊）、行尾空白、空行後取 hash——任何實質內容
     變動（不論用什麼語法）一律紅燈，指路「確認變更仍屬薄殼職責後同步更新
     釘選值」。註解／說明文字調整不觸發（正規化吸收）。
  2. 【第二訊號】行數上限（MAX_LINES）：hash 更新後的長期膨脹警戒線。
  3. 【診斷輔助】原黑名單降級為 advisory 提示——只在 hash 已紅時附加印出
     命中的樣板關鍵字，幫助定位「長出了什麼」；不再是權威判定。

執行：python tools/check_wrapper_thinness.py
測試：tools/tests/test_check_wrapper_thinness.py
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護

ROOT = Path(__file__).resolve().parent.parent

# 目前 dev_start.sh=78 行、dev_start.ps1=75 行、local_ci_gate.sh=23 行、
# local_ci_gate.ps1=39 行、bootstrap.sh=24/.ps1=30、integration_gate.sh=23/.ps1=30、
# run_act.sh=21/.ps1=54（R16 三對收斂）；上限抓 100 行，留自然增長空間。
MAX_LINES = 100

_PS1_BLOCK_COMMENT_RE = re.compile(r"<#.*?#>", re.DOTALL)

# 正規化內容 sha256 釘選（權威判定）。刻意修改 wrapper 時：先確認變更仍屬
# 「選直譯器／轉呼叫核心／啟用 venv」薄殼職責，再以本檔 --print-hash 取新值
# 同步更新此表（並跑 tools/tests 確認）。
_PINNED_SHA256: dict[str, str] = {
    "tools/dev_start.sh": (
        "8a70670e8d48e9644b7ac1857beba95f7a048e1e7b5629ca493e2aa7379eeb68"
    ),
    "tools/dev_start.ps1": (
        "90ae5db991a75e2907bd0d3a743f75a129c75bc4e2ebd23dd22f132248daec14"
    ),
    # R12（DEF-101-070 ②）：local_ci_gate 收斂為薄殼＋Python 核心後納入釘選
    "AutoClaude/tools/local_ci_gate.sh": (
        "8a077fc86de14495a7d62fd49b350c4f7a089cb3f654c278a15de37f38c6f00b"
    ),
    "AutoClaude/tools/local_ci_gate.ps1": (
        "4143c4580317e72db09e7184601595fb19a7b1a576f23bc99f4d4262692efdb5"
    ),
    # R16（Architect 建議 B）：bootstrap/integration_gate/run_act 收斂為薄殼＋
    # 各自 Python 核心（bootstrap_core.py／integration_gate_core.py／
    # run_act_core.py）後，由 check_script_parity.py 的 _MARKER_PAIRS 標籤比對
    # 遷移至此 hash 釘選（同 R12 local_ci_gate 先例；gate-call 抽取比對隨之退場）
    "tools/bootstrap.sh": (
        "dc11cfbecb4cab979da1492a8a0646ad8dbb97b25173e4c6552fdaae6c06fd46"
    ),
    "tools/bootstrap.ps1": (
        "f5596876e03d3a7e382d3c336918da146f720aa43b700367ee049e4b97490b5c"
    ),
    "tools/integration_gate.sh": (
        "6a7d08e438d25d0ffeb223e5b4a3ebcc7869065b2088c50b52aa2ebd2f8c6c83"
    ),
    "tools/integration_gate.ps1": (
        "0c9efcddc4ab83b7a1b214ae698f28f8b04bbce093c664b585ccdcaa95ee8daa"
    ),
    "AutoClaude/tools/run_act.sh": (
        "d1603a0f6e32dbdf036ec95e0ee3cc646c92669ad7f8f5be8b6bc321e0f55990"
    ),
    "AutoClaude/tools/run_act.ps1": (
        "e90016dc7c6855fa2febb728297e2ff82909155cdd0777746d97791e4279b064"
    ),
}

# 業務邏輯樣板關鍵字（診斷輔助；權威判定為上方 hash 釘選）。歷史上三輪被繞的
# 史料保留於此，作為 hash 紅燈時的定位提示。
_FORBIDDEN: dict[str, tuple[str, ...]] = {
    "tools/dev_start.sh": (
        "while ",       # 迴圈：wrapper 不該有迭代式業務邏輯
        "for ",         # 迴圈（bash for）
        "for(",         # C-style for 無空格寫法（2026-07-16 SD 第三輪繞過史料）
        "jq ",          # JSON 解析（外部工具）
        "python -c",    # 內嵌 Python 業務邏輯
        "python3 -c",   # 同上（獨立複審發現的前綴繞過史料）
    ),
    "tools/dev_start.ps1": (
        "ConvertFrom-Json",
        "ConvertTo-Json",
        "[System.Text.Json",  # .NET JSON 反序列化（第三輪繞過史料）
        "foreach (",
        "foreach(",           # 無空格寫法（第三輪繞過史料）
        "while (",
        "for (",
        "ForEach-Object",
        ".ForEach(",          # 陣列方法呼叫（第三輪繞過史料）
    ),
    # local_ci_gate 薄殼沿用 dev_start 同款診斷關鍵字（R12 納入時複製，非新增判準）
    "AutoClaude/tools/local_ci_gate.sh": (
        "while ",
        "for ",
        "for(",
        "jq ",
        "python -c",
        "python3 -c",
    ),
    "AutoClaude/tools/local_ci_gate.ps1": (
        "ConvertFrom-Json",
        "ConvertTo-Json",
        "[System.Text.Json",
        "foreach (",
        "foreach(",
        "while (",
        "for (",
        "ForEach-Object",
        ".ForEach(",
    ),
    # R16：bootstrap/integration_gate/run_act 薄殼沿用同款診斷關鍵字（複製非新增判準）
    "tools/bootstrap.sh": (
        "while ",
        "for ",
        "for(",
        "jq ",
        "python -c",
        "python3 -c",
    ),
    "tools/bootstrap.ps1": (
        "ConvertFrom-Json",
        "ConvertTo-Json",
        "[System.Text.Json",
        "foreach (",
        "foreach(",
        "while (",
        "for (",
        "ForEach-Object",
        ".ForEach(",
    ),
    "tools/integration_gate.sh": (
        "while ",
        "for ",
        "for(",
        "jq ",
        "python -c",
        "python3 -c",
    ),
    "tools/integration_gate.ps1": (
        "ConvertFrom-Json",
        "ConvertTo-Json",
        "[System.Text.Json",
        "foreach (",
        "foreach(",
        "while (",
        "for (",
        "ForEach-Object",
        ".ForEach(",
    ),
    "AutoClaude/tools/run_act.sh": (
        "while ",
        "for ",
        "for(",
        "jq ",
        "python -c",
        "python3 -c",
    ),
    "AutoClaude/tools/run_act.ps1": (
        "ConvertFrom-Json",
        "ConvertTo-Json",
        "[System.Text.Json",
        "foreach (",
        "foreach(",
        "while (",
        "for (",
        "ForEach-Object",
        ".ForEach(",
    ),
}


def _normalize(text: str, is_ps1: bool) -> str:
    """剝除註解／空行／行尾空白——hash 只反映實質內容。"""
    if is_ps1:
        text = _PS1_BLOCK_COMMENT_RE.sub("", text)
    lines = [line.rstrip() for line in text.splitlines()]
    kept = [line for line in lines if line.strip() and not line.lstrip().startswith("#")]
    return "\n".join(kept)


def normalized_sha256(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    norm = _normalize(text, is_ps1=path.suffix.lower() == ".ps1")
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def check_wrapper_thinness() -> list[str]:
    """回傳違規訊息清單；空清單＝全部通過。"""
    problems: list[str] = []
    for rel, pinned in _PINNED_SHA256.items():
        path = ROOT / rel
        if not path.is_file():
            problems.append(f"{rel}：檔案不存在（wrapper 被移除或改名？）")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        line_count = len(text.splitlines())
        if line_count > MAX_LINES:
            problems.append(
                f"{rel}：{line_count} 行超過薄殼上限 {MAX_LINES} 行 —— "
                f"業務邏輯應收斂進 tools/dev_start.py，不應長在 wrapper 內"
            )
        actual = normalized_sha256(path)
        if actual != pinned:
            problems.append(
                f"{rel}：正規化內容 hash 與釘選不符（釘選 {pinned[:12]}… / 實際 "
                f"{actual[:12]}…）—— wrapper 實質內容變動；若變更仍屬「選直譯器／"
                f"轉呼叫核心／啟用 venv」薄殼職責，請以 --print-hash 取新值同步更新 "
                f"_PINNED_SHA256；否則請把邏輯收斂進 tools/dev_start.py"
            )
            for keyword in _FORBIDDEN.get(rel, ()):
                if keyword in text:
                    problems.append(
                        f"{rel}：出現禁止樣板關鍵字 {keyword!r} —— 疑似業務邏輯"
                        f"外溢回 wrapper（診斷輔助；權威判定為 hash 釘選）"
                    )
    return problems


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["--print-hash"]:
        for rel in _PINNED_SHA256:
            path = ROOT / rel
            shown = normalized_sha256(path) if path.is_file() else "（檔案不存在）"
            print(f"{rel}: {shown}")
        return 0
    problems = check_wrapper_thinness()
    if not problems:
        print(f"✅ wrapper 薄殼守門通過（{len(_PINNED_SHA256)} 支殼 hash 釘選 + 行數上限皆正常）")
        return 0
    print("❌ wrapper 薄殼守門失敗：")
    for p in problems:
        print(f"  - {p}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
