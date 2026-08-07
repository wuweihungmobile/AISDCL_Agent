#!/usr/bin/env python3
# 🔴 本檔 docstring 必須維持 raw（`r"""`）：內文引述 Windows 路徑形態
# （`.\local_ci_gate.ps1`），非 raw 時 `\l` 是**非法轉義序列**——Python 3.11 印
# DeprecationWarning、3.12 起升為 SyntaxWarning、CPython 已宣告未來版本改為
# SyntaxError（屆時本檔＝本機 CI 閘門唯一核心將無法 import）。R60 QA-R60-05 實測：
# 本輪新增該行時 `pytest tests/ -q` 尾行就印出 `invalid escape sequence '\l'`，
# 而專案 ruff `select` 當時不含 `W` ⇒ 閘門結構上看不到（已同輪把 `W` 補進 select，
# 見 pyproject.toml）。改回非 raw 會讓 `ruff check --select W605` 與
# `python -W error::SyntaxWarning` 兩道都紅。
r"""local_ci_gate.py — 本機 CI 閘門單一核心（macOS / Linux / Windows 共用）。

DEF-101-070 ② 收斂案（R12 ARCH-R12-1）：原 tools/local_ci_gate.{sh,ps1} 為雙實作
（bash / PowerShell 各長一份業務邏輯，靠 tools/check_script_parity.py 事後比對防漂移），
本檔將全部 gate 語意收斂為單一 Python 核心，兩支同名 .sh / .ps1 降為「確認直譯器 →
轉呼叫本檔 → 傳遞 exit code」的薄殼——模式對齊 tools/dev_start.{py,sh,ps1} 既有範例。
薄殼本身由 monorepo 根 tools/check_wrapper_thinness.py 以正規化內容 hash 釘選守門
（釘選與 check_script_parity.py 的 _THINNESS_ENROLLED 登記均已接線，兩清單另有
鍵集合交叉鎖）。介面邊角揭露（R12 SD 一審 SD-1）：.ps1 薄殼 `-PytestArgs ''`
（空字串）現落回核心預設參數——舊版此邊角行為 host 相依（PS5.1 丟空元素、
pwsh 7.3+ 傳 '' 使 pytest 報錯），新行為為兩者之良性收斂；`-PytestArgs '--act'`
會被核心解析為 gate 旗標而非 pytest 參數（舊版傳給 pytest 報錯），正常用法不受影響。

R60 訂正（F-refuter-1）：上段「`-PytestArgs ''` 落回核心預設」曾是需要特別揭露的
**邊角**，因為 .ps1 的 `$PytestArgs` 預設值寫死著一份 `'tests/ -q --tb=short'`——
R59 在下方 DEFAULT_PYTEST_ARGS 加 `-rs` 時那份複本沒跟上，於是 Windows 側（含
nightly Stage L）**無參數呼叫**就被薄殼整批取代掉核心預設、`-rs` 靜默消失。現已把
.ps1 預設改為 `''`，「無參數」與「`-PytestArgs ''`」兩條路完全等價、都落回本檔的
單一真相源，上段揭露因此降為歷史註記。另訂正該段自身的一處不可達：以本檔
`.EXAMPLE` 示範的 `-File` 呼叫傳 `-PytestArgs ''`，PS 5.1 直接報
`Missing an argument for parameter 'PytestArgs'` 而中止（要走呼叫運算子
`& …\local_ci_gate.ps1 -PytestArgs ''` 才到得了該邊角）——即該邊角在文件自己示範的
載具上根本觸發不到。跨檔語意鎖：tests/tools/test_local_ci_gate_shell_arg_parity.py。

依序（全綠才建議 push；鏡像 monorepo 根層 .github/workflows/autoclaude-ci.yml push gating jobs）：
  0. editable 哨兵       （autoclaude 指向本 monorepo；in-process 動態比對，取證紀律 #19）
  1. LOC 預算
  2. CLAUDE.md <= 400 行
  2b. CLAUDE.md 單行 <= 800 codepoint（contract test）
  3. snapshot 可重現
  4. import-linter
  5. pytest
可選：
  --pg   額外起 docker-compose.ci.yml（pg17）跑 PG 契約測
  --act  額外用 act 在 Linux 容器跑 ci.yml（POSIX 走 run_act.sh；Windows 以 PowerShell
         載具 -File 呼叫 run_act.ps1，powershell 優先、pwsh 後備——對齊 tools/dev_start.py
         先例與 Local_CI_Parity_NextAction「pwsh→powershell（本機僅 PS5.1）」修正史料）

用法（一般經薄殼呼叫；直接呼叫亦可）：
  python tools/local_ci_gate.py
  python tools/local_ci_gate.py --act
  python tools/local_ci_gate.py --pg
  python tools/local_ci_gate.py -k test_foo -v   # 非 --act/--pg 參數整批取代預設 pytest 參數
  python tools/local_ci_gate.py --census-only <pytest 輸出檔>
      只跑 **skip 分群普查**（不跑任何 gate、不跑 pytest、不注入任何環境變數）。
      給「已經在別處跑過 pytest」的通道消費——push 通道（根層 tools/git-hooks/pre-push
      的 AutoClaude leg）與 CI 的 test job 都是這一種：它們刻意直跑 pytest 不經本檔
      （R12 QA-2 紀律：兩個訊號不得合流），於是天花板此前一條阻斷通道都沒接上。
      離開碼三態（**刻意不是兩態**）：
        0 ＝健康；1 ＝真問題（量測塌掉／天花板被突破／找不到剖面標記）；
        3 ＝剖面未登記（量測正常，但這個平台沒有人量過健康值 ⇒ 沒有天花板可比）。
      3 存在的理由：mac／Linux 從來沒被量過，把「沒人量過」與「skip 變多」壓成同一個
      rc，push 通道只能二選一——要嘛誤擋沒量過的平台，要嘛整條放行。
"""
from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent  # AutoClaude repo 根
MONO_ROOT = REPO_ROOT.parent                        # monorepo 根 — 定位共用 tools/

# platform_utils 位於 monorepo 根 tools/lib/ 子目錄（非本檔同層），需顯式插入
# sys.path 才能 import——手法對齊本輪其他核心檔案既有慣例（R17 DEF-101-231 觀察點
# 1+2：收斂 is_windows/os_label/venv_python_path 平台判斷邏輯的第二次重複）。
sys.path.insert(0, str(MONO_ROOT / "tools" / "lib"))
import platform_utils  # noqa: E402
import skip_group_policy  # noqa: E402  ← R79：skip 分群天花板的政策 SSOT（根層 tools/lib/）

# `-rs`（R59 ARCH-R59-01）：印出每一支 skip 的理由。
# WHY：DEF-101-510 立的原則是「因為跑在某平台而失去的覆蓋不得只併成一個數字」，但那輪
# 只把機制補在根層 `tools/run_root_unittests.py`（unittest 沒有 `-rs` 這種內建能力，只好
# 自己寫）。真正的測試量體在 pytest 側（AutoClaude 3740/208），而本 repo 所有 pytest
# 呼叫端一律 `-q` 且從未加 `-rs`——`grep -rn '\-rs\b'` 全 repo 唯一命中曾是 run_root_unittests
# 的一句註解。也就是說「skip 可見度」只做在最小的那一面：DEF-101-515 之所以要人工考古才
# 解釋得出 v0.30 −4（`requires_docker_success` 硬排除 win／POSIX shebang `skipif(win)`），
# 正是因為 pytest 面把理由丟掉了。加 `-rs` 是這件事的最小修法（pytest 內建，零新程式碼）。
# 安全性已實測：`scripts/pytest_passed_count.sh` 以 `grep -oE '[0-9]+ passed' | tail -1`
# 取值，SKIPPED 行不含該樣式，加 `-rs` 後計數不變（R59 實測仍得正確值）。
DEFAULT_PYTEST_ARGS = ["tests/", "-q", "-rs", "--tb=short"]

_PG_DSN = "postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude"
_PG_COMPOSE = ["docker", "compose", "-f", "docker-compose.ci.yml"]

# ── R79（D-skipped #2／掌舵者 S3）：讓「甲類 skip」預設就會跑 ─────────────────────
#
# 🔴 問題不是缺件，是**沒人記得設環境變數**。R79 在這台 Windows 11 真機實測：PG 容器長駐
# healthy、`.venv` 的 sqlalchemy／psycopg2／pgvector／asyncpg／alembic 全部已裝、DB 已在
# `alembic upgrade head`——一件缺件都沒有，缺的只是三個環境變數。設好之後
# `pytest tests/ -q` 由 **4069 passed／135 skipped** 變成 **4160 passed／44 skipped**
# （多跑 91 支，其中含 16 支 alembic 0010 契約、15 支三層 schema 契約這類「從未執行過的
# 斷言」）。「靠人記得」正是這個數字每輪都要重新盤點的原因，所以這裡改成**自動偵測**。
#
# 設計上的四條剎車（缺一都會把它從幫手變成災難來源）：
#   ① 使用者已顯式設過任一個 DSN 變數 ⇒ 一律不碰（顯式優先，本工具不猜使用者的意圖）。
#   ② `CI` 有值 ⇒ 不跑（雲端 job 自己在 `env:` 區塊宣告，不需要也不該被猜）。
#   ③ 本行程是 pytest（`PYTEST_CURRENT_TEST` 有值）⇒ 不跑。本函式會改**行程級** env，
#      而 `tests/tools/test_local_ci_gate.py` 會在同一個 pytest 行程裡直接呼叫 `main()`
#      ——不擋的話它會污染同行程其後所有測試（這條是實測踩到才補的，不是預想）。
#   ④ 那顆 DB 必須真的被 migrate 過（`alembic_version` 有列）才注入。沒有這一條，注入
#      DSN 只會把 92 支 skip 換成 92 支 `UndefinedTable` ——把訊號換成雜訊。
#      ⚠️ 刻意**只**驗到「有沒有被 migrate 過」這個粒度，**不**在這裡複製一份鏈完整性
#      判準：那件事的 SSOT 是 `tests/contract/test_alembic_0010_fk_three_step.py::
#      TestMigrationChainIntegrity`，而讓它對著這顆長壽 DB 轉紅正是 R79 D-skipped #5 的
#      目的（同一份知識住兩個家、只有一個家被改，是本 repo 最常復發的缺陷形態）。
#
# 🔴 R79 收輪（QA 實測）：本函式落地當輪**只有 local_ci_gate 這一個呼叫端**，而
# 「本機預設路徑」（`python -m pytest tests/ -q`，不設任何環境變數）根本不經過它
# ——量測值 136 skipped 一支都沒少。機制是好的，只是掛錯入口。現在第二個呼叫端是
# `AutoClaude/tests/conftest.py::pytest_configure`（pytest 一定會載），四條剎車完全
# 沿用本函式、不另複製一份判斷（同一份知識只有一個家）。
_AUTODETECT_OPT_OUT = "AUTOCLAUDE_NO_PG_AUTODETECT"
_PG_ENV_KEYS = ("AUTOCLAUDE_DB_DSN", "AUTOCLAUDE_TEST_PG_DSN")

#: 剖面標記：讓「這次 pytest 是在有沒有 PG 的條件下跑的」變成**輸出裡的一個事實**。
#:
#: 🔴 為何非有不可：`--census-only` 消費的是別的行程留下的 log，而剖面（`+pg`／`+nopg`）
#: 決定要拿哪一組天花板來比——兩組差 92 支。從 census 這一端**倒推**剖面是循環論證
#: （拿被判的東西決定判準），從 census 行程自己的環境變數推也是錯的：conftest 注入的是
#: **pytest 那個行程**的 env，不會傳給任何父行程或後續行程。所以只有產出那份 log 的人
#: 說得準，它必須把答案寫進 log 裡。找不到標記＝剖面量不到 ⇒ 一律紅（同「量不到 ≠ 量到零」）。
#: 刻意全 ASCII 且不含 `N passed` 樣式：`scripts/pytest_passed_count.sh` 以
#: `grep -oE '[0-9]+ passed'` 取值，任何新增輸出都不得改變它的答案。
PG_PROFILE_MARKER = "AUTOCLAUDE-PG-DSN-IN-EFFECT="
_PG_MARKER_RE = re.compile(re.escape(PG_PROFILE_MARKER) + r"([01])")

#: `--census-only` 的三態離開碼（WHY 見檔頭用法段）。
CENSUS_OK = 0
CENSUS_FAIL = 1
CENSUS_PROFILE_UNREGISTERED = 3


def _pg_reachable(host: str = "localhost", port: int = 5432, timeout: float = 0.5) -> bool:
    """TCP 探針。刻意不用 `docker ps`：DSN 指向的是一個 port，不是一個容器名——
    本機 PG、遠端 PG、compose 起的容器都應該一視同仁（同 CLAUDE.md〈斷言環境缺件前
    必先實查〉：要問的是「它在不在」，不是「它是怎麼來的」）。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def _pg_migrated(dsn: str) -> str | None:
    """`alembic_version` 有列 ⇒ 回 None（可注入）；否則回一句不能注入的理由。"""
    try:
        import psycopg2
    except ImportError:
        return "psycopg2 未安裝（`uv pip install -e '.[postgres]'`）"
    sync_dsn = re.sub(r"\+asyncpg", "", dsn)
    try:
        with psycopg2.connect(sync_dsn, connect_timeout=3) as conn, conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM alembic_version")
            if cur.fetchone()[0] < 1:
                return "alembic_version 是空的（這顆 DB 沒被 migrate 過）"
    except Exception as exc:  # noqa: BLE001 — 任何連線／查詢失敗都只是「不注入」
        return str(exc).strip().splitlines()[0]
    return None


def pg_autodetect(dsn: str = _PG_DSN) -> tuple[bool, str]:
    """回傳 `(是否注入了 DSN, 給人看的一句話)`。純副作用集中在這裡，便於測試。"""
    if os.environ.get("CI"):
        return False, "跳過：CI 環境（雲端 job 自己在 env: 區塊宣告 DSN）"
    if os.environ.get(_AUTODETECT_OPT_OUT):
        return False, f"跳過：{_AUTODETECT_OPT_OUT} 已設"
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False, "跳過：本行程是 pytest（改行程級 env 會污染同行程其他測試）"
    preset = [k for k in _PG_ENV_KEYS if os.environ.get(k)]
    if preset:
        return False, f"跳過：{'、'.join(preset)} 已由使用者顯式設定（顯式優先）"
    if not _pg_reachable():
        return False, "localhost:5432 沒有在聽 ⇒ 不注入（PG 相關測試維持 skip）"
    blocked = _pg_migrated(dsn)
    if blocked is not None:
        return False, f"偵測到 PG 但拒絕注入（{blocked}）——注入只會把 skip 換成 UndefinedTable"
    os.environ["AUTOCLAUDE_DB_DSN"] = dsn
    os.environ["AUTOCLAUDE_TEST_PG_DSN"] = dsn
    os.environ.setdefault("AUTOCLAUDE_ALLOW_INSECURE_DB", "1")
    return True, f"已注入 AUTOCLAUDE_DB_DSN／AUTOCLAUDE_TEST_PG_DSN = {dsn}"


def pg_dsn_in_effect() -> bool:
    """這次跑測試的行程**實際上**有沒有 PG DSN（自己注入的與使用者顯式設的都算）。

    🔴 R79 收輪訂正：剖面此前取自 `pg_autodetect()` 的回傳值（＝「我有沒有注入」），
    於是「使用者自己 export 過 DSN」那條路上 `pg_autodetect` 回 False、剖面判成 `nopg`
    ——測試明明跑在有 PG 的條件下（44 支 skip），卻拿 `nopg` 的 118 上限去比，永遠通過。
    那不是紅，是**沒有鑑別力**，而且方向是「看起來很健康」。要問的是「DSN 在不在」，
    不是「它是怎麼來的」（同 `_pg_reachable` 的既有理由）。
    """
    return any(os.environ.get(k) for k in _PG_ENV_KEYS)


def pg_marker_line(in_effect: bool) -> str:
    """產出剖面標記行（唯一產生者；消費者＝`pg_in_effect_from_log`）。"""
    return f"{PG_PROFILE_MARKER}{1 if in_effect else 0}"


def pg_in_effect_from_log(text: str) -> bool | None:
    """從 pytest 輸出讀回剖面標記；找不到回 `None`（＝剖面量不到，不是「沒有 PG」）。"""
    hits = _PG_MARKER_RE.findall(text or "")
    return bool(int(hits[-1])) if hits else None


# ── R79（D-skipped #2）：runtime skipped 數的**分群天花板** ────────────────────
#
# 🔴 修前實況（當回合逐項實查）：全 repo 對「這次真的 skip 了幾支」零管轄——
# `PG_CONTRACT_MAX_SKIPPED` 是唯一天花板且只覆蓋 `pg-contract` 一個 CI job；**本檔對
# `skipped` 零字樣**；根層 runner 只印不判；ONBOARDING §7 自陳 `skipped=N` 刻意不在鎖內。
# 掌舵者問的那個數字沒有任何東西在替它說話，於是它可以無聲上升、而上升的樣子在摘要裡
# 長得像「乾淨」。逐支消除治不了復發（R76 壓到 158 後，R77／R78 又各自新增站點）。
# 判準與棘輪的 SSOT 住 `tools/lib/skip_tag_policy.py`（根層共用），本檔只是消費者。
#
# 🔴 R79 收輪（QA blocking）：`-rs` 區塊的解析器與**量測完整性**判準已一併移進
# `tools/lib/skip_group_policy.py`。搬家的理由不是整潔：QA 實測到的缺陷正好長在
# 「解析器在這裡、判準在那裡」的縫上——空輸出／缺 `-rs`／SKIPPED 前綴漂移三種輸入都
# 印「共 0 支」並回 **rc=0**，因為天花板只比大小、而塌掉的量測給出的 0 小於任何上限。
# 判準與它所依賴的解析器同住一個家，才有辦法讓「量不到」在進到天花板之前就先轉紅。


def _skip_profile(pg: bool) -> str:
    """剖面鍵：同一棵樹在「有 PG」與「沒 PG」下的健康值差 92 支，用同一個數字管必然
    一邊沒鑑別力、另一邊恆假紅；平台同理（Windows 上 POSIX-only 全 skip，mac 反過來）。
    剖面由**實測**決定，不是由人宣告。未登記的剖面會被判準點名並要求以實測值入表。"""
    return f"AutoClaude/tests@{sys.platform}+{'pg' if pg else 'nopg'}"


def skipped_reasons(pytest_output: str) -> list[str]:
    """`-rs` 區塊的理由清單（實作已上移政策 SSOT；本名保留給既有呼叫端）。"""
    return skip_group_policy.skipped_reasons(pytest_output)


def census_verdict(pytest_output: str, *, pg: bool) -> tuple[int, list[str]]:
    """純函式：回 `(離開碼, 要印的行)`。離開碼三態見 `CENSUS_*`。

    順序是判準的一部分：**量測完整性先於天花板**。反過來寫的話，塌掉的量測會先拿到
    「每一格都沒超過上限」這個綠章，而那正是 QA 抓到的原形態。
    """
    reasons = skip_group_policy.skipped_reasons(pytest_output)
    profile = _skip_profile(pg)
    census = skip_group_policy.skip_group_census(reasons)
    lines = [f"[skip census] {profile} 共 {len(reasons)} 支："
             + "／".join(f"{g}={n}" for g, n in census.items())]
    collapsed = skip_group_policy.skip_measurement_problems(pytest_output, len(reasons))
    if collapsed:
        lines.append("❌ skip 量測塌掉——這一份輸出量不到 skip 數，上面那行普查不可信：")
        lines += [f"   - {msg}" for msg in collapsed]
        return CENSUS_FAIL, lines
    problems = skip_group_policy.skip_group_census_problems(
        profile, census, reasons=reasons)
    if not problems:
        return CENSUS_OK, lines
    if not skip_group_policy.profile_registered(profile):
        lines.append(
            "⚠️ 剖面未登記——量測本身正常，但這個平台從來沒有人量過健康值，"
            "沒有天花板可比（advisory；把實測值入表即升級為阻斷）：")
        lines += [f"   - {msg}" for msg in problems]
        return CENSUS_PROFILE_UNREGISTERED, lines
    lines.append("❌ skip 分群天花板不合格（S3：skipped 數必須有人管）：")
    lines += [f"   - {msg}" for msg in problems]
    return CENSUS_FAIL, lines


def check_skip_census(pytest_output: str, *, pg: bool) -> int:
    """印分群普查並判天花板；回 0／1（呼叫端把它併進 pytest gate 的 rc）。

    🔴 本入口對「剖面未登記」仍判**紅**（`CENSUS_PROFILE_UNREGISTERED` 併成 1），與
    `--census-only` 的 advisory 刻意不同，而這個差異是有理由的、不是漏改：本入口是
    「我要 push 了，把全部東西跑一遍」的手動閘門，人就在現場，可以當場把實測值入表；
    `--census-only` 掛在 push 通道與 CI 上，那裡擋下一個從來沒人量過的平台是**誤擋**
    （沒有鑑別力的紅），不是嚴格。
    """
    rc, lines = census_verdict(pytest_output, pg=pg)
    print("\n" + "\n".join(lines))
    return 0 if rc == CENSUS_OK else 1


def census_only(log_path: str) -> int:
    """`--census-only <pytest 輸出檔>`：只判普查，回三態離開碼（見檔頭）。

    `-` ＝從 stdin 讀。push 通道走的就是這一條：`mktemp` 回的是 POSIX 路徑，而 Windows
    側的 python 是原生 exe（路徑會過 MSYS 參數轉換）——改用 shell 的重導向就完全繞開
    那一層。stdin 顯式以 UTF-8 解碼：skip 理由含中文，呼叫端的 codepage 不該決定它
    讀不讀得懂。

    🔴 R79 收輪：這裡刻意**讀 `stdin.buffer` 的位元組再自己 decode**，而不是就地把
    stdin 重新設定成 UTF-8 串流。後者是「強制 stdio 為 UTF-8」的**第二份實作**
    （唯一實作住 `tools/_stdio_utf8.py`，`tools/tests/test_platform_utils_dedup.py`
    的去重棘輪在守，收輪當回合實測 AutoClaude 那一格由基線升一而轉紅）。
    語意上也更貼切：這裡要的只是「**這一次讀取**用什麼編碼」，不是改掉整個行程的
    stdio 狀態。`.buffer` 不存在時（測試以 `io.StringIO` 替身注入）退回直接讀字串。

    🔴 附帶一個當回合踩到的教訓：**這段 WHY 的第一版把那個被禁的呼叫逐字拼了出來**，
    而去重棘輪掃的是原始碼字面、不分程式碼與註解 ⇒ 複本數照樣是升的，紅燈原封不動。
    解釋「我為什麼不用 X」時把 X 的字面寫進檔案，在被機械判讀的面上等於又用了一次 X。
    """
    if log_path == "-":
        buf = getattr(sys.stdin, "buffer", None)
        text = (buf.read().decode("utf-8", "replace") if buf is not None
                else sys.stdin.read())
        return _census_from_text(text)
    path = Path(log_path)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"❌ [skip census] 讀不到 pytest 輸出檔 {path}：{exc}"
              "——通道自己壞了，不得當成「沒有 skip」")
        return CENSUS_FAIL
    return _census_from_text(text)


def _census_from_text(text: str) -> int:
    """已取得輸出之後的共同尾段（剖面標記 → 判準 → 印出）。"""
    pg = pg_in_effect_from_log(text)
    if pg is None:
        print(f"❌ [skip census] 這份輸出裡找不到剖面標記 `{PG_PROFILE_MARKER}`"
              "——它由 AutoClaude/tests/conftest.py 的 pytest_terminal_summary 印出。"
              "標記不在＝要嘛這不是 AutoClaude 測試樹的輸出、要嘛那段被拿掉了；"
              "兩種都代表**剖面量不到**，此時任何一組天花板的比較結果都沒有意義。")
        return CENSUS_FAIL
    rc, lines = census_verdict(text, pg=pg)
    print("\n".join(lines))
    return rc


def parse_args(argv: list[str]) -> tuple[bool, bool, list[str]]:
    """解析參數（語意照收斂前 .sh 逐參數迴圈）。

    --act / --pg 為旗標，可出現在任意位置；首個非旗標參數起「整批取代」預設
    pytest 參數（而非附加），其後的非旗標參數依序累積。
    """
    do_act = False
    do_pg = False
    pytest_args = list(DEFAULT_PYTEST_ARGS)
    overridden = False
    for arg in argv:
        if arg == "--act":
            do_act = True
        elif arg == "--pg":
            do_pg = True
        else:
            if not overridden:
                pytest_args = []
                overridden = True
            pytest_args.append(arg)
    return do_act, do_pg, pytest_args


def _stream(cmd: list[str]) -> int:
    """直通輸出執行子行程（繼承 stdio）；FileNotFoundError 等交由 run_gate 統一判 FAIL。"""
    return subprocess.run(cmd).returncode


def _run_quiet(cmd: list[str]) -> int:
    """靜音執行（對齊 .sh 的 `>/dev/null 2>&1 || true` 清理語意）；任何失敗都不外拋。"""
    try:
        return subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode
    except OSError:
        return 1


def _hooks_liveness_advisory() -> None:
    """git hooks liveness 偵測（警告不擋）。

    repo 搬移/改名或未安裝時 dispatcher hooks 會靜默失效（實證）；CI 環境（CI 有值）
    跳過（GitHub/act 環境無 hooks 屬正常）。偵測邏輯抽共用（S11）：見 monorepo 根
    tools/check_hooks_liveness.py（單一真相源）。advisory：任何探測失敗（含腳本
    自身 rc != 0 / 直譯器炸掉）都不得影響閘門本體——對齊 .ps1 的 try/catch 語意。
    """
    if os.environ.get("CI"):
        return
    script = MONO_ROOT / "tools" / "check_hooks_liveness.py"
    if not script.is_file():
        return
    try:
        subprocess.run([sys.executable, str(script)])
    except OSError:
        pass


# ---------------------------------------------------------------------------
# 各 gate（名稱字串與順序為凍結介面——由 tests/tools/test_local_ci_gate.py 的
# _BASE_GATES 精確等值測試機械凍結，文件（CLAUDE.md/Guide）亦引用這些字樣，勿改；
# 另一道獨立訊號＝根層 dispatcher pre-push AutoClaude leg 直跑 pytest，不經本檔）
# ---------------------------------------------------------------------------

def gate_editable() -> int:
    """0. editable 哨兵：autoclaude 套件須位於本 repo 根之下（取證紀律 #19）。

    動態比對 repo 根（勿硬編碼資料夾名——clone 到任何目錄名皆應 PASS）。in-process
    import 時 sys.path[0] 為 tools/（無 cwd 遮蔽），真正檢驗 editable 安裝指向，
    比舊 `python -c`（sys.path[0]=cwd，源碼樹恆遮蔽 site-packages）更貼近哨兵原意。
    """
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, encoding="utf-8", errors="replace",
        )
        top = proc.stdout.strip() if proc.returncode == 0 else ""
    except OSError:
        top = ""  # 對齊 .sh 的 `git rev-parse … || pwd` 回退
    if not top:
        top = os.getcwd()
    import autoclaude  # 延遲 import：未安裝（ImportError）由 run_gate 統一判 FAIL

    pkg = Path(autoclaude.__file__).resolve()
    root = Path(top).resolve()
    ok = root == pkg or root in pkg.parents
    print("autoclaude:", pkg)
    print("repo root :", root)
    return 0 if ok else 1


def gate_loc() -> int:
    """1. LOC 預算。"""
    return _stream([sys.executable, "tools/check_loc_budget.py"])


def gate_claudemd() -> int:
    """2. CLAUDE.md <= 400 行。

    行計數採 .ps1 的 ReadAllLines 語意（末行無換行符仍計 1 行）——為 wc -l
    （只數 \\n）的超集合，較保守；檔案以換行結尾時兩者相等。
    """
    with open(REPO_ROOT / "CLAUDE.md", encoding="utf-8", errors="replace") as fh:
        n = sum(1 for _ in fh)
    if n > 400:
        print(f"CLAUDE.md={n} > 400")
        return 1
    print(f"CLAUDE.md={n} lines OK")
    return 0


def gate_claudemd_line() -> int:
    """2b. CLAUDE.md 單行 <= 800 codepoint（contract test）。"""
    return _stream([
        sys.executable, "-m", "pytest",
        "tests/contract/test_claude_md_no_long_lines.py", "-q", "--tb=short",
    ])


def gate_snapshot() -> int:
    """3. snapshot 可重現。"""
    return _stream([sys.executable, "tools/snapshot_sync.py", "--check"])


def gate_importlinter() -> int:
    """4. import-linter（未安裝時同收斂前語意：印指引並判 FAIL）。"""
    exe = shutil.which("lint-imports")
    if exe is None:
        print("lint-imports 未安裝（pip install -e '.[lint]'）")
        return 1
    return _stream([exe])


def _stream_capture(cmd: list[str]) -> tuple[int, str]:
    """直通輸出**並**留一份給判準看。

    為何不用 `subprocess.run(capture_output=True)`：那會讓使用者盯著一片空白等 90 秒
    （pytest 整段輸出到結束才一次吐出）。為何不用 `| tee`：本 repo 剛在 R79 修掉
    `.github/workflows/autoclaude-ci.yml` 的同一個坑——管線會吞 rc。這裡兩者都要。
    """
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        encoding="utf-8", errors="replace", bufsize=1,
    )
    chunks: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(line)
        chunks.append(line)
    sys.stdout.flush()
    return proc.wait(), "".join(chunks)


def gate_pytest(pytest_args: list[str]) -> int:
    """5. pytest（參數可被位置參數整批取代，見 parse_args）。

    R79：跑完順手判一次 **skip 分群天花板**（見 `check_skip_census`）。
    🔴 只在「使用者沒有覆寫 pytest 參數」時判——`-k foo` 只跑一小撮測試，那個 census
    是另一個母體，拿去比全樹的天花板必然是假綠（甚至假紅）。判準的比較對象不得隨
    「被它所判的動作」而改變，這是 R75 升為機械物的頭號教訓。
    """
    if pytest_args != DEFAULT_PYTEST_ARGS:
        return _stream([sys.executable, "-m", "pytest", *pytest_args])
    rc, output = _stream_capture([sys.executable, "-m", "pytest", *pytest_args])
    census_rc = check_skip_census(output, pg=pg_dsn_in_effect())
    return rc or census_rc


def gate_pg() -> int:
    """選配：PG 契約測 via docker-compose.ci.yml（pg17）。

    --wait：等 healthcheck 通過才回（慢機不會 PG 未 ready 就跑 alembic）。
    alembic rc 防吞：migration 失敗即清理容器並判 FAIL，不讓後續 pytest rc 蓋過。
    alembic 以 `python -m alembic` 執行（同 venv 同直譯器；bare `alembic` 缺裝時
    .sh 是 rc=127 判 FAIL，此處為 module not found rc != 0，殊途同歸且必經清理）。
    """
    if _stream([*_PG_COMPOSE, "up", "-d", "--wait"]) != 0:
        print("docker compose up --wait 失敗")
        return 1
    # 全程用 asyncpg DSN，與 CI 一致（alembic/env.py 會自動 strip +asyncpg 改 psycopg2）；
    # export 至行程環境（對齊 .sh export 語意——其後 gate 亦可見）
    os.environ["AUTOCLAUDE_DB_DSN"] = _PG_DSN
    os.environ["AUTOCLAUDE_TEST_PG_DSN"] = _PG_DSN
    os.environ["AUTOCLAUDE_ALLOW_INSECURE_DB"] = "1"
    if _stream([sys.executable, "-m", "alembic", "upgrade", "head"]) != 0:
        print("alembic upgrade head 失敗")
        _run_quiet([*_PG_COMPOSE, "down", "-v"])
        return 1
    rc = _stream([
        sys.executable, "-m", "pytest",
        "tests/contract/test_pg_state_repository_contract.py", "-q", "--tb=short",
    ])
    _run_quiet([*_PG_COMPOSE, "down", "-v"])
    return rc


def gate_act() -> int:
    """選配：act 在 Linux 容器跑真 CI（test job）。

    POSIX 走 bash 載具跑 run_act.sh；Windows 以 PowerShell 載具 `-File` 呼叫
    run_act.ps1（勿用 -Command 包裹——會吞 exit code 假綠，useMacWin 啟動提示詞
    修漏史料）。探測順序 powershell → pwsh：對齊 tools/dev_start.py 先例與
    Local_CI_Parity_NextAction「pwsh→powershell（本機僅 PS5.1）」修正。
    """
    if platform_utils.is_windows():
        shell = shutil.which("powershell") or shutil.which("pwsh")
        if shell is None:
            print("找不到 PowerShell（powershell / pwsh）— 無法執行 tools/run_act.ps1")
            return 1
        return _stream([
            shell, "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(REPO_ROOT / "tools" / "run_act.ps1"), "-Job", "test",
        ])
    return _stream(["bash", str(REPO_ROOT / "tools" / "run_act.sh"), "--job", "test"])


# ---------------------------------------------------------------------------
# 閘門編排
# ---------------------------------------------------------------------------

def build_gates(
    do_act: bool, do_pg: bool, pytest_args: list[str]
) -> list[tuple[str, Callable[[], int]]]:
    """組出 gate 清單（名稱與順序為凍結介面；--pg 先於 --act，照收斂前 .sh/.ps1）。"""
    gates: list[tuple[str, Callable[[], int]]] = [
        ("editable sentinel", gate_editable),
        ("LOC budget", gate_loc),
        ("CLAUDE.md <=400", gate_claudemd),
        ("CLAUDE.md line<=800", gate_claudemd_line),
        ("snapshot --check", gate_snapshot),
        ("import-linter", gate_importlinter),
        # 延遲查全域名（勿綁死 default）：測試 monkeypatch gate_pytest 後仍需生效
        ("pytest", lambda: gate_pytest(pytest_args)),
    ]
    if do_pg:
        gates.append(("PG contract (pg17)", gate_pg))
    if do_act:
        gates.append(("act CI (Linux test job)", gate_act))
    return gates


def run_gate(name: str, fn: Callable[[], int], results: list[tuple[str, str]]) -> None:
    """執行單一 gate 並收集結果（逐項收集不中斷，對齊 .ps1 Continue 語意）。

    gate 執行失敗（FileNotFoundError 等例外）判 FAIL 不炸——對齊 .ps1 try/catch。
    """
    print(f"\n===== [{name}] =====", flush=True)
    try:
        rc = int(fn() or 0)
    except Exception as exc:  # KeyboardInterrupt 不攔（BaseException 直接外拋）
        print(f"[{name}] 例外：{exc}", flush=True)
        rc = 1
    status = "PASS" if rc == 0 else "FAIL"
    print(f"[{name}] {status} (rc={rc})", flush=True)
    results.append((name, status))


def main(argv: list[str] | None = None) -> int:
    # 自身 stdout/stderr best-effort UTF-8（✅/❌ 於非 UTF-8 終端不崩潰）；
    # 子行程統一 PYTHONUTF8=1（薄殼已先設，此處兜底 direct 呼叫路徑）
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass
    os.environ["PYTHONUTF8"] = "1"

    # 🔴 R69（DEF-101-702／R68-19）：`-h/--help` 原本會被 parse_args 當成「首個非旗標參數」
    # 而整批取代 pytest 預設參數 ⇒ 使用者想看用法，實際跑掉的是 editable 哨兵／LOC／
    # CLAUDE.md／snapshot／import-linter 整套閘門（全跑完才輪到 pytest 印 help）。同族入口
    # bootstrap_core／integration_gate_core 都已 fail-loud，本檔是最後一個沒跟上的。
    # 刻意**只**攔 help、不攔未知旗標：本檔的 CLI 契約逐字寫著「非 --act/--pg 參數整批
    # 取代預設 pytest 參數」，未知旗標是合法輸入（交給 pytest 自己判），攔了會改語意。
    # 位置在 os.chdir 之前——印用法不該有任何副作用。
    raw_argv = sys.argv[1:] if argv is None else argv
    if any(a in ("-h", "--help") for a in raw_argv):
        print((__doc__ or "").strip(), flush=True)
        return 0

    # `--census-only <log>`：只判 skip 普查。刻意排在 `os.chdir` 與 PG 自動偵測**之前**
    # ——它消費的是別的行程留下的輸出，本身不得跑 gate、不得注入任何環境變數、也不該
    # 因為 cwd 換過而讓呼叫端傳進來的相對路徑失效（push 通道傳的是 mktemp 的絕對路徑，
    # 但相對路徑同樣要能用）。argv 形狀刻意嚴格：多給或少給參數一律 fail-loud，不猜。
    if "--census-only" in raw_argv:
        if raw_argv[0] != "--census-only" or len(raw_argv) != 2:
            # 🔴 fail-loud 而不是「當成 pytest 參數」：本檔的 CLI 契約是「首個非旗標參數
            # 起整批取代預設 pytest 參數」，於是 `… foo --census-only bar` 這種寫法會**跑完
            # 整套閘門**再把三個字串丟給 pytest——使用者想要的是幾毫秒的普查，拿到的是
            # 分鐘級的全套執行外加一個看不懂的 pytest 錯誤。同 `-h/--help` 那一段的理由。
            print("用法：python tools/local_ci_gate.py --census-only <pytest 輸出檔｜->"
                  "（本模式不接受其他參數）", flush=True)
            return CENSUS_FAIL
        return census_only(raw_argv[1])

    os.chdir(REPO_ROOT)

    do_act, do_pg, pytest_args = parse_args(raw_argv)
    _hooks_liveness_advisory()

    # R79（S3）：讓「甲類 skip」預設就會跑。刻意**不**做成一道 gate——gate 名稱與順序是
    # 凍結介面（`tests/tools/test_local_ci_gate.py::_BASE_GATES` 精確等值），加一格會破壞
    # 呼叫端／smoke／文件的比對。這一步與 `_hooks_liveness_advisory()` 同性質：
    # main() 內的前置副作用，本身不判 rc（判 rc 的是它讓誰跑起來）。
    # 🔴 R79 收輪：本檔已不再自己記「有沒有注入」——剖面一律現查 `pg_dsn_in_effect()`
    # （WHY 見該函式）。這裡只保留給人看的一行說明。
    _, why = pg_autodetect()
    print(f"[PG autodetect] {why}", flush=True)

    results: list[tuple[str, str]] = []
    for name, fn in build_gates(do_act, do_pg, pytest_args):
        run_gate(name, fn, results)

    # ----- 總結（字樣為凍結介面）-----
    print("\n========== 本機 CI 閘門總結 ==========", flush=True)
    failed = 0
    for name, status in results:
        print(f"  {name:<22} {status}")
        if status == "FAIL":
            failed += 1
    if failed:
        print(f"\n❌ {failed} 項失敗 — 請於本機修復後再 push。")
        return 1
    print("\n✅ 全部通過 — 可安全 push。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
