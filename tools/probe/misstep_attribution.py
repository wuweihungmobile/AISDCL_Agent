#!/usr/bin/env python3
"""失誤歸因分群器 —— 讓 Q4 的百分比第一次成為「可重跑的量測」而不是常數。

WHY（本檔的立案理由）
--------------------
根 CLAUDE.md 的〈Windows 側單一載具原則〉現行結論（鎖無鑑別力 vs 選錯載具 vs 宣稱先於
查證 vs 取數管道給假數字）是 R77 以「n=36 的關鍵詞人工分群」得出的，而**那次分群沒有
留下任何可重跑的產物**：R77 那個 commit 只新增了攔截器與量測器兩支檔，全庫零分群腳本，
36 列的來源清單也不在 repo 內。同一份 CLAUDE.md 同時要求「每輪重跑一次，分群腳本與桶的
判準要具名可重跑」——於是那條要求在結構上永遠滿足不了，而讀者看到「重跑指令」會以為
跑一下就好，跑完拿到的其實是另一個量（`audit_session.py` 量的是**指令字串形態**，不是
失誤歸因）。這正是 R71 那個 n=8 模型被當現行結論用五輪的同一個形態，只是換了個數字。

本檔就是那個缺席的產物。它不解決「分群準不準」，它解決的是**「這個數字下一輪還量得出來
嗎」**——沒有這一點，任何百分比都是不可稽核的常數。

判準的性質（誠實劃界，本檔自己也會印出來）
------------------------------------------
· 分群是**關鍵詞啟發式**，不是語意理解。**量級穩健、小數不穩健**：桶與桶之間的大小
  關係可以引用，「44%」這種確切值**不得**被引用為常數。R77 自陳過一筆歸錯桶
  （一列本該進「決策負荷」卻因為含 CP950 字樣被歸進「取數管道」）——同型錯誤本檔照樣
  會犯，差別只在它現在**看得見、可重跑、可 diff**。
· 每一筆的桶歸屬都附「是哪幾個關鍵詞讓它進這個桶」，所以可以逐筆覆核而不必相信總數。
· 得分相同或全部為零 ⇒ 一律進 `OTHER`，**不做偏好性拆分**。把 `OTHER` 藏起來會讓其餘
  桶的百分比虛胖，而虛胖的方向正好是「我們已經懂了」。

用法
----
    python tools/probe/misstep_attribution.py                 # 全部來源
    python tools/probe/misstep_attribution.py --json
    python tools/probe/misstep_attribution.py --source ledger # 只算缺陷帳本
    python tools/probe/misstep_attribution.py --jsonl out.jsonl   # 逐筆落檔供 diff
    python tools/probe/misstep_attribution.py --show OTHER    # 印某一桶的全部原文
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _stdio_utf8  # noqa: E402,F401  （side effect：強制 stdout/stderr 為 UTF-8）
from probe.audit_session import (  # noqa: E402
    _blocks,
    iter_records,
    project_transcript_dir,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: 🔴 來源清單是 SSOT，寫死在檔內。理由：R77 那次分群無法重跑的直接原因就是「來源
#: 清單不在 repo 內」。來源可以增減，但增減必須是一次**看得見的變更**，不能靠某個人
#: 當下手邊剛好有哪幾份檔案。
_LEDGER_GLOBS = (
    "docs/06_quality/AutoSDD_Defect_Log.md",
    "docs/06_quality/AutoSDD_Defect_Log_archive_*.md",
)

#: 帳本列＝以 `DEF-<輪>-<序>` 開頭的表格列。這是帳本自己的格式定義（見該檔檔頭）。
_LEDGER_ROW_RE = re.compile(r"^\|\s*(DEF-\d+-\d+)\b(.*)$")

#: 逐字稿裡的「自陳失誤」：助理自己說某件事做錯／判錯／寫錯／要訂正的句子。
#: 刻意不含「缺陷」「bug」這類**描述別人的東西**的詞——那會把「我在報告一個發現」
#: 混進「我自己搞砸了」，兩者的歸因意義完全不同。
_MISSTEP_RE = re.compile(
    r"(我(?:剛剛|之前|上面|當時)?(?:做|判|寫|抓|查|念|указ)?錯"
    r"|低級錯誤|失誤|搞錯|弄錯|看錯|記錯|誤判|誤用|誤植|誤以為|漏看|漏掉了"
    r"|訂正|更正|我的錯|不好意思，?我|抱歉，?我)"
)

#: `桶名 -> (這個桶抓的是什麼, 關鍵詞)`。
#: 🔴 桶的判準必須**具名且可重跑**（根 CLAUDE.md 逐字要求）。關鍵詞表就是判準本身，
#: 改動它會直接改動所有歷史數字 —— 所以改它等於重新定義量測，必須當成一次變更來做。
_BUCKETS: dict[str, tuple[str, tuple[str, ...]]] = {
    "LOCKBLIND": (
        "鎖／判準存在，但看不到它該看的東西（射程失明、恆綠、幽靈機械物）",
        ("沒有鑑別力", "零鑑別力", "鑑別力", "恆綠", "永遠是綠", "結構上看不到",
         "結構上不可能", "射程", "失明", "掃描面", "沒有機械物", "零機械物",
         "沒有任何東西會紅", "不會轉紅", "假綠", "空洞", "幽靈", "棘輪",
         "判準自己", "鎖自己", "早退", "遮蔽"),
    ),
    "CARRIER": (
        "選錯載具／平台工具面（用了 Bash、裸 bash、裸 cd、引擎版本挑錯）",
        ("Bash 工具", "裸 bash", "Git Bash", "WSL", "載具", "裸 cd", "Set-Location",
         "cwd", "PowerShell 5.1", "pwsh", "powershell.exe", "here-string",
         "PATHEXT", "$IsWindows", "路徑分隔", "反斜線", "副檔名"),
    ),
    "CLAIM-FIRST": (
        "宣稱先於查證（沒跑就說已驗證、採信提示詞／agent 回報而未親查）",
        ("宣稱", "未查證", "沒查證", "先於查證", "採信", "假宣稱", "失實",
         "事後諸葛", "編造", "沒有實測", "未實測", "自陳", "以為", "假設",
         "沒跑就", "誤稱", "過期事實", "stale", "快照"),
    ),
    "BADPIPE": (
        "取數管道給假數字（rc 被污染、編碼誤讀、計數器數錯、log 解析錯位）",
        ("LASTEXITCODE", "rc 被", "真紅", "讀成綠", "管線", "CP950", "cp1252",
         "big5", "編碼", "BOM", "亂碼", "行尾", "CRLF", "假數字", "假陰性",
         "假陽性", "數字不對", "算錯", "計數", "tee", "pipefail", "吞掉"),
    ),
}

_OTHER = "OTHER"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def ledger_items() -> list[dict]:
    """缺陷帳本（主檔＋全部 archive）的每一列一筆。"""
    items: list[dict] = []
    for pattern in _LEDGER_GLOBS:
        parent = _REPO_ROOT / Path(pattern).parent
        for path in sorted(parent.glob(Path(pattern).name)):
            for lineno, line in enumerate(_read(path).splitlines(), 1):
                match = _LEDGER_ROW_RE.match(line)
                if match:
                    items.append({
                        "source": "ledger",
                        "origin": f"{path.relative_to(_REPO_ROOT).as_posix()}:{lineno}",
                        "key": match.group(1),
                        "text": line,
                    })
    return items


#: 分類單位＝**含有自陳失誤句的那一整段助理文字**（上限字元數），不是那一句。
#: 🔴 為何不是句子：R77 那份 n=36 的單位是「一列失誤描述」，含前因後果；改用單句會讓
#: 判準看不到解釋失誤成因的那半段——實測 85% 落進 OTHER，那不是「沒有歸因」而是
#: 「取樣單位切太細」。同一段裡有多句自陳只算一筆，避免同一次失誤被重複計數。
_BLOCK_CHARS = 1200


def transcript_items(project_dir: Path | None = None) -> list[dict]:
    """逐字稿裡助理**自陳失誤**的段落（本機資料，缺席時回空清單並在報表說明）。"""
    base = project_dir or project_transcript_dir(_REPO_ROOT)
    if not base.is_dir():
        return []
    items: list[dict] = []
    for path in sorted(base.glob("*.jsonl")):
        for index, rec in enumerate(iter_records(path)):
            role, blocks = _blocks(rec)
            if role != "assistant":
                continue
            for block in blocks:
                if not isinstance(block, dict) or block.get("type") != "text":
                    continue
                text = str(block.get("text") or "")
                hit = _MISSTEP_RE.search(text)
                if not hit:
                    continue
                sentence = next(
                    (s.strip() for s in re.split(r"(?<=[。！？!?\n])", text)
                     if s.strip() and _MISSTEP_RE.search(s)), text[:120])
                items.append({
                    "source": "transcript",
                    "origin": f"{path.name}#{index}",
                    "key": sentence[:200],
                    "text": text[:_BLOCK_CHARS],
                })
    return items


def classify(text: str) -> tuple[str, list[str]]:
    """`(桶名, 命中的關鍵詞)`。純函式——桶的判準就是這裡，紅綠可由注入自證。

    得分＝命中的關鍵詞**種類數**（不是出現次數：一列裡把同一個詞講三遍不代表更像
    那個桶）。最高分獨得；**平手或全零一律 OTHER**，不做偏好性拆分。
    """
    scores: dict[str, list[str]] = {}
    for bucket, (_why, keywords) in _BUCKETS.items():
        hits = [word for word in keywords if word in text]
        if hits:
            scores[bucket] = hits
    if not scores:
        return _OTHER, []
    best = max(len(hits) for hits in scores.values())
    winners = [bucket for bucket, hits in scores.items() if len(hits) == best]
    if len(winners) != 1:
        return _OTHER, sorted({w for hits in scores.values() for w in hits})
    return winners[0], scores[winners[0]]


def attribute(items: list[dict]) -> list[dict]:
    for item in items:
        bucket, hits = classify(item["text"])
        item["bucket"] = bucket
        item["matched"] = hits
    return items


def tally(items: list[dict]) -> dict[str, int]:
    counts = dict.fromkeys([*_BUCKETS, _OTHER], 0)
    for item in items:
        counts[item["bucket"]] += 1
    return counts


_DISCLAIMER = (
    "🔴 判準性質（本行由腳本自己印，不是散文）：分群是**關鍵詞啟發式**。\n"
    "   量級穩健（桶與桶的大小關係可引用）、小數不穩健（確切百分比**不得**引用為常數）。\n"
    "   每一筆都附命中的關鍵詞，請逐筆覆核而不是相信總數；平手與零命中一律進 OTHER。"
)


def _print_report(items: list[dict], counts: dict[str, int], sources: list[str],
                  show: str | None) -> None:
    total = len(items)
    print(f"### 失誤歸因分群（來源：{'＋'.join(sources)}；n={total}）")
    print(_DISCLAIMER)
    print()
    classified = total - counts[_OTHER]
    print(f"  {'桶':12s} {'筆數':>5s}  {'% of n':>7s} {'% of 已歸類':>11s}  這個桶抓的是什麼")
    for bucket in [*_BUCKETS, _OTHER]:
        value = counts[bucket]
        pct = 100.0 * value / total if total else 0.0
        pct_cls = (100.0 * value / classified
                   if (classified and bucket != _OTHER) else float("nan"))
        cls_col = "     —" if bucket == _OTHER else f"{pct_cls:9.1f}%"
        why = _BUCKETS[bucket][0] if bucket in _BUCKETS else "以上皆不明顯／關鍵詞平手"
        print(f"  {bucket:12s} {value:5d}  {pct:6.1f}% {cls_col}  {why}")
    # 🔴 兩個分母都印，且都不准單獨引用：`% of n` 誠實（OTHER 在分母裡），
    # `% of 已歸類` 才是唯一能跟「沒有 OTHER 桶」的舊數字放在一起看的那一欄——
    # 而舊數字是人工分群、單位也不同，所以那也只是**量級**上的對照，不是同一把尺。
    print(f"\n  已歸類 {classified} / {total}（OTHER {counts[_OTHER]}）"
          "——舊的人工分群沒有 OTHER 桶，故只有『% of 已歸類』那一欄可做量級對照")
    by_source: dict[str, int] = {}
    for item in items:
        by_source[item["source"]] = by_source.get(item["source"], 0) + 1
    print(f"\n  逐來源筆數：{by_source or '（無）'}")
    if show:
        print(f"\n### 桶 `{show}` 的全部原文（供逐筆覆核）")
        for item in items:
            if item["bucket"] == show:
                print(f"  · [{item['origin']}] {item['matched']}")
                print(f"      {item['text'][:220]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", choices=("all", "ledger", "transcript"),
                        default="all")
    parser.add_argument("--project-dir", help="逐字稿目錄（覆寫 slug 推導）")
    parser.add_argument("--jsonl", help="把逐筆歸屬寫成 .jsonl 供下一輪 diff")
    parser.add_argument("--show", help="印出某一桶的全部原文（桶名）")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    items: list[dict] = []
    sources: list[str] = []
    if args.source in ("all", "ledger"):
        items += ledger_items()
        sources.append("缺陷帳本")
    if args.source in ("all", "transcript"):
        base = Path(args.project_dir) if args.project_dir else None
        found = transcript_items(base)
        items += found
        sources.append(f"逐字稿自陳失誤（{len(found)} 句"
                       f"{'；本機無逐字稿目錄' if not found else ''}）")

    attribute(items)
    counts = tally(items)

    if args.jsonl:
        with open(args.jsonl, "w", encoding="utf-8", newline="\n") as handle:
            for item in items:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    if args.as_json:
        print(json.dumps({"n": len(items), "counts": counts,
                          "sources": sources, "disclaimer": _DISCLAIMER,
                          "items": items}, ensure_ascii=False, indent=2))
    else:
        _print_report(items, counts, sources, args.show)

    # 🔴 語料塌了要 fail-loud：`n=0` 讀起來像「這一輪沒有失誤」，而那個方向
    # 正是本 repo 反覆記載的「看起來變乾淨」——比紅更危險。
    if not items:
        print("\n❌ 取不到任何一筆語料 ⇒ 來源清單過期／檔案改格式，"
              "不是『零失誤』", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
