"""研究 stage 測試的共用助手（PKG-BR-C）：讓「會真的啟動 stage」的測試維持 hermetic。

stage 啟動端點自 PKG-BR-C 起不再是 501 骨架：請求被接受就會建 stage run 列、編譯 playbook、
起引擎行程。測試因此多了三件事要負責——

- 框架檔：編譯層從 SDD 樹讀 agent YAML 與 PRD 模板，讀不到就 503 `compile_failed`（產品的
  fail-loud 行為，不是測試要壓掉的錯）⇒ 假 SDD 樹要用 `install_framework` 補上夾具框架。
- 引擎的 claude：只想驗「啟動請求被接受」的測試把 `research_claude_command` 設成 `ABSENT_CLAUDE`
  （不存在的指令名）——引擎一起行程就拿不到 claude、run 立刻失敗，**絕不呼叫真正的模型**（本機
  有裝 claude 時預設的 `claude` 會真的跑）。要驗完整流程的測試改用
  `fixtures/research/fake_claude.py`。
- 安靜的資料庫：stage 鏈在背景執行緒寫資料庫；測試要在拍快照或手改列之前 `settle` 等它結束。
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

FRAMEWORK = Path(__file__).resolve().parent / "fixtures" / "research" / "framework"
#: 不存在的指令名：引擎拿不到 claude ⇒ stage run 立刻失敗（hermetic：不呼叫模型、不連網）。
ABSENT_CLAUDE = "aisdlc-absent-claude-for-tests"


def install_framework(tree: Path) -> Path:
    """把夾具框架的 agent YAML 與 PRD 模板複製進（假）SDD 樹；回傳同一個樹以便串接。"""
    for name in ("agent", "docs_template"):
        shutil.copytree(FRAMEWORK / name, tree / name, dirs_exist_ok=True)
    return tree


def settle(live: Any, research_id: str, timeout: float = 60.0) -> None:
    """等這個專案的 stage 鏈結束（`live`＝`make_bridge` 回傳的活 Bridge）。"""
    ctx = getattr(live.app.state, "research", None)
    orchestrator = None if ctx is None else ctx.orchestrator
    assert orchestrator is not None, "這個 Bridge 沒有 orchestrator（未設資料庫？）"
    assert orchestrator.join(research_id, timeout), f"stage 鏈 {timeout:g} 秒內沒有結束"
