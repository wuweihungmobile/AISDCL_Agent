#!/usr/bin/env python3
"""dev_start 薄殼 wrapper 退化守門 — 正規化內容 hash 釘選（R10 拍板案(a)，DEF-101-134）。

背景：tools/dev_start.py 是本 repo 目前唯一貫徹「薄殼 + Python 核心」模式的
範例 —— tools/dev_start.sh / tools/dev_start.ps1 依其自身 docstring 只做
「選直譯器 → 轉呼叫核心（dev_start.py）→ 視需要啟用 venv」三件事，業務邏輯
全部收斂在 dev_start.py。本工具守護「已經薄殼化」的 dev_start 對子不再退化
回去長業務邏輯。

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

# 目前 dev_start.sh=78 行、dev_start.ps1=75 行；上限抓 100 行，留自然增長空間。
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
        print("✅ dev_start wrapper 薄殼守門通過（hash 釘選 + 行數上限皆正常）")
        return 0
    print("❌ dev_start wrapper 薄殼守門失敗：")
    for p in problems:
        print(f"  - {p}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
