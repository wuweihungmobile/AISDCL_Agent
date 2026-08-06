#!/usr/bin/env python3
"""NTFS 敵意檔名 CI 閘 — tools/git-hooks/pre-commit「NTFS 敵意檔名防護閘（A3）」的 CI 對等。

為何需要：A3 閘只活在本機 pre-commit，`git commit --no-verify`、GitHub web 編輯、
未裝 hooks 的 clone 都可繞過；敵意檔名一旦入庫，所有 Windows(NTFS) checkout 直接
炸掉（無法建檔）或靜默大小寫碰撞覆蓋。本腳本供 root-infra-ci 在雲端複核。

範圍差異（by design）：hook 版只掃「本次 commit 新增（A/C）」路徑；本 CI 版掃
`git ls-files` **全量 tracked 路徑**——已入庫的違規也要現形。

檢查邏輯與 hook 版一致（tools/git-hooks/pre-commit `_ntfs_seg_bad` + 大小寫碰撞 + 長度閘）：
  1. 路徑含控制字元（C locale [:cntrl:]＝0x00-0x1F + 0x7F），或任一路徑段含
     Windows 不允許字元 < > : " | ? * \\，或以空白/句點結尾（NTFS 不允許）
  2. 任一段去（第一個點起的）副檔名、再剝除尾隨空白後（不分大小寫）為 Windows 保留裝置名
     CON / PRN / AUX / NUL / COM0~9 / LPT0~9 / CONIN$ / CONOUT$
     （R60 訂正：本行原稱「COM0/LPT0 非 Microsoft 官方保留名，但比照
     sindresorhus/filename-reserved-regex 等業界防禦性實作採保守納入」——實測 git
     for Windows 對兩者的裁決並不相同：`git -c core.protectNTFS=true update-index
     --add --cacheinfo` 對 `LPT0` 回 `error: Invalid path`、對 `COM0` 則 ACCEPT。
     即 LPT0 是**必須**擋（否則 Windows checkout 整棵樹開不出來），只有 COM0 才是
     純保守納入。CONIN$／CONOUT$ 見 `_RESERVED_RE` 上方註解）
  3. 大小寫碰撞：兩 tracked 路徑正規化鍵（NFC → lowercase）相同但原字串不同
     （NTFS 大小寫不敏感 → checkout 時互相覆蓋）
  4. MAX_PATH 保守長度閘（DEF-101-039）：Windows 未開 core.longpaths 時絕對路徑上限
     MAX_PATH=260 UTF-16 單位（含結尾 NUL，可用 259）→ repo 相對路徑 >200 字元 fail、
     >180 字元 warn（不影響退出碼）。長度＝Unicode code point 數（len()；BMP 字元＝
     1 UTF-16 單位；hook 版以「刪 UTF-8 連續位元組計數」達成同語意且 locale 無關；
     astral 字元低估 1 單位屬可忽略邊角）。
     🔴 **R76-01：這道門檻隱含一個從未寫下的假設，現改以算式表達並每次執行都印出來。**
     兩個面各自的關係式（根前綴＝checkout 根**含結尾分隔符**的長度）：
         檔案面   根前綴 ≤ 259 − 最長 tracked 相對路徑
         目錄面   根前綴 ≤ 247 − 最深 tracked 相對目錄（CreateDirectoryW 上限 248 含 NUL）
     fail 門檻 200 只保證「根前綴 ≤ 259 − 200」這一種 checkout；那個減出來的數字就是
     本檔此前寫死在散文裡的「預留 clone 前綴」，它**不是** repo 現況能撐的長度。現況
     兩個面的實際值一律由 `_clone_prefix_budget_lines()` 現算現印，本 docstring 不寫死
     任何當下的數字（寫下即開始過期——同 ONBOARDING §7 表①「受管值不得寫進散文」）。
     🔴 **本閘測不到、也擋不住的那一半**：它量的是 **repo 相對長度**，對「checkout 根
     前綴有多長」結構上失明。R76-01 實測：Windows 上 `git clone` 到 168 字元的目錄、
     未帶 `-c core.longpaths=true` ⇒ rc=128 且 27,523 支 tracked 檔只落地 301 支
     （半套 checkout，連 `tools/bootstrap.ps1` 都不在磁碟上）。而該旗標查下來只存在於
     **已 clone 成功**的那個 repo 的 `--local` config（`--system`／`--global` 皆 rc=1）
     ⇒ fresh clone 零保護。開箱指引見 ONBOARDING.md §2 第 0 步。
  5. 目錄段層級碰撞（R67-A2）：把每條 tracked 路徑的**每一層目錄前綴**收集後以同一組
     正規化鍵分群，同鍵而拼法不同即違規。第 3 項只比「整條路徑」，對「目錄段拼法不同、
     basename 完全不重複」結構上失明——本 repo 曾因此長出 `docs/04_planning/Archive/`
     與 `docs/04_planning/archive/` 兩個 index 目錄（f81ad94 收 01–31 用大寫、22782fe
     收 32–50 改小寫），在 macOS/Windows 上塌縮成一個目錄、`git status` 全綠，整整 6 週
     零訊號；同一 commit 在 Linux CI／github.com 上卻是兩個目錄（真・case-sensitive
     APFS 卷實測坐實）。危害不是立即覆蓋（basename 不重疊時不會），而是**同一份程式碼
     在兩平台掃到不同的檔案集合**，以及交叉引用在 Linux/github.com 變死連結（R67-A15）。
  6. Unicode 正規化（R67-B16）：index 路徑必須是 NFC。macOS(APFS/HFS+) 對檔名做 NFD、
     Windows(NTFS) 用 NFC，git 以 core.precomposeunicode 在 macOS readdir 端轉回 NFC；
     一旦 index 內存的是 NFD 位元組（只能由非 macOS/非 Windows 端提交或 plumbing 產生
     ——mac 側 `git add` 無論走 argv 或目錄走訪都會 precompose，實測見下），macOS clone
     後該檔即永久呈現「index 一份 NFD、工作樹一份 NFC 未追蹤」的雙重身影：`git status`
     恆不乾淨，且 `git clean -fd` 清掉 phantom 會直接變成 tracked 檔遺失（兩種不乾淨狀態
     互斥，無常規手段回到乾淨）。第 3/5 項的分群鍵亦先做 NFC 再 lowercase，使「僅正規化
     形式不同」與「僅大小寫不同」歸為同一類碰撞（macOS 與 NTFS 兩側皆會互相覆蓋）。

範圍決策（R67-B16，刻意不對稱，勿「補齊對稱性」）：第 6 項**只在本 CI 版實作，不鏡射
進 hook 版**。理由是實測而非省事——pre-commit 只看「本機開發者這次新增的路徑」，而本 repo
的兩個開發平台都不可能在該路徑上產生 NFD index 項：macOS 端 `git add` 走 argv 有
precompose_argv、走目錄走訪有 readdir precompose（實測：磁碟 NFD 檔名 `63616665cc812e6d64`
經 `git add .` 後 index 記為 NFC `636166c3a92e6d64`），Windows/NTFS 本身即 NFC。NFD 只能
由 Linux 貢獻者／GitHub web／plumbing 進來，那三條路**都不經過 pre-commit**，鏡射進 hook
純屬零收益的死碼；而它們全都會被本 CI 版的全量 tracked 掃描網住。此決策由
`tools/tests/test_ntfs_trailing_space_device_name.py::TestNfcAxisScopeIsCiOnlyByDesign`
機械釘住。第 5 項（目錄段碰撞）則**有**鏡射進 hook（bash 3.2 相容實作），因為那條路徑
開發者在 mac/Win 上按 tab 補全就會踩到。

已知侷限：大小寫折疊用 str.lower()（Unicode 全覆蓋）。🔴 R76-10 訂正：本段原稱
「hook 的 grep -iFx 在 UTF-8 locale 亦 fold 非 ASCII 字母，方向一致」——hook 側自
R76-10 起已改為 `tr '[:upper:]' '[:lower:]'` ＋不帶 `-i` 的 `grep -Fx`（`-i`＋`-F`
在無 UTF-8 locale 時 SIGABRT，而 `|| true` 把崩潰吞成「沒有碰撞」）。`tr` **只折
ASCII** ⇒ 兩側折疊面自此**刻意不對稱**：非 ASCII 字母的大小寫碰撞由本 CI 版的全量
tracked 掃描獨力兜底。這不是退化——原本那條「hook 也折得到非 ASCII」的路，成立條件
正好就是會讓 grep 崩潰的那個 locale。檔名內嵌換行/控制字元非缺口：git 對含控制字元
路徑恆 C-quote（不受 core.quotepath=false 影響），hook 逐行讀所見之引號化表徵
含 " 與 \\ 觸發第 1 項攔截；本腳本 -z 讀原始路徑由控制字元檢查攔截——兩側皆
封閉（第五輪 SD/QA 雙實證）。`_tracked_files()` 對 `git ls-files` 輸出以
`errors="replace"` 解碼：tracked 路徑若真含非法 UTF-8 位元組序列，違規清單印出的
檔名會混入 U+FFFD 替代字元、人類辨識度打折，但偵測本身不受影響（違規仍會被列出、
exit 1 仍正確觸發，R25 複審確認）。

使用：
  python3 tools/check_ntfs_paths.py   # 於 repo 內任意 cwd；違規印明細並 exit 1
"""
from __future__ import annotations

import re
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌/⚠) 防崩潰保護

_REPO_ROOT = Path(__file__).resolve().parents[1]

_FORBIDDEN_CHARS = set('<>:"|?*\\')
# R60（DEF-101-B-refuter-1）：補上 `CONIN$`／`CONOUT$`。納入的**證據來源**是 git for
# Windows 的 `core.protectNTFS`（Windows 預設 true），因為真正炸掉的環節不是 Win32 建檔
# 而是 git 簽出——但它只是證據來源，**不是本判準要對齊的模型**（本檔下方 R77-51 段落以
# 外接 oracle 逐名對拍過，兩者在四個樣本上判決相反）。
# 本機實測（Win 11 Pro 26200 / Git Bash 5.2.37，拋棄式 repo、不碰本 repo）：
#   git -c core.protectNTFS=true update-index --add --cacheinfo …
#     REJECT: CONIN$.log / CONOUT$.txt / CONIN$ / conin$.log / CONIN$.tar.gz /
#             CONIN$ .log / CONOUT$   .txt（大小寫、多重副檔名、尾隨空白皆不影響）
#     ACCEPT: CLOCK$.txt / CLOCK$ .txt（故**刻意不納入** CLOCK$，見下方 benign 樣本）
#             CONIN.log / CONIN（少了 `$` 就不是裝置名，故正則要求完整 token）
#   實害：以 protectNTFS=false 把 'CONIN$.log' 提交後，用預設設定 clone →
#         `error: invalid path 'CONIN$.log'` + `fatal: unable to checkout working tree`、
#         rc=128、工作樹**全空**（連無關的 plain.txt 也沒有）。與 R57 已修的
#         「保留名 + 尾隨空白」（DEF-101-478）破壞同級：不是單檔失敗，是整個 clone 不可用。
#   繞過管道＝本檔檔頭已列的三條（--no-verify／GitHub web／未裝 hooks），加上
#   `core.protectNTFS` 在非 Windows 平台預設不啟用 → mac/Linux 側可入庫。
#
# **前導空白刻意不處理**（R60，四處實作統一決策）：「保留名 + **前導**空白」（' CON.txt'／
# '  COM1.log'／' NUL .log'／' CON .txt'）看似 R57 尾隨空白形態的鏡像，實測**不是**缺口：
#   · git（protectNTFS=true）對上述全部形態 ACCEPT——git 只在路徑段**起頭**比對保留名，
#     前導空白使比對失配；含前導形態的 repo clone 實測 rc=0、工作樹有檔、
#     `git status --porcelain` 空、內容讀回正確 payload。
#   · Win32 只吞**尾隨**空白/句點，不吞前導：本機實測 ' CON.txt'／' CON'／'CON.txt'／
#     ' CON .txt' 四者可同時共存於同一目錄（os.listdir 全部列出、各 10 bytes 可讀回）。
#   故在本檔（validator）加擋前導空白＝**純新增偽陽性**（擋下 git 與 Windows 都接受的
#   檔名），零實害可擋。此決策由 tools/tests/test_windows_forbidden_filename_parity.py
#   的 `LEADING_SPACE_RESERVED_SEGMENTS` 樣本電池機械釘住（validator 側必須放行），
#   下輪掃描者若再把它當鏡像缺口回報，請先讀該樣本清單與本段實測。
#
# 🔴 交替分支順序有意義，勿「整理」：四個基本裝置名（CON、PRN、AUX、NUL）必須**相鄰**，
# 新裝置名一律加在清單**尾端**。
# `tools/tests/test_windows_forbidden_filename_parity.py::_RESERVED_LIST_ANCHOR` 這道
# repo-wide 前瞻掃描鎖（抓「新增第 5 份獨立重寫」）要求四者依序出現且間隙 ≤5 字元。
# R60 初版把 CONIN／CONOUT 兩支插在 CON 與 PRN 之間，實測使本檔、pre-commit、logger.py
# 三處**同時**掉出錨①（間隙 17 字元），只靠錨②（禁用字元集合）苟活——註冊表等值斷言
# 照樣全綠，degradation 完全無訊號。改置於清單尾端後三處回歸命中。
# 對正則語意零影響（`^(...)$` 完全錨定，交替順序不改變匹配集合）。
#
# R68（四處同修）：追加 Microsoft《Naming Files, Paths, and Namespaces》保留名清單明列的
# 上標變體 `COM¹ COM² COM³ LPT¹ LPT² LPT³`（該文件與 ASCII 數字版並列；本機實測
# `unicodedata.normalize("NFKC","COM¹") == "COM1"` 佐證兩者在相容性分解下同值）。
# 🔴 **證據等級＝官方文件＋靜態分析，非 Windows 真機實測**——本輪無 Windows 真機，未跑
# `core.protectNTFS` update-index／clone 對照（CONIN$ 納入、CLOCK$ 排除當初都是實測後才定）。
# 取捨刻意選「擋」：本檔是 validator，誤擋的代價是一個沒人會用的檔名進不了庫（可用
# --no-verify 或改名繞過）；漏擋的代價是每一台 Windows clone 的 checkout 整體失敗。
#
# 🔴 R77-51 訂正（Windows 11 Pro 26200 真機，當回合實測）——上一段末尾原本留下一條
# 「將來真機測到兩個 oracle 都接受就四處移除」的指示，那個條件**已經成立**，而它導出的
# 動作已被明文推翻，故該指示就地改寫為以下裁決，不得再照舊執行：
#   ① `git -c core.protectNTFS=true update-index --add --cacheinfo` 逐名對拍本檔
#      `_ntfs_seg_bad()`，四個樣本判決相反——`COM0.txt`／`COM¹.txt`／`COM²`／`LPT³.log`
#      git ACCEPT 而本判準 BLOCK。對照 `LPT0.txt` git REJECT：git 側 COM0 與 LPT0 並不
#      對稱，本判準擋下 LPT0 與 git 同結論**純屬巧合**，不是因為本判準在模擬 git。
#   ② Win32 `open()`：上列四者連同 `CON.txt`／`PRN`／`NUL.log`／`COM1.txt`／`CONIN$.log`
#      全部落地為**真檔案**（size 正確、`os.listdir` 命中），無一拋 OSError。會拋 OSError
#      的是禁用字元那一組（八個字元逐一實測，errno 22／2）——兩件事不可混為一談。
#   ⇒ 本判準與 protectNTFS 是**刻意的嚴格超集**關係，不是對齊關係。掌舵者本輪裁決：
#      過攔保留（過攔是安全方向），只修失實的宣稱；四處一律**不得**因「git 也接受」放寬。
#      這層超集關係現在有外接 oracle 在守，不再只靠四處互相對照（四處一起錯時，等值鎖
#      結構上恆綠）：`tools/tests/test_windows_forbidden_filename_parity.py`
#      的 `TestReservedNameVsGitOracle`——刻意分歧須逐筆具名，且**分歧消失也會紅**。
_RESERVED_RE = re.compile(
    r"^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9]|CONIN\$|CONOUT\$|COM[¹²³]|LPT[¹²³])$"
)

# MAX_PATH 保守長度閘（DEF-101-039）：
# 可用 259（260 含 NUL）− clone 前綴預留 ＝ 200 fail；180 warn
# （預留值不再寫死在此，由 `_clone_prefix_budget_lines()` 以 `_MAX_PATH_USABLE - _LEN_FAIL`
#  算出並印出——R76-01：那個數字是門檻的**衍生物**，寫死一份就是第二個會漂移的真相）
# 🔴 R68 三站點長度政策（本處是第 3 站，治理 tracked git **整條相對路徑**）：另兩站是
# `AISDLC_SDD/scripts/component_sanitizer.py::_MAX_COMPONENT_LEN=80`（FSM state 檔名的
# **單一 component**，為前後綴留餘裕）與 `AutoClaude/autoclaude/utils/logger.py`（runtime
# log 檔名，**刻意無上限**，超長交 OSError fallback）。三者治理不同域、刻意不相等，不是
# 「同一政策的三份真相」——下一輪掃描者請勿再把它當四處不一致重新回報。已知未覆蓋的
# 跨平台窄帶：單一 component ~200–254 字元在 mac/Linux 合法、Windows 未開 longPaths 時
# 總路徑可能破 260（≥255 是兩平台共同 ENAMETOOLONG，非跨平台落差；本輪 APFS 實測
# 200/250 OK、255/256/300 FAIL errno 63）。該窄帶須先有 Windows 真機實證再設鎖，否則
# 等於再加一道從未紅過的鎖。對照鎖：AISDLC_SDD/scripts/tests/test_ntfs_length_gate.py
# ::test_length_policy_three_sites_registry。
_LEN_FAIL = 200
_LEN_WARN = 180


def _length_level(path: str) -> str | None:
    """路徑長度分級：>200 → "fail"、>180 → "warn"、其餘 → None（單位＝code point）。"""
    n = len(path)
    if n > _LEN_FAIL:
        return "fail"
    if n > _LEN_WARN:
        return "warn"
    return None


def _ntfs_seg_bad(path: str) -> str | None:
    """路徑有 NTFS 相容性問題 → 回傳原因字串；乾淨 → None（對齊 hook 版同名函式）。"""
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in path):
        return "含控制字元"
    for seg in path.split("/"):
        bad = _FORBIDDEN_CHARS.intersection(seg)
        if bad:
            return f'路徑段「{seg}」含 Windows 不允許字元（< > : " | ? * \\）'
        if seg.endswith((" ", ".")):
            return f"路徑段「{seg}」以空白或句點結尾（NTFS 不允許）"
        # R57 修正（DEF-101-B1）：base 需先剝除尾隨空白再比對保留名。原本
        # `seg.split(".", 1)[0]` 對 `CON .txt` 得到 `"CON "`，`^(CON|...)$` 不匹配
        # 而放行；L77 的「整段以空白/句點結尾」也不成立（結尾是 t）→ 完全逃逸。
        # Win32 解析裝置名時會忽略基底名後的尾隨空白，故此形態在 Windows 上仍會
        # 撞到裝置名。剝除後 `" .txt"` 這類純空白 base 退化為空字串，
        # `^(CON|...)$` 不匹配空字串，不會誤判。（僅剝空白：base 已在第一個點處
        # 切斷故不含句點；tab 等其他空白屬控制字元，已由 L71 攔下。）
        base = seg.split(".", 1)[0].rstrip(" ")  # 去（第一個點起的）副檔名；CON.txt 一樣是保留名
        if _RESERVED_RE.match(base.upper()):
            return f"路徑段「{seg}」為 Windows 保留裝置名（{base.upper()}）"
    return None


def _collision_key(path: str) -> str:
    """碰撞分組鍵：先 NFC 正規化、再 lowercase（R67-A2/B16）。

    兩個軸合成同一把鍵，是因為它們在 checkout 端造成的後果**完全相同**——
    NTFS 大小寫不敏感使 `README.MD` 與 `README.md` 互相覆蓋；macOS 的
    precomposeunicode 使 NFD 與 NFC 兩形態指向同一個磁碟項目、同樣互相覆蓋。
    分成兩把鍵會讓「大寫 + NFD」對上「小寫 + NFC」這種混合形態從兩邊漏出去。
    """
    return unicodedata.normalize("NFC", path).lower()


def _dir_prefixes(path: str) -> list[str]:
    """回傳 path 的所有目錄前綴（由淺至深，**不含 path 自身**）。

    `a/b/c.md` → `["a", "a/b"]`；無目錄的 `x.md` → `[]`。
    刻意排除 path 自身：整條路徑的碰撞由第 3 項負責，此處只管目錄段，
    兩邊訊息不同（一個是檔案互相覆蓋、一個是目錄拓撲跨平台分歧）。
    """
    segs = path.split("/")
    return ["/".join(segs[:i]) for i in range(1, len(segs))]


def _non_nfc_reason(path: str) -> str | None:
    """index 路徑非 NFC → 回傳原因字串；是 NFC（含全 ASCII、CJK）→ None。

    零偽陽性：`is_normalized("NFC", s)` 對純 ASCII 與 CJK（本身無正規化分解）恆真，
    只有真的帶可組合序列（拉丁變音、諺文、含濁音假名…）的分解形態才會回 False。
    """
    if unicodedata.is_normalized("NFC", path):
        return None
    return (
        "索引路徑非 NFC 正規化形式（含可組合序列）— macOS 簽出會產生 phantom："
        "core.precomposeunicode 使 readdir 回 NFC，index 內的 NFD 項與工作樹的 NFC 檔"
        "成為兩個身份，git status 永遠不乾淨且無常規手段回復"
    )


def _scan_violations(files: list[str]) -> tuple[list[str], list[str]]:
    """對一組（已解碼的）tracked 路徑跑完六項檢查 → (violations, warnings)。

    與 `main()` 分離是為了讓六項檢查能以純路徑清單單元測試——不必造 git repo
    就能對每一項做缺陷注入紅綠實測（回歸鎖見
    `tools/tests/test_ntfs_trailing_space_device_name.py`）。
    """
    violations: list[str] = []
    warnings: list[str] = []

    for f in files:
        reason = _ntfs_seg_bad(f)
        if reason:
            violations.append(f"NTFS 不相容檔名：{f} — {reason}")
        nfc_reason = _non_nfc_reason(f)
        if nfc_reason:
            violations.append(f"Unicode 正規化違規：{f} — {nfc_reason}")
        level = _length_level(f)
        if level == "fail":
            violations.append(
                f"路徑過長：{f}（{len(f)} > {_LEN_FAIL} 字元；"
                f"Windows MAX_PATH=260 扣除 clone 前綴預留後超限）"
            )
        elif level == "warn":
            warnings.append(f"路徑偏長：{f}（{len(f)} > {_LEN_WARN} 字元，>{_LEN_FAIL} 將擋下）")

    # 第 3 項 — 整路徑碰撞：全量 tracked 路徑依正規化鍵分群，同鍵而拼法 >1 即互撞。
    # 用 set 收集拼法（而非 list）：merge conflict 期間 `git ls-files` 會把同一路徑
    # 依 stage 印多次，用 list 會把「同一條路徑」誤報成自己跟自己碰撞。
    by_key: dict[str, set[str]] = {}
    for f in files:
        by_key.setdefault(_collision_key(f), set()).add(f)
    for key in sorted(by_key):
        group = by_key[key]
        if len(group) > 1:
            joined = "」「".join(sorted(group))
            violations.append(f"NTFS 大小寫碰撞：「{joined}」僅大小寫不同（checkout 互相覆蓋）")

    # 第 5 項 — 目錄段層級碰撞：收集每條路徑的每一層目錄前綴，同鍵而拼法 >1 即違規。
    dirs_by_key: dict[str, set[str]] = {}
    for f in files:
        for d in _dir_prefixes(f):
            dirs_by_key.setdefault(_collision_key(d), set()).add(d)
    for key in sorted(dirs_by_key):
        group = dirs_by_key[key]
        if len(group) > 1:
            joined = "」「".join(sorted(group))
            violations.append(
                f"目錄段大小寫/正規化碰撞：「{joined}」僅大小寫或正規化形式不同"
                "（case-insensitive FS 上塌縮成一個目錄、case-sensitive FS 上是兩個，"
                "同一 commit 兩平台拓撲不同）"
            )

    return violations, warnings


# ── R76-01：checkout 根前綴預算（把隱含假設變成每次執行都印出來的量測值）──────────
# 兩個 Windows 上限都以「含結尾 NUL 的字串上限」計，減 1 即可用字元數：
#   檔案 CreateFileW    MAX_PATH = 260 ⇒ 可用 259
#   目錄 CreateDirectoryW      248 ⇒ 可用 247（MAX_PATH−12，替 8.3 短檔名留位）
# 「根前綴」一律指 **含結尾分隔符** 的 checkout 根（`C:\\Users\\u\\repo\\` ＝ 20），
# 這樣 `根前綴 + 相對路徑` 就是完整絕對路徑，算式不必再另外記一個 ±1。
_MAX_PATH_USABLE = 259
_MAX_DIRPATH_USABLE = 247


def _deepest_dir_len(files: list[str]) -> int:
    """最深 tracked **目錄**相對路徑的長度（無目錄時 0）。

    與「最長路徑」是兩個不同的量：目錄面的上限比檔案面低 12，故最長檔案路徑所在的
    目錄不一定就是綁住 clone 的那一個（R76-01 的實測順序正是先炸在建目錄那一步）。
    """
    return max((len(d) for f in files for d in _dir_prefixes(f)), default=0)


def _clone_prefix_budget_lines(files: list[str]) -> list[str]:
    """現況能安全 checkout 的「根前綴」上限——算式與代入值一起印，不寫死任何現值。"""
    longest = max((len(f) for f in files), default=0)
    deepest = _deepest_dir_len(files)
    file_side = _MAX_PATH_USABLE - longest
    dir_side = _MAX_DIRPATH_USABLE - deepest
    gate_side = _MAX_PATH_USABLE - _LEN_FAIL
    return [
        "📏 checkout 根前綴預算（含結尾分隔符，UTF-16 單位；未開 core.longpaths 時）：",
        f"   檔案面 {_MAX_PATH_USABLE} − 最長 tracked 路徑 {longest} = {file_side}",
        f"   目錄面 {_MAX_DIRPATH_USABLE} − 最深 tracked 目錄 {deepest} = {dir_side}",
        f"   ⇒ 現況根前綴上限 = min({file_side}, {dir_side}) = {min(file_side, dir_side)} 字元",
        f"   fail 門檻 {_LEN_FAIL} 對應的根前綴預留 = {_MAX_PATH_USABLE} − {_LEN_FAIL}"
        f" = {gate_side} 字元（本閘只保證這一種 checkout；上一行才是 repo 現況）",
        "   🔴 本閘量的是 repo **相對**長度，對 checkout 根前綴結構上失明 ⇒ clone 一律帶"
        " `-c core.longpaths=true`（R76-01：168 字元的根 → 27,523 檔只落地 301 檔、"
        "rc=128、無聲半套 checkout）。開箱指引：ONBOARDING.md §2 第 0 步",
    ]


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", "-z"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    ).stdout
    return [p for p in out.split("\0") if p]


def main() -> int:
    files = _tracked_files()
    violations, warnings = _scan_violations(files)

    # 預算區塊**先印且無條件印**：它是本閘的射程自陳，違規與否都要看得到
    # （R76-01：這道閘擋不住的那一半，只有寫成輸出才有人會讀到）。
    for line in _clone_prefix_budget_lines(files):
        print(line)

    for w in warnings:
        print(f"⚠ {w}", file=sys.stderr)

    if violations:
        for v in violations:
            print(f"❌ {v}", file=sys.stderr)
        print(
            f"\n共 {len(violations)} 筆違規 — 修法：改名後重新提交"
            "（對齊 tools/git-hooks/pre-commit A3 閘）",
            file=sys.stderr,
        )
        return 1

    max_len = max((len(f) for f in files), default=0)
    print(
        f"✅ NTFS 檔名檢查通過（{len(files)} 個 tracked 路徑，0 違規；"
        f"最長 {max_len} 字元，warn>{_LEN_WARN}/fail>{_LEN_FAIL}）"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
