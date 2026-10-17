"""部署設定的回歸鎖（W5-INFRA：DEF-AC-003／006／008／010、O-08／O-09／O-20；W7-INFRA：D-14）。

為什麼放在 Bridge 的測試目錄：這些缺陷的共同特徵是「本機、mock、單元測試全綠，
只有 Docker 全棧真跑才現形」，而 docker／compose／nginx 設定沒有自己的 pytest 家。
這裡只做**靜態**檢查（讀檔、不起 Docker），把每個缺陷的修法釘成一條斷言——有人把設定改回去，
會在最便宜的地方先紅，而不是等下一輪全棧驗證。真正的行為驗證（容器起得來、502 後重連、
還原演練…）仍是 docker compose 的實跑，見 docker/README.md。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

CONSOLE_DIR = Path(__file__).resolve().parents[2]            # <monorepo>/AgentConsole
COMPOSE = CONSOLE_DIR / "docker-compose.yml"
NGINX_DIR = CONSOLE_DIR / "docker" / "nginx"
PROMETHEUS_DIR = CONSOLE_DIR / "docker" / "prometheus"
APP_DASHBOARD = CONSOLE_DIR / "docker" / "grafana" / "dashboards" / "app-overview.json"
DOCKERFILE = CONSOLE_DIR / "engine-bridge" / "Dockerfile"
RESTORE_SH = CONSOLE_DIR / "docker" / "pgbackrest" / "scripts" / "restore.sh"

pytestmark = pytest.mark.skipif(
    not COMPOSE.is_file(), reason="不在 monorepo 內（例如只有 engine-bridge 目錄的 checkout）")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _service_block(compose: str, name: str) -> str:
    """`  <name>:` 到下一個同層服務（兩格縮排的 `  xxx:`）之前。"""
    match = re.search(
        rf"^  {re.escape(name)}:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|^[a-z#]|\Z)",
        compose, flags=re.S | re.M)
    assert match, f"docker-compose.yml 找不到服務 {name}"
    return match.group(1)


# ── DEF-AC-003（P1）：Bridge 映像缺 git，/health 卻永遠 200 ──────────────────────
def test_the_bridge_image_installs_git_and_smoke_tests_it_at_build_time() -> None:
    text = _read(DOCKERFILE)
    install = re.search(r"apt-get install[^\n]*(?:\\\n[^\n]*)*", text)
    assert install, "Dockerfile 沒有 apt-get install"
    assert "--no-install-recommends" in install.group(0)
    assert "git" in install.group(0).split() and "ca-certificates" in install.group(0)
    smoke = re.search(r"^RUN git --version$", text, flags=re.M)
    assert smoke, "build 期冒煙：git 裝不上就要讓 build 失敗"


def test_both_healthchecks_probe_the_deep_endpoint() -> None:
    # 只認「真的會執行的那一行」，不認註解裡提到的字
    image_cmd = re.search(r"^\s+CMD \[.*\]$", _read(DOCKERFILE).split("HEALTHCHECK", 1)[1],
                          flags=re.M)
    assert image_cmd and "127.0.0.1:%s/health/deep" in image_cmd.group(0)
    compose_test = re.search(r"^\s+test: \[\"CMD\", \"python\".*\]$",
                             _service_block(_read(COMPOSE), "engine-bridge"), flags=re.M)
    assert compose_test and "127.0.0.1:8081/health/deep" in compose_test.group(0)


# ── DEF-AC-006：CONSOLE_ENCRYPTION_KEY 預設空、compose 層不擋 ─────────────────────
def test_the_encryption_key_is_required_by_compose_itself() -> None:
    lines = _service_block(_read(COMPOSE), "backend").splitlines()
    line = next(ln for ln in lines if ln.strip().startswith("CONSOLE_ENCRYPTION_KEY:"))
    assert "${CONSOLE_ENCRYPTION_KEY:?" in line, "必須是 :? 形式（未設或留空就在 config 階段失敗）"
    assert ":-" not in line, "不得有預設值"


# ── ADR-XPLAT-016 §9（G-09）：SDD 寫入面權杖的部署接線 ─────────────────────────────────────────
def test_only_backend_and_engine_bridge_receive_the_sdd_write_token_with_an_empty_default() -> None:
    """持有者只有 backend（發送）與 Bridge（驗證）：前端、資料庫層與其他服務都不該拿到它；預設空＝
    停用（SDD 是選用引擎，不像 JWT_SECRET 設成 `:?` 必填）。"""
    compose = _read(COMPOSE)
    for service in ("backend", "engine-bridge"):
        lines = [ln.strip() for ln in _service_block(compose, service).splitlines()]
        assert "BRIDGE_SDD_WRITE_TOKEN: ${BRIDGE_SDD_WRITE_TOKEN:-}" in lines, service
    services = yaml.safe_load(compose)["services"]
    holders = sorted(name for name, body in services.items()
                     if "BRIDGE_SDD_WRITE_TOKEN" in (body.get("environment") or {}))
    assert holders == ["backend", "engine-bridge"]
    assert "BRIDGE_SDD_WRITE_TOKEN:?" not in compose, "必填會讓不用 SDD 的部署起不來"


def test_the_env_example_holds_only_the_placeholder_and_the_bridge_refuses_it_verbatim() -> None:
    from app.settings import SettingsError, load_settings

    text = _read(CONSOLE_DIR / ".env.example")
    entries = re.findall(r"^\s*#?\s*BRIDGE_SDD_WRITE_TOKEN=(.*)$", text, flags=re.M)
    assert entries == ["<YOUR_BRIDGE_SDD_WRITE_TOKEN_MIN_32_CHARS>"], \
        "範例檔只准放佔位，不放任何真值"
    with pytest.raises(SettingsError):          # 原樣取消註解照抄＝啟動即失敗，不靜默退回停用
        load_settings({"BRIDGE_SDD_WRITE_TOKEN": entries[0]})


# ── C-16：檔案日誌與共用卷的權限 ─────────────────────────────────────────────────
def test_file_logging_is_wired_to_the_shared_volume_without_order_dependence() -> None:
    compose = _read(COMPOSE)
    bridge = _service_block(compose, "engine-bridge")
    assert re.search(r"^\s+BRIDGE_LOG_DIR: /app/logs$", bridge, flags=re.M)
    backend = _service_block(compose, "backend")
    assert re.search(r"^\s+LOG_DIR: /app/logs$", backend, flags=re.M)
    # 具名卷還空著時，Docker 在每個容器 create 時都把映像內該目錄的權限複製進卷根；
    # 最後 create 的 backend 會把 Bridge 映像的 1777 蓋成 spring:spring 0755
    # （W5 全棧實測 Bridge 因而 Permission denied）。backend 掛載加 nocopy 才與順序無關。
    assert "- app_logs:/app/logs:nocopy" in backend
    assert "chmod 1777 /app/logs" in _read(DOCKERFILE)


# ── O-20：未認證限流可被 X-Forwarded-For 繞過 ────────────────────────────────────
def test_the_default_trusted_proxies_are_the_pinned_subnet_minus_the_gateway() -> None:
    compose = _read(COMPOSE)
    subnet = re.search(r"subnet: \$\{BACKEND_NET_SUBNET:-([0-9./]+)\}", compose)
    proxies = re.search(
        r"CONSOLE_INTERNAL_PROXIES: \$\{CONSOLE_INTERNAL_PROXIES:-([^}]+)\}", compose)
    assert subnet and proxies, "backend-net 要有固定子網，且 backend 要有 CONSOLE_INTERNAL_PROXIES"
    assert subnet.group(1).endswith(".0/24"), "這支測試對預設值寫法的假設是 /24 子網"
    prefix = subnet.group(1).rsplit(".", 1)[0]
    regex = re.compile(proxies.group(1))          # Java 正規表示式；這裡只用兩邊共通的語法
    matched = [n for n in range(0, 256) if regex.fullmatch(f"{prefix}.{n}")]
    # .0／.255 不是主機位址；.1＝Docker 閘道＝主機端進來的請求位址，信它就等於信任偽造
    assert matched == list(range(2, 255))
    for outside in ("10.0.0.5", "192.168.1.50", "172.31.251.2", "127.0.0.1"):
        assert not regex.fullmatch(outside), f"子網以外的私網位址不可信：{outside}"


# ── DEF-AC-008／O-08／O-09：nginx ───────────────────────────────────────────────
def test_nginx_error_log_is_crit_so_the_access_token_never_reaches_it() -> None:
    conf = _read(NGINX_DIR / "nginx.conf")
    levels = re.findall(r"^error_log\s+\S+\s+(\w+);", conf, flags=re.M)
    assert levels == ["crit"], f"error_log 必須只有一行且為 crit，實際 {levels}"


def test_nginx_routes_frontend_health_before_api_and_keeps_one_cache_control() -> None:
    locations = _read(NGINX_DIR / "conf.d" / "console-locations.inc")
    health = locations.index("location = /api/health {")
    api = locations.index("location /api/ {")
    assert health < api, "/api/health 要在 /api/ 之前（O-08：否則被反代到 backend 回 401）"
    health_block = locations[health:locations.index("}", health)]
    assert "proxy_pass http://frontend;" in health_block
    static = locations[locations.index("location /_next/static/ {"):]
    directives = [ln.strip() for ln in static.splitlines() if not ln.strip().startswith("#")]
    assert sum(ln.startswith("add_header Cache-Control") for ln in directives) == 1
    # 上游（Next）自己也會送一份：丟掉它才只剩一份（O-09）
    assert "proxy_hide_header Cache-Control;" in directives


def test_http_and_https_servers_share_one_set_of_locations() -> None:
    include = "include /etc/nginx/conf.d/console-locations.inc;"
    default = _read(NGINX_DIR / "conf.d" / "default.conf")
    https = _read(NGINX_DIR / "conf.d" / "https.conf.example")
    assert include in default
    assert include in https, "兩份路由漂移＝HTTPS 行為與 HTTP 不同"
    assert "listen 443 ssl;" in https and "/etc/nginx/certs/fullchain.pem" in https
    redirect = _read(NGINX_DIR / "conf.d" / "https-redirect.inc")
    # compose 的 nginx healthcheck 打 80 埠的 /nginx-health，不能被轉址
    assert "location = /nginx-health" in redirect
    assert "return 301 https://$host$request_uri;" in redirect


# ── DEF-AC-010：restore.sh 對不存在的資料目錄失敗 ────────────────────────────────
def test_restore_creates_the_data_directory_as_root_before_dropping_privileges() -> None:
    text = _read(RESTORE_SH)
    root_phase = text[text.index('if [ "$(id -u)" = "0" ]; then'):text.index("exec gosu postgres")]
    commands = [ln.strip() for ln in root_phase.splitlines() if not ln.strip().startswith("#")]
    for needle in ('mkdir -p "$PGDATA_DIR"', 'chown postgres:postgres "$PGDATA_DIR"',
                   'chmod 0700 "$PGDATA_DIR"'):
        # 卷根屬 root:root：postgres 沒有權限建立 pgdata，所以一定要在 gosu 之前
        assert needle in commands, f"root 階段（gosu 之前）缺 {needle}"
    assert "\r" not in text, ".sh 含 CR 會在容器內炸 $'\\r'"


# ── W7 D-14（NFR-9.3-01）：可用性 SLO 的量測機制 ─────────────────────────────────────
# 規則「算對、會響」由 promtool 單元測試負責（docker/prometheus/tests/slo_test.yml，要 Docker）；
# 這裡只釘「規則真的被載入」與「數字與 PRD 對得上」——這兩件事靜默失效時，promtool 測試照樣全綠：
# Prometheus 對 rule_files 裡找不到的檔案不報錯（glob 沒有符合就當沒有），
# 少一行掛載＝規則整組消失而沒人知道。
def _slo_rules() -> dict[str, dict]:
    """slo.yml 的全部 recording／alert 規則，以名稱為鍵。"""
    doc = yaml.safe_load(_read(PROMETHEUS_DIR / "slo.yml"))
    rules: dict[str, dict] = {}
    for group in doc["groups"]:
        for rule in group["rules"]:
            rules[rule.get("record") or rule["alert"]] = rule
    return rules


def test_the_slo_rules_are_loaded_by_prometheus_and_mounted_into_its_container() -> None:
    config = yaml.safe_load(_read(PROMETHEUS_DIR / "prometheus.yml"))
    assert "/etc/prometheus/slo.yml" in config["rule_files"]
    prometheus = _service_block(_read(COMPOSE), "prometheus")
    assert "- ./docker/prometheus/slo.yml:/etc/prometheus/slo.yml:ro" in prometheus, \
        "沒掛進容器＝rule_files 找不到檔，Prometheus 不報錯、SLO 規則整組消失"


def test_the_availability_ratios_average_the_up_signal_of_a_job_prometheus_really_scrapes() -> None:
    config = yaml.safe_load(_read(PROMETHEUS_DIR / "prometheus.yml"))
    assert "spring-boot" in {job["job_name"] for job in config["scrape_configs"]}, \
        "SLO 訊號 up{job=\"spring-boot\"} 的 job 改名了：可用率會變成永遠沒有資料"
    rules = _slo_rules()
    for window in ("1d", "7d", "30d"):
        rule = rules[f"aisdlc:console_availability:ratio_{window}"]
        assert rule["expr"] == f'avg_over_time(up{{job="spring-boot"}}[{window}])'


def test_the_slo_alerts_pin_the_prd_target_and_the_one_minute_down_detection() -> None:
    rules = _slo_rules()
    down, below = rules["ConsoleDown"], rules["ConsoleAvailabilityBelowTarget"]
    assert down["expr"] == 'up{job="spring-boot"} == 0' and down["for"] == "1m"
    # PRD §9.3「可用性 目標 99.5% Uptime」：0.995 是 PRD 的數字，不是調參
    assert below["expr"] == "aisdlc:console_availability:ratio_30d < 0.995"
    assert below["for"] == "15m"
    assert down["labels"]["severity"] == below["labels"]["severity"] == "critical"


def test_prometheus_keeps_at_least_the_30_days_of_raw_samples_the_30d_ratio_needs() -> None:
    prometheus = _service_block(_read(COMPOSE), "prometheus")
    match = re.search(r"--storage\.tsdb\.retention\.time=(\d+)d\b", prometheus)
    assert match, "retention.time 要以「天」為單位明確設定"
    assert int(match.group(1)) >= 30, \
        "保留期短於 30 天時 ratio_30d 只涵蓋保留期那麼久，卻被標成 30 天（原本的 15d 就是這樣）"


def test_prometheus_history_lives_in_a_named_volume_that_survives_down() -> None:
    # 保留期夠長還不夠：資料目錄若在映像宣告的匿名卷，`down` 後重起會接到新的匿名卷，30 天歷史歸零
    compose = yaml.safe_load(_read(COMPOSE))
    service = compose["services"]["prometheus"]
    assert "prometheus_data:/prometheus" in service["volumes"], \
        "沒掛具名卷：容器重建後 30 天可用率從零累積"
    assert "--storage.tsdb.path=/prometheus" in service["command"], \
        "TSDB 路徑與掛載點不同：卷掛了，Prometheus 卻寫在別處"
    assert "prometheus_data" in compose["volumes"], \
        "頂層 volumes 沒宣告：`docker compose config` 會報 undefined volume"


def test_the_promtool_unit_tests_load_slo_yml_and_mention_every_rule() -> None:
    text = _read(PROMETHEUS_DIR / "tests" / "slo_test.yml")
    assert yaml.safe_load(text)["rule_files"] == ["../slo.yml"]
    for name in _slo_rules():
        assert name in text, f"promtool 單元測試沒有涵蓋規則 {name}"


def test_the_app_overview_dashboard_shows_the_slo_against_the_prd_threshold() -> None:
    panels = json.loads(_read(APP_DASHBOARD))["panels"]
    ids = [p["id"] for p in panels]
    assert len(ids) == len(set(ids)), "面板 id 重複：Grafana 會互相覆蓋"
    # 面板引用的每一條 SLO recording rule 都必須是 slo.yml 真有的（改名後面板會靜默變成 No data）
    rules = _slo_rules()
    for panel in panels:
        for target in panel.get("targets", []):
            if target["expr"].startswith("aisdlc:console_availability:"):
                assert target["expr"] in rules, f"面板 {panel['title']} 引用了不存在的規則"

    def panels_with(kind: str, expr: str) -> list[dict]:
        return [p for p in panels
                if p["type"] == kind and any(t["expr"] == expr for t in p["targets"])]

    stat = panels_with("stat", "aisdlc:console_availability:ratio_30d")
    assert len(stat) == 1, "要有一個 30 天可用率的 stat 面板"
    steps = stat[0]["fieldConfig"]["defaults"]["thresholds"]["steps"]
    assert [(s["color"], s["value"]) for s in steps] == [("red", None), ("green", 0.995)]
    assert len(panels_with("timeseries", "aisdlc:console_availability:ratio_1d")) == 1
    # 版面：24 欄格線內、互不重疊（手動改 y 座標時最容易出錯）
    boxes = [(p["gridPos"]["x"], p["gridPos"]["y"], p["gridPos"]["w"], p["gridPos"]["h"])
             for p in panels]
    assert all(x + w <= 24 for x, _y, w, _h in boxes)
    for i, (ax, ay, aw, ah) in enumerate(boxes):
        for bx, by, bw, bh in boxes[i + 1:]:
            assert not (ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah), \
                f"面板格位重疊：{(ax, ay, aw, ah)} 與 {(bx, by, bw, bh)}"
