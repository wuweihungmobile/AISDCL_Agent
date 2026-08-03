#!/usr/bin/env python3
"""ONBOARDING.md §7「live 基線格」產生器 ＋ 新鮮度稽核（generate + --check 慣例）。

WHY 存在（R60 SD-R60-09）：
  R60 為 §7 的 LOC 那一格加了新鮮度鎖，但**只有 `--check` 半邊、沒有產生器**——
  於是「任何動到 `AutoClaude/autoclaude/` 行數的變更」都直接接成根層閘門紅燈 ＋
  必須手工回填一份文件，而本 repo 對「機器可算出來的數字」的既有形狀是
  **產生器 ＋ `--check`**（`AutoClaude/CLAUDE.md` 的 `[Architecture Snapshot]` ↔
  `AutoClaude/tools/snapshot_sync.py`，CI job `claude-md-budget`）。本檔補上缺的
  那半邊：`--write` 一鍵回填，`--check` 供閘門與測試消費，兩者共用同一份取值邏輯，
  不可能一邊算出 A、另一邊算出 B。

守什麼（受管的 live 格；擴充只需在 `_SPECS` 加一筆，判定邏輯不用改）：
  1. `loc-baseline-live:`      → `AutoClaude/tools/check_loc_budget.py --json`
                                 的 `total` / `cap` / `violations`
  2. `rootunit-baseline-live:` → `tools/run_root_unittests.py` 的 `MIN_TESTS`
                                 （§7 那一格的「N tests OK」）

R60 round 3 補的兩件事（四方複審 round 2 全數 REJECT 的兩個根因）：
  A. **受鎖行的散文也要受管**（ARCH-R60R2-03／SA-R60R2-02／SD-R60-R2-03／QA2-R60-02，
     四方獨立全數命中）：round 1 落地本產生器後，受鎖行的 token 已是 845，而**同一行的
     散文仍寫「R60=756」**。⇒ **產生器 ＋ `--check` 只保證「被抽取的那個 token」新鮮，
     完全不保證同一行的散文新鮮**——這是本 repo 對「機械鎖已落地」的認定門檻必須修正的
     地方（DEF-101-562）。兩道判準（見 `prose_problems()`）：
       (1) **受管值不得在受鎖行出現第二次**（≥3 位數才判，見該函式的位數門檻 WHY）：
           散文裡複製一份當輪值，下一次變動時它就是新的 stale 站點。
       (2) **同量宣稱**：值 ≠ live 者必須登記進 `Spec.historical` 並附 WHY，否則紅。
           歷史值放行、當輪值一律不得寫進散文。

R60 round 3 **四方複審之後**回補的三筆（四方獨立命中，非本檔自查）：
  C. **`Spec.historical` 補上 stale 自檢**（QA-R60R3-02／ARCH-R60R3-01 附帶／
     SA-R60R3-04／SD-R60R3-02，**四方全數獨立命中同一筆**）：判準(2) 在 round 2 新增了
     這張豁免表卻沒給它任何反向檢查——注入一筆文件裡從未出現的死登記，`--check` 照樣
     rc=0。而**同一個函式的判準(1)** 錯誤訊息自己就寫著「本鎖刻意不設個別豁免——豁免表
     本身就是下一個 stale 站點」，判準(2) 卻正好設了一張。見 `historical_problems()`。
  D. **判準(2) 不再綁死 `=` 標點**（ARCH-R60R3-01／SD-R60R3-01 二方命中）：原形只認
     `R<輪號>=<數字>` 字面，中文同義散文整類逸出，而受鎖行上當時就躺著未登記的舊值。
     改為「主詞 × 連接」兩段式，並補一道**無輪號主詞**的量測宣稱判準。落地當下即在兩條
     受鎖行各抓到一筆未登記歷史值（其一正是 ARCH 指認的活體證據），皆改以登記收編。
  E. **指紋觸發器四棵 glob 對齊為遞迴**（SD-R60R3-03）：見 `_FINGERPRINT_TREES` 的 WHY。
  F. **指紋改為行尾無關**（DEF-101-613）：原版 hash 原始 bytes，而本機 Windows 工作樹
     有 48／72／92 檔是 CRLF、索引卻因 `.gitattributes` 的 `* text=auto eol=lf` 一律 LF
     ⇒ **fresh clone／CI runner／macOS 上四格必然全部對不上，`--check-snapshot` 開箱即紅**。
     修法＝hash 前先在 bytes 層折行尾，見 `_normalize_eol`。本輪主題正是跨平台相容性，
     故不交棒。
  B. **表②（dated snapshot）從「靠人記得」升為「一條指令 ＋ 因果式 stale 觸發器」**
     （ARCH-R60R2-02③／SA-R60R2-02②）：round 1 填了 v0.30=1736，round 2 動了 v0.30
     測試樹使實測變 1747，**沒人記得回填**，而表頭同時宣稱「四格皆經獨立覆核」⇒ 假宣稱。
       - `--write --with-slow`：實跑 ci-gate（解析其 `逐軌計數：vX:N` 自證行）＋ AutoClaude
         pytest，四格一次填完（`_SLOW_SPECS`）。
       - `--check-snapshot`：重算四套**測試樹內容指紋**與文件記載比對，指紋一變即判
         presumed stale。判準是**因果的**（計數只可能因測試樹變動而變），同
         `ADR-SD09-011`「把證據從日曆解綁、改綁源碼變動」的既有先例。
       - 接線刻意只到 **pre-push**（收輪＝push 時點付這個代價才合理），**不**接根層 unittest
         閘門——那支每輪跑數十次，會養成忽略紅燈的習慣。
     🔴 **對 ARCH-R60R2-06（護欄層成長過快）的正面回應**：本次擴充**零新增鎖檔、零新增
     測試檔**——全部落在本檔既有 `_SPECS` 機制與既有
     `tools/tests/test_doc_loc_baseline_freshness_r60.py` 內，且淨效果是**把表② 那 4 格
     「零機制」的欄位收進既有機制** ⇒ 未受檢面淨減少。這是對「禁止新增鎖、只准合併」
     的遵守，不是規避。

R67 補的兩件事（本輪 R67-D1〔P1〕／R67-D6／R67-D20；WHY 見各自區塊）：
  G. **平台維度升為一等公民**（R67-D1，本輪唯一 P1）：本檔在 R67 之前**全檔零平台偵測**
     （`grep -E "platform|sys.platform|os.name|darwin|win32"` 零命中），而表② 四格的
     欄位正則一律以 `**…**` 粗體錨定「Windows 11」那一欄（原註解自陳「以 `**` 包裝限定
     在 Windows 欄」）。⇒ **在 macOS 上執行文件與 `--check-snapshot` 紅燈訊息都指路的
     `--write --with-slow`，會把 macOS 實測值靜默寫進標示「Windows 11 實測」的格子**，
     摧毀該表存在的唯一理由（讓開發者分辨「平台差異」與「退化」）並產生一句假 provenance。
     修法**不是**「照平台換一組正則」（那是同一語意兩份實作，本檔一直在治的病），而是
     **改以 markdown 欄位座標定位**：`_PLATFORM_COLUMN_LABELS` 只記「平台鍵 → 表頭識別字」，
     真正的欄號由 `platform_cell_index()` **當場從表頭推導**（欄號寫死才會在表格增欄時
     靜默抽錯欄——正是 SA-R60-01 的形態）；讀寫一律先 `_split_row()` 切格、只在自己那
     一格內做 `findall`／`sub`（見 `slow_documented`／`render_slow`）⇒ **寫到別欄在結構
     上不可能發生**，且兩欄共用同一組 Field 正則（少一份會漂移的東西）。回填路徑另加
     兩道守門：(a) 無對應欄的平台（例：Linux CI runner）**fail-loud rc=2**，絕不猜一欄
     來寫；(b) `--platform` 只准用於唯讀稽核，**不得**與 `--write` 併用——跨平台代填
     產生的正是一句假 provenance，那就是 R67-D1 本體。
  H. **指紋記帳改為 per-platform**（R67-D6）：原版只有一條全域 `snapshot-fingerprints`
     錨，語意是「上一次回填時的測試樹」；但回填只寫得到一欄 ⇒ **另一欄的 stale 在結構上
     永遠測不到**（實測：macOS 欄三格灌成 9999，`--check-snapshot` 照樣印 ✅ rc=0）。
     改為每平台一條 `snapshot-fingerprints-<平台鍵>:` 錨，各自記「**該欄的數字是在哪一棵
     測試樹上量的**」＋ `measured-at`／`host`／`docker`／`pgextras` provenance（何時、哪台
     機器、docker daemon 狀態、venv 有無 PG extras——後兩者各自都會改變計數：docker 停用
     時 v0.01／v0.30 各 −3〔§7 既有容差段〕、PG extras 存在時 AutoClaude 的 PG-gated 測試
     由 skip 轉 pass 使 passed 虛高，兩者不入帳就是下一個「把環境差異誤判為退化」）。
     判準：**當前平台欄的記錄指紋 ≠ live 指紋 ⇒ 該欄 presumed stale（紅）**；
     其他欄只做 ⚠️ 告知不影響 rc（別台機器的欄不是本機修得動的東西，硬紅只會養成忽略
     紅燈的習慣）。無對應欄的平台（Linux CI runner）判準**退化為舊語意**：
     「沒有任何一欄是新鮮的」才紅——嚴格弱於逐欄判準，如實劃界寫在 `check_snapshot()`。
  I. **`main()` argparse 化 ＋ 未知旗標 fail-loud**（R67-D20）：原版用 `"--flag" in argv`
     手搓解析，未知旗標一律靜默掉進 default 分支並 rc=0。實測後果：`--check-snapsho`
     （少一字）在「表② 確實過期」的工作樹上回 **rc=0 假綠**，而正確拼法 rc=1；
     文件到處引用的 `--check` 根本不是實存旗標，只是恰好掉進 default 才「看起來對」。
     修法＝argparse（未知旗標 rc=2、`--help` 印用法）＋**把 `--check` 實作為顯式旗標**
     （選它而非改文件：`--check` 已被 ONBOARDING §7、`CrossPlatform_Scan_Dimensions.md`、
     `ADR-XPLAT-002` 三份文件引用，且「產生器 ＋ `--check`」正是本 repo 既有慣例
     〔`snapshot_sync.py`〕——讓字面成真比讓三份文件改口更小、更對）。
  J. **指紋夾住慢量測窗口**（DEF-101-677，R67 收尾 Scan-H）：原本是「先跑分鐘級的
     `measure_slow()`、**跑完之後**才 `measure_fingerprints()`」⇒ 樹若在那段窗口內被改動
     （並行的修復包還在寫測試檔），錨記下**改動後**的樹、四格計數卻留在**改動前**的樹，
     事後 `--check-snapshot` 指紋相符判 ✅ rc=0 而計數已 stale。**回填路徑親手把觸發器
     拆掉**：樹確實變動了（那正是本觸發器唯一認得的事件），卻被寫成基準。修法＝
     `measure_slow_on_stable_tree()` 前後各取一次指紋，不同即 fail-loud 且**一個字都不寫**
     （見該函式的完整 WHY／代價／劃界）。同型收斂：`--check-snapshot` 與 `--json` 原本在
     單次呼叫內把 live 指紋量 2～3 次 ⇒ 判決與取證可能來自不同時點；改為一次量、注入共用。

🔴 判準邊界（誠實劃界）：
  - **只管帶錨點的那一行**。§7／§9 其他地方的數字是有標日期的歷史快照（如 R57 註的
    `total=20356`），依本 repo「時代快照不納管」慣例（見
    `tools/check_pytest_baseline_sites.py` docstring）刻意不回填、也刻意不鎖。
  - **表① 尚未平台化**（如實揭露）：`_SPECS` 兩格的 live 值本身無平台差異（LOC 是純靜態
    分析；`MIN_TESTS` 是兩平台共用的收集數下限），受鎖 token 仍只住 Windows 欄，
    macOS 欄是 dated snapshot 散文、不受 live 鎖管轄。R67 的處置是**把該格改寫成指向
    live 值**（而非再寫死一個會過期的數字），並在格內明說它不受鎖管轄——該措辭由
    `test_table1_macos_cell_declares_it_is_not_lock_covered` 釘住。表②（有真平台差）
    才是本輪平台化的標的。
  - **指紋只覆蓋測試樹**（四棵皆遞迴 `**/*.py` 的**行尾正規化後**內容）。生產碼變動改變
    `parametrize`
    來源、docker daemon 可用性、平台差異都能改變計數而指紋不動 ⇒ 它是 stale 的
    **充分觸發器、非必要條件**（會漏、不會冤）。要它變成必要條件就得付整套重測的代價，
    那正是表② 沒有 live 鎖的原因。
  - **窗口夾住的是「淨變動」**（J 的劃界）：`measure_slow_on_stable_tree()` 只比對慢量測
    前後兩點的指紋 ⇒ 在窗口內改動、又在窗口結束前還原（暫存檔一寫一刪）仍偵測不到。
    這仍屬「會漏、不會冤」那一側；被根治的是**回填路徑自己製造出來的漏**，不是全部的漏。
  - 每個欄位的正則在受鎖行上必須**恰好命中一次**：0 次＝敘述被改寫成抽不到的形態、
    ≥2 次＝抽錯欄（例如同一列 macOS 欄與 Windows 欄都寫了 `total=`），兩者皆
    fail-loud。這一條是 R60 SA-R60-01 的直接教訓：原鎖用 `search()` 取第一個命中，
    讀到的其實是 macOS 欄，而它恰好與 Windows 欄同值，所以看不出來。
  - `skipped=N`（根層測試那格的另一半）與 `8 kept / 0 broken`（lint-imports）
    **不在管理範圍**：前者無現場取值來源、後者要另跑 import-linter。如實揭露，
    未來要納管就在該處加新錨點 ＋ 在 `_SPECS` 補一筆。
  - **`--check` 不是 LOC 閘門**：`check_loc_budget.py --json` 在 LOC 破線時回 rc=1
    但**仍會印出完整 JSON**，本檔照樣解析並比對，且當 `violations > 0` 時訊息會明說
    「這是 LOC 閘門自己紅、不是文件 stale」，避免錯誤定位（SD-R60-09 附帶項）。

用法（argparse；未知旗標一律 rc=2 fail-loud，`--help` 印完整用法）：
  python tools/sync_onboarding_baselines.py                  # 稽核模式（＝ --check，表①）
                                                             # stale 即 exit 1
  python tools/sync_onboarding_baselines.py --check          # 同上的顯式寫法
                                                             # （文件與閘門引用的那條路）
  python tools/sync_onboarding_baselines.py --write          # 一鍵回填表①（bytes 層 LF 寫入）
  python tools/sync_onboarding_baselines.py --check-snapshot # 表② 指紋比對（毫秒級，pre-push 消費）
  python tools/sync_onboarding_baselines.py --write --with-slow
                                            # 表①＋**本平台那一欄**＋指紋全回填（分鐘級）
  python tools/sync_onboarding_baselines.py --json           # 機讀報表（含表② 與逐平台指紋）
  python tools/sync_onboarding_baselines.py --check-snapshot --platform win32
                                                             # 在 mac 上稽核 Windows 欄
                                                             # （唯讀；不得用於 --write）
測試：tools/tests/test_doc_loc_baseline_freshness_r60.py
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import platform as platform_mod
import re
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護
from lib import baseline_origin as _BO  # noqa: E402  # 基線三態＋nightly 探針（R70 抽出）

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ONBOARDING = _REPO_ROOT / "ONBOARDING.md"
_LOC_TOOL = _REPO_ROOT / "AutoClaude" / "tools" / "check_loc_budget.py"


@dataclass(frozen=True)
class Field:
    """一個受管數字：抽取正則（必須恰一群組）＋ 回填時的字面樣板。"""

    name: str
    pattern: re.Pattern[str]
    template: str  # 以 {v} 帶入實測值


@dataclass(frozen=True)
class Spec:
    """一個受管的 live 格：錨點 → 欄位集合 ＋ 取值來源 ＋ 散文歷史值白名單。"""

    anchor: str
    fields: tuple[Field, ...]
    source: str  # 人讀的取值來源說明（訊息用）
    # 受鎖行散文裡允許出現的 `R<輪號>=<數字>` 同量歷史宣稱。鍵＝輪號字串、值＝(數字, WHY)。
    # 判準見 prose_problems()：不在此表且 ≠ live 值者一律紅。
    historical: tuple[tuple[str, int, str], ...] = ()


# 受管值在受鎖行重複出現的判定門檻（位數）。
# WHY 3：`violations=0`／`8 kept` 這類 1~2 位數在散文裡是無關的巧合同值（「8 支 pgid」
# 「1 支 symlink」），對它們硬判會製造大量誤紅，而它們 stale 的危害近零。3 位數以上
# （845 tests／20361 total）才是真正會誤導讀者的量。門檻寫在這裡而非散文裡（本檔自己也
# 受「不得把可機械算出的數字寫進散文」那條紀律管）。
_PROSE_DUP_MIN_DIGITS = 3

# 散文裡的「同量宣稱」形態。刻意拆成**主詞 × 連接**兩段（而非一條長正則）：要收一種新
# 方言＝往集合裡加一個字，判準結構不必動。
#
# 🔴 R60 round 3（ARCH-R60R3-01／SD-R60R3-01 二方獨立命中）：round 2 版本寫死
# `R(\d+)\s*=\s*(\d+)`，**把判準綁死在 `=` 這一個標點上**，於是同義的中文散文全數逸出
# （`R60 收尾實測 756`／`R60：756`／`R60 — 756 tests OK`／`R60 為 756` 一律放行），
# 而受鎖行上**當時就真的躺著一個未登記的舊值**（ARCH 的活體證據）。這正是本輪反覆在治
# 的「鎖比對表面形式、不比對語意」反模式：判準只認一種字面，換個標點就繞過去。
_CLAIM_SUBJECT = r"(?:R|[Rr]ound\s+)(\d+)"
# 連接：等號家族／全形冒號／破折號／中文繫詞。
# 🔴 **刻意不收 ASCII 連字號 `-`**：本 repo 的 finding id 一律長成 `SA-R60-01`／
# `SD-R60-R2-03`／`DEF-101-562`，即 `R<輪號>-<數字>` ⇒ 收了 `-` 會把每一個 id 都判成
# 同量宣稱（實測：收 `-` 後 `SA-R60-01` 產出假紅「R60=1」）。破折號只收全形 `—`／`–`
# 且要求兩側空白，同一理由。
_CLAIM_LINK = r"(?:\s*[=＝:：]\s*|\s+[—–]\s+|\s+(?:收尾)?(?:實測|重釘|為|是)\s*)"
_PROSE_ROUND_CLAIM_RE = re.compile(_CLAIM_SUBJECT + _CLAIM_LINK + r"\*{0,2}(\d+)")

# 無輪號主詞的量測宣稱：`MIN_TESTS 已重釘 <值>`／`實測：主控動工量 <值>` 這類句子沒有
# `R<輪號>` 可鉤，但「量測動詞 ＋ 具體數字」本身就是對受管量的宣稱 ⇒ 同樣要受管。
# 間隔上限刻意**有界且不得跨數字**：緊鄰版（`\s*`）抓不到中間插了敘述的那一種，
# 無界版則會把整行的數字全部吸進來。位數門檻沿用 `_PROSE_DUP_MIN_DIGITS`（同一個理由：
# 1~2 位數的巧合同值極多），不另立第二個魔數。
_PROSE_MEASURE_CLAIM_RE = re.compile(
    rf"(?:已)?(?:收尾)?(?:實測|重釘)[^\d\n]{{0,10}}?\*{{0,2}}(\d{{{_PROSE_DUP_MIN_DIGITS},}})"
)


_SPECS: tuple[Spec, ...] = (
    Spec(
        anchor="loc-baseline-live:",
        fields=(
            Field("total", re.compile(r"total=(\d+)"), "total={v}"),
            Field("cap", re.compile(r"cap=(\d+)"), "cap={v}"),
            Field("violations", re.compile(r"violations=(\d+)"), "violations={v}"),
        ),
        source="AutoClaude/tools/check_loc_budget.py --json",
        historical=(
            (
                "60",
                20359,
                "R60 主控動工當下的 LOC 量測值。受鎖行以它舉例說明「為何只在收輪的最終"
                "工作樹填一次」（同輪另一包改 utils/logger.py 後該值即變動）。"
                "R60 round 3 放寬判準(2)（ARCH-R60R3-01）後才第一次被抓出來——在那之前"
                "它是受鎖行上未經登記的散文歷史值，與 ARCH 指認的那一筆是同一species",
            ),
        ),
    ),
    Spec(
        anchor="rootunit-baseline-live:",
        fields=(Field("tests", re.compile(r"(\d+) tests OK"), "{v} tests OK"),),
        source="tools/run_root_unittests.py 的 MIN_TESTS",
        historical=(
            ("57", 616, "R57 macOS 實機量測（ONBOARDING §7 表① macOS 欄同值）"),
            ("59", 661, "R59 收尾實測，見 DEF-101-519"),
            (
                "60",
                756,
                "R60 round 1 的 MIN_TESTS 值。受鎖行引用 SA-R60-01／ARCH-R60-03 的原始"
                "發現逐字語料（『本格寫 661 而 MIN_TESTS 已重釘 <此值>』）以保住該發現的"
                "具體性。🔴 **這一筆就是 ARCH-R60R3-01 指認的活體證據**：判準(2) 綁死 `=` "
                "標點時它是受鎖行上唯一未登記的散文歷史值，放寬後轉紅、於此登記；"
                "刪掉散文而非登記會毀掉該發現的可讀性，登記才是本機制設計的出口",
            ),
        ),
    ),
)


class BaselineToolError(AssertionError):
    """取值來源本身壞掉（非「文件 stale」）——必須與 stale 分開回報。"""


# ─────────────────────── 平台維度（R67-D1／D6，檔頭 G） ───────────────────────
# 平台鍵 → §7 表② 表頭裡那一欄的識別字。**刻意只存識別字、不存欄號**：欄號寫死會在
# 表格增欄／換欄序時靜默抽錯欄（SA-R60-01 的原始形態），識別字則讓欄位由表頭當場推導，
# 表頭一改或該欄被刪即 fail-loud。
_PLATFORM_COLUMN_LABELS: dict[str, str] = {"darwin": "macOS", "win32": "Windows"}

# `--platform` 未指定時的哨兵：解析為「本機平台」。刻意不用 None——None 有語意
# （「本平台在表② 沒有欄」，例如 Linux CI runner），兩者混用會讓退化判準無聲失準。
_AUTO_PLATFORM = "auto"

# markdown 表格分隔列（`|---|---|`；本節表格在引言塊內，故容許行首 `> `）。
_SEPARATOR_ROW_RE = re.compile(r"^\s*>?\s*\|(?:\s*:?-{2,}:?\s*\|)+\s*$")


def current_platform_key(raw: str | None = None) -> str | None:
    """`sys.platform` → 受管平台鍵；無對應欄者回 `None`（**不猜一欄**）。

    Linux 刻意沒有欄：表② 只有兩台實機在維護，給 Linux 一欄就是承諾一份沒人量的數字。
    """
    value = sys.platform if raw is None else raw
    for key in _PLATFORM_COLUMN_LABELS:
        if value.startswith(key):
            return key
    return None


def resolve_platform(requested: str | None) -> str | None:
    """把 CLI／呼叫端給的平台參數解析成平台鍵（`_AUTO_PLATFORM` → 本機平台）。"""
    if requested == _AUTO_PLATFORM:
        return current_platform_key()
    return requested


def _split_row(line: str) -> list[str]:
    """markdown 表格列 → 原樣格片段（**不 strip**，以便 `"|".join()` 原地重組）。"""
    return line.split("|")


def _anchored_index(lines: list[str], anchor: str) -> int:
    """帶錨點那一行的索引；0 行或多行皆 fail-loud（同 `anchored_line` 的判準）。"""
    hits = [i for i, line in enumerate(lines) if anchor in line]
    if len(hits) != 1:
        raise AssertionError(
            f"ONBOARDING.md 的基線錨點「{anchor}」命中 {len(hits)} 行（預期恰 1）"
            f"——錨點被刪除或被複製都會讓本鎖失去鑑別力，故此處 fail-loud"
        )
    return hits[0]


def platform_cell_index(lines: list[str], row_idx: int, platform_key: str) -> int:
    """`lines[row_idx]` 這一列中，屬於 `platform_key` 的格在 `_split_row()` 裡的索引。

    由**表頭**推導（往上找最近的分隔列 `|---|`，其上一行即表頭），不寫死欄號。
    表頭中含該平台識別字的格必須恰 1 個、且該列格數必須與表頭一致——兩者任一不成立
    都代表表格結構被改動，此時**寧可 fail-loud 也不准猜**：猜錯的代價正是把某平台的
    實測值寫進另一平台的欄位（R67-D1）。
    """
    label = _PLATFORM_COLUMN_LABELS[platform_key]
    header_idx = next(
        (i - 1 for i in range(row_idx - 1, -1, -1) if _SEPARATOR_ROW_RE.match(lines[i])),
        None,
    )
    if header_idx is None or header_idx < 0:
        raise AssertionError(
            f"第 {row_idx + 1} 行所屬表格找不到表頭（往上無 `|---|` 分隔列）"
            f"——表格結構已變動，平台欄位無法推導。\n  行文：{lines[row_idx].strip()[:200]}"
        )
    header_cells = _split_row(lines[header_idx])
    hits = [i for i, cell in enumerate(header_cells) if label in cell]
    if len(hits) != 1:
        raise AssertionError(
            f"表頭（第 {header_idx + 1} 行）中含平台識別字「{label}」的格有 {len(hits)} 個"
            f"（預期恰 1）——該平台欄被刪除、被複製或表頭措辭改到抽不到；"
            f"此時不得猜欄。\n  表頭：{lines[header_idx].strip()[:240]}"
        )
    row_cells = _split_row(lines[row_idx])
    if len(row_cells) != len(header_cells):
        raise AssertionError(
            f"第 {row_idx + 1} 行的格數 {len(row_cells)} ≠ 表頭格數 {len(header_cells)}"
            f"——欄位對不齊時依表頭推導出的欄號會指到別的格。\n"
            f"  行文：{lines[row_idx].strip()[:200]}"
        )
    return hits[0]


# ─────────────────────────── 文件側（純函式） ───────────────────────────


def anchored_line(text: str, anchor: str) -> str:
    """取唯一帶錨點的行；0 行或多行皆 fail-loud（文件改組須同步本案）。"""
    lines = [line for line in text.splitlines() if anchor in line]
    if len(lines) != 1:
        raise AssertionError(
            f"ONBOARDING.md 的基線錨點「{anchor}」命中 {len(lines)} 行（預期恰 1）"
            f"——錨點被刪除或被複製都會讓本鎖失去鑑別力，故此處 fail-loud；"
            f"若刻意改組 §7，請把錨點註解搬到新的基線格上"
        )
    return lines[0]


def parse_documented(line: str, spec: Spec) -> dict[str, int]:
    """從受鎖行抽出文件字面值；欄位缺席或重複命中皆 fail-loud。"""
    values: dict[str, int] = {}
    problems: list[str] = []
    for field in spec.fields:
        found = field.pattern.findall(line)
        if len(found) != 1:
            problems.append(f"{field.name}（命中 {len(found)} 次，預期恰 1）")
        else:
            values[field.name] = int(found[0])
    if problems:
        raise AssertionError(
            f"受鎖行（錨點 {spec.anchor}）的欄位抽取失敗：{problems}。\n"
            f"  0 次＝敘述被改寫成本鎖抽不到的形態；≥2 次＝同一列有多個同形數字"
            f"（例如 macOS 欄與 Windows 欄都寫了同一個欄位）⇒ 會抽錯欄。\n"
            f"  兩者都不得靜默放行（R60 SA-R60-01：原鎖取第一個命中，讀到的其實是"
            f"macOS 欄）。\n  行文：{line.strip()[:200]}"
        )
    return values


def prose_problems(line: str, spec: Spec, live: dict[str, int]) -> list[str]:
    """受鎖行的**散文**新鮮度判準（R60 round 3，DEF-101-562）。純函式，供測試以合成行驅動。

    兩道判準（WHY 見檔頭 A）：
      (1) 受管值不得在受鎖行出現第二次（≥ `_PROSE_DUP_MIN_DIGITS` 位數才判）。
      (2) `R<輪號>=<數字>` 形態的同量宣稱，值 ≠ live 者必須在 `spec.historical` 登記。
    """
    problems: list[str] = []

    for field in spec.fields:
        value = live[field.name]
        digits = str(value)
        if len(digits) < _PROSE_DUP_MIN_DIGITS:
            continue
        occurrences = len(re.findall(rf"(?<!\d){re.escape(digits)}(?!\d)", line))
        if occurrences > 1:
            problems.append(
                f"受管值 {field.name}={value} 在受鎖行出現 {occurrences} 次（預期恰 1）"
                f"——第二次就是下一個 stale 站點：本鎖只會回填被抽取的那一個 token，"
                f"散文裡那一份下次變動時不會被更新。\n"
                f"    處置：把散文那份改成指向左欄的寫法（例「見本格 live 值」「見左欄」）；"
                f"若確為無關的巧合同值，同樣改寫散文使其字面不同（本鎖刻意不設個別豁免——"
                f"豁免表本身就是下一個 stale 站點）"
            )

    allowed_pairs = {(rnd, val) for rnd, val, _why in spec.historical}
    allowed_values = {val for _rnd, val, _why in spec.historical}
    live_values = set(live.values())

    reported: set[int] = set()
    for match in _PROSE_ROUND_CLAIM_RE.finditer(line):
        rnd, val = match.group(1), int(match.group(2))
        if val in live_values or (rnd, val) in allowed_pairs:
            continue
        reported.add(val)
        # 訊息刻意引**逐字命中的原文**而非重組成 `R<n>=<v>`：判準已不再只認一種字面，
        # 重組會讓讀者在文件裡搜不到那一段（round 2 版本就是這樣寫的）。
        problems.append(
            f"受鎖行散文有同量宣稱「{match.group(0).strip()}」，但它既不等於任何 live 值"
            f" {sorted(live_values)}、也不在 Spec.historical 白名單內。\n"
            f"    這正是 R60 round 2 四方全數命中的形態：受鎖 token 已回填為當輪實測，"
            f"而散文仍留著同輪的較舊宣稱（DEF-101-562）。\n"
            f"    處置：歷史值 → 在 `_SPECS` 的 `historical` 登記 (輪號, 值, WHY)；"
            f"當輪值 → **不要寫進散文**，改寫成「見本格 live 值」"
        )

    for match in _PROSE_MEASURE_CLAIM_RE.finditer(line):
        val = int(match.group(1))
        if val in live_values or val in allowed_values or val in reported:
            continue
        problems.append(
            f"受鎖行散文有**無輪號主詞**的量測宣稱「{match.group(0).strip()}」，"
            f"而它既不等於任何 live 值 {sorted(live_values)}、也不在 Spec.historical "
            f"白名單內。\n"
            f"    ⚠️ 這一道是 R60 round 3 補的（ARCH-R60R3-01）：判準綁死 `=` 標點時，"
            f"『某某已重釘 <值>』『實測：某某 <值>』整類句子全部逸出，而受鎖行上當時就"
            f"躺著這樣一個未登記的舊值。\n"
            f"    處置：歷史值 → 在 `_SPECS` 的 `historical` 登記 (輪號, 值, WHY)"
            f"（無輪號主詞者，輪號寫進 WHY 即可）；當輪值 → 改寫成「見本格 live 值」"
        )
    return problems


def historical_problems(line: str, spec: Spec, live: dict[str, int]) -> list[str]:
    """`Spec.historical` 白名單的 **stale 自檢**（反向檢查）。純函式。

    🔴 WHY（R60 round 3，**四方全數獨立命中**：QA-R60R3-02／ARCH-R60R3-01 附帶／
    SA-R60R3-04／SD-R60R3-02）：round 2 為判準(2) 新增了 `Spec.historical` 這張豁免表，
    **卻沒有給它任何 stale 自檢**——注入一筆「文件從未出現過」的死登記，`--check` 照樣
    rc=0、零訊號。諷刺的是**同一個函式的判準(1)** 錯誤訊息裡自己就寫著「本鎖刻意不設個別
    豁免——豁免表本身就是下一個 stale 站點」，而判準(2) 就設了一張，且沒補上那句話所預言
    的防護。同 repo 的兩張姊妹豁免表都有自檢（`_BASELINE_WAIVERS` 的
    `test_baseline_waivers_are_not_stale`、`archive_defect_log._ARITY_BASELINE` 的
    「實測 < 登記即紅」），本表是唯一的例外 ⇒ 同輪內標準不一致。

    判準＝**leave-one-out**：把一筆登記拿掉後，受鎖行若**不會多出任何一條問題**，代表它
    現在沒有遮蔽任何東西 ⇒ stale。刻意不另寫第二套「這筆登記對應到哪段散文」的比對邏輯
    ——那會變成同一個語意兩個算法（本檔一直在治的病），而且判準(2) 一放寬就會失準。

    邊界（誠實劃界）：同一個**值**登記兩筆時，leave-one-out 會互相遮蔽而失去鑑別力
    （拿掉任一筆，另一筆仍放行）⇒ 該情形另以顯式的重複登記判準擋在前面。
    """
    problems: list[str] = []

    seen: dict[int, str] = {}
    for rnd, val, _why in spec.historical:
        if val in seen:
            problems.append(
                f"`historical` 把同一個值 {val} 登記了兩筆（輪號 {seen[val]} 與 {rnd}）"
                f"——兩筆會互相遮蔽，使下方的 leave-one-out stale 自檢對這個值失去鑑別力。\n"
                f"    處置：只留一筆，把另一個輪號併進該筆的 WHY"
            )
        seen[val] = rnd

    baseline = set(prose_problems(line, spec, live))
    for idx, (rnd, val, why) in enumerate(spec.historical):
        reduced = replace(
            spec, historical=spec.historical[:idx] + spec.historical[idx + 1 :]
        )
        if set(prose_problems(line, reduced, live)) <= baseline:
            problems.append(
                f"`historical` 的登記 (輪號 {rnd}, 值 {val}) 已 **stale**：把這一筆拿掉之後，"
                f"受鎖行不會多出任何一條問題 ⇒ 它現在沒有遮蔽任何東西"
                f"（散文已被改寫或該宣稱已被刪除）。\n"
                f"    **這是好消息，紅燈只是要你回收登記**——豁免只准因為「散文裡還留著那個"
                f"歷史值」而存在，不准因為「沒人記得回收」而存在。\n"
                f"    處置：編輯 tools/sync_onboarding_baselines.py 的 `_SPECS`，把錨點"
                f" `{spec.anchor}` 那筆 Spec 的 `historical` 中**這一筆整個刪掉**。\n"
                f"    該筆登記的 WHY 原文：{why}"
            )
    return problems


def render(text: str, measured: dict[str, dict[str, int]]) -> str:
    """把受鎖行的數字就地換成實測值，回傳新文件內容（不寫檔）。"""
    lines = text.split("\n")
    for spec in _SPECS:
        values = measured[spec.anchor]
        target = anchored_line(text, spec.anchor)
        parse_documented(target, spec)  # 先確認可抽取（含恰一次），再改寫
        idx = next(i for i, line in enumerate(lines) if spec.anchor in line)
        new_line = lines[idx]
        for field in spec.fields:
            new_line = field.pattern.sub(
                field.template.format(v=values[field.name]), new_line, count=1
            )
        lines[idx] = new_line
    return "\n".join(lines)


# ─────────────────────────── 取值來源側 ───────────────────────────


def measure_loc() -> dict[str, int]:
    """實跑 check_loc_budget.py --json。rc=1（LOC 破線）仍會有完整 JSON，照樣解析。

    violations 的算式刻意鏡射該工具純文字輸出的 `violations=` 欄位
    （absolute + tier + special + total 破線，見 check_loc_budget.check()），
    這樣文件裡照抄工具輸出的人不會被本鎖誤殺。
    """
    proc = subprocess.run(
        [sys.executable, str(_LOC_TOOL), "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(_REPO_ROOT),
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise BaselineToolError(
            f"check_loc_budget.py --json 沒有印出可解析的 JSON（rc={proc.returncode}）"
            f"——這是**取值來源壞掉**，不是文件 stale；請先修那件事。\n"
            f"stdout: {proc.stdout[-800:]}\nstderr: {proc.stderr[-800:]}"
        ) from exc
    return {
        "total": int(payload["total"]),
        "cap": int(payload["cap"]),
        "violations": (
            len(payload["absolute_violations"])
            + len(payload["tier_violations"])
            + len(payload["special_violations"])
            + (1 if payload["total_violation"] else 0)
        ),
    }


def measure_rootunit() -> dict[str, int]:
    """讀 tools/run_root_unittests.py 的 MIN_TESTS（同一份 repo 的既成 SSOT）。

    刻意用 import 而非重跑整套 unittest：MIN_TESTS 就是「收輪時填實測值」的釘選
    （見該檔第 38 行的重釘紀律），文件與它必須是同一個數字——R60 SA-R60-01 抓到的
    正是「MIN_TESTS 已重釘 756 而 §7 仍寫 661」這種同 repo 兩種說法。
    """
    import run_root_unittests  # noqa: PLC0415  # 延後 import：避免 CLI 未用到時付代價

    return {"tests": int(run_root_unittests.MIN_TESTS)}


_MEASURERS = {
    "loc-baseline-live:": measure_loc,
    "rootunit-baseline-live:": measure_rootunit,
}


def measure_all() -> dict[str, dict[str, int]]:
    return {spec.anchor: _MEASURERS[spec.anchor]() for spec in _SPECS}


# ──────────────── 表②（dated snapshot）：一條指令回填 ＋ 指紋觸發器 ────────────────
# WHY 分成 _SLOW_SPECS 而非塞進 _SPECS：這四格要實跑整套測試（分鐘級），不能進根層
# unittest 閘門的預設路徑。詳見檔頭 B。

# 🔴 R67-D6：**每平台一條錨**（原版是全域單一 `snapshot-fingerprints:`）。單錨的語意是
# 「上一次回填時的測試樹」，但回填在結構上只寫得到一欄 ⇒ 另一欄的 stale 永遠測不到
# （實測：macOS 欄三格灌成 9999，`--check-snapshot` 照樣 ✅ rc=0）。逐平台記帳之後，
# 每一欄各自回答「**這一欄的數字是在哪一棵測試樹上量的**」。
_FINGERPRINT_ANCHOR_PREFIX = "snapshot-fingerprints-"
_FP_LEN = 12  # sha256 前 12 hex；碰撞機率對「偵測有人改了測試樹」這個用途遠足夠

# 逐平台 provenance 欄位（缺任一欄即 fail-loud）。**provenance 是這張表能被信任的全部
# 理由**，讓它「可以沒有」等於讓它消失；且 docker／pgextras 兩項各自都會改變計數
# （docker 停用 → v0.01／v0.30 各 −3；PG extras 存在 → AutoClaude PG-gated 測試由 skip
# 轉 pass 使 passed 虛高），不入帳就是下一位驗證者把環境差異誤判為退化。
# 基線三態語意＋nightly 探針住 `tools/lib/baseline_origin.py`（R70 依 ADR-SD08-001 棘輪的
# 「抽共用模組」路徑抽出；事故原文／判準論證全在該模組檔頭）。此處只做名稱再匯出。
_ENV_PROVENANCE_FIELDS, _UNRECORDED = _BO.ENV_PROVENANCE_FIELDS, _BO.UNRECORDED
_ORIGIN_FIELD, _ORIGIN_VALUES = _BO.ORIGIN_FIELD, _BO.ORIGIN_VALUES
_ORIGIN_SELF, _ORIGIN_PRE_MECHANISM = _BO.ORIGIN_SELF, _BO.ORIGIN_PRE_MECHANISM
_ORIGIN_NEVER, _PROVENANCE_FIELDS = _BO.ORIGIN_NEVER, _BO.PROVENANCE_FIELDS
_COVERAGE_SOURCES = _BO.COVERAGE_SOURCES


def fingerprint_anchor(platform_key: str) -> str:
    return f"{_FINGERPRINT_ANCHOR_PREFIX}{platform_key}:"

# 指紋覆蓋的測試樹：鍵＝文件裡的欄位名，值＝(相對路徑, glob)。
#
# 🔴 **四棵一律用遞迴 `**/*.py`**（R60 round 3 SD-R60R3-03）：round 2 版本三棵 SDD 樹用
# 非遞迴 `*.py`、只有 AutoClaude 用 `**/*.py`，四棵不對稱且無 WHY。而表② 那四格的計數
# 全部來自 **pytest，pytest 收集測試是遞迴的** ⇒ 在任一棵的子目錄新增測試會改變計數、
# 指紋卻不動＝觸發器漏（注入實測：改 top-level 檔轉紅、新增 top-level 檔轉紅、
# **新增子目錄檔不轉紅**）。修法刻意選「把三棵對齊成遞迴」而非「補一條 WHY 說明會漏」：
# 這是**消除不對稱**，不是加機制。三棵現況子目錄有 `fixtures/` 但 `.py` 數為零，
# 故改用遞迴 glob 後四格指紋逐格 byte-identical、文件無需回填（已實測比對）。
_FINGERPRINT_TREES: tuple[tuple[str, str, str], ...] = (
    ("v001", "AISDLC_SDD/AISDLC_SDD_v0.01/tools/fsm_runtime/tests", "**/*.py"),
    ("v030", "AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/tests", "**/*.py"),
    ("scripts", "AISDLC_SDD/scripts/tests", "**/*.py"),
    ("autoclaude", "AutoClaude/tests", "**/*.py"),
)

# 🔴 **rootdir conftest 也是該格計數的輸入**（R67 round 2，SD-R67-02）。
#
# WHY：上面那段（R60 SD-R60R3-03）修的是「樹**內**子目錄漏掉」；本輪出的是同一類缺口的
# 另一個入口——**樹外**、但同樣決定那次 pytest 收集結果的 rootdir `conftest.py`。pytest
# 依 rootdir 隱式載入它，一句 `collect_ignore_glob` 就能改變計數，而它不在任何一棵 glob
# 的覆蓋面內。實測（沙箱，內容＝本輪工作樹）：在 `AISDLC_SDD_v0.30/conftest.py` 末尾加
# 一行 `collect_ignore_glob = [...]`，v0.30 實測計數確實改變，四格指紋卻**逐字不變**、
# `--check-snapshot` 照樣 ✅ rc=0 ⇒ 觸發器對這一軸全盲（SD-R67-02 的原始形態）。
#
# 對應關係取決於**該次 pytest 的 rootdir**（不是目錄包含關係）：
#   v001／v030 ← `cd vX && pytest tools/fsm_runtime/tests`（ci-gate.sh 的呼叫形態）
#                ⇒ rootdir=vX，載入 `vX/conftest.py`；共用層在 confcutdir 之上**不載入**
#   scripts    ← `cd AISDLC_SDD && pytest scripts/tests/` ⇒ 載入 `AISDLC_SDD/conftest.py`
#   autoclaude ← `cd AutoClaude && pytest` ⇒ 會載入 `AutoClaude/conftest.py`（現不存在）
#
# 檔案**不存在**時不貢獻任何 bytes（見 `tree_fingerprint`）：v0.01 依 ADR-XPLAT-001 不得
# 原地修改故無此檔、AutoClaude 目前也沒有——兩者今日指紋逐字不變，但**一旦被建立，指紋
# 立刻改變**。這正是要的語意：「該格是在哪一棵樹＋哪一份 conftest 上量的」。
_FINGERPRINT_ROOTDIR_CONFTESTS: tuple[tuple[str, str], ...] = (
    ("v001", "AISDLC_SDD/AISDLC_SDD_v0.01/conftest.py"),
    ("v030", "AISDLC_SDD/AISDLC_SDD_v0.30/conftest.py"),
    ("scripts", "AISDLC_SDD/conftest.py"),
    ("autoclaude", "AutoClaude/conftest.py"),
)


@dataclass(frozen=True)
class SlowSpec:
    """一個表② 的格：錨點 → 欄位 ＋ 該格的量測器鍵。"""

    anchor: str
    fields: tuple[Field, ...]
    measurer: str
    source: str


# 三格 ci-gate 共用同一個 Field（frozen dataclass，可安全共享）。
# 🔴 R67-D1：正則由 `\*\*(\d+)\*\*` 改為裸 `(\d+)`——粗體不再是「哪一欄」的判準（欄由
# `platform_cell_index()` 決定），`**` 只是排版；只替換數字本身即可原地保留粗體。
# 代價（明說）：該格內**只准出現一個數字**，`1729（R59 記載）` 這種把 provenance 塞進
# 格子的寫法會命中 2 次而 fail-loud ⇒ provenance 一律住 `snapshot-fingerprints-*` 錨。
_CIGATE_PASSED = Field("passed", re.compile(r"(\d+)"), "{v}")

_SLOW_SPECS: tuple[SlowSpec, ...] = (
    SlowSpec(
        anchor="autoclaude-pytest-snapshot:",
        fields=(
            # 🔴 R67-D1：正則**不再靠 `**` 粗體區分平台欄**（那正是「回填只寫得到
            # Windows 欄」的成因）。欄位由 `platform_cell_index()` 切格決定，正則只在
            # 那一格內作用 ⇒ 兩平台共用同一組式子，少一份會漂移的東西。
            # 仍用**零寬斷言只替換數字本身**：把 ` passed / N skipped` 納入 match 會讓
            # 第一次 sub 吃掉第二個欄位所需的上下文（本檔的斷言當場抓到過），且能原地
            # 保留該格既有的 `**` 粗體與其他排版。
            Field("passed", re.compile(r"(\d+)(?= passed)"), "{v}"),
            Field("skipped", re.compile(r"(\d+)(?= skipped)"), "{v}"),
        ),
        measurer="autoclaude_pytest",
        source="cd AutoClaude && python -m pytest tests/ -q（plain 形態）",
    ),
    SlowSpec(
        anchor="cigate-v001-snapshot:",
        fields=(_CIGATE_PASSED,),
        measurer="cigate_v001",
        source="bash AISDLC_SDD/scripts/ci-gate.sh 的『逐軌計數』自證行",
    ),
    SlowSpec(
        anchor="cigate-v030-snapshot:",
        fields=(_CIGATE_PASSED,),
        measurer="cigate_v030",
        source="bash AISDLC_SDD/scripts/ci-gate.sh 的『逐軌計數』自證行",
    ),
    SlowSpec(
        anchor="cigate-scripts-snapshot:",
        fields=(_CIGATE_PASSED,),
        measurer="cigate_scripts",
        source="bash AISDLC_SDD/scripts/ci-gate.sh 的『逐軌計數』自證行",
    ),
)


def _normalize_eol(raw: bytes) -> bytes:
    """行尾正規化：CRLF 與孤立 CR（老 Mac 行尾）一律折成 LF。純 bytes 層。

    🔴 WHY（DEF-101-613，R60 round 3）：**指紋要回答的問題是「測試樹的內容變了沒」，
    而行尾是 checkout 產物、不是內容。** 不正規化就等於讓**同一個 commit 在不同平台
    得到不同指紋**。

    這不是假想風險，是本機實查的活體狀態：`.gitattributes` 宣告 `* text=auto eol=lf`
    ⇒ 索引一律 LF，但 Windows 工作樹大量檔案是 CRLF（`git ls-files --eol <樹>` 數
    `i/lf w/crlf`：v0.01 樹 48／v0.30 樹 72／AutoClaude 樹 92）。原版直接 hash
    `read_bytes()` ⇒ 任何 fresh clone／CI runner／macOS 機器 checkout 出來都是 LF，
    四格指紋必然全部對不上，`--check-snapshot` **開箱即紅**。今日零後果純粹因為只有
    這一台 Windows 機器在跑——那是巧合，不是設計正確。

    刻意**在 bytes 層做、不 decode 成文字**：測試樹裡可能有非 UTF-8 或含 BOM 的檔，
    decode 會引進一整類與行尾無關的新失敗模式；而且 `str.splitlines()` 連 U+2028／
    U+0085 也當行尾，會把正規化範圍偷偷擴大到「內容差異」上，反而縮掉鑑別力。
    """
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def tree_fingerprint(rel_dir: str, pattern: str, extra_files: tuple[str, ...] = ()) -> str:
    """測試樹內容指紋：sha256(排序後的 相對路徑 + **行尾正規化後**的檔案 bytes)。

    `extra_files`（R67 round 2，SD-R67-02）＝**樹外**但同樣決定該次 pytest 收集結果的
    檔案，目前唯一用途是 rootdir `conftest.py`（見 `_FINGERPRINT_ROOTDIR_CONFTESTS`）。
    刻意用 **repo 相對路徑**當 digest 的鍵（樹內檔用的是樹相對路徑）：這些檔住在樹外，
    沒有「相對於樹根」這回事，硬換算只會產生一個看不懂的鍵。**不存在即不貢獻**（不是
    fail-loud）——v0.01 凍結版依 ADR-XPLAT-001 不得原地修改故無此檔，AutoClaude 目前
    也沒有；此時指紋逐字不變，而一旦有人建立該檔，指紋立刻改變（正是要的鑑別力）。

    刻意**不用 git**：`git rev-parse HEAD:<path>` 只看 HEAD，untracked／未 commit 的新測試
    檔不算進去 ⇒ 一輪內新增測試會漏觸發（本 repo 已有「worktree 隔離看不到未 commit 修改」
    這條踩過的教訓）。純檔案內容雜湊對 tracked／untracked 一視同仁。

    正規化的 WHY 見 `_normalize_eol`（DEF-101-613：不做就是平台相依指紋）。
    """
    root = _REPO_ROOT / rel_dir
    if not root.is_dir():
        raise BaselineToolError(
            f"指紋來源目錄不存在：{rel_dir}——目錄被搬動時必須同步 `_FINGERPRINT_TREES`，"
            f"故此處 fail-loud 而非靜默回傳空指紋"
        )
    digest = hashlib.sha256()
    for path in sorted(root.glob(pattern)):
        if not path.is_file():
            continue
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(_normalize_eol(path.read_bytes()))
        digest.update(b"\0")
    for rel_file in extra_files:
        extra = _REPO_ROOT / rel_file
        if not extra.is_file():
            continue
        digest.update(rel_file.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_normalize_eol(extra.read_bytes()))
        digest.update(b"\0")
    return digest.hexdigest()[:_FP_LEN]


def rootdir_conftests_for(name: str) -> tuple[str, ...]:
    """該指紋欄對應的 rootdir conftest（排序固定，讓 digest 與宣告順序無關）。"""
    return tuple(sorted(rel for tree, rel in _FINGERPRINT_ROOTDIR_CONFTESTS if tree == name))


def measure_fingerprints() -> dict[str, str]:
    return {
        name: tree_fingerprint(rel, pat, rootdir_conftests_for(name))
        for name, rel, pat in _FINGERPRINT_TREES
    }


def parse_fingerprints(text: str, platform_key: str) -> dict[str, str]:
    """從該平台的錨點行抽出文件記載的指紋；欄位缺席即 fail-loud。"""
    anchor = fingerprint_anchor(platform_key)
    line = anchored_line(text, anchor)
    values: dict[str, str] = {}
    missing: list[str] = []
    for name, _rel, _pat in _FINGERPRINT_TREES:
        found = re.findall(rf"{re.escape(name)}=([0-9a-zA-Z]+)", line)
        if len(found) != 1:
            missing.append(f"{name}（命中 {len(found)} 次，預期恰 1）")
        else:
            values[name] = found[0]
    if missing:
        raise AssertionError(
            f"`{anchor}` 行的指紋欄位抽取失敗：{missing}\n"
            f"  一鍵回填（只寫本機平台那一欄）："
            f"python tools/sync_onboarding_baselines.py --write --with-slow\n"
            f"  行文：{line.strip()[:240]}"
        )
    return values


def parse_provenance(text: str, platform_key: str) -> dict[str, str]:
    """從該平台的錨點行抽出 provenance（何時／哪台機器／docker／pgextras）。

    缺任一欄即 fail-loud：**provenance 是這張表能被信任的全部理由**，容許它缺席
    等於容許「這欄數字誰在什麼環境量的沒人知道」這種狀態靜默存在（R67-D1／F28）。
    """
    anchor = fingerprint_anchor(platform_key)
    line = anchored_line(text, anchor)
    values: dict[str, str] = {}
    missing: list[str] = []
    for key in _PROVENANCE_FIELDS:
        found = re.findall(rf"{re.escape(key)}=(\S+)", line)
        if len(found) != 1:
            missing.append(f"{key}（命中 {len(found)} 次，預期恰 1）")
        else:
            values[key] = found[0]
    if missing:
        raise AssertionError(
            f"`{anchor}` 行的 provenance 欄位抽取失敗：{missing}\n"
            f"  必備欄位：{list(_PROVENANCE_FIELDS)}——缺席即代表該欄數字的量測環境不可考，"
            f"下一位驗證者會把環境差異（docker 停用／venv 帶 PG extras）誤判為退化。\n"
            f"  行文：{line.strip()[:240]}"
        )
    return values


def column_has_measurements(text: str, platform_key: str) -> bool:
    """表② 該欄有無實測數字＝「有沒有量過」的唯一判準（WHY 見 `_BO` 檔頭）。"""
    lines = text.split("\n")
    for spec in _SLOW_SPECS:
        idx = _anchored_index(lines, spec.anchor)
        cell = _split_row(lines[idx])[platform_cell_index(lines, idx, platform_key)]
        if any(len(field.pattern.findall(cell)) != 1 for field in spec.fields):
            return False
    return True


def baseline_state(text: str, platform_key: str) -> str:
    """該平台欄的三態之一，並交叉驗證宣告與資料不得互相矛盾（判準與 WHY 見 `_BO`）。"""
    return _BO.validate_state(
        _PLATFORM_COLUMN_LABELS[platform_key],
        parse_provenance(text, platform_key),
        column_has_measurements(text, platform_key),
        f"  修法：改寫 `{fingerprint_anchor(platform_key)}` 錨的 {_ORIGIN_FIELD}=，"
        f"合法值 {list(_ORIGIN_VALUES)}；或讓表② 該欄的資料與宣告一致。",
    )


def baseline_status_line(text: str, platform_key: str) -> str:
    """該欄基線狀態的**單行**人話（三態措辭彼此不可混淆，見 `_BO.status_line`）。"""
    return _BO.status_line(
        _PLATFORM_COLUMN_LABELS[platform_key],
        parse_provenance(text, platform_key),
        baseline_state(text, platform_key),
    )


def _stale_messages(
    text: str, platform_key: str, names: list[str], live: dict[str, str],
) -> list[str]:
    documented = parse_fingerprints(text, platform_key)
    prov = parse_provenance(text, platform_key)
    label = _PLATFORM_COLUMN_LABELS[platform_key]
    return [
        f"[{label} 欄／{name}] 測試樹指紋 {documented[name]} → {live[name]}"
        f"（測試樹已變動）⇒ ONBOARDING.md §7 表② 該欄該格判定 **presumed stale**。\n"
        f"    該欄 provenance：{prov}\n"
        f"    這是因果判準：測試計數只可能因測試樹變動而變。"
        f"R60 round 1 填了 v0.30 的當時值、round 2 動了該測試樹使實測改變而沒人回填，"
        f"就是本觸發器要擋的形態（DEF-101-563；具體數字見帳本該列，此處刻意不寫死）。\n"
        f"    回填（只會寫本機平台那一欄）："
        f"python tools/sync_onboarding_baselines.py --write --with-slow"
        for name in names
    ]


_measurement_age_days = _BO.measurement_age_days


def _stale_summary(text: str, platform_key: str, names: list[str], live: dict[str, str]) -> str:
    """別平台欄的**單行**狀態列（不計入 rc，且**刻意不是警告**）。

    🔴 R67 round 2（QA-R67-05）——這一則為何從 ⚠️ 降級為 ℹ️：
    別平台欄的 stale 在**單機交替工作流**（R66 在 Windows、R67 在 macOS、下一輪再換回去）
    下是**結構性恆真**的：任一輪都會動到四棵樹之一，於是另一平台上一輪填的指紋必然對不上；
    即使那台機器剛回填過，本機一動樹它立刻又過期。也就是說，這是一則**在系統完全正常運作
    時也永遠亮著、且本機無論如何都清不掉**的訊號。而本 repo 已在
    `tools/run_root_unittests.py` 明文論證過這種常亮訊號的後果：「純 WARN 擋不住『11 輪
    沒人重釘』的心理機制（**常亮的警告＝背景噪音**）」——一旦讀者學會略過這個區塊，同一段
    輸出裡真正有牙的「**本機平台欄** presumed stale 並紅」也會被一起略過，那是這套機制唯一
    會咬人的部分。

    處置刻意**不是**「消音」：消音之後，真正該換平台補量測的那一天，沒有任何地方會告訴那個
    人「另一欄已經 N 天沒量了」。改為三件事——
      (a) 移出警告頻道（`main()` 改印 `ℹ️` 到 **stdout**，與 ✅ 同一列語氣），
      (b) 把「距上次量測幾天」這個**唯一隨時間變化、也唯一可行動**的量放進來取代四棵樹的
          指紋 diff（那串 diff 每輪都不一樣但資訊量為零：它只是在說「樹動過了」），
      (c) 訊息自己說明它在此工作流下是結構性常態、並把讀者的注意力指回本機平台欄。
    🔴 R70（DEF-101-756）措辭由**兩態改三態**：原版對「provenance 全 unrecorded」印
    「尚未建立基線」，而該句在 Windows 欄是假的（見 `_BO` 檔頭事故原文）。
    """
    documented = parse_fingerprints(text, platform_key)
    prov = parse_provenance(text, platform_key)
    state = baseline_state(text, platform_key)
    tail = (
        "——**不計入本機 rc**（本機修不動：回填必須在該平台上實跑）。"
        "真正有牙的是**本機平台欄**，見同段的 ✅／❌ 那一行"
    )
    head = baseline_status_line(text, platform_key)
    if state != _ORIGIN_SELF:
        return (
            f"{head}{tail}；補上 provenance 的唯一方式：在該平台執行 "
            f"`python tools/sync_onboarding_baselines.py --write --with-slow`"
        )
    age = _measurement_age_days(prov["measured-at"])
    age_text = (
        f"距今 {age} 天" if age is not None
        else f"measured-at={prov['measured-at']!r} 無法解析"
    )
    drift = ", ".join(f"{n}:{documented[n]}→{live[n]}" for n in names)
    label = _PLATFORM_COLUMN_LABELS[platform_key]
    return (
        f"{label} 欄上次量測 {prov['measured-at']}（{age_text}），此後 "
        f"{len(names)}/{len(_FINGERPRINT_TREES)} 棵樹已變動（{drift}）"
        f"——單機交替工作流下這是**結構性常態**、不是新問題{tail}"
    )


def snapshot_report(
    text: str, platform_key: str | None, live: dict[str, str] | None = None
) -> tuple[list[str], list[str]]:
    """表② 的 presumed-stale 判準，**逐平台欄**。回傳 (rc 級問題, 僅告知的提醒)。

    判準（R67-D6，檔頭 H）：
      - `platform_key` 有對應欄 → **只有該欄的 stale 算問題**；其他欄的 stale 只做
        ⚠️ 告知。WHY：別台機器的欄不是本機修得動的東西（回填要在那台機器上實跑），
        硬紅只會養成忽略紅燈的習慣——那比沒有鎖更糟（同 §7 表② 為何不接根層閘門）。
      - `platform_key` 為 None（Linux CI runner 等無欄平台）→ 判準**退化**為舊語意：
        「**沒有任何一欄是新鮮的**」才紅。誠實劃界：這**嚴格弱於**逐欄判準（只要有
        一欄新鮮就綠），但無欄平台本來就無從判斷「該看哪一欄」，寧可弱而不冤。

    `live` 可由呼叫端注入**同一份**已量指紋（R67 Scan-H 同型收斂）：同一次 CLI 呼叫裡
    重複量同一個量，會讓「判決所依據的指紋」與「印給人看／寫進 JSON 的指紋」變成兩次
    不同時點的量測 ⇒ 取證載具自己就可能與判決不一致。一次量、到處用。
    """
    if live is None:
        live = measure_fingerprints()
    stale: dict[str, list[str]] = {}
    for key in _PLATFORM_COLUMN_LABELS:
        # 每一欄都驗，不論本機是哪個平台：只驗本機那欄＝「另一欄寫著假話」結構上永遠
        # 測不到（R67-D6 修過的形態，不得在新判準上重蹈）。DEF-101-756
        baseline_state(text, key)
        documented = parse_fingerprints(text, key)
        stale[key] = [n for n, _r, _p in _FINGERPRINT_TREES if documented[n] != live[n]]
    if platform_key is not None:
        problems = _stale_messages(text, platform_key, stale[platform_key], live)
        notices = [
            _stale_summary(text, key, stale[key], live)
            for key in _PLATFORM_COLUMN_LABELS
            if key != platform_key and stale[key]
        ]
        return problems, notices

    every_column_stale = all(stale[key] for key in _PLATFORM_COLUMN_LABELS)
    messages = [
        m for key in _PLATFORM_COLUMN_LABELS for m in _stale_messages(text, key, stale[key], live)
    ]
    if every_column_stale:
        return messages, []
    return [], [
        f"（本平台在表② 無對應欄，判準退化為「全部欄皆 stale 才紅」）"
        f"{_stale_summary(text, key, stale[key], live)}"
        for key in _PLATFORM_COLUMN_LABELS
        if stale[key]
    ]


def check_snapshot(
    text: str, platform_key: str | None = _AUTO_PLATFORM, live: dict[str, str] | None = None
) -> list[str]:
    """`snapshot_report()` 的 rc 級問題那一半（保留舊呼叫端形狀）。"""
    problems, _notices = snapshot_report(text, resolve_platform(platform_key), live)
    return problems


def render_fingerprints(
    text: str, live: dict[str, str], platform_key: str, provenance: dict[str, str]
) -> str:
    """只改**該平台**那一條錨——別的平台欄由那台機器自己維護（R67-D1）。"""
    line = anchored_line(text, fingerprint_anchor(platform_key))
    new_line = line
    for name, _rel, _pat in _FINGERPRINT_TREES:
        new_line = re.sub(
            rf"{re.escape(name)}=[0-9a-zA-Z]+", f"{name}={live[name]}", new_line, count=1
        )
    for key in _PROVENANCE_FIELDS:
        new_line = re.sub(
            rf"{re.escape(key)}=\S+", f"{key}={provenance[key]}", new_line, count=1
        )
    return text.replace(line, new_line, 1)


def _docker_state() -> str:
    """docker daemon 狀態（provenance 用）。停用時 v0.01／v0.30 各 −3，見 §7 容差段。"""
    try:
        proc = subprocess.run(["docker", "info"], capture_output=True, timeout=60)
    except FileNotFoundError:
        return "absent"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    return "up" if proc.returncode == 0 else "down"


def pg_extras_state() -> str:
    """本直譯器有無 PG extras（provenance 用；`present` 會讓 AutoClaude 計數虛高）。

    刻意在**本行程內**探測而非另開子行程：`_run_autoclaude_pytest()` 用的就是
    `sys.executable`，兩者必須是同一個 venv 才叫同一件事。
    """
    present = [m for m in ("psycopg2", "sqlalchemy") if importlib.util.find_spec(m) is not None]
    return "present" if present else "absent"


def measure_provenance() -> dict[str, str]:
    """量測當下的 provenance（誰、何時、哪台機器、什麼環境）。值一律無空白 token。"""
    return {
        "measured-at": datetime.date.today().isoformat(),
        "host": f"{platform_mod.system()}-{platform_mod.release()}-{platform_mod.machine()}",
        "docker": _docker_state(),
        "pgextras": pg_extras_state(),
        # 實跑量測 ⇒ 必為 self-recorded；另兩態只可能由人依史料填（機器不替歷史作證）。
        _ORIGIN_FIELD: _ORIGIN_SELF,
    }


def _run_cigate() -> dict[str, int]:
    """實跑 ci-gate 並解析它自己的『逐軌計數』自證行（DEF-06-001 就是為取證而加的）。

    刻意解析那一行而非自己數 pytest 輸出：它是 ci-gate 的 SSOT，若格式改了要 fail-loud，
    不要在這裡另造一份計數邏輯（否則就是同一個量兩個算法＝本輪一直在治的病）。
    """
    # 🔴 **不得寫裸 `"bash"`**（R60 round 3 主控自己踩到，DEF-101-588）：本機 PATH 上
    # `bash` 解析到的是 **WSL 的 `C:\\Windows\\System32\\bash.exe`**，不是 Git Bash。
    # 用它跑 repo 的 `.sh` 會進 Linux 子系統，`python` 解析成 `/mnt/c/.../pyenv-win/shims/python`
    # ——那是一支 CRLF 的 Windows 批次腳本，於是報 `/bin/sh^M: bad interpreter`、rc=126。
    # 這與同輪 Pkg-P10 在 `Find-GitBash.ps1` 修掉的是**同一個缺陷**，而我在新寫的程式碼裡
    # 又犯了一次 ⇒ 一律走既有 SSOT `integration_gate_core.find_git_bash()`，不自寫第二份。
    import integration_gate_core  # noqa: PLC0415  # 延後 import：CLI 未用到時不付代價

    bash = integration_gate_core.find_git_bash()
    if not bash:
        raise BaselineToolError(
            "找不到 Git Bash（`integration_gate_core.find_git_bash()` 回 None）——"
            "這是**取值來源壞掉**，不是文件 stale。ci-gate.sh 必須以 Git Bash 執行；"
            "PATH 上的 `bash` 在本機可能是 WSL 佔位（System32），用它會進 Linux 子系統。"
        )
    proc = subprocess.run(
        [bash, "scripts/ci-gate.sh"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(_REPO_ROOT / "AISDLC_SDD"),
    )
    match = re.search(r"逐軌計數：(.+)", proc.stdout)
    if proc.returncode != 0 or not match:
        raise BaselineToolError(
            f"ci-gate.sh 未成功或找不到『逐軌計數：』自證行（rc={proc.returncode}）"
            f"——這是**取值來源壞掉**，不是文件 stale；請先修那件事。\n"
            f"stdout 尾段: {proc.stdout[-1200:]}\nstderr 尾段: {proc.stderr[-600:]}"
        )
    counts: dict[str, int] = {}
    for token in match.group(1).split():
        key, _, val = token.rpartition(":")
        if key and val.isdigit():
            counts[key] = int(val)
    wanted = {
        "cigate_v001": "AISDLC_SDD_v0.01",
        "cigate_v030": "AISDLC_SDD_v0.30",
        "cigate_scripts": "scripts/tests",
    }
    missing = [k for k in wanted.values() if k not in counts]
    if missing:
        raise BaselineToolError(
            f"『逐軌計數』行缺少軌道 {missing}（實得 {counts}）——ci-gate 的軌道組成變了，"
            f"請同步本檔的 `wanted` 對照表"
        )
    return {name: counts[track] for name, track in wanted.items()}


def _run_autoclaude_pytest() -> dict[str, int]:
    """plain 形態實跑 AutoClaude 全套（與 §7 表② 該格宣告的量測形態逐字一致）。

    ⚠️ 刻意**不加** `PYTHONDONTWRITEBYTECODE=1 -p no:cacheprovider`：加了會量到不同的數字
    （ARCH-R60-04 的整個爭點），而該格自陳「以 plain 形態量得」。形態與宣告必須同一件事。
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(_REPO_ROOT / "AutoClaude"),
    )
    match = re.search(r"(\d+) passed, (\d+) skipped", proc.stdout)
    if proc.returncode != 0 or not match:
        raise BaselineToolError(
            f"AutoClaude pytest 未全綠或找不到『N passed, M skipped』（rc={proc.returncode}）"
            f"——取值來源壞掉，不是文件 stale。\nstdout 尾段: {proc.stdout[-1200:]}"
        )
    return {"passed": int(match.group(1)), "skipped": int(match.group(2))}


def measure_slow() -> dict[str, dict[str, int]]:
    """跑一次 ci-gate ＋ 一次 AutoClaude pytest，餵滿全部 `_SLOW_SPECS`（分鐘級）。"""
    cigate = _run_cigate()
    pytest_counts = _run_autoclaude_pytest()
    by_measurer: dict[str, dict[str, int]] = {
        "autoclaude_pytest": pytest_counts,
        "cigate_v001": {"passed": cigate["cigate_v001"]},
        "cigate_v030": {"passed": cigate["cigate_v030"]},
        "cigate_scripts": {"passed": cigate["cigate_scripts"]},
    }
    return {spec.anchor: by_measurer[spec.measurer] for spec in _SLOW_SPECS}


def measure_slow_on_stable_tree() -> tuple[dict[str, dict[str, int]], dict[str, str]]:
    """慢量測 ＋ **前後各取一次指紋**把量測窗口夾住；窗口內樹變動即 fail-loud。

    回傳 `(四格計數, 這些計數所依據的那棵樹的指紋)`。

    🔴 WHY（DEF-101-677，R67 收尾 Scan-H）：原本的順序是「先 `measure_slow()`（分鐘級）、
    **跑完之後**才 `measure_fingerprints()`」。於是若測試樹在那段分鐘級窗口內被改動
    （並行的修復包還在寫測試檔／編輯器自動存檔／另一個 agent 同時作業），錨會記下
    **改動後**那棵樹的指紋，而四格計數留在**改動前**的樹上 ⇒ 事後 `--check-snapshot`
    量到的 live 指紋與錨相符、判 ✅ rc=0，**而計數其實已 stale**。

    這比「指紋沒動、計數已變」那類漏更嚴重，因為它是**回填路徑親手把觸發器拆掉**：
    樹確實變動了（那正是本觸發器唯一認得的事件），卻被寫進錨當成基準。錨的字面語意
    是「**該欄的數字是在哪一棵測試樹上量的**」（見 `_FINGERPRINT_ANCHOR_PREFIX` 區塊），
    而事後取指紋記下的是一棵**從未被量測過**的樹 ⇒ 語意與實作不是同一件事。
    （反向也會咬：若那筆改動事後被還原，錨反而與 live 對不上而**誤紅**。）

    修法**不是**放寬判準，而是讓回填路徑遵守它自己宣告的判準：既有契約已經是
    「指紋一變即判 presumed stale」，唯獨回填路徑替自己免除了這一條。夾住窗口之後，
    「量測期間樹變動」與「量測後樹變動」得到同一種處置——前者當場擋、後者下次
    `--check-snapshot` 擋。**嚴格度沒有提高**，只是不再有豁免。

    代價：正常單人作業零影響——多的那一次 `measure_fingerprints()` 是毫秒級
    （本機四棵樹實測約 25 ms，對比慢量測的分鐘級可忽略），且指紋相符時行為與原版
    逐字相同。只有「窗口內真的有人動了測試樹」才付代價，而那筆量測本來就是廢的。

    誠實劃界：夾住的是**淨變動**——在窗口內改動又在窗口結束前還原（例如量測中途
    暫存檔一寫一刪）仍偵測不到。要根治得對每一支子量測各自夾一次，那是更大的機制；
    本函式處理的是實際咬到人的形態（並行寫入後**留在樹上**）。
    """
    before = measure_fingerprints()
    slow = measure_slow()
    after = measure_fingerprints()
    drifted = [n for n, _r, _p in _FINGERPRINT_TREES if before[n] != after[n]]
    if drifted:
        raise BaselineToolError(
            "❌ 量測期間測試樹被改動 ⇒ 本次量測作廢，**未寫入任何檔案**。\n"
            f"  窗口內變動的樹：{', '.join(f'{n}: {before[n]} → {after[n]}' for n in drifted)}\n"
            "  為何不寫：四格計數是在**改動前**的樹上量的，而量完才取的指紋屬於**改動後**"
            "的樹。兩者一起寫進去，`--check-snapshot` 會量到相符的指紋而判 ✅ rc=0——"
            "那是一句『這些數字是新鮮的』的假保證，比沒有指紋更危險"
            "（`snapshot-fingerprints-*` 錨的語意是「**該欄的數字是在哪一棵樹上量的**」）。\n"
            "  怎麼辦：先讓測試樹靜下來（停掉並行的修復包／agent／編輯器自動存檔，"
            "`git status` 確認不再變動），**再重跑同一條指令**："
            "python tools/sync_onboarding_baselines.py --write --with-slow\n"
            "  若那筆改動是你自己刻意做的：這次的分鐘級量測就是廢的（跨了兩棵樹），"
            "重跑一次是唯一誠實的處置，不要為了省時間而回頭手改文件。"
        )
    # 刻意回傳 `before`（≡ `after`）：要記的是「**計數所依據的那棵樹**」，不是「量完之後
    # 剛好長怎樣的樹」。兩者在此已證明相等，選 `before` 是把意圖寫進程式碼。
    return slow, before


def _slow_cell_fields(cell: str, spec: SlowSpec, platform_key: str) -> list[tuple[Field, str]]:
    """在**單一格**內抽出每個受管欄位（恰一次命中，否則 fail-loud）。"""
    out: list[tuple[Field, str]] = []
    for field in spec.fields:
        found = field.pattern.findall(cell)
        if len(found) != 1:
            raise AssertionError(
                f"表② 受管欄位 {spec.anchor}/{field.name} 在 "
                f"{_PLATFORM_COLUMN_LABELS[platform_key]} 欄命中 {len(found)} 次（預期恰 1）"
                f"——0 次＝該格被改成抽不到的形態；≥2 次＝格內混進了第二個數字"
                f"（例如把 `（R59 記載）` 這類 provenance 塞進格子；provenance 一律住 "
                f"`{fingerprint_anchor(platform_key)}` 錨）。\n  格文：{cell.strip()[:200]}"
            )
        out.append((field, found[0]))
    return out


def render_slow(text: str, measured: dict[str, dict[str, int]], platform_key: str) -> str:
    """把表② 四格**該平台那一欄**的數字就地換成實測值（其餘欄逐字不動）。

    🔴 R67-D1 的核心：欄位由 `platform_cell_index()` 從表頭推導、`sub` 只在那一格的
    字串上作用 ⇒ **寫到別的平台欄在結構上不可能發生**（原版靠 `**` 粗體錨定，在 macOS
    上跑同一條回填指令會把 macOS 數字寫進標示「Windows 11 實測」的格子）。
    """
    lines = text.split("\n")
    for spec in _SLOW_SPECS:
        values = measured[spec.anchor]
        idx = _anchored_index(lines, spec.anchor)
        col = platform_cell_index(lines, idx, platform_key)
        cells = _split_row(lines[idx])
        cell = cells[col]
        for field, _found in _slow_cell_fields(cell, spec, platform_key):
            cell = field.pattern.sub(
                field.template.format(v=values[field.name]), cell, count=1
            )
        cells[col] = cell
        lines[idx] = "|".join(cells)
    return "\n".join(lines)


def slow_documented(text: str, platform_key: str) -> dict[str, dict[str, int]]:
    """讀出表② 四格**該平台那一欄**的文件字面值。"""
    lines = text.split("\n")
    out: dict[str, dict[str, int]] = {}
    for spec in _SLOW_SPECS:
        idx = _anchored_index(lines, spec.anchor)
        cell = _split_row(lines[idx])[platform_cell_index(lines, idx, platform_key)]
        out[spec.anchor] = {
            field.name: int(raw) for field, raw in _slow_cell_fields(cell, spec, platform_key)
        }
    return out


# ─────────────────────────── 稽核 / CLI ───────────────────────────


def check(text: str, measured: dict[str, dict[str, int]]) -> list[str]:
    """回傳不符項訊息清單（空清單＝新鮮）。純函式，供測試以合成文本驅動。"""
    problems: list[str] = []
    for spec in _SPECS:
        line = anchored_line(text, spec.anchor)
        documented = parse_documented(line, spec)
        live = measured[spec.anchor]
        problems.extend(f"[{spec.anchor}] {p}" for p in prose_problems(line, spec, live))
        problems.extend(
            f"[{spec.anchor}] {p}" for p in historical_problems(line, spec, live)
        )
        if documented != live:
            note = ""
            if live.get("violations", 0) > 0:
                note = (
                    "\n  ⚠️ 實測 violations>0 ⇒ **這是 LOC 閘門自己紅、不是文件 stale**，"
                    "請先修 LOC 預算，不要為了讓本鎖轉綠而把破線值填進文件"
                )
            problems.append(
                f"[{spec.anchor}] 文件 {documented} ≠ 實測 {live}（來源：{spec.source}）"
                f"{note}\n  一鍵回填：python tools/sync_onboarding_baselines.py --write"
            )
    return problems


def _write_onboarding(new_text: str) -> int:
    """bytes 層 LF 寫入 ＋ 落地後零 CR 斷言（共用，避免兩條寫入路徑各寫一份）。

    🔴 .gitattributes 宣告 `*.md text eol=lf`，而 Path.write_text() 在 Windows 會把 \\n
    譯成 CRLF（DEF-101-528 的原始形態，本輪已被咬過一次）。
    """
    _ONBOARDING.write_bytes(new_text.encode("utf-8"))
    if b"\r" in _ONBOARDING.read_bytes():
        print("❌ 落地後偵測到 CR，行尾被寫壞", file=sys.stderr)
        return 1
    return 0


# 模式旗標（互斥；一個都沒給時預設 `--check`）。集中成一張表而非散在 `if` 裡：
# 「文件引用的旗標是否真的存在」由 `tools/tests/test_doc_loc_baseline_freshness_r60.py`
# 直接對 parser 反查（R67-D20 的另一半——文件不得引用不存在的旗標）。
_MODE_FLAGS: tuple[str, ...] = ("--check", "--write", "--check-snapshot", "--json")


def build_parser() -> argparse.ArgumentParser:
    """CLI 定義（R67-D20）。

    🔴 `allow_abbrev=False`：argparse 預設接受**唯一前綴縮寫**，於是 `--check-snapsho`
    這種打錯字會被「好心地」解讀成 `--check-snapshot`。本檔的整個修法主張是「拼錯就要
    當場知道」，容許縮寫等於保留一條「看起來對、其實靠運氣」的路，與主張自相矛盾。
    關掉之後：未知旗標 / 打錯字 / 縮寫一律 rc=2，`--help` 印完整用法。
    """
    parser = argparse.ArgumentParser(
        prog="python tools/sync_onboarding_baselines.py",
        description=(
            "ONBOARDING.md §7 基線格產生器 ＋ 新鮮度稽核（表① live 格／表② dated snapshot）"
        ),
        allow_abbrev=False,
    )
    parser.add_argument(
        "--check", action="store_true",
        help="稽核表① live 格（不給任何模式旗標時的預設）；stale 即 rc=1",
    )
    parser.add_argument("--write", action="store_true", help="回填表① live 格（bytes 層 LF 寫入）")
    parser.add_argument(
        "--with-slow", action="store_true",
        help="與 --write 併用：另回填表②「本機平台那一欄」＋該平台指紋/provenance（分鐘級實跑）",
    )
    parser.add_argument(
        "--check-snapshot", action="store_true",
        help="表② presumed-stale 觸發器（毫秒級；pre-push 與 root-infra-ci 消費的就是這條）",
    )
    parser.add_argument("--json", action="store_true",
                        help="機讀報表（含表② 與逐平台指紋/provenance）")
    parser.add_argument(
        "--platform", choices=sorted(_PLATFORM_COLUMN_LABELS),
        help="唯讀模式下指定稽核哪一個平台欄（預設＝本機平台）；**不得**與 --write 併用",
    )
    parser.add_argument(
        "--allow-pg-extras", action="store_true",
        help="允許在可 import psycopg2/sqlalchemy 的 venv 上回填表②（該環境會使 AutoClaude "
             "passed 虛高；預設拒絕，provenance 會記 pgextras=present）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    except SystemExit as exc:  # argparse：未知旗標 rc=2、`--help` rc=0
        return int(exc.code or 0)

    selected = [name for name in _MODE_FLAGS if getattr(args, name[2:].replace("-", "_"))]
    if len(selected) > 1:
        print(f"❌ 模式旗標互斥，實得 {selected}——請一次只給一個", file=sys.stderr)
        return 2
    mode = selected[0] if selected else "--check"

    if args.with_slow and mode != "--write":
        print("❌ --with-slow 只在 --write 下有意義（它是回填模式）", file=sys.stderr)
        return 2
    if args.platform and mode == "--write":
        print(
            "❌ --platform 不得與 --write 併用：回填一律只寫**本機平台**那一欄。"
            "跨平台代填等於替另一台機器捏造 provenance，那正是 R67-D1 本體",
            file=sys.stderr,
        )
        return 2

    text = _ONBOARDING.read_text(encoding="utf-8-sig")
    audit_platform = resolve_platform(args.platform or _AUTO_PLATFORM)

    # `--check-snapshot`：只算指紋（毫秒級），不碰 live 格的量測器。pre-push 消費的就是這條。
    if mode == "--check-snapshot":
        # 一次量、判決與取證共用同一份（R67 Scan-H 同型收斂：原版判決後又重量一次，
        # 印出來的「證據」與判決所依據的可能不是同一時點的樹）。
        live = measure_fingerprints()
        problems, notices = snapshot_report(text, audit_platform, live)
        # 🔴 R67 round 2（QA-R67-05）：別平台欄的提醒改印 `ℹ️` 到 **stdout**，不再是
        # stderr 的 `⚠️`。理由見 `_stale_summary` 的 docstring——它在單機交替工作流下
        # **結構上恆亮**，掛在警告頻道只會訓練讀者略過這一段，連帶略過同段真正會紅的
        # 本機平台欄（本 repo「常亮的警告＝背景噪音」既定紀律，tools/run_root_unittests.py）。
        for n in notices:
            print(f"ℹ️ {n}")
        rc = 1 if problems else 0
        if problems:
            print("❌ ONBOARDING.md §7 表② presumed stale：", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
        scope = (
            f"{_PLATFORM_COLUMN_LABELS[audit_platform]} 欄"
            if audit_platform
            else f"（本平台 sys.platform={sys.platform} 無對應欄，退化判準：全欄皆 stale 才紅）"
        )
        # 🔴 判決行與逐欄明細在 ✅／🔴 **兩條路都印**（rc 語意不變）：原版 stale 時當場
        # return 1，整段平台覆蓋資訊被一個無關漂移吃掉。WHY 見 `_BO.snapshot_verdict`。
        print(_BO.snapshot_verdict(rc == 0, scope, live))
        for key in _PLATFORM_COLUMN_LABELS:
            documented = slow_documented(text, key)
            # 🔴 狀態人話排在原始 dict **之前**：原版只印 provenance，讀者看到四個
            # `unrecorded` 就自行補完成「這平台沒被驗過」，而下三行印的正是該平台實機
            # 量得的數字。先給結論、再給欄位，讓誤讀不靠讀者自律。DEF-101-756
            print(f"   [{_PLATFORM_COLUMN_LABELS[key]} 欄] {baseline_status_line(text, key)}")
            print(f"     provenance={parse_provenance(text, key)}")
            for ev in _BO.daily_evidence(_REPO_ROOT, key):
                print(f"     {ev}")
            for spec in _SLOW_SPECS:
                print(f"     [{spec.anchor}] {documented[spec.anchor]}")
        print(
            "   ℹ️ 🔴 **本工具不是平台覆蓋的權威**：它只知道「表② 這一欄的數字在什麼環境量的」。"
            f"「哪一輪在哪個平台跑過真機」請查 {_COVERAGE_SOURCES}（DEF-101-756）"
        )
        return rc

    measured = measure_all()

    if mode == "--write" and args.with_slow:
        write_platform = current_platform_key()
        if write_platform is None:
            print(
                f"❌ 本平台（sys.platform={sys.platform}）在 §7 表② 沒有對應欄 ⇒ 拒絕回填。\n"
                f"   受管平台欄：{sorted(_PLATFORM_COLUMN_LABELS)}。"
                f"**不猜一欄來寫**——猜錯就是把本平台數字寫進別平台的格子（R67-D1）；"
                f"要納管新平台請在 `_PLATFORM_COLUMN_LABELS` 加一筆並為 §7 表② 增一欄。",
                file=sys.stderr,
            )
            return 2
        pg_state = pg_extras_state()
        if pg_state == "present" and not args.allow_pg_extras:
            print(
                "❌ 本直譯器可 import psycopg2／sqlalchemy ⇒ AutoClaude 的 PG-gated 測試會由"
                " skip 轉 pass、passed 數虛高，與 §7 表② 宣告的出廠環境不是同一件事。\n"
                "   處置：改用只裝 `.[dev,notifications]` 的乾淨 venv 執行本指令；"
                "確實要以此環境入帳請加 --allow-pg-extras（provenance 會記 pgextras=present）。",
                file=sys.stderr,
            )
            return 2
        print("⏳ 實跑 ci-gate ＋ AutoClaude pytest（分鐘級）…", file=sys.stderr)
        # 指紋**夾住**慢量測窗口（R67 Scan-H）：窗口內樹變動即 fail-loud、一個字都不寫。
        slow, measured_fp = measure_slow_on_stable_tree()
        provenance = measure_provenance()
        new_text = render_fingerprints(
            render_slow(render(text, measured), slow, write_platform),
            measured_fp,
            write_platform,
            provenance,
        )
        rc = _write_onboarding(new_text)
        if rc:
            return rc
        for spec in _SPECS:
            print(f"✅ 已回填 [{spec.anchor}] → {measured[spec.anchor]}")
        label = _PLATFORM_COLUMN_LABELS[write_platform]
        for spec in _SLOW_SPECS:
            print(f"✅ 已回填 [{spec.anchor}]（{label} 欄）→ {slow[spec.anchor]}"
                  f"（來源：{spec.source}）")
        print(f"✅ 已回填 [{fingerprint_anchor(write_platform)}] → {measured_fp} ＋ {provenance}")
        return 0

    if mode == "--json":
        # 同上：每個量只算一次，報表印的與 rc 依據的必定是同一份（原版 live 指紋量 3 次、
        # `check()` 算 2 次 ⇒ JSON 可能印 `snapshot_problems: []` 卻回 rc=1）。
        live_fp = measure_fingerprints()
        problems = check(text, measured)
        snapshot_problems = check_snapshot(text, audit_platform, live_fp)
        print(
            json.dumps(
                {
                    "measured": measured,
                    "documented": {
                        s.anchor: parse_documented(anchored_line(text, s.anchor), s)
                        for s in _SPECS
                    },
                    "problems": problems,
                    "audit_platform": audit_platform,
                    "snapshot_documented": {
                        key: slow_documented(text, key) for key in _PLATFORM_COLUMN_LABELS
                    },
                    "snapshot_fingerprints_documented": {
                        key: parse_fingerprints(text, key) for key in _PLATFORM_COLUMN_LABELS
                    },
                    "snapshot_provenance": {
                        key: parse_provenance(text, key) for key in _PLATFORM_COLUMN_LABELS
                    },
                    "snapshot_fingerprints_live": live_fp,
                    "snapshot_problems": snapshot_problems,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 1 if problems or snapshot_problems else 0

    if mode == "--write":
        new_text = render(text, measured)
        if new_text == text:
            print("✅ ONBOARDING.md §7 live 基線格已是最新，未變更")
            return 0
        rc = _write_onboarding(new_text)
        if rc:
            return rc
        for spec in _SPECS:
            print(f"✅ 已回填 [{spec.anchor}] → {measured[spec.anchor]}")
        return 0

    problems = check(text, measured)
    if problems:
        print("❌ ONBOARDING.md §7 live 基線格 stale：", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    for spec in _SPECS:
        print(f"✅ [{spec.anchor}] {measured[spec.anchor]}（來源：{spec.source}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
