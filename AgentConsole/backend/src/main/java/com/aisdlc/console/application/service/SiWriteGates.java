package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.SiWriteUseCase.CloseInput;
import com.aisdlc.console.application.port.in.SiWriteUseCase.DecideInput;
import com.aisdlc.console.application.port.in.SiWriteUseCase.ObservationInput;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.Violation;
import com.aisdlc.console.domain.model.si.SiCloseCommand;
import com.aisdlc.console.domain.model.si.SiDecideCommand;
import com.aisdlc.console.domain.model.si.SiObservationCommand;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * 寫入請求的輸入閘（TCS-SelfImprovingDecide-P2b W12；欄位與值域＝§5.2 表 M-D、M-O、M-C；NFR-P2b-2）。
 *
 * <p><b>閘的目的是不送出「根層入帳時不拒、事後 {@code check} 才轉紅」的 body</b>（accept-then-red）：SA 對真 CLI 的實測——approve 多帶
 * reason 或 flags、reject 的 reason 為空或含換行、obs-add 或 obs-close 欄位含換行，真 CLI 皆 rc 0 入帳而 {@code check} 轉紅。
 * 所以這裡把「禁止欄」與「必填欄」依動詞列死、把會在帳本裡造成壞列的字元（控制字元、OBS 列的豎線）擋在簽章之前。列規則與前提的權威仍是 CLI
 * （{@code retired} 的座標、{@code corrects} 是否存在、PROP 狀態前提、卡面 digest 新鮮度）——Console 不複製，入帳時才判。
 *
 * <p>規則：字串欄<b>不得含</b> C0 控制字元（U+0000～U+001F）、DEL（U+007F）或孤立的代理字元（不論在哪個位置，連首尾的換行都拒收而不是靜默剝除）；
 * 通過後去前後空白；長度以 code point 計；一次回報<b>全部</b>違規（不是遇到第一個就停）。違規一律 422、頂層 reason 為 {@value #INVALID_REQUEST}、
 * {@code details.violations[{field,message}]}（camelCase 欄名）。
 */
public final class SiWriteGates {

    /** 本閘的頂層 {@code reason}（與 Bridge 層同名同義；不進 {@code ErrorReasons}，W15 只新增三個 SI reason）。 */
    public static final String INVALID_REQUEST = "invalid_request";

    public static final int REASON_MAX = 500;
    public static final int OBS_FIELD_MAX = 300;
    /** 三個觀察字串欄的 UTF-8 位元組和上限（必要條件；權威是預檢與 CLI 的列位元組上限）。 */
    public static final int OBS_BYTES_MAX = 700;
    public static final int CLOSE_TEXT_MAX = 120;

    static final List<String> DKINDS = List.of("approve", "reject", "return", "promote", "decline-promote", "rollback", "unblock",
            "resume", "ack-handoff");
    private static final Set<String> WITH_DIGEST = Set.of("approve", "reject", "return", "promote", "decline-promote", "ack-handoff");
    private static final Set<String> WITH_REASON = Set.of("reject", "decline-promote", "return", "rollback", "resume");
    private static final Set<String> WITH_CLASS = Set.of("reject", "decline-promote", "return");
    static final List<String> REASON_CLASSES = List.of("證據不足", "風險過高", "工件類別錯", "已被涵蓋", "範圍外", "卡面不清", "未說明");
    static final List<String> CATEGORIES = List.of("process", "bug", "tooling", "doc", "decision");
    static final List<String> SEVERITIES = List.of("P1", "P2", "P3", "P4");
    static final List<String> FACES = List.of("守衛", "產品", "文件", "流程");
    static final List<String> EXPOSURES = List.of("a", "b", "c", "無");
    static final List<String> TERMINALS = List.of("fixed", "def", "deferred", "retired", "decided", "merged", "proposed");
    private static final Set<String> REF_TERMINALS = Set.of("fixed", "def", "merged", "proposed");

    private static final Pattern ACCOUNT = Pattern.compile("[A-Za-z0-9_.-]{1,64}");
    private static final Pattern PROP_ID = Pattern.compile("PROP-SI-[0-9]{3,}");
    private static final Pattern RUN_ID = Pattern.compile("RUN-SI-[0-9]{3,}");
    private static final Pattern OBS_ID = Pattern.compile("OBS-SI-[0-9]{3,}");
    private static final Pattern DIGEST = Pattern.compile("sha256:[0-9a-f]{64}");
    private static final Pattern GIT_REF = Pattern.compile("[0-9a-f]{7,40}");
    private static final Pattern DEF_ID = Pattern.compile("DEF-[0-9]+-[0-9]+");
    /** 處置文字不得含的空泛說法（根層 {@code rows.py} 的 DISP-DEFER-LATER：入帳後 {@code check} 轉紅；PRD AC-SI-35-2）。 */
    private static final String VAGUE = "之後再看";

    private SiWriteGates() {
    }

    // ── 決定（表 M-D）────────────────────────────────────────────────────────────────────────

    /** 驗帳號名、路徑 id 與決定欄位；通過回命令（欄位已 trim、{@code flags} 已定），違規丟 {@link UnprocessableException}。 */
    public static SiDecideCommand decide(String user, String id, DecideInput input) {
        Check check = new Check();
        account(check, user);
        String dkind = oneOf(check, "dkind", input.dkind(), true, DKINDS);
        decideId(check, id, dkind);
        String digest = null;
        String reason = null;
        String reasonClass = null;
        List<String> flags = List.of();
        if (dkind != null) {
            if (WITH_DIGEST.contains(dkind)) {
                digest = digest(check, input.digest());
            } else {
                forbidden(check, "digest", input.digest(), dkind);
            }
            if (WITH_REASON.contains(dkind)) {
                reason = text(check, "reason", input.reason(), true, REASON_MAX, false);
            } else {
                forbidden(check, "reason", input.reason(), dkind);
            }
            if (WITH_CLASS.contains(dkind)) {
                reasonClass = oneOf(check, "reasonClass", input.reasonClass(), true, REASON_CLASSES);
            } else {
                forbidden(check, "reasonClass", input.reasonClass(), dkind);
            }
            if (Boolean.TRUE.equals(input.unverifiedAck())) {
                if ("promote".equals(dkind)) {
                    flags = List.of("unverified_ack");
                } else {
                    check.add("unverifiedAck", "unverifiedAck 只有 promote（verdict 為 NE 的晉升後式）可為 true，" + dkind + " 不可");
                }
            }
        }
        check.throwIfAny();
        return new SiDecideCommand(id, dkind, digest, reasonClass, reason, flags);
    }

    private static void decideId(Check check, String id, String dkind) {
        if ("resume".equals(dkind)) {
            if (id == null || !RUN_ID.matcher(id).matches()) {
                check.add("id", "id 須為 RUN-SI-<三位以上數字>（resume 綁運轉，不是提案）");
            }
        } else if (dkind != null) {
            if (id == null || !PROP_ID.matcher(id).matches()) {
                check.add("id", "id 須為 PROP-SI-<三位以上數字>（" + dkind + " 綁提案）");
            }
        } else if (id == null || !(PROP_ID.matcher(id).matches() || RUN_ID.matcher(id).matches())) {
            check.add("id", "id 須為 PROP-SI-<三位以上數字>（resume 為 RUN-SI-<三位以上數字>）");
        }
    }

    private static String digest(Check check, String raw) {
        String value = text(check, "digest", raw, true, 71, false);
        if (value != null && !DIGEST.matcher(value).matches()) {
            check.add("digest", "digest 須為 sha256: 加 64 位小寫十六進位");
            return null;
        }
        return value;
    }

    // ── 新增觀察（表 M-O；obs-add 與預檢共用）──────────────────────────────────────────────

    /** 驗帳號名與觀察欄位；通過回命令（字串欄已 trim、不含豎線與控制字元）。 */
    public static SiObservationCommand observation(String user, ObservationInput input) {
        Check check = new Check();
        account(check, user);
        String context = text(check, "context", input.context(), true, OBS_FIELD_MAX, true);
        String symptom = text(check, "symptom", input.symptom(), true, OBS_FIELD_MAX, true);
        String evidence = text(check, "evidence", input.evidence(), true, OBS_FIELD_MAX, true);
        if (context != null && symptom != null && evidence != null) {
            int bytes = utf8(context) + utf8(symptom) + utf8(evidence);
            if (bytes > OBS_BYTES_MAX) {
                String message = "context、symptom、evidence 三欄的 UTF-8 位元組和為 " + bytes + "，超過 " + OBS_BYTES_MAX
                        + "（入帳列還有其他欄位，實際上限更低；以預檢為準）";
                check.add("context", message);
                check.add("symptom", message);
                check.add("evidence", message);
            }
        }
        String category = oneOf(check, "category", input.category(), true, CATEGORIES);
        String severity = oneOf(check, "severity", input.severity(), true, SEVERITIES);
        String face = oneOf(check, "face", input.face(), true, FACES);
        String exposure = null;
        if (input.exposure() != null) {
            exposure = oneOf(check, "exposure", input.exposure(), false, EXPOSURES);
            if (face != null && !"守衛".equals(face)) {
                check.add("exposure", "exposure 只有 face 為守衛時可填");
                exposure = null;
            }
        } else if ("守衛".equals(face)) {
            check.add("exposure", "face 為守衛時 exposure 為必填（a、b、c 或 無）");
        }
        if (input.externalDerived() == null) {
            check.add("externalDerived", "externalDerived 為必填（true 或 false）");
        }
        String corrects = null;
        if (input.corrects() != null) {
            corrects = text(check, "corrects", input.corrects(), false, 64, false);
            if (corrects != null && !OBS_ID.matcher(corrects).matches()) {
                check.add("corrects", "corrects 須為 OBS-SI-<三位以上數字>");
                corrects = null;
            }
        }
        check.throwIfAny();
        return new SiObservationCommand(context, symptom, evidence, category, severity, face, exposure,
                Boolean.TRUE.equals(input.externalDerived()), corrects);
    }

    // ── 關閉觀察（表 M-C）────────────────────────────────────────────────────────────────────

    /** 驗帳號名、路徑 id 與終值欄位；通過回命令（{@code disposition} 已由終值組成）。 */
    public static SiCloseCommand close(String user, String id, CloseInput input) {
        Check check = new Check();
        account(check, user);
        if (id == null || !OBS_ID.matcher(id).matches()) {
            check.add("id", "id 須為 OBS-SI-<三位以上數字>");
        }
        String terminal = null;
        if ("open".equals(input.terminal() == null ? null : input.terminal().strip())) {
            check.add("terminal", "terminal 不可為 open（open 是新增列時的初始處置，不是終值）");
        } else {
            terminal = oneOf(check, "terminal", input.terminal(), true, TERMINALS);
        }
        String disposition = null;
        if (terminal != null) {
            disposition = REF_TERMINALS.contains(terminal) ? refDisposition(check, terminal, input)
                    : textDisposition(check, terminal, input);
        }
        check.throwIfAny();
        return new SiCloseCommand(id, disposition);
    }

    private static String refDisposition(Check check, String terminal, CloseInput input) {
        forbidden(check, "text", input.text(), terminal);
        String ref = text(check, "ref", input.ref(), true, 64, false);
        if (ref == null) {
            return null;
        }
        Pattern pattern = switch (terminal) {
            case "fixed" -> GIT_REF;
            case "def" -> DEF_ID;
            case "merged" -> OBS_ID;
            default -> PROP_ID;
        };
        if (!pattern.matcher(ref).matches()) {
            check.add("ref", switch (terminal) {
                case "fixed" -> "ref 須為 7～40 碼小寫十六進位（提交編號）";
                case "def" -> "ref 須為 DEF-<數字>-<數字>";
                case "merged" -> "ref 須為 OBS-SI-<三位以上數字>";
                default -> "ref 須為 PROP-SI-<三位以上數字>";
            });
            return null;
        }
        return switch (terminal) {
            case "fixed" -> "fixed@" + ref;
            case "def" -> ref;
            case "merged" -> "merged@" + ref;
            default -> "proposed@" + ref;
        };
    }

    private static String textDisposition(Check check, String terminal, CloseInput input) {
        forbidden(check, "ref", input.ref(), terminal);
        String text = text(check, "text", input.text(), true, CLOSE_TEXT_MAX, true);
        if (text != null && text.contains(VAGUE)) {
            check.add("text", "text 不可含「" + VAGUE + "」（空泛的處置不算處置）");
            return null;
        }
        return text == null ? null : terminal + "：" + text;
    }

    // ── 共用 ────────────────────────────────────────────────────────────────────────────────

    private static void account(Check check, String user) {
        if (user == null || !ACCOUNT.matcher(user).matches()) {
            check.add("user", "登入帳號名須為 1～64 個英數字、底線、點或連字號（目前的帳號名不合，無法寫進稽核簽章）");
        }
    }

    /** 這個動詞（終值）不可帶的欄位：有值（含空字串）就是違規。 */
    private static void forbidden(Check check, String field, String raw, String verb) {
        if (raw != null) {
            check.add(field, field + " 在 " + verb + " 不可填");
        }
    }

    private static String oneOf(Check check, String field, String raw, boolean required, List<String> allowed) {
        String value = text(check, field, raw, required, 64, false);
        if (value != null && !allowed.contains(value)) {
            check.add(field, field + " 須為 " + String.join("、", allowed) + " 之一");
            return null;
        }
        return value;
    }

    /**
     * 字串欄的通則：{@code null} 只有選填才可；不得含控制字元或孤立代理字元（先判原值，所以首尾的換行也拒收）；去前後空白後不可為空；
     * {@code forbidPipe} 時不可含 {@code |}（OBS 列是 Markdown 九欄表）；長度以 code point 計。回通過的值，違規回 {@code null}（已登記）。
     */
    private static String text(Check check, String field, String raw, boolean required, int maxCodePoints, boolean forbidPipe) {
        if (raw == null) {
            if (required) {
                check.add(field, field + " 為必填");
            }
            return null;
        }
        if (hasForbiddenChar(raw)) {
            check.add(field, field + " 不可含控制字元（換行、TAB 等）或無效字元");
            return null;
        }
        String value = raw.strip();
        if (value.isEmpty()) {
            check.add(field, field + " 不可全為空白");
            return null;
        }
        if (forbidPipe && value.indexOf('|') >= 0) {
            check.add(field, field + " 不可含豎線 |（觀察列是 Markdown 九欄表）");
            return null;
        }
        int length = value.codePointCount(0, value.length());
        if (length > maxCodePoints) {
            check.add(field, field + " 為 " + length + " 個字元，超過上限 " + maxCodePoints);
            return null;
        }
        return value;
    }

    private static boolean hasForbiddenChar(String value) {
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (c < 0x20 || c == 0x7F) {
                return true;
            }
            if (Character.isHighSurrogate(c)) {
                if (i + 1 >= value.length() || !Character.isLowSurrogate(value.charAt(i + 1))) {
                    return true;
                }
                i++;
            } else if (Character.isLowSurrogate(c)) {
                return true;
            }
        }
        return false;
    }

    private static int utf8(String value) {
        return value.getBytes(StandardCharsets.UTF_8).length;
    }

    /** 收集違規、一次丟出。 */
    private static final class Check {

        private final List<Violation> violations = new ArrayList<>();

        void add(String field, String message) {
            violations.add(new Violation(field, message));
        }

        void throwIfAny() {
            if (violations.isEmpty()) {
                return;
            }
            List<Map<String, Object>> asMaps = new ArrayList<>();
            for (Violation violation : violations) {
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("field", violation.field());
                item.put("message", violation.message());
                asMaps.add(item);
            }
            throw new UnprocessableException("請求欄位未通過檢查（" + violations.size() + " 項）", INVALID_REQUEST, List.of(),
                    violations, Map.of("violations", asMaps));
        }
    }
}
