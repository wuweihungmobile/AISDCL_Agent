"""act 本機自建 runner 映像的機械鎖 —— `.actrc` ↔ `run_act_core` ↔ `tools/act/Dockerfile`。

WHY 這三處必須被綁在一起（R77 實測到的破口與它的修法）：
  `act -n`（dry-run）對 root-infra-ci.yml 回 rc=0，但**真跑**到第 3 個 step
  （`pwsh 語法解析 + UTF-8 BOM 守門`）就 `exitcode 127` —— `.actrc` 釘的
  `catthehacker/ubuntu:act-latest` 沒有 pwsh，而 GitHub 的 ubuntu-latest runner 自帶。
  修法是自建一顆薄映像（base ＋ pwsh ＋ gh）並把 `.actrc` 指過去。於是「映像 tag」這個
  字面值同時住在三個地方：`.actrc` 的 `-P` 行、`run_act_core.RUNNER_IMAGE`（`--build-image`
  build 出來的 tag、`ensure_images()` 檢查存在性的對象）、以及 Dockerfile 檔頭的說明。
  三處只要有一處漂掉，失敗方向都是**靜默的**：

    · `.actrc` 指到一個不存在的 tag ⇒ act 帶 `--pull=false` 會去 pull 一個 registry 上
      不存在的映像然後失敗 —— 這一種還算大聲。
    · `.actrc` 指回 base、而 `run_act_core` 仍 build/檢查自建 tag ⇒ `ensure_images()`
      一路綠燈（那顆自建映像確實在），act 卻起 base 容器，pwsh 那步**又**回 127。
      畫面上是「準備階段全綠、跑到一半才炸」，而準備階段的綠與這次失敗毫無關係。
      這正是本 repo 反覆在治的「鎖存在但沒有鑑別力」。

判準刻意只鎖「三處對得上」與「Dockerfile 真的在補那兩支工具」，**不**去 docker 跑任何
東西：本檔隨 `tools/run_root_unittests.py` 在每次根層 push 與 root-infra-ci 內執行，那兩處
都不保證有 docker，也不該為了一個字面一致性檢查去付容器的錢。

誠實劃界（本鎖抓不到的）：
  · 抓不到「映像裡的 pwsh 版本與雲端 runner 分歧」——那是量測值，會隨 GitHub 更新
    runner 映像而漂移，釘死它等於製造必然的假紅。取值與重查方式寫在 Dockerfile 檔頭。
  · 抓不到「Dockerfile 寫了但沒 build」——`.actrc` 指向的映像存在與否只有 docker 知道，
    由 `run_act_core.ensure_images()` 在真要跑的時候現查並自動 build。
"""
from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path
from types import ModuleType

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ACTRC = _REPO_ROOT / ".actrc"
_CORE = _REPO_ROOT / "AutoClaude" / "tools" / "run_act_core.py"

#: `.actrc` 的 runner 映射行：`-P <label>=<image>`（與 run_act_core._ACTRC_RUNNER_RE 同源，
#: 但這裡連 image 一起抓）。
_ACTRC_MAP_RE = re.compile(r"^-P\s+([^=\s]+)=(\S+)\s*$", re.MULTILINE)

#: 自建映像必須補上的工具＝「GitHub ubuntu-latest 自帶、catthehacker 中型映像沒有」的那些。
#: 這兩支是本次修法的**全部理由**；Dockerfile 若不再提到它們，本鎖失去對象即紅。
_MUST_PROVIDE = ("pwsh", "gh")


def _load_core() -> ModuleType:
    """以檔案路徑載入 `run_act_core`（不寫 sys.modules；同 test_smoke_ci_sync 既有手法）。

    刻意載入模組本體讀常數，而不是 regex 掃原始碼：後者只鎖得住長相，「常數改了但
    `.actrc` 沒跟上」照樣可能因為 regex 抓錯行而綠——而那正是本鎖要抓的失敗形態。
    """
    spec = importlib.util.spec_from_file_location("_run_act_core_for_image_lock", _CORE)
    if spec is None or spec.loader is None:
        raise AssertionError(f"無法載入 {_CORE}——act runner 映像鎖失效")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestActLocalRunnerImage(unittest.TestCase):
    def setUp(self) -> None:
        self.core = _load_core()
        self.actrc = _ACTRC.read_text(encoding="utf-8")
        self.mappings = dict(_ACTRC_MAP_RE.findall(self.actrc))

    def test_actrc_has_runner_mappings_at_all(self) -> None:
        """0 命中假綠防線：抽取式壞掉時下面每一條斷言都會恆真（同 _MIN_EXTRACT_COUNTS 慣例）。"""
        self.assertGreaterEqual(
            len(self.mappings), 3,
            f"`.actrc` 只抽到 {len(self.mappings)} 條 `-P` 映射——抽取式疑似漂移，"
            f"而漂移方向正好是「下面每一條都通過」",
        )

    def test_ubuntu_latest_points_at_the_locally_built_image(self) -> None:
        """全庫 ubuntu job 一律 `runs-on: ubuntu-latest` ⇒ 這一行決定 act 到底起哪顆容器。"""
        self.assertEqual(
            self.mappings.get("ubuntu-latest"), self.core.RUNNER_IMAGE,
            f"`.actrc` 的 `-P ubuntu-latest=` 指向 "
            f"{self.mappings.get('ubuntu-latest')!r}，而 run_act_core.RUNNER_IMAGE 是 "
            f"{self.core.RUNNER_IMAGE!r}——兩者不一致時 `ensure_images()` 會為 A 映像"
            f"開綠燈、act 卻起 B 容器，失敗會延到 job 跑到一半才出現（pwsh 那步 127），"
            f"而準備階段的綠與那次失敗毫無關係",
        )

    def test_locally_built_image_is_not_the_upstream_base(self) -> None:
        """自建 tag 不得等於 base：相等即代表薄映像那一層被整個繞過（回到 R77 的破口）。"""
        self.assertNotEqual(
            self.core.RUNNER_IMAGE, self.core.ACT_BASE_IMAGE,
            "RUNNER_IMAGE 等於 ACT_BASE_IMAGE —— 自建映像層被繞過，pwsh 缺件會原樣回來。"
            "base 沒有 pwsh 是實測事實（`docker run --rm <base> command -v pwsh` not found），"
            "不是猜測",
        )

    def test_dockerfile_exists_and_is_built_from_the_declared_base(self) -> None:
        dockerfile = _REPO_ROOT / self.core.ACT_DOCKERFILE
        self.assertTrue(
            dockerfile.is_file(),
            f"{self.core.ACT_DOCKERFILE} 不存在——`--build-image` 的唯一來源缺席，"
            f"而 `.actrc` 已經指向那顆只有它能產生的映像 ⇒ 任何人 fresh clone 後都跑不動",
        )
        text = dockerfile.read_text(encoding="utf-8")
        self.assertIn(
            f"FROM {self.core.ACT_BASE_IMAGE}", text,
            f"{self.core.ACT_DOCKERFILE} 的 FROM 不是 ACT_BASE_IMAGE"
            f"（{self.core.ACT_BASE_IMAGE}）——base 換掉時本鎖要求顯式同步這個常數，"
            f"否則 preflight 對「映像缺什麼」的判斷會建立在錯的前提上",
        )

    def test_dockerfile_actually_provides_the_tools_that_justify_it(self) -> None:
        """實質判準：Dockerfile 必須真的在裝 pwsh 與 gh，不只是「檔案在」。

        WHY 要這一條（本 repo 的 R75 教訓）：只斷言「具名檔案存在」的鎖，遇到「檔案在、
        但守的是別的東西」會照樣放行——比指向一個不存在的檔更難看見。
        """
        text = (_REPO_ROOT / self.core.ACT_DOCKERFILE).read_text(encoding="utf-8")
        for tool in _MUST_PROVIDE:
            self.assertRegex(
                text, rf"/usr/bin/{tool}\b",
                f"{self.core.ACT_DOCKERFILE} 內找不到把 {tool} 放進 /usr/bin 的痕跡——"
                f"這顆映像存在的**全部理由**就是補上 base 缺的 {'／'.join(_MUST_PROVIDE)}；"
                f"補不到就別讓 `.actrc` 指過來",
            )

    def test_tools_already_provided_are_not_still_listed_as_missing(self) -> None:
        """`RUNNER_IMAGE_MISSING_TOOLS` 不得再列本映像已經裝好的工具。

        WHY：那份清單驅動 preflight 的警告。把已經有的東西列成缺件，會讓每一次執行都印
        一條假警告——而假警告的長期代價是**真警告也一起被忽略**（本 repo 對 advisory 被
        無視已有實證）。方向與 R74「把會跑的東西寫成不會跑」的假事實同型。
        """
        for tool in _MUST_PROVIDE:
            self.assertNotIn(
                tool, self.core.RUNNER_IMAGE_MISSING_TOOLS,
                f"{tool!r} 仍列在 RUNNER_IMAGE_MISSING_TOOLS，但自建映像已經裝了它"
                f"（實測 `docker run --rm {self.core.RUNNER_IMAGE} command -v {tool}` 有值）"
                f"——請自該清單移除，否則 preflight 會對每一支提到它的 job 印假警告",
            )

    def test_no_local_channel_alternatives_cover_every_unmapped_runner(self) -> None:
        """每個「`.actrc` 沒有映射」的 runs-on 都必須查得到替代驗證出口——不得留白。

        留白就是 R77 那張盤點表原本的問題：讀者只知道「不行」，不知道「那要改用什麼驗」。
        """
        unmapped = sorted({
            label for _wf, _job, label, has_runner, _svc in self.core.job_inventory()
            if not has_runner
        })
        self.assertTrue(
            unmapped,
            "全庫沒有任何一個 runner 落在 .actrc 映射之外——若屬實可刪本條；更可能是 "
            "job_inventory() 的 runs-on 抽取式已漂移，而那個方向看起來正好像「都沒問題」",
        )
        missing = [x for x in unmapped if x not in self.core.NO_LOCAL_CHANNEL_ALTERNATIVES]
        self.assertEqual(
            missing, [],
            f"runs-on {missing} 沒有登記替代驗證出口——請補 "
            f"run_act_core.NO_LOCAL_CHANNEL_ALTERNATIVES（鍵是 runner 標籤，不是 job，"
            f"故新增同平台 job 不需要再補一次）",
        )


class TestActRunLedgerIsMeasuredNotDeclared(unittest.TestCase):
    """實跑帳本的分類判準：✅ 只能來自實跑，且 workflow 一改就降級。"""

    def setUp(self) -> None:
        self.core = _load_core()

    def _classify(self, ledger: dict) -> str:
        wf, job = "root-infra-ci.yml", "root-infra"
        cat, _notes = self.core.classify_job(
            wf, job, "ubuntu-latest", True, False, {"push"}, "push", ledger
        )
        return cat

    def test_no_ledger_entry_is_never_reported_as_verified(self) -> None:
        self.assertEqual(
            self._classify({}), self.core.CAT_RUNNABLE,
            "帳本沒有紀錄卻被分到 ✅ —— 那就是「宣稱先於查證」本身",
        )

    def test_stale_evidence_is_downgraded_when_the_workflow_changed(self) -> None:
        """workflow 改過之後，舊的 rc=0 不再代表現況（過期的綠比沒有綠更危險）。"""
        ledger = {"root-infra-ci.yml::root-infra": {
            "rc": 0, "wf_sha": "deadbeefcafe", "at": "2000-01-01T00:00:00Z", "image": "x",
        }}
        self.assertEqual(self._classify(ledger), self.core.CAT_STALE)

    def test_fresh_passing_evidence_is_verified(self) -> None:
        wf_path = _REPO_ROOT / self.core.WORKFLOW_DIR / "root-infra-ci.yml"
        ledger = {"root-infra-ci.yml::root-infra": {
            "rc": 0, "wf_sha": self.core.workflow_fingerprint(wf_path),
            "at": "2026-08-07T00:00:00Z", "image": self.core.RUNNER_IMAGE,
        }}
        self.assertEqual(self._classify(ledger), self.core.CAT_VERIFIED)

    def test_failing_evidence_is_not_silently_dropped(self) -> None:
        """實跑失敗必須有自己的一格——掉回「未實跑」等於把紅洗成中性。"""
        wf_path = _REPO_ROOT / self.core.WORKFLOW_DIR / "root-infra-ci.yml"
        ledger = {"root-infra-ci.yml::root-infra": {
            "rc": 1, "wf_sha": self.core.workflow_fingerprint(wf_path),
            "at": "2026-08-07T00:00:00Z", "image": self.core.RUNNER_IMAGE,
        }}
        self.assertEqual(self._classify(ledger), self.core.CAT_FAILED)

    def test_every_obstacle_is_reported_not_just_the_first(self) -> None:
        """同時中兩個障礙時，說明必須兩個都在（Scan-H⑦ 早退遮蔽的反向鎖）。

        活體實例：`autoclaude-pg-e2e-on-label.yml` 既無 push 觸發、又帶 `services:`。
        """
        _cat, notes = self.core.classify_job(
            "autoclaude-pg-e2e-on-label.yml", "pg-e2e", "ubuntu-latest",
            True, True, {"pull_request"}, "push", {},
        )
        blob = " ".join(notes)
        self.assertIn("services", blob, "帶 services: 這個障礙被吞掉了")
        self.assertIn("--event", blob, "事件對不上這個障礙被吞掉了")


class TestRunActShellFlagParity(unittest.TestCase):
    """兩支 `run_act` 薄殼必須到得了核心宣告的**每一個**長旗標（SD-06／LOCKBLIND）。

    🔴 這條鎖存在的理由是一個真實的、被兩道專職對等檢查器同時放行的落差：R77 給
    `run_act.sh` 接上了 `--workflow`／`--event`，`run_act.ps1` 卻沒有——Windows 是本 repo
    的主要開發平台，而它的薄殼因此指不到 11 支 workflow 裡的 10 支。當時
    `check_script_parity.py` 與 `check_wrapper_thinness.py` **雙雙 rc=0**：
      · `check_wrapper_thinness` 是**逐檔** hash 釘選 —— 它問「這份檔案有沒有變」，
        兩側各自更新各自的 pin 就都是綠的，它從不把兩側拿來互相比較；
      · `check_script_parity` 對 hash 釘選類的對子只做「有沒有納管」與鍵集合交叉鎖，
        _MARKER_PAIRS（唯一會比對兩側內容的機制）對這一對是空的。
    ⇒ 專門守對等的鎖看不見對等落差。只補旗標而不補判準，同型缺陷會再來一次。

    判準刻意**由核心的 argparse 現查**（`parse_args([])` 的 Namespace 欄位），不是在這裡
    抄一份旗標清單：抄的那一份會變成第三個會腐化的家，而它腐化的方向正好是「看起來
    都對得上」。核心新增旗標時本鎖自動要求兩側跟上，不需要有人記得回來改這裡。

    覆蓋邊界（誠實劃界）：
      · 只驗「旗標到得了」，不驗語意等價（`-Job x` 與 `--job x` 傳的是不是同一個東西）。
      · 只涵蓋 `run_act` 這一對。其餘 `_THINNESS_ENROLLED` 對子的同型落差仍無判準——
        泛化到全部對子需要處理「核心不是 argparse」（如 install-hooks／run_tlc）的情形，
        不在本次射程內。這一格是已知缺口，不是已解決。
    """

    #: 0 命中假綠防線：核心旗標抽不到時，下面的 for 迴圈會恆真。
    _MIN_CORE_FLAGS = 6

    def setUp(self) -> None:
        self.core = _load_core()
        self.sh = (_REPO_ROOT / "AutoClaude" / "tools" / "run_act.sh").read_text(
            encoding="utf-8-sig"
        )
        ps1 = (_REPO_ROOT / "AutoClaude" / "tools" / "run_act.ps1").read_text(
            encoding="utf-8-sig"
        )
        # 剝註解後再比對：`<# … #>` 說明區塊裡當然會提到每一個旗標，不剝的話這條鎖
        # 對「文件寫了、param 沒補」完全盲目——那恰好就是 R77 的實況。
        ps1 = re.sub(r"<#.*?#>", "", ps1, flags=re.DOTALL)
        self.ps1 = "\n".join(
            ln for ln in ps1.splitlines() if not ln.lstrip().startswith("#")
        )

    def _core_long_flags(self) -> list[str]:
        """核心真正接受的長旗標——呼叫 `parse_args([])` 取 Namespace 欄位，不掃原始碼。"""
        ns = self.core.parse_args([])
        return sorted(f"--{k.replace('_', '-')}" for k in vars(ns))

    def test_core_flag_extraction_is_not_empty(self) -> None:
        flags = self._core_long_flags()
        self.assertGreaterEqual(
            len(flags), self._MIN_CORE_FLAGS,
            f"只抽到 {len(flags)} 個核心旗標（下限 {self._MIN_CORE_FLAGS}）——"
            f"parse_args 的形態疑似改變，而漂移方向正好是「兩側都對得上」",
        )

    def test_bash_shell_forwards_everything(self) -> None:
        """`.sh` 側靠 `"$@"` 全轉 —— 拿掉它就會退化成 `.ps1` 當年那種逐旗標映射。"""
        self.assertIn(
            '"$@"', self.sh,
            'run_act.sh 不再以 "$@" 全轉引數——一旦改成逐旗標映射，它就會和 run_act.ps1 '
            "一樣開始漏轉新旗標（那正是 SD-06 的病）。若確為刻意改動，請改為逐旗標斷言",
        )

    def test_powershell_shell_forwards_every_core_flag(self) -> None:
        """`.ps1` 側是顯式映射 ⇒ 每個核心長旗標的字面都必須真的出現在**非註解**碼上。

        刻意比「param 區有沒有同名參數」更嚴：R77 的失敗形態是**宣告與轉呼叫脫節**，
        而使用者痛的是「旗標沒被送到核心」，不是「param 區少一行」。
        """
        missing = [f for f in self._core_long_flags() if f not in self.ps1]
        self.assertEqual(
            missing, [],
            f"run_act.ps1 沒有把這些核心旗標轉下去：{missing} —— Windows 側因此碰不到"
            f"對應功能，而 check_script_parity／check_wrapper_thinness 對此結構性全綠"
            f"（hash 釘選只問「檔案有沒有變」，從不把兩側互相比較）。修法：在 param 區"
            f"補參數並在 $CliArgs 映射，**同一個 commit 內**以 "
            f"`python tools/check_wrapper_thinness.py --print-hash` 更新釘選",
        )

    def test_powershell_does_not_shadow_the_event_automatic_variable(self) -> None:
        """`$Event` 是 PowerShell 自動變數，不得拿來當參數名（鐵律三的活體實例）。

        對外拼法 `-Event` 由 `[Alias]` 保留，兩件事可以同時成立；本鎖擋的是「為了跟
        `--event` 對稱而直接叫 `$Event`」這個看起來最自然、實際會遮蔽 runtime 語意的寫法
        （PSScriptAnalyzer `PSAvoidAssignmentToAutomaticVariable`）。
        """
        self.assertNotRegex(
            self.ps1, r"\[string\]\$Event\b",
            "run_act.ps1 以 $Event 當參數名——那是 PowerShell 自動變數（事件訂閱 "
            "scriptblock 內由 runtime 填入）。請改名並以 [Alias('Event')] 保留對外拼法",
        )
        self.assertRegex(
            self.ps1, r"\[Alias\('Event'\)\]",
            "run_act.ps1 少了 [Alias('Event')] —— 少了它，`-Event` 這個與核心 --event "
            "對稱的對外拼法就不存在，使用者得記住兩套名字",
        )


if __name__ == "__main__":
    unittest.main()
