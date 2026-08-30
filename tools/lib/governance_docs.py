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
#     （`_GOVERNANCE_DOC_GLOBS`）而未登記者一律 rc=1——「新增姊妹檔卻忘了登記」正是實際
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
    # R88 五筆結案的詳情面（同一資格：複審者要逐條重驗就得讀完它 ⇒ 受體積守門；
    # 它逐筆寫出「某缺陷現居何處／當回合實測值」⇒ 受指針稽核）。即刻登記，不等下一輪。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R88_Closure_Evidence.md",
    # R89 兩列（`DEF-200-112` 結案／`DEF-200-114` 立案）的詳情面。同一資格：帳本列被
    # 體積守門壓成索引之後，逐條重驗所需的原文只住這裡 ⇒ 它自己也必須受體積守門。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R89_Closure_Evidence.md",
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
    # R82 缺陷帳本清債的唯一居所（清債包 A5 開檔、帳本包續寫）。資格同上：它逐筆寫出
    # 「某 DEF-ID 的原狀態欄原文現居本檔某節」的座標宣稱（⇒ 指針稽核），而帳本列被瘦身成
    # 索引之後，**唯一**還能重驗那些結案是否為真的地方就是它（⇒ 體積守門）。
    # 🔴 它一度刻意取名 `AutoSDD_R82_*` 以避開本清單——因為開檔的那個包的持有面不含
    # `tools/lib/`，而登記進來是它結構上做不到的動作。那不是設計，是**沒有登記權的人
    # 用改名讓「不受管」變成看得見的決定**（該檔檔頭逐字記著這件事，並把補登記列為交棒
    # 第一項）。本輪由持有 `tools/lib/` 的包接手改回慣例前綴並登記——這正是那條交棒的兌現。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R82_Ledger_Closure.md",
    # R82 掃描發現的唯一居所。資格同 R80／R81 同名檔：它逐筆寫出「某發現／某 DEF-ID 的
    # 座標在某檔某行」的宣稱（⇒ 指針稽核），複審者要判「R82 還有哪些缺口開著」就得讀完
    # 它（⇒ 體積守門）。🔴 登記而非改名：`unregistered_governance_docs()` 的紅燈訊息
    # 自己提供了「改名避開命名慣例」這條出口，而上一列那支檔的檔頭正逐字記著上一次有人
    # 這樣做的判例——出口存在不等於它是合法動作。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R82_Scan_Findings.md",
    # R82 成果首次在 macOS 真機啟動時，平台切換 SOP 自身的五處障礙（DEF-101-999）的唯一
    # 居所。資格同上：它逐項寫出「某障礙的證據落在某檔某行／某實測輸出」的座標宣稱
    # （⇒ 指針稽核），而該 DEF 列已依 ROW_MAX_BYTES 瘦身成索引 ⇒ 唯一還能重驗那五項
    # 判讀的地方就是它（⇒ 體積守門）。它另承載三支待補機械鎖的 Next Action。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R82_Mac_Switch_Obstacles.md",
    # R83（mac 真機首輪）的掃描發現唯一居所。資格同 R80~R82 同名檔：它逐筆寫出「某發現／
    # 某 DEF-ID 的座標在某檔某行」的宣稱（⇒ 指針稽核），而本輪帳本列已依 ROW_MAX_BYTES
    # 瘦身成索引 ⇒ 唯一還能重驗那些判讀的地方就是它（⇒ 體積守門）。
    # 它另承載兩件本輪特有的東西：① `repin_log_problems()` 款(9) 強制的護欄層淨額承認
    # （`<!-- guard-total:R83 -->` 標記行，由 `doc_guard_total_problems()` 與
    # `_GUARD_LINES_REPIN_LOG` 表尾雙向對帳，寫錯即紅）；② §E 的 Next Action（五項尚未
    # 關的缺口，含「四方複審未執行 ⇒ 本輪全部修復皆屬作者自證」這一條）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R83_Scan_Findings.md",
    # R84（mac 第二輪、九包並行）的掃描發現唯一居所。資格同 R80~R83 同名檔：逐筆寫出
    # 「某發現／某 DEF-ID 的座標在某檔某節」的宣稱（⇒ 指針稽核），而本輪帳本列已依
    # ROW_MAX_BYTES 瘦身成索引 ⇒ 唯一還能重驗那些判讀的地方就是它（⇒ 體積守門）。
    # 它另承載兩件本輪特有的東西：① `repin_log_problems()` 款(9) 強制的護欄層淨額承認
    # （`<!-- guard-total:R84 -->` 標記行，由 `doc_guard_total_problems()` 與
    # `_GUARD_LINES_REPIN_LOG` 表尾雙向對帳，寫錯即紅）；② §D 的跨 session `git stash`
    # 事故——`block_destructive_git.py` 已知射程缺口的第一個真實命中。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R84_Scan_Findings.md",
    # 帳本洩壓包（bytes 死結出路①）搬出來的 15 列**已結超長列原文**的唯一居所。資格同
    # `CrossPlatform_R82_Ledger_Closure.md`（同一個動作的上一次先例）：主檔那些列已依
    # `ROW_MAX_BYTES` 瘦身成索引 ⇒ **唯一還能重驗那些結案是否為真的地方就是它**（⇒ 體積
    # 守門），且它逐節寫出「某 DEF-ID 的原文現居本檔某節」的座標宣稱（⇒ 指針稽核）。
    # 🔴 即刻登記而非改名避開：紅燈訊息自己提供了「改名」這條出口，而
    # `CrossPlatform_R82_Ledger_Closure.md` 那一列的註解正逐字記著上一次有人這樣做的判例。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R85_Ledger_Closure.md",
    # 本輪掃描發現的唯一居所（由掃描包產出、由帳本包代為登記——登記面住 `tools/lib/`，
    # 不在掃描包的持有面內，同 `CrossPlatform_R82_Ledger_Closure.md` 那一列記載的形態）。
    # 資格同 R80~R84 同名檔：逐筆寫出座標宣稱（⇒ 指針稽核），複審者要判「還有哪些缺口
    # 開著」就得讀完它（⇒ 體積守門）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R85_Scan_Findings.md",
    # R85 收尾單人窗口：護欄層重釘稽核列（`_GUARD_LINES_REPIN_LOG` R85 第二列）指名的
    # 「逐檔清單的家」——款(10) 要求淨額為正的重釘必須指名一份 `CrossPlatform_R<n>_*.md`。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R85_Guard_Repin_Evidence.md",
    # R85 四方複審：發現面（`CrossPlatform_R85_*.md` glob）與登記面本來就是雙向核對，
    # 而複審**每多落一份 findings 檔就多一筆紅**——SA 當場預測並驗證（落檔前 1 筆、
    # 落檔後 3 筆）。四份一次登齊，避免下一輪重蹈。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R85_Review_Architect.md",
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R85_Review_SA.md",
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R85_Review_SD.md",
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R85_Review_QA.md",
    # R86 配速最佳化的證據面。資格同上：它承載 repo 至今**唯一一筆外部獨立校準基準**
    # （掌舵者的 CLI 畫面 vs 程式從 `axes[]` 算出的值），而訴求 6z 的調研結論是沒有任何
    # 官方通道可問 ⇒ 那筆基準一旦只留在對話裡就等於沒發生（R85 教訓 5）；它另逐筆寫出
    # 「某常數／某判準現居某檔某符號」的宣稱（⇒ 指針稽核）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R86_Pace_Calibration.md",
    # R86 帳本改派的證據面（`ROW_MAX_BYTES` 洩壓的**接收端**，先例＝上方
    # `CrossPlatform_R85_Ledger_Closure.md`）：26 列的**原**承接輪次被就地改寫成新輪號後，
    # 主檔已不存在那個事實，而本輪 7 列孤兒列又依 700 bytes 上限瘦身成索引 ⇒ 唯一還能重驗
    # 「改派是否為真、原承接輪次是誰」的地方就是它（⇒ 體積守門）；它逐節寫出「某 DEF-ID 的
    # 原文現居本檔某節」的座標宣稱（⇒ 指針稽核）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R86_Ledger_Reassign_Evidence.md",
    # 本輪收尾單人窗口（`DEF-200-103`）：`_GUARD_LINES_REPIN_LOG` 兌現 `_NET_SUBTRACTION_
    # DUE_ROUND` 的到期義務（單輪淨額 ≤ 0）時，動用棘輪 `[歷史變短]` 那一款**自己指定**的
    # 出口——「真的要縮短（例如把史前列搬進 ADR）時…並在交件回報寫出搬去哪裡」。本檔就是那個
    # 「哪裡」：§A＝整列搬出的 R77~R80 共 11 列（逐列數字＋理由原文逐字）、§B＝理由欄搬出而
    # 本體留在程式碼內的 R81~R85 共 14 列、§C＝宣稱判準鎖的模組層立案敘事。資格同 R85 同名檔：
    # 它是那些史料**唯一還能重驗的地方**（⇒ 體積守門），且逐節寫出「某一列的原文現居本檔某節」
    # 的座標宣稱（⇒ 指針稽核）。🔴 它另受 `test_every_per_file_list_named_by_a_real_row_
    # exists_on_disk` 對磁碟驗——稽核列指名的清單不存在，款(9) 就是被幽靈檔名滿足的。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R86_Guard_Repin_Evidence.md",
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R87_Guard_Repin_Evidence.md",
    # R90 收尾單人窗口：稽核列款(9) 指名的「逐檔清單的家」，資格同上兩列（受
    # `test_every_per_file_list_named_by_a_real_row_exists_on_disk` 對磁碟驗）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R90_Guard_Repin_Evidence.md",
    # 本輪掃描發現的居所（慣例位置，資格同 R80~R85 同名檔：逐筆寫出座標宣稱 ⇒ 指針稽核；
    # 複審者要判「還有哪些缺口開著」就得讀完它 ⇒ 體積守門）。它同時是 `doc_guard_total_
    # problems()` 款(1) 要求的兩個標記站點之一（另一處＝`AutoSDD_improving_110.md`）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R86_Scan_Findings.md",
    # R91 收尾：同時是稽核列款(9) 指名的「逐檔清單的家」與 `doc_guard_total_problems()`
    # 款(1) 的兩個標記站點。資格另有一項是同名檔沒有的：它承載本輪那組**真跑實驗**的
    # 逐字輸出（單一 vs 兩個相接的 `hookSpecificOutput` 物件，後者實測兩則訊息一起消失）
    # ——那是 `emit_to_model()` 為何非得「一行程至多一份 JSON」的唯一還能重驗的依據。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R91_Scan_Findings.md",
    # R93：額度攤提換方案適配（DEF-200-122 收尾／DEF-200-114 補完）的落地證據。資格同
    # 上方同名檔：逐節寫出「規格覆核發現／紅綠自證輸出／LOC 棘輪處置狀態」的座標宣稱
    # （⇒ 指針稽核），複審者要重驗落地過程中發現的規格缺陷（`burn_ratio` 的 `last_fp`
    # 取法）就得讀完它（⇒ 體積守門）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R93_Plan_Change_Adaptive_Evidence.md",
    # R95 三個並行包（Pkg-B 治理檔禁寫／Pkg-C 配速致動器／Pkg-D 喚醒選路）各自的證據檔，
    # 由收尾單人窗口一次補三列（鐵律七：登記面住 `tools/lib/`，不在任何並行包的持有面內；
    # 三份檔頭皆自陳「登記留收尾窗口」）。資格同 R85~R93 同名檔：各自承載該包唯一還能重驗
    # 的實測逐字帳（govwrite 九格 rc 矩陣／攤提免除的憲法檢查表／逐字稿大小分佈量測），
    # 且皆為 R89 體例的史料搬遷目的地——逐節寫出「某敘事原文現居本檔某節」的座標宣稱
    # （⇒ 指針稽核），複審者要重驗各包落地就得讀完它（⇒ 體積守門）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R95_GovWrite_Evidence.md",
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R95_Pace_Actuator_Evidence.md",
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R95_Resume_Strategy_Evidence.md",
    # R95 收尾單人窗口：護欄層行數棘輪重釘的量測帳＋鎖檔史料搬遷目的地（資格同
    # R86/R87/R90 的同名 Guard_Repin 檔：稽核列指名的家、逐節座標宣稱、體積守門）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R95_Guard_Repin_Evidence.md",
    # R96（Windows 真機切換輪）兩份姊妹檔。資格與 R88/R89 同名 Closure_Evidence 逐字同一份：
    # 帳本九列（`DEF-200-149`～`157`）被體積守門壓成索引之後，逐筆重驗所需的原文（根因、
    # 平台不對稱性、當回合 rc）只住 Closure_Evidence ⇒ 它自己必須受體積守門；而 Scan_Findings
    # 逐列寫出「某 DEF-ID 的詳情在某節」的座標宣稱 ⇒ 受指針稽核。兩者同輪新生，即刻登記，
    # 不等下一輪（SA-R60R3-01 的復發路徑正是「新建姊妹檔而兩張清單都沒進」）。
    # 🔴 Scan_Findings 另承載本輪護欄層重釘的 `guard-total:R96` 兩處標記（`_GUARD_TOTAL_DOC_GLOBS`
    # 的掃描面之一）⇒ 它同時是行數棘輪的文件側對帳站點，漏登記會讓那道對帳無人可查。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R96_Closure_Evidence.md",
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R96_Scan_Findings.md",
    # 額度哨兵 token 洩漏調查（非 R71~R96 跨平台複審系列延續，僅沿用命名慣例；即刻登記，
    # 理由與上方各列相同：複審者要逐條重驗就得讀完它 ⇒ 受體積守門；逐筆寫出座標宣稱 ⇒ 受
    # 指針稽核）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R97_Scan_Findings.md",
    # R98 PRD 對照現況差距分析（AutoClaude↔AISDLC_SDD 橋接複驗，另一併行包產出）。資格同
    # 上方同名檔：逐節寫出「某 PRD 概念的落地位置／某 DEF-ID 的座標」宣稱（⇒ 指針稽核），
    # 複審者要判「PRD 對照現況還有哪些落差」就得讀完它（⇒ 體積守門）。即刻登記，不等下一輪。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R98_PRD_Gap_Analysis.md",
    # DEF-200-131 修復：`Quota_R90_CrossAccount_Experiment.md` 是 PRD `:79`／`:1372`／`:296`
    # 三處修憲／校準論述**唯一**引用的實測依據，資格同上——複審者要重驗 T5 升格與跨帳號碰撞
    # 率結論就得讀完它（⇒ 體積守門），且它是「某論述現居本檔某節」座標宣稱的對象（⇒ 指針
    # 稽核）。此檔命名不符 `CrossPlatform_*` 慣例，過去對 `unregistered_governance_docs()`
    # 結構上不可見（見下方 `_GOVERNANCE_DOC_GLOBS` 的第二個樣式）。
    _REPO_ROOT / "docs" / "06_quality" / "Quota_R90_CrossAccount_Experiment.md",
    # R98 護欄層行數棘輪重釘證據（收尾單人窗口產出）。資格同上：`_GUARD_LINES_REPIN_LOG`
    # 的 R98 稽核列指名本檔為逐檔漂移清單的家（⇒ 指針稽核），複審者要重驗「為何本輪淨額
    # 能壓到 ≤0」就得讀完它（⇒ 體積守門）。即刻登記，不等下一輪。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R98_Scan_Findings.md",
    # R98 第二次收斂（BSD regex 修復再度撞上護欄層行數棘輪）：把 `test_platform_neutral_
    # paths.py` 裡最大宗的 20 段逐輪判準 WHY 敘事原文一字不漏搬到這裡，測試檔本身只留判準
    # 邏輯＋指回本檔對應章節的錨點。資格同上——它是那 20 段敘事**唯一還能重驗的地方**
    # （⇒ 體積守門），且逐節寫出「某判準的 WHY 原文現居本檔某錨點」的座標宣稱（⇒ 指針稽核）。
    # 🔴 DEF-200-131 同型：新建證據檔沒有即刻登記，導致 `unregistered_governance_docs()`
    # 對它結構上不可見。即刻登記，不等下一輪。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_Guard_Line_History.md",
    # R98 收尾（macOS 側）七支跨平台紅的取證：DEF-200-178~184 七列已依 ROW_MAX_BYTES
    # 瘦身成索引 ⇒ 本檔是那七筆判讀（四種修法的實測比較、A3 放寬守衛的實證、驗證清單
    # 涵蓋缺口的逐字證據）**唯一還能重驗的地方**（⇒ 體積守門），且七列各指名本檔某節
    # 為其詳情居所（⇒ 指針稽核）。即刻登記，不等下一輪（DEF-200-131 同型）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R98_Mac_Closure_Evidence.md",
    # 帳本減半波（單一書記收斂）：四包回報複驗、B 類證偽、E 類拆列裁決的詳情面。
    # 資格同上——本輪 30 餘筆帳本列瘦身為索引後，逐條重驗所需的原文只住這裡
    # （⇒ 體積守門），且逐節寫出「某 DEF-ID 現居本檔某節」的座標宣稱（⇒ 指針稽核）。
    # 即刻登記，不等下一輪（DEF-200-131 同型）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R99_Ledger_Closure.md",
    # 本輪護欄層行數棘輪重釘證據（收尾單人窗口產出）。資格同 R98 同名檔：
    # `_GUARD_LINES_REPIN_LOG` 本輪的稽核列指名本檔為逐檔漂移清單的家（⇒ 指針稽核），
    # 且本檔承載本輪 `guard-total:` 兩處標記（`_GUARD_TOTAL_DOC_GLOBS` 掃描面之一）⇒
    # 同時是行數棘輪的文件側對帳站點。即刻登記，不等下一輪（DEF-200-131 同型）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R99_Scan_Findings.md",
    # 帳本連通分量分析（R-06 對抗包）：本輪核心因果敘事「48 個連通分量、41 個孤立單筆
    # ⇒ 推翻結案吞吐恆為 1」的落地物與可重跑證據。資格同上——複審者要核對這個量化判決
    # 就得讀完輸入定義／演算法／逐一列出的成員（⇒ 體積守門），且逐節寫出「某 DEF-ID
    # 屬於哪個分量」的座標宣稱（⇒ 指針稽核）。即刻登記，不等下一輪（DEF-200-131 同型）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R99_Ledger_Connectivity_Analysis.md",
    # ADR-XPLAT-013（LOC 計價改 assertion-only）的逐檔清單與立案實測。資格同前一輪同名檔：
    # `_GUARD_LINES_REPIN_LOG` 本輪兩列稽核痕跡各指名本檔為逐檔清單的家（⇒ 指針稽核），
    # 且本檔承載本輪 `guard-total:` 兩處標記（`_GUARD_TOTAL_DOC_GLOBS` 掃描面之一）⇒
    # 同時是行數棘輪的文件側對帳站點；改前／改後的計價實測只住這裡，複審者要重驗
    # 「餘裕從 12 行變成四位數是怎麼來的」就得讀完它（⇒ 體積守門）。
    # 即刻登記，不等下一輪（DEF-200-131 同型）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R100_Scan_Findings.md",
    # DEF-200-207／DEF-200-208 的逐檔清單與立案實測。資格同前一輪同名檔：
    # `_GUARD_LINES_REPIN_LOG` 的 R101 列指名本檔為逐檔清單的家（⇒ 指針稽核，round-label-ok），
    # 且本檔承載本輪 `guard-total:` 標記（`_GUARD_TOTAL_DOC_GLOBS` 掃描面之一）⇒
    # 同時是行數棘輪的文件側對帳站點；複審者要重驗「baseline provenance 修法」與
    # 「一次性例外核准淨額」就得讀完它（⇒ 體積守門）。即刻登記，不等下一輪。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R101_Scan_Findings.md",
    # DEF-200-204（PRD §4.2.4 動態配速平穩性機制）的逐檔清單與立案實測。資格同前一輪
    # 同名檔：`_GUARD_LINES_REPIN_LOG` 的兩筆 R102 列皆指名本檔為逐檔清單的家（⇒ 指針  round-label-ok  # noqa: E501
    # 稽核），且本檔承載本輪 `guard-total:` 標記（`_GUARD_TOTAL_DOC_GLOBS` 掃描面之一）
    # ⇒ 同時是行數棘輪的文件側對帳站點；複審者要重驗四方終審殘留項（H1 fixture、
    # 啟動自檢 60 秒佔位值）就得讀完它（⇒ 體積守門）。即刻登記，不等下一輪。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R102_Scan_Findings.md",
    # PRD §4.2.5／§4.2.1 BURSTING/EWMA（只算不接線）的逐檔清單與搬遷散文全文。資格同
    # 前幾輪同名檔：`_GUARD_LINES_REPIN_LOG` 的 R104 列指名本檔為逐檔清單的家  round-label-ok
    # （⇒ 指針稽核），且本檔承載本輪 `guard-total:` 標記（`_GUARD_TOTAL_DOC_GLOBS`
    # 掃描面之一）⇒ 同時是行數棘輪的文件側對帳站點。即刻登記，不等下一輪。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R104_Scan_Findings.md",
    # tools/tests/ 護欄層行數棘輪維護輪（DEF-200-224）的逐檔清單與搬遷散文全文。資格同
    # 前幾輪同名檔：`_GUARD_LINES_REPIN_LOG` 的 R105 列指名本檔為逐檔清單的家  round-label-ok
    # （⇒ 指針稽核），且本檔承載本輪 `guard-total:` 標記（`_GUARD_TOTAL_DOC_GLOBS`
    # 掃描面之一）⇒ 同時是行數棘輪的文件側對帳站點。即刻登記，不等下一輪。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R105_Scan_Findings.md",
    # 四方複審 REJECT 修復（DEF-200-202）同輪追加的逐檔清單與 WHY。資格同前幾輪
    # 同名檔：`_GUARD_LINES_REPIN_LOG` 的 R105 追加列指名本檔為逐檔清單的家  round-label-ok
    # （⇒ 指針稽核）；本檔不承載 `guard-total:` 標記（避免與上一列同名檔重複被
    # `_GUARD_TOTAL_DOC_GLOBS` 掃到造成雙重對帳站點）⇒ 只受體積守門管。即刻登記。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R105_FourParty_Fix.md",
    # Windows 11 交接輪兩筆真缺陷（root-infra-ci／windows-compat-ci）逐檔清單與根因。
    # 資格同前幾輪同名檔：`_GUARD_LINES_REPIN_LOG` 的本輪列指名本檔為逐檔清單的家  round-label-ok
    # （⇒ 指針稽核），且本檔承載本輪 `guard-total:` 標記（`_GUARD_TOTAL_DOC_GLOBS`
    # 掃描面之一）⇒ 同時是行數棘輪的文件側對帳站點。即刻登記，不等下一輪。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R106_Scan_Findings.md",
    # 外部阻塞軌複查（2026-08-27）：DEF-200-185 已依 `ROW_MAX_BYTES` 瘦身成索引，本檔是
    # 唯一還能重驗該筆結案的地方（⇒ 體積守門），且逐節寫出「DEF-200-185 現居本檔」的
    # 座標宣稱（⇒ 指針稽核）。即刻登記，不等下一輪。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_External_Blocked_Recheck_20260827.md",
    # DEF-101-752（R82）帳本瘦身的接收端：帳本該列 R82 前的「狀態」欄原文（逐字保全）＋
    # R82 三處收斂的紅綠自證輸出，皆已從主檔搬出。資格同上——帳本列已瘦身成索引 ⇒ 唯一還
    # 能重驗該次結案的地方就是它（⇒ 體積守門），且它逐節寫出「DEF-101-752 原文現居本檔
    # 某節」的座標宣稱（⇒ 指針稽核）。🔴 本檔命名曾刻意不循 `CrossPlatform_*.md` 慣例
    # 以迴避這道登記；四方複審 Architect 發現後先改為僅登記、不改名，但帳本結案輪修復
    # 包發現「僅登記」本身仍讓登記面（本清單）與發現面（`_GOVERNANCE_DOC_GLOBS` 掃描
    # 磁碟）不一致——與本機制原本要防的「磁碟上有卻沒登記」方向相反。正確做法是讓檔名
    # 符合 glob 樣式，故已改名為下列檔名（該檔頭自述已一併訂正）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R82_DEF101752_Untracked_Scan_Closure.md",
    # R107 結案輪逐筆結案證據（結案包 #1）：主帳本各結案列的狀態欄  round-label-ok
    # 已瘦身成「短句＋指針」，驗證指令逐字／rc／輸出關鍵行全數只住本檔 ⇒ 唯一還能重驗
    # 這批結案的地方就是它（⇒ 體積守門），且它逐節寫出「證據見本檔 §DEF-XXX-XXX」的
    # 座標宣稱（⇒ 指針稽核）。即刻登記，不等下一輪。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R107_Ledger_Closure.md",
    # R107 兩場四方複審的磁碟固化載體（2026-08-28）：PRD v2.1.4 修憲批次與收尾複審 round-label-ok
    # 的四鏡判決全文唯一長存處——PRD 落款與帳本 DEF-200-141/142/157 結案列引據的就是它
    # （⇒ 體積守門＋指針稽核），逐字轉存自 session 逐字稿、僅路徑匿名化。即刻登記。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R107_Review.md",
    # 架構輪四方複審一審紀錄（19 blocking 的逐筆判決與收斂鏈）：WHY 屬本類＝五份設計產出
    # 的每一筆 blocking 處置只住這裡，複審者要重驗「哪一筆被誰打回、修在哪」就得讀完它
    # （⇒ 體積守門），且它逐筆寫出「某 finding 的處置落在某檔某節」的座標宣稱（⇒ 指針稽核）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R108_Review.md",
    # DEF-200-231 哨兵死因實機取證：WHY 屬本類＝該列已依 ROW_MAX_BYTES 瘦身成索引，
    # 「哨兵為何自刪排程」的四疊加缺陷 D1~D4 與當回合實測值（User/Machine/行程三層環境變數、
    # 自刪時刻）唯一還能重驗的地方就是它（⇒ 體積守門），且它寫出「該 DEF-ID 詳情現居本檔
    # 某節」的座標宣稱（⇒ 指針稽核）。即刻登記，不等下一輪（DEF-200-131 同型）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R108_Sentinel_Forensics.md",
    # R111 哨兵事故鑑識（mac 429 同池同死）：WHY 屬本類＝ round-label-ok
    # DEF-200-231③/234 的時間軸取證與 D3+D4 mac 重演證據唯一的家（⇒ 體積守門），
    # 且帳本兩列以「＝R111鑑識檔」座標宣稱指向本檔（⇒ 指針稽核）。 round-label-ok
    # 即刻登記，同 R108 姊妹檔判例。 round-label-ok
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R111_Sentinel_Forensics_Mac.md",
)

# 姊妹治理文件的命名慣例：`docs/06_quality/{CrossPlatform,Quota}_*.md`。這**不是**把具名
# 常數換成 glob（那個方向的反對理由見上方），而是拿 glob 當**發現面**去反查登記面：具名
# 常數仍是權威，glob 只負責在「有人建了一份長得像治理文件的檔卻沒登記」時吵起來。
# 🔴 DEF-200-131：原僅 `CrossPlatform_*.md` 一個樣式，使命名慣例不同的姊妹檔（`Quota_*.md`，
# 例：`Quota_R90_CrossAccount_Experiment.md`）對這道發現面結構上不可見——`fnmatch`／
# `Path.glob()` 不支援單一字串內的前綴交替（無 `{a,b}` 語法），故改為**樣式元組**、
# 呼叫端逐一 glob 後聯集。新增樣式前先確認不會誤撈 `docs/06_quality/` 既有其他慣例
# （已現查：`Quota_*.md` 今日在該目錄下唯一命中即 `Quota_R90_CrossAccount_Experiment.md`）。
_GOVERNANCE_DOC_GLOBS = ("CrossPlatform_*.md", "Quota_*.md")
_GOVERNANCE_DOC_DIR = _REPO_ROOT / "docs" / "06_quality"
