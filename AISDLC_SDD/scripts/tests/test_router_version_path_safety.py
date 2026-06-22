"""根 router `SDD_ACTIVE_VERSION` 路徑注入防護 — DEF-CLDREV-028（SA 鏡 F-01）回歸鎖.

為何重要（架構紅線：路徑注入 / 對外 I/O 安全）：`sdd_hook_router.py` 把 `SDD_ACTIVE_VERSION`
**原樣插值**進 `AISDLC_SDD/AISDLC_SDD_v{version}/.claude/hooks/<script>` 路徑後，唯一閘門
是 `target.is_file()`，通過即 `subprocess.run([python, target])`。修復前 `_normalize_version`
僅 strip + 去前導 v、不擋 `../`／絕對路徑／路徑分隔符 → 可逃逸 AISLDC_SDD 樹指向任意
`<dir>/.claude/hooks/<script>` 而被執行（路徑注入→RCE）。

本鎖機械守護縱深兩道修復不被回退：
  ① 語法白名單：version 須完整匹配「數字.數字」（正則 r"\\d+\\.\\d+"），惡意值一律
     以「格式非法」WARN 放行、**不** subprocess.run；
  ② 邊界斷言：resolved target 須落在 AISLDC_SDD 樹內。
正例（合法 0.19 → 確實路由）與負例（惡意值 → 拒路由且印新拒絕訊息）對稱覆蓋。
"""
from __future__ import annotations

import importlib.util
import io
import os
import types
from pathlib import Path
from unittest import mock


def _monorepo_root() -> Path:
    # test 檔在 AISDLC_SDD/scripts/tests/ → parents[3] = monorepo 整合層根。
    return Path(__file__).resolve().parents[3]


def _load_router():
    path = _monorepo_root() / ".claude" / "hooks" / "sdd_hook_router.py"
    spec = importlib.util.spec_from_file_location("sdd_hook_router_test", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    # 釘住 REPO_ROOT，避免測試環境殘留的 CLAUDE_PROJECT_DIR 影響正例 target 解析。
    mod.REPO_ROOT = _monorepo_root()
    return mod


class _FakeTtyStdin:
    def isatty(self) -> bool:
        return True  # 使 router 視為無 pipe，stdin_data="" 不阻塞


def _run_main(version: str, hook: str = "session_start"):
    mod = _load_router()
    calls: list = []
    fake_proc = types.SimpleNamespace(stdout="{}", stderr="", returncode=0)

    def _fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return fake_proc

    buf = io.StringIO()
    env = {"SDD_ACTIVE_VERSION": version, "SDD_ROUTER_QUIET": "1"}
    with mock.patch.object(mod.subprocess, "run", _fake_run), \
            mock.patch.object(mod.sys, "stdin", _FakeTtyStdin()), \
            mock.patch.object(mod.sys, "stdout", buf), \
            mock.patch.dict(os.environ, env, clear=False):
        rc = mod.main(["sdd_hook_router.py", hook])
    return rc, buf.getvalue(), calls


MALICIOUS = [
    "0.19/../../../../Windows",   # 相對逃逸到磁碟根
    "../../../etc",               # 純 ../ 逃逸
    "0.19/../v0.19",              # 含分隔符（即使最終落樹內，語法白名單先擋）
    "/etc/passwd",                # 絕對路徑
    "0.19; rm -rf /",             # 夾帶 shell metacharacter
    "0.19\\..\\..\\evil",         # Windows 分隔符
]


def test_malicious_version_not_routed():
    for bad in MALICIOUS:
        rc, out, calls = _run_main(bad)
        assert rc == 0, f"惡意版本 {bad!r} 應放行 exit 0，得 {rc}"
        assert not calls, f"惡意版本 {bad!r} 不應觸發 subprocess.run（路徑注入逃逸），實際被執行：{calls}"
        # 非空殼：須印**新**的拒絕訊息（白名單「格式非法」或邊界斷言「解析逃逸」其一），
        # 而非修復前 is_file 落空時才出現的「hook 不存在」訊息——後者 pre-fix 也會出現、無
        # 鑑別力。兩道訊息皆為本修復新增，故任一出現即證縱深防護生效（移除任一層另一層仍擋）。
        assert ("格式非法" in out) or ("解析逃逸" in out), (
            f"惡意版本 {bad!r} 應被白名單或邊界斷言擋下，實得：{out!r}"
        )


def test_valid_version_is_routed():
    # 正例對照：合法 0.19 必須真的路由（證白名單未誤殺合法值、修復非「全擋」）。
    rc, _out, calls = _run_main("0.19")
    assert rc == 0
    assert len(calls) == 1, f"合法版本 0.19 應觸發恰一次 subprocess.run，實際：{calls}"


def test_v_prefix_normalized_and_routed():
    # `v0.19` 經 _normalize_version 去前導 v 後仍合法 → 應路由。
    rc, _out, calls = _run_main("v0.19")
    assert rc == 0
    assert len(calls) == 1
