#!/usr/bin/env python3
"""Stop hook：量化判決數字**沒有出處**時出聲（治「宣稱先於查證」最大失誤桶的輸出面）。

WHY（本檔的立案量測）
--------------------
`tools/probe/misstep_attribution.py` 連兩輪把 `CLAIM-FIRST`（宣稱先於查證）量成最大的
非-OTHER 桶（本批當回合實測 n=1269／201 筆，`--control` lift 亦居首）。而該桶此前
**零攔截器**：它發生的平面是「宣稱本身」，永不變成 repo 裡的檔案 ⇒ 全庫靜態掃描器
結構上看不見它。既有的 `tools/probe/audit_session.py` 已經在事後量它（`CLAIM_RE` ×
`EVIDENCE_RE` × 往回看 3 個 tool_result），但依其檔頭自述**只能當每輪收尾的量測器**，
而且沒有任何地方會自動跑它 ⇒ 那個數字只在有人想起來時才存在。

本檔補的是**那個平面上的觀測者**：Stop 事件在「一則回覆剛落地」的那一刻觸發，payload
同時給得到宣稱（`last_assistant_message`）與證據面（`transcript_path`）——本批以拋棄式
dump hook 實測確認兩個欄位都在，且逐字稿當下**已經含**那一則的文字。

判準（為什麼是這個形狀，而不是「有沒有跑過工具」）
------------------------------------------------
逐字稿實測逼掉了兩個更直覺的判準，過程留在這裡以免有人再走一次：
  · **「這一輪沒叫過工具就出宣稱」** → 51 支逐字稿命中 28 筆，逐筆判讀後**多數是假紅**：
    收尾那一則本來就常是「把本場前幾輪真的跑過的結果收斂成一段話」，零工具是正常的。
  · **`EVIDENCE_RE` 近鄰佐證（audit_session 的既有判準）** → 同一批母體 `--latest 8`
    實測 78/275（28.4%）判無佐證。那個量級當量測器可以，當每輪都會響的警報不行——
    本 repo 已判過「一個永遠在響的警報等於沒有警報」。

現行判準因此收到**值域**上：一個「只可能來自某次執行」的數字（`N passed`／`N failed`／
`N OK`／`rc=N`），若它在**本場自己的工具輸出裡從來沒出現過**，那它只有兩個來源——
別人的回報，或者沒有來源。⇒ 判準不是「你有沒有驗」，是「**這個數字的出處在哪**」，
而它是**可滿足的**：自己跑過就必然對得上，轉述別人的就標一個出處標記（`[他包回報]`
是 `docs/04_planning/AutoSDD_improving_106.md` §0 已定義的既有慣例，此前零觀測者）。
可滿足性是設計約束不是客氣：擋到讓人無法工作的守衛會被整個關掉，而被關掉的守衛比
沒有守衛更糟。

落地當回合的真實面假紅普查（母體＝本機 51 支逐字稿，非 tracked 面）：
命中 **13 筆／470 筆量化判決宣稱**（2.8%），逐筆人工判讀 **12 筆真陽性**（全部是把別包
交件的數字當自己的話講）、**1 筆假陽性**（在描述某個機制的門檻值時寫出 `pmset rc=127`）。
收斂過程中修掉的兩類假紅**都是量出來的、不是猜的**：
  ① 千分位逗號——`3,566 passed` 的 `\\b(\\d+)` 只抓到 `566`，與輸出裡的 `3566` 對不上。  # baseline-ok:語料
     正規化刻意只吃**數字之間**的半角逗號：先前版本連全角「，」一起吃，把
     `rc=0，44 skip` 併成 `rc=044` 而自製一筆假紅。
  ② 已帶出處標記的轉述——那正是本判準要的行為，命中它等於處罰正解。

🔴 **只出聲，永不阻斷**（exit 0；Stop hook 的 `decision:block` 一律不用）。三條理由各自
獨立成立：① 上述 7.7% 假紅率對阻斷型判準太高；② Stop 阻斷會把回合推回模型手上，而
本判準治的是「話講得太滿」，不是「工作沒做完」——推回去只會生出更多話；③ Stop 阻斷
迴圈的唯一煞車是 `stop_hook_active`，把煞車押在單一旗標上不值得。

誠實劃界（本檔抓不到什麼）
------------------------
· **只看數字**。「全綠」「已驗證」「零損失」這種**不帶值**的判決一律看不到——它們沒有
  可比對的值域，而那正是 `audit_session.py` 那支事後量測器的射程（兩者刻意分工，不是
  同一份知識住兩個家）。
· **抓不到「有輸出但輸出被誤讀」**：數字對得上就放行，即使那個輸出講的是另一件事。
  R84 帳本裡「看著 rc=0 的下三行印著 Windows 欄失敗卻得出相反結論」那一型，本檔看不到。
· **出處標記無法防無人看管的模型自己寫**：句子裡塞一個「宣稱」就會被抑制。與
  `# git-guard-ok:` 同型，故 `AUTOSDD_UNATTENDED` 有設時**抑制詞表縮到只認方括號標記**
  （`[他包回報]`／`[本包實測]`），因為那兩個字面在 `docs/04_planning/` 有成文定義、
  亂標會在收輪對帳時被逐列核出來。這仍**不是**密封，只是把成本拉高。
· **證據面只認 `tool_result`**：背景 agent 的完成通知不是 tool_result ⇒ 它帶回來的數字
  一律判成無出處。這是**刻意的**——那正是「採信 agent 回報而未親查」本身。
· 逐字稿讀不到／payload 退化／任何非預期例外 ⇒ **一律 fail-open 靜默放行**
  （`.claude/settings.json` description 記載過的 P0：hook 誤觸 deny 會把所有工具硬鎖死）。

判準本體 `unsourced_verdict_hits()` 是純函式，由 `tools/tests/test_claim_provenance_r86.py`
機械釘住（含合成注入紅綠雙向自證）。依賴方向與 `lint_powershell_command.py` 同：
**`tools/probe` 向本檔借，本檔不 import 任何 repo 模組**（本檔由 `runpy.run_path` 起、
`sys.path` 上沒有 `tools/`，import 期爆掉會破壞 fail-open 契約）。
"""
from __future__ import annotations

import json
import os
import re
import sys

# payload 讀取與 UTF-8 stdio 都住共用層 `tools/lib/platform_utils.py`，形態逐字對齊姊妹檔
# `block_destructive_git.py`／`lint_powershell_command.py`（同一個 shim、同一個 except 語意）。
# 🔴 **本檔不得自己碰 `sys.stdin`、也不得自己 reconfigure**：兩者各有一條 shrink-only 棘輪
# 在守（`test_pre_commit_dispatcher_sigpipe.py::TestHookPayloadSingleHome`／
# `test_platform_utils_dedup.py::TestR75StdioUtf8HasOneImplementation`）。本檔第一版兩條都
# 犯了，被那兩道鎖當場判紅——立論逐字是「長出第二個家的唯一入口就是自己碰 stdin」，而
# 此前 7 支手抄本實測已漂移成 3 種行為。無 UTF-8 保護的代價同樣是實測過的（DEF-101-789，
# GitHub windows-latest 逐字重現）：本檔的輸出**就是使用者唯一看得到的指引**，en-US
# （cp1252）下整段變 `\uXXXX` 逃脫、zh-TW（cp950）下變亂碼 ⇒ 「出聲有了、教學沒了」。
# 與 fail-open 契約不衝突：共用層不可達時 payload 退化成 `{}`（走下面「缺欄位即 return 0」
# 分支）、`init_utf8_streams()` 契約是「取不到就靜默不動」，兩者都與 fail-open 同向。
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tools", "lib"))
try:
    from platform_utils import read_hook_payload  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001 — 共用層不可達＝退化，不是崩潰（fail-open 是 P0）
    def read_hook_payload() -> dict:  # type: ignore[misc]
        return {}

try:
    from platform_utils import init_utf8_streams  # type: ignore[import-not-found]

    init_utf8_streams()
except Exception:  # noqa: BLE001 — 模組層崩潰會繞過 main() 的 fail-open，故必須吞掉
    pass

#: 「只可能來自某次執行」的量化判決形狀。刻意不含不帶值的判決詞（見檔頭誠實劃界）。
VERDICT_RE = re.compile(
    r"(?:\b(\d{1,7})\s+(?:passed|failed|OK)\b|\brc\s*=\s*(\d{1,3})\b)", re.IGNORECASE
)

#: 出處標記。命中即抑制——轉述別人的數字並標明出處，是本判準要的**正解**。
PROVENANCE_RE = re.compile(
    r"(\[他包回報\]|\[本包實測\]|宣稱|回報|回覆|轉述|聲稱|所述|交件|測得|據|"
    r"未親驗|未重跑)"
)

#: 無人看管時只認方括號標記（見檔頭：把「自己寫一個豁免」的成本拉高）。
UNATTENDED_PROVENANCE_RE = re.compile(r"(\[他包回報\]|\[本包實測\])")

#: 千分位正規化：**只**吃數字之間的半角逗號。連全角「，」一起吃會把
#: `rc=0，44 skip` 併成 `rc=044` ⇒ 自製假紅（本批實測）。
_THOUSANDS_RE = re.compile(r"(?<=\d),(?=\d)")

_SENTENCE_RE = re.compile(r"(?<=[。！？!?\n])")


def normalize_digits(text: str) -> str:
    """把千分位逗號拿掉，讓 `3,566 passed` 與輸出裡的 `3566` 對得上。"""  # baseline-ok:語料
    return _THOUSANDS_RE.sub("", text)


def unsourced_verdict_hits(claim_text: str, tool_output: str,
                           unattended: bool = False) -> list[dict]:
    """`claim_text` 裡「值在 `tool_output` 中找不到」的量化判決（`[]`＝沒有）。

    純函式，供攔截端（本檔 Stop 分支）與事後量測端（`tools/probe/`）共用同一份判準。
    """
    corpus = normalize_digits(tool_output)
    seen = set(re.findall(r"\d{1,7}", corpus))
    marker = UNATTENDED_PROVENANCE_RE if unattended else PROVENANCE_RE
    hits: list[dict] = []
    for sentence in _SENTENCE_RE.split(claim_text):
        if not sentence.strip() or marker.search(sentence):
            continue
        for match in VERDICT_RE.finditer(normalize_digits(sentence)):
            value = match.group(1) or match.group(2)
            if value in seen:
                continue
            hits.append({"value": value, "sentence": sentence.strip()[:200]})
    return hits


def _tool_output_digits(transcript_path: str, byte_cap: int = 32 * 1024 * 1024) -> str:
    """本場**自己跑出來的**工具輸出（只認 `tool_result`；見檔頭誠實劃界）。

    `byte_cap` 是防呆而非效能手段：本機最大逐字稿 6.0 MB／全場 51 支掃完 10.3 s
    ⇒ 單場遠在預算內。超過上限時**回空字串會讓每個數字都變成命中**（截斷偏向假紅），
    故超限一律讓呼叫端 fail-open 放行，見 `main()`。
    """
    # 🔴 讀不到／超上限一律 **raise**，讓 `main()` 走 fail-open 靜默放行。
    # 絕不可 `return ""`：空證據面會讓**每一個**數字都變成命中，而那是假紅方向。
    # 本檔第一版就是回空字串，被 `tools/tests/test_claim_provenance_r86.py::
    # TestTruncationBiasesTowardsSilenceNotFalseRed` 當場抓出來（逐字稿路徑不存在時
    # 噴出一整段違規訊息）——「證據面拿不到」與「證據面裡沒有這個數字」必須分開。
    size = os.path.getsize(transcript_path)  # OSError ⇒ 交給 main() fail-open
    if size > byte_cap:
        raise ValueError("transcript exceeds byte cap")
    chunks: list[str] = []
    with open(transcript_path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if '"tool_result"' not in line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue  # 逐字稿邊寫邊讀，尾列半截是常態
            message = record.get("message")
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                inner = block.get("content")
                if isinstance(inner, str):
                    chunks.append(inner)
                elif isinstance(inner, list):
                    chunks.extend(str(b.get("text") or "") for b in inner
                                  if isinstance(b, dict))
    return "\n".join(chunks)


def main() -> int:
    if os.environ.get("AUTOSDD_CLAIM_GUARD_OFF"):
        return 0
    try:
        payload = read_hook_payload()
        claim = str(payload.get("last_assistant_message") or "")
        transcript = str(payload.get("transcript_path") or "")
        if not claim or not transcript:
            return 0
        hits = unsourced_verdict_hits(
            claim, _tool_output_digits(transcript),
            unattended=bool(os.environ.get("AUTOSDD_UNATTENDED")),
        )
        if hits:
            listed = "／".join(f"{h['value']}" for h in hits[:4])
            print(
                f"🔴 這一則有 {len(hits)} 個量化判決數字（{listed}）在本場自己的工具輸出裡"
                f"找不到出處。若是轉述別包交件，請標 `[他包回報]`；若是自己跑的，請把那次"
                f"執行的指令與 rc 一起貼出來。（判準：.claude/hooks/check_claim_provenance.py"
                f"；關閉：AUTOSDD_CLAIM_GUARD_OFF=1）",
                file=sys.stderr,
            )
    except Exception:  # noqa: BLE001 — fail-open，見檔頭 P0
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
