"""具名治理文件清單（`_GOVERNANCE_DOCS`）的 SSOT —— R80 自 `check_defect_log_crossref.py` 下沉。

為何搬家（不是為了整齊）：這張清單是**單調增長**的登記面（每輪新生的證據檔都要加一筆），
而它原本住的那支檔受 `AutoClaude/tools/check_loc_budget.py` 的 SPECIAL_FILES **raw-line
棘輪**管、且該棘輪以「納管當下實際行數」設定＝近乎零餘裕。兩者相乘的後果已經實際發生：
`unregistered_governance_docs()` 的紅燈訊息教人「請在 `_GOVERNANCE_DOCS` 補上一筆」，
而照做即撞 LOC 棘輪 ⇒ **A 鎖要求的動作正是 B 鎖的違規**（`test_check_defect_log_crossref.py::
TestActionableMessagesHaveLocHeadroom` 就是為這個形態而立的，R80 實測它真的紅了）。
把單調增長項移到不受該棘輪管的模組，是那道棘輪自己指定的第一順位處置（「先刪死碼／抽共用
模組」，先例 `tools/lib/ci_liveness.py`、`tools/lib/defect_ledger_index.py`），
優於在帳本裡具名調高門檻——調高門檻是砸溫度計。

**物件同一性契約不變**：`check_defect_log_crossref` 再匯出本模組這個 tuple、
`archive_defect_log` 再匯出閘門那一個，三者是**同一個物件**（`assertIs` 鎖住，
見 `tools/tests/test_archive_defect_log.py::TestGovernanceDocsAreOneSharedSsotObject`）。
消費端（含測試的 `mock.patch.object(m, "_GOVERNANCE_DOCS", ...)`）零改動。
"""

from __future__ import annotations

from pathlib import Path

#: repo 根。本模組住 `tools/lib/`，故往上兩層。刻意自己解析而非由呼叫端傳入：
#: 這份清單是**模組載入時就成立的常數**，且下方 WHY 第三點明載「路徑不由帳本主檔推導」。
_REPO_ROOT = Path(__file__).resolve().parents[2]

# 🔴 R60 round 3（`DEF-101-587` ＋ SA-R60R3-01）：體積守門的涵蓋面由「帳本家族」擴到
# **具名治理文件**，且**全 repo 只有這一張清單**。詳細史料見帳本該兩列與
# `docs/06_quality/CrossPlatform_R60_Fix_Evidence_r3.md`；此處只留仍在約束今日行為的 WHY：
#
#   · **為何要管**：帳本兩層化後，完整證據（bug-injection 紅綠、逐條指令與輸出）住在這些
#     檔裡，它們承擔與帳本**同等**的可讀性義務，卻一度完全不在任何體積守門內（實測曾距
#     上限僅 1,181 bytes）。把資料搬到另一支檔就繞過守門＝守門綁在檔名而非義務上。
#   · **為何具名而不 glob 整個 docs/**：「哪些檔承擔帳本級義務」是判斷，判斷要能被 review
#     看見。新增治理文件時在此加一筆，並在該檔內寫明它為何屬於這一類。
#   · **為何路徑不由 `_DEFECT_LOG.parent` 推導**：治理文件在哪與帳本主檔在哪是兩件事；
#     綁在一起會讓測試把 `_DEFECT_LOG` mock 到暫存目錄時，這些檔被判為缺席而整批假紅。
#   · **為何是一個集合而非「體積一張、指針一張」**：兩項義務綁同一個資格——複審者要逐條
#     重驗就得讀完它（⇒ 體積），它會寫出「某 DEF-ID 現居某檔」的宣稱（⇒ 指針稽核）。
#     曾經兩支工具各有一個同名 `_GOVERNANCE_DOCS` 而成員不同、各缺對方一支，於是新生的
#     姊妹檔只進了其中一張清單。今日三側綁的是**同一個 tuple 物件**（閘門與 archive 側
#     皆 `= <上游>._GOVERNANCE_DOCS` 再匯出，`assertIs` 鎖住）。若未來真出現
#     只受其中一項管的檔，才拆成兩個**不同名字**的常數並各寫 WHY——絕不可同名而成員不同。
#   · 另一道守門（`unregistered_governance_docs()`）：磁碟上凡符合姊妹檔命名慣例
#     （`_GOVERNANCE_DOC_GLOB`）而未登記者一律 rc=1——「新增姊妹檔卻忘了登記」正是實際
#     發生過的路徑，不能只靠人記得。
_GOVERNANCE_DOCS = (
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R60_Fix_Evidence.md",
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R60_Fix_Evidence_r3.md",
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_Scan_Dimensions.md",
    # 下三支＝R61／R62 收輪證據：免重演 SA-R60R3-01「新建證據檔兩張清單都沒進」與 R61「插曲二」。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R61_Architect_Evidence.md",
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R61_SAQA_Evidence.md",
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R62_Architect_Evidence.md",
    # R68 十二維掃描的 69 筆存活缺陷清單（帳本 DEF-101-702 的詳情面）。資格＝複審者要逐條
    # 重驗就得讀完它（⇒ 體積守門）＋ 它會寫出「某缺陷現居何處」的宣稱（⇒ 指針稽核）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R68_Scan_Findings.md",
    # R75 缺陷詳情面（即刻登記；本檔受 raw-line 棘輪零餘裕，上兩段註解各兩行併一行換出額度）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R75_Review_Evidence.md",
    # 本輪掃描發現清單（承擔同一個資格：複審者要逐條重驗就得讀完它 ⇒ 受體積守門；它逐筆
    # 寫出「某缺陷現居何處」的座標宣稱 ⇒ 受指針稽核）。即刻登記，不等下一輪。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R76_Scan_Findings.md",
    # 本輪的兩份：triage（去重分級與跨維形態）與 fix plan（修復包切分與驗收指令）。
    # 同一個資格——複審者要逐條重驗就得讀完，且兩者都寫出缺陷座標宣稱。即刻登記。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R77_Triage.md",
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R77_Fix_Plan.md",
    # 技術債清除輪：未結列逐筆實查的證據面（結案 3 筆的紅→綠實測、STILL-OPEN 的當回合
    # 量測、NEEDS-DECISION 清單）。同一個資格——複審者要重驗結案判定就得讀完它。即刻登記。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R78_Debt_Audit.md",
    # M1~M6 成熟度判準的 SSOT（R78 ARCH-05 搬家：原本寄生在輪次專屬的掃描發現文件裡，
    # 那種文件是凍結記錄、沒人回頭維護，於是 M5 的攔截率三處各寫一份且全部過期）。
    # 資格同上：複審者要判「這一輪算不算成熟」就得讀完它，且它寫出載具座標宣稱。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_Maturity_Criteria.md",
    # R78 四方複審與五修復包的證據面（30 findings 逐筆、每道新判準的注入紅綠）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R78_Review.md",
    # R79 清債包：帳本瘦身的**接收端**（列＝索引 ≤700 bytes，長文一律搬去那裡）。資格同上。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R79_Debt_Audit.md",
    # R79 四方複審結論的轉錄（宣稱「某 DEF-ID 處置為何」⇒ 指針稽核；覆核就得讀完它 ⇒ 體積守門）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R79_Review.md",
    # R80 架構減法包的證據面（每一筆刪除的「刪什麼／誰還在守／省幾行」逐筆取證與淨額表）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R80_Subtraction_Evidence.md",
    # R80 包 F（mac／POSIX 落差）的證據面：逐筆 before/after 與 rc，並寫出「某 DEF-ID 的
    # 詳情在本檔某節」的座標宣稱 ⇒ 體積守門與指針稽核兩項義務都成立，資格同上。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R80_PackF_Posix_Evidence.md",
    # R80 八維掃描 88 筆發現的唯一居所（R80-SD-05）＋護欄層 +1528 的逐檔清單與必要性辯護。
    # 資格同上：複審者要判「哪些缺口還開著」就得讀完它，且它逐筆寫出座標與居所宣稱。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R80_Scan_Findings.md",
    # R80 四方複審（一審＋二審）結論的轉錄。資格同 R79 同名檔：它逐筆寫出「某 finding 的
    # 處置落在某 DEF-ID」的座標宣稱（⇒ 指針稽核），覆核者要重驗處置就得讀完它（⇒ 體積守門）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R80_Review.md",
    # R81 第一批九路掃描的唯一居所，**三份姊妹檔**（第一版合成單檔實測 253,373 bytes 已越
    # warn 線 245,760，故照 `DEF-101-587` 體例拆分；三份各自維護同一張對照表的 `__SELF__`
    # 指向）。資格同 R80 同名檔：複審者要判「R81 還有哪些缺口開著」就得讀完（⇒ 體積守門），
    # 且三份都逐筆寫出「某發現／某 DEF-ID 的座標在某檔某行」的宣稱（⇒ 指針稽核）。即刻登記。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R81_Scan_Findings.md",
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R81_Quota_Review.md",
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R81_Ledger_Triage.md",
    # R81 四方複審裁決與 17 筆 blocking 的逐筆轉錄。資格同 R79／R80 同名檔：它逐筆寫出
    # 「某 finding 的處置落在某檔某節」的座標宣稱（⇒ 指針稽核），覆核者要重驗處置就得
    # 讀完它（⇒ 體積守門）。即刻登記。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R81_Review.md",
)

# 姊妹治理文件的命名慣例：`docs/06_quality/CrossPlatform_*.md`。這**不是**把具名常數
# 換成 glob（那個方向的反對理由見上方），而是拿 glob 當**發現面**去反查登記面：
# 具名常數仍是權威，glob 只負責在「有人建了一份長得像治理文件的檔卻沒登記」時吵起來。
_GOVERNANCE_DOC_GLOB = "CrossPlatform_*.md"
_GOVERNANCE_DOC_DIR = _REPO_ROOT / "docs" / "06_quality"
