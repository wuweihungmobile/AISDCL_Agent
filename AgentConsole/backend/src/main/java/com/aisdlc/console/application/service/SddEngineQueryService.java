package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.SddEngineUseCase;
import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.model.engine.SddEngineReason;
import com.aisdlc.console.domain.model.engine.SddEngineStatus;
import com.aisdlc.console.domain.model.engine.SddFsmList;
import com.aisdlc.console.domain.model.engine.SddFsmState;
import com.aisdlc.console.domain.model.engine.SddVersion;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.regex.Pattern;

/**
 * AISDLC_SDD 引擎狀態（API-ENG-01；契約 §1.7.1、§3.1.3；D-16）。
 *
 * <p>三個 Bridge 呼叫依序進行、<b>失敗即短路</b>（後面的不再發），每個連線 2 秒／讀取 3 秒、不重試（在 {@link AgentBridge} 實作）。
 * 這支查詢回報的是「引擎現在的狀態」，不是「這次呼叫成不成功」，所以 Bridge 不可達、503、非預期回應都轉成
 * {@code available=false}＋{@code reason}（沿用「Bridge 不可達回 200」的慣例），不丟例外；只有 {@code project} 不合白名單是 400。
 * 不快取：每次請求都打 Bridge（前端 30 秒輪詢一次）。console-api 唯讀：不寫 SDD 目錄、不寫任何 FSM-STATE 檔（ADR-001 D22）。
 */
@Service
public class SddEngineQueryService implements SddEngineUseCase {

    /** 與 Bridge 同一條 FSM 專案名白名單（契約 §1.7.1、§3.1.3）。 */
    static final Pattern PROJECT_NAME = Pattern.compile("^[A-Za-z0-9._-]{1,128}$");
    private static final int LOGGED_NAMES = 20;
    private static final Logger LOG = LoggerFactory.getLogger(SddEngineQueryService.class);

    private final AgentBridge bridge;
    private final Clock clock;

    public SddEngineQueryService(AgentBridge bridge, Clock clock) {
        this.bridge = bridge;
        this.clock = clock;
    }

    @Override
    public SddEngineStatus status(String project) {
        if (project != null && !PROJECT_NAME.matcher(project).matches()) {
            throw ValidationException.of("project", "project 須符合 ^[A-Za-z0-9._-]{1,128}$（FSM 專案名）");
        }
        Instant checkedAt = clock.instant();

        SddVersion version;
        try {
            version = bridge.sddVersion();
        } catch (UpstreamException | BridgeRejectedException e) {
            return unavailable(reasonOf(e, false), null, checkedAt, e);
        }

        SddFsmList list;
        try {
            list = bridge.sddFsmList();
        } catch (UpstreamException | BridgeRejectedException e) {
            return unavailable(reasonOf(e, false), version, checkedAt, e);
        }
        logUnreadableFiles(list);

        if (project == null) {
            return new SddEngineStatus(true, null, version, list.projects(), null, checkedAt);
        }
        try {
            SddFsmState fsm = bridge.sddFsm(project);
            return new SddEngineStatus(true, null, version, list.projects(), fsm, checkedAt);
        } catch (UpstreamException | BridgeRejectedException e) {
            SddEngineReason reason = reasonOf(e, true);
            LOG.info("AISDLC_SDD 單一專案 FSM 取不到（project={}，原因 {}）：{}", project, reason.wire(), e.getMessage());
            // 第三個呼叫的 404／422 是「專案層級」的問題：引擎本身可用（available=true），清單與版本照常；
            // 連線失敗、逾時與其他錯誤則連引擎都不可用（available=false），但保留前兩個呼叫已取得的值
            return new SddEngineStatus(reason.engineAvailable(), reason, version, list.projects(), null, checkedAt);
        }
    }

    private static SddEngineStatus unavailable(SddEngineReason reason, SddVersion version, Instant checkedAt,
                                               RuntimeException cause) {
        LOG.warn("AISDLC_SDD 引擎不可用（原因 {}）：{}", reason.wire(), cause.getMessage());
        return new SddEngineStatus(false, reason, version, List.of(), null, checkedAt);
    }

    /**
     * 例外 → {@code reason}（契約 §1.7.1 映射表）。連線失敗、逾時 → {@code bridge_unreachable}；503 {@code sdd_unavailable} →
     * {@code sdd_unavailable}；其餘（5xx、非預期的 4xx、2xx 但形狀不對）→ {@code bridge_error}；
     * 第三個呼叫（{@code /sdd/fsm/{project}}）的 404 → {@code fsm_not_found}、422 → {@code fsm_state_unreadable}。
     */
    static SddEngineReason reasonOf(RuntimeException e, boolean singleProject) {
        if (e instanceof UpstreamException.Unavailable || e instanceof UpstreamException.TimedOut) {
            return SddEngineReason.BRIDGE_UNREACHABLE;
        }
        if (e instanceof UpstreamException.Failure failure) {
            boolean unavailable = Integer.valueOf(503).equals(failure.details().get("bridgeStatus"))
                    && "sdd_unavailable".equals(failure.details().get("bridgeReason"));
            return unavailable ? SddEngineReason.SDD_UNAVAILABLE : SddEngineReason.BRIDGE_ERROR;
        }
        if (e instanceof BridgeRejectedException rejected && singleProject) {
            if (rejected.status() == 404) {
                return SddEngineReason.FSM_NOT_FOUND;
            }
            if (rejected.status() == 422) {
                return SddEngineReason.FSM_STATE_UNREADABLE;
            }
        }
        return SddEngineReason.BRIDGE_ERROR;
    }

    /** Bridge 清單裡讀不動的檔名（{@code errors[]}）只記 WARN，不轉發給前端（契約 §1.7.1）；檔名來自檔案系統，先去掉控制字元防日誌注入。 */
    private static void logUnreadableFiles(SddFsmList list) {
        if (list.errors().isEmpty()) {
            return;
        }
        List<String> names = list.errors().stream().limit(LOGGED_NAMES).map(SddEngineQueryService::printable).toList();
        LOG.warn("Bridge 回報 {} 個讀不動的 FSM 狀態檔（只記日誌、不轉發）：{}{}", list.errors().size(), names,
                list.errors().size() > LOGGED_NAMES ? " …" : "");
    }

    private static String printable(String name) {
        String clean = name == null ? "" : name.replaceAll("\\p{Cntrl}", "?");
        return clean.length() > 100 ? clean.substring(0, 100) + "…" : clean;
    }
}
