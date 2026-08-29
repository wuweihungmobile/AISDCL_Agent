# 護欄層行數棘輪 — 逐輪判準敘事史料歸檔

- **建立日期**：2026-08-21
- **建立者**：R98 收尾單人窗口（第二次收斂：BSD regex 修復再度撞上護欄層行數棘輪後的結構性減法）

## 這份文件是什麼、為什麼要有它

`tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `TestGuardLayerRatchet`／`TestShrinkOnlyRatchet`
把 `tools/tests/*.py` 的**淨行數**釘成只准往下走（見該檔 `_FROZEN_GUARD_LINES`／
`guard_line_problems()`）。`tools/tests/test_platform_neutral_paths.py` 是這張表上最大的
幾支鎖檔之一，而它每一道跨平台判準旁邊都附了一段完整的「缺陷本體／判準設計取捨／
誠實劃界」中文散文——這是好的工程紀律（Rule 9：測試要驗 intent 不只是 behavior），
但它與「淨行數只准往下走」這個機械物直接打架：本輪（R98）已經第四次因為一支功能性
修復（LOC 拆分、E501 修復、BSD regex 修復…）讓某支鎖檔的行數往上走，而前三次的處理
方式都是在 `_scan_roots()` 附近「找一行可以壓縮的史料註解」勉強打平淨額到 0——這只是
把同一個結構性問題往後推，不是解決它。

Architect 複審（R98 三審）點名了根因：**逐輪重釘的敘事不該住在被棘輪管轄的測試檔本身**。
本文件把 `test_platform_neutral_paths.py` 裡最大宗的「逐輪歷史敘事」段落**原文一字不漏**
搬到這裡（只是換位置，不是刪減內容——所有缺陷本體、實測數字、誠實劃界都完整保留），
測試檔本身只留：判準邏輯（regex／AST／常數）＋一行指向本文件對應章節的指標。
本文件是純 Markdown、不在 `tools/tests/*.py` 的行數棘輪掃描面內，因此可以承載這些內容
而不再吃掉護欄層的預算，也不會遺失任何「為什麼這樣設計」的紀錄。

**索引**（依原始碼在 `test_platform_neutral_paths.py` 內出現的順序排列；章節標題即
原始碼裡指向本文件時使用的〈…〉錨點名稱）：

1. [`_scan_roots` 三處修正 WHY](#_scan_roots-三處修正-why)
2. [R60 round 3 tmpdir 判準 WHY](#r60-round-3-tmpdir-判準-why)
3. [R69 反方向 POSIX 絕對路徑判準 WHY](#r69-反方向-posix-絕對路徑判準-why)
4. [R69 mock.call repr 判準 WHY](#r69-mockcall-repr-判準-why)
5. [R69 P1 Path 識別鍵判準 WHY](#r69-p1-path-識別鍵判準-why)
6. [R74 PATHEXT 平台守衛判準 WHY](#r74-pathext-平台守衛判準-why)
7. [R76 文字編碼判準 WHY](#r76-文字編碼判準-why)
8. [R76 複審 ARCH-01 標記互斥 WHY](#r76-複審-arch-01-標記互斥-why)
9. [第六道判準（平台專屬 API 守衛）WHY](#第六道判準平台專屬-api-守衛why)
10. [R79 工作樹行尾閘 WHY](#r79-工作樹行尾閘-why)
11. [R79 Windows 目錄項原語 WHY](#r79-windows-目錄項原語-why)
12. [R79 exec bit 索引模式判準 WHY](#r79-exec-bit-索引模式判準-why)
13. [雙向注入語料矩陣 WHY](#雙向注入語料矩陣-why)
14. [R80 鐵律三對照表訂正 WHY](#r80-鐵律三對照表訂正-why)
15. [R82 行尾量測面訂正 WHY](#r82-行尾量測面訂正-why)
16. [R82 shebang×CRLF 判準 WHY](#r82-shebangcrlf-判準-why)
17. [naive 本地時間戳判準 WHY](#naive-本地時間戳判準-why)
18. [PowerShell 站點級判準 WHY](#powershell-站點級判準-why)
19. [鐵律三無機械物證偽判準 WHY](#鐵律三無機械物證偽判準-why)
20. [R81 包 G 路徑列舉排序鍵判準 WHY](#r81-包-g-路徑列舉排序鍵判準-why)

**R107 追加**（帳本結案包 #3，DEF-200-166／171 落地的抵銷窗口；自本批起本文件也承載
`test_adr_xplat001_c1c2_lock.py` 的逐輪敘事——同一道棘輪、同一個結構性理由）：

21. [站點級守衛四種罩法 WHY](#站點級守衛四種罩法-why)
22. [外部執行檔 argv[0] transitive WHY](#外部執行檔-argv0-transitive-why)
23. [作用域級存量債表沿革](#作用域級存量債表沿革)
24. [DEF-200-208 一次性例外名冊 WHY](#def-200-208-一次性例外名冊-why)
25. [到期義務兌現沿革](#到期義務兌現沿革)
26. [凍結基準不由 git 導出 WHY](#凍結基準不由-git-導出-why)
27. [淨減法到期斷言訂正 WHY](#淨減法到期斷言訂正-why)
28. [SC-2/3/5 射程收窄 WHY](#sc-235-射程收窄-why)

**R109 追加**（Gap C：ONBOARDING §7 表② 指紋檢查接進 dev_start [6/7]；`tools/dev_start.py`
是 SPECIAL_FILES raw-line 棘輪＝同一道「行數只准往下」的機械物，接線新增行以本節搬遷抵銷）：

29. [dev_start 史料搬遷](#dev_start-史料搬遷)

---

## `_scan_roots` 三處修正 WHY

（原住 `_scan_roots()` 的 docstring 內；`test_platform_neutral_paths.py` 現行版本只留
函式簽名附近的精簡摘要並指回本節）

per-tree 下限（R12 SD 一審 SD-3）：全域總數下限對「單樹靜默縮面」不敏感
（如 LATEST 樹 rglob 被改 glob，總數 377→303 仍過全域 200）；逐樹釘選使任一
樹縮面必紅。

🔴 本輪三處修正（缺陷本體＝**同一份知識住兩個家、只有一個家被修好**）：

① **掃描面對稱化**。與姊妹鎖 `test_subprocess_encoding_hygiene._scan_roots()`
逐檔對拍，本清單此前少看 44 支 active `.py`，而缺口**正好蓋住整層 hook**
（`AutoClaude/tools/hooks/` 6 支＋LATEST `.claude/hooks/` 5 支）——hook 是本
repo 唯一「會主動阻斷使用者操作」的一層，指路錯誤代價最高。兩個成因並存：
`AutoClaude/tools` 一邊 flat glob 一邊 rglob；本清單少了 4 棵樹。修法＝改
recursive ＋ 補齊 4 棵樹 ＋ 補 `_scan_single_files()`；對稱性此後由
`TestScanSurfaceParityWithSisterLock` 機械看守（擴一邊沒擴另一邊即紅）。
落地當回合實測：缺口內的存量債對本檔五道判準**全為 0**，屬零成本擴面。

② **下限改雙邊帶**。原下限是單邊的（只有 `assertGreaterEqual`），而單邊下限
必然腐化：樹會長大、下限不會。落地當回合實測 `tools/tests` floor=10／
actual=56 ⇒ **可靜默蒸發 82% 掃描面而全綠**，比姊妹鎖當初立案的 78% 更差。
姊妹鎖已把藥開好（`repin_ceiling`／`suggested_floor`／`tree_count_verdict`
三支純函式），本檔改為直接 import 那三支，兩鎖共用同一組上下界。
🔴 下限值一律＝**落地當回合實測 × 0.95**（`suggested_floor()`），不再是
「首掃數打八折」那種化石；實測值隨行註記於各列。

③ **一律遞迴**（落地當回合被上面那道對稱鎖自己抓到的第三個病灶）：本清單原本
混用 flat／rglob，而 flat 的那幾棵對「有人在樹下新開一個子目錄」結構性隱形
——並行包當回合新增的 `tools/probe/` 就是這樣落在射程外。巢狀樹（如
`tools/tests` 住在 `tools` 底下）仍各自保有自己的下限，由 `_scan_units()`
的**最長前綴認領**分帳，不會被外層重複計算。

🔴 **下方刻意不逐列寫「實測 N」**：那等於在每一列旁邊放一個沒有任何機械物看守的
量測快照（同 ADR-XPLAT-002 §8 表頭規則 3）。當回合實際發生過：兩列的隨行實測值在
寫下後幾分鐘內就被並行包改動的樹弄過期。下限本身受雙邊帶看守，實測值由失敗訊息
當場印出——那才是唯一不會腐化的取值面。

---

## R60 round 3 tmpdir 判準 WHY

```
══════════════════════════════════════════════════════════════════════════════
R60 round 3 — 測試不得把「樹內固定路徑」當可寫暫存區（QA-R60R3-01／ARCH-R60R3-05）
══════════════════════════════════════════════════════════════════════════════
WHY（這是本檔第二道判準，與磁碟機假路徑正交，但同屬「測試原始碼的路徑寫法」家族，
故共用本檔的掃描根／豁免／stale 慣例，不另開新檔）：
  `tools/fsm_runtime/tests/test_slv_generator.py` 的四個測試類把暫存規則目錄寫死成
  `Path(__file__).resolve().parent / "_tmp_*"`——**tracked 樹內的共用固定路徑**，且
  `setUp` 清空它、`tearDown` `rmdir` 它。兩個行程同時跑（並行四方複審／並行閘門／
  CI 與地端同時跑）必互刪，產生與被測邏輯無關的假紅：
    · `FileNotFoundError: ..._tmp_rules\SLV-900.yaml.lock`（QA 實測，並行 2/2 重現）
    · `PermissionError: [WinError 32] ..._tmp_rules\SLV-900.yaml`（integration_gate 實測）
    · `FileNotFoundError: [WinError 2] ..._tmp_imm_rules\SLV-910.yaml.tmp`（ARCH 實測）
  隔離重跑必綠 ⇒ 長期被誤讀成 flaky。本鎖把「別再這樣寫」變成機械事實。
  修法慣例＝`tempfile.mkdtemp()`（根治：兩行程拿到不同目錄）；只加
  `unlink(missing_ok=True)` **不算**修好——那只讓競態不拋例外，資料仍互相污染。

判準（AST，非行級 regex）：對「寫入類呼叫」的目標表達式判斷它是否指向樹內固定路徑：
  寫入動作＝`.mkdir/.write_text/.write_bytes/.touch/.unlink/.rmdir`、
            `shutil.rmtree/copytree/move(<目標>)`、`open(<目標>, 'w'|'a'|'x'|'+')`。
  「樹內固定路徑」＝該表達式自身含 `__file__`，或其最左名稱是**模組層常數**／
  **同一個 class 內的 `self.<attr>`**，而該名稱曾被指派為含 `__file__` 的表達式。

🔴 刻意劃界（誠實記錄，勿超譯）：
  ❌ **函式區域變數不追**。這不是偷懶，是為了避開一個已知會誤報的形態：本鎖的原型
     掃描器做了跨作用域的別名傳遞，於是
     `tools/tests/test_git_hooks_install_common.py` 內同名的 `hooks_dir`（第 152 行是
     `_REPO_ROOT` 衍生，第 45／176 行卻是 tempdir 衍生）被整支污染成假陽性。同型病灶
     在本 repo 已有前科（R46 `build_alias_map` 的函式→ClassDef 作用域碰撞）。
     模組常數與 `self.<attr>` 兩種形態就足以涵蓋本缺陷家族的全部已知站點。
  ❌ 路徑「當引數交給生產碼、由生產碼去寫」的形態不追（如 `rules_dir=self.tmp`）——
     靜態無法判定被呼叫端是否真的寫入；實掃證實 `project_root=FIXTURE_ROOT`
     （multimodal_validator，全檔零寫入）正是這種唯讀傳遞，追了就是假陽性。
     本缺陷家族在此形態下仍會被 `.mkdir()` 那一半抓到，鑑別力不因此喪失。
  ❌ `str.replace` 等與 `Path` 同名的方法刻意不納入寫入動作集合（實掃三處皆假陽性）。
  ❌ **凍結版 v0.02~v0.29 不在掃描面**（見 `_tmpdir_scan_roots` 的 WHY）——那 95 個
     同型站點確實存在且**未修**，是待裁決項，不是本鎖宣稱乾淨的區域。
```

---

## R69 反方向 POSIX 絕對路徑判準 WHY

```
══════════════════════════════════════════════════════════════════════════════
R69 — 反方向：測試不得拿 POSIX 絕對路徑字面值去斷言 Path 產物
══════════════════════════════════════════════════════════════════════════════
WHY（本檔第三道判準；與第一道判準是**同一個病的兩個方向**）：
  第一道守「Windows 磁碟機字面值 → Mac 假紅」，但反方向此前**零守門**：
  `tools/tests/test_dev_start.py:2959` 寫
      self.assertIn("/elsewhere", printed)
  而 `printed` 的來源是生產碼把一個 `Path` 內插進訊息字串。`Path` 的 `str()`
  在 Windows 是 `\elsewhere\AutoClaude\…`，POSIX 字面值必然落空 →
  **Mac/Linux 全綠、windows-compat-ci 假紅**（R68 `375f291` 實紅，run 30720156050；
  同 commit 前一版 `24c5f34` 為 success，故確定是新增測試帶進來的病，不是環境）。
  本輪本機無 Windows 真機 ⇒ 這種病只能靠雲端 CI 才發現，一次來回數十分鐘；本鎖把它
  拉到 macOS 本機的 `python tools/run_root_unittests.py` 就抓到。
  修法慣例＝把字面值換成 `str(Path(<同一個字面值常數>))`（兩平台各自正規化後比對，
  斷言強度不降反升——鎖的是**整條路徑**而非片段），或改用 `PurePosixPath`／
  `as_posix()` 明示語意。

判準（AST）：`*.assert*(…)` 呼叫的引數（含 keyword 值、含巢狀於 list/tuple/set/dict
  內的元素）出現 **POSIX 絕對路徑字面值**（以單一 `/` 開頭、次字元非 `/` 非空白）。

🔴 刻意劃界（誠實記錄，勿超譯 — 沿用本檔既有慣例）：
  ❌ **不做值流分析**。「比對對象是不是 Path 產物」靜態不可判定：病灶站點的
     `printed` 是由 helper method 回傳的區域變數，任何合理的 Path-來源推導都追不到它
     （實測：以「名稱曾被指派為含 Path(/resolve()/os.fspath 的運算式」為條件時，
     本病灶站點**漏抓**）。故採「assert 家族引數出現 POSIX 絕對路徑字面值」這個
     過寬近似——代價由下面兩條劃界壓到實測零誤報。
  ❌ **pytest 裸 `assert` 形態不在射程**。實測四棵樹裸 assert 命中 44 筆，絕大多數
     不是路徑（`/compact` 是 Claude Code slash 指令、`/T` `/F` `/PID` 是 tasklist 欄位、
     `/api/config/schema` 是 URL path、`/tmp/x.yaml` 是從未 Path 化的假字串）。納入
     即等於一上線就要開 40 餘筆白名單——那會讓本鎖淪為永久白名單，反而失去鑑別力。
     unittest 形態涵蓋四棵樹的實際病灶家族（實掃：修前 1 筆＝真陽性、修後 0 筆）。
  ❌ **f-string 片段不算字面值**。`f"{parent}/archive/（小寫）復活了"` 這種訊息文字
     被 AST 拆成 Constant，形狀與路徑字面值無法區分（實測 2 筆皆為訊息文字誤報）；
     JoinedStr 內的 Constant 一律不計。
```

---

## R69 mock.call repr 判準 WHY

```
══════════════════════════════════════════════════════════════════════════════
R69 — 第三道判準的姊妹：不得用 `mock.call` 物件的 repr 拼裝輸出再拿去斷言
══════════════════════════════════════════════════════════════════════════════
WHY（與上一道判準是**同一個病的另一個入口**）：
  上一道守「斷言側寫死 POSIX 字面值」，但病也可以從**被斷言的那一側**進來：
      printed = " ".join(str(c) for c in fake_print.call_args_list)   # ← c 是 mock.call
  `str(mock.call(x))` 走的是 `repr`，於是字串裡的反斜線被轉義成 `\\`、換行變成
  `\n` 兩個字元。Windows 上生產碼印出的 `Path` 是 `\elsewhere\AutoClaude\…`，
  拼進 repr 後變成 `\\elsewhere\\AutoClaude\\…` ⇒ 任何對路徑（或多行文案）的
  `assertIn` 在 Windows 必然落空、Mac/Linux 全綠。實測（R69）：
      str(mock.call(r"…\elsewhere\AutoClaude\…"))
        → call('… \\elsewhere\\AutoClaude\\…')      ← 斷言 False
      " ".join(str(a) for a in c.args)
        → … \elsewhere\AutoClaude\…                 ← 斷言 True
  A1 只修了 `test_dev_start.py` 的一處，姊妹站點（同檔 2656、
  `AutoClaude/tests/test_perception.py` 三處）仍是舊寫法且零守門 ⇒ 本判準補上。
  修法慣例：`str(a) for c in <mock>.call_args_list for a in c.args`（取實際引數）。

判準（AST）：迭代 `*.call_args_list` / `*.mock_calls` / `*.await_args_list` 的
  comprehension 或 for 迴圈，其迴圈變數（`mock.call` 物件）被 `str()`／`repr()`／
  f-string 內插**整個物件**。取 `.args` / `.kwargs` / `.args[0]` 的形態不在射程
  （那正是修法本身）。

🔴 刻意劃界（誠實記錄）：
  ❌ 不追「先把 call_args_list 指派給區域變數、再於另一處迭代」的跨陳述式形態
     —— 那需要值流分析（同上一道判準的劃界理由）。實掃四棵樹＋生產碼樹此形態 0 筆，
     納入的成本大於收益；哪天出現，靠 windows-compat-ci 兜底。
  ❌ 不追 `assertIn(x, str(mock_obj.mock_calls))` 這種「整個 list 直接 repr」形態
     —— 實掃 0 筆；同理留給 CI 兜底。射程若擴大，請同步改本區段測試。
```

---

## R69 P1 Path 識別鍵判準 WHY

```
══════════════════════════════════════════════════════════════════════════════
R69 P1 — 第四道判準：Path 的平台相依字串化不得當「識別鍵／比對值」
══════════════════════════════════════════════════════════════════════════════
WHY（本判準是為了補上第三道判準結構性抓不到的洞——那個洞正好放走了一個 P1）：
  `tools/tests/test_dev_start.py` 的 `_scoped_sources()` 曾寫
      out[str(path.relative_to(_TOOLS_DIR.parent))] = src        # ← 產出側
      ...
      self.assertIn("tools/dev_start.py", scoped)                 # ← 斷言側
      self.assertNotIn("tools/lib/ci_liveness.py", scoped)        # ← 斷言側
  `str(PurePath)` 在 Windows 渲染成 `tools\dev_start.py`。於是 Windows 上：
    · `assertIn` 必然落空 ⇒ **windows-compat-ci 再度轉紅**（Mac/Linux 全綠）；
    · `assertNotIn` 更糟——它**恆真通過**，而它正是「ci_liveness 不得進入
      下限版 prelude 射程」那道鎖本身 ⇒ Windows 側整條變成**假鎖**。
  實測重現（ntpath 語意注入真實測試類）：
      AssertionError: 'tools/dev_start.py' not found in
      {'tools\\bootstrap_core.py': ...}
  第三道判準抓不到它，原因是**結構性**的：它的正則要求字面值以 `/` 開頭，
  而這裡的字面值是**相對路徑**（`tools/dev_start.py`）。

為什麼不是把第三道判準的正則放寬到相對路徑就好：
  相對路徑形狀的字面值在四棵測試樹＋生產碼樹極為普遍（`docs/04_planning`、
  URL path、套件名 `a/b`…），過寬近似在此形態下會爆量誤報。故本判準改採
  **窄化條件**：必須有「語法上可判定的 Path 產物」在場。分兩個入口：

  (4a) 產出側：`str(<Path 產物>)` 被當成**識別鍵**——dict 下標／dict/set 字面值
       或推導式的鍵／`.add(...)`。這正是上面病灶的**源頭**那一行。修法＝
       `.as_posix()`（或 `PurePosixPath`），兩平台同鍵。
  (4b) 斷言側：同一個斷言（**含 pytest 裸 `assert`**）裡同時出現「路徑形狀字面值
       （絕對或相對）」與「語法可見的 Path 產物」。修法＝`as_posix()` 或
       `str(Path(<同一字面值>))`。

🔴 刻意劃界（誠實記錄，勿超譯）：
  ❌ **4b 仍不做值流分析**。上面病灶的斷言側（`assertIn("tools/dev_start.py",
     scoped)`）中 `scoped` 的 Path 血統藏在 helper method 裡，4b **抓不到它**；
     該站點是由 4a 從產出側抓住的。兩個入口互補，但都不宣稱涵蓋「Path 血統
     隔了任意層呼叫」的形態——那需要跨程序值流，本檔一貫不做。
  ❌ **`PurePosixPath`／`PosixPath`／`PureWindowsPath` 產物不算違規**（顯式平台
     語意，對齊本檔第一道判準的 `_EXPLICIT_PLATFORM` 慣例）。實掃唯一因此排除的
     站點：`test_windowsapps_guard_bash_parity.py` 的
     `str(PurePosixPath(rel).parent)`——恆為正斜線，本來就中立。
  ❌ **`list.append(str(<Path>))` 不算識別鍵**（識別鍵＝下標／dict-set 鍵／`.add`）。
     實掃全庫此形態 3 筆，皆只流向失敗訊息文字或與 `[]` 比對（`dev_start.py:812`
     清理報告、`test_sanitize_component_frozen_sdd_versions_lock.py` 兩處、
     `hub_sync.py:517` 鏡像檔清單），**下游無正斜線字面值斷言** ⇒ 今日無分歧，
     故不納入以免把「顯示用字串」也一併判違規。若哪天有人拿它去比對字面值，
     4b 會從斷言側接住（前提是 Path 血統在同句可見）。
  ❌ **路徑建構子的引數不算「比對值」**（`Path("/nonexistent/a.png")`）。pathlib
     會正規化輸入，那是路徑**輸入**不是平台相依**輸出**；不排除的話
     `test_multimodal_validator.py` 的兩筆立刻變誤報（實測）。

📏 「擴到 pytest 裸 assert」的實測取捨（終審 P2 #7 指名項；此處誠實劃界）：
  十一棵掃描根共 **9705** 個裸 `assert`。若把第三道判準（過寬近似）直接套上去，
  命中 **41** 筆，逐筆親讀後**全部是噪音**（`/compact` slash 指令、`/T` `/F` `/PID`
  tasklist 旗標、`/api/config/schema` URL、`/tmp/x.yaml` 從未 Path 化的假字串）
  ⇒ 一上線就得開 41 筆白名單，鎖即淪為白名單，故**維持不擴**。
  改以本判準的窄化條件（同句 Path 產物在場）套用裸 assert：實測命中 **0** 筆
  ⇒ 零存量債、零誤報的擴面。**結論**：裸 assert 自此在射程內，但只在「Path 產物
  語法可見」時；「純字面值 vs 不可見血統」的裸 assert 仍在射程外，靠
  windows-compat-ci 兜底。宣稱到此為止，不多一分。
```

---

## R74 PATHEXT 平台守衛判準 WHY

```
══════════════════════════════════════════════════════════════════════════════
R74 — 第五道判準：平台專屬環境變數的讀取必須帶平台守衛（PKG-4 C）
══════════════════════════════════════════════════════════════════════════════
WHY（本檔第五道判準；與前四道同屬「跨平台寫法」家族，故沿用本檔的掃描根／豁免／
stale 慣例，不另開新檔——護欄層棘輪 `TestGuardLayerRatchet` 要求新鎖併入既有檔；
🔴 R78 ARCH-03 訂正：R74 當時它量的是檔數，R77 起改量逐檔行數的**淨額**）：
  `DEF-101-766` 的病灶是 `WindowsAppsGuard.ps1::Resolve-NativeExecutable` **無條件**
  照 `$env:PATHEXT` 過濾候選——PATHEXT 是 Windows-only 概念，PS Core 跑在
  macOS/Linux 上該變數不存在、POSIX 執行檔又不帶副檔名 ⇒ 每個候選都被淘汰 ⇒
  函式恆回 `$null` ⇒ macos-compat-ci 與 root-infra-ci(ubuntu) 必紅。

  🔴 R74 要治的不是那個缺陷（R71 已修），而是**它的鎖只圈一個站點**：修復當時建的鎖
  （`tools/tests/test_dev_start.py::TestResolveNativeExecutable*`）綁死在那一支
  `.ps1` 的那一個函式上——換一支檔案、換一種語言（Python 的
  `os.environ["PATHEXT"]`）寫同一個缺陷，全 repo 零掃描。這是 `DEF-101-757`／
  `DEF-101-777` 判過的同一件事（已知的鎖射程缺口不得只以劃界結案），而本 repo 已經
  為它付過三次代價。故本判準改成**形態掃描**：不問「哪一支檔案」，只問
  「這一處讀 PATHEXT 的程式碼，有沒有先確認自己在 Windows 上」。

判準（逐行文字，射程含 `.py`／`.ps1`／`.psm1`／`.sh`）：
  讀取形態＝`$env:PATHEXT`（PowerShell）／`PATHEXT` 出現在 `os.environ`、`getenv`
  同一行（Python）／`$PATHEXT`（shell）。
  「有守衛」＝同一個檔案內、該行**之前**出現過平台守衛述詞（見 `_PLATFORM_GUARDS`）。

🔴 刻意劃界（誠實記錄，勿超譯）：
  ❌ **只看「之前出現過」，不做控制流分析**。靜態判不出守衛是否真的支配該行（R71 的
     `DEF-101-766` 正是「守衛存在但排在過濾之後」）。那一半由既有的**順序鎖**
     （`test_dev_start.py::TestResolveNativeExecutableShortCircuitOrder`）承接——
     兩道鎖的射程刻意不同：本鎖問「有沒有」（廣、全庫），順序鎖問「排對了沒」
     （窄、逐站點）。把兩者混成一道會兩頭都做不好。
  ❌ **註解與 docstring 內提到 PATHEXT 不算讀取**（本 repo 有大量在地 WHY 逐字提到
     它）。做法＝掃描前先剝行尾 `#` 之後的部分（heuristic，沿用本檔第一道判準
     `_scan_file` 的既有取捨：不解析字串內的 `#`，代價是「字串內含 `#` 且其後才出現
     讀取語法」會漏掃）。判準另要求出現**真正的讀取語法**，不只是出現這個字。
  ❌ **注入／設定（`mock.patch.dict(os.environ, {"PATHEXT": …})`）不算讀取**。
     實測本 repo 有這種站點（`tools/tests/test_bash_probe_spec_contract.py`），
     它是在替被測碼**佈置**環境，本身不依賴本機平台。故 Python 側的形態刻意寫得窄
     （下標／`.get`／`in`／`getenv` 四種真讀取），不用「同一行出現 os.environ」這種
     寬判準——寬判準製造的假紅會逼下一輪的人把整條鎖關掉。
```

---

## R76 文字編碼判準 WHY

```
══════════════════════════════════════════════════════════════════════════════
R76 — 第七道判準：文字讀寫必須指名 encoding（PKG-E 標的三；R76-09）
══════════════════════════════════════════════════════════════════════════════
WHY（沿用本檔的掃描根／標記／stale 慣例，不另開新檔——護欄層棘輪
`TestGuardLayerRatchet` 要求新增鎖併入既有檔；🔴 R78 ARCH-03 訂正：R76 當時它量的是
檔數，R77 起改量逐檔行數的**淨額**，新增檔案本身不違規）：
  `Path.read_text()`／`write_text()`／`open()` 不帶 `encoding=` 時，用的是**本機
  locale 預設編碼**。mac 上那是 UTF-8，所以在 mac 寫、在 mac 跑，永遠是綠的；
  同一行程式碼在 zh-TW Windows 上是 cp950，讀到任何非 Big5 字元就 `UnicodeDecodeError`。
  這是「mac→Windows 落差」最典型的一整類缺陷，而 R76 掃描實測它**零靜態掃描器**。

🔴 更麻煩的是它連**執行期**都看不見：根 `.claude/settings.json` 設了 `PYTHONUTF8=1`，
  於是 agent 驅動的開發迴圈裡每一支 python 都跑在 UTF-8 模式下、這類缺陷在本機一次
  都不會現形（而另有一道鎖在強制那個值存在）。把區分本機與雲端的變數全域正規化掉，
  結果就是**唯一能看見它的環境被關掉了** ⇒ 只剩靜態判準這一條路。

判準（AST，非逐行文字）：
  · `<expr>.read_text(...)`／`<expr>.write_text(...)` — 恆為文字 I/O，必須有 encoding。
  · `open(...)`（builtin 形態）與 `<expr>.open(...)`（pathlib 形態）— mode 帶 `b`
    即二進位，出射程；其餘要求 encoding。
  · encoding 可以是關鍵字，也可以是**位置引數**（四種呼叫形態的位置各不相同，見
    `_ENC_POS`）——只認關鍵字會對合法寫法製造假紅。
  · 行尾 `<標記> <WHY>` 豁免（標記字串見 `_ENCODING_OK_MARKER`）＋ stale 自檢：
    標記在而違規不在（或 WHY 留空）即紅，防清單腐化。

🔴 刻意劃界（誠實記錄，勿超譯）：
  ❌ **mode 是非字面值運算式時出射程**（`open(p, mode_var)`）——靜態判不出它是不是
     二進位，硬判會製造假紅。實測本 repo 現況零此形態；這是**已知可繞道**，不是沒想到。
  ❌ **`**kwargs` 轉發視為已帶 encoding**（同樣判不出來，且該形態通常是包裝函式）。
  ❌ **非 pathlib 的 `.open(`**（`os.open` 連 encoding 參數都沒有、`gzip`/`tarfile`/
     `zipfile` 預設二進位）由 `_NON_TEXT_OPEN_OWNERS` 排除。R76 落地前實測：不排除
     的話光 `os.open` 就製造 5 筆假紅，而寬判準製造的假紅會逼下一輪把整條鎖關掉
     （同第五道判準對 `mock.patch.dict` 的取捨）。
  ❌ **`errors=` 不在本判準射程內**（那是另一個軸，不混進來）。

🔴 標記字串為何取專屬主題名（值見程式碼常數；本節刻意不逐字寫出它——寫出來就會被
  自己的取標記函式當成一個真標記而判 stale，同 `_encoding_markers` docstring 的理由）：
  R76 落地首版與 `tools/tests/test_subprocess_encoding_hygiene.py`
  的判準一 `_OK_MARKER` **逐字相同**，而兩支掃描器的掃描面是包含關係（本判準 810 檔
  全在對方 854 檔之內）⇒ 任一方的**合法**豁免會在另一方變成一筆 `標記 stale` 紅，
  而那筆紅的訊息還寫著「該行無被壓下的違規」（對他那一行是誤導）。兩支的錯誤訊息都
  主動教人加這個標記，所以第一個照做的人就會踩到。這正是本輪 PKG-0 在拆的「兩道鎖的
  合法動作互為對方違規」死結，不可在同一輪又造一個。命名比照同檔既有的
  `_PATHEXT_OK_MARKER`／`_TMPDIR_OK_MARKER`：**每道判準取專屬主題名**。
  另：比對改用邊界正則（同姊妹檔 `_marker_lines`），裸子字串比對是縱深防禦缺的那一層
  ——未來若再出現含本標記為子字串的第三個標記，改名這一層就擋不住了。
```

---

## R76 複審 ARCH-01 標記互斥 WHY

```
══════════════════════════════════════════════════════════════════════════════
R76 複審 ARCH-01：豁免標記**不得跨判準互相認領**（本輪自造死結的根治面）
══════════════════════════════════════════════════════════════════════════════
缺陷本體（實測重現，非理論）：新落地的 file-IO 判準，其標記字串與
`test_subprocess_encoding_hygiene.py` 判準一的 `_OK_MARKER` **逐字相同**（值不在此
逐字引述，理由見上一節），而兩者掃描面是包含關係 ⇒ 一個**合法**的 subprocess
豁免會在 file-IO 這邊多出一筆 `標記 stale`，反向亦然。兩支的錯誤訊息都主動教人加該
標記，所以第一個照訊息辦事的人就會撞上一筆指著自己剛加的合法豁免的紅——正是本輪
PKG-0 在拆的那種死結。

這道鎖守的是**根因而非個案**：全庫每一個「行尾 `<slug>-ok:` 豁免標記」常數都必須
是各判準專屬的，且彼此不得互相認領。姊妹檔已有一支同型鎖
（`test_the_two_criteria_markers_do_not_claim_each_other`），但它只驗自己那兩個，
對**跨檔**碰撞零射程——那個縫就是這次逃出去的地方。
```

---

## 第六道判準（平台專屬 API 守衛）WHY

```
══════════════════════════════════════════════════════════════════════════════
本輪 — 第六道判準：對面平台專屬 API 必須帶平台守衛
══════════════════════════════════════════════════════════════════════════════
缺陷本體（雙向注入實測，注入點固定為**生產碼**路徑而非測試樹，R68-34 判例）：
  方向 mac→Windows 的 10 題語料，被本 repo 全部靜態判準攔下的是 **0 題**；
  方向 Windows→mac 的 12 題，攔下 5 題（扣掉順帶命中只有 4 題）。也就是
  「在 mac 上寫出只有 POSIX 成立的程式碼」這一整類，本機四關全部放行，唯一的
  發現通道是雲端 windows-compat-ci——而雲端額度正好停擺。

判準只問兩個問題（刻意窄，寬判準製造的假紅會逼下一輪把整條鎖關掉）：
  ① 這個 symbol 是不是單平台專屬？（下方三張白名單，**不含**跨平台但語意不同的
     `os.chmod`／`os.stat` 那類——落地當回合實測 `os.chmod` 帶執行位的站點有 9 個
     合法用法在 `tools/tests`，納入即上線全紅，正是本 repo 判過的「永紅的閘門會被
     整個關掉」形態）；
  ② 它之前有沒有平台守衛？**直接複用**第五道判準已驗紅綠的 `_PLATFORM_GUARDS`
     與「守衛必須排在讀取之前」那條順序判準，不另立一套。
     另接受 `hasattr(os, "<名字>")` 這種明示能力探測——那正是修法慣例，判準不能
     反過來懲罰它。

🔴 刻意劃界（勿超譯）：判準是 **AST** 的，故註解與 docstring 內提到這些名字不算
  使用（落地當回合先寫過一版行掃描，實測 68 筆命中裡絕大多數是 docstring 舉例）；
  也**不做值流分析**——`getattr(os, "fork")()` 這種動態取用抓不到。
  字面值類（`/tmp` 硬編、`"/" `串接、`.exe` 後綴假設）**不在本判準內**，理由是
  實測存量 52 筆且多為測試 fixture 的不透明字串；它們在下方注入語料矩陣裡以
  `caught=False` 逐題記帳，於是「還沒被守住的是哪幾類」是可查的量測值而非散文。
```

---

## R79 工作樹行尾閘 WHY

```
══════════════════════════════════════════════════════════════════════════════
R79（D-ps1eol）— **工作樹**行尾閘：`.ps1` 必為 CRLF、`.sh` 必為 LF
══════════════════════════════════════════════════════════════════════════════
缺陷本體：`.ps1` 要 CRLF 這件事在三處被宣告（`.gitattributes` 的
`*.ps1 text eol=crlf`、`.editorconfig`、`root-infra-ci.yml` 第 4 道 EOL 閘），
**寫入端零強制**——而 R79 已把寫入者溯源到 Claude Code 的 `Write` 工具（新建與
覆寫既有 CRLF 檔都吐 LF）。R79 已為此把 PostToolUse 的 `check_ps1_encoding.py`
擴成位元組正規化器（BOM ＋ CRLF），但 hook 只罩得住「經由工具寫入」這一條路：
人工編輯器、GitHub web、外部腳本一律繞得過，所以必須另有一道**事後**閘。

🔴 方向不可照抄 `.sh` 那一道：`tools/git-hooks/pre-commit` 對 `.sh` 看的是
  **blob**（index 內容），而 `.ps1` 因 `eol=crlf` 的 checkin 正規化，其 blob
  **恆為 LF** ⇒ blob 判準對 `.ps1` 結構上恆綠。本閘因此讀 `git ls-files --eol`
  的 `w/`（working tree）欄。同一個理由讓 CI 也看不見這件事：`actions/checkout`
  必定重新 smudge，雲端的工作樹結構上永遠合規（R78 逐項實查的結論）。

為何連 `.sh` 一起看（射程刻意對稱）：`.sh` 方向今天乾淨，但乾淨的原因是三重
覆蓋裡沒有一層在看工作樹——CRLF `.sh` 一旦被 `git add` 前的人工編輯造出來，
本機同樣沒有訊號。一個判準覆蓋兩個方向，比兩個各自半殘的判準便宜。
🔴 R79 四方複審（SD nonblocking）訂正：本表原是一份**手抄**的副檔名→行尾映射，
  也就是 `.gitattributes` 的第二個家——而它在落地當下就已經不完整（漏了同樣宣告
  `eol=crlf` 的 `.cmd`／`.bat`）。字面表天生看不出「漏了什麼」，因為漏掉的那一格
  在表裡不存在，任何只讀表的判準都掃不到它。改法不是補兩格，是**讓表變成量測值**：
  下面的映射從 `.gitattributes` 現查產生，`.gitattributes` 因此維持唯一真相源。
```

---

## R79 Windows 目錄項原語 WHY

```
══════════════════════════════════════════════════════════════════════════════
R79（S-xplat）— 「別人開著這個檔」在 Windows 會炸掉的**目錄項原語**
══════════════════════════════════════════════════════════════════════════════
缺陷本體：本 repo 已經正確登記了「Windows 刪不掉被開著的檔」，卻把它記成一條
關於 `unlink` 的知識，而不是一條關於「任何會改動目錄項的原語」的知識。換一個
原語就整片失明——**連錯誤碼都換了**。當回合在本機實測（三個案例同一支探針）：
    os.replace 覆寫「被純讀者開著」的目的檔 → PermissionError winerror=5
    同一組但目的檔已關閉                    → OK
    os.unlink 一個被開著的檔                → PermissionError winerror=32
POSIX 上前者恆成功 ⇒ 這是一個只在 Windows、只在並行時發生、且不留痕跡的落差。
本 repo 的常態作業型態正是它的觸發條件（多 agent 共用一棵工作樹，CONTEXT-LEDGER
與 trajectory/drift 那幾份 YAML 同時被多方讀寫）。

🔴 誠實劃界（這一節買到的是什麼、買不到什麼）：
  · 買到：新增一個**未處置** `PermissionError/OSError` 的目錄項原語站點會轉紅。
  · 買不到：「捕了但吞掉」不算修好——`context_ledger_pre.py` 外層那個
    `except Exception` 會把它吞成靜默漏記（token 帳目變少，沒有人覺得不對）。
    靜態判準看得到「有沒有處置」，看不到「處置得對不對」。
  · 不代改：現存站點全在 `AISDLC_SDD/**`（Copy-on-Evolve 禁改凍結版；LATEST 的
    那批也不在 R79 XPLAT 包的檔案所有權內），故本輪只誠實登記、逐筆可查。
```

---

## R79 exec bit 索引模式判準 WHY

```
══════════════════════════════════════════════════════════════════════════════
R79（S-xplat）— exec bit：Windows 上唯一還看得見的那個管道＝**git 索引模式**
══════════════════════════════════════════════════════════════════════════════
缺陷本體（兩半，同源）：
 ① 索引模式在 Windows 上「不是沒人查，是 git 自己被設定成不看」——本機實測
    `core.filemode=false`，於是檔案模式從不出現在 `git status`／`git diff`／任何
    pre-commit 掃描裡。27,544 支 tracked 檔只有 7 支是 100755，而框架**給外部
    使用者的第一條指令**（30 個版本樹的 `tools/README.md`「方法 3 → Mac / Linux」）
    教人裸跑 `./…/init_project.sh`，該檔索引模式是 100644 ⇒ mac/Linux 使用者
    一 clone 就死在第一步（POSIX execve 對非 x 檔回 EACCES，shell 回 rc=126）。
    緊接的 Windows 欄用 `.\init_project.ps1` 照樣能跑 ⇒ 這份文件在 Windows 上
    永遠讀起來是對的。**製造端與觀測端都在 Windows，受害端只在 mac/Linux。**
 ② Windows 側那條 exec bit 治理鏈（`tools/git-hooks/post-commit` 的 `[ -x ]`
    守衛、它的回歸鎖、macos-compat-ci 的 `test -x`）**一格覆蓋都沒有**。當回合
    在 Git Bash（MINGW64）實測，比原判詞更糟：
        with_shebang.sh  [ -x ]=EXECUTABLE  ls=-rwxr-xr-x
        no_shebang.sh    [ -x ]=NOT-EXEC    ls=-rw-r--r--
        bom_shebang.sh   [ -x ]=NOT-EXEC    ls=-rw-r--r--   ← 檔首多 3 個位元組就翻
        no_shebang.sh 加 `chmod +x` 之後 → 仍然 NOT-EXEC
    也就是說 `[ -x ]` 在這裡是**對檔首兩個位元組的內容猜測**，不是權限位元，
    而且 `chmod` 動不了它 ⇒ 「加執行權限」在 Windows 側是一個做不到的動作。
    反向失效（檔首多任何位元組 → dispatcher 靜默 exit 0）全 repo 零判準。

本判準因此**只讀 `git ls-files -s` 的索引模式**：那是 Windows 上唯一不受
`core.filemode` 影響、也不依賴檔案系統權限位元的觀測管道，同一支判準在三個
平台上都跑得動、都給同一個答案。
```

---

## 雙向注入語料矩陣 WHY

```
══════════════════════════════════════════════════════════════════════════════
本輪 — 雙向注入語料矩陣（M5 的可重跑載具；此前語料零落點、結構上不可逐輪比較）
══════════════════════════════════════════════════════════════════════════════
缺陷本體：M5「雙向注入攔截率」的量測配方寫著「每輪跑固定形制 N=10 注入矩陣」，
但語料本身**沒有任何落點**——每輪重新發明、量完就丟。R74 宣稱的六類基線全庫查無，
於是那個數字結構上不可跨輪比較（`DEF-101-018` 同型：不可重現的存量數字）。

本表把語料落成**字串常數**（不是檔案：違規樣本不留在樹裡）並逐題釘住「現在有沒有
被攔下」。兩個方向都會說話：
  · 某題由攔得到變成攔不到 ⇒ 判準退化，紅；
  · 某題由攔不到變成攔得到 ⇒ 有人補了判準，也紅，訊息要求把該題改成 True。
後者刻意不放行——「進步沒有被記錄」就是下一輪又要重新發明語料的起點。

🔴 注入點固定為**生產碼**路徑：R68-34 判過「只掃測試樹」的偏差，語料若掛在測試樹
  路徑上，量到的是一個比實況樂觀的數字。
```

---

## R80 鐵律三對照表訂正 WHY

```
══════════════════════════════════════════════════════════════════════════════
R80（包 B / S4）— 跨平台危害類：訂正兩筆假事實 ＋ 三個新家族上鎖
══════════════════════════════════════════════════════════════════════════════
本段一次處理四件同源的事，全部長在「鐵律三對照表」這個治理面上：

 ① **低報分子**（S4-01，判準在本檔最後一節）。表上「大小寫敏感度」列自陳無機械物，
    而 NTFS 大小寫碰撞判準 `tools/check_ntfs_paths.py` 的正規化鍵早就存在、且接在
    pre-commit 與四支 CI workflow 上。舊的覆蓋率棘輪只讀那張表本身，於是「表說沒有、
    實際有」這個方向**結構上失明**。

 ② **有鎖在守假話**（S4-02）。表上「行尾（`.py` 方向）」列自陳無機械物——不真。
    機械物在（`TestWorktreeEolMatchesPolicy`），只是被 `_EOL_LF_SCOPE` 這個常數窄化
    成只看 `.sh`／`.bash`，而且 `test_the_policy_follows_the_declaration_instead_of_a_copy`
    還有一條 `assertNotIn(".py", policy)` **釘死它必須放行**。這比沒有鎖更難看見：
    檔案在、判準在、測試全綠，只有讀完那個常數才知道 `.py` 從來不在射程裡。

 ③ **修法方向被規模否決**（S4-03）。全庫工作樹行尾與 `.gitattributes` 宣告不符者
    **18,255 支**（不是表上那個只講 `.py` 的 4,176），其中**絕大多數**落在
    Copy-on-Evolve 凍結面 ⇒「全部就地轉 LF」不是修法，是打破凍結政策。正解是把
    凍結面與活躍面**分開處置**：活躍面止血（新漂移必紅）、凍結面誠實登記為欠債。

 ④ 兩個此前零判準的新危害家族：**shebang ＋ 非 LF 行尾**（S4-08）與
    **naive 本地時間戳被持久化**（S4-07），加上 PowerShell 側的**站點級**判準
    （S4-04／S4-05）。三者共同的性質是「今天幾乎沒有存量，缺的是寫入面的門」。

🔴 本段所有數字都是**當回合實測**、不是常數：欠債釘子旁邊寫的就是那份實測，
   判準失效時失敗訊息會把現值印出來（同本檔 `_scan_roots()` 的既有慣例）。
```

---

## R82 行尾量測面訂正 WHY

```
── 共用：tracked 檔案的行尾三欄（現查一次）───────────────────────────────────
🔴 **R82 訂正本段最要緊的一件事：量測面選錯了平面**（本段三支判準在 mac 上同時必紅）。
原設計只量「本機工作樹的實際位元組」，並把某一台 Windows 機器上量到的 220／3956／30
直接寫成常數 ⇒ 換一棵樹（換平台、或同平台重新 clone）結構上就對不起來。

當回合在 mac 上以兩個受控 repo 實測（scratchpad，非本 repo），把兩件事分開了：
  探針 A｜blob 內就帶 CRLF（`i/crlf`）：`git clone` 出來的新樹**照樣是 CRLF**，
    連 `-c core.autocrlf=true` 的 clone 也一樣（`xxd` 首行逐字 `…python3 0d0a`）。
    ⇒ 這一半**會跨機器、跨平台傳染**；POSIX 上 shebang 檔就是 rc=127。
  探針 B｜blob 是 LF、只有工作樹被就地改成 CRLF（`i/lf w/crlf`）：`git status` 空白
    （結構上看不見），而全新 clone 拿到的是 **LF**（`…python3 0a`）。
    ⇒ 這一半**不傳染**，它是「這一棵 checkout 的歷史」，不是平台常數。
探針 B 的 `-c core.autocrlf=true` 對照組同時證偽了「Windows 就會這樣」：`.gitattributes`
對 `.py` 明文宣告 `eol=lf`，而明文宣告**勝過** `core.autocrlf` ⇒ 今天在 Windows 全新
clone 一樣拿到 LF。Windows 那台的四千支是**陳舊 checkout 殘留**（那些檔在
`.gitattributes` 宣告它們之前就已 checkout，git 不會因為屬性改變而重新 smudge），
把它寫成常數＝把一台機器的歷史寫成平台事實，與 `DEF-101-778` 同型。

⇒ 本段自 R82 起**分成兩個平面，各自有牙**（刻意不加 skip——skip 等於那個平台從此零
  覆蓋，而下面 ① 在兩個平台都真的在跑）：
  ① **blob（`i/` 欄）＝平台中立閘門**：blob 是 content-addressed，每台機器同一個值。
     零容忍、雙向精確，mac 與 Windows 讀到同一個答案 ⇒ 這才是「在 mac 開發不會給
     Windows 製造落差、反之亦然」真正要鎖的那一面。
  ② **工作樹（`w/` 欄）＝本機健康度**：機器狀態。判準改成「0（乾淨 checkout）或落在
     欠債帶內」——**0 在任何平台都達得到**，於是 mac 綠、Windows 帶著它的存量也綠，
     而任一側**新增**漂移都紅。上下界不再是「平台欄」，是「那台機器的存量上界」。
```

---

## R82 shebang×CRLF 判準 WHY

```
── ④-a shebang ⇒ 必須是 LF ──────────────────────────────────────────────────
缺陷本體：`#!/usr/bin/env python3` 加上 CRLF 行尾，POSIX kernel 會把 `\r` 一起當成
直譯器名的一部分 ⇒ `env: 'python3\r': No such file or directory`。本 repo 今天
**30 支 `.py` 已同時成立**（shebang ＋ CRLF），沒有炸掉純粹是因為它們的 git 索引模式
都不是 100755 ⇒ 沒有人真的去 `./x.py` 執行它。**那是偶然，不是設計**：
`TestExecBitIsGovernedViaTheGitIndex` 那一節記載的正是「文件教人裸跑、索引模式卻是
100644」這個家族——哪天有人把 exec bit 補對（那是**正確**的修法），這 30 支就會在
mac/Linux 上一起變成 rc=127，而修 exec bit 的人完全看不到行尾這一半。

🔴 判準刻意是**shebang × 行尾**的交集而不是各自一半：單看行尾，凍結面上萬支要判
（不可能）；單看 exec bit，今天零違規（已有鎖）。交集才是「一補另一半就炸」的那一組，
而它小到可以逐檔具名。

🔴 **R82 訂正本段的量測面**（同上方平面①／②的裁決，這裡是它的第二個消費者）：
上面那 30 支是**某一台機器的工作樹**上量到的，換一棵 checkout 就不成立（mac 上 0 支），
於是「雙向精確比對」這個原本正確的紀律，套在一個隨機器變的量上就變成必紅。分成兩層：
  ①-shebang｜**blob 側**（`shebang_blob_sites`）：零容忍、雙向精確、每台機器同值。
    這才是會傳染的那一半——blob 帶 CR 的 shebang 檔，clone 到哪台都是 rc=127。
  ②-shebang｜**工作樹側**（`shebang_non_lf_sites`）：機器狀態 ⇒ 改為**子集合**語意
    （不得多出登記外的站點；少掉不判，因為「少掉」在乾淨的樹上是常態而非成就）。
    子集合語意會讓清單腐爛，補救不是回頭用精確比對，而是
    `test_every_registered_debt_entry_still_has_a_platform_neutral_reason`：
    每一筆登記的**理由**必須仍然成立，而理由本身是機器中立的（仍是 tracked、
    仍宣告 eol=lf、首行仍是 shebang）。理由沒了就得刪，這樣清單不會靠慣性活著。
```

---

## naive 本地時間戳判準 WHY

```
── ④-b naive 本地時間戳被持久化 ─────────────────────────────────────────────
缺陷本體：`datetime.now()`（無 tz）產生的是**沒有 offset 的本地時間**，`.isoformat()`
之後寫進 checkpoint／YAML／JSON，讀回來再與另一個 naive `datetime.now()` 相減。那個
減法在**同一個 offset 內**是對的，跨 DST 切換就整整差一小時——而且是**靜默**的：
沒有例外、沒有 log，只是恢復時間錯一小時。AutoClaude Kernel 的 Token Guard 正是這個
形態（checkpoint 存 naive ISO、`auto_resume` 以 `resume_at - datetime.now()` 算還要等
幾秒）⇒ DST 那一天會**提早一小時**恢復。

🔴 為何本 repo 至今沒撞到：開發機時區是 Asia/Taipei（**不實施 DST**）。也就是說這個
缺陷在本機**結構上重現不了**——與 DEF-101-778「把一台機器的偶然事實寫成常數」同型，
只是這次的偶然事實是「我們的時區沒有夏令時間」。下面的自證測試因此**不動系統時區、
不動環境變數**，改以 `zoneinfo` 直接構造切換點：那是唯一在本機也跑得動、且對並行工作
包零副作用的重現方式。

判準（AST）：`datetime.now()`／`datetime.datetime.now()`／`utcnow()` **不帶任何引數**
且結果直接串 `.isoformat(...)` ⇒ 產出不帶 offset 的 ISO 字串。修法慣例＝
`datetime.now().astimezone().isoformat()`（帶上 offset，字串自我描述）或
`datetime.now(UTC).isoformat()`。

🔴 誠實劃界：
  ❌ 測試檔不判（路徑含 `tests` 段或檔名 `test_*.py`）：測試造時間戳當 fixture，不進
     持久層；納入會製造十餘筆需要逐一辯護的假紅。
  ❌ 「存了 naive 再讀回來相減」的**讀**側不判——靜態追不到跨檔案的值流。本判準守的是
     **產出端**，把不帶 offset 的字串擋在寫入之前；讀側今天由 `_NAIVE_TS_PERSIST_DEBT`
     的具名站點承接（每一筆都寫明它餵給誰）。
```

---

## PowerShell 站點級判準 WHY

```
── ④-c PowerShell 站點級：Windows 專屬 `$env:` 與 `bash` 解析 ────────────────
缺陷本體（S4-04）：`$env:TEMP`／`$env:TMP` 在 Windows 一定有值，在 macOS/Linux 的
PowerShell Core 上**不存在** ⇒ `Join-Path $env:TEMP '…'` 會直接
`Cannot bind argument to parameter 'Path' because it is null` 拋例外（不是回空字串、
不是走 fallback，是整支腳本當場死掉）。命中的站點裡有一支是
`AISDLC_SDD/<LATEST>/tools/init_project.ps1`——**框架發給使用者的安裝腳本**，也就是
別人第一次用這個框架跑的第一支程式。正解＝`[System.IO.Path]::GetTempPath()`
（.NET API，三平台皆回真值）。

缺陷本體（S4-05）：`Get-Command bash` 在本機解析到 `C:\WINDOWS\system32\bash.exe`
（WSL 佔位／真 WSL），repo 已為此立 SSOT `tools/lib/Find-GitBash.ps1`（含 system32
逐段排除）。今天**零違規**——所以這一格缺的不是存量掃描，是**站點級**的門：判準的
價值全部在「下一個人寫出裸解析時當場紅」，而不是在今天數出幾筆。

🔴 誠實劃界：
  ❌ 只判 `$env:TEMP`／`$env:TMP` 這**兩個**變數，不判整個 `$env:*`。理由是「粗數」
     本身就是這一格此前失真的原因：活躍 `.ps1` 剝註解後 `$env:` 粗抓 48 筆，其中
     22 筆是**賦值**（`$env:X = …` 是設定不是讀取，任何平台都成立），剩下 26 筆讀取
     分屬 11 個變數，而真正「在 POSIX 上會拋例外」的只有 TEMP／TMP 這一族。把 11 個
     變數一起判會製造 20 餘筆需要逐一辯護的假紅，那種鎖活不過一輪。
  ❌ 不判「這支腳本是不是 Windows 專用」——那件事沒有可靠的機械信號（檔名、路徑、
     檔頭措辭都可以繞過）。改以具名欠債逐檔寫明「它是不是真的只在 Windows 跑」，讓那個
     判斷是**寫下來的**而不是推斷出來的。
```

---

## 鐵律三無機械物證偽判準 WHY

```
══════════════════════════════════════════════════════════════════════════════
R80（包 B / S4-01）— 鐵律三對照表：「無機械物」必須是**可證偽**的宣稱
══════════════════════════════════════════════════════════════════════════════
缺陷本體：覆蓋率棘輪（`test_doc_loc_baseline_freshness_r60.py` 的鐵律三對帳鎖）的分子
只讀那張表**自己說**有沒有機械物。於是它抓得到「有人把機械物欄改回無機械物」（分子
下降），也抓得到「指名一支不存在／守錯主題的檔」（過報分子），**唯獨抓不到一格從一
開始就填錯**——「表說沒有、實際有」這個方向結構上失明。
實例：「大小寫敏感度」列自陳無機械物，而 `tools/check_ntfs_paths.py` 的大小寫碰撞
正規化鍵早就存在（NFC → lowercase；`README.MD` 與 `README.md` 在 NTFS 上互相覆蓋），
且接在 pre-commit 與四支 CI workflow 上。低報分子的代價與過報一樣大：它讓下一輪有人
「補一支已經存在的鎖」，也讓「還有幾類沒人守」這個治理數字是假的。

判準：每一列自陳「無機械物」者，必須登記一組**證偽探針**——一組 token，凡在機械物的
**已知住所**內出現於 `def`／`class` 定義行或模組層常數名，就是反證。命中落在「已審視
並判定不算」的檔案內時放行，但那個判定必須寫下來（考察軌跡本身就是產物）。

🔴 為何掃「定義名」而不是全文：全文比對對散文（註解裡順口提到主題）零抵抗力，而本檔
   與 CLAUDE.md 自己就滿是這些詞——那種鎖第一天就會被假紅淹掉然後被整道關掉。機械物是
   **被命名的東西**：它一定有 `def scan_*`／`class Test*`／`_DIRENT_UNGUARDED_DEBT`
   這種識別字。
   掃識別字是必要條件不是充分條件（抓得到「其實有人在守」，抓不到「守得很弱」），
   與本 repo 既有的實質判準同一種誠實度。
```

---

## R81 包 G 路徑列舉排序鍵判準 WHY

```
══════════════════════════════════════════════════════════════════════════════
R81（包 G）— 兩個「今天存量是 0／已清空、缺的是門」的跨平台危害類
══════════════════════════════════════════════════════════════════════════════
兩者共同性質：live 危害今天不存在，失明的方向卻一律是「本機恆綠、mac／fresh clone
恆紅（或更糟：靜默縮面）」。⇒ 本節交付的是**門**，不是清存量（同表上 `Get-Command`
解析那一列已被接受的形狀：「今天的存量違規是 0——所以缺的一直是下一個人寫出時當場
紅的門，而不是數今天有幾筆」）。

① `git ls-files`／`git diff --name-only` 的非 ASCII 路徑引號化（XPL-S1-01）。
   git 預設把非 ASCII 路徑吐成 C-quoted（`"a/\346\211\213.md"`）。本 repo 今天沒炸，
   唯一的原因是 `.git/config` 有 `core.quotepath=false`——那個檔由 `git clone` 就地
   新建、**不是 tracked**，不隨 repo 走，連 grep 都掃不到。落地當回合實測：全庫
   27,566 條 tracked 路徑中 **630 條非 ASCII**，兩種設定下 key 集合差 630 筆，
   C-quoted key 的 `is_file()` 回 **False**（檔案靜默掉出掃描面）。
   修法三段：取數層 SSOT（`tools/lib/git_paths.py`）＋逐站點收斂＋本判準守新站點。

② 排序鍵的平台相依性污染 digest（XPL-S1-06）。裸 `sorted(Path)` 比的是
   `PurePath._str_normcase`：Windows case-fold、POSIX 原字元序。`DEF-101-613` 特地
   把 hash 前的 bytes 折行尾、明說目的是讓指紋在 macOS／CI 上對得上，但**排序這一軸
   沒有一起處理** ⇒ 同一個目標留了第二個入口沒關。
   🔴 判準刻意**只**判「排序結果餵給 digest」這個形態：落地當回合實測全活躍面
   `sorted(<glob/rglob/iterdir>)` 未帶 `key=` 的站點有 **148 筆**，絕大多數是列印／
   迭代用途、與跨平台一致性無關 ⇒ 一律判紅就是 148 筆假紅，而假紅會逼下一輪把整條
   鎖關掉。收斂到 digest 形態後存量是 2 筆，兩筆當輪都修掉了。
```

---

## 站點級守衛四種罩法 WHY

> 搬遷自 `tools/tests/test_platform_neutral_paths.py`（R107 帳本結案包 #3 抵銷窗口；原文全文保全、知識零刪除；僅指稱詞（本檔→該檔等）隨載體必要調整）。

舊判準：「整檔第一個含守衛字樣的**行號** < 使用點行號 ⇒ 特赦」。三個結構性後果：
① 檔案級——任何一段與違規完全無關的守衛（隔壁函式、檔頭的一句 `if
   sys.platform == "win32"`）會把它後面**整檔**的違規全部赦免；
② 純文字——守衛字樣寫在字串常數或訊息裡即可開後門，而本 repo 的中文 WHY
   大量逐字提到 `sys.platform == "win32"` 這種字樣，開後門完全不像在繞過；
③ 只看「之前出現過」——連「同一個作用域」都不要求。
新判準只問一句：**這個使用點在語法上被平台守衛罩住了嗎**。四種罩法（皆為
repo 內既存的真實寫法，不是發明出來的）：

    enclosing-if       祖先鏈上有 `If`/`IfExp`/`While`，其 test 在判平台
    early-return-guard 同一個 block 內、排在它**之前**的 `if <守衛>: … return`
                       （`platform_caps.kill_process_tree()` 就是這個形狀）
    guarded-decorator  所在 def/class（含**同檔基底類別**）帶平台守衛 decorator
                       （`@unittest.skipUnless(sys.platform == "darwin", …)`）
    try-capability     使用點在 `try:` 本體、而 handler 捕 ImportError／
                       ModuleNotFoundError／AttributeError＝作者明示這是可選能力

🔴 刻意劃界：不做方向判定（`if is_windows():` 的 else 分支放 POSIX 碼是對的、
body 放 POSIX 碼是錯的，兩者本判準都算「有守衛」）。方向那一半屬控制流語意，
靜態誤判的代價是假紅，而假紅會逼下一輪把整條鎖關掉（該檔第五道判準同樣取捨）。

## 外部執行檔 argv[0] transitive WHY

> 搬遷自 `tools/tests/test_platform_neutral_paths.py`（R107 帳本結案包 #3 抵銷窗口；原文全文保全、知識零刪除；僅指稱詞（本檔→該檔等）隨載體必要調整）。

上面那個判準（單平台專屬 API 詞彙表）結構上看不到這一族：它的詞彙表收的是 **Python
符號**，而「送給 OS 的外部程式名」不是符號——AST 看到的只是一個 `ast.Constant` 字串
⇒ 那一族從來不在分母裡（與 R81 訂正的 `ctypes.*` 失明逐字同型；失明是靜默的：掃描器
照跑照綠照回報命中數）。

🔴 **詞彙表刻意不在測試檔再寫一份**：它是量測本身，唯一的家＝
`tools/probe/xplat_hazard_census.py`。測試檔只提供「門」，不提供第二份詞彙。

🔴 **transitive 可達性是本族的必要條件，不是加值**（P7 逐筆查完 AutoClaude 那一棵的
實測結論）：守衛有四種形狀，其中一種是**跨 1~3 層的 helper**——`_run_ps1`／
`_run_powershell`／`_try_osascript` 自己一個守衛都沒有，安全性完全寄託在呼叫端。
只認站點級守衛的判準對全庫 24 筆噴 **3 筆假紅**（實測），而假紅到需要逐一辯護的鎖
活不過一輪。深度上界 3 是量出來的：`check_scheduled_task_drift._run_powershell` 的
真實鏈是 `main`（帶 `sys.platform != "win32"` 早退）→ 三個中介 → 它，恰好 3 層。

🔴 transitive **只**用在本族，不回頭套到符號判準：那張債表
（`_FOREIGN_API_SCOPE_DEBT`）是**雙向精確比對**，而它登記的 `dev_start.py:1051`
正好就是這個形狀 ⇒ 套過去會把一筆**有人登記過的**債靜默抹掉。要不要抹是那筆債的
所有者的決定，不是判準的副作用。

## 作用域級存量債表沿革

> 搬遷自 `tools/tests/test_platform_neutral_paths.py` 的 `_FOREIGN_API_SCOPE_DEBT` 註解（R107 帳本結案包 #3 抵銷窗口；原文全文保全、知識零刪除；僅指稱詞（本檔→該檔等）隨載體必要調整）。

🔴 R79 誠實劃界：表內這支檔不屬 R79 XPLAT 包的所有權（`tools/dev_start.py` 的
`_forward_signal_to_bootstrap()` 是 POSIX-only 的訊號 handler，只在 POSIX 側
`signal.signal()` 註冊——那個註冊點在別的函式裡，靜態上罩不到它），故該輪只
登記不代改；處置已列入交棒（加行尾豁免標記即可歸零）。

🔴 R81（XPL-S1-04）由 4 升到 5：詞彙表補上 `ctypes.*` 之後，`tools/dev_start.py`
9 個 `ctypes.windll` 站點裡有 **8 個**被既有作用域守衛正確罩住（enclosing-if 5、
try-capability 1、guarded-decorator 2 —— 逐點實測），剩下 `:1051`
`kernel32 = ctypes.windll.kernel32` 位在 `_list_pid_ppid_pairs_windows()` 函式體
最上層，**函式自己沒有內部守衛**，安全性完全寄託在兩個呼叫端（`:1120`／`:1141`）
——那正好是靜態上證不出來、而且下一個人新增第三個呼叫端時不會有任何東西轉紅的形態。
該包不代改 `dev_start.py`（不在所有權內），故據實登記；歸零動作＝在該行行尾加
豁免標記並寫明呼叫端契約，或把守衛搬進函式本體（後者才是真的修好）。

## DEF-200-208 一次性例外名冊 WHY

> 搬遷自 `tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `_REPIN_APPROVED_ROUND_OVERAGE` 註解（R107 帳本結案包 #3 抵銷窗口；原文全文保全、知識零刪除；僅指稱詞（本檔→該檔等）隨載體必要調整）。

**不是**修改 `net_cap_for_round()` 或 `_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS`——那兩者
是往後**每一輪**都適用的門檻本體，字面與判準邏輯該輪一個字未動。本表只讓**指名的
那一輪**的款(10)(11) 不計入 `repin_growth_problems()` 的回傳，未列名的輪次（含未來
任何一輪）完全不受影響——這是名冊，不是開關；下一輪若也想超標，必須自己在缺陷帳本
立新案號並再走一次四方複審，不能靠「反正這張表已經有前例」就往這裡加第二個 key。

WHY（該輪非有不可的理由）：R101 同時撞上兩件各自獨立、卻在同一輪疊加的機械事實——
① `_REPIN_NET_CAP_DUE_ROUND=101` 到期義務要求 cap 降到 `_REPIN_NET_CAP_DUE_TARGET`
   （750）以下（見排程列），而該輪待重釘的真實漂移淨額（+1136）遠超過新舊任一 cap；
② 這批漂移**不是該輪新造成的成長**，是既有鎖檔跨多輪（ADR-XPLAT-013 落地後）
   從未被 `--print-guard-lines` 覆核揪出的陳舊漂移，加上該檔自身修復
   `pricing_exemption_problems()` provenance 缺陷的編修（DEF-200-208 主線）；
③ R99／R100 已連續兩輪淨額為正，R101 若照常規計入即成第三輪，撞款(11)。
四方複審裁決：一次性把陳舊漂移收斂進帳，比讓判準繼續帶著 DEF-200-208 那個「baseline
大小關係恆假」的缺陷空轉、或被迫放寬 cap／streak 門檻本體，更誠實也更安全——後者才是
真正的指標套利（一次放寬，永遠放寬）。

🔴 為何 value 是 `(該輪的精確淨額, 理由)` 而不是只用輪號當 key：`_rising()` 這支既有
測試 fixture 會拿 `_REPIN_NET_CAP_SCHEDULE[-1]` 的輪號造合成樣本（`test_a_round_that_
exceeds_the_net_cap_is_red`），而該輪號**恰好就是**每次到期義務兌現時的活躍輪號——
該輪的例外剛好也落在同一個輪號上（R101）。若 key 只用輪號，合成測試造出的
`("R101", 1000, 1751, 751, ...)` 也會被誤判成「已核准」而讓那支測試的紅燈熄掉，
那不是本表的射程（本表只赦免**這一個真實事件**，不是「這個輪號往後怎麼標都算數」）。
把精確淨額也綁進判準，合成測試的任意 delta 與真實核准值不同、自然不受影響。

## 到期義務兌現沿革

> 搬遷自 `tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `_REPIN_NET_CAP_DUE_*` 註解（R107 帳本結案包 #3 抵銷窗口；原文全文保全、知識零刪除；僅指稱詞（本檔→該檔等）隨載體必要調整）。

R101 兌現：`_REPIN_NET_CAP_DUE_ROUND=101` 該輪到期，cap 降到目標本身（750，見
`_REPIN_NET_CAP_SCHEDULE` 的 `(101, 750)` 列）。同輪就地重新武裝下一段（R85 起
慣例）：步伐 50 < 前一段的 100，續守「步伐刻意變小」——不使目標貼齊現行 cap，
否則 `assertLess(_REPIN_NET_CAP_DUE_TARGET, _REPIN_ROUND_NET_CAP)` 這道「到期目標
必須嚴格低於現行上限」的方向鎖會立刻恆真失效（款(12) 是一句永遠成立的話）。

DEF-200-221 兌現：`_REPIN_NET_CAP_DUE_ROUND=103` 該輪到期，cap 降到目標本身
（700，見 `_REPIN_NET_CAP_SCHEDULE` 的 `(103, 700)` 列）。同輪就地重新武裝下一段：
步伐 40 < 前一段的 50，續守「步伐刻意變小」。

DEF-200-224 兌現：cap 降到目標本身（660，見 `(105, 660)` 列）。同輪重新武裝下一段：
步伐 30 < 前一段的 40，續守「步伐刻意變小」。

DEF-200-166／171 結案窗口兌現（R107）：cap 降到目標本身（630，見 `(107, 630)` 列）。
同輪重新武裝下一段：步伐 20 < 前一段的 30，續守「步伐刻意變小」（`(109, 610)` 到期段）。

## 凍結基準不由 git 導出 WHY

> 搬遷自 `tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `_FROZEN_MAX_BASELINE_ENTRIES` 註解（R107 帳本結案包 #3 抵銷窗口；原文全文保全、知識零刪除；僅指稱詞（本檔→該檔等）隨載體必要調整）。

🔴🔴 R67 round 2（SA-R67-08）凍結基準：兩個 shrink-only 常數的「上一版」不再由 git 導出。

病灶（SA 沙箱實證：git 導出基準對每一個跑在 commit 之後的閘門恆真，放大十餘倍門檻
零訊號）——實測原文＝Guard_Repin 證據檔 §B-11。

為什麼凍結常數不會重蹈恆真覆轍：git 導出的基準會被「commit」這個動作自己同步過去，而
每個閘門都在那之後才跑；簽入原始碼的字面常數則 commit 不動它、checkout 不動它、CI 乾淨樹
也不動它——只有人手改那一行才會變。於是「門檻」與「基準」是兩個獨立可變的量，比較在任何
時點、任何消費者（髒樹／pre-commit／pre-push／CI）都非退化。整條 git 依賴一併消失，
連帶消滅舊實作的另一面 fail-open：`previous is None`（git 取不到）時整支 skip。
論證與形狀逐字同 `tools/check_script_parity.py` 的 `_TIER_BASELINE`（R67-H14），
該處是照抄該檔而來的下游——該輪把上游本體也修了。

殘餘面（誠實揭露，與 R67-H14 同一句）：同一個 commit 內**同時**改門檻與該組凍結基準仍可
通過——這是所有釘選式棘輪共有的邊界，與「零成本、隱形、自動」的舊行為是不同量級；且該組
是純量，調升在 diff 上就是一個變大的數字，方向一望即知（不像 tier 名稱那樣需要對照表）。
本性質有機械鎖：`TestShrinkOnlyRatchet::test_ratchet_is_independent_of_git_state`
（禁用 subprocess 仍須完整運作），舊實作在該鎖下會直接紅。
另有一道獨立張力：`_BASELINE_ID_CEILING` 同時被 `TestCriterionIsBoundToAdrProse` 綁在
ADR §4.3.4 的宣告句上 ⇒ 調升它還得動 ADR，那是該檔之外的第三個站點。

## 淨減法到期斷言訂正 WHY

> 搬遷自 `tools/tests/test_adr_xplat001_c1c2_lock.py`（R107 帳本結案包 #3 抵銷窗口；原文全文保全、知識零刪除；僅指稱詞（本檔→該檔等）隨載體必要調整）。

🔴 R85 收尾單人窗口訂正（把動工中的預測寫成契約、當輪即被證偽）——
立案原文＝Guard_Repin 證據檔 §B-12。

🔴 **為何是訂正而不是放寬**——三件事逐條攤開，供下一輪覆核：
① 「必須有一輪 ≤ 0」這個**要求本身保留**，一個字都沒拿掉；
② 到期時點**釘死在 `_NET_SUBTRACTION_DUE_ROUND`**，且照款(12) 的體例
   **刻意不留延期參數**（「可延期的到期日不是到期日」）；
③ 今天的斷言內容由「已經達成」改成「**尚未到期**」——後者今天為真，前者為假。
真正的義務居所本來就是**到期日形狀**：ADR-XPLAT-002 §8.1 item 15 要求的是
「**到期輪之前**必須出現一次淨額 ≤ 0」（輪號現查 `_NET_SUBTRACTION_DUE_ROUND`，
測試檔註解刻意不複寫那個字面——寫出來就會超前帳本當前輪而被輪號鎖擋下，
而那條鎖是對的：程式碼註解不該宣稱一個帳本上還不存在的輪次）。
該斷言原文比該義務嚴，且嚴在一個被證偽的前提上。

🔴 **R85 為何達不到（是算術不是判斷）**：全部出口用盡 ≈ 442 < 需刪 588——
兩份獨立量測原文＝Guard_Repin 證據檔 §B-12（原逐筆交棒＝R85 同名檔 §4）。

## SC-2/3/5 射程收窄 WHY

> 搬遷自 `tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `_SEC8_*` 註解（R107 帳本結案包 #3 抵銷窗口；原文全文保全、知識零刪除；僅指稱詞（本檔→該檔等）隨載體必要調整）。

🔴 R67 round 4（SA2-R67-01）把 SC-2／SC-3 的下界由 `_SEC8_END_ALL` 收窄到 `### 8.1`。
原版掃 §8 全區，於是 §8.3——本 repo 自己指定的「逐字保全散文區」——也落在射程內，而這
三條**都沒有同行豁免**（只有 SC-1／SC-4 走 `_line_hits_with_waiver`）。後果可列舉：
下一次照該輪體例把一句含 `**R62+**` 或千分位常數的 §8 原文保全進 §8.3，該鎖即**永紅**，
而唯二出路都是本 repo 已判過更糟的——改寫保全原文（違反逐字保全紀律），或臨時加豁免
（「誤報的鎖最後一定被加豁免繞過，比沒有鎖更糟」，見該檔多處與 `DEF-101-700` 的拒收理由）。
⇒ 豁免路徑刻意**不是**新加一枚標記，而是沿用 §9.1 邊界 (b) 已裁決的既有出口：**把逐字
原句移進 §8.3 散文區**。界線對齊後，「§8.3 是這幾條共同的保全區」才從口號變成一句真話。
`_SEC8_END_ALL` 保留給 `test_the_scan_surface_did_not_collapse`——它以「全區嚴格長於本體」
反證 `### 8.1` 界線還活著（界線一旦失效，這幾條會一起退化回掃全區，正是該次修掉的形態）。

## dev_start 史料搬遷

> 搬遷自 `tools/dev_start.py` 的兩段沿革註解（Gap C 接線輪：ONBOARDING §7 表② 指紋
> 檢查接進 [6/7] 平台健檢，新增行以本節搬遷抵銷、該檔 raw-line 維持 1952 不變；
> 原文全文保全、知識零刪除；僅指稱詞隨載體必要調整）。

### `import _stdio_utf8` 模組載入期重設（原址：版本閘前 prelude）

R3 四方複審 QA 發現：tools/tests/ 先前從未在真實 Windows 上執行過，本輪首次
真實執行後，`_warn()`/`_hr()` 的 `print()` 在 Windows 非 UTF-8 終端（如 zh-TW 預設
cp1252 codepage、或任何非互動/被導向的 stdout）下對 ⚠️/✅ 等符號直接
UnicodeEncodeError 崩潰——先前只有 `main()`（CLI 入口）內重設編碼，測試套件與
任何未經 `main()` 直接呼叫模組內部函式的呼叫端（未來的 import 使用者）不會套用
到這道保護。改在模組載入當下就重設，涵蓋所有呼叫路徑，且與 `main()` 原本的保護
邏輯等價。R4 複審 S7 發現：此保護抽成 `tools/_stdio_utf8.py` 共用 helper（避免
`check_ntfs_paths.py` / `check_script_parity.py` 各自複製貼上第三份同款程式碼）。

### R67-M40 心跳年齡整數秒差（原址：`_check_nightly_heartbeat()` 內 `age_days` 計算行）

R67-M40：年齡先收斂為「整數秒差」再換算天數，與 `install_mac_nightly.sh`
`report_heartbeat()` 的秒級語意精確對齊。WHY：BSD `stat -f %m` 與 `date +%s`
都只給整數秒，而 `os.stat().st_mtime` 保留次秒精度——當心跳檔 mtime 恰為整秒、
年齡恰落在 [8 天, 8 天+1 秒) 時，bash 側算出 691200（`-gt 691200` 為偽→新鮮）
而 python 側算出 691200.0x（`> 8` 為真→過期），同一台機器同一顆心跳檔兩個
官方工具給出相反結論，且實測 10/10 必然重現（不是 flaky，是確定性分歧）。
兩端同樣先截成整數秒即結構性消除該邊界，無須為 1 秒窗口新增任何跨檔耦合。
