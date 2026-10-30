package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.BackupJobUseCase;
import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.BackupClock;
import com.aisdlc.console.application.port.out.BackupControlPort;
import com.aisdlc.console.application.port.out.BackupJobRepository;
import com.aisdlc.console.application.port.out.BackupJobRepository.Job;
import com.aisdlc.console.application.port.out.BackupJobRepository.Status;
import com.aisdlc.console.application.port.out.BackupSettings;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.ServiceUnavailableException;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.exception.Violation;
import com.aisdlc.console.domain.model.backup.BackupJobReason;
import com.aisdlc.console.domain.model.backup.BackupMasker;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

/**
 * 手動觸發備份（TCS-SysAdminBackup-20261027 R-BK-30～R-BK-38、R-BK-56；API-BK-04）。Console 在備份功能唯一的寫入：建一列 QUEUED、寫一份請求檔給 sidecar。
 *
 * <p>驗證序（D-BK-T13；先中者定案，<b>任一前序失敗都零列、零檔</b>）：{@code type} 合法（422 {@code invalid_request}）→ {@code confirm} 為 JSON
 * 布林 true（400 {@code backup_confirm_required}；字串 "true"、數字 1 都不收）→ 控制面可用（503：目錄未設、心跳過期、匯出不可讀、資料庫讀取失敗）→
 * 無進行中（409）→ 頻率上限（409）→ 建列並寫檔。成功路徑的呼叫序恆為 {@code findActive → insertQueued → writeRequest}（<b>先插列、後寫檔</b>）：
 * 先寫檔再插列，檔被撿走而列插入失敗時就有一個無主的工作在跑。
 *
 * <p>單工的兜底是資料庫的部分唯一索引：兩個併發的 POST 可能同時通過「無進行中」的檢查，輸家的 INSERT 被唯一鍵拒絕，轉成同一個 409（不是 500）。
 * 寫請求檔失敗時，該列以<b>條件式</b> UPDATE 補償為 FAILED（{@code control_write_failed}；唯一索引釋放、可立即重試）；已被別處改成 EXPIRED 的列不覆蓋。
 */
@Service
public class BackupJobService implements BackupJobUseCase {

    /** 入口閘的頂層 {@code reason}（與 Bridge 層及 {@code SiWriteGates} 同名同義；以區域常數持有、不進 {@code ErrorReasons}）。 */
    public static final String INVALID_REQUEST = "invalid_request";

    // 五個有狀態碼的 API reason 的中文訊息（與契約表、前端 BACKUP_REASONS 逐字相同；BackupReasonsContractTest 雙向鎖住）
    public static final String CONTROL_UNAVAILABLE_MESSAGE = "備份控制面目前無法使用";
    public static final String CONFIRM_REQUIRED_MESSAGE = "請先確認後再執行";
    public static final String IN_PROGRESS_MESSAGE = "已有進行中的備份工作";
    public static final String TOO_FREQUENT_MESSAGE = "距離上一份同類備份過近，請稍後再試";

    private static final Logger LOG = LoggerFactory.getLogger(BackupJobService.class);

    private final BackupSettings settings;
    private final BackupControlPort control;
    private final BackupJobRepository jobs;
    private final BackupClock clock;
    private final AuditTrail audit;
    private final BackupQueryService.ExportReader reader;

    BackupJobService(BackupSettings settings, BackupControlPort control, BackupJobRepository jobs, BackupClock clock,
                     AuditTrail audit) {
        this.settings = settings;
        this.control = control;
        this.jobs = jobs;
        this.clock = clock;
        this.audit = audit;
        this.reader = new BackupQueryService.ExportReader(settings, control, clock);
    }

    @Override
    public Accepted trigger(String user, Map<String, Object> body) {
        String type = checkedType(body);
        if (!Boolean.TRUE.equals(body.get("confirm"))) {
            throw ValidationException.of("confirm", CONFIRM_REQUIRED_MESSAGE, ErrorReasons.BACKUP_CONFIRM_REQUIRED, Map.of());
        }
        if (settings.exportDir() == null || settings.requestDir() == null) {
            throw controlUnavailable();
        }
        BackupQueryService.Export export = reader.read();
        if (export.reason != null) {
            // 目錄未設、心跳過期、匯出不可讀、schema 不符：無法評估頻率與安全性＝不可觸發（不誤判為 409，也不放行）
            throw controlUnavailable();
        }
        try {
            if (!jobs.findActive().isEmpty()) {
                throw new ConflictException(IN_PROGRESS_MESSAGE, ErrorReasons.BACKUP_JOB_IN_PROGRESS);
            }
        } catch (DataAccessException e) {
            LOG.warn("備份工作表讀取失敗，POST 回 503：{}", BackupMasker.mask(e.toString()));
            throw controlUnavailable();
        }
        checkFrequency(type, export);

        // 秒精度：請求檔、資料庫列、回應三處同值（sidecar 以秒精度比 expires_at）
        Instant requestedAt = clock.instant().truncatedTo(ChronoUnit.SECONDS);
        UUID id = UUID.randomUUID();
        try {
            jobs.insertQueued(new Job(id, type, Status.QUEUED, user, requestedAt, null, null, null, null, ""));
        } catch (DuplicateKeyException e) {
            // 併發的輸家：部分唯一索引拒絕了第二個進行中的列
            throw new ConflictException(IN_PROGRESS_MESSAGE, ErrorReasons.BACKUP_JOB_IN_PROGRESS);
        } catch (DataAccessException e) {
            LOG.warn("備份工作列建立失敗，POST 回 503：{}", BackupMasker.mask(e.toString()));
            throw controlUnavailable();
        }
        audit.note("backup.trigger", "backup", id.toString());
        try {
            control.writeRequest(new BackupControlPort.Request(id, type, requestedAt,
                    requestedAt.plusSeconds(settings.requestTtlSeconds())));
        } catch (IOException | RuntimeException e) {
            LOG.warn("請求檔寫入失敗，該列補償為 FAILED（{}）：{}", BackupJobReason.CONTROL_WRITE_FAILED.value(), e.toString());
            compensate(id);
            throw controlUnavailable();
        }
        return new Accepted(id.toString(), type, Status.QUEUED.name(), requestedAt);
    }

    /** {@code type} 缺、非字串或不在 {full,diff,verify}（區分大小寫；{@code dump}、{@code incr} 非法）⇒ 422，{@code details.violations} 點名 {@code type}。 */
    private static String checkedType(Map<String, Object> body) {
        Object raw = body.get("type");
        if (raw instanceof String text && Set.of("full", "diff", "verify").contains(text)) {
            return text;
        }
        List<Violation> violations = List.of(new Violation("type", "type 須為 full、diff、verify 之一（區分大小寫）"));
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("field", "type");
        item.put("message", violations.get(0).message());
        throw new UnprocessableException("請求欄位未通過檢查（1 項）", INVALID_REQUEST, List.of(), violations,
                Map.of("violations", List.of(item)));
    }

    /**
     * 頻率上限（伺服器端；R-BK-38、D-BK-T12）：full——各已設定 repo 最近一份<b>全備</b>的 stop 距現在<b>皆</b> &lt; 門檻（嚴格小於；恰好 24 小時允許）
     * ⇒ 409，{@code nextAllowedAt}＝各 repo（最近該類備份＋門檻）的最小值；任一 repo 較舊或缺席 ⇒ 允許；diff 同形（看各 repo 最近一份<b>差異</b>備份）；
     * verify 不設。info 是 {@code ok:false}（合法檔、來源失敗）時評估不了——依主控裁決（backup_impl_decisions 第 5 點）不擋。
     */
    private void checkFrequency(String type, BackupQueryService.Export export) {
        if ("verify".equals(type) || !export.infoOk || export.repoKeys.isEmpty()) {
            return;
        }
        long threshold = "full".equals(type) ? settings.minFullIntervalSeconds() : settings.minDiffIntervalSeconds();
        Instant earliestAllowed = null;
        for (int repo : export.repoKeys) {
            Optional<Instant> last = export.backups.stream().filter(b -> b.repoKey() == repo && type.equals(b.kind()))
                    .map(BackupQueryService.Backup::stop).max(Instant::compareTo);
            if (last.isEmpty()) {
                return;
            }
            Instant allowedAt = last.get().plusSeconds(threshold);
            if (!export.now.isBefore(allowedAt)) {
                return;
            }
            earliestAllowed = earliestAllowed == null || allowedAt.isBefore(earliestAllowed) ? allowedAt : earliestAllowed;
        }
        Map<String, Object> details = new LinkedHashMap<>();
        details.put("type", type);
        details.put("nextAllowedAt", earliestAllowed.toString());
        throw new ConflictException(TOO_FREQUENT_MESSAGE, ErrorReasons.BACKUP_TOO_FREQUENT, details);
    }

    /** 補償：條件式 UPDATE（只改仍在進行中的列；已被改成 EXPIRED 等終態的列不覆蓋）。補償失敗只記 WARN——503 照回。 */
    private void compensate(UUID id) {
        try {
            jobs.markTerminalIfActive(id, Status.FAILED, null, BackupJobReason.CONTROL_WRITE_FAILED.value(), null,
                    clock.instant(), "");
        } catch (RuntimeException e) {
            LOG.warn("補償 UPDATE 失敗（該列可能停在 QUEUED，由對帳的過期兜底收回）：{}", BackupMasker.mask(e.toString()));
        }
    }

    private static ServiceUnavailableException controlUnavailable() {
        return new ServiceUnavailableException(CONTROL_UNAVAILABLE_MESSAGE, ErrorReasons.BACKUP_CONTROL_UNAVAILABLE);
    }
}
