"""重產 SelfImproving 黃金檔（TCS-SelfImprovingMirror-P1b §5.1；測試支援腳本，不是測試）。

    python tests/si_golden_regen.py          # 在 AgentConsole/engine-bridge 下執行（用根 .venv）

做的事：以 `make_si_repo` 建狀態 A 與 B 的 tmp 倉，取真 CLI 的輸出，寫四個黃金檔
（`tests/fixtures/si_golden/{A,B}.{snake,camel}.json`），再把同樣的位元組複製到兩份副本：
backend（`backend/src/test/resources/si/` 四個）與 frontend（`frontend/tests/fixtures/si/` 兩個
camelCase）。寫入前逐檔列印差異；AT 會鎖住三份副本逐位元組相同與「黃金檔是真輸出的子集」，所以真
CLI 的輸出格式變動時，先看這裡印出的差異、確認是預期的變動，再把重產結果一起 commit。

snake 版＝真 CLI 輸出（各回應頂層的 `generated_at` 與 `head_sha` 置固定占位；其餘鍵值保留），
camelCase 版＝R9 轉換（`si_repo_support.camel_keys`）。黃金檔不得含任何由 commit sha 衍生的值：
建倉所得的 HEAD 一律不進黃金檔（事件與運轉內的 `head_sha` 皆為夾具寫死的固定字面）。
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ""):                 # 以 `python tests/si_golden_regen.py` 直接執行
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import si_repo_support as sup  # noqa: E402

BACKEND_COPY = sup.MONOREPO / "AgentConsole" / "backend" / "src" / "test" / "resources" / "si"
FRONTEND_COPY = sup.MONOREPO / "AgentConsole" / "frontend" / "tests" / "fixtures" / "si"
#: B 版只涵蓋會變的 kind 加不變的 proposals（不含單筆）。`issues`（議題中心）A、B 兩態都有
#: （TCS-IssueCenter-20261027 D-C7）：夾具倉不增帳本檔，故其 `ne` 含缺陷主檔與姊妹軌讀不到的聲明。
STATE_KEYS = {"A": ("observations", "events", "proposals", "proposal_one", "runs", "status",
                    "issues"),
              "B": ("observations", "events", "proposals", "runs", "status", "issues")}


def render_all(work: Path) -> dict[str, bytes]:
    """檔名 → 位元組：`A.snake.json`、`A.camel.json`、`B.snake.json`、`B.camel.json`。"""
    home = work / "home"
    home.mkdir()
    old = {k: os.environ.get(k) for k in ("HOME", "USERPROFILE")}
    os.environ["HOME"] = os.environ["USERPROFILE"] = str(home)    # 真家目錄不得被碰
    try:
        repo_a = sup.make_si_repo(work, "A")
        golden_a = sup.to_golden(sup.collect_state_outputs(repo_a, with_one=True))
        repo_b = sup.advance_to_b(repo_a)
        golden_b = sup.to_golden(sup.collect_state_outputs(repo_b, with_one=False))
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    out: dict[str, bytes] = {}
    for state, golden in (("A", golden_a), ("B", golden_b)):
        snake = {key: golden[key] for key in STATE_KEYS[state]}
        out[f"{state}.snake.json"] = sup.render_json(snake)
        out[f"{state}.camel.json"] = sup.render_json(sup.camel_keys(snake))
    return out


def _write(path: Path, data: bytes) -> str:
    old = path.read_bytes() if path.is_file() else None
    if old == data:
        return "same"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return "new" if old is None else f"changed ({len(old)} -> {len(data)} bytes)"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="si-golden-") as raw:
        rendered = render_all(Path(raw))
    for name, data in sorted(rendered.items()):
        targets = [sup.GOLDEN_DIR / name, BACKEND_COPY / name]
        if name.endswith(".camel.json"):
            targets.append(FRONTEND_COPY / name)
        for target in targets:
            print(f"{_write(target, data):>28}  {target.relative_to(sup.MONOREPO).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
