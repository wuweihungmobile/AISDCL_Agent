"""可用 bash 探測規則的共用資料規格（單一真相源，R32 Architect 架構最佳化）。

WHY：本 repo 有數份「找可用 Git Bash、排除 WSL System32 佔位版」的實作，被**硬邊界**
隔開而無法互相 import——`AISDLC_SDD/scripts/bash_probe.py::usable_bash()`（生產用，
子專案邊界）、`tools/integration_gate_core.py::find_git_bash()`、
`tools/tests/_platform_helpers.py::usable_bash_for_fixture()`（根層測試樹的 SSOT），
以及 PS1 側的 `tools/lib/Find-GitBash.ps1`（語言邊界）。

🔴 **R80 S5-03 訂正本段原文**：原文把 `test_pre_push_dispatcher.py::_usable_bash()` 與
`test_git_hooks_install_common.py::_usable_bash()` 列為「測試檔內**獨立重寫**的回歸鎖，
其獨立性讓生產程式碼的共同盲點也抓得到」。當回合以 AST 正規化實測，那兩份加上
`test_windows_forbidden_filename_parity.py` 的第三份，**剝除 docstring 後逐字相同**
（雜湊皆 `9797b0251822`）＝複製貼上，不是獨立重寫；逐字相同的複本共享 100% 盲點，
提供的額外鑑別力是零。三份已收斂進 `_platform_helpers.usable_bash_for_fixture()`
（量測、覆蓋承接對照見 `docs/06_quality/CrossPlatform_R80_Subtraction_Evidence.md`）。
上面列的那幾份雜湊互不相同，是真的各自寫成的，故保留。

各份原本各自寫死同一組「參數」（驗活探測指令、期望輸出、System32 排除段），
導致 DEF-101-275（R27 開出）「僅用 `echo` 驗活、未驗 coreutils，精簡版 Git Bash
會誤判為可用」這個缺口連續 5 輪（R27~R31）都沒有任何一份補上——本檔把這些
「資料」抽成單一真相源，三份程式各自 import 取得同一份規則資料，但驗活的
**執行邏輯**（subprocess 呼叫、逐段路徑比對）仍各自獨立寫在各自檔案內，不抽成
共用函式，以維持三份回歸鎖彼此獨立的鑑別力（不會因為共用函式本身壞掉而三份
同時失效）。

DEF-101-275 修復：`PROBE_CMD` 由單純 `echo ok` 改為 `echo` + `dirname` 兩段
coreutils 探測串接——精簡版 Git Bash 若缺 `dirname` 這類 coreutils 二進位檔，
第二段會以非 0 回傳碼失敗，呼叫端據此拒絕該候選（不再只驗 echo 這種 shell
內建字串處理）。`dirname` 為純字串運算，不需要路徑實際存在。

第四份消費者（R32 一審 SA/QA 交叉發現後補上）：`tools/tests/test_bash_probe_spec_contract.py`
——上述三份消費者的既有測試全數 mock `subprocess.run`，未曾驗證 `PROBE_CMD`
本身是否真的依賴 `dirname`；該檔以不 mock 的真實 subprocess 呼叫，直接鎖住
本規格檔的資料內容與三份消費者的實際 wiring。
"""
from __future__ import annotations

# 排除的 Windows 路徑段（WSL 系統目錄佔位 bash.exe）；逐段精確比對、不分大小寫。
# 消費者：AISDLC_SDD/scripts/bash_probe.py、tools/tests/test_pre_push_dispatcher.py、
# tools/tests/test_windows_forbidden_filename_parity.py、
# tools/tests/test_git_hooks_install_common.py，以及 tools/integration_gate_core.py
#（R36 DEF-101-307 收斂併入，原為獨立硬編字面值的第二座 SSOT 孤島；PS1 側
# tools/lib/Find-GitBash.ps1 因無法直接 import Python 常數、仍維持獨立字面值，
# 由 tools/tests/test_find_git_bash_parity.py 鎖住兩邊字面值同步）。
SYSTEM32_SEGMENT = "system32"

# 驗活探測指令：`&&` 串接 echo（基本存活）與 dirname（coreutils 真的可執行，
# 不只是 shell 內建字串處理）。用 POSIX 路徑寫法，Git Bash 內部一律以 POSIX
# 語意處理路徑字串，跨平台輸出穩定；dirname 不需要該路徑實際存在。
PROBE_CMD = "echo probe_ok && dirname /tmp/probe_dir/leaf"

# PROBE_CMD 成功執行時，stdout 逐行的期望值（依序）。
PROBE_EXPECT_ECHO = "probe_ok"
PROBE_EXPECT_DIRNAME = "/tmp/probe_dir"
