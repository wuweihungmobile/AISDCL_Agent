#!/usr/bin/env python3
"""缺陷帳本 × 高風險文件「狀態宣稱」跨文件一致性機械守護（DEF-101-068(e) 落地）。

🔴 本工具的邊界（務必先讀，比照 `check_script_parity.py` docstring 風格誠實承認侷限）：
本工具**不理解自然語言**，只做「正則抽取 + 關鍵字比對」兩件事：
  1. 在掃描目標文件中找出「一個或多個 `DEF-\\d+-\\d+` 緊接著一個括號」的樣式
     （括號可為全形｀（）｀或半形｀()｀；ID 前後允許 markdown 粗體 `**`）。
  2. 從該括號內文字裡找出**最早出現**的已知狀態關鍵字
     （`open` / `routed` / `fixed` / `wontfix` / `closed-by-decision`，
     對應帳本《格式定義》§ 狀態欄的合法值），視為該文件對這個/這些 DEF ID 的「狀態宣稱」。
  3. 與 `docs/06_quality/AutoSDD_Defect_Log.md` 表格中該 ID 「狀態」欄的最新紀錄
     （同樣取表格該欄文字中最早出現的關鍵字）比對，不一致即回報。

**不做**、也**做不到**的事（誠實劃界，勿誤讀為完整性保證）：
  - 沒有括號緊跟在 ID 後面的單純引用（例如「見 DEF-101-058」）**不會被檢查**——
    這類引用未對狀態做任何明確宣稱，強行判讀等同瞎猜，故刻意略過以避免假陽性。
  - 括號內文字**巢狀提及**另一個 DEF ID 的狀態（例如 A 的括號內順帶一句「其根因 B
    已 fixed」）不會被拆成 B 的獨立宣稱——只有「緊鄰括號」的最外層 ID 才會被判讀。
  - 帳本表格若同一 ID 出現多列（理論上 append-only 帳本不應如此，但若發生），
    僅取**最後一列**的狀態為準（視為對前列的訂正）。
  - 掃描範圍刻意限縮於 `ONBOARDING.md`（DEF-101-066 這類「改帳本忘同步姊妹文件」
    真實復發過一次的高風險文件），非涵蓋 repo 全部文件；未來如需擴大範圍，
    加入 `_CROSSREF_TARGETS` 即可，不需改動核心比對邏輯。

為何需要：DEF-101-066 實際發生過一次——commit 只改帳本把 DEF-101-058 標記 fixed，
`ONBOARDING.md` §9 卻仍宣稱該 ID open，兩份文件對同一 ID 各說各話卻無任何機械訊號。
本腳本把「發現即記」這類跨文件漂移的偵測，從「靠人工複審碰運氣」提升為可重複執行的
機械檢查。

使用：
  python3 tools/check_defect_log_crossref.py   # 於 repo 內任意 cwd；不一致印清單並 exit 1
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFECT_LOG = _REPO_ROOT / "docs" / "06_quality" / "AutoSDD_Defect_Log.md"
_CROSSREF_TARGETS = [
    _REPO_ROOT / "ONBOARDING.md",
]

_ID_RE = re.compile(r"DEF-\d+-\d+")
_ROW_RE = re.compile(r"^\|\s*DEF-\d+-\d+\s*\|")
# 一個或多個「(粗體)DEF-id(粗體)(分隔符)」緊接一個括號 → 該括號內文字視為這些 ID 的狀態宣稱。
_CLAIM_RE = re.compile(
    r"((?:\*{0,2}DEF-\d+-\d+\*{0,2}[、，,／/\s]*)+)[（(]([^）()]{0,150})[）)]"
)

# 狀態關鍵字（對應帳本《格式定義》§ 狀態欄合法值）；用各自獨立 regex 各找最早出現位置，
# 而非 alternation 依 dict 順序短路——wontfix 不含 "fixed" 子字串，兩者互不干擾。
_STATUS_KEYWORDS: dict[str, re.Pattern[str]] = {
    "wontfix": re.compile(r"wontfix"),
    "closed-by-decision": re.compile(r"closed-by-decision"),
    "routed": re.compile(r"\brouted\b"),
    "fixed": re.compile(r"\bfixed\b"),
    "open": re.compile(r"\bopen\b"),
}


def _classify(text: str) -> str | None:
    """回傳 text 中『最早出現』的已知狀態關鍵字類別；找不到回 None。"""
    best_pos: int | None = None
    best_label: str | None = None
    for label, pat in _STATUS_KEYWORDS.items():
        m = pat.search(text)
        if m and (best_pos is None or m.start() < best_pos):
            best_pos = m.start()
            best_label = label
    return best_label


def _load_ledger_status() -> dict[str, str]:
    """解析缺陷帳本表格列，回傳 {DEF-ID: 狀態分類}。同 ID 重複出現時，以最後一列為準。"""
    status: dict[str, str] = {}
    text = _DEFECT_LOG.read_text(encoding="utf-8-sig")
    for line in text.splitlines():
        if not _ROW_RE.match(line):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line) if c.strip()]
        if len(cells) < 2:
            continue
        def_id, status_cell = cells[0], cells[-1]
        if not _ID_RE.fullmatch(def_id):
            continue
        label = _classify(status_cell)
        if label:
            status[def_id] = label
    return status


def _scan_target(path: Path, ledger: dict[str, str]) -> list[str]:
    problems: list[str] = []
    text = path.read_text(encoding="utf-8-sig")
    for m in _CLAIM_RE.finditer(text):
        ids_blob, claim_text = m.group(1), m.group(2)
        claimed = _classify(claim_text)
        if not claimed:
            continue
        for def_id in _ID_RE.findall(ids_blob):
            actual = ledger.get(def_id)
            if actual is None:
                problems.append(
                    f"{path.name}：{def_id} 宣稱狀態「{claimed}」，但缺陷帳本查無此 ID"
                    f"（claim 片段：{claim_text[:60]!r}）"
                )
            elif actual != claimed:
                problems.append(
                    f"{path.name}：{def_id} 宣稱狀態「{claimed}」，帳本實際狀態為「{actual}」"
                    f"（claim 片段：{claim_text[:60]!r}）"
                )
    return problems


def main() -> int:
    if not _DEFECT_LOG.exists():
        print(f"❌ 找不到缺陷帳本：{_DEFECT_LOG}", file=sys.stderr)
        return 1
    ledger = _load_ledger_status()
    if not ledger:
        print("❌ 缺陷帳本解析結果為空 — 表格格式可能已改版導致比對邏輯失效，"
              "請同步本腳本的 _ROW_RE / 欄位解析", file=sys.stderr)
        return 1

    all_problems: list[str] = []
    for target in _CROSSREF_TARGETS:
        if not target.exists():
            print(f"❌ 找不到掃描目標：{target}", file=sys.stderr)
            return 1
        all_problems.extend(_scan_target(target, ledger))

    if all_problems:
        print(f"❌ 缺陷帳本跨文件狀態不一致（{len(all_problems)} 筆）：", file=sys.stderr)
        for p in all_problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print(f"✅ 缺陷帳本跨文件狀態一致：帳本 {len(ledger)} 筆有效狀態紀錄、"
          f"{len(_CROSSREF_TARGETS)} 份掃描目標皆無矛盾")
    return 0


if __name__ == "__main__":
    sys.exit(main())
