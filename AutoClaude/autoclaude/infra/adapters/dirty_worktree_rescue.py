# 髒污工作樹的存檔救援序列（PRD §4.5.9 ／ §8-8，v2.1.9 條文）。
#
# 救援序列**只有一個動作**：產生 patch，不動工作樹。原條文前兩步（`commit --no-verify`、
# `git stash`）已被本 repo 憲法直接禁止（鐵律五對 stash 全族機械阻斷；`--no-verify` 是
# 逐字禁止事項），故此處一個字都不寫它們。
#
# 🔴 母體有**兩段**（v2.1.9 修憲補上第二段）：
#     ① tracked 變更：git diff HEAD --binary
#     ② untracked 新檔：ls-files --others --exclude-standard -z ⇒ 逐檔 diff --no-index
#   缺 ② 會產生「四道斷言全綠、而全新工作被靜默丟掉」——`git diff HEAD` 的射程結構上只有
#   index 與 HEAD 認識的路徑，untracked 正是 index 不認識的那一半。而全新的檔恰好是最貴的
#   那一半：tracked 變更在 HEAD 裡至少還留著一個祖先版本，untracked 一丟就是歸零。
#
# 🔴 為什麼不是「把 add 從禁用動詞裡放出來」：`git add` 改動**索引**，`status --porcelain`
#   的第一欄會從 `??` 變成 `A ` ⇒ 直接違反「救援後工作樹狀態逐字不變」。禁令守的不是
#   「別寫 add 這三個字」，是「救援不得改變下一個讀者看到的工作樹狀態」。
#   `git diff --no-index` 把兩個路徑當**檔案系統上的兩份檔**比：一個 git 物件都不寫、
#   索引一個位元組都不動 ⇒ 同時滿足兩個約束。
#
# 🔴 第二道語意閘的形態是**寫死的**：天真寫法 `git apply --check <patch>` 在本節唯一會被
#   跑到的情境（工作樹定義上是髒的）結構上恆紅；吃真索引的 `--cached` 在有 staged 變更時
#   假紅；`--3way` 會把「套不上」fuzz 成綠。唯一形態＝臨時索引 read-tree 到記錄的 base_sha
#   再 `apply --check --cached`，判準 `rc == 0`（**不是** `rc == 1` 才算失敗——截半的 patch
#   實測回 rc=128）。
from __future__ import annotations

import hashlib
import logging
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ...core.ports.worktree_rescue import CLEAN, DIRTY_UNSAVED, SAVED
from ...utils.disk_space import InsufficientSpaceError, require_space

logger = logging.getLogger("autoclaude.infra.adapters.dirty_worktree_rescue")

# 🔴 DEF-200-205：`SAVED`／`DIRTY_UNSAVED` 兩個字面**搬去 `core/ports/worktree_rescue.py`**，
# 上面那行 import 同時是本模組的 re-export（既有 `R.SAVED`／`R.DIRTY_UNSAVED` 讀者拿到的
# 是同一個物件，行為位元級不變）。理由：消費端（`core/services/auto_resume.py`）要拿
# `status` 比對才知道敢不敢睡，而 core/ 依 core-purity contract 讀不到本模組。字面留兩份時
# 漂移方向是「消費端那份沒跟著改」⇒ 比不中 ⇒ 一律當成救援成功（fail-open），正是
# R-4.5.9-4 逐字禁止的那一件事。

# PRD §6 區塊 12：值域 0 ≤ 本值 ≤ 3；0＝不重試（合法）。總寫入嘗試 = 本值 + 1。
# 🔴 上界不是風格問題：磁碟滿是最可能的失敗成因，每一次重試再吃一份空間
# ⇒ 重試本身會讓它更不可能成功。
DIRTY_SAVE_RETRIES_DEFAULT = 1
DIRTY_SAVE_RETRIES_MAX = 3

# git 路徑列舉一律 `-z` ＋ `core.quotepath=false`（根 CLAUDE.md 鐵律三該列）：
# 非 ASCII 檔名在預設組態下會被 git 引號化成 `"\346\226\207"`，逐字拿去當路徑必定找不到檔。
_QUOTEPATH_OFF = ("-c", "core.quotepath=false")


@dataclass(frozen=True)
class RescueResult:
    # `DIRTY_UNSAVED` 的四個可重驗值（PRD R-4.5.9-4 第 1 點）都在這裡：只寫「救援失敗」
    # 等於把下一輪的診斷成本推給人。
    status: str
    patch_path: str = ""
    expected_checksum: str = ""      # 側檔內容（寫入時算的）
    actual_checksum: str = ""        # 重新開檔讀回來算的
    bytes_written: int = 0
    bytes_read_back: int = 0
    base_sha: str = ""
    attempts: int = 0
    reason: str = ""
    expected_paths: tuple[str, ...] = field(default_factory=tuple)


class _GitError(RuntimeError):
    pass


def _git(worktree: str | Path, *args: str, env: dict | None = None) -> tuple[int, bytes]:
    # shell=False ＋ argv 陣列：救援序列不經任何殼，`shell=True` 的原生殼差異
    # （Windows cmd.exe / POSIX /bin/sh）在這條路上沒有任何用處。
    proc = subprocess.run(
        ["git", "-C", str(worktree), *args],
        capture_output=True, env=env, check=False)
    return proc.returncode, proc.stdout


def _git_text(worktree: str | Path, *args: str) -> str:
    rc, out = _git(worktree, *args)
    if rc != 0:
        raise _GitError(f"git {' '.join(args)} rc={rc}")
    return out.decode("utf-8", errors="replace").strip()


def _z_paths(worktree: str | Path, *args: str) -> list[str]:
    rc, out = _git(worktree, *_QUOTEPATH_OFF, *args)
    if rc != 0:
        raise _GitError(f"git {' '.join(args)} rc={rc}")
    return [os.fsdecode(chunk) for chunk in out.split(b"\0") if chunk]


def status_porcelain(worktree: str | Path) -> str:
    # 「救援後逐字不變」那一句要比的就是這個字串（含順序、含空白）。
    rc, out = _git(worktree, *_QUOTEPATH_OFF, "status", "--porcelain")
    if rc != 0:
        raise _GitError(f"git status --porcelain rc={rc}")
    return out.decode("utf-8", errors="replace")


def patch_filename(agent_id: str, base_sha: str, when: datetime | None = None) -> str:
    # `dirty-<agent_id>-<offset-aware ISO8601 basic>-<short_sha>.patch`（PRD R-4.5.9-2）。
    # 🔴 時間戳必須帶 offset：鐵律三已有機械物釘住「naive 本地時間戳被持久化」——
    #    naive 跨 DST 相減完全靜默。`astimezone()` 讓沒帶時區的呼叫者也拿到 aware。
    # 🔴 不覆寫（帶時間戳）也是繞開一個平台事實：`os.replace` 在 Windows 上覆寫「被別人
    #    開著」的目的檔會 WinError 5。
    ts = (when or datetime.now().astimezone()).strftime("%Y%m%dT%H%M%S%z")
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in agent_id) or "agent"
    return f"dirty-{safe}-{ts}-{base_sha}.patch"


def build_patch_bytes(worktree: str | Path) -> tuple[bytes, list[str]]:
    """兩段輸出依序落成**同一份** patch（順序是規範性的：① 在前，② 在後）。

    回 (patch_bytes, expected_paths)。expected_paths＝tracked ∪ untracked，來自
    **列舉**而不是 patch 自己——後者是拿答案去對答案。
    """
    tracked = _z_paths(worktree, "diff", "HEAD", "--name-only", "-z")
    untracked = _z_paths(worktree, "ls-files", "--others", "--exclude-standard", "-z")
    rc, part1 = _git(worktree, "diff", "HEAD", "--binary", "--no-color")
    if rc != 0:
        raise _GitError(f"git diff HEAD rc={rc}")
    chunks = [part1]
    for path in untracked:
        # `--no-index` 對「兩份檔不同」回 rc=1，那是**正常**輸出不是錯誤；只有 >1 才是壞。
        # `/dev/null` 是 git 自己的空檔慣例（Git for Windows 同樣認得它），不是 POSIX 路徑。
        rc, part = _git(worktree, "diff", "--no-index", "--binary", "--no-color",
                        "--", "/dev/null", path)
        if rc > 1:
            raise _GitError(f"git diff --no-index {path} rc={rc}")
        chunks.append(part)
    return b"".join(chunks), [*tracked, *untracked]


def unique_path(target: Path) -> Path:
    # PRD R-4.5.9-2「不覆寫」：ISO8601 basic 只到**秒**，而救援可能在同一秒內連續發生
    # （實測：同一測試內連跑兩次 ⇒ 檔名逐字相同、第二份把第一份靜默蓋掉，而那正是這一條
    # 要防的事）。碰撞時往後找第一個空位，不動時間戳（時間戳是事實快照，不該為了避碰改）。
    if not target.exists():
        return target
    for n in range(2, 1000):
        candidate = target.with_name(f"{target.stem}-{n}{target.suffix}")
        if not candidate.exists():
            return candidate
    raise OSError(f"同一秒內超過 999 次救援，無法產生不覆寫的檔名：{target}")


def _write_atomically(target: Path, blob: bytes) -> int:
    tmp = target.with_suffix(target.suffix + ".tmp")
    try:
        with tmp.open("wb") as f:
            f.write(blob)
            f.flush()
            os.fsync(f.fileno())          # PRD 步驟 1：flush 之後、replace 之前
        try:
            os.replace(tmp, target)
        except PermissionError as exc:
            # 🔴 鐵律三「Windows 檔案鎖」那一列：`os.replace` 覆寫**被別人開著**的目的檔
            # 在 Windows 上是 WinError 5，而 POSIX 上恆成功 ⇒ 這條路徑在 mac/Linux 開發機
            # 上結構上重現不了，理由只能寫在這裡。處置＝變成一次可診斷的失敗（呼叫端的
            # 重試迴圈接住 OSError 並依 DIRTY_SAVE_RETRIES 重試），**不得吞掉**：吞掉會讓
            # 「patch 沒寫成」與「patch 寫好了」外觀相同，那正是本節整段要治的靜默。
            raise OSError(
                f"換名失敗（Windows 上目的檔被別的行程開著即 WinError 5）：{target}"
            ) from exc
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return len(blob)


def _sha256_of_file(p: Path) -> tuple[str, int]:
    # 🔴 重新開檔讀回：**不得**複用寫入時的 buffer／記憶體內容——那樣驗的是記憶體，
    #    而磁碟才是這一條要治的東西（PRD D3 的紅綠自證就是拿這一格當對照）。
    h, n = hashlib.sha256(), 0
    with p.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
            n += len(block)
    return h.hexdigest(), n


def patch_covers(patch_text: str, paths: list[str]) -> list[str]:
    """回「沒被涵蓋到的路徑」（空＝全涵蓋）。

    🔴 比對是 `diff --git a/<X> b/<Y>` 標頭的 **X 或 Y 任一側**，不是 `a/<p> b/<p>`：
    git 對**改名**產生的標頭兩側路徑**不同**（實測 `diff --git a/ren.txt b/renamed.txt`），
    而 `--name-only` 只報新名 ⇒ 寫成兩側同名的實作會對改名判失敗，那是一次**假紅**，
    而假紅會讓整道判準被關掉。
    """
    sides: set[str] = set()
    for line in patch_text.splitlines():
        if not line.startswith("diff --git "):
            continue
        for token in line[len("diff --git "):].split(" "):
            if len(token) > 2 and token[1] == "/":
                sides.add(token[2:])
    return [p for p in paths if p not in sides]


def semantic_gate(worktree: str | Path, patch: Path, base_sha: str,
                  index_file: Path) -> tuple[bool, str]:
    """第二道閘：臨時索引 read-tree 到 base_sha ＋ `apply --check --cached`，判準 rc == 0。"""
    env = {**os.environ, "GIT_INDEX_FILE": str(index_file)}
    try:
        rc, _ = _git(worktree, "read-tree", base_sha, env=env)
        if rc != 0:
            return False, f"read-tree {base_sha} rc={rc}"
        rc, _ = _git(worktree, "apply", "--check", "--cached", str(patch), env=env)
        # 判準是 `rc == 0`。寫成 `rc == 1` 才算失敗的實作會把截半 patch 的 rc=128 當成通過。
        return rc == 0, f"apply --check --cached rc={rc}"
    finally:
        index_file.unlink(missing_ok=True)


def _selfrecursion_hazard(worktree: Path, checkpoint_dir: Path) -> str:
    # patch 檔落在 repo 內而該目錄**不在** .gitignore 時，② 會把 patch 自己列舉進來
    # （把自己抄進自己），且 status --porcelain 會多一行 ⇒ 違反「逐字不變」。
    # §6.1 不變式 9 已要求 `.autoclaude/` 在 .gitignore；這裡是同一條的就地前置斷言——
    # 那條不變式若失效，本節的失效形態是**靜默的**（patch 照樣非空、斷言照樣全綠）。
    try:
        rel = checkpoint_dir.resolve().relative_to(worktree.resolve())
    except ValueError:
        return ""                                   # 目錄在工作樹外 ⇒ 結構上無遞迴
    if not rel.parts:
        return ""
    # 🔴 問的必須是**完整的相對路徑**、不是頂層那一段：實測 `.gitignore` 寫
    # `.autoclaude/`（帶斜線＝只配目錄）時，`check-ignore .autoclaude` 在該目錄還不存在
    # 時回 rc=1（git 把不存在的 pathname 當檔案），而 `check-ignore .autoclaude/checkpoints`
    # 回 rc=0。拿前者當判準會對一棵**已經正確 ignore** 的 repo 判危害＝假紅。
    target = rel.as_posix()
    rc, _ = _git(worktree, "check-ignore", "-q", target)
    if rc == 0:
        return ""
    return (f"checkpoint 目錄 `{target}` 在工作樹內但**不在** .gitignore 的排除面內"
            f"（git check-ignore rc={rc}）⇒ patch 會把自己列舉進自己，"
            "且 status --porcelain 會多一行。請先把它加入 .gitignore（§6.1 不變式 9）")


def rescue_dirty_worktree(
    worktree: str | Path,
    checkpoint_dir: str | Path,
    *,
    agent_id: str = "agent",
    retries: int | None = None,
    notifier: Callable[[str], None] | None = None,
    space_check: Callable[[int], None] | None = None,
) -> RescueResult:
    """單步救援 ＋ 寫後讀回驗證。回 RescueResult（status ∈ {SAVED, DIRTY_UNSAVED}）。

    絕不 fail-open：驗證失敗時**不**回 SAVED，呼叫端因此不得轉入 WAITING_RESET／
    LONG_HIBERNATE（那兩個狀態的語意是「工作已保全」，而此刻工作沒有保全）。
    """
    wt, ck_dir = Path(worktree), Path(checkpoint_dir)
    n_retries = DIRTY_SAVE_RETRIES_DEFAULT if retries is None else retries
    n_retries = max(0, min(DIRTY_SAVE_RETRIES_MAX, int(n_retries)))
    ck_dir.mkdir(parents=True, exist_ok=True)
    before = status_porcelain(wt)
    # 步驟 0：base_sha 在跑 ① **之前**取、之後不再重取（PRD R-4.5.9-2 寫死）。
    # 它決定第二道閘的成敗：① 產出的 hunk 是相對該 HEAD 的 diff，基準寫錯，閘門測的
    # 就是另一個問題。
    base_sha = _git_text(wt, "rev-parse", "--short", "HEAD")
    hazard = _selfrecursion_hazard(wt, ck_dir)
    if hazard:
        return _unsaved(RescueResult(status=DIRTY_UNSAVED, base_sha=base_sha,
                                     reason=hazard), notifier)
    blob, expected = build_patch_bytes(wt)
    checker = space_check or (lambda n: require_space(ck_dir, n))
    attempts = 0
    # 🔴 `last` 必須是**整個 RescueResult**而不是一個理由字串：只留理由的版本會在迴圈
    # 結束時把四個可重驗值（patch 路徑／期望 checksum／實測 checksum／位元組數）一起
    # 丟掉，而 PRD R-4.5.9-4 第 1 點逐字要求它們進 state.json——「只寫救援失敗等於把
    # 下一輪的診斷成本推給人」。本輪由 D3／D5b 兩格當場抓到。
    last = RescueResult(status=DIRTY_UNSAVED, base_sha=base_sha,
                        expected_paths=tuple(expected), reason="救援未執行")
    while attempts <= n_retries:
        attempts += 1
        try:
            # 🔴 順序：空間檢查在寫 patch **之前**（PRD R-6.2-3 ①／G7）。順序反了，
            # 這道檢查在它唯一要治的情境（磁碟滿）下根本不會被跑到。
            checker(len(blob) * 2)          # patch ＋ 側檔 ＋ tmp 檔的同時佔用
            res = _attempt(wt, ck_dir, agent_id, base_sha, blob, expected, attempts)
        except (InsufficientSpaceError, OSError, _GitError) as exc:
            last = RescueResult(status=DIRTY_UNSAVED, base_sha=base_sha,
                                attempts=attempts, expected_paths=tuple(expected),
                                reason=f"{type(exc).__name__}: {exc}")
            continue
        if res.status == SAVED:
            after = status_porcelain(wt)
            if after != before:
                return _unsaved(RescueResult(
                    status=DIRTY_UNSAVED, base_sha=base_sha, attempts=attempts,
                    patch_path=res.patch_path, expected_paths=tuple(expected),
                    reason=("救援改動了工作樹：status --porcelain 前後不相等\n"
                            f"before={before!r}\nafter={after!r}")), notifier)
            return res
        last = res
    return _unsaved(last, notifier)


def _attempt(wt: Path, ck_dir: Path, agent_id: str, base_sha: str,
             blob: bytes, expected: list[str], attempts: int) -> RescueResult:
    patch = unique_path(ck_dir / patch_filename(agent_id, base_sha))
    n_written = _write_atomically(patch, blob)
    digest = hashlib.sha256(blob).hexdigest()
    side = patch.with_suffix(patch.suffix + ".sha256")
    _write_atomically(side, digest.encode("ascii"))
    actual, n_read = _sha256_of_file(patch)
    expect_side = side.read_text(encoding="ascii").strip()
    base = RescueResult(status=DIRTY_UNSAVED, patch_path=str(patch),
                        expected_checksum=expect_side, actual_checksum=actual,
                        bytes_written=n_written, bytes_read_back=n_read,
                        base_sha=base_sha, attempts=attempts,
                        expected_paths=tuple(expected))
    if actual != expect_side:                                   # (a)
        return _with(base, "讀回的 SHA-256 與側檔不符")
    if n_read != n_written:                                     # (b)
        return _with(base, f"讀回位元組數 {n_read} != 寫入 {n_written}")
    if n_written <= 0:                                          # (c)
        return _with(base, "patch 是 0 bytes（空檔 vs 空檔的 SHA-256 會一致）")
    missing = patch_covers(                                     # (d)
        patch.read_text(encoding="utf-8", errors="replace"), expected)
    if missing:
        return _with(base, f"覆蓋率不足：expected_paths 有 {missing} 不在 patch 內")
    ok, detail = semantic_gate(wt, patch, base_sha,             # 第二道語意閘
                               ck_dir / f".{patch.name}.index")
    if not ok:
        return _with(base, f"第二道語意閘未過（{detail}）")
    logger.info("髒污工作樹已存檔：%s（%d bytes，base=%s，涵蓋 %d 個路徑）",
                patch, n_written, base_sha, len(expected))
    return _with(base, "", status=SAVED)


def _with(base: RescueResult, reason: str, status: str = DIRTY_UNSAVED) -> RescueResult:
    return RescueResult(
        status=status, patch_path=base.patch_path,
        expected_checksum=base.expected_checksum, actual_checksum=base.actual_checksum,
        bytes_written=base.bytes_written, bytes_read_back=base.bytes_read_back,
        base_sha=base.base_sha, attempts=base.attempts, reason=reason,
        expected_paths=base.expected_paths)


class DirtyWorktreeRescueAdapter:
    """`IWorktreeRescue` 實作（DEF-200-205 的接電面）。

    把「patch 落哪／retries 幾次／agent_id 是誰／通知走哪個通道」四件**組裝期知識**綁在
    建構時，讓消費端只需要呼叫零參數的 `rescue()`——否則 `core/` 就得知道 patch 目錄長
    什麼樣，而那正是本 Port 要隔開的東西。
    """

    def __init__(
        self,
        worktree: str | Path,
        checkpoint_dir: str | Path,
        *,
        agent_id: str = "agent",
        retries: int | None = None,
        notifier: Callable[[str], None] | None = None,
    ) -> None:
        self._worktree = Path(worktree)
        self._checkpoint_dir = Path(checkpoint_dir)
        self._agent_id = agent_id
        self._retries = retries
        self._notifier = notifier

    def rescue(self) -> RescueResult:
        """兩道前置守衛 ＋ 委派 `rescue_dirty_worktree`。

        🔴 **守衛一（工作樹根）**：救援序列的路徑語意要求 `worktree` 就是 repo 頂層。
        `git -C <子目錄> diff HEAD --name-only` 回的是**根相對**路徑，而
        `ls-files --others` 回的是**cwd 相對**路徑 ⇒ 從子目錄跑會讓 ② 那半的
        `diff --no-index -- /dev/null <path>` 找不到檔（rc>1 → _GitError）。所以這裡先
        `rev-parse --show-toplevel` 把它正規化，而不是相信呼叫端傳對了。

        🔴 **守衛二（乾淨就不要進去）**：R-4.5.9 的進入條件是「worktree 有未提交變更」。
        乾淨工作樹送進救援序列 ⇒ patch 是 0 bytes ⇒ (c) 斷言判 DIRTY_UNSAVED ⇒ 每一次
        乾淨的 halt 都被讀成「工作沒保全、禁止自動喚醒」＝假紅。回 `CLEAN` 而不是 `SAVED`：
        「沒有東西要救」與「救到了」是兩件事，混在一起下一個讀者就分不出來。
        """
        try:
            root = _git_text(self._worktree, "rev-parse", "--show-toplevel")
            dirty = status_porcelain(root)
        except (_GitError, OSError) as exc:
            # 不在 git 工作樹內／git 不可用 ⇒ 沒有「未提交變更」這個概念，不是救援失敗。
            return RescueResult(status=CLEAN, reason=f"不在 git 工作樹內或 git 不可用：{exc}")
        if not dirty:
            return RescueResult(status=CLEAN,
                                reason="工作樹乾淨（status --porcelain 為空），無需救援")
        return rescue_dirty_worktree(
            root, self._checkpoint_dir, agent_id=self._agent_id,
            retries=self._retries, notifier=self._notifier)


def _unsaved(res: RescueResult, notifier: Callable[[str], None] | None) -> RescueResult:
    # PRD R-4.5.9-4：state.json 帶齊四個可重驗值（＝RescueResult 本身）＋ 桌面通知
    # **恰好一次** ＋ 禁止自動喚醒（呼叫端看到 DIRTY_UNSAVED 就不得排喚醒）。
    # 🔴 原條文只要求「在 state.json 中明確警示」——state.json 沒有讀者會主動去看它，
    #    那是 fail-quiet，而本節整段修憲的出發點正是這種靜默。
    msg = (f"DIRTY_UNSAVED：髒污工作樹存檔失敗（base={res.base_sha}，"
           f"attempts={res.attempts}）：{res.reason}")
    logger.error(msg)
    if notifier is not None:
        notifier(msg)
    return res
