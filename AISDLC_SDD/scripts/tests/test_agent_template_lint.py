"""agent_template_lint 意圖鎖（DEF-AGTREV-002 + DEF-AGTREV-005 盲區封閉）.

每個 case 編碼「為何此行為重要」（Rule 9）：本 lint 的價值＝讓「agent 定義檔引用一個
不存在 / 非根相對 / 裸檔名（非 docs_template/ 前綴）的 template」這件事被機械擋下。

緣由（v0.18 重審）：原 lint 的 TOK regex 只認帶 `docs_template/` 前綴的 token，使核心
agent 內 12 條短名 broken template_path（如 `user-story-template.md`）+ 19 條誤指
`docs/` 輸出區的 template + 3 條 dependencies.templates 短名長期假綠潛伏。DEF-AGTREV-005
封閉盲區後，本測試鎖死三類偵測：
  (1) docs_template/ 路徑存在 → 0；
  (2) docs_template/ 路徑不存在 → 非零（BROKEN）；
  (3) ../docs_template/（非根相對）→ 非零（NON-ROOT-RELATIVE）；
  (4) 裸檔名 template_path（非 docs_template/ 前綴）→ 非零（BARE-NAME，盲區封閉）；
  (5) dependencies.templates 裸檔名 → 非零（清單項盲區封閉）；
  (6) dependencies.templates 指向存在的 docs_template/ → 0；
  (7) 突變實證：clean → 把路徑改裸名即轉紅（抓退化）。
任一退化都會讓「broken template 假綠」死灰復燃。
"""
from __future__ import annotations

import os

from scripts import agent_template_lint as atl

_VER = "AISDLC_SDD_v0.18"


def _write_template(repo: str, rel: str) -> None:
    """在 <ver>/docs_template/ 下建一個存在的模板檔（pool 來源）。"""
    p = os.path.join(repo, _VER, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write("# template\n")


def _write_agent(repo: str, fname: str, body: str) -> None:
    """以原始 YAML 文字寫 agent（含引號，對齊真實 agent 格式使 BARE regex 生效）。"""
    base = os.path.join(repo, _VER, "agent", "core")
    os.makedirs(base, exist_ok=True)
    with open(os.path.join(base, fname), "w", encoding="utf-8") as f:
        f.write(body)


def _agent_with_template_path(value: str) -> str:
    return (
        "agent:\n"
        "  id: \"sa-analyst\"\n"
        "document_responsibilities:\n"
        "  primary_documents:\n"
        "    - document_type: \"FRD\"\n"
        f"      template_path: \"{value}\"\n"
    )


# ── (1) docs_template/ 路徑存在 → 0 ──────────────────────────────────────────

def test_existing_docs_template_passes(tmp_path):
    repo = str(tmp_path)
    _write_template(repo, "docs_template/core/frd/FRD_Universal_Template.md")
    _write_agent(repo, "04.sa-analyst-zh.yaml",
                 _agent_with_template_path("docs_template/core/frd/FRD_Universal_Template.md"))
    assert atl.main([repo]) == 0


# ── (2) docs_template/ 路徑不存在 → 非零 ──────────────────────────────────────

def test_missing_docs_template_fails(tmp_path):
    repo = str(tmp_path)
    _write_template(repo, "docs_template/core/frd/FRD_Universal_Template.md")  # 別的存在檔，確保 pool 非空
    _write_agent(repo, "04.sa-analyst-zh.yaml",
                 _agent_with_template_path("docs_template/core/frd/DOES_NOT_EXIST.md"))
    assert atl.main([repo]) == 1


# ── (3) ../docs_template/（非根相對）→ 非零 ───────────────────────────────────

def test_non_root_relative_fails(tmp_path):
    repo = str(tmp_path)
    _write_template(repo, "docs_template/core/frd/FRD_Universal_Template.md")
    _write_agent(repo, "04.sa-analyst-zh.yaml",
                 _agent_with_template_path("../docs_template/core/frd/FRD_Universal_Template.md"))
    assert atl.main([repo]) == 1


# ── (4) 裸檔名 template_path（盲區封閉）→ 非零 ────────────────────────────────

def test_bare_name_template_path_fails(tmp_path):
    """DEF-AGTREV-005：裸檔名（非 docs_template/ 前綴）原 TOK 看不到 → 必須被 BARE 抓出。"""
    repo = str(tmp_path)
    _write_template(repo, "docs_template/core/frd/FRD_Universal_Template.md")
    _write_agent(repo, "04.sa-analyst-zh.yaml",
                 _agent_with_template_path("user-story-template.md"))
    assert atl.main([repo]) == 1


# ── (5) dependencies.templates 裸檔名（清單項盲區）→ 非零 ─────────────────────

def test_dependencies_templates_bare_name_fails(tmp_path):
    repo = str(tmp_path)
    _write_template(repo, "docs_template/core/frd/FRD_Universal_Template.md")
    body = (
        "agent:\n  id: \"ba-business-analyst\"\n"
        "dependencies:\n"
        "  templates:\n"
        "    - stakeholder-validation-template.md\n"
    )
    _write_agent(repo, "02.ba-business-analyst-zh.yaml", body)
    assert atl.main([repo]) == 1


# ── (6) dependencies.templates 指向存在的 docs_template/ → 0 ──────────────────

def test_dependencies_templates_valid_passes(tmp_path):
    repo = str(tmp_path)
    _write_template(repo, "docs_template/support/Requirement_Extraction_Report_Template.md")
    body = (
        "agent:\n  id: \"ba-business-analyst\"\n"
        "dependencies:\n"
        "  templates:\n"
        "    - docs_template/support/Requirement_Extraction_Report_Template.md\n"
    )
    _write_agent(repo, "02.ba-business-analyst-zh.yaml", body)
    assert atl.main([repo]) == 0


# ── (4b) DEF-AGTREV-008：非 .md 副檔名（.yaml）誤指 docs/ 也須抓 ────────────────

def test_non_md_yaml_template_in_docs_fails(tmp_path):
    """sdd_skills 的 API CONTRACT template 為 .yaml；原 `\\.md` 規格漏抓誤指 docs/ 者。
    擴 _TMPL_EXT 後，指向非 docs_template/ 的 .yaml 必須非零。"""
    repo = str(tmp_path)
    _write_template(repo, "docs_template/sdd/api/CONTRACT-TEMPLATE.yaml")
    _write_agent(repo, "05.sd-architect-zh.yaml",
                 "agent:\n  id: \"sd-architect\"\n"
                 "sdd_skills:\n"
                 "  contract_first:\n"
                 "    template: \"docs/02_architecture/api/CONTRACT-TEMPLATE.yaml\"\n")
    assert atl.main([repo]) == 1


def test_valid_yaml_docs_template_passes(tmp_path):
    """指向存在的 docs_template/ .yaml → 0（確認擴副檔名後不誤殺合法 .yaml）。"""
    repo = str(tmp_path)
    _write_template(repo, "docs_template/sdd/api/CONTRACT-TEMPLATE.yaml")
    _write_agent(repo, "05.sd-architect-zh.yaml",
                 "agent:\n  id: \"sd-architect\"\n"
                 "sdd_skills:\n"
                 "  contract_first:\n"
                 "    template: \"docs_template/sdd/api/CONTRACT-TEMPLATE.yaml\"\n")
    assert atl.main([repo]) == 0


# ── (8) AGT-11（R85）：dependencies 另四桶擴面 ────────────────────────────────
#
# 為何這幾個 case 重要（Rule 9）：本 lint 在 R85 之前只驗 `dependencies.templates`
# **一個**桶，而 `dependencies` 有五個桶。另四桶在 HEAD 實測共 302 條、其中 301 條在版本樹內
# 零解析，卻**結構上不會轉紅**——lint 照跑、照綠，只是那四桶從來不在分母裡。
# 以下 case 鎖死的是「分母不得再被桶名窄化」：任一 case 退化，301 條幽靈依賴的假綠即復活。
#
# 🔴 被訂正的原文逐字保留（訂正協議：禁止靜默覆寫）：「另四桶當回合實測共 199 條、其中
#    198 條在版本樹內零解析」／「198 條幽靈依賴的假綠即復活」。兩個數字都假（真值 302／301）；
#    上一句話尤其危險——它斷言一個**今天不可能被任何人驗證為真**的數量，而讀者會拿它當
#    這幾個 case 的價值依據。數字與判準來源見 `agent_template_lint.py` 檔頭同節（不複寫）。
#
# 🔴 **今天的活分母是 1**：301 條已於同輪清除，四桶現存 data 1／tasks 0／checklists 0／
#    tools 0。⇒ 以下 case 全部是**純寫入面**保護（存量已空，守的是下一個人寫出違規時當場紅），
#    它們的鑑別力**不能靠真實樹自證**——真實樹今天無論判準好壞都是綠的。
#    鑑別力有兩向、由兩支 case 分別承擔，缺一即失明：
#      ① 判準對桶內容有沒有鑑別力 → `test_ghost_bare_name_in_each_dep_bucket_fails`
#      ② 桶集合本身會不會被縮掉   → `test_dep_asset_buckets_may_not_shrink`
#    ①**守不住**②（它的迴圈讀的就是那個常數，縮清單＝縮迴圈，照樣全綠；F2 突變實證
#    見該 case docstring）——這是 F2 複審在本區塊抓到的第四筆，SD 三筆駁回未涵蓋。


def _write_tree_asset(repo: str, rel: str) -> None:
    """在 <ver>/ 下（docs_template/ 之外）建一個存在的資產檔——判準 4 的解析面是整棵版本樹。"""
    p = os.path.join(repo, _VER, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write("# asset\n")


def _agent_with_dep_bucket(bucket: str, value: str) -> str:
    return (
        "agent:\n  id: \"dev-developer\"\n"
        "dependencies:\n"
        f"  {bucket}:\n"
        f"    - {value}\n"
    )


def test_ghost_bare_name_in_each_dep_bucket_fails(tmp_path):
    """四桶各自都必須在分母裡——只補其中一桶就是把同一個盲區留給下一個桶。

    🔴 F2 複審補記（本 case 的射程比它讀起來的小）：迴圈跑的是 ``atl.DEP_ASSET_BUCKETS``
    **本身**，所以它守得住「桶在清單裡、但判準對它沒鑑別力」，**守不住「有人把桶從清單裡
    拿掉」**——清單縮短時迴圈跟著縮短，本 case 照樣全綠。F2 突變實證：把常數改成
    ``("data",)``（刪掉 tasks／checklists／tools 三桶）後單獨跑本 case ⇒ **1 passed**。
    而「分母不得再被桶名窄化」正是本區塊註解宣稱要鎖的那件事 ⇒ 本 case 對它結構上失明，
    與本 lint 判準 4 當初要治的「分母被常數窄化」**是同一個病，只是搬到測試身上**。
    真正守那一向的是下一個 case（``test_dep_asset_buckets_may_not_shrink``）。
    """
    for bucket in atl.DEP_ASSET_BUCKETS:
        repo = str(tmp_path / bucket)
        _write_template(repo, "docs_template/core/frd/FRD_Universal_Template.md")
        _write_agent(repo, "06.dev-developer-zh.yaml",
                     _agent_with_dep_bucket(bucket, "coding-standards.md"))
        assert atl.main([repo]) == 1, f"{bucket} 桶的幽靈依賴未被擋下"


def test_dep_asset_buckets_may_not_shrink():
    """判準 4 的桶集合是 shrink-forbidden 棘輪：只准長，不准縮。

    為何此行為重要（Rule 9）：上一個 case 的分母是這個常數，所以**縮小常數是繞過整組
    判準最省力的方式**，而它不會讓任何既有 case 轉紅（F2 突變實證：縮成單桶 ⇒ 1 passed）。
    本 case 是唯一比對「清單 ↔ 一份寫死的期望」的地方，故意不從被測模組取值——
    從被測模組取值的斷言，正是它要防的那個形狀。

    ``dependencies`` 的五個桶：``templates`` 走更嚴的 ``docs_template/`` 前綴規則（判準 3），
    其餘四桶走判準 4。新增第六個桶時本 case 應**加**一個名字（分母變大＝好事），
    刪桶則必須先在此處說明為什麼那個桶不再需要被判。
    """
    assert set(atl.DEP_ASSET_BUCKETS) >= {"data", "tasks", "checklists", "tools"}, (
        "判準 4 的桶集合被縮小——被移除的桶會退回『分母 0 的恆綠鎖』，"
        "而 lint 仍會照跑、照綠、照回報命中數"
    )


def test_dep_bucket_entry_resolving_in_tree_passes(tmp_path):
    """判準 4 刻意不要求 docs_template/ 前綴：四桶的合法標的可以是 guides/ 等任何版本樹內資產。
    把 templates 桶那條更嚴的前綴規則外推過來會製造假紅，而那種鎖活不過一輪。"""
    repo = str(tmp_path)
    _write_template(repo, "docs_template/core/frd/FRD_Universal_Template.md")
    _write_tree_asset(repo, "guides/user/process/Development_Build_Test_Cycle.md")
    _write_agent(repo, "06.dev-developer-zh.yaml",
                 _agent_with_dep_bucket("data", "guides/user/process/Development_Build_Test_Cycle.md"))
    assert atl.main([repo]) == 0


def test_dep_bucket_entry_with_dotdot_prefix_fails(tmp_path):
    """存在但帶 ../ ⇒ 仍非零（框架根相對是單一慣例）。這正是真實樹上唯一那一條的形態：
    它指向真實存在的檔，所以「刪掉」是錯的處置，「修正前綴」才是。"""
    repo = str(tmp_path)
    _write_template(repo, "docs_template/core/frd/FRD_Universal_Template.md")
    _write_tree_asset(repo, "guides/user/process/Development_Build_Test_Cycle.md")
    _write_agent(repo, "06.dev-developer-zh.yaml",
                 _agent_with_dep_bucket("data", "../guides/user/process/Development_Build_Test_Cycle.md"))
    assert atl.main([repo]) == 1


def test_tmpl_ext_escape_hatch_is_registered_not_endorsed(tmp_path):
    """`_TMPL_EXT` 逃生門＝**已登記的 fail-open**，本 case 是登記，不是背書。

    🔴 被訂正的原意圖逐字保留（訂正協議：禁止靜默覆寫）——本 case 原名
    ``test_dep_bucket_non_file_entry_is_not_a_false_red``，docstring 為「無副檔名的描述性
    條目不判（同 templates 桶既有的避誤報慣例）——這條 case 守的是『判準要收窄而不是硬上』，
    否則假紅會多到要逐一辯護」。

    為何原意圖需要訂正（F2 複審實測）：那段話把逃生門講成「正在防一批假紅」，
    而**那批假紅今天一條都不存在**。全判準面逐條實測：四桶 1 條、``templates`` 桶 42 條、
    行級 ``BARE`` regex 117 條，合計 160 條，**被 `_TMPL_EXT` 略過者＝0 條**
    ——逃生門today 沒有任何消費者，它防的是一個空集合。與此同時它是可利用的：
    同一個不存在的標的，只要**把副檔名拿掉**就從 rc=1 變成 rc=0（下方兩段斷言即該利用手法
    的紅綠對照）。這正是本輪在別處判過的「2 支測試把 fail-open 釘成契約」同型——
    下一個人想收緊判準時，會先撞到自己人蓋的這道鎖。

    本 case 因此**保留但改變語意**：它記錄「現行行為是放行」這個事實，讓退化可見；
    它**不主張**放行是對的。要收緊時，正確動作是連同本 case 一起改（並在此補上新的
    立案事實），而不是把它當成不可動的契約繞開。刻意不在本輪逕行收緊：真實樹上
    `dependencies` 的合法描述性條目未來仍可能出現，收緊屬判準變更，需自帶立案事實。
    """
    repo = str(tmp_path)
    _write_template(repo, "docs_template/core/frd/FRD_Universal_Template.md")
    # (a) 帶副檔名的不存在標的 → 擋下（判準有鑑別力）
    _write_agent(repo, "06.dev-developer-zh.yaml",
                 _agent_with_dep_bucket("tools", "static-analysis-tooling.md"))
    assert atl.main([repo]) == 1, "帶副檔名的幽靈依賴必須擋下，否則判準 4 整條失效"
    # (b) 同一個不存在的標的、只拿掉副檔名 → 放行。這一行就是逃生門的射程。
    _write_agent(repo, "06.dev-developer-zh.yaml",
                 _agent_with_dep_bucket("tools", "static analysis tooling"))
    assert atl.main([repo]) == 0


# ── (7) 突變實證：clean → 改裸名即轉紅 ────────────────────────────────────────

def test_clean_then_bare_name_detects_regression(tmp_path):
    repo = str(tmp_path)
    _write_template(repo, "docs_template/core/frd/FRD_Universal_Template.md")
    _write_agent(repo, "04.sa-analyst-zh.yaml",
                 _agent_with_template_path("docs_template/core/frd/FRD_Universal_Template.md"))
    assert atl.main([repo]) == 0
    # 突變：根相對改裸名 → 盲區若復活則仍 0；封閉後必須轉 1
    _write_agent(repo, "04.sa-analyst-zh.yaml",
                 _agent_with_template_path("frd-template.md"))
    assert atl.main([repo]) == 1
