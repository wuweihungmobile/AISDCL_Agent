package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.DomainException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.UpstreamException;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Bridge 明確拒絕（4xx）→ Console 回應的轉譯（契約 §3.2）。為什麼重要：使用者看到的是這裡決定的狀態碼與 reason——
 * 鎖被持有要讓人知道「誰在跑」、狀態不允許要讓人知道「Bridge 眼中的狀態」、引擎端工作區被清掉不能被誤報成 Console 自己的 404；
 * 其餘 4xx 必須帶著引擎的原因逐項原樣交給前端，而不是吞成一句「失敗」。
 */
class BridgeErrorsTest {

    private static final UUID RUN = UUID.fromString("22222222-2222-2222-2222-222222222222");

    private static BridgeRejectedException rejected(int status, String reason, Map<String, Object> body) {
        return new BridgeRejectedException(status, reason, null, null, List.of(), body);
    }

    // ── 啟動（execute／審核開後續批次）────────────────────────────────────────────

    @Test
    void aHeldAdvisoryLockOnStartNamesTheRunThatHoldsIt() {
        DomainException e = BridgeErrors.forStart(rejected(409, "advisory_lock_held",
                Map.of("holder_run_id", "99999999-9999-9999-9999-999999999999")));

        assertThat(e).isInstanceOf(ConflictException.class);
        assertThat(e.reason()).isEqualTo(ErrorReasons.LOCK_HELD);
        assertThat(e.getMessage()).isEqualTo("同專案同路徑已有執行中的批次");
        assertThat(e.details()).containsOnly(Map.entry("holderRunId", "99999999-9999-9999-9999-999999999999"));
    }

    @Test
    void aHeldLockWithoutAHolderStillConflictsWithEmptyDetails() {
        DomainException e = BridgeErrors.forStart(rejected(409, "advisory_lock_held", Map.of()));

        assertThat(e).isInstanceOf(ConflictException.class);
        assertThat(e.details()).isEmpty();
    }

    @Test
    void aDuplicateRunIdIsAnUpstreamFailureBecauseConsoleAlwaysGeneratesAFreshUuid() {
        DomainException e = BridgeErrors.forStart(rejected(409, "run_exists", Map.of()));

        assertThat(e).isInstanceOf(UpstreamException.Failure.class);
        assertThat(e.reason()).isEqualTo(ErrorReasons.BRIDGE_ERROR);
        assertThat(e.details()).containsEntry("bridgeStatus", 409).containsEntry("bridgeReason", "run_exists");
    }

    @Test
    void anyOtherRejectionOnStartIsAnUnprocessableRequestCarryingTheEnginesReasonAndViolations() {
        List<Map<String, Object>> violations = List.of(Map.of("field", "tasks[0].description", "message", "含禁用字元"));
        BridgeRejectedException source = new BridgeRejectedException(422, "sanitize_failed", null, null, violations,
                Map.of());

        DomainException e = BridgeErrors.forStart(source);

        assertThat(e).isInstanceOf(UnprocessableException.class);
        assertThat(e.reason()).isEqualTo(ErrorReasons.BRIDGE_REJECTED);
        assertThat(e.getMessage()).isEqualTo("Engine Bridge 拒絕此請求（HTTP 422，sanitize_failed）");
        assertThat(e.details()).containsEntry("bridgeReason", "sanitize_failed").containsEntry("violations", violations);
        assertThat(BridgeErrors.forStart(rejected(409, "other_conflict", Map.of()))).isInstanceOf(UnprocessableException.class);
    }

    // ── 控制（pause／resume／cancel／restore／review）────────────────────────────

    @Test
    void anInvalidStateShowsBothTheConsoleAndTheBridgeViewOfTheRun() {
        DomainException e = BridgeErrors.forControl(rejected(409, "invalid_state", Map.of("status", "PAUSING")), "pause",
                RUN, "RUNNING");

        assertThat(e).isInstanceOf(ConflictException.class);
        assertThat(e.reason()).isEqualTo(ErrorReasons.RUN_STATE_NOT_ALLOWED);
        assertThat(e.getMessage()).isEqualTo("Bridge 不允許在目前狀態執行 pause");
        assertThat(e.details()).containsEntry("action", "pause").containsEntry("runStatus", "RUNNING")
                .containsEntry("bridgeStatus", "PAUSING");
    }

    @Test
    void anInvalidStateWithoutAStatusInTheBodyOmitsTheBridgeStatusKey() {
        DomainException e = BridgeErrors.forControl(rejected(409, "invalid_state", Map.of()), "resume", RUN, "PAUSED");

        assertThat(e.details()).containsOnlyKeys("action", "runStatus");
    }

    @Test
    void noCheckpointToResumeFromIsADedicatedConflict() {
        DomainException e = BridgeErrors.forControl(rejected(409, "no_checkpoint", Map.of()), "restore", RUN, "PAUSED");

        assertThat(e).isInstanceOf(ConflictException.class);
        assertThat(e.reason()).isEqualTo(ErrorReasons.NO_CHECKPOINT);
        assertThat(e.getMessage()).isEqualTo("找不到可續跑的 checkpoint");
    }

    @Test
    void aLockHeldWhileResumingNamesTheHolderToo() {
        DomainException e = BridgeErrors.forControl(rejected(409, "advisory_lock_held", Map.of("holder_run_id", "abc")),
                "resume", RUN, "PAUSED");

        assertThat(e.reason()).isEqualTo(ErrorReasons.LOCK_HELD);
        assertThat(e.details()).containsEntry("holderRunId", "abc");
    }

    @Test
    void aRunTheEngineNoLongerKnowsIsAConflictNotAConsoleNotFound() {
        DomainException e = BridgeErrors.forControl(rejected(404, "run_not_found", Map.of()), "cancel", RUN, "RUNNING");

        assertThat(e).as("Console 的 DB 認得這個批次，只是引擎端的工作區被清了").isInstanceOf(ConflictException.class);
        assertThat(e.reason()).isEqualTo(ErrorReasons.RUN_UNKNOWN_AT_BRIDGE);
        assertThat(e.details()).containsEntry("runId", RUN.toString());
    }

    @Test
    void aMissingCheckpointIsANotFoundThatNamesIt() {
        DomainException named = BridgeErrors.forControl(rejected(404, "checkpoint_not_found",
                Map.of("checkpoint_id", "cp-7")), "restore", RUN, "PAUSED");
        DomainException anonymous = BridgeErrors.forControl(rejected(404, "checkpoint_not_found", Map.of()), "restore",
                RUN, "PAUSED");

        assertThat(named).isInstanceOf(NotFoundException.class);
        assertThat(named.getMessage()).isEqualTo("checkpoint 不存在或不屬於此執行：cp-7");
        assertThat(anonymous.getMessage()).isEqualTo("checkpoint 不存在或不屬於此執行：");
    }

    @Test
    void everythingElseOnAControlCallIsAnUnprocessableRequest() {
        DomainException e = BridgeErrors.forControl(rejected(400, "bad_request", Map.of()), "restore", RUN, "PAUSED");

        assertThat(e).isInstanceOf(UnprocessableException.class);
        assertThat(e.details()).containsEntry("bridgeReason", "bad_request");
        assertThat(BridgeErrors.forControl(rejected(404, "something_else", Map.of()), "pause", RUN, "RUNNING"))
                .as("404 但不是 run_not_found／checkpoint_not_found").isInstanceOf(UnprocessableException.class);
    }
}
