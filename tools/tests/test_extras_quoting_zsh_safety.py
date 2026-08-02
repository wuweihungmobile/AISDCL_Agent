"""機械鎖：pip/uv 安裝指令的 extras 與 target 必須加引號（macOS zsh glob 安全）.

# 缺陷（R57 Scan-A2 = DEF-101-479；R59 擴面 = DEF-101-507／508）

macOS 自 Catalina 起預設登入 shell 為 **zsh**，且 `nomatch` 預設開啟。zsh 對未加引號的
`.[dev,notifications]` 執行 filename generation（glob）；repo 內沒有「`.` + 單一字元」的
匹配檔名，zsh 遂 **在執行指令之前就中止整條命令列**：

    $ zsh -c 'echo REACHED .[dev,notifications]'
    zsh:1: no matches found: .[dev,notifications]      rc=1     ← echo 從未執行
    $ zsh -c "echo REACHED '.[dev,notifications]'"
    REACHED .[dev,notifications]                        rc=0
    $ bash -c 'echo REACHED .[dev,notifications]'
    REACHED .[dev,notifications]                        ← bash 無此行為

實害：macOS 開發者照文件複製貼上 `uv pip install -e .[dev,notifications]`，看到的是  <!-- zsh-glob-ok: 本檔即此鎖的實作，docstring 必須原樣引述壞形態才能說明缺陷本身 -->
一個與套件完全無關的 `no matches found` —— uv/pip 根本沒被呼叫到。同一行在 bash 與
PowerShell 下都正常，故 **Windows 開發者永遠不會遇到**，是單邊平台缺陷。

R57 動工時全 repo 活文件共 16 處未加引號（`AutoClaude/README.md` 9、
`docs/AISDLC_Agent_UserGuide.md` 4、另三份各 1），全部已修。

**R59 擴面的兩個新形態**（DEF-101-507／508）：R57 只修了裸 `.[extras]`，但同一個 zsh
`nomatch` 語意對 **具名套件** 完全一樣——`autoclaude[postgres]` 是合法 glob（literal
`autoclaude` + 一個取自 `{p,o,s,t,g,r,e}` 的字元），無匹配檔名時同樣整條中止。R59 動工時
掃描面內這種形態有 40 行（另 1 行在 `README_Prompt_v0.1_history.md` 歷史快照，依逐字保全
政策不改），其中十幾處是 **執行期 raise/print 給使用者的唯一修復指引**
（`factory.py` 4 處、各 `Pg*` adapter/repository 的 ImportError、`alembic/env.py`、
`migrate_file_to_pg.py`）——使用者已經卡在缺依賴，照唯一提示做又拿到第二個看不懂的錯。
另一形態是 `tools/bootstrap_core.py` 安裝失敗訊息把 **f-string 插值的絕對路徑 target**
裸著印出（DEF-101-508）。

# 為何需要這道鎖

修完只是解決當下；本 repo 反覆的教訓是「人工修完的東西沒有機械鎖就會回流」。
extras 語法在文件裡是高頻複製貼上的樣板，未來任一次新增安裝說明都可能寫回未加引號
形態，而 `check_pytest_baseline_sites.py` 等既有守門完全不看這個面向。

**R59 的教訓更直接**：這道鎖 R57 版的 docstring 曾以「repo 內無此寫法」為理由明文排除
具名套件形態——該前提當下即為假（40 行），且 R57 自己在 `ONBOARDING.md` 寫的
`pip install -e 'AutoClaude[dev,notifications,lint]'` 已經加了引號，可見它認得這個風險，
卻在鎖裡宣稱不存在。**未實測的「repo 內沒有」不可以拿來當縮減掃描面的理由**，這正是
`docs/06_quality/CrossPlatform_Scan_Dimensions.md` 判準 (4) 要治的病。

# 掃描面與邊界（三段式，依 CrossPlatform_Scan_Dimensions.md 判準 (4)）

掃描 **git tracked 的 `*.md` + `*.sh` + `*.py` + `*.toml` + `*.yaml` + `*.yml`
＋三處 git-hooks 無副檔名檔**（清單見 `_SCAN_PATHSPECS`／`_HOOK_DIRS`）。R59 加入
`*.toml`/`*.yaml`/`*.yml` 的理由：`AutoClaude/pyproject.toml`（6 處）與
`AutoClaude/config.yaml`（1 處）連掃描面都進不去，而 `pyproject.toml` 的 extras 註解
正是「使用者要裝選配時最先讀的一行」。排除 `_EXCLUDED_SUBSTRINGS` 所列的歷史紀錄檔
（缺陷帳本與其 archive、sprint_history、improving 系列、`README_Prompt_v0.1_history`）
——那些是時代快照，逐字保全優先於修正，比照 `check_pytest_baseline_sites.py` 政策。

## 已實測涵蓋（下列每項都在 R59 落地當下以本檔正則實跑驗證，並由常駐斷言守住）

- 裸 `.[extras]`：`uv pip install -e .[dev]`（DEF-101-479 原形態）  <!-- zsh-glob-ok: 邊界三段式必須逐項列出被涵蓋的壞形態，否則「已實測涵蓋」無從查證 -->
- 具名套件 `<pkg>[extras]`：`pip install autoclaude[postgres]`（DEF-101-507）  <!-- zsh-glob-ok: 同上，具名形態的病例樣本 -->
- 路徑前綴：`pip install -e /abs/AutoClaude/.[dev]`（POSIX `/` 與 Windows `\\` 皆試）  <!-- zsh-glob-ok: 同上，DEF-101-508 的字面形態樣本 -->
- 未加引號的插值 target：`pip install -e {autoclaude_target}` / `${TARGET}`——這才是  <!-- zsh-glob-ok: 同上，DEF-101-508 在原始碼裡的真實形態樣本 -->
  DEF-101-508 在原始碼裡的**真實**長相（f-string 插值，靜態掃描看不到方括號本身），
  故另立此分支；否則本鎖對它所要守的那個站點恰恰零覆蓋。
- GNU 長旗標夾在中間（`--upgrade -e`）仍命中（R57 round 1 SD 訂正過的既有分支）。
- `python -m pip install <pkg>[extras]`——**R59 撰寫本節時原本把它列進「不涵蓋」，實跑
  當場證偽**：本正則的錨是 `re.search` 的子字串比對而非行首錨定，`python -m pip install …`
  裡的 `pip install …` 一樣命中。這一條留在此處當作判準 (4) 的活教材：連寫鎖的人對自己
  正則的邊界直覺都會錯，所以三段式的每一項都必須真的跑過才准寫。
- 已加 **單引號** 與 **雙引號** 的正確形態皆不誤報（`.github/workflows/*.yml` 內 14 處
  `pip install -e ".[dev]"` 在 R59 加入 `*.yml` 後全數不觸發，實跑確認）；
  `pip install -e .`（無 extras）、`pip install -r requirements.txt`、
  `pip install foo   # 見 [附註]`（同行後方另有方括號）三種亦實測不誤報。

## 已實測不涵蓋（下列每項都實跑確認會漏，明文承認）

- 旗標帶 `=` 的長形式：`pip install --index-url=https://x pkg[extra]`——旗標段以
  `[ \t]+` 收尾，遇 `=` 即失配，整條漏報。
- 反斜線續行的跨行寫法（target 落在次行）：本鎖逐行掃描，不做行接續還原。
- 非 `pip` / `uv pip` 字面的安裝器：`pip3 install`（`pip` 後緊接 `3`，前綴的 `[ \t]+`
  失配）、`uv add`、`poetry add`。R59 實跑確認 repo 內目前無這些形態，但**不代表本鎖
  擋得住**——真出現時會漏。
- `.ps1` 刻意不納入（PowerShell 無此 glob 語意，納入只製造偽陽性）。
  🔴 **R70 訂正**：本行原本還寫著「未 tracked 的新檔在 `git add` 前掃不到（`git ls-files`
  固有性質，與 `test_platform_utils_dedup.py` 同政策）」——R69 證明那不是可接受的取捨而是
  真 fail-open（`DEF-101-752`：untracked 的 `platform_caps.py` 讓一個真實違規躲過四輪四方
  複審）。掃描面已改為 **tracked ∪ untracked-not-ignored**（見 `_scan_targets()`），
  該項已不再是本鎖的邊界；`.gitignore` 內的檔案（venv／快取）仍在掃描面外。
- 本鎖**不驗證 shell 實際行為**（那需要 zsh，CI 的 ubuntu runner 未必有）；它是純文字
  形態鎖。行為面的證據記在本 docstring 頂部與缺陷帳本 DEF-101-479／507／508。

## 未窮舉

以上兩份清單**均非窮舉**。本檔刻意不做「唯一殘餘風險是 X」這類宣稱——R57 有兩輪的
修復就是栽在這種絕對詞上（一次「與引號界定全部無關」被推翻、一次「唯一殘餘風險是非
cmdlet 途徑」被 `get-childitem` 當場推翻），而 R57 版本檔自己的「repo 內無此寫法」
同樣是未實測的絕對詞、同樣被推翻。新形態出現時本鎖會漏，這是邊界不是保證。

# 豁免機制（`zsh-glob-ok:`）

雷區對照表這類**刻意引述壞形態**的行（ONBOARDING §5 就必須寫出壞形態才說得清症狀；
本檔的邊界三段式亦必須逐項列出病例樣本）無法避免命中，故提供行內豁免：在該行加上
`# zsh-glob-ok: <理由>`（Python/bash/yaml）或 `<!-- zsh-glob-ok: <理由> -->`（markdown）。
比照 `check_pytest_baseline_sites.py` 的 `baseline-ok:` 既有慣例——**豁免必須附理由，
且被 `test_exemptions_are_audited` 稽核**（理由非空、且總數不得超過 `_MAX_EXEMPTIONS`），
避免「豁免變成靜默放行的後門」。
"""

import re
import subprocess
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

# `pip install` / `uv pip install` + 任意（不含 `=` 的）旗標。以 `[ \t]` 而非 `\s` 收尾，
# 是為了保證正則不會跨行匹配——`\s` 含 `\n`，一行以 `pip install` 結尾時會把下一行的
# 內容誤接上來。
_INSTALL_PREFIX = r"(?:uv[ \t]+)?pip[ \t]+install[ \t]+(?:--?[A-Za-z][A-Za-z-]*[ \t]+)*"

# 未加引號的 install target。四個分支，各對應一個實測過的缺陷形態（見 docstring
# §已實測涵蓋）。三種殼（bash/zsh/PowerShell）都把 `'` 當引號字元，故正確形態一律
# 用單引號；雙引號在 zsh 下同樣抑制 glob，故本正則對兩者都不誤報（起始位置是引號時，
# 四個分支的第一個字元需求皆失配）。
#
# R57 round 1 SD 複審訂正沿革（皆經實測，見 DEF-101-479）：
# (a) 旗標段原為 `(?:-[A-Za-z]+\s+)*`，**只吃單槓短旗標**——`pip install --upgrade -e .[dev]`  # zsh-glob-ok: 正則沿革說明必須引述被漏報的壞形態
#     這種帶 GNU 長旗標的寫法整條漏報（實測 old=False / new=True）。改為 `--?[A-Za-z][A-Za-z-]*`。
# (b) 原有的前方 lookbehind `(?<!["'])` 是**死碼**：加引號版長成 `install -e '.[dev]'`，該位置
#     的字元是 `'` 而 `\.\[` 本身就要求是 `.`，正則在此必然失配，lookbehind 沒有額外作用。
#     實測 6 組樣本在「有 lookbehind／無 lookbehind」下結果完全相同，故移除並訂正註解。
#
# R59 新增三件（DEF-101-507／508）：
# (c) 裸 `.[` 分支前置一個 **選配的路徑前綴** `(?:[^\s'"]*[/\\])?`——R57 版的錨要求 `.[`
#     緊接在旗標之後，故下列這種寫法整條漏報。POSIX `/` 與 Windows `\` 兩種分隔符都吃
#     （`bootstrap_core.py` 用 `os.sep` 組路徑，兩者都會出現）：
#         pip install -e /abs/path/.[dev]  # zsh-glob-ok: 正則沿革要說明「原本漏報什麼」就必須引述該壞形態
# (d) **具名套件**分支 `[A-Za-z_][A-Za-z0-9_.-]*\[…\]`：DEF-101-507 的本體。名稱字元類
#     刻意不含空白，故 `pip install foo   # 見 [附註]` 這種「同行後方另有方括號」不誤報。
# (e) **插值 target**分支 `\$?\{[^}!]*\}`（R59 SD-R59-04 起排除 `!`，見下）：DEF-101-508 在原始碼裡的真實長相如下，方括號
#     在字面上根本不存在，(a)~(d) 全都看不到它。無論插值進來的是什麼，你都無法保證它
#     不含 glob 元字元或空白，故「印給使用者複製貼上的插值 target 一律要加引號」是這裡
#     唯一站得住的規則：
#         _err(f"…pip install -e {autoclaude_target}")  # zsh-glob-ok: DEF-101-508 的真實形態病例樣本
_UNQUOTED_EXTRAS_RE = re.compile(
    _INSTALL_PREFIX
    + r"(?:"
    + r"(?:[^\s'\"]*[/\\])?\.\[[^\]]+\]"  # (a)+(c) 裸 / 路徑前綴 `.[extras]`
    + r"|[A-Za-z_][A-Za-z0-9_.-]*\[[^\]]+\]"  # (d) 具名套件 `pkg[extras]`
    # R59 SD-R59-04：字元類排除 `!`，避免誤傷 `{target!r}`——`!r` 本身就會產出引號，
    # 是 Python 裡「把插值路徑加引號」的**正統做法**，判它違規會讓做對事的人被翻紅，
    # 而豁免預算本就吃緊（見 _MAX_EXTERNAL_EXEMPTIONS 分帳說明）。
    + r"|\$?\{[^}!]*\}"  # (e) 未加引號的插值 target（排除 !r/!a 轉換）
    + r")"
)

# 正確形態計數用（見 test_quoted_form_still_present）：分裸/路徑形態與具名形態兩支，
# 各自釘下限——只釘一支的話，另一支被整段刪除時仍會綠。
_QUOTED_DOT_RE = re.compile(_INSTALL_PREFIX + r"'(?:[^\s'\"]*[/\\])?\.\[")
_QUOTED_NAMED_RE = re.compile(_INSTALL_PREFIX + r"'[A-Za-z_][A-Za-z0-9_.-]*\[")

# 歷史紀錄檔：逐字保全優先，不納管（與 check_pytest_baseline_sites.py 同政策）。
# R59 新增 `README_Prompt_v0.1_history`：`AutoClaude/docs/internal/` 下的 v0.1 prompt
# 時代快照，含一處具名 extras，屬同類歷史檔（原清單四項不含它，加入具名分支後才浮現）。
_EXCLUDED_SUBSTRINGS = (
    "AutoSDD_Defect_Log",
    "sprint_history",
    "improving",
    "/archive/",
    "README_Prompt_v0.1_history",
)

# R57 round 1 Architect／QA 交叉指出（DEF-101-479）：原掃描面只有 tracked `*.md`，
# 完全看不到**執行期真的印給使用者複製貼上**的訊息——`AutoClaude/tools/git-hooks/pre-push`
# 與 `AutoClaude/tools/local_ci_gate.py` 當時各有一處壞形態，這道鎖卻全綠。那比文件更要命：
# 那是 push 被擋當下的唯一指引，mac 使用者照做 → `zsh: no matches found` → 再 push 再被擋，
# 形成迴圈。故掃描面擴為「tracked *.md + *.sh + *.py + 三處 git-hooks 無副檔名檔」。
# R59（DEF-101-507）再加 `*.toml`/`*.yaml`/`*.yml`：`AutoClaude/pyproject.toml` 的 extras
# 註解（6 處）與 `AutoClaude/config.yaml`（1 處）原本連掃描面都進不去，而 pyproject 的
# 註解正是「要裝選配時最先讀到的一行」；`.github/workflows/*.yml` 已全用雙引號，加入
# 後實跑確認零誤報。`.ps1` 仍刻意不納入：PowerShell 無此 glob 語意，納入只會製造偽陽性。
# R59 SD-R59-06：加入 `*.yaml` 後掃描面由 ~3,000 暴增到 24,140 份（單模組 20.3s，
# 且是每次 pre-push／根層 unittest 都要付的延遲），暴增主因是 AISDLC_SDD 30 個凍結版
# 的 governance/R-*.yaml 與 docs_template。凍結版依 Copy-on-Evolve 政策不回改，
# 掃它們對本鎖零收益，故以 pathspec 排除；LATEST 版仍在掃描面內。
_SCAN_PATHSPECS = (
    "*.md", "*.sh", "*.py", "*.toml", "*.yaml", "*.yml",
    ":(exclude)AISDLC_SDD/AISDLC_SDD_v0.0*/**/*.yaml",
    ":(exclude)AISDLC_SDD/AISDLC_SDD_v0.1*/**/*.yaml",
    ":(exclude)AISDLC_SDD/AISDLC_SDD_v0.2*/**/*.yaml",
)
_HOOK_DIRS = ("tools/git-hooks", "AutoClaude/tools/git-hooks", "AISDLC_SDD/.githooks")

# 掃描面下限：防「glob/排除清單被改壞導致掃 0 份檔案卻靜默綠燈」的 fail-open。
# R59 擴面後實測 tracked 檔（扣除排除項）為 24,140 份。原下限 500 是 R57 對「3000+ 份」
# 取的保守值，但那讓「掃描面崩掉 98% 仍全綠」成為可能；既然本輪動了 pathspec，順手把
# 下限提到 3000（仍遠低於實測值，AISDLC_SDD 未來歸檔版本目錄也不會誤觸）。
_MIN_SCANNED = 3000

# 已加引號的正確形態下限：本鎖若只斷言「沒有未加引號」，把全部 extras 指令從文件裡
# 刪光也會綠。釘正確形態的數量下限，讓「修復被整段刪除」也有訊號。
# R57 修復後裸/路徑形態實測 30 處，R59 擴面後為 35；具名形態 R59 修復後實測 42 處。
# 42 的分解（二審 QA-R59-P3-2 訂正：初稿寫「41 處本輪新加引號 + ONBOARDING 1 處」，
# 41 這個數字對不上帳本 DEF-101-507 記的 40 處，差額是本鎖 docstring 自帶的正確樣本）：
#   40 處＝本輪 DEF-101-507 實際新加引號的站點（與帳本一致）
# +  1 處＝`ONBOARDING.md` 那處 R57 自己就寫對的 `'AutoClaude[dev,…]'`
# +  1 處＝本鎖 docstring 內自帶的正確形態樣本（掃描面含本檔，故自己也被計入）
# 兩者各取約 6 成的保守下限。
_MIN_QUOTED_DOT = 20
_MIN_QUOTED_NAMED = 25

# 行內豁免標記（見 docstring §豁免機制）。刻意引述壞形態的行專用。
# 語言中立：`# zsh-glob-ok: 理由`（Python/bash/yaml）與 `<!-- zsh-glob-ok: 理由 -->`
# （markdown）皆可，理由取到行尾或 `-->` 之前。
_EXEMPT_RE = re.compile(r"zsh-glob-ok:\s*(?P<why>.*?)\s*(?:-->\s*)?$")

# 豁免總數上限：豁免是給「必須引述壞例子」這類少數情境用的，不是給人繞過的後門。
# 超過此數＝豁免正在被濫用，fail-loud 要求人重新檢視（同 check_script_parity 對
# `_SINGLE_SIDED_EXEMPT` 的 stale 反向檢查精神）。
# R59 實測 9 行：`ONBOARDING.md` §5 雷區表 1 行 + 本檔 docstring／註解的病例樣本 8 行
# （本檔是這道鎖的實作，且判準 (4) 的三段式**要求**逐項列出被涵蓋/不涵蓋的壞形態，
# 內含壞形態是本質需求；整檔排除才是 fail-open，故仍走逐行豁免）。上限自 R57 的 5
# 調到 10 即為此擴面所需，非放寬紀律。**R59 二審再訂正**：單一總上限本身就是缺陷來源
# ——它把「本鎖的規格文件有多長」與「有沒有人濫用豁免」混在同一個計數器裡，撞頂訊息
# 會把成因指錯人，最省力的反應就是再調高數字。現行權威已改為下方兩本分帳，
# `_MAX_EXEMPTIONS` 為其衍生值（sanity net）。

# ── R59 ARCH-R59-02：豁免預算必須分兩本帳 ─────────────────────────────────────
# 問題（Architect 一審實測）：`_MAX_EXEMPTIONS` 的設計意圖是偵測「豁免被當成繞過後門」，
# 但實測 9 筆已用豁免裡有 8 筆**在本鎖檔自己內部**——因為判準 (4) 的三段式邊界宣稱
# **要求**逐項列出被涵蓋／不涵蓋的壞形態，而列出壞形態就得引述壞形態、就得申請豁免。
# 於是這個計數器現在量的主要是「本鎖的規格文件有多長」，不是「有沒有人濫用豁免」。
# 後果可預測：下一輪只要新增一種形態、依判準補一行病例樣本就撞頂，而撞頂訊息會說
# 「疑似被當成繞過手段」——**把成因指錯人**，最省力的反應就是再調高上限（R57→R59 已
# 調過一次 5→10）。這正是姊妹檔 test_windowsapps_guard_cross_consistency.py 的腐化
# 路徑起點：機制被自己的文件需求推著鬆綁。
#
# 修法：拆兩本帳。本鎖檔自身的病例樣本走寬上限**並加下限**（樣本被整段刪掉＝三段式
# 宣稱失去查證性，同樣要紅）；本鎖檔**之外**的豁免走嚴格上限——那才是原本想守的訊號。
_SELF_FILE = "tools/tests/test_extras_quoting_zsh_safety.py"
# 本檔自身病例樣本：上限寬（規格文件會隨形態增加而變長），但下限防「樣本被刪光」。
_MAX_SELF_SAMPLES = 20
_MIN_SELF_SAMPLES = 6
# 本檔之外的豁免：這是真正該嚴管的一本帳（R59 實測僅 ONBOARDING.md §5 雷區表 1 行）。
_MAX_EXTERNAL_EXEMPTIONS = 3

# R59 二審 ARCH-R59-02-C1 訂正：本常數原為寫死的 10，於是「自身樣本寬上限 20」在結構上
# **不可達**——總帳先綁死，實際自身天花板是 `10 − external`（實測 7），headroom 只剩 1，
# 我要修的失效模式原封不動還在（下輪補 2 行病例樣本就翻紅，訊息仍把成因指錯人）。
# 改為**衍生值**：分帳成為權威，總帳降格為 sanity net（仍保留 fail-loud 網，不刪測試）。
_MAX_EXEMPTIONS = _MAX_SELF_SAMPLES + _MAX_EXTERNAL_EXEMPTIONS


def _scan_targets() -> list[Path]:
    """掃描面＝**tracked ∪ untracked-not-ignored**（R70／`DEF-101-752`）。

    🔴 本函式原名 `_tracked_scan_targets`、只跑 `git ls-files`，而本檔 docstring
    「已實測不涵蓋」節逐字寫著「未 tracked 的新檔在 `git add` 前掃不到（`git ls-files`
    固有性質，**與 `test_platform_utils_dedup.py` 同政策**）」——R69 證明那個政策是
    真 fail-open：`AutoClaude/autoclaude/utils/platform_caps.py` 全程 untracked，
    使它與 dedup 鎖的衝突躲過四輪四方複審與多次全套實跑，直到 `git add -A` 才顯形。
    該檔已於 R70 改為聯集掃描面，本檔同步（否則「同政策」這句話會指向一個已經不存在
    的政策，讀者仍會以為盲區是刻意取捨）。`-o --exclude-standard` 尊重 `.gitignore`，
    `_EXCLUDED_SUBSTRINGS` 過濾與 `_MIN_SCANNED` 下限皆不受影響。
    """
    paths = []
    seen: set[str] = set()
    for extra in ((), ("-o", "--exclude-standard")):
        out = subprocess.run(
            ["git", "-c", "core.quotepath=false", "ls-files", *extra, "-z",
             *_SCAN_PATHSPECS, *_HOOK_DIRS],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        ).stdout
        for rel in out.split("\0"):
            if not rel or rel in seen:
                continue
            if any(sub in rel for sub in _EXCLUDED_SUBSTRINGS):
                continue
            seen.add(rel)
            paths.append(_REPO_ROOT / rel)
    return paths


class TestExtrasQuotingZshSafety(unittest.TestCase):
    def setUp(self) -> None:
        self.files = _scan_targets()

    def test_scan_surface_not_silently_shrunk(self) -> None:
        """掃描面下限：排除清單或 glob 被改壞時 fail-loud，而非掃 0 份仍綠。"""
        self.assertGreaterEqual(
            len(self.files),
            _MIN_SCANNED,
            f"掃描面只剩 {len(self.files)} 份 < 下限 {_MIN_SCANNED}"
            "——排除清單或 git ls-files pathspec 疑似被改壞（fail-open 風險）",
        )

    def _scan(self) -> tuple[list[str], list[tuple[str, str]]]:
        """回傳 (未豁免的違規行, [(位置, 豁免理由)])。"""
        offenders: list[str] = []
        exemptions: list[tuple[str, str]] = []
        for path in self.files:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rel = path.relative_to(_REPO_ROOT).as_posix()
            for lineno, line in enumerate(text.splitlines(), 1):
                if not _UNQUOTED_EXTRAS_RE.search(line):
                    continue
                exempt = _EXEMPT_RE.search(line)
                if exempt:
                    exemptions.append((f"{rel}:{lineno}", exempt.group("why")))
                else:
                    offenders.append(f"{rel}:{lineno}: {line.strip()[:110]}")
        return offenders, exemptions

    def test_exemptions_are_audited(self) -> None:
        """豁免必須附非空理由、且總數受限——防豁免退化為靜默放行的後門。"""
        _, exemptions = self._scan()
        self.assertLessEqual(
            len(exemptions),
            _MAX_EXEMPTIONS,
            f"zsh-glob-ok 豁免已達 {len(exemptions)} 行 > 總上限 {_MAX_EXEMPTIONS}，"
            f"疑似被當成繞過手段：{exemptions}",
        )
        for where, why in exemptions:
            self.assertTrue(
                why.strip(),
                f"{where} 的 zsh-glob-ok 豁免未附理由——豁免必須說明為何該行必須引述壞形態",
            )

    def test_exemption_budget_is_split_self_vs_external(self) -> None:
        """R59 ARCH-R59-02：分兩本帳，讓「濫用豁免」的訊號不被本鎖自己的規格文件淹掉。

        - 本檔自身病例樣本：上限寬（判準 (4) 要求逐項列出壞形態，樣本必然隨形態增加），
          但**加下限**——樣本被整段刪光時三段式宣稱失去查證性，同樣是退化，必須紅。
        - 本檔之外的豁免：嚴格上限。這才是原本 `_MAX_EXEMPTIONS` 想守的訊號。
        """
        _, exemptions = self._scan()
        self_n = sum(1 for where, _ in exemptions if where.startswith(_SELF_FILE))
        external = [where for where, _ in exemptions if not where.startswith(_SELF_FILE)]
        self.assertGreaterEqual(
            self_n, _MIN_SELF_SAMPLES,
            f"本檔病例樣本只剩 {self_n} 行 < 下限 {_MIN_SELF_SAMPLES}——三段式邊界宣稱"
            f"若沒有對應的樣本行，「已實測涵蓋/不涵蓋」就無從查證（fail-open）",
        )
        self.assertLessEqual(
            self_n, _MAX_SELF_SAMPLES,
            f"本檔病例樣本已達 {self_n} 行 > 上限 {_MAX_SELF_SAMPLES}——請檢查是否有樣本"
            f"其實不是三段式宣稱所必需",
        )
        self.assertLessEqual(
            len(external), _MAX_EXTERNAL_EXEMPTIONS,
            f"**本檔之外**的 zsh-glob-ok 豁免已達 {len(external)} 行 > 上限 "
            f"{_MAX_EXTERNAL_EXEMPTIONS}，這才是「豁免被當成繞過手段」的真訊號"
            f"（不要靠調高總上限解決）：{external}",
        )

    def test_no_unquoted_extras_in_live_docs(self) -> None:
        offenders, _ = self._scan()
        self.assertEqual(
            offenders,
            [],
            "以下站點的 pip/uv install target 未加引號，macOS zsh 下會 `no matches found`、"
            "指令根本不會執行（DEF-101-479／507／508）。修法：一律用單引號包住整個 target，"
            "`install -e '.[dev,notifications]'`／`install 'autoclaude[postgres]'`／"
            "`install -e '{target}'`\n" + "\n".join(offenders),
        )

    def test_quoted_form_still_present(self) -> None:
        """防「把 extras 指令整段刪掉」這種也能讓上一支測試變綠的退化。

        兩支形態各自釘下限：只釘裸/路徑形態的話，R59 修好的 **40** 處（二審 QA 訂正，原寫 41）具名形態被整段刪除
        時本鎖仍全綠——那正是 DEF-101-507 的回流路徑。
        """
        dot = named = 0
        for path in self.files:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            dot += len(_QUOTED_DOT_RE.findall(text))
            named += len(_QUOTED_NAMED_RE.findall(text))
        self.assertGreaterEqual(
            dot,
            _MIN_QUOTED_DOT,
            f"全 repo 只剩 {dot} 處加引號的裸/路徑 extras 指令 < 下限 {_MIN_QUOTED_DOT}"
            "——安裝說明疑似被整段刪除；本鎖的『無未加引號』因而變成空洞的真",
        )
        self.assertGreaterEqual(
            named,
            _MIN_QUOTED_NAMED,
            f"全 repo 只剩 {named} 處加引號的具名套件 extras 指令 < 下限 {_MIN_QUOTED_NAMED}"
            "——DEF-101-507 的修復疑似被整段刪除或回退",
        )


if __name__ == "__main__":
    unittest.main()
