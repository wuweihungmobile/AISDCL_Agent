package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.minibridge.MiniBridge;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@code GET /api/v1/engines/sdd}（API-ENG-01；契約 §1.7.1；D-16；E2E-15 的後端面），對<b>真的 HTTP</b> 迷你 Bridge 驗映射表的每一列。
 * 為什麼重要：這支端點是 Console 對 FSM 狀態的唯一消費點（NFR-OBS-01：FSM 檔 ↔ API ↔ 畫面逐值相等），而且引擎不可用也要回 200——
 * 前端靠 {@code available}／{@code reason} 畫「不可用」，若這裡把 Bridge 的錯誤轉成 502，監控頁的 SDD 卡就會變成錯誤頁。
 * 只能 E2E 的部分（磁碟上真實的 FSM 檔、畫面 DOM、乾淨 clone 與 Docker 全棧）見 {@code rtm_backfill_W7BE.md}。
 */
class EnginesApiIT extends AbstractExecutionIT {

    private static final String SDD = "/api/v1/engines/sdd";

    private Resp get(String query) {
        return api.get(viewer(), SDD + query);
    }

    private long sddRequests() {
        return MINI.requests().stream().filter(r -> r.startsWith("GET /sdd")).count();
    }

    // ── 可用：清單（E2E-15 第 1 列）、單一專案（第 2、3 列）──────────────────────────────────────

    @Test
    void withoutAProjectItListsTheProjectsInTheBridgeOrderAndHasNoFsm() {
        Resp resp = get("");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.available")).isTrue();
        assertThat(resp.<Object>read("$.data.reason")).as("沒問題時 reason 為 null（鍵固定出現）").isNull();
        assertThat(resp.<String>read("$.data.version.latest")).isEqualTo("AISDLC_SDD_v9.99");
        assertThat(resp.<String>read("$.data.version.root")).isEqualTo("/sdd/AISDLC_SDD_v9.99");
        assertThat(resp.<List<String>>read("$.data.projects[*].project")).containsExactly("e2e-alpha", "e2e-bravo");
        assertThat(resp.<List<String>>read("$.data.projects[*].source"))
                .containsExactly("FSM-STATE-e2e-alpha.yaml", "FSM-STATE-e2e-bravo.yaml");
        assertThat(resp.<List<String>>read("$.data.projects[*].currentState"))
                .containsExactly("IMPLEMENTATION", "HUMAN_PENDING");
        assertThat(resp.<List<String>>read("$.data.projects[*].updatedAt"))
                .containsExactly("2026-10-16T01:02:03+00:00", "2026-10-15T08:00:00+00:00");
        assertThat(resp.<Object>read("$.data.fsm")).as("未帶 project：fsm=null 且不帶 reason").isNull();
        assertThat(resp.<String>read("$.data.checkedAt")).endsWith("Z");
        assertThat(resp.body()).as("Bridge 的 errors[]（讀不動的檔名）只記日誌，不轉發")
                .doesNotContain("e2e-broken").doesNotContain("bad name");
        assertThat(MINI.requests()).containsExactly("GET /sdd/version", "GET /sdd/fsm");
    }

    @Test
    void aProjectNameReturnsItsStateWithNestedContentVerbatim() {
        Map<String, Object> expected = MINI.sdd.states.get("e2e-alpha");

        Resp resp = get("?project=e2e-alpha");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.available")).isTrue();
        assertThat(resp.<Object>read("$.data.reason")).isNull();
        assertThat(resp.<String>read("$.data.fsm.project")).isEqualTo("e2e-alpha");
        assertThat(resp.<String>read("$.data.fsm.currentState")).isEqualTo("IMPLEMENTATION");
        assertThat(resp.<Integer>read("$.data.fsm.currentSprint")).isEqualTo(2);
        assertThat(resp.<String>read("$.data.fsm.sessionId")).isEqualTo("sid-alpha");
        assertThat(resp.<String>read("$.data.fsm.updatedAt")).as("原樣的字串，不轉型").isEqualTo("2026-10-16T01:02:03+00:00");
        assertThat(resp.<String>read("$.data.fsm.source")).isEqualTo("FSM-STATE-e2e-alpha.yaml");
        assertThat(resp.<List<Object>>read("$.data.fsm.frozenStages")).isEqualTo(expected.get("frozen_stages"));
        assertThat(resp.<List<Object>>read("$.data.fsm.decisionTrace")).as("尾 5 筆、舊→新、巢狀鍵保留 snake_case，逐值相等")
                .isEqualTo(expected.get("decision_trace")).hasSize(5);
        assertThat(resp.<Object>read("$.data.fsm.decisionTrace[0].spec_refs")).isEqualTo(List.of("SPEC-3"));
        assertThat(resp.<Object>read("$.data.fsm.decisionTrace[4].agents_consulted")).isEqualTo(List.of("sa"));
        assertThat(resp.<Integer>read("$.data.fsm.humanPending.count")).isZero();
        assertThat(resp.<List<Object>>read("$.data.fsm.humanPending.items")).isEmpty();
        assertThat(resp.<Integer>read("$.data.fsm.retryHistory.count")).isEqualTo(3);
        assertThat(resp.<Map<String, Object>>read("$.data.fsm.retryHistory.last")).as("原筆再加 gate 欄")
                .containsEntry("gate", "PR_REVIEW").containsEntry("attempt", 1)
                .containsEntry("failure_reason", "review rejected");
        assertThat(resp.<Object>read("$.data.fsm.rtmCoverage")).as("現行 FSM-STATE 沒有 RTM 覆蓋數值：恆為 null").isNull();
        assertThat(resp.<List<String>>read("$.data.projects[*].project")).containsExactly("e2e-alpha", "e2e-bravo");
        assertThat(MINI.requests()).containsExactly("GET /sdd/version", "GET /sdd/fsm", "GET /sdd/fsm/e2e-alpha");
    }

    @Test
    void aProjectWaitingForAHumanShowsTheEnteredAtVerbatim() {
        Resp resp = get("?project=e2e-bravo");

        assertThat(resp.<String>read("$.data.fsm.currentState")).isEqualTo("HUMAN_PENDING");
        assertThat(resp.<Integer>read("$.data.fsm.humanPending.count")).isEqualTo(1);
        assertThat(resp.<String>read("$.data.fsm.humanPending.items[0].entered_at"))
                .isEqualTo("2026-10-15T08:00:00+00:00");
        assertThat(resp.<Integer>read("$.data.fsm.humanPending.items[0].reminder_hours")).isEqualTo(72);
        assertThat(resp.<Integer>read("$.data.fsm.retryHistory.count")).isZero();
        assertThat(resp.<Object>read("$.data.fsm.retryHistory.last")).isNull();
    }

    @Test
    void anEmptyFsmDirectoryIsAnAvailableEngineWithNoProjectsAndNoReason() {
        MINI.sdd.projects.clear();
        MINI.sdd.states.clear();
        MINI.sdd.errors.clear();

        Resp resp = get("");

        assertThat(resp.<Boolean>read("$.data.available")).as("乾淨 clone 沒有 FSM 狀態檔：available=true、projects=[]").isTrue();
        assertThat(resp.<Object>read("$.data.reason")).isNull();
        assertThat(resp.<List<Object>>read("$.data.projects")).isEmpty();
        assertThat(resp.<Object>read("$.data.fsm")).isNull();
    }

    // ── 專案層級的問題：引擎仍可用（E2E-15 第 4 列）──────────────────────────────────────────

    @Test
    void anUnknownProjectKeepsTheEngineAvailableWithNotFoundAndTheListIntact() {
        Resp resp = get("?project=nope");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.available")).isTrue();
        assertThat(resp.<String>read("$.data.reason")).isEqualTo("fsm_not_found");
        assertThat(resp.<Object>read("$.data.fsm")).isNull();
        assertThat(resp.<String>read("$.data.version.latest")).isEqualTo("AISDLC_SDD_v9.99");
        assertThat(resp.<List<String>>read("$.data.projects[*].project")).containsExactly("e2e-alpha", "e2e-bravo");
    }

    @Test
    void anUnreadableFsmFileKeepsTheEngineAvailableWithTheUnreadableReason() {
        MINI.sdd.unreadable.add("e2e-broken");

        Resp resp = get("?project=e2e-broken");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.available")).isTrue();
        assertThat(resp.<String>read("$.data.reason")).isEqualTo("fsm_state_unreadable");
        assertThat(resp.<Object>read("$.data.fsm")).isNull();
        assertThat(resp.<List<String>>read("$.data.projects[*].project")).hasSize(2);
        assertThat(resp.body()).as("Bridge 的 detail 不外露").doesNotContain("while scanning");
    }

    // ── project 驗證：不合白名單 400（第 4 列③④）─────────────────────────────────────────────

    @Test
    void namesOutsideTheWhitelistAre400AndNeverReachTheBridge() {
        for (String query : List.of("?project=a%20b", "?project=..%2Fx", "?project=", "?project=a%2Fb",
                "?project=" + "x".repeat(129), "?project=%E5%90%8D%E7%A8%B1")) {
            Resp resp = get(query);

            assertThat(resp.status()).as(query).isEqualTo(400);
            assertThat(resp.errorFields()).as(query).containsExactly("project");
        }
        assertThat(sddRequests()).as("驗證在任何 Bridge 呼叫之前").isZero();
    }

    // ── 引擎層級的不可用：200＋available=false（第 7、8 列）──────────────────────────────────

    @Test
    void anUnreachableBridgeIs200BridgeUnreachableWithNothingElse() {
        setting("sdd", "engineUrl", "http://127.0.0.1:1");

        Resp resp = get("?project=e2e-alpha");

        assertThat(resp.status()).as("不是 502").isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.available")).isFalse();
        assertThat(resp.<String>read("$.data.reason")).isEqualTo("bridge_unreachable");
        assertThat(resp.<Object>read("$.data.version")).isNull();
        assertThat(resp.<List<Object>>read("$.data.projects")).isEmpty();
        assertThat(resp.<Object>read("$.data.fsm")).isNull();
        assertThat(resp.<String>read("$.data.checkedAt")).endsWith("Z");
    }

    @Test
    void aBridgeThatAnswersTooSlowlyIsAlsoBridgeUnreachable() {
        MINI.sdd.delayMillis = 3_600;

        long started = System.nanoTime();
        Resp resp = get("");
        long elapsedMillis = (System.nanoTime() - started) / 1_000_000;

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.available")).isFalse();
        assertThat(resp.<String>read("$.data.reason")).isEqualTo("bridge_unreachable");
        assertThat(elapsedMillis).as("讀取逾時 3 秒、不重試（重試會讓這裡超過 9 秒）").isBetween(2_500L, 8_000L);
        assertThat(MINI.countRequests("GET /sdd/version")).as("只打一次，失敗即短路").isEqualTo(1);
    }

    @Test
    void anInvalidSddRootIs200SddUnavailableAndTheLaterCallsAreNeverMade() {
        MINI.sdd.unavailable = true;

        Resp resp = get("?project=e2e-alpha");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.available")).isFalse();
        assertThat(resp.<String>read("$.data.reason")).isEqualTo("sdd_unavailable");
        assertThat(resp.<Object>read("$.data.version")).isNull();
        assertThat(resp.<List<Object>>read("$.data.projects")).isEmpty();
        assertThat(MINI.requests()).as("第一個呼叫就失敗：後面的不再發").containsExactly("GET /sdd/version");
    }

    @Test
    void aServerErrorOrAWrongShapeIsBridgeErrorAndKeepsTheVersion() {
        MINI.failNext("sddVersion", 500, Map.of("code", 500, "reason", "boom"));
        Resp first = get("");
        assertThat(first.status()).isEqualTo(200);
        assertThat(first.<Boolean>read("$.data.available")).isFalse();
        assertThat(first.<String>read("$.data.reason")).isEqualTo("bridge_error");
        assertThat(first.<Object>read("$.data.version")).isNull();

        MINI.failNext("sddFsmList", 200, Map.of("unexpected", true));
        Resp second = get("");
        assertThat(second.<Boolean>read("$.data.available")).isFalse();
        assertThat(second.<String>read("$.data.reason")).as("2xx 但形狀不對").isEqualTo("bridge_error");
        assertThat(second.<String>read("$.data.version.latest")).as("第二個呼叫失敗：保留版本").isEqualTo("AISDLC_SDD_v9.99");
        assertThat(second.<List<Object>>read("$.data.projects")).isEmpty();
    }

    @Test
    void aThirdCallFailureMakesTheEngineUnavailableButKeepsTheList() {
        MINI.failNext("sddFsm", 500, Map.of("code", 500, "reason", "boom"));

        Resp resp = get("?project=e2e-alpha");

        assertThat(resp.<Boolean>read("$.data.available")).isFalse();
        assertThat(resp.<String>read("$.data.reason")).isEqualTo("bridge_error");
        assertThat(resp.<Object>read("$.data.fsm")).isNull();
        assertThat(resp.<String>read("$.data.version.latest")).isEqualTo("AISDLC_SDD_v9.99");
        assertThat(resp.<List<String>>read("$.data.projects[*].project")).containsExactly("e2e-alpha", "e2e-bravo");
    }

    // ── 不快取、唯讀、標頭與權限 ────────────────────────────────────────────────────────────

    @Test
    void everyRequestHitsTheBridgeAndCarriesTheTraceIdOfItsOwnRequest() {
        Resp first = get("");
        Resp second = get("");

        assertThat(MINI.countRequests("GET /sdd/version")).as("這支端點不快取").isEqualTo(2);
        assertThat(first.header("X-Trace-Id")).isNotBlank().isNotEqualTo(second.header("X-Trace-Id"));
        assertThat(MINI.traced().stream().filter(t -> t.request().startsWith("GET /sdd")).toList())
                .extracting(MiniBridge.Traced::traceId)
                .containsExactly(first.header("X-Trace-Id"), first.header("X-Trace-Id"), second.header("X-Trace-Id"),
                        second.header("X-Trace-Id"));
    }

    @Test
    void onlyAnAuthenticatedUserMayReadAndEveryRoleMay() {
        assertThat(api.get(null, SDD).status()).isEqualTo(401);
        for (String token : List.of(viewer(), operator(), admin())) {
            assertThat(api.get(token, SDD).status()).isEqualTo(200);
        }
        assertThat(api.post(operator(), SDD, Map.of()).status()).as("沒有任何寫入方法：只讀端點").isEqualTo(405);
    }
}
