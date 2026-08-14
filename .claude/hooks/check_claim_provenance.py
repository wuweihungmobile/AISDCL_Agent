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

第二個判準：錯誤訊息的字面被當成機制結論（R89 `DEF-200-123`，逃生口自己一個）
------------------------------------------------------------------------
立案事故（真實）：13 個 subagent 死於 `You've hit your monthly spend limit`，主控把**錯誤
訊息的字面**當成根因、宣稱保險池撞頂擋住了 agent，並把它寫進交棒書與多個 commit、還當
成前提餵給 Architect。掌舵者一句話戳破：那個池**本來就滿**——落款 `quota_burn.jsonl`
逐列實證它連續 15 列都是 100.0 ⇒ **它是常數，數學上不可能是變因**。

上面那個值域判準對這件事**結構上失明**：因果宣稱不帶可比對的值域。而「你有沒有做變因
查證」問不出可滿足的答案（普查實測見下），所以本判準同樣做了一次**收斂到可判定面**的
動作，只是收斂的目標不同：不問「你驗了嗎」，問「**這句話的主詞是不是機器剛剛吐給你的
那串字**」——句子做出機制結論（`MECHANISM_RE`）、主詞是一段反引號英文錯誤字面、而那串
字**逐字出現在本場的工具輸出裡** ⇒ 出聲。三個條件都是字串比對，沒有一項需要理解語意。

可滿足性同上一個判準：句子裡寫出你做過的對照（`常數`／`變因`／`對照組`／`反例`／
`成功組`／`失敗組`／`唯一差異`／`證偽`…＝`CONTRAST_RE`）即抑制。**這不是客氣**——真的做
過對照的句子本來就會寫出對照，而沒做過的寫不出來。

真實面假紅普查（母體＝本機**全部** 1,039 支逐字稿，非 tracked 面；重跑＝
`python tools/probe/causal_form_census.py`）：assistant 句 **40,703**、其中機制結論句
**1,474**、被 `CONTRAST_RE` 抑制 **54**、**最終命中 3 筆**（0.007%），逐筆人工判讀
**3 筆全部是真陽性**——都是本事故那條假前提鏈，分屬三場（上一輪的主 session、它派出的
一個 subagent、本輪主 session）。**假陽性 0 筆。**
🔴 **母體差一點就是假的**：`~/.claude/projects/<slug>/` 只住 60 支，另外 **978 支 subagent
逐字稿住在再深一層**的 `<session>/subagents/`。第一版普查用 `glob("*/*.jsonl")` 只掃到
6% 的母體、報回 4 筆命中／50% 精確率——**「假紅率看起來很低」最常見的成因就是母體被截斷**。
改 `rglob` 之後同一份判準命中 13 筆、精確率掉到 23%。
🔴 **精確率 23%→100% 是靠一條判準修的，不是靠調參**：那 10 筆假陽性有 8 筆的共同形態是
「引述的字面其實是**符號**」（`ModuleNotFoundError`／`DeadlineExceeded`／`WinError 216`／
`subprocess.TimeoutExpired`／某支測試的名字因為含 `…NeverExceed…` 而命中 `exceed`）。
符號與訊息的分別是語意上的，不是統計上的——見 `_is_prose_message()`。
🔴 抑制詞的鑑別力也是**量出來的**：拿掉它會多命中 1 筆，而那 1 筆**恰好是掌舵者訂正後
我自己寫下的正解**（「⇒ 它是常數，不可能是變因」）⇒ 它只擋正解、不減損鑑別力。
🔴 **誠實劃界：3 筆命中引述的是同一串字面**（`monthly spend limit`）⇒ 本判準在**這一型
缺陷的複發**上已證明有鑑別力且零假紅，但它對「別的錯誤訊息被當成根因」的召回率
**在本機母體上無從量測**（沒有第二個實例）。這是邊界，不是保證。

🔴 **兩個更直覺的形狀已被同一份普查逐一證偽，不要再走一次**（數字皆現跑
`--shape a`／`--shape b`）：
  · **「因果宣稱裡的具名量在本場觀測值全同」**（＝直接把「常數不可能是變因」寫成判準）
    → 命中 3 筆，逐筆判讀 **1 真 2 假**（33%）。假紅的成因是結構性的：判準只知道那個識別
    字**出現在句子裡**，不知道它是不是被當成原因（兩筆假紅分別是「`arm_reset` 全是 0 ⇒
    兩個痕跡不一致」與「跟 `five_hour`、`seven_day` 平起平坐 ⇒ 它 100% ⇒ 一票否決」，
    命中的識別字都只是**被順帶提到**）。這件事在散文平面上沒有解——要判斷誰是主詞就要
    理解語意，而那正是判準不該做的事。
  · **「因果宣稱裡的具名量在本場沒有兩個相異觀測值」**（含 0 次觀測）→ 命中 **153 筆**，
    隨機抽 12 筆逐筆判讀 **0 真 12 假**（0%）：命中的全部是 `condition_evaluator`／
    `last_log_path`／`enable_kernel_brain`／某支測試的名字這種**程式符號**，它們根本不是
    「量」，本來就不會有觀測值 ⇒ 這個形狀等於對「句子裡出現 snake_case」發警報。
⇒ **常數／變因這條軸在散文平面上做不出鑑別力**，它只在**落款平面**上是精確的（那裡欄位
與值都是結構化的，不必猜主詞）。所以那一半刻意**不做成警報**，改做成一支**正向工具**
`tools/probe/variate_contrast.py`：餵它一份 JSONL 落款，逐欄印出「觀測數／相異值數／
是不是常數」，並可 `--split-at` 切成兩組看哪些欄位真的區分得開兩組。本事故用它是一行的事
——`spend`／`extra_usage` 會直接印成 `CONSTANT`＝不可能是變因。本判準的訊息因此**指著它**，
讓查證比宣稱便宜（判準治形態、工具治內容，兩者刻意分工，不是同一份知識住兩個家）。

誠實劃界（本檔抓不到什麼）
------------------------
· **只看數字**。「全綠」「已驗證」「零損失」這種**不帶值**的判決一律看不到——它們沒有
  可比對的值域，而那正是 `audit_session.py` 那支事後量測器的射程（兩者刻意分工，不是
  同一份知識住兩個家）。
· 第二個判準只認**反引號包起來的英文**錯誤字面。同一句話改寫成中文轉述（「死於月度支出
  上限」）或拿掉反引號就完全看不到 ⇒ 它守的是**這一型的複發**，不是整類因果謬誤。
· 第二個判準**不判斷因果是對是錯**，只判斷「你把機器的話當成了自己的結論」。上面兩筆
  假陽性正是這個邊界：推理其實成立，只是形態相同。**所以它只出聲、不阻斷**（同上）。
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

#: 「這句話在做機制結論」的標記。`⇒` 收在裡面是量出來的：本 repo 的推論慣用它，而事故
#: 那兩句**都沒有**用 `造成`／`導致`，只用了 `⇒`——不收它就對本事故零召回。
MECHANISM_RE = re.compile(
    r"(根因|真因|成因|病因|真正的原因|造成|導致|肇因|引發|root cause|⇒)")

#: 反引號內的英文長字面（≥11 字元）＝ 錯誤訊息被引述時的典型形態。
_BACKTICK_LITERAL_RE = re.compile(r"`([A-Za-z][A-Za-z0-9'’,.\- ]{10,120})`")

#: 上面那個字面要**看起來像錯誤訊息**才算數（否則整片反引號英文都會進來）。
_ERROR_WORD_RE = re.compile(
    r"(?i)(error|limit|failed|failure|denied|refus|exceed|not found|timeout|"
    r"unauthor|forbidden|cannot|can't|unable|hit your)")

#: 🔴 **符號 ≠ 訊息**——這一條把精確率從 23% 拉到 100%（普查實測，見檔頭）。
#: 錯誤**訊息**是機器寫給人看的散文（小寫詞＋空白）；例外**類別名**是符號
#: （`ModuleNotFoundError`／`DeadlineExceeded`／`WinError 216`／`subprocess.TimeoutExpired`）。
#: 寫「⇒ `ModuleNotFoundError`」的人是在指認一個他推理出來的失效**模式**，不是在轉述機器
#: 的話——那正是本判準要放行的行為。判準：≥2 個空白分隔的詞，且每個詞都不含**詞內大寫**、
#: 也不含 `.`／`_`／`:`（三者都是符號的記號，不是散文的記號）。
_SYMBOL_TOKEN_RE = re.compile(r"[._:]|(?<=.)[A-Z]")


def _is_prose_message(literal: str) -> bool:
    """這串字看起來是「機器寫給人看的一句話」，而不是一個符號名。"""
    tokens = literal.split()
    return len(tokens) >= 2 and not any(_SYMBOL_TOKEN_RE.search(t) for t in tokens)

#: 抑制詞＝「我已經做過變因對照」的證據。普查實測它只擋掉正解那一句（見檔頭）。
CONTRAST_RE = re.compile(
    r"(常數|變因|對照組|對照|反例|控制|兩組|證偽|唯一差異|成功組|失敗組|同一個值|沒有變)")


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


def error_literal_mechanism_hits(claim_text: str, tool_output: str) -> list[dict]:
    """`claim_text` 裡「把機器吐出來的錯誤字面當成機制結論」的句子（`[]`＝沒有）。

    純函式，供攔截端（本檔 Stop 分支）與普查端（`tools/probe/causal_form_census.py`）
    共用同一份判準。三個條件全部是字串比對：① 句子在做機制結論；② 句子引述了一段
    看起來像錯誤訊息的反引號英文字面；③ 那串字**逐字出現在本場工具輸出裡**（＝它確實
    是機器說的，不是我自己造的詞）。句子自帶對照詞時抑制——見檔頭的抑制詞鑑別力量測。
    """
    hits: list[dict] = []
    for sentence in _SENTENCE_RE.split(claim_text):
        sentence = sentence.strip()
        if not sentence or not MECHANISM_RE.search(sentence):
            continue
        if CONTRAST_RE.search(sentence):
            continue
        for literal in _BACKTICK_LITERAL_RE.findall(sentence):
            if not _ERROR_WORD_RE.search(literal) or not _is_prose_message(literal):
                continue
            if literal not in tool_output:
                continue
            hits.append({"literal": literal, "sentence": sentence[:200]})
            break  # 一句只報一次：同一句裡的第二個字面不是另一筆缺陷
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
    # 🔴 兩個判準各自一個逃生口，且**都在讀 payload 之後才分別檢查**：共用一個開關會讓
    # 「我只是想暫時別被唸這一件事」順手把另一件也關掉，而那件事沒有人會注意到。
    try:
        payload = read_hook_payload()
        claim = str(payload.get("last_assistant_message") or "")
        transcript = str(payload.get("transcript_path") or "")
        if not claim or not transcript:
            return 0
        output = _tool_output_digits(transcript)
        if not os.environ.get("AUTOSDD_CLAIM_GUARD_OFF"):
            hits = unsourced_verdict_hits(
                claim, output,
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
        if not os.environ.get("AUTOSDD_CAUSAL_GUARD_OFF"):
            causal = error_literal_mechanism_hits(claim, output)
            if causal:
                listed = "／".join(f"`{h['literal']}`" for h in causal[:3])
                print(
                    f"🔴 這一則有 {len(causal)} 句把**錯誤訊息的字面**（{listed}）當成機制"
                    f"結論。那串字是機器吐給你的**症狀**，不是你查出來的**變因**——變因必須"
                    f"有兩個不同的觀測值（R89 事故：那個量連續 15 列都是 100.0＝常數，數學上"
                    f"不可能是變因）。查證只要一行："
                    f"`python tools/probe/variate_contrast.py <落款.jsonl> --split-at <時刻>`"
                    f"（逐欄印相異值數與 CONSTANT 標記）；已經對照過就在句子裡寫出來"
                    f"（常數／變因／對照組／反例／成功組／失敗組…）即抑制。"
                    f"（判準：.claude/hooks/check_claim_provenance.py"
                    f"；關閉：AUTOSDD_CAUSAL_GUARD_OFF=1）",
                    file=sys.stderr,
                )
    except Exception:  # noqa: BLE001 — fail-open，見檔頭 P0
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
