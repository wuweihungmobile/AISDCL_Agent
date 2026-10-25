package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.SiWriteUseCase;
import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.SiAuditRefSource;
import com.aisdlc.console.application.port.out.SiConsoleWriteRepository;
import com.aisdlc.console.application.port.out.SiWriteSettings;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.ForbiddenException;
import com.aisdlc.console.domain.exception.ServiceUnavailableException;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.model.si.SiCloseCommand;
import com.aisdlc.console.domain.model.si.SiConsoleWrite;
import com.aisdlc.console.domain.model.si.SiDecideCommand;
import com.aisdlc.console.domain.model.si.SiObservationCommand;
import com.aisdlc.console.domain.model.si.SiValidation;
import com.aisdlc.console.domain.model.si.SiWriteKind;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import java.util.function.BiFunction;
import java.util.function.Consumer;

/**
 * SelfImproving 寫入載體的用例（TCS-SelfImprovingDecide-P2b W10、W11、W15）。<b>整個 backend 唯一</b>呼叫 {@code AgentBridge.siWrite…} 與
 * {@link SiConsoleWriteRepository}（寫入埠）的類別（ArchUnit 鎖住）。
 *
 * <p>流程（決定、新增觀察、關閉觀察同一條）：授權 → 停用檢查 → 輸入閘 → 取 {@code auditRef}（{@link SiAuditRefSource}）與 {@code time}
 * → {@link SiAuditSigner} 組 body 並簽章 → <b>INSERT 稽核列</b> → 單次 Bridge 呼叫（外層字串原樣送出）→ 回收據。INSERT 先於 Bridge：
 * 寧可有列無檔、不要有檔無列（PRD §9.3）。<b>不重試</b>；重送一律新 {@code auditRef}。
 *
 * <p><b>補償</b>：Bridge 明確拒絕（任何 4xx、503）、其他 5xx、連線階段失敗、1xx／3xx（請求沒有被處理）＝確定沒有落檔→刪除剛寫的那一列；
 * 讀取逾時、送出後連線重設或提前 EOF、2xx 但本文無法解析＝結果不明（檔可能已落地）→<b>保留</b>該列並在錯誤的 {@code details.outcomeUnknown}
 * 標明（之後由對帳面板以待入帳呈現）。補償刪除本身失敗只記 WARN、不遮蓋原本的錯誤（已知邊界 13：留下幽靈待入帳列）。
 *
 * <p>🔴 金鑰與權杖值不進日誌、例外與回應；日誌只記 kind、auditRef、帳號名與 key_id。
 */
@Service
public class SiConsoleWriteService implements SiWriteUseCase {

    private static final Logger LOG = LoggerFactory.getLogger(SiConsoleWriteService.class);

    private final SiWriteSettings settings;
    private final SiAuditSigner signer;
    private final SiAuditRefSource refs;
    private final SiConsoleWriteRepository repository;
    private final AgentBridge bridge;

    public SiConsoleWriteService(SiWriteSettings settings, SiAuditSigner signer, SiAuditRefSource refs,
                                 SiConsoleWriteRepository repository, AgentBridge bridge) {
        this.settings = settings;
        this.signer = signer;
        this.refs = refs;
        this.repository = repository;
        this.bridge = bridge;
    }

    @Override
    public Receipt decide(String user, String id, DecideInput input) {
        authorize(user);
        SiDecideCommand command = SiWriteGates.decide(user, id, input);
        return write(SiWriteKind.DECIDE, user, command.subject(), command.digest(),
                (ref, time) -> signer.decideBody(ref, user, time, command),
                audit -> bridge.siWriteDecide(command.subject(), audit));
    }

    @Override
    public Receipt addObservation(String user, ObservationInput input) {
        authorize(user);
        SiObservationCommand command = SiWriteGates.observation(user, input);
        return write(SiWriteKind.OBS_ADD, user, null, null, (ref, time) -> signer.observationBody(ref, user, time, command),
                bridge::siWriteObservation);
    }

    @Override
    public Receipt closeObservation(String user, String id, CloseInput input) {
        authorize(user);
        SiCloseCommand command = SiWriteGates.close(user, id, input);
        return write(SiWriteKind.OBS_CLOSE, user, command.obsId(), null, (ref, time) -> signer.closeBody(ref, user, time, command),
                audit -> bridge.siWriteObservationClose(command.obsId(), audit));
    }

    /**
     * 預檢：同一關（授權、停用、輸入閘），但<b>不取 ref、不簽章、不寫資料庫</b>；Bridge 收到的是未簽 body（無 {@code audit_ref}、
     * {@code mac}、{@code key_id}）。
     */
    @Override
    public SiValidation validateObservation(String user, ObservationInput input) {
        authorize(user);
        SiObservationCommand command = SiWriteGates.observation(user, input);
        String body = signer.observationBody(null, user, SiAuditSigner.formatTime(signer.now()), command);
        try {
            return bridge.siValidateObservation(body);
        } catch (BridgeRejectedException e) {
            throw SiBridgeErrors.mapWrite(e);
        }
    }

    // ── 閘門序的前兩關（授權、停用）────────────────────────────────────────────────────────────

    private void authorize(String user) {
        if (user == null || !settings.deciders().contains(user)) {
            throw new ForbiddenException("帳號不在 SelfImproving 決定者名單內（console.si.deciders；區分大小寫）",
                    ErrorReasons.SI_WRITE_FORBIDDEN);
        }
        if (settings.keyRing().isEmpty()) {
            throw disabled("audit_key_unset", "backend 沒有設定稽核簽章金鑰（CONSOLE_SI_AUDIT_KEY），SelfImproving 寫入面已停用");
        }
        if (!settings.bridgeWriteTokenConfigured()) {
            throw disabled("bridge_token_unset", "backend 沒有設定 SelfImproving 寫入權杖（BRIDGE_SI_WRITE_TOKEN），寫入面已停用");
        }
    }

    private static ServiceUnavailableException disabled(String cause, String message) {
        return new ServiceUnavailableException(message, ErrorReasons.SI_WRITE_DISABLED, Map.of("cause", cause));
    }

    // ── 寫入主流程 ──────────────────────────────────────────────────────────────────────────

    private Receipt write(SiWriteKind kind, String user, String subject, String digest,
                          BiFunction<String, String, String> bodyOf, Consumer<String> send) {
        String ref = refs.next();
        UUID auditRef = UUID.fromString(ref);
        if (!ref.equals(auditRef.toString())) {
            throw new IllegalStateException("audit_ref 須為小寫正規 UUID（Bridge 與根層 CLI 都只收這個形態）");
        }
        OffsetDateTime time = signer.now();
        String timeText = SiAuditSigner.formatTime(time);
        SiAuditSigner.SignedAudit signed = signer.sign(kind, ref, subject, bodyOf.apply(ref, timeText), settings.keyRing());
        repository.insert(new SiConsoleWrite(auditRef, kind, user, SiAuditSigner.ROLE, time, subject, digest, signed.body(),
                signed.keyId(), signed.mac()));
        try {
            send.accept(signed.file());
        } catch (BridgeRejectedException e) {
            compensate(auditRef);
            throw SiBridgeErrors.mapWrite(e);
        } catch (UpstreamException e) {
            throw settle(e, auditRef);
        }
        LOG.info("SelfImproving 稽核檔已落地：kind={} auditRef={} user={} keyId={}", kind.wire(), ref, user, signed.keyId());
        return new Receipt(ref, kind.wire(), subject, timeText, signed.keyId());
    }

    /** 上游失敗的善後：結果不明就保留稽核列並標明；確定沒有落檔就刪除。 */
    private UpstreamException settle(UpstreamException failure, UUID auditRef) {
        if (!outcomeUnknown(failure)) {
            compensate(auditRef);
            return failure;
        }
        LOG.warn("SelfImproving 稽核檔落地結果不明，保留稽核列：auditRef={} cause={}", auditRef, failure.getClass().getSimpleName());
        Map<String, Object> details = new LinkedHashMap<>(failure.details());
        details.put("outcomeUnknown", true);
        String message = failure.getMessage() + "；稽核檔可能已落地，稽核列已保留（結果不明），請以對帳面板為準";
        if (failure instanceof UpstreamException.TimedOut) {
            return new UpstreamException.TimedOut(message, details);
        }
        if (failure instanceof UpstreamException.Unavailable unavailable) {
            return new UpstreamException.Unavailable(message, unavailable.deliveryUncertain(), details);
        }
        return new UpstreamException.Failure(message, details);
    }

    /**
     * 這個上游失敗之後，Bridge 是否「可能已處理請求」：讀取逾時（請求已送出）、送出後的通訊失敗（{@code deliveryUncertain}）、2xx 但本文無法解析
     * （{@code bridgeStatus}＝200）為結果不明；連線階段失敗、5xx 與其他非 2xx（含 1xx／3xx）為確定沒有落檔。缺 {@code bridgeStatus} 的
     * {@code Failure} 無從判斷，保守地視為結果不明（保留列比誤刪列安全）。
     */
    private static boolean outcomeUnknown(UpstreamException failure) {
        if (failure instanceof UpstreamException.TimedOut) {
            return true;
        }
        if (failure instanceof UpstreamException.Unavailable unavailable) {
            return unavailable.deliveryUncertain();
        }
        Object status = failure.details().get("bridgeStatus");
        return !(status instanceof Number number) || number.intValue() == 200;
    }

    private void compensate(UUID auditRef) {
        try {
            repository.deleteByAuditRef(auditRef);
        } catch (RuntimeException e) {
            LOG.warn("SelfImproving 補償刪除稽核列失敗（留下待入帳的幽靈列，對帳面板會呈現）：auditRef={} cause={}", auditRef,
                    e.getClass().getSimpleName());
        }
    }
}
