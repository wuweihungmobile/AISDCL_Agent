# R216 收尾證據：換 session 依快取成本（不讓快取過期）與真機自驗載具收尾

> 輪次＝R216（`python tools/check_handoff_carriers.py` 首行以本檔檔名現查）。收尾單人窗口（SD＋文件治理）於 2026-11-19 做連動面收齊；本檔只記**可重驗的座標**，不複寫數字（量測值一律現查）。
> 上游：掌舵者 2026-11-18「請檢討context 25萬就切換Session的合理性, 是否應該專注在不要讓Cache過期!」（再指令三連）；裁決＝不設軟線、只留硬線、hold 不實作。設計＝`docs/02_architecture/SessionSwitch_CostModel_Design.md`（§11 裁決段優先）；驗收＝`docs/03_testing/contracts/TCS-SessionSwitch-CostModel-20261118.md`；ADR＝ADR-XPLAT-004 §2.19；PRD＝v2.1 修訂表 v2.1.22。

## 一、本輪收齊的連動面（同一個 commit）

| 面 | 座標 |
|---|---|
| ADR | `docs/04_planning/ADR/ADR-XPLAT-004-token-endurance-protocol.md` §2.19（新）；§2.13／§2.14／§2.17／§2.18 的 R1／R3／「已出聲」敘述就地加註「v2.1.22 起見 §2.19」 |
| PRD 修憲 | `docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`：修訂表 v2.1.22 列、§16.6 列、§1.2 原則 2／§4.3／§4.5.4／§11.3 四處就地註記（不改既有條文一字） |
| 根 CLAUDE.md | 〈換 session 的 SOP〉〈收斂閘與硬線〉〈派背景代理＝同一回合掛監督〉、新增〈不讓快取過期〉一段、機械守衛總表 `sessionctl_guard.py`／`context_budget_guard.py` 兩列、現查速查表三列（keepwarm／runlong+waitfor／realverify） |
| TCS | `TCS-SessionSwitch-CostModel-20261118.md`（軟線／hold 標「依裁決不實作」、`waitfor` 上限 255）；`TCS-SessionCtl-20261113.md`／`TCS-TokenWaste-20261114.md`（R1／R3 列標史料；FR-W2、V-W3 改保溫點新定義） |
| 缺陷帳本 | `AutoSDD_Defect_Log.md` DEF-200-611～615（詳情 `CrossPlatform_R215_PendingVerification_Closure.md`〈R216 收尾〉） |
| 落點表 | `docs/02_architecture/Root_Layout_and_Module_Placement.md` sessionctl 列補新檔、realverify 列 DEF 號訂正 |
| realverify | `RealVerify_Protocol/cases.json` 補登 14 案例；`sched.register_once` 改走 `quiet_python()`；`os.name` 守衛；整檔 `# ruff: noqa: E501` 改逐行 |
| 棘輪 | `test_adr_xplat001_c1c2_lock.py`（逐檔表、重釘列、接鏈列、名冊精確淨額）、`run_root_unittests.py::MIN_TESTS`、`skip_tag_policy._TREE_FILE_FLOORS`、`test_subprocess_encoding_hygiene.py` 掃描面下限、`governance_docs.py`、compat-ci `paths`（`tools/lib/realverify/**`）、ONBOARDING 基線 |
| 死碼 | `supervise.WATCH_CMD_MARK` 刪除（改 `_WATCH_CMD_RE`，無外部引用，ADR／TCS 敘述同步） |

## 二、誠實未結（不得宣稱已完成）

- TCS WP-G（`waste_census` M-K1～M-K6、`--replay-switch`、`--calibrate-switch`）本輪未實作；park 選路（階段 3，REQ-SS-19）未實作。
- E2E-SS-04（`-p` 模式快取層）、E2E-SS-05（上線 14 天後 M-K2＝0）、V-SS1～V-SS4 互動真機項：以 `docs/06_quality/RealVerify_Result_Ledger.md` 已入帳者為準，未入帳＝未結。
- PRD §16.6 v2.1.22 列因此維持 ⏸。

## 三、當回合驗證輸出

見收尾回報（指令、Ran／OK／rc）；本檔刻意不抄數字。
