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
import random
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

# ══════════════════════════════════════════════════════════════════════════
# 🔴 R80／S7-04：「自陳失誤」的偵測器此前**沒有鑑別力**，先前的 n 是被灌水的
# ══════════════════════════════════════════════════════════════════════════
# 全庫 73 支逐字稿實測（母體＝3,177 個 assistant text 區塊）：舊判準（今名
# `_LEGACY_MISSTEP_RE`，保留在下方當對照組）命中
# 188 筆，其中 **93 筆（49.5%）是只由「訂正」這一個字觸發的**，第二名「誤判」只有
# 14 筆。逐筆抽樣看那 93 筆長什麼樣：
#
#   · 「訂正了 ADR 一筆過期宣稱（BOM 修復其實 R60 就做完了）」   ← 在報告修好了什麼
#   · 「六包全部落地……＋三筆訂正＋EVOLUTION_LOG」               ← 收輪清單的項目名
#   · 「這個 repo 有明文規則：訂正註記逐字引述假話等於……」        ← 在引述 CLAUDE.md
#   · 「已逐一用實測數字訂正，第二輪複審四方確認數字完全吻合」    ← 在講流程走完了
#
# 這些是**在討論失誤**，不是自陳失誤。歸因分群的單位若混進「我在報告一個發現」，
# 那個分佈量到的是「這個 repo 的文件在談什麼」，不是「我犯了什麼錯」——而後者才是
# 舵手訴求 4 問的東西。方向也很糟：一輪的收尾摘要愈完整、討論訂正的句子就愈多，
# 於是**做得愈仔細、量到的失誤愈多**。
#
# 修法不是把「訂正」刪掉（真的自陳「我訂正一下，剛才那句是錯的」也用這個字），
# 而是把詞分成兩類，**弱詞要求同一句裡有第一人稱歸屬**：
#: 🔴 中間**必須留有界的間隙**：實測「我上面那句寫錯了」被固定詞綴版整條漏掉
#: （`我` 與 `寫錯` 之間隔了「上面那句」）。間隙上界刻意小且不得跨句讀點，否則
#: 「我要去查一下，那份文件寫錯了」這種兩件事會被黏成一件。
_GAP = r"[^。！？!?；;\n]{0,8}"
_STRONG_MISSTEP_RE = re.compile(
    r"(我" + _GAP + r"(?:做|判|寫|抓|查|念|搞|弄|看|記)錯"
    r"|低級錯誤|搞錯|弄錯|看錯|記錯|誤植|誤以為|漏看|漏掉了"
    r"|我的錯|不好意思，?我|抱歉，?我)"
)
#: 弱詞：真的自陳失誤時會用，但**更常**出現在「報告我修好了什麼／引述規則／列清單」。
#: 單獨出現不算數，要同一句裡有第一人稱歸屬才算。
_WEAK_CORRECTION_RE = re.compile(r"(訂正|更正|失誤|誤判|誤用)")
#: 第一人稱歸屬：這件事是**我**做的／**我**身上發生的。刻意不收裸「我」——
#: 「我來看一下」「我先跑」滿場都是，收了等於沒收。
#: 第一人稱歸屬＝這件事是**我**做的／**我**身上發生的。用「有界鄰近共現」而不是
#: 固定詞綴：實測固定詞綴會漏掉「我照實訂正」「訂正**了**我三個前提」這兩種最常見的
#: 寫法（自證第 2、3 組），而它們正是真的自陳失誤。
#: 誠實劃界：這條會把「我來訂正這份文件的一個過期記載」也算進來（我在修別人的東西，
#: 不是我犯的錯）——方向是**高報**。選它是因為另一個方向（漏掉真的自陳）在本檔的用途
#: 上更糟：歸因分群漏掉真失誤時，剩下的分佈會偏向「還沒被漏掉的那幾類」。
_SELF_ATTRIB_RE = re.compile(
    r"(?:我|自己)" + _GAP +
    r"(?:錯|失誤|誤判|誤用|誤植|漏|沒有?查|沒跑|未查|說法|宣稱|判斷|理解|前提|結論"
    r"|訂正|更正)"
    r"|(?:訂正|更正|打臉)" + _GAP + r"(?:我|自己)"
)

#: 句子切割（與 `audit_session._sentences` 同形，但本檔要的是「弱詞與第一人稱是否
#: **同一句**」，所以不能只看整段）。
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?\n])")


def misstep_hit(text: str) -> str | None:
    """`None`＝不是自陳失誤；否則回傳觸發的那一句（供逐筆覆核）。

    強詞：整段任一句命中即可。
    弱詞：必須與第一人稱歸屬**同一句**——這一條就是 S7-04 的修正本體。
    """
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        stripped = sentence.strip()
        if not stripped:
            continue
        if _STRONG_MISSTEP_RE.search(stripped):
            return stripped
        if (_WEAK_CORRECTION_RE.search(stripped)
                and _SELF_ATTRIB_RE.search(stripped)):
            return stripped
    return None


#: 舊判準保留為**對照用**（`--selftest` 要印出它錯在哪；拿掉它自證就沒有紅的一半）。
_LEGACY_MISSTEP_RE = re.compile(
    r"(我(?:剛剛|之前|上面|當時)?(?:做|判|寫|抓|查|念)?錯"
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


def transcript_items(project_dir: Path | None = None,
                     control: bool = False) -> list[dict]:
    """逐字稿裡助理**自陳失誤**的段落（本機資料，缺席時回空清單並在報表說明）。

    `control=True` 時回傳的是**對照組**：同一批 assistant text 區塊裡**沒有**自陳
    失誤的那些。用途見 `control_lift()`——沒有對照組，「最大的桶是 X」這句話就無法
    與「這個 repo 平常就常講 X」分開。
    """
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
                if not text.strip():
                    continue
                sentence = misstep_hit(text)
                if control:
                    if sentence is not None:
                        continue
                    sentence = " ".join(text.split())[:120]
                elif sentence is None:
                    continue
                items.append({
                    "source": "control" if control else "transcript",
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


# ══════════════════════════════════════════════════════════════════════════
# 🔴 R80／S7-03：沒有對照組的「最大的桶是 X」是一句不可證偽的話
# ══════════════════════════════════════════════════════════════════════════
# 上一版只印處理組（自陳失誤那些段落）的桶分佈，於是「最大的桶是 X」這個結論
# **無法**與「這個 repo 的文字平常就常出現 X 的關鍵詞」分開。桶的判準是關鍵詞計數，
# 而關鍵詞的**基底出現率**在這份語料裡差異極大（`棘輪`／`射程`／`鑑別力` 是本 repo
# 的日常詞彙，`WSL`／`PATHEXT` 不是）⇒ 一個完全不含失誤資訊的段落照樣會被分進某個桶。
#
# 修法是任何觀測研究都會做的那一件：拿**同一個分類器**去跑一組已知「不是失誤」的
# 語料（＝同一批 assistant 段落裡沒有自陳失誤的那些），把兩邊的百分比相減。
#   lift > 0：這個桶在失誤語料裡確實過度出現 ⇒ 結論有依據
#   lift ≈ 0：這個桶只是反映語料的基底詞頻 ⇒ **不得**拿它下結論
# 對照組的抽樣倍率固定寫在報表上；抽樣用固定 seed，重跑會得到同一組數字。
_CONTROL_RATIO = 3
_CONTROL_SEED = 80


def control_lift(treated: list[dict], control: list[dict]) -> dict[str, dict]:
    """`桶 -> {treated_pct, control_pct, lift_pp}`（純函式，供 `--selftest`）。"""
    t_counts, c_counts = tally(treated), tally(control)
    out: dict[str, dict] = {}
    for bucket in t_counts:
        t_pct = 100.0 * t_counts[bucket] / len(treated) if treated else 0.0
        c_pct = 100.0 * c_counts[bucket] / len(control) if control else 0.0
        out[bucket] = {"treated_n": t_counts[bucket], "control_n": c_counts[bucket],
                       "treated_pct": t_pct, "control_pct": c_pct,
                       "lift_pp": t_pct - c_pct}
    return out


_DISCLAIMER = (
    "🔴 判準性質（本行由腳本自己印，不是散文）：分群是**關鍵詞啟發式**。\n"
    "   量級穩健（桶與桶的大小關係可引用）、小數不穩健（確切百分比**不得**引用為常數）。\n"
    "   每一筆都附命中的關鍵詞，請逐筆覆核而不是相信總數；平手與零命中一律進 OTHER。"
)


def _print_report(items: list[dict], counts: dict[str, int], sources: list[str],
                  show: str | None, lift: dict[str, dict] | None = None) -> None:
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
    if lift:
        treated_n = sum(row["treated_n"] for row in lift.values())
        control_n = sum(row["control_n"] for row in lift.values())
        print(f"\n### 對照組（同一個分類器 × 已知**不是**自陳失誤的段落；"
              f"處理組 n={treated_n}〔僅逐字稿〕、對照組 n={control_n}，"
              f"抽樣倍率 {_CONTROL_RATIO}×、seed={_CONTROL_SEED}）")
        print("  🔴 沒有這一段，『最大的桶是 X』無法與『這個 repo 平常就常講 X』分開。")
        print("  🔴 兩個桶的 lift 都為正且筆數相近時，**不得**挑其中一個當「最大宗」"
              "——這把尺分不開它們。")
        print(f"  {'桶':12s} {'處理%':>8s} {'對照%':>8s} {'lift(pp)':>10s}  判讀")
        for bucket, row in lift.items():
            verdict = ("有正 lift，可下結論" if row["lift_pp"] >= 5
                       else "lift 太小 ⇒ 只是基底詞頻，**不得**據此下結論")
            print(f"  {bucket:12s} {row['treated_pct']:7.1f}% "
                  f"{row['control_pct']:7.1f}% {row['lift_pp']:+9.1f}  {verdict}")
        print("  （lift 的門檻 5pp 是判讀輔助，不是統計檢定；n 小時請直接看絕對筆數）")
    if show:
        print(f"\n### 桶 `{show}` 的全部原文（供逐筆覆核）")
        for item in items:
            if item["bucket"] == show:
                print(f"  · [{item['origin']}] {item['matched']}")
                print(f"      {item['text'][:220]}")


#: 🔴 自陳失誤偵測器的紅綠自證語料（`--selftest`，可重跑）。
#: **每一句都是從本機逐字稿真的抄下來的**（origin 記在括號裡），不是我編出來的
#: 樣本——編出來的樣本會不自覺地照著判準寫，那種自證恆綠。
_MISSTEP_SELFTEST: tuple[tuple[str, bool, str], ...] = (
    # ── 已知**是**自陳失誤 ──────────────────────────────────────────────
    ("我誤稱「本機沒有 PostgreSQL」，被掌舵者點名為低級錯誤。", True,
     "自陳＋低級錯誤（強詞）"),
    ("這條歸因我照實訂正，不編一個來源出來。", True, "弱詞「訂正」＋第一人稱歸屬"),
    ("agent 訂正了我三個前提，其中一個是我的清單漏了一整包。", True,
     "弱詞＋「訂正我」＝被別人指出我的錯"),
    ("我先前的說法有兩處要訂正：現行是 10 個 hook 條目，不是 8。", True,
     "弱詞＋「我先前的說法」"),
    ("我上面那句寫錯了，實測值是 7 不是 0。", True, "強詞「我…寫錯」"),
    # ── 已知**不是**自陳失誤（只是在討論／報告訂正這件事） ──────────────
    ("訂正了 ADR 一筆過期宣稱（BOM 修復其實 R60 就做完了）、真跑補齊了驗證缺口。",
     False, "在報告修好了什麼——舊判準會把它算成一次失誤"),
    ("六包全部落地，收尾包已派出（帳本歸檔 + 立帳 + 三筆訂正 + ONBOARDING §9）。",
     False, "收輪清單的項目名"),
    ("這個 repo 有明文規則：訂正註記逐字引述假話等於製造新假話。", False,
     "在引述 CLAUDE.md 的規則"),
    ("已逐一用實測數字訂正，第二輪複審四方確認數字完全吻合、機械閘門全綠。", False,
     "在講流程走完了"),
    ("四方審查抓到幾處行號描述漂移，第二輪因訂正順序又冒出 2 處連鎖偏移。", False,
     "在描述別人的審查結果與流程"),
)


def _selftest() -> int:
    """紅綠自證：新判準要全對，且**舊判準必須有錯**，否則自證證明不了任何事。"""
    print(f"### 自陳失誤偵測器紅綠自證（{len(_MISSTEP_SELFTEST)} 句，"
          "全部抄自本機逐字稿）")
    print("  🔴 綠：新判準每一句都要判對。")
    print("  🔴 紅：同一批句子餵給**舊判準**（`_LEGACY_MISSTEP_RE`）看它錯在哪。")
    wrong_new = wrong_old = 0
    for sentence, expected, why in _MISSTEP_SELFTEST:
        new_verdict = misstep_hit(sentence) is not None
        old_verdict = bool(_LEGACY_MISSTEP_RE.search(sentence))
        wrong_new += int(new_verdict is not expected)
        wrong_old += int(old_verdict is not expected)
        print(f"  {'✅' if new_verdict is expected else '❌'} "
              f"應判={str(expected):5s} 新={str(new_verdict):5s} "
              f"舊={str(old_verdict):5s}  {why}")
        print(f"       {sentence[:90]}")
    print(f"\n  新判準判錯 {wrong_new} / {len(_MISSTEP_SELFTEST)}；"
          f"舊判準判錯 {wrong_old} / {len(_MISSTEP_SELFTEST)}")
    if wrong_old == 0:
        print("  ⚠️ 舊判準一句都沒判錯 ⇒ 這批語料對「修了什麼」沒有鑑別力，"
              "自證是空的。", file=sys.stderr)
    return 1 if (wrong_new or wrong_old == 0) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", choices=("all", "ledger", "transcript"),
                        default="all")
    parser.add_argument("--project-dir", help="逐字稿目錄（覆寫 slug 推導）")
    parser.add_argument("--jsonl", help="把逐筆歸屬寫成 .jsonl 供下一輪 diff")
    parser.add_argument("--show", help="印出某一桶的全部原文（桶名）")
    parser.add_argument("--control", action="store_true",
                        help="加跑對照組（同一個分類器 × 已知**不是**自陳失誤的段落）"
                             "並印出逐桶 lift。沒有它，『最大的桶是 X』無法與"
                             "『這份語料平常就常講 X』分開")
    parser.add_argument("--selftest", action="store_true",
                        help="對已知自陳失誤／已知只是討論失誤的句子各數組跑偵測器，"
                             "並印出舊判準對同一批語料的判定當作紅的那一半")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()

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

    lift: dict[str, dict] | None = None
    if args.control:
        # 🔴 只拿逐字稿那一半來比：對照組是「同一批 assistant 段落裡沒有自陳失誤的
        # 那些」，帳本列**不是同一種文本**（別人寫的缺陷描述，句法與詞頻都不同）。
        # 把兩者混進同一個處理組，lift 量到的會是「帳本與逐字稿的文體差異」。
        treated = [i for i in items if i["source"] == "transcript"]
        base = Path(args.project_dir) if args.project_dir else None
        pool = transcript_items(base, control=True)
        if not treated or not pool:
            print("⚠️ --control：處理組或對照組是空的 ⇒ lift 無意義，本次不算。"
                  "（逐字稿目錄不在本機？--source 排除了 transcript？）",
                  file=sys.stderr)
        else:
            random.seed(_CONTROL_SEED)
            sample = random.sample(
                pool, min(len(treated) * _CONTROL_RATIO, len(pool)))
            attribute(sample)
            lift = control_lift(treated, sample)

    if args.jsonl:
        with open(args.jsonl, "w", encoding="utf-8", newline="\n") as handle:
            for item in items:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    if args.as_json:
        payload = {"n": len(items), "counts": counts,
                   "sources": sources, "disclaimer": _DISCLAIMER,
                   "items": items}
        if lift is not None:
            payload["control_lift"] = lift
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_report(items, counts, sources, args.show, lift)

    # 🔴 語料塌了要 fail-loud：`n=0` 讀起來像「這一輪沒有失誤」，而那個方向
    # 正是本 repo 反覆記載的「看起來變乾淨」——比紅更危險。
    if not items:
        print("\n❌ 取不到任何一筆語料 ⇒ 來源清單過期／檔案改格式，"
              "不是『零失誤』", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
