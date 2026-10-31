# 受測面：docs/02_architecture/Root_Layout_and_Module_Placement.md 等 P0 文件（文件結構測試）
"""帳本改 DB P0 的時間穩定驗收（TCS-SelfImprovingLedgerDb-P0 的 DT 全集，共 14 個 AT）。

方法名含 AT 底線形，`-k AT_LD_11_4_1_` 可單跑。只放時間穩定謂詞與判準函式的合成紅綠自證；內容
字樣與一次性驗收（`sql_draft_problems`、`p0_acceptance_problems`）只以函式形態存在，由審查閘
G-P0-13 呼叫、DT 不跑。被測文件尚未交付時對應 AT 為紅（不略過）；DT 不讀 build/、不連 PG。
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import test_root_module_layout as tml  # noqa: E402

from lib.selfimproving.params import CHECK_RULES_REV, PROTOCOL_REL, fingerprint  # noqa: E402

ARCH, QUAL = "docs/02_architecture", "docs/06_quality"
RL = f"{ARCH}/Root_Layout_and_Module_Placement.md"
THIS = "tools/tests/test_selfimproving_ledgerdb_p0.py"
DRAFT = f"{ARCH}/SelfImproving_LedgerDb_Architecture_Draft.md"
ERRATA = f"{QUAL}/SelfImproving_LedgerDb_P0_Errata.md"
BASELINE = f"{QUAL}/SelfImproving_LedgerDb_P0_Baseline.md"
PRERUN = f"{QUAL}/SelfImproving_LedgerDb_P0_Ratchet_PreRun.md"
# TCS 契約節 C1.3：SelfImproving 登記列須登記的路徑（只對磁碟上已存在者要求；glob 以存在任一檔計）
REGISTERED = (THIS, f"{ARCH}/ADR-SIDB-*.md", DRAFT, ERRATA, BASELINE, PRERUN)

# TCS C1.1：兩格的落點與規則欄必含字樣（單一家；其餘處一律引用本表）
PG_WORDS = (
    "WHY", "SKIP-M6", "guardrail_cli", "750", "≤4", "≤3", "不計入", "行數棘輪", "skip 政策",
    "run_root_unittests", "ruff", "SI_TEST_PG_DSN", "SI_TEST_PG_REQUIRED",
)
SQL_WORDS = (
    "WHY", "V<NNN>__", "UTF-8", "LF", "只追加", "MIGRATION-CHECKSUM", "不含密碼", "PGPASSFILE",
    "non_evolvable_globs", "*.py",
)
CELLS = {
    "PG 專屬契約測試": ("`tools/tests_pg/`", PG_WORDS),
    "套件內 SQL 遷移資料目錄": ("`tools/lib/<module>/sql/`", SQL_WORDS),
}

# TCS C2 與 5.2：ADR 六節，及逐檔必含（N -> 選項標籤、「決定」節字樣、「狀態」節字樣）
SIX = ("## 狀態", "## 脈絡", "## 選項與代價", "## 決定", "## 再開症狀", "## 連動面")
ADR_SPEC = {
    1: (tuple("ABCD"), ("C", "B 在同樣隔離下可接受", "影子期任何可達的 PG18", "單一主力機為真相"),
        ("階段性", "H2", "H3")),
    2: (tuple("ABC"),
        ("B", "tools/tests_pg/", "LEDGER_TRUTH", "SI_LEDGER_STORE", "file", "shadow", "db"), ()),
    3: (tuple("ABC"), ("B", "錨點", "快照內鏈頭", "audit_chain_guard", "row_hash"), ()),
    4: (tuple("ABC"), ("B", "READ-MODEL-STALE", "ledger_head"), ()),
    5: (tuple("ABC"), ("B", "pg_advisory_xact_lock", "max+1", "lock_timeout"), ()),
    6: (("A", "B", "B′"),
        ("B", "B′", "console.si.write-carrier", "file", "dual", "db", "audit_sha256"), ()),
    7: (tuple("ABC"), ("B", "SI_DB_DSN", "PGPASSFILE", "sslmode", "D-5"), ()),
    8: (("(a)", "(b)", "(c)", "(d)"),
        ("舊檔永遠保留", "(b)", "(c)", "AUTOSDD_SNAPSHOT_GATE_OFF",
         "docs/06_quality/SelfImproving_Snapshots/", "pg_dump -n si"), ()),
}
SQL_TOKENS = (
    "CREATE SCHEMA", "si_owner", "si_writer", "si_reader", "RETURNS trigger",
    "BEFORE UPDATE OR DELETE", "integrity_constraint_violation", "CREATE CONSTRAINT TRIGGER",
    "DEFERRABLE INITIALLY DEFERRED", "audit_chain_guard", "pg_advisory_xact_lock", "sha256(",
    "txid", "prev_hash", "row_hash", "after_sha", "row_sha256", "REVOKE", "GRANT",
)
CLASSES = ("追加專用", "可變且逐列 audit", "讀模型", "自舉例外")
_TABLES = (
    "events artifacts audit legacy_rows console_audit_files", "observations defects debt_tracks",
    "issues export_items export_meta", "schema_migrations meta import_runs",
)
TABLE_CLASS = {t: cls for cls, tables in zip(CLASSES, _TABLES) for t in tables.split()}
CONN = re.compile(r"postgres(?:ql)?://[^<\s]*:[^<\s@]+@")  # 帶密碼段的連線字串（B-15）
BARE_M = re.compile(r"(?<![-\w])M[1-7](?!\d)")  # 命名紀律：裸 M 編號（D10）

# TCS C3、C4、C6：草稿補丁、勘誤欄位、預演證據檔的必要結構
PATCHES = (("§7.2", "Architecture.md:612"), ("§9.4", ":854"), ("§10.3", ":944"))
PATCH_LABELS = ("目標檔：", "插入文：", "生效階段：", "路由：")
# TCS §7.1#2／§7.3：三塊補丁各自的生效階段（SCG-4 一審 F-06：此前只驗行首字樣在、不驗值）
PATCH_STAGES = {"§7.2": "P3", "§9.4": "P1", "§10.3": "P2"}
E_FIELDS = ("目標文件", "原文座標", "原文", "訂正文", "生效階段", "套用階段", "理由")
PRERUN_PARTS = ("預演腳本", "輸出表", "標籤規則", "結論", "乾跑選檔名單")
PRERUN_WORDS = (
    "S-A", "S-B", "P0", "P1", "P2", "P3a", "P3b", "P4", "repin_growth_problems",
    "repin_cost_ratchet_problems", "TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound",
    "_REPIN_APPROVED_ROUND_OVERAGE",
)


def read_doc(rel: str, root: Path = ROOT) -> str:
    """讀文件的位元組；缺檔、BOM、CR 一律當失敗（B-01：被 CRLF 化時所有讀它的 DT 一起紅）。"""
    path = root / rel
    if not path.is_file():
        raise AssertionError(f"{rel}：檔不存在（尚待交付）")
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise AssertionError(f"{rel}：須為 UTF-8 無 BOM、LF only")
    return raw.decode("utf-8")


def _split(text: str, level: int) -> list[tuple[str, str]]:
    """依 `#`×level 標題切節：圍欄內不算標題；同級或更高階標題終止該節，較低階不終止。"""
    out: list[list] = []
    fenced = False
    for line in text.split("\n"):
        fenced ^= line.lstrip().startswith("```")
        head = None if fenced else re.match(r"(#{1,6}) ", line)
        if head and len(head.group(1)) <= level:
            out.append([line.strip() if len(head.group(1)) == level else "", []])
        elif out:
            out[-1][1].append(line)
    return [(key, "\n".join(body)) for key, body in out if key]


def sections(text: str, level: int = 2) -> dict[str, str]:
    return dict(_split(text, level))


def section_of(text: str, prefix: str) -> str:
    return next((body for key, body in sections(text).items() if key.startswith(prefix)), "")


def table_rows(section: str) -> list[list[str]]:
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")]
            for ln in section.split("\n") if ln.startswith("|")]
    return [r for r in rows if not set("".join(r)) <= set("-: ")]


def layout_cell_problems(text: str) -> list[str]:
    """`## 2.` 節的兩新列：恰一列、落點格、規則格必含字樣（C1.1）。"""
    rows = table_rows(section_of(text, "## 2."))
    out: list[str] = []
    for name, (landing, words) in CELLS.items():
        hit = [r for r in rows if len(r) >= 3 and name in r[0]]
        if len(hit) == 1:
            out += [f"{name}：落點格缺 {landing}"] if landing not in hit[0][1] else []
            out += [f"{name}：規則格缺字樣 {w}" for w in words if w not in hit[0][2]]
        else:
            out.append(f"{name}：## 2. 節應恰一列，實得 {len(hit)} 列")
    return out


def adr_title_problems(filename: str, text: str) -> list[str]:
    name = re.fullmatch(r"ADR-SIDB-(00[1-8])-[a-z0-9-]+\.md", filename)
    title = next(iter(sections(text, 1)), "")
    m = re.fullmatch(r"# ADR-SIDB-(00[1-8])：(.+)（PRD 簡稱 SIDB-(0[1-8])）", title)
    if name is None:
        return ["檔名須符合 ADR-SIDB-00N-<小寫 slug>.md（N 為 1～8）"]
    if m is None:
        return [f"標題格式不符：{title!r}"]
    if m.group(1) != name.group(1):
        return [f"標題編號 {m.group(1)} 與檔名編號 {name.group(1)} 不一致"]
    return []


def adr_problems(filename: str, text: str) -> list[str]:
    """C2：標題、六節順序、選項計數規則（5.1.2）、再開症狀的反引號 token、狀態值。"""
    out = adr_title_problems(filename, text)
    body = sections(text)
    heads = [key for key, _ in _split(text, 2) if key in SIX]
    if heads != list(SIX):
        missing = [h for h in SIX if h not in heads]
        out.append(f"六節標題缺 {missing}" if missing else f"六節標題順序或重複不符：{heads}")
    status = next((ln for ln in body.get("## 狀態", "").split("\n") if ln.strip()), "")
    if not status.startswith(("Accepted", "Superseded")):
        out.append(f"狀態值須以 Accepted 或 Superseded 起頭，實得 {status!r}")
    costs: list[int] = []  # 每個選項其後的「- 代價：」行數
    for ln in body.get("## 選項與代價", "").split("\n"):
        if re.match(r"\s*- 選項 [^：\s]+：", ln):
            costs.append(0)
        elif re.match(r"\s*- 代價：", ln) and costs:
            costs[-1] += 1
    if len(costs) < 2:
        out.append(f"選項與代價須 ≥2 個選項，實得 {len(costs)}")
    out += [f"第 {i} 個選項的「- 代價：」行數應恰 1，實得 {n}"
            for i, n in enumerate(costs, 1) if n != 1]
    items: list[str] = []  # 再開症狀的條目：頂層項目符號行（含其縮排的續行與子項）
    for ln in body.get("## 再開症狀", "").split("\n"):
        if re.match(r"(?:[-*]|\d+\.) ", ln):
            items.append(ln)
        elif items and ln.strip():
            items[-1] += " " + ln.strip()
    out += [] if items else ["再開症狀須 ≥1 條"]
    return out + [f"再開症狀第 {i} 條缺反引號 token" for i, it in enumerate(items, 1)
                  if not any(t.strip() for t in re.findall(r"`([^`]+)`", it))]


def adr_decision_problems(n: int, text: str) -> list[str]:
    """5.2.1：該 N 的必含選項標籤、「決定」節字樣、「狀態」節字樣。"""
    labels, decision_words, status_words = ADR_SPEC[n]
    body = sections(text)
    found = set(re.findall(r"^\s*- 選項 ([^：\s]+)：", body.get("## 選項與代價", ""), flags=re.M))
    out = [f"選項標籤缺 {lab}" for lab in labels if lab not in found]
    out += [f"決定節缺字樣 {w}" for w in decision_words if w not in body.get("## 決定", "")]
    return out + [f"狀態節缺字樣 {w}" for w in status_words if w not in body.get("## 狀態", "")]


def conn_problems(text: str) -> list[str]:
    """連線字串字面（B-15）；只報行號，不回顯內容。"""
    lines = text.split("\n")
    return [f"連線字串字面（第 {i} 行）" for i, ln in enumerate(lines, 1) if CONN.search(ln)]


def sql_draft_problems(text: str) -> list[str]:
    """ADR-003：```sql 區塊與物件字樣、14 表守衛矩陣逐表分類、不重算 row_hash 句意、無連線字串。"""
    blocks = re.findall(r"^```sql\n(.*?)^```", text, flags=re.S | re.M)
    if not blocks:
        return ["缺 ```sql 區塊"]
    out = [f"SQL 區塊缺字樣 {w}" for w in SQL_TOKENS if w not in "\n".join(blocks)]
    rows = table_rows(re.sub(r"^```.*?^```", "", text, flags=re.S | re.M))
    for table, cls in TABLE_CLASS.items():
        hit = [" ".join(r[1:]) for r in rows if r[0].replace("`", "").removeprefix("si.") == table]
        if not hit:
            out.append(f"守衛矩陣缺表 {table}")
        elif cls not in hit[0] or any(c in hit[0] for c in CLASSES if c != cls):
            out.append(f"守衛矩陣的 {table} 分類應為「{cls}」（每表恰屬一類）")
    if not re.search(r"不重算[^\n]{0,12}row_hash", text):
        out.append("缺「不重算 row_hash」句意字樣")
    return out + conn_problems(text)


def draft_problems(text: str) -> list[str]:
    """C3：三塊補丁標題、每塊四個行首字樣與目標檔座標；§7.2 另含 B／C 方案小標與 docker README。"""
    out: list[str] = []
    heads = sections(text)
    for key, coord in PATCHES:
        hit = [b for h, b in heads.items() if h.startswith("## 補丁") and key in h]
        if len(hit) != 1:
            out.append(f"補丁 {key}：標題應恰一個，實得 {len(hit)} 個")
            continue
        out += [f"補丁 {key}：缺行首字樣 {lab}" for lab in PATCH_LABELS
                if not re.search(f"^{lab}", hit[0], flags=re.M)]
        out += [f"補丁 {key}：目標檔座標字樣缺 {coord}"] if coord not in hit[0] else []
        stage = re.search(r"^生效階段：(P\w+)", hit[0], flags=re.M)
        if stage and stage.group(1) != PATCH_STAGES[key]:
            out.append(f"補丁 {key}：生效階段 {stage.group(1)} 應為 "
                       f"{PATCH_STAGES[key]}（TCS §7.1#2）")
        if key == "§7.2":
            out += [f"補丁 §7.2：缺小標 ### {v} 方案" for v in "BC"
                    if not re.search(f"^### {v} 方案", hit[0], flags=re.M)]
    return out + ([] if "docker/README.md" in text else ["缺 docker/README.md〈4.3〉的補丁說明"])


def errata_problems(text: str) -> list[str]:
    """C4：E-1～E-7 七節、七欄位標籤且非空、套用階段值域、E-4 核准座標、E-6／E-7 目標、不勘誤節。"""
    entries = {m.group(1): dict(re.findall(r"^- ([^：\n]+)：(.*)$", m.group(2), flags=re.M))
               for m in re.finditer(r"^### (E-\d+)\n((?:- .*\n?)+)", text, flags=re.M)}
    want = [f"E-{i}" for i in range(1, 8)]
    out = [] if sorted(entries) == want else [f"應恰含 E-1～E-7，實得 {sorted(entries)}"]
    for name, fields in sorted(entries.items()):
        out += [f"{name} 缺欄位或欄值為空：{k}" for k in E_FIELDS if not fields.get(k, "").strip()]
        if not re.match(r"P(?:1|2|3a|3b)", fields.get("套用階段", "")):
            out.append(f"{name} 套用階段須以 P1、P2、P3a、P3b 之一起頭")
    e4 = " ".join(entries.get("E-4", {}).values())
    if "〈sid／line 由主控填〉" not in e4 and not re.search(r"sid [0-9a-f-]{36} line \d+", e4):
        out.append("E-4 缺核准座標欄（佔位或已填）")
    out += [f"{n} 的目標文件須為 Issue_Center_PRD.md" for n in ("E-6", "E-7")
            if "Issue_Center_PRD.md" not in entries.get(n, {}).get("目標文件", "")]
    waived = sections(text).get("## 不勘誤", "")
    return out + [f"## 不勘誤 節缺 {t}（或缺該節）" for t in ("#6", "#8", "#9") if t not in waived]


def bare_m_hits(text: str) -> list[str]:
    return [f"{i}: {ln.strip()}" for i, ln in enumerate(text.split("\n"), 1) if BARE_M.search(ln)]


def fingerprint_of(tree: Path) -> str:
    params = json.loads((tree / PROTOCOL_REL / "params.json").read_text(encoding="utf-8"))
    return fingerprint(tree, params)[0]


def baseline_value(text: str, label: str) -> str | None:
    """基準檔表中「項」等於 label 的最後一列的「值」欄（C5：同項多列取最後一列）。"""
    vals = [r[1] for r in table_rows(text)
            if len(r) >= 2 and r[0].replace("`", "").replace("*", "").strip() == label]
    return vals[-1] if vals else None


def scan_docs(rels, check, root: Path = ROOT) -> list[str]:
    """逐檔讀文件並跑 check(rel, 文字)；缺檔、BOM、CR 也回報（尚待交付＝紅）。"""
    out: list[str] = []
    for rel in rels:
        try:
            text = read_doc(rel, root)
        except AssertionError as exc:
            out.append(str(exc))
            continue
        out += [f"{rel}：{p}" for p in check(rel, text)]
    return out


def adr_scan(check, root: Path = ROOT) -> list[str]:
    """ADR-SIDB-001～008 各取唯一一檔跑 check(檔名, 文字)；缺檔或重複＝紅。"""
    found = sorted((root / ARCH).glob("ADR-SIDB-*.md"), key=lambda p: p.name)
    out: list[str] = []
    rels: list[str] = []
    for n in range(1, 9):
        files = [p.name for p in found if p.name.startswith(f"ADR-SIDB-{n:03d}-")]
        if len(files) == 1:
            rels.append(f"{ARCH}/{files[0]}")
        else:
            out.append(f"ADR-SIDB-{n:03d}：應恰一檔，實得 {len(files)} 檔")
    return out + scan_docs(rels, lambda rel, text: check(Path(rel).name, text), root)


def p0_acceptance_problems(root: Path) -> list[str]:
    """一次性驗收（G-P0-13；DT 不跑）：ADR 決定字樣、ADR-003 的 SQL 草稿、草稿補丁、連線字串。"""
    def adr(name: str, text: str) -> list[str]:
        n = int(name.split("-")[2])
        extra = sql_draft_problems(text) if n == 3 else conn_problems(text)
        return adr_decision_problems(n, text) + extra

    def other(rel: str, text: str) -> list[str]:
        return conn_problems(text) + (draft_problems(text) if rel == DRAFT else [])

    return adr_scan(adr, root) + scan_docs((DRAFT, ERRATA, BASELINE, PRERUN), other, root)


def synth_layout(without: str = "", drop: str = "") -> str:
    """合成 SSOT 文字：`## 2.` 含兩新列（可去掉一列、或缺一個字樣）。"""
    rows = "".join(f"| {name} | {land} | {' '.join(w for w in words if w != drop)} |\n"
                   for name, (land, words) in CELLS.items() if name != without)
    head = "## 1. 地圖\n\n## 2. 落點\n\n| 內容 | 落點 | 規則 |\n|---|---|---|\n"
    return head + rows + "\n## 3. 登記\n"


def synth_adr(n: int = 2, status: str = "Accepted", costs: int = 3,
              reopen: str = "- `si-pg-contract` 跑不起來",
              decision: str = " ".join(ADR_SPEC[2][1])) -> str:
    """合規的合成 ADR（記憶體字串；預設決定節含 002 的全部必含字樣）；參數造反例。"""
    opts = "".join(f"- 選項 {lab}：x\n" + ("- 代價：y\n" if i < costs else "")
                   for i, lab in enumerate("ABC"))
    return (f"# ADR-SIDB-00{n}：標題（PRD 簡稱 SIDB-0{n}）\n\n## 狀態\n\n{status}\n\n"
            f"## 脈絡\n\nx\n\n## 選項與代價\n\n{opts}\n## 決定\n\n{decision}\n\n"
            f"## 再開症狀\n\n{reopen}\n\n## 連動面\n\nx\n")


def synth_sql_doc() -> str:
    matrix = "".join(f"| `si.{t}` | {c} |\n" for t, c in TABLE_CLASS.items())
    return ("```sql\n" + "\n".join(SQL_TOKENS) + "\n```\n\n| 表 | 類 |\n|---|---|\n" + matrix
            + "\n`audit_chain_guard` 只驗 seq 連續、prev_hash 銜接與 txid，不重算 `row_hash`。\n")


def synth_draft() -> str:
    blocks = [f"## 補丁 {k} 標題\n\n目標檔：{c}-9\n插入文：x\n"
              f"生效階段：{PATCH_STAGES[k]}\n路由：甲、乙\n"
              for k, c in PATCHES]
    return ("# 草稿\n\n" + blocks[0] + "\n### B 方案（x）\n\n### C 方案（y）\n\n"
            + "\n".join(blocks[1:]) + "\ndocker/README.md〈4.3〉\n")


class TestRootLayoutCells(unittest.TestCase):
    """`docs/02_architecture/Root_Layout_and_Module_Placement.md` 的兩新格、地圖與登記（D1）。"""

    def _cell_problems(self, name: str) -> list[str]:
        return [p for p in layout_cell_problems(read_doc(RL)) if p.startswith(name)]

    def test_AT_LD_11_4_1_root_layout_has_the_pg_contract_test_cell(self):
        problems = self._cell_problems("PG 專屬契約測試")
        self.assertEqual(problems, [], "\n".join(problems))

    def test_AT_LD_11_4_2_root_layout_has_the_sql_migration_dir_cell(self):
        problems = self._cell_problems("套件內 SQL 遷移資料目錄")
        self.assertEqual(problems, [], "\n".join(problems))

    def test_AT_LD_11_4_3_map_row_and_registry_cover_the_existing_p0_paths(self):
        text = read_doc(RL)
        rows = [r for r in table_rows(section_of(text, "## 1."))
                if len(r) >= 3 and "`tools/tests_pg/`" in r[0]]
        problems: list[str] = []
        if len(rows) != 1:
            problems.append(f"## 1. 應恰一列首格含 `tools/tests_pg/`，實得 {len(rows)} 列")
        else:
            problems += [f"## 1. 列缺字樣 {w}" for w in ("PG 專屬", "不進 runner discover 根")
                         if w not in rows[0][1]]
            problems += [] if "§2" in rows[0][2] else ["## 1. 列的權威指引欄未指向本檔 §2"]
        si = next((r for r in tml.registry_rows(ROOT) if r[0].startswith("SelfImproving")), None)
        if si is None:
            problems.append("## 3. 缺 SelfImproving 登記列")
        else:
            frags = set(re.findall(r"`([^`]+)`", si[3] + " " + si[4]))
            problems += [f"## 3. SelfImproving 列未登記已存在的 {rel}"
                         for rel in REGISTERED if any(ROOT.glob(rel)) and rel not in frags]
        self.assertEqual(problems, [], "\n".join(problems))

    def test_AT_LD_11_4_E_1_layout_checker_names_missing_cells_and_words(self):
        self.assertEqual(layout_cell_problems(synth_layout()), [])
        pg, sql, word = "PG 專屬契約測試", "套件內 SQL 遷移資料目錄", "SI_TEST_PG_REQUIRED"
        for label, text, want in (
            ("缺 PG 列", synth_layout(without=pg), f"{pg}：## 2. 節應恰一列"),
            ("缺 SQL 列", synth_layout(without=sql), f"{sql}：## 2. 節應恰一列"),
            ("缺字樣", synth_layout(drop=word), f"規則格缺字樣 {word}"),
        ):
            with self.subTest(label):
                self.assertTrue(any(want in p for p in layout_cell_problems(text)), want)

    def test_AT_LD_11_4_E_2_registering_a_missing_path_is_red_for_the_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tml.write(root, "tools/real.py")
            tml.make_ssot(root, [tml.row("SelfImproving", tests="`tools/tests_pg/`")])
            problems = tml.registry_problems(root)
            self.assertTrue(any("tools/tests_pg/" in p for p in problems), problems)
            tml.make_ssot(root, [tml.row("SelfImproving", tests="`tools/real.py`")])
            self.assertEqual(tml.registry_problems(root), [])


class TestAdrFiles(unittest.TestCase):
    """`docs/02_architecture/ADR-SIDB-001～008` 八個 ADR 檔的命名、標題與六節結構（D3）。"""

    def test_AT_LD_00_D3_1_eight_adr_files_with_matching_titles(self):
        problems = adr_scan(adr_title_problems)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_AT_LD_00_D3_2_every_adr_has_six_sections_options_and_signals(self):
        problems = adr_scan(adr_problems)
        self.assertEqual(problems, [], "\n".join(problems))


class TestAdrNegativeControls(unittest.TestCase):
    """`docs/02_architecture/ADR-SIDB-*.md` 之判準函式的合成紅綠自證（記憶體字串，不讀真檔）。"""

    def test_AT_LD_00_D3_E_1_adr_checkers_name_each_broken_variant(self):
        good, name = synth_adr(), "ADR-SIDB-002-dal-and-modes.md"
        self.assertEqual(adr_problems(name, good), [])
        self.assertEqual(adr_decision_problems(2, good), [])
        for label, found, want in (
            ("缺再開症狀", adr_problems(name, good.replace("## 再開症狀", "## 別的")), "再開症狀"),
            ("無反引號", adr_problems(name, synth_adr(reopen="- 跑不起來")), "缺反引號"),
            ("缺代價行", adr_problems(name, synth_adr(costs=2)), "代價"),
            ("狀態 Draft", adr_problems(name, synth_adr(status="Draft")), "狀態值"),
            ("編號不符", adr_problems("ADR-SIDB-003-dal-and-modes.md", good), "不一致"),
            ("決定缺字樣", adr_decision_problems(2, synth_adr(decision="採 B")), "決定節缺字樣"),
        ):
            with self.subTest(label):
                self.assertTrue(any(want in p for p in found), found)
        # 同一組紅綠自證也涵蓋 ADR-003 的 SQL 草稿判準（G-P0-13 以它驗真檔，不得是空判準）
        good = synth_sql_doc()
        self.assertEqual(sql_draft_problems(good), [])
        fake_dsn = "postgresql" + "://u:" + "FAKEPW" + "@h/db"  # 執行期現組，原始碼不含完整字面
        for text, want in (
            (good.replace("REVOKE", "x"), "SQL 區塊缺字樣 REVOKE"),
            (good.replace("| `si.defects` | 可變且逐列 audit |\n", ""), "缺表 defects"),
            (good.replace("| `si.events` | 追加專用 |", "| `si.events` | 讀模型 |"), "events 分類"),
            (good.replace("不重算", "重算"), "row_hash"),
            (good + fake_dsn + "\n", "連線字串"),
        ):
            with self.subTest(want):
                self.assertTrue(any(want in p for p in sql_draft_problems(text)), want)


class TestArchitectureDraft(unittest.TestCase):
    """`docs/02_architecture/SelfImproving_LedgerDb_Architecture_Draft.md` 的判準函式自證（D4）。"""

    def test_AT_LD_00_D4_E_1_draft_checker_names_each_broken_variant(self):
        good = synth_draft()
        self.assertEqual(draft_problems(good), [])
        for label, text, want in (
            ("缺一塊補丁", good.replace("## 補丁 §10.3", "## 其他 §10.3"), "補丁 §10.3：標題"),
            ("缺生效階段", good.replace("生效階段：P1", "x"), "生效階段："),
            ("生效階段值錯", good.replace("生效階段：P3", "生效階段：P9"), "生效階段 P9 應為 P3"),
            ("缺 B 方案", good.replace("### B 方案", "### Z 方案"), "### B 方案"),
            ("座標被改", good.replace(":854", ":000"), "目標檔座標字樣缺 :854"),
            ("整檔空", "", "補丁 §7.2：標題"),
        ):
            with self.subTest(label):
                self.assertTrue(any(want in p for p in draft_problems(text)), want)


class TestErrataCase(unittest.TestCase):
    """`docs/06_quality/SelfImproving_LedgerDb_P0_Errata.md` 的 E-1～E-7 結構（D5）。"""

    def test_AT_LD_00_D5_1_errata_case_has_seven_complete_entries(self):
        problems = errata_problems(read_doc(ERRATA))
        self.assertEqual(problems, [], "\n".join(problems))

    def test_AT_LD_00_D5_E_1_errata_checker_names_each_broken_variant(self):
        """SCG-4 一審 F-07：`errata_problems` 此前無反例（弱化成 `return []` 全門存活）。以真實案文
        為對照組，六種變體各須被點名。"""
        good = read_doc(ERRATA)
        self.assertEqual(errata_problems(good), [])
        coord = "sid c61e3847-c8bf-4694-962f-93a657a7bf35 line 4437"
        self.assertIn(coord, good, "對照組已不含 E-4 核准座標，本測試的變體失去意義")
        for label, text, want in (
            ("少一節", good.replace("### E-3\n", "### E-30\n"), "應恰含 E-1～E-7"),
            ("欄值清空", re.sub(r"(?m)^(- 理由：).*$", r"\1", good, count=1), "欄值為空：理由"),
            ("套用階段值域", good.replace("套用階段：P", "套用階段：X"), "套用階段須以"),
            ("E-4 無座標", good.replace(coord, "sid 待填"), "E-4 缺核准座標欄"),
            ("E-6 目標", good.replace("Issue_Center_PRD.md", "Other_PRD.md"), "目標文件須為"),
            ("無不勘誤節", good.replace("## 不勘誤", "## 不勘"), "## 不勘誤 節缺"),
        ):
            with self.subTest(label):
                self.assertTrue(any(want in p for p in errata_problems(text)), want)


class TestBaselineAndFingerprint(unittest.TestCase):
    """`docs/06_quality/SelfImproving_LedgerDb_P0_Baseline.md` 與協定目錄的活值（D8）。"""

    def test_AT_LD_02_6_1_baseline_rows_equal_live_values(self):
        text = read_doc(BASELINE)
        problems: list[str] = []
        for name in ("metrics.md", "params.json", "research_sources.json"):
            label = f"協定目錄 {name}" + ("（排除於指紋）" if name.startswith("research") else "")
            raw = (ROOT / PROTOCOL_REL / name).read_bytes()
            cell = baseline_value(text, label) or ""
            digits = re.findall(r"\d[\d,]*", re.sub(r"[0-9a-f]{64}", "", cell))
            if (hashlib.sha256(raw).hexdigest() not in cell
                    or len(raw) not in {int(d.replace(",", "")) for d in digits}):
                problems.append(f"「{label}」列缺或與活值不等（{len(raw)} bytes）")
        if fingerprint_of(ROOT) not in (baseline_value(text, "指紋") or ""):
            problems.append("「指紋」列缺或與 params.fingerprint() 的活值不等")
        rev = re.match(r"\D*(\d+)", baseline_value(text, "CHECK_RULES_REV") or "")
        if rev is None or int(rev.group(1)) != CHECK_RULES_REV:
            problems.append(f"「CHECK_RULES_REV」列缺或與活值 {CHECK_RULES_REV} 不等")
        self.assertEqual(problems, [], "\n".join(problems))

    def test_AT_LD_02_6_E_1_fingerprint_tracks_protocol_bytes_except_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            shutil.copytree(ROOT / PROTOCOL_REL, tree / PROTOCOL_REL)
            base = fingerprint_of(tree)
            self.assertEqual(base, fingerprint_of(ROOT))
            for name, moves in (("params.json", True), ("metrics.md", True),
                                ("research_sources.json", False)):
                path = tree / PROTOCOL_REL / name
                raw = path.read_bytes()
                path.write_bytes(raw + b"\n")
                self.assertEqual(fingerprint_of(tree) != base, moves, name)
                path.write_bytes(raw)
                self.assertEqual(fingerprint_of(tree), base, f"{name} 還原後應相等")


class TestNamingDiscipline(unittest.TestCase):
    """`docs/02_architecture/` 與 `docs/06_quality/` 的 P0 文件不得含裸 M1～M7 編號（D10）。"""

    def test_AT_LD_00_D10_1_no_bare_m_numbers_in_p0_documents(self):
        self.assertEqual(bare_m_hits("MEAS-M1 SKIP-M6 G-SIDB-3 HM1"), [])
        self.assertEqual(len(bare_m_hits("進場須過 M2")), 1)
        hits = adr_scan(lambda _name, text: bare_m_hits(text))
        rels = [r for r in (DRAFT, ERRATA, BASELINE, PRERUN) if r != DRAFT or any(ROOT.glob(r))]
        hits += scan_docs(rels, lambda _rel, text: bare_m_hits(text))
        cells = [" | ".join(r) for r in table_rows(section_of(read_doc(RL), "## 2."))
                 if any(name in r[0] for name in CELLS)]
        hits += [f"{RL}:{h}" for h in bare_m_hits("\n".join(cells))]
        self.assertEqual(hits, [], "\n".join(hits))


class TestPreRunEvidence(unittest.TestCase):
    """`docs/06_quality/SelfImproving_LedgerDb_P0_Ratchet_PreRun.md` 的必要結構（D7 的 DT 半）。"""

    def test_AT_LD_13_7_2_prerun_evidence_has_the_required_parts(self):
        text = read_doc(PRERUN)
        heads = [ln for ln in text.split("\n") if re.match(r"#{1,6} ", ln)]
        preamble = text.split("\n## ", 1)[0]
        problems = [f"缺部分標題 {p}" for p in PRERUN_PARTS if not any(p in h for h in heads)]
        problems += [f"檔頭缺字樣 {w}" for w in ("HEAD", "唯讀") if w not in preamble]
        problems += [f"缺字樣 {w}" for w in PRERUN_WORDS if w not in text]
        blocks = re.findall(r"^```python\n(.*?)^```", text, flags=re.S | re.M)
        problems += [] if blocks else ["缺 ```python 區塊"]
        problems += [f"預演腳本含 {w}（須唯讀）" for w in ("write_text", "open(", "subprocess")
                     if any(w in b for b in blocks)]
        self.assertEqual(problems, [], "\n".join(problems))


if __name__ == "__main__":  # pragma: no cover
    import _stdio_utf8  # noqa: F401

    unittest.main()
