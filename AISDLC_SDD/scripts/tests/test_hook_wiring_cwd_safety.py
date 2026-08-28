"""Hook wiring cwd 安全性 contract — 四方複審第四輪 P0 回歸鎖.

為何重要（Rule 9 / Rule 12 fail-loud）：三份 settings.json（monorepo 根 router、
AutoClaude、AISDLC_SDD LATEST 版）的 hook command 原為「裸 `python <相對路徑>`」，
hook 子行程的 cwd ≠ 對應專案根時（Agent SDK spawn 子 session、Bash 工具 cd 殘留），
python 找不到腳本的退出碼**恰為 2**＝Claude Code PreToolUse 的「deny」語意 →
matcher 涵蓋的全部工具（Write/Edit/Read/Bash/Task）被連鎖硬阻斷，session 完全癱瘓
（四方複審第四輪 SD P0 live 實證）。修法＝python -c shim：python 自行讀
CLAUDE_PROJECT_DIR 環境變數錨定專案根（不經 shell 變數展開，Windows cmd 亦可用），
缺檔 fail-open exit 0（恢復 ONBOARDING §4 文件宣稱的「靜默失效」語意）。

本鎖三道防線：
1. 行為鎖（缺檔情境）：每條 hook command 在「cwd=空目錄 + 無 CLAUDE_PROJECT_DIR」
   下執行必須 exit 0（絕不可為 2 = deny）。
2. 行為鎖（錨定情境）：根 router command 在「cwd=空目錄 + CLAUDE_PROJECT_DIR=根」
   下必須真正執行 router（stdout 出現 hookSpecificOutput）。
3. 結構鎖：每條 command 必須引用 CLAUDE_PROJECT_DIR（防止回退成裸相對路徑）。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

from scripts import router_hook_coverage_lint as lint


def _sdd_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _monorepo_root() -> str:
    return os.path.dirname(_sdd_root())


# exec form 的 POSIX 載具只有一個家（`tools/lib/hook_wiring.LAUNCHER_REL`）。
_LAUNCHER = os.path.join(_monorepo_root(), ".claude", "hooks", "_hook_launcher.py")


def _running_pythonw() -> str:
    """Windows 側「自己那一半」材料化用：**目前正在跑**這個測試的直譯器旁邊那支
    GUI 子系統 sibling（`sys.executable` 同目錄）。

    刻意不用 repo-root 相對 join 拼出這個路徑：那個目錄是 gitignore 排除的本機產物，
    不可能出現在任何 git diff 裡，寫成 repo-root 相對 join 會被
    `test_ci_paths_cover_root_consumers.py` 的掃描器誤判成「需要 CI paths 覆蓋的根層
    消費檔」（它認的是磁碟上存在即算數，不分辨 gitignore；連本段說明文字裡若照樣寫出
    那個 join 字面都會被同一支掃描器命中——這正是本函式為何連文件裡都不示範那個寫法）。
    用 `sys.executable` 推導既避開誤判，語意也更正確——用的就是真正在跑的那個 venv。
    """
    return os.path.join(os.path.dirname(sys.executable), "pythonw.exe")


def _pyvenv_cfg_text() -> str:
    """材料化用的 `pyvenv.cfg` 內容 — **合成**，不是複製本機既有那一份。

    🔴 DEF-200-232（windows-compat-ci 連續 6 次紅的第一支）：原實作是
    `shutil.copy(<sys.executable 上兩層>/pyvenv.cfg, …)`，內含一個沒說出口的前提
    「跑本測試的直譯器一定住在 venv 裡」。那個前提在 CI 上為假——GitHub
    `actions/setup-python` 交出來的是 **base install**（直譯器直接住在 prefix 底下、
    旁邊與上一層都沒有 `pyvenv.cfg`）⇒ `FileNotFoundError` 在載具材料化就炸，
    一條 hook 都還沒驗到，而炸點與被測物完全無關。

    合成才是對的形狀：`pyvenv.cfg` 的內容本來就只是「指回 base install」，而那個值
    `sys.base_prefix` **兩種情境都答得出來**（在 venv 裡＝它的 base；在 base install
    裡＝自己）。複製只是「剛好在 venv 裡時取得同一個值」的脆弱寫法。
    本機實測（Windows，以 pyenv base install 當來源模擬 CI 形狀）：合成 cfg ＋ 複製
    `pythonw.exe` 的假 venv 起得來，缺目標腳本時 rc=0（fail-open）。
    """
    v = sys.version_info
    return (
        f"home = {sys.base_prefix}\n"
        "include-system-site-packages = false\n"
        f"version = {v.major}.{v.minor}.{v.micro}\n"
    )


def _settings_paths() -> list[str]:
    """三份受 contract 保護的 settings.json：根 router、AutoClaude、SDD LATEST。"""
    paths = [
        os.path.join(_monorepo_root(), ".claude", "settings.json"),
        os.path.join(_monorepo_root(), "AutoClaude", ".claude", "settings.json"),
    ]
    latest = lint.analyze(_sdd_root()).get("latest")
    if latest:
        paths.append(os.path.join(_sdd_root(), latest, ".claude", "settings.json"))
    return paths


def _all_hook_entries(settings_path: str) -> list[dict]:
    """三份 settings 內全部 `type=command` 的 hook 條目（原始 dict，不只 command 字串）。

    🔴 R80：本檔原本取的是 `hook["command"]` 字串、再以 `shell=True` 跑它。Claude Code
    的 hook 條目有兩種形態：shell form 的 `command` 本來就是要交給 shell 的一整串；
    **exec form**（帶 `args`；Windows 上不經 `bash.exe` 故不閃 console 視窗）的 `command`
    只是一個**執行檔路徑**、真正的引數在 `args` 裡。拿後者去 `shell=True` 會變成
    「跑一個叫 `${CLAUDE_PROJECT_DIR}/.venv/Scripts/pythonw.exe` 的指令」＝rc≠0，
    而本檔第一道防線正是在斷言 rc==0（fail-open）⇒ 形態一轉就會假紅。
    改成保留整個條目、交由 `_run()` 依形態決定怎麼起。
    """
    with open(settings_path, encoding="utf-8") as f:
        doc = json.load(f)
    entries: list[dict] = []
    for event_blocks in doc.get("hooks", {}).values():
        for blk in event_blocks:
            for hook in blk.get("hooks", []):
                if hook.get("type", "command") == "command":
                    entries.append(hook)
    return entries


def _describe(hook: dict) -> str:
    """給斷言訊息用的可讀描述（兩種形態都要看得懂它會跑什麼）。"""
    return " ".join(lint._hook_wiring().hook_entry_argv(hook))


def _run(hook: dict, cwd: str, extra_env: dict[str, str] | None = None,
         stdin_payload: str = "") -> subprocess.CompletedProcess:
    """依條目形態起它：shell form 走 `shell=True`；exec form 走 argv list（不經 shell）。

    exec form 的 `${CLAUDE_PROJECT_DIR}` 由 CC 展開，測試環境沒有 CC ⇒ 這裡自己展開成
    `extra_env` 給的值（未給時展開成 cwd，重現「cwd≠專案根」那個 P0 情境）。
    """
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    # 測試環境不啟 SDD 守門，確保 router 走休眠快路徑
    env.pop("SDD_ACTIVE_VERSION", None)
    if extra_env:
        env.update(extra_env)
    wiring = lint._hook_wiring()
    common = {
        "cwd": cwd, "env": env, "input": stdin_payload, "capture_output": True,
        "text": True, "encoding": "utf-8", "errors": "replace", "timeout": 60,
    }
    argv = wiring.hook_entry_argv(hook)
    if not wiring.is_exec_form(hook):
        return subprocess.run(argv[0], shell=True, **common)
    project_dir = env.get("CLAUDE_PROJECT_DIR", cwd)
    return subprocess.run(wiring.expand_tokens(argv, project_dir), **common)


def _viable(hook: dict, project_dir: str, *, exists=os.path.exists) -> bool:
    """本平台上這個條目的載具跑不跑得起來（跨平台配對的另一半是刻意 fail-open）。

    `exists` 是注入點：用來構造「這台機器上 venv 沒被材料化」情境（見
    `_resolve_carriers()` 與其紅綠自證兩支測試），不是給生產路徑用的。
    """
    return lint._hook_wiring().carrier_available(hook, project_dir, exists=exists)


def _as_running_interpreter(hook: dict) -> dict | None:
    """把「宣告 Windows venv 載具」的條目換成用**目前這個直譯器**跑同一條 shim 鏈的
    等價條目；不是那一種載具就回 `None`（不代換）。

    🔴 DEF-200-232（windows-compat-ci 連續 6 次紅的第二支）：這裡要切開兩件被
    `carrier_available()` 綁在一起、但責任歸屬完全不同的事——

      (a) **佈線缺陷**：本平台那一半的載具從 settings 消失／被寫成別的東西。
          那是 repo 內容問題，任何機器上都必須紅。
      (b) **機器姿態**：載具形態正確，但它指到的 venv 是 gitignored 的**本機產物**，
          在 fresh clone 與 CI runner 上本來就不在。**這不是 repo 缺陷**——CI 從不
          執行 Claude Code hook（根 CLAUDE.md〈hook 載具〉逐字如此劃界），而
          「這台機器上載具在不在」早就有自己的家：
          `tools/check_hooks_liveness.py::check_claude_hook_carriers`（對三份活躍
          settings 逐份查存在性，CI 刻意跳過那一層）。

    原本的 `assert runnable` 把 (b) 也判成紅，於是 windows-compat-ci 在
    `AutoClaude/.venv` 從未被建立的 runner 上連續 6 次紅，紅的內容與當輪改動無關；
    而同一份「載具存在嗎」的知識同時住在兩個家，正是本 repo 的頭號病。

    代換的射程刻意收到最窄，這樣它遮得住的只有 (b)：**只有 Windows、且 argv[0] 正是
    那個唯一合法的 venv 載具**（`win_carrier_kind()=="venv"`，字面被改壞就對不上）
    才代換。POSIX 那一半的載具是 **git tracked 的檔**，它缺席就是真缺陷 ⇒ 由
    `os.name` 守住、一律不代換。
    """
    wiring = lint._hook_wiring()
    argv = wiring.hook_entry_argv(hook)
    if os.name != "nt" or len(argv) < 2 or not wiring.is_exec_form(hook):
        return None
    if wiring.win_carrier_kind(argv[0]) != "venv":
        return None
    return {"type": "command", "command": sys.executable, "args": list(argv[1:])}


def _resolve_carriers(hooks: list[dict], project_dir: str,
                      *, exists=os.path.exists) -> list[dict]:
    """把條目清單收斂成「本平台真的 spawn 得動」的那些（必要時代換成目前直譯器）。

    條目數刻意**不因代換而增減**：可跑的原樣留下，只有「宣告正確但沒材料化」的
    Windows venv 載具被代換，另一個平台那一半仍照樣被丟掉（fail-open 的那一半）。
    回空清單＝本平台在這份佈線裡已無任何跑得動的條目 ⇒ 呼叫端必須出聲。
    """
    out: list[dict] = []
    for hook in hooks:
        if _viable(hook, project_dir, exists=exists):
            out.append(hook)
            continue
        substitute = _as_running_interpreter(hook)
        if substitute is not None:
            out.append(substitute)
    return out


def _fake_project_root(tmp: str) -> str:
    """tmp 內一個**空的**假專案根，深度足夠讓 `../`／`../../` 載具仍落在 tmp 內。

    🔴 R84 W3 收尾：本鎖轉 exec form 後在 mac 上 `checked==0`（反空轉斷言當場說話）。
    成因是**構造情境本身失真**，不是判準太嚴——原構造把 `CLAUDE_PROJECT_DIR` 留空，
    於是 `_run()` 把佔位符展開成 tmp，連**載具**（`_hook_launcher.py`）都被解析到
    tmp 底下而不存在 ⇒ `_viable()` 正確地把每一條都判成「本平台跑不起來」，一條都沒驗。
    但那不是本鎖要測的東西：真實情境裡 CC 一定會注入 CLAUDE_PROJECT_DIR，載具**一定
    在**，會缺的是**目標腳本**（被刪／改名／子專案沒同步）。所以正確的構造是
    「載具在、目標缺」——把載具照它自己宣告的相對位置擺好，專案根維持全空。
    深度取 3 是因為現存條目最深的載具前綴是 `../../`（SDD LATEST 版目錄在 repo 第 2 層）；
    不夠深時 normpath 會把路徑帶到 tmp 之外（＝往系統暫存區的父目錄寫檔）。
    """
    root = os.path.join(tmp, "lvl0", "lvl1", "lvl2")
    os.makedirs(root, exist_ok=True)
    return root


def _materialise_carrier(hook: dict, project_root: str) -> None:
    """把**本平台**真正會被 spawn 的載具材料化到這個條目宣告的位置——只造載具，不造
    任何目標腳本。

    🔴 R97（round-label-ok：非帳本追蹤的正式輪，僅沿用便於追蹤的標籤）：跨平台配對必須**各造自己那一半**，不是「只造 POSIX 那一半、Windows 永遠
    不造」。後者在 POSIX 上恰好對，因為那一半就是本平台會 viable 的那一半；但直接搬到
    Windows 上跑同一份邏輯時，POSIX 載具因 `.py` + `os.name=="nt"` 本就恆判不可跑
    （`carrier_available()`），而 Windows 那一半从未被材料化 ⇒ 全部條目 `checked==0`，
    反空轉斷言在 Windows 上恆假（R84 docstring 記載的是 mac 那一半的等價修復，Windows
    這一半此前一直缺席）。修法：依 `os.name` 材料化「自己」那一半，另一半維持不造
    （在**另一個**平台上執行到才會需要它，而那正是它應該保持 fail-open 的一半）。

    Windows 側材料化需要兩個檔（缺一 GUI 子系統直譯器啟動不了、找不到 base install）：
    直譯器本體＋緊鄰的 `pyvenv.cfg`（venv 啟動器靠它定位 base Python install；內容
    **合成**而非複製，理由見 `_pyvenv_cfg_text()`）。只材料化 `kind=="venv"` 的
    條目：`kind=="path"`（裸執行檔名，靠 PATH 解析）`carrier_available()` 本就無條件
    視為 viable，不需要、也不該材料化任何檔案。
    """
    wiring = lint._hook_wiring()
    argv = wiring.hook_entry_argv(hook)
    if not argv or not wiring.is_exec_form(hook):
        return
    if wiring.is_posix_carrier(argv[0]):
        if os.name == "nt":
            return  # 另一半：留給 carrier_available() 自己判死，不材料化
        exe = wiring.expand_tokens([argv[0]], project_root)[0]
        os.makedirs(os.path.dirname(exe), exist_ok=True)
        # copyfile 不帶權限位 ⇒ 複本沒有 exec bit，spawn 會拿到 EACCES 而不是我們要測的
        # 「目標缺檔」路徑。用 copy（帶模式）並顯式補上 exec bit，兩層都不依賴來源的模式。
        shutil.copy(_LAUNCHER, exe)
        os.chmod(exe, 0o755)
        return
    if os.name == "nt" and wiring.win_carrier_kind(argv[0]) == "venv":
        # 多個條目常共用同一個相對路徑（同一個 fake project_root）⇒ 冪等：已經材料化過
        # 就不再覆寫。除了省 I/O，也避開「前一次 spawn 的行程剛結束、Windows 尚未完全
        # 釋放該 .exe 的檔案鎖」這種瞬時競態（PermissionError，本機實測會發生）。
        exe = wiring.expand_tokens([argv[0]], project_root)[0]
        if not os.path.exists(exe):
            os.makedirs(os.path.dirname(exe), exist_ok=True)
            shutil.copy(_running_pythonw(), exe)
            cfg = os.path.join(os.path.dirname(os.path.dirname(exe)), "pyvenv.cfg")
            if not os.path.exists(cfg):
                with open(cfg, "w", encoding="utf-8", newline="\n") as f:
                    f.write(_pyvenv_cfg_text())
        if len(argv) > 1:
            launcher = wiring.expand_tokens([argv[1]], project_root)[0]
            if not os.path.exists(launcher):
                os.makedirs(os.path.dirname(launcher), exist_ok=True)
                shutil.copy(_LAUNCHER, launcher)


def test_missing_target_is_fail_open_not_deny():
    """載具在、目標腳本缺，且 cwd≠專案根 → 必須 exit 0（絕不可 2=deny）。"""
    with tempfile.TemporaryDirectory() as tmp:
        checked = 0
        project_root = _fake_project_root(tmp)
        for settings in _settings_paths():
            for hook in _all_hook_entries(settings):
                _materialise_carrier(hook, project_root)
                if not _viable(hook, project_root):
                    continue  # 跨平台配對的另一半：CC 對 spawn 失敗是 fail-open
                res = _run(hook, cwd=tmp, extra_env={"CLAUDE_PROJECT_DIR": project_root},
                           stdin_payload="{}")
                checked += 1
                assert res.returncode == 0, (
                    f"hook 條目在 cwd≠專案根時未 fail-open（rc={res.returncode}，"
                    f"rc=2 會被 PreToolUse 視為 deny 而鎖死 session）：\n"
                    f"  settings: {settings}\n  entry: {_describe(hook)}\n"
                    f"  stderr: {res.stderr[:400]}"
                )
        # 反空轉：全部條目都被判成「本平台不可跑」時上面的迴圈一次都沒跑，
        # 而那與「全部通過」在 rc 上無法區分（R80 exec form 轉換的失明形態）。
        assert checked >= 3, f"本平台可跑的 hook 條目只有 {checked} 條 ⇒ 本鎖已近乎空轉"


def test_claude_project_dir_anchors_root_router():
    """cwd=空目錄但 CLAUDE_PROJECT_DIR=monorepo 根 → router 必須真正執行。"""
    root = _monorepo_root()
    settings = os.path.join(root, ".claude", "settings.json")
    wiring = lint._hook_wiring()
    hooks = [
        h for h in _all_hook_entries(settings)
        if any("sdd_hook_router" in rel
               for rel in wiring.hook_entry_targets(h, include_launcher=True))
    ]
    assert hooks, "根 settings.json 找不到 sdd_hook_router 佈線"
    runnable = _resolve_carriers(hooks, root)
    assert runnable, (
        "根 settings.json 有 sdd_hook_router 佈線，但**本平台一條都跑不起來** ⇒ "
        f"router 在這台機器上整支靜默失效。條目：{[_describe(h) for h in hooks]}"
    )
    with tempfile.TemporaryDirectory() as tmp:
        for hook in runnable:
            res = _run(hook, cwd=tmp, extra_env={"CLAUDE_PROJECT_DIR": root},
                       stdin_payload='{"tool_name": "Bash", "tool_input": {}}')
            assert res.returncode == 0, (
                f"錨定情境下 router 執行失敗（rc={res.returncode}）："
                f"{_describe(hook)}\n{res.stderr[:400]}"
            )
            assert "hookSpecificOutput" in res.stdout, (
                f"錨定情境下 router 未真正執行（stdout 無 hookSpecificOutput）："
                f"{_describe(hook)}"
            )


def _autoclaude_enforce_docs_path_hooks() -> tuple[str, list[dict]]:
    """(AutoClaude 專案根, 佈線裡**實際會跑到** `enforce_docs_path` 的那些條目)。"""
    ac_root = os.path.join(_monorepo_root(), "AutoClaude")
    settings = os.path.join(ac_root, ".claude", "settings.json")
    with open(settings, encoding="utf-8") as f:
        doc = json.load(f)
    wiring = lint._hook_wiring()
    hooks = [
        h
        for blk in doc["hooks"]["PreToolUse"]
        for h in blk["hooks"]
        if any("enforce_docs_path" in rel
               for rel in wiring.hook_entry_targets(h, include_launcher=True))
    ]
    return ac_root, hooks


def _assert_deny_semantics(entry: dict, ac_root: str) -> None:
    """跑一條已解析好的條目，斷言 shim 原樣傳遞目標腳本的 exit 2。"""
    payload = json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": "evil_probe.md", "content": "x"}}
    )
    with tempfile.TemporaryDirectory() as tmp:
        res = _run(entry, cwd=tmp, extra_env={"CLAUDE_PROJECT_DIR": ac_root},
                   stdin_payload=payload)
        assert res.returncode == 2, (
            f"錨定情境下 enforce_docs_path 未保留阻斷語意（rc={res.returncode}）——"
            f"shim 必須原樣傳遞目標腳本的 exit 2\n{res.stderr[:400]}"
        )


def test_claude_project_dir_anchors_autoclaude_deny_semantics():
    """AutoClaude 錨定情境：enforce_docs_path 經 shim 仍真執行且保留 exit 2 阻斷語意。"""
    ac_root, hooks = _autoclaude_enforce_docs_path_hooks()
    assert hooks, "AutoClaude settings.json 找不到 enforce_docs_path 佈線"
    # 🔴 R81：本檔轉成 exec form 之後，這裡不能再拿 `hooks[0]` 就跑——那是**Windows 載具**
    # 那一條（`.venv/Scripts/pythonw.exe`），在 mac/Linux 上 spawn 直接 FileNotFoundError，
    # 而跨平台配對的另一半本來就是刻意 fail-open、不是缺陷。與同檔 root router 那個 case
    # 用同一個 `_resolve_carriers()`；解析完為空要出聲（不得靜默跳過＝本平台整支失去 hook）。
    # 🔴 DEF-200-232：解析器對「宣告正確但本機沒材料化的 venv 載具」會代換成目前直譯器——
    # 「載具在這台機器上存不存在」的判定住 `tools/check_hooks_liveness.py`，不住這裡。
    runnable = _resolve_carriers(hooks, ac_root)
    assert runnable, (
        "AutoClaude settings.json 有 enforce_docs_path 佈線，但**本平台那一半連代換都"
        f"湊不出來** ⇒ 佈線裡已沒有本平台跑得動的條目。條目：{[_describe(h) for h in hooks]}"
    )
    _assert_deny_semantics(runnable[0], ac_root)


def test_autoclaude_deny_semantics_survives_a_machine_without_the_local_venv():
    """紅綠自證（綠面）：載具指到的 venv 未材料化時，阻斷語意仍必須被**真的驗到**。

    這就是 CI runner 的條件（`AutoClaude/.venv` 從未被建立）。刻意不是 skip：
    把「本機沒有那個 gitignored 產物」變成靜默跳過，等於用看不見換綠燈。
    """
    ac_root, hooks = _autoclaude_enforce_docs_path_hooks()

    def _no_venv(path: str) -> bool:
        return False if ".venv" in path.replace("\\", "/") else os.path.exists(path)

    runnable = _resolve_carriers(hooks, ac_root, exists=_no_venv)
    assert runnable, "無 venv 的機器上湊不出可跑的載具 ⇒ 上一支測試在 CI runner 上必炸"
    _assert_deny_semantics(runnable[0], ac_root)


def test_deny_carrier_resolution_stays_red_when_the_local_platform_half_is_missing():
    """紅綠自證（紅面）：本平台那一半從佈線消失時，代換必須湊不出來（真缺陷仍紅）。

    Windows 上餵它 POSIX 載具那一條、POSIX 上餵它 Windows 載具那一條——兩邊都必須
    解析成空。若代換被寫得太寬（例如不看 `win_carrier_kind`、或漏掉 `os.name` 守門），
    這裡會當場變綠。
    """
    wiring = lint._hook_wiring()
    ac_root, hooks = _autoclaude_enforce_docs_path_hooks()

    def _is_local_half(hook: dict) -> bool:
        argv = wiring.hook_entry_argv(hook)
        if not argv:
            return False
        if os.name == "nt":
            return wiring.win_carrier_kind(argv[0]) is not None
        return wiring.is_posix_carrier(argv[0])

    foreign_only = [h for h in hooks if not _is_local_half(h)]
    assert foreign_only, "前提不成立：佈線裡找不到另一個平台那一半，構造不出證偽情境"
    assert _resolve_carriers(foreign_only, ac_root) == [], (
        "只剩另一個平台那一半時仍解析出可跑的載具 ⇒ 代換的射程過寬，"
        f"會遮住真正的佈線缺陷。條目：{[_describe(h) for h in foreign_only]}"
    )


def test_claude_project_dir_anchors_latest_version_session_start():
    """SDD LATEST 版錨定情境：session_start 經 shim 真執行（stdout 出現 hookSpecificOutput）。"""
    latest = lint.analyze(_sdd_root()).get("latest")
    assert latest, "找不到最新演化版"
    v_root = os.path.join(_sdd_root(), latest)
    settings = os.path.join(v_root, ".claude", "settings.json")
    with open(settings, encoding="utf-8") as f:
        doc = json.load(f)
    hooks = [h for blk in doc["hooks"]["SessionStart"] for h in blk["hooks"]]
    assert hooks, f"{latest} settings.json 找不到 SessionStart 佈線"
    # 🔴 R84 W3：本份 settings 轉 exec form 之後，`hooks[0]` 是 **Windows 載具**那一條
    # （`../../.venv/Scripts/pythonw.exe`），在 mac/Linux 上 spawn 直接 FileNotFoundError。
    # 跨平台配對的另一半是刻意 fail-open、不是缺陷 ⇒ 與同檔 root router／AutoClaude
    # 兩個 case 用同一個 `_resolve_carriers()`；解析完為空要出聲（不得靜默跳過＝整支失去 hook）。
    runnable = _resolve_carriers(hooks, v_root)
    assert runnable, (
        f"{latest} settings.json 有 SessionStart 佈線，但**本平台一條都跑不起來** ⇒ "
        f"這台機器上該版 session_start 整支靜默失效。條目：{[_describe(h) for h in hooks]}"
    )
    with tempfile.TemporaryDirectory() as tmp:
        # SDD_HOOKS_DISABLE=1：disabled 分支仍輸出 hookSpecificOutput，足證 shim 真執行
        # 目標腳本，且不觸碰 v0.30 dogfooding FSM 狀態（bootstrap/reconcile 零副作用）
        res = _run(runnable[0], cwd=tmp,
                   extra_env={"CLAUDE_PROJECT_DIR": v_root, "SDD_HOOKS_DISABLE": "1"})
        assert res.returncode == 0, (
            f"錨定情境下 {latest} session_start 執行失敗（rc={res.returncode}）\n{res.stderr[:400]}"
        )
        assert "hookSpecificOutput" in res.stdout, (
            f"錨定情境下 {latest} session_start 未真正執行（stdout 無 hookSpecificOutput）"
        )


def test_commands_are_project_dir_anchored():
    """結構鎖：每個條目必須引用 CLAUDE_PROJECT_DIR（防回退成裸相對路徑）。

    R80：判斷面由「`command` 字串」擴成「`command` ＋ `args` 整串」——exec form 的錨定
    可能寫在 `args` 元素裡（實測 `${CLAUDE_PROJECT_DIR}` 在兩處都會被 CC 展開），
    只看 `command` 會把已錨定的條目誤判成未錨定。
    """
    for settings in _settings_paths():
        for hook in _all_hook_entries(settings):
            joined = _describe(hook)
            assert "CLAUDE_PROJECT_DIR" in joined, (
                f"hook 條目未經 CLAUDE_PROJECT_DIR 錨定（回退成 cwd 相對路徑會復發 P0）：\n"
                f"  settings: {settings}\n  entry: {joined}"
            )
