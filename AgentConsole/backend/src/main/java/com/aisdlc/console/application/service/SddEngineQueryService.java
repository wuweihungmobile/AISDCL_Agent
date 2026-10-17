package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.SddEngineUseCase;
import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.model.engine.SddEngineReason;
import com.aisdlc.console.domain.model.engine.SddEngineStatus;
import com.aisdlc.console.domain.model.engine.SddFsmList;
import com.aisdlc.console.domain.model.engine.SddFsmState;
import com.aisdlc.console.domain.model.engine.SddVersion;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.service.SddBindingRules;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import java.util.regex.Pattern;

/**
 * AISDLC_SDD 引擎狀態（API-ENG-01、API-ENG-02；契約 §1.7.1、§1.10.4、§3.1.3；D-16、D-115-02）。
 *
 * <p>三個 Bridge 呼叫依序進行、<b>失敗即短路</b>（後面的不再發），每個連線 2 秒／讀取 3 秒、不重試（在 {@link AgentBridge} 實作）。
 * 這支查詢回報的是「引擎現在的狀態」，不是「這次呼叫成不成功」，所以 Bridge 不可達、503、非預期回應都轉成
 * {@code available=false}＋{@code reason}（沿用「Bridge 不可達回 200」的慣例），不丟例外；只有 {@code project} 不合規則是 400、
 * {@code projectId} 找不到是 404。不快取：每次請求都打 Bridge（前端 30 秒輪詢一次）。console-api 唯讀：不寫 SDD 目錄、不寫任何
 * FSM-STATE 檔（ADR-001 D22；v1.5 唯一的寫入動詞是 {@code POST /projects/{id}/sdd/freeze}，不在這支查詢）。
 *
 * <p>v1.5：帶 {@code projectId} 時 {@code GET /sdd/fsm*} 帶 {@code root=<專案的 executionPath>}，{@code project} 省略時預設取專案的
 * <b>有效 FSM 專案</b>（{@code sddProject} 有值取它，否則專案名；Backend 不淨化，值原樣交給 Bridge 的淨化鏡像）。
 */
@Service
public class SddEngineQueryService implements SddEngineUseCase {

    /** 專案名（有效值）只驗長度與控制字元（契約 §1.10.4；不淨化、不檢查 Windows 禁用字元，那是 Bridge 的淨化鏡像的事）。 */
    private static final Pattern CONTROL_CHARS = Pattern.compile("\\p{Cntrl}");
    private static final int LOGGED_NAMES = 20;
    private static final Logger LOG = LoggerFactory.getLogger(SddEngineQueryService.class);

    private final AgentBridge bridge;
    private final ProjectRepository projects;
    private final Clock clock;

    public SddEngineQueryService(AgentBridge bridge, ProjectRepository projects, Clock clock) {
        this.bridge = bridge;
        this.projects = projects;
        this.clock = clock;
    }

    @Override
    public SddEngineStatus status(String project, UUID projectId) {
        requireValidProject(project);                     // 400 先於 projectId 的 404（契約 §1.10.4）
        String root = null;
        String name = project;
        if (projectId != null) {
            Project bound = projects.findById(projectId).orElseThrow(() -> NotFoundException.of("專案", projectId));
            root = bound.executionPath();
            if (name == null) {
                name = bound.effectiveSddProject();
            }
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
            list = bridge.sddFsmList(root);
        } catch (UpstreamException | BridgeRejectedException e) {
            if (root != null && isRootRejected(e)) {
                return rootRejected(version, checkedAt, e);
            }
            return unavailable(reasonOf(e, false), version, checkedAt, e);
        }
        logUnreadableFiles(list);

        if (name == null) {
            return new SddEngineStatus(true, null, version, list.projects(), null, checkedAt);
        }
        if (project == null && list.projects().isEmpty()) {
            // 預設取的專案（沒有明示 project）而這個專案根還沒有任何 FSM 狀態檔：不是錯誤，卡片顯示「尚無 FSM 狀態檔」（契約 §1.10.4）
            return new SddEngineStatus(true, null, version, list.projects(), null, checkedAt);
        }
        try {
            SddFsmState fsm = bridge.sddFsm(name, root);
            return new SddEngineStatus(true, null, version, list.projects(), fsm, checkedAt);
        } catch (UpstreamException | BridgeRejectedException e) {
            if (root != null && isRootRejected(e)) {
                return rootRejected(version, checkedAt, e);
            }
            SddEngineReason reason = reasonOf(e, true);
            LOG.info("AISDLC_SDD 單一專案 FSM 取不到（project={}，原因 {}）：{}", printable(name), reason.wire(), e.getMessage());
            // 第三個呼叫的 404／422 是「專案層級」的問題：引擎本身可用（available=true），清單與版本照常；
            // 連線失敗、逾時與其他錯誤則連引擎都不可用（available=false），但保留前兩個呼叫已取得的值
            return new SddEngineStatus(reason.engineAvailable(), reason, version, list.projects(), null, checkedAt);
        }
    }

    /** {@code project} 的規則（契約 §1.10.4）：1～200 字元、不含控制字元（U+0000～U+001F、U+007F）；不合 → 400 {@code errors[0].field=project}。 */
    private static void requireValidProject(String project) {
        if (project == null) {
            return;
        }
        if (project.isEmpty() || project.length() > SddBindingRules.MAX_EFFECTIVE_PROJECT
                || CONTROL_CHARS.matcher(project).find()) {
            throw ValidationException.of("project", "project 須為 1～" + SddBindingRules.MAX_EFFECTIVE_PROJECT
                    + " 字元且不含控制字元（FSM 專案名的有效值）");
        }
    }

    private static SddEngineStatus unavailable(SddEngineReason reason, SddVersion version, Instant checkedAt,
                                               RuntimeException cause) {
        LOG.warn("AISDLC_SDD 引擎不可用（原因 {}）：{}", reason.wire(), cause.getMessage());
        return new SddEngineStatus(false, reason, version, List.of(), null, checkedAt);
    }

    /**
     * Bridge 對 {@code root} 回 422 {@code sanitization_failed}（專案路徑不在 {@code BRIDGE_ALLOWED_PATH_ROOTS} 內、或已不存在）：
     * 引擎可用，只是「這個專案的根」不被接受（契約 §1.10.4）；{@code violations[]} 有給時須指向 {@code root}，沒給就視為 root。
     */
    private static boolean isRootRejected(RuntimeException e) {
        if (!(e instanceof BridgeRejectedException rejected) || rejected.status() != 422
                || !"sanitization_failed".equals(rejected.reason())) {
            return false;
        }
        return rejected.violations() == null || rejected.violations().isEmpty()
                || rejected.violations().stream().anyMatch(violation -> "root".equals(violation.get("field")));
    }

    private static SddEngineStatus rootRejected(SddVersion version, Instant checkedAt, RuntimeException cause) {
        LOG.info("AISDLC_SDD 專案根被 Bridge 拒絕（{}）：{}", SddEngineReason.SDD_ROOT_REJECTED.wire(), cause.getMessage());
        return new SddEngineStatus(true, SddEngineReason.SDD_ROOT_REJECTED, version, List.of(), null, checkedAt);
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
