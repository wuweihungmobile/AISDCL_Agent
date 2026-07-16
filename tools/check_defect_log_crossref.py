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
    僅取**最後一列**的狀態為準（視為對前列的訂正）——即使最後一列的狀態欄文字無法
    辨識任何已知關鍵字，也視為「該 ID 目前狀態不明」而非沿用更早一列的舊值
    （獨立複審 finding：舊實作在此情境下會靜默沿用前一列，與本條承諾矛盾，已修正）。
  - 掃描範圍限縮於 `ONBOARDING.md` + `.github/workflows/{windows,macos}-compat-ci.yml`
    （DEF-101-066 這類「改帳本忘同步姊妹文件」真實復發過一次的高風險文件；R4 複審
    QA 發現 windows-compat-ci.yml 的 R4 複審修正段落明確引用 DEF-101-067⑤ 卻未同步
    更新帳本狀態，補入此二檔擴大覆蓋），非涵蓋 repo 全部文件；未來如需擴大範圍，
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
    _REPO_ROOT / ".github" / "workflows" / "windows-compat-ci.yml",
    _REPO_ROOT / ".github" / "workflows" / "macos-compat-ci.yml",
    # 2026-07-16 四方複審 SA 發現：本檔會對 DEF-101-051 等 PG-track 缺陷做明確狀態宣稱
    # （曾實際自相矛盾——同檔第 3 行宣稱 fixed、第 52 行「追蹤」段落仍宣稱 open，且與
    # 帳本最新狀態不一致），先前不在掃描範圍內故未被機械鎖抓到。只新增此一檔，不擴大為
    # 全 repo 掃描（那是架構層級更大改動，非本輪範圍）。
    _REPO_ROOT / "AutoClaude" / "docs" / "05_development" / "SD10_PG_Contract_NextAction.md",
]

_ID_RE = re.compile(r"DEF-\d+-\d+")
_ROW_RE = re.compile(r"^\|\s*DEF-\d+-\d+\s*\|")
# 一個或多個「(粗體)DEF-id(粗體)(分隔符)」緊接一個括號 → 該括號內文字視為這些 ID 的狀態宣稱。
# 括號內容不設人為字數上限：曾以 {0,150} 限制，結果本 repo 慣用的長句敘述（例如
# DEF-101-057 的括號內容實測 186 字元）一旦超過上限便整段比對失敗、被靜默略過，
# 且不會有任何警告——等同複製本工具本應防止的 DEF-101-066 doc-drift 假綠情境
# （複審實測：帳本刻意設為與文件矛盾的狀態，_scan_target 仍回報空清單）。
# 改用 `[^）()]*`：因排除左右括號字元本身，最多只會掃到下一個括號為止，屬線性掃描、
# 無 catastrophic backtracking 風險，可安全移除上限。
_CLAIM_RE = re.compile(
    r"((?:\*{0,2}DEF-\d+-\d+\*{0,2}[、，,／/\s]*)+)[（(]([^）()]*)[）)]"
)

# 狀態關鍵字（對應帳本《格式定義》§ 狀態欄合法值）；用各自獨立 regex 各找最早出現位置，
# 而非 alternation 依 dict 順序短路——wontfix 不含 "fixed" 子字串，兩者互不干擾。
# 邊界改用 (?<![A-Za-z0-9])...(?![A-Za-z0-9]) 而非 \b：Python re 預設 Unicode 語意下 \b 把
# CJK 表意文字也視為 word 字元，中文字緊貼英文狀態詞（如「修復後open尚待驗證」）時兩側都判
# 定為非邊界，導致 \b 比對靜默找不到（已用 _classify() 實測重現）；改成明確只把 ASCII
# 英數字視為邊界字元，CJK／標點／空白都視為合法邊界，才能正確比對中英夾雜文字。
_STATUS_KEYWORDS: dict[str, re.Pattern[str]] = {
    "wontfix": re.compile(r"wontfix"),
    # `no_action_needed`／`no action needed`（帳本實例：DEF-101-077）＝查證後決定
    # 不需修復 → 歸類 closed-by-decision（R9 跨平台複審：原詞彙表缺此詞導致該列
    # 被計入「有效狀態紀錄」卻實為 None 含糊）。
    "closed-by-decision": re.compile(r"closed-by-decision|no[_ ]action[_ ]needed"),
    "routed": re.compile(r"(?<![A-Za-z0-9])routed(?![A-Za-z0-9])"),
    "fixed": re.compile(r"(?<![A-Za-z0-9])fixed(?![A-Za-z0-9])"),
    # `workaround`（帳本實例：DEF-101-089 workaround-applied）＝以流程繞過、
    # 程式碼缺陷本身仍在 → 歸類 open（workaround 非程式修復）。
    "open": re.compile(r"(?<![A-Za-z0-9])open(?![A-Za-z0-9])|workaround"),
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


def _load_ledger_status() -> dict[str, str | None]:
    """解析缺陷帳本表格列，回傳 {DEF-ID: 狀態分類}。同 ID 重複出現時，以最後一列為準——

    最後一列一律覆寫（即使該列狀態欄無法辨識任何已知關鍵字，此時存 None，代表
    「該 ID 目前狀態不明」），不會靜默沿用更早一列的舊分類值。
    """
    status: dict[str, str | None] = {}
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
        status[def_id] = _classify(status_cell)
    return status


def _scan_target(path: Path, ledger: dict[str, str | None]) -> list[str]:
    problems: list[str] = []
    text = path.read_text(encoding="utf-8-sig")
    for m in _CLAIM_RE.finditer(text):
        ids_blob, claim_text = m.group(1), m.group(2)
        claimed = _classify(claim_text)
        if not claimed:
            continue
        for def_id in _ID_RE.findall(ids_blob):
            if def_id not in ledger:
                problems.append(
                    f"{path.name}：{def_id} 宣稱狀態「{claimed}」，但缺陷帳本查無此 ID"
                    f"（claim 片段：{claim_text[:60]!r}）"
                )
                continue
            actual = ledger[def_id]
            if actual is None:
                problems.append(
                    f"{path.name}：{def_id} 宣稱狀態「{claimed}」，但缺陷帳本裡該 ID 最後"
                    f"一列的狀態欄文字無法辨識任何已知關鍵字，帳本自身狀態含糊"
                    f"（claim 片段：{claim_text[:60]!r}）"
                )
            elif actual != claimed:
                problems.append(
                    f"{path.name}：{def_id} 宣稱狀態「{claimed}」，帳本實際狀態為「{actual}」"
                    f"（claim 片段：{claim_text[:60]!r}）"
                )
    return problems


# 帳本輪替界線（DEF-99-001 政策：主檔 < 256KB Read 上限；DEF-101-123 機械化——
# R9 發現主檔已默默長到 272KB 超線，政策沒有任何機械守門）。
# 逼近（>= _LEDGER_WARN_BYTES）印 warning；超線（>= _LEDGER_FAIL_BYTES）直接 fail，
# 強制執行既定輪替程序（已結列搬遷 archive_NN）。
_LEDGER_WARN_BYTES = 240 * 1024
_LEDGER_FAIL_BYTES = 256 * 1024


def main() -> int:
    if not _DEFECT_LOG.exists():
        print(f"❌ 找不到缺陷帳本：{_DEFECT_LOG}", file=sys.stderr)
        return 1
    ledger_bytes = _DEFECT_LOG.stat().st_size
    if ledger_bytes >= _LEDGER_FAIL_BYTES:
        print(f"❌ 缺陷帳本主檔 {ledger_bytes} bytes ≥ 輪替上限 {_LEDGER_FAIL_BYTES}"
              "（DEF-99-001 政策 <256KB）——請將已結列搬遷至下一個 "
              "AutoSDD_Defect_Log_archive_NN.md（參照 DEF-101-123 之 R9 輪替程序）",
              file=sys.stderr)
        return 1
    if ledger_bytes >= _LEDGER_WARN_BYTES:
        print(f"⚠️  缺陷帳本主檔 {ledger_bytes} bytes 已逼近輪替上限 "
              f"{_LEDGER_FAIL_BYTES}（DEF-99-001 政策），請規劃已結列搬遷 archive",
              file=sys.stderr)
    # DEF-99-001 政策同時要求「每一個 archive 檔」< 256KB（單一 archive 逼近即拆下
    # 一個 archive）——Architect 二審 OBS-3：守門不可只量主檔。
    for arch in sorted(_DEFECT_LOG.parent.glob("AutoSDD_Defect_Log_archive_*.md")):
        arch_bytes = arch.stat().st_size
        if arch_bytes >= _LEDGER_FAIL_BYTES:
            print(f"❌ 帳本歸檔 {arch.name} {arch_bytes} bytes ≥ 上限 "
                  f"{_LEDGER_FAIL_BYTES}（DEF-99-001 政策）——請拆分至下一個 archive_NN",
                  file=sys.stderr)
            return 1
        if arch_bytes >= _LEDGER_WARN_BYTES:
            print(f"⚠️  帳本歸檔 {arch.name} {arch_bytes} bytes 已逼近上限 "
                  f"{_LEDGER_FAIL_BYTES}（DEF-99-001 政策），請規劃拆分", file=sys.stderr)
    ledger = _load_ledger_status()
    if not ledger:
        print("❌ 缺陷帳本解析結果為空 — 表格格式可能已改版導致比對邏輯失效，"
              "請同步本腳本的 _ROW_RE / 欄位解析", file=sys.stderr)
        return 1

    # 「有效」與「含糊」分開呈現（R9 跨平台複審：舊版把 _classify 回 None 的列
    # 也一併計入「有效狀態紀錄」總數，帳本自身品質問題被靜默吞掉）。
    # 含糊 >0 只印 warning 不 fail：這是帳本品質提示，非跨文件矛盾。
    vague_ids = sorted(def_id for def_id, cls in ledger.items() if cls is None)
    if vague_ids:
        print(f"⚠️  帳本狀態含糊 {len(vague_ids)} 筆（狀態欄辨識不出已知關鍵字）："
              f"{'、'.join(vague_ids)}", file=sys.stderr)

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

    vague_note = f"（另 {len(vague_ids)} 筆狀態含糊，見 warning）" if vague_ids else ""
    print(f"✅ 缺陷帳本跨文件狀態一致：帳本 {len(ledger) - len(vague_ids)} 筆有效狀態紀錄"
          f"{vague_note}、{len(_CROSSREF_TARGETS)} 份掃描目標皆無矛盾")
    return 0


if __name__ == "__main__":
    sys.exit(main())
