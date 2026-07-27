"""
共用工具：從完整 evaluator_command 推導 SPLIT_STEP Part A 輕量評估指令。

Gap-026-A（PlaybookEvolver）與 Gap-026-B（MinimaxEvolver）原各自維護一份
100% 重複的 `_derive_part_a_evaluator` 實作（R50 四方審查發現的 SSOT 違反，
P2）：同一個 POSIX-only `{ cmd; } || true` bug 需在兩個檔案分別發現、
分別修復。本模組將邏輯抽成單一共用函式，兩個 Evolver 的
`_derive_part_a_evaluator` staticmethod 皆委派至此，往後只需修一處。
"""
# ── R56 round 5：已知取捨揭露（落盤產物不可攜；刻意不修，僅記錄）──────────────
# 本模組產出的字串會被**寫進落盤 YAML**：`playbook_evolver.py` 的 SPLIT_STEP 提案
# 帶著 part_a_evaluator 一路 yaml.dump 進 `evolved_<playbook>.yaml`，
# `playbook_persistence_plugin._mutated_path_for()` 的 `<stem>.mutated.yaml` 同理。
# 而下方 `_QUOTED_PY` 是**生成期**的 `sys.executable` 絕對路徑（R51 起的政策，R56 擴到
# pytest 分支）——路徑本身綁定當下平台。
#
# 後果：`tools/dev_start.py::_ensure_venv_shape()` 的 `.venv-cache-posix` /
# `.venv-cache-windows` 換手機制，其設計目的（見該函式 docstring）正是支援「共用工作
# 目錄來回切換各平台」。在該情境下 macOS 產生的 `evolved_*.yaml` 會固化
# `"/Users/…/.venv/bin/python" -m pytest …`，切到 Windows 續跑即失效（反向亦然：
# Windows 產的 `...\.venv\Scripts\python.exe` 在 macOS 同樣不存在）。
#
# 為何本輪刻意不修：這是 R51「裸 `python` 在乾淨 PATH 上 rc=127」決策的**延伸**而非
# R56 新造，且無更好的單行替代——`python3` 在 Windows venv 不存在，裸 `python` 在
# macOS/多數 Linux 乾淨 PATH 不存在，任何單一字面值都會在某一平台壞掉；相較之下
# 「絕對路徑 + 跨平台共用工作目錄」是明顯較窄的觸發面。
#
# 架構正解（未來若要修的方向）：把直譯器解析下移到**執行期**——由 ShellEvaluator
# 在跑 evaluator_command 時辨識 head token 為裸直譯器名並就地換成當下行程的
# `sys.executable`，落盤 YAML 只保留可攜的 `python -m pytest …` 字面值。屬跨模組
# 契約變更（生成期→執行期職責搬遷），須另立提案，不在本輪範圍。
# ──────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import base64
import re
import sys

# R56 修正：裸直譯器名判準（`python` / `python3` / `python3.11` / `Python.exe`）。
# macOS /usr/bin 與多數現代 Linux distro 的乾淨 PATH 上只有 `python3`、沒有裸 `python`，
# 故 `python -m pytest ...` 形態的 head token 命中本 pattern 時一律置換為
# `sys.executable` 絕對路徑 —— 與下方非 pytest 分支自 R51 起的既有政策同一條。
_BARE_PY_RE = re.compile(r"python(3(\.\d+)?)?(\.exe)?", re.IGNORECASE)
# 雙引號包住以相容含空白的路徑（Windows "Program Files"）；`or "python3"` 為
# sys.executable 罕見為空（嵌入式直譯器）時的兜底，與 R51 原實作一致。
_QUOTED_PY = '"%s"' % (sys.executable or "python3")


def _pytest_invocation_index(tokens: list[str]) -> int | None:
    """回傳 tokens 中真正呼叫 pytest 的位置；非任意子字串命中。

    僅認 tokens[0] == 'pytest' 或 '-m' 後緊接 'pytest'（R53：修正舊 `\\bpytest\\b`
    偵測 vs `tokens.index("pytest")` 擷取判準不等價，對複合 token 誤判的缺陷）。
    """
    if tokens and tokens[0] == "pytest":
        return 0
    for i, tok in enumerate(tokens[:-1]):
        if tok == "-m" and tokens[i + 1] == "pytest":
            return i + 1
    return None


def derive_part_a_evaluator(full_evaluator: str | None) -> str | None:
    """
    從完整 evaluator_command 推導 Part A 輕量評估指令。
    策略：
    - pytest 指令 → 改為 --collect-only（僅確認測試可被收集）
    - 其他指令 → 執行原指令但無條件回傳成功（確保不因 Part A 僅涵蓋一半任務而誤報失敗）
    - 無 evaluator → 回傳 None

    跨平台注意：evaluator.py 以 subprocess.run(shell=True) 執行，Windows 走 cmd.exe、
    POSIX 走 /bin/sh，兩者語法不相容。舊實作 `{ cmd; } || true` 為 POSIX 專屬分組語法，
    cmd.exe 不支援（`{` 會被當成不存在的命令）。改以 `python -c` 包裝：以 base64 編碼
    原指令避開任何引號/特殊字元造成的殼層轉義問題，內部仍以 subprocess.run(shell=True)
    交給平台原生殼執行 cmd 本身（保留原指令可用任意殼語法的彈性），並無條件 sys.exit(0)。

    R51 修正：包裝殼一律用 `sys.executable`（本行程實際執行的 Python 直譯器絕對路徑）
    而非裸字面值 `python`。macOS /usr/bin 與多數現代 Linux distro 預設 PATH 上並無
    `python` 別名（僅有 `python3`），裸字面值在該類環境會以 shell rc=127
    「command not found」收場，打破本函式「非 pytest 指令必須無條件回傳成功」的契約。
    以雙引號包住路徑以相容路徑含空白（如 Windows "Program Files"）。

    R56 修正：上述「一律」原僅對非 pytest 分支為真 —— pytest 分支把輸入的 head token
    逐字保留，`python -m pytest ...` 會推導出裸 `python -m pytest --collect-only`，在同一
    類環境同樣以 rc=127 收場。現兩分支同政策（見 `_BARE_PY_RE` 上方註解）。

    R52/R53 修正：pytest 判定改用 `_pytest_invocation_index`（見該函式 docstring）。
    """
    if not full_evaluator:
        return None
    cmd = full_evaluator.strip()
    pytest_idx = _pytest_invocation_index(cmd.split())
    if pytest_idx is not None:
        # pytest → collect-only；先剝除 -k/-x/-v/-s/-q 與 --tb= 旗標
        base = re.sub(r'\s+-[kxvsq]\S*', '', cmd)
        base = re.sub(r'\s+--tb=\S+', '', base)
        tokens = base.split()
        pytest_idx = _pytest_invocation_index(tokens)
        head = tokens[: pytest_idx + 1] if pytest_idx is not None else tokens[:1]
        head[:1] = [_QUOTED_PY] if _BARE_PY_RE.fullmatch(head[0]) else head[:1]
        return " ".join(head) + " --collect-only"
    payload = base64.b64encode(cmd.encode("utf-8")).decode("ascii")
    return (
        f'{_QUOTED_PY} -c "import subprocess, base64, sys; '
        f"subprocess.run(base64.b64decode('{payload}').decode('utf-8'), shell=True); "
        'sys.exit(0)"'
    )
