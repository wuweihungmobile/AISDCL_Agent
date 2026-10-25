package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.SiWriteUseCase.CloseInput;
import com.aisdlc.console.application.port.in.SiWriteUseCase.DecideInput;
import com.aisdlc.console.application.port.in.SiWriteUseCase.ObservationInput;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.Violation;
import com.aisdlc.console.domain.model.si.SiCloseCommand;
import com.aisdlc.console.domain.model.si.SiDecideCommand;
import com.aisdlc.console.domain.model.si.SiObservationCommand;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.catchThrowable;

/**
 * 寫入請求的輸入閘（TCS-SelfImprovingDecide-P2b AT-950-7-1、7-2、7-E-1、7-E-2、7-E-3；W12、表 M-D／M-O／M-C）。為什麼重要：SA 對真 CLI 的實測是
 * 「approve 多帶 reason、reject 的 reason 為空或含換行、觀察欄位含換行或豎線」都會 rc 0 入帳、事後 {@code check} 才轉紅——accept-then-red 沒有任何
 * 人當場看得到。所以閘要在簽章之前把這些擋成 422，而且一次全列（表單才能一次標紅所有問題）；每條規則都要有「恰好通過」的邊界對照，
 * 否則閘會悄悄鬆掉或緊掉。
 */
class SiWriteGatesTest {

    private static final String D0 = "sha256:d21ae6f5a48de71266479e0a7f6278786764f9a52bbb0a7c6d82b7f1419cec9c";
    private static final String PROP = "PROP-SI-004";
    private static final String RUN = "RUN-SI-001";
    private static final String OBS = "OBS-SI-005";
    /** 四位數的 id：執行期組字串，使原始碼不出現帳本裡不存在的 id 字面（根層 ref.obs 判準掃整個 repo）。 */
    private static final String FOUR_PROP = "PROP-SI-" + "1234";
    private static final String FOUR_OBS = "OBS-SI-" + "1234";

    /** 位數不足的壞號：根層 {@code ref.obs} 掃整個 repo 的 {@code OBS-SI-<數字>} 字面、不在帳本內的一律懸空，所以壞號在執行期才組出。 */
    private static String obsId(String digits) {
        return "OBS-SI-" + digits;
    }

    // ── 小幫手 ────────────────────────────────────────────────────────────────────────────

    private static DecideInput in(String dkind, String digest, String reason, String reasonClass, Boolean ack) {
        return new DecideInput(dkind, digest, reason, reasonClass, ack);
    }

    private static ObservationInput obs(String context, String symptom, String evidence, String category, String severity,
                                        String face, String exposure, Boolean external, String corrects) {
        return new ObservationInput(context, symptom, evidence, category, severity, face, exposure, external, corrects);
    }

    private static ObservationInput validObs() {
        return obs("Console・自我進化頁", "待入帳徽章在入帳後仍顯示", "AgentConsole/frontend/components/domain/si/SiView.tsx:88", "bug",
                "P3", "產品", null, false, null);
    }

    private static UnprocessableException rejected(Runnable gate) {
        Throwable thrown = catchThrowable(gate::run);
        assertThat(thrown).as("閘應當拒收").isInstanceOf(UnprocessableException.class);
        return (UnprocessableException) thrown;
    }

    private static List<String> fieldsOf(UnprocessableException e) {
        return e.violations().stream().map(Violation::field).distinct().toList();
    }

    private static String repeat(String unit, int times) {
        return unit.repeat(times);
    }

    // ── AT-950-7-1：九個有效 decide 組合 ────────────────────────────────────────────────────

    @Test
    void AT_950_7_1_theNineValidDecideCombinationsPassAndYieldTheTableCommands() {
        record Case(String id, DecideInput input, SiDecideCommand expected) {
        }
        List<Case> cases = List.of(
                new Case(PROP, in("approve", D0, null, null, null), new SiDecideCommand(PROP, "approve", D0, null, null, List.of())),
                new Case(PROP, in("reject", D0, "證據座標不足，無法判定", "證據不足", null),
                        new SiDecideCommand(PROP, "reject", D0, "證據不足", "證據座標不足，無法判定", List.of())),
                new Case(PROP, in("return", D0, "改用 M 類", "工件類別錯", null),
                        new SiDecideCommand(PROP, "return", D0, "工件類別錯", "改用 M 類", List.of())),
                new Case(PROP, in("promote", D0, null, null, null), new SiDecideCommand(PROP, "promote", D0, null, null, List.of())),
                new Case(PROP, in("decline-promote", D0, "風險太高", "風險過高", null),
                        new SiDecideCommand(PROP, "decline-promote", D0, "風險過高", "風險太高", List.of())),
                new Case(PROP, in("rollback", null, "太慢", null, null), new SiDecideCommand(PROP, "rollback", null, null, "太慢", List.of())),
                new Case(PROP, in("unblock", null, null, null, null), new SiDecideCommand(PROP, "unblock", null, null, null, List.of())),
                new Case(RUN, in("resume", null, "兩個壞窗已人工檢視", null, null),
                        new SiDecideCommand(RUN, "resume", null, null, "兩個壞窗已人工檢視", List.of())),
                new Case(PROP, in("ack-handoff", D0, null, null, null), new SiDecideCommand(PROP, "ack-handoff", D0, null, null, List.of())));

        for (Case c : cases) {
            assertThat(SiWriteGates.decide("admin", c.id(), c.input())).as("dkind=%s", c.input().dkind()).isEqualTo(c.expected());
        }
    }

    @Test
    void AT_950_7_1_theAckFlagOnlyAppearsOnPromoteAndFalseOrAbsentMeansNoFlag() {
        assertThat(SiWriteGates.decide("admin", PROP, in("promote", D0, null, null, true)).flags()).containsExactly("unverified_ack");
        assertThat(SiWriteGates.decide("admin", PROP, in("promote", D0, null, null, false)).flags()).isEmpty();
        assertThat(SiWriteGates.decide("admin", PROP, in("approve", D0, null, null, false)).flags())
                .as("非 promote 帶 false 不是違規").isEmpty();
    }

    @Test
    void AT_950_7_1_reasonsAreStrippedAndCountedInCodePointsWithFullWidthAndSurrogatePairsAllowed() {
        SiDecideCommand stripped = SiWriteGates.decide("admin", PROP, in("rollback", null, "   理由，含全形標點：「引號」。   ", null, null));
        String emoji500 = repeat("😀", 250) + repeat("字", 250);                  // 500 個 code point（750 個 UTF-16 單位之外的位元組更多）
        SiDecideCommand longest = SiWriteGates.decide("admin", PROP, in("rollback", null, emoji500, null, null));

        assertThat(stripped.reason()).as("前後空白被剝除").isEqualTo("理由，含全形標點：「引號」。");
        assertThat(longest.reason().codePointCount(0, longest.reason().length())).as("代理對字元算一個 code point").isEqualTo(500);
        assertThat(longest.reason().length()).isGreaterThan(500);
    }

    // ── AT-950-7-2：觀察與關閉的有效組合 ────────────────────────────────────────────────────

    @Test
    void AT_950_7_2_validObservationsPassWithTrimmedFieldsAndTheGuardFaceCarriesItsExposure() {
        SiObservationCommand base = SiWriteGates.observation("admin", validObs());
        SiObservationCommand padded = SiWriteGates.observation("admin", obs("  Console・自我進化頁  ", " 待入帳徽章在入帳後仍顯示",
                "AgentConsole/frontend/components/domain/si/SiView.tsx:88 ", "bug", "P3", "產品", null, false, null));
        SiObservationCommand guard = SiWriteGates.observation("admin", obs("Console・自我進化頁", "待入帳徽章在入帳後仍顯示",
                "AgentConsole/frontend/components/domain/si/SiView.tsx:88", "tooling", "P2", "守衛", "b", true, null));
        SiObservationCommand correcting = SiWriteGates.observation("admin", obs("Console・自我進化頁", "待入帳徽章在入帳後仍顯示",
                "AgentConsole/frontend/components/domain/si/SiView.tsx:88", "bug", "P3", "產品", null, false, " OBS-SI-001 "));

        assertThat(padded).as("字串欄已 trim").isEqualTo(base);
        assertThat(base.exposure()).isNull();
        assertThat(base.corrects()).isNull();
        assertThat(guard.exposure()).isEqualTo("b");
        assertThat(guard.externalDerived()).isTrue();
        assertThat(correcting.corrects()).isEqualTo("OBS-SI-001");
        for (String exposure : List.of("a", "b", "c", "無")) {
            assertThat(SiWriteGates.observation("admin", obs("c", "s", "e/x.py:1", "doc", "P4", "守衛", exposure, false, null)).exposure())
                    .isEqualTo(exposure);
        }
    }

    @Test
    void AT_950_7_2_theSevenCloseTerminalsComposeTheirDispositionVerbatim() {
        Map<String, CloseInput> inputs = new java.util.LinkedHashMap<>();
        inputs.put("fixed@2b2b0b3d", new CloseInput("fixed", "2b2b0b3d", null));
        inputs.put("DEF-200-559", new CloseInput("def", "DEF-200-559", null));
        inputs.put("deferred：等 P3 輪", new CloseInput("deferred", null, "等 P3 輪"));
        inputs.put("retired：docs/06_quality/SelfImproving_Protocol/params.json",
                new CloseInput("retired", null, "docs/06_quality/SelfImproving_Protocol/params.json"));
        inputs.put("decided：夾具關閉", new CloseInput("decided", null, "夾具關閉"));
        inputs.put("merged@OBS-SI-001", new CloseInput("merged", "OBS-SI-001", null));
        inputs.put("proposed@PROP-SI-004", new CloseInput("proposed", "PROP-SI-004", null));

        inputs.forEach((disposition, input) -> {
            SiCloseCommand command = SiWriteGates.close("admin", OBS, input);

            assertThat(command).as(input.terminal()).isEqualTo(new SiCloseCommand(OBS, disposition));
        });
        assertThat(SiWriteGates.close("admin", OBS, new CloseInput(" fixed ", " 2b2b0b3d ", null)).disposition())
                .as("終值與 ref 先 trim 再判").isEqualTo("fixed@2b2b0b3d");
        assertThat(SiWriteGates.close("admin", OBS, new CloseInput("fixed", repeat("a", 40), null)).disposition())
                .as("ref 恰 40 碼").isEqualTo("fixed@" + repeat("a", 40));
        assertThat(SiWriteGates.close("admin", OBS, new CloseInput("fixed", repeat("a", 7), null)).disposition())
                .as("ref 恰 7 碼").isEqualTo("fixed@" + repeat("a", 7));
    }

    // ── AT-950-7-E-1：decide 違規 ───────────────────────────────────────────────────────────

    private static void expectFields(String label, UnprocessableException e, String... fields) {
        assertThat(fieldsOf(e)).as(label).containsExactlyInAnyOrder(fields);
    }

    @Test
    void AT_950_7_E_1_forbiddenFieldsMissingFieldsAndWrongIdTypesAreAllReported() {
        // 禁止欄
        for (String verb : List.of("rollback", "unblock", "resume")) {
            String id = "resume".equals(verb) ? RUN : PROP;
            DecideInput input = in(verb, D0, "rollback".equals(verb) || "resume".equals(verb) ? "理由" : null, null, null);
            expectFields("digest 出現在 " + verb, rejected(() -> SiWriteGates.decide("admin", id, input)), "digest");
        }
        for (String verb : List.of("approve", "promote", "ack-handoff", "unblock")) {
            DecideInput input = in(verb, "unblock".equals(verb) ? null : D0, "不該有理由", null, null);
            expectFields("reason 出現在 " + verb, rejected(() -> SiWriteGates.decide("admin", PROP, input)), "reason");
        }
        for (String verb : List.of("approve", "promote", "ack-handoff", "rollback", "unblock")) {
            DecideInput input = in(verb, List.of("approve", "promote", "ack-handoff").contains(verb) ? D0 : null,
                    "rollback".equals(verb) ? "理由" : null, "證據不足", null);
            expectFields("reasonClass 出現在 " + verb, rejected(() -> SiWriteGates.decide("admin", PROP, input)), "reasonClass");
        }
        expectFields("resume 帶 reasonClass", rejected(() -> SiWriteGates.decide("admin", RUN, in("resume", null, "理由", "未說明", null))),
                "reasonClass");
        for (String verb : List.of("approve", "reject", "return", "decline-promote", "rollback", "unblock", "resume", "ack-handoff")) {
            DecideInput input = in(verb, null, null, null, true);
            UnprocessableException e = rejected(() -> SiWriteGates.decide("admin", "resume".equals(verb) ? RUN : PROP, input));
            assertThat(fieldsOf(e)).as("unverifiedAck 為 true 於 %s", verb).contains("unverifiedAck");
        }
        // 缺必填欄：一次全列
        expectFields("approve 缺 digest", rejected(() -> SiWriteGates.decide("admin", PROP, in("approve", null, null, null, null))), "digest");
        expectFields("reject 缺三項", rejected(() -> SiWriteGates.decide("admin", PROP, in("reject", null, null, null, null))),
                "digest", "reason", "reasonClass");
        expectFields("rollback 缺 reason", rejected(() -> SiWriteGates.decide("admin", PROP, in("rollback", null, null, null, null))), "reason");
        expectFields("resume 缺 reason", rejected(() -> SiWriteGates.decide("admin", RUN, in("resume", null, null, null, null))), "reason");
        // 多項違規一次全列，不只回報第一項
        UnprocessableException many = rejected(() -> SiWriteGates.decide("bad name", PROP, in("approve", "sha256:XYZ", "多餘", "證據不足", true)));
        expectFields("approve 的四項加帳號名", many, "user", "digest", "reason", "reasonClass", "unverifiedAck");
        assertThat(many.reason()).isEqualTo("invalid_request");
        assertThat(many.details()).containsKey("violations");
        assertThat(many.details().get("violations")).asInstanceOf(org.assertj.core.api.InstanceOfAssertFactories.LIST).hasSize(5)
                .allSatisfy(item -> assertThat(item).asInstanceOf(org.assertj.core.api.InstanceOfAssertFactories.MAP)
                        .containsOnlyKeys("field", "message"));
        assertThat(many.violations()).allSatisfy(v -> assertThat(v.message()).isNotBlank());
    }

    @Test
    void AT_950_7_E_1_digestReasonReasonClassAndDkindValuesAreChecked() {
        for (String digest : List.of("sha256:ABC", "sha256:" + repeat("a", 63), "sha256:" + repeat("a", 65),
                "sha256:" + repeat("A", 64), repeat("a", 64), "sha1:" + repeat("a", 64), "sha256:" + repeat("g", 64), " ", "")) {
            expectFields("digest=" + digest, rejected(() -> SiWriteGates.decide("admin", PROP, in("approve", digest, null, null, null))),
                    "digest");
        }
        assertThat(SiWriteGates.decide("admin", PROP, in("approve", "  " + D0 + "  ", null, null, null)).digest()).as("digest 先 trim").isEqualTo(D0);

        for (String reason : List.of("   ", "第一行\n第二行", "含\rCR", "含\tTAB", "含\0NUL", "含\u007fDEL", "尾端換行\n", repeat("字", 501),
                repeat("😀", 501))) {
            expectFields("reason=" + reason.length(), rejected(() -> SiWriteGates.decide("admin", PROP, in("rollback", null, reason, null, null))),
                    "reason");
        }
        assertThat(SiWriteGates.decide("admin", PROP, in("rollback", null, repeat("字", 500), null, null)).reason()).as("恰 500 個").hasSize(500);
        expectFields("孤立高代理", rejected(() -> SiWriteGates.decide("admin", PROP, in("rollback", null, "壞\uD83D字", null, null))), "reason");
        expectFields("孤立低代理", rejected(() -> SiWriteGates.decide("admin", PROP, in("rollback", null, "壞\uDE00字", null, null))), "reason");

        expectFields("reasonClass 不在七值", rejected(() -> SiWriteGates.decide("admin", PROP,
                in("reject", D0, "理由", "隨便", null))), "reasonClass");
        for (String reasonClass : List.of("證據不足", "風險過高", "工件類別錯", "已被涵蓋", "範圍外", "卡面不清", "未說明")) {
            assertThat(SiWriteGates.decide("admin", PROP, in("reject", D0, "理由", reasonClass, null)).reasonClass()).isEqualTo(reasonClass);
        }
        for (String dkind : new String[] {"approve-all", "APPROVE", "", "  ", null}) {
            expectFields("dkind=" + dkind, rejected(() -> SiWriteGates.decide("admin", PROP, in(dkind, D0, null, null, null))), "dkind");
        }
    }

    @Test
    void AT_950_7_E_1_theIdMustMatchTheVerbAndTheAccountNameItsDomain() {
        expectFields("resume 配 PROP", rejected(() -> SiWriteGates.decide("admin", PROP, in("resume", null, "理由", null, null))), "id");
        for (String verb : List.of("approve", "reject", "promote", "unblock")) {
            DecideInput input = in(verb, "unblock".equals(verb) ? null : D0, "reject".equals(verb) ? "理由" : null,
                    "reject".equals(verb) ? "未說明" : null, null);
            expectFields(verb + " 配 RUN", rejected(() -> SiWriteGates.decide("admin", RUN, input)), "id");
        }
        // id 格式：缺位數、小寫、前後空白、換行、非數字、其他前綴、null
        String shortProp = "PROP-SI-" + "04";
        for (String id : new String[] {shortProp, "prop-si-004", "PROP-SI-004 ", " PROP-SI-004", "PROP-SI-004\n", "PROP-SI-00a",
                "OBS-SI-004", "", null}) {
            expectFields("id=" + id, rejected(() -> SiWriteGates.decide("admin", id, in("approve", D0, null, null, null))), "id");
        }
        assertThat(SiWriteGates.decide("admin", FOUR_PROP, in("approve", D0, null, null, null)).subject()).as("四位數也合格").isEqualTo(FOUR_PROP);
        // dkind 本身不合時，id 只要是任一種合法 id 就不再另外回報
        expectFields("dkind 錯 id 對", rejected(() -> SiWriteGates.decide("admin", PROP, in("zzz", null, null, null, null))), "dkind");
        expectFields("dkind 錯 id 也錯", rejected(() -> SiWriteGates.decide("admin", "zzz", in("zzz", null, null, null, null))), "dkind", "id");

        for (String user : new String[] {"bad name", "", "名字", repeat("a", 65), "a/b", "a b", null, "a\n"}) {
            expectFields("user=" + user, rejected(() -> SiWriteGates.decide(user, PROP, in("approve", D0, null, null, null))), "user");
        }
        for (String user : new String[] {"admin", "ops_admin", "Admin", "a.b-c_9", repeat("a", 64)}) {
            assertThat(SiWriteGates.decide(user, PROP, in("approve", D0, null, null, null)).subject()).as("user=%s", user).isEqualTo(PROP);
        }
    }

    // ── AT-950-7-E-2：觀察違規 ──────────────────────────────────────────────────────────────

    private static ObservationInput withField(String field, String value) {
        return switch (field) {
            case "context" -> obs(value, "s", "e/x.py:1", "bug", "P3", "產品", null, false, null);
            case "symptom" -> obs("c", value, "e/x.py:1", "bug", "P3", "產品", null, false, null);
            default -> obs("c", "s", value, "bug", "P3", "產品", null, false, null);
        };
    }

    @Test
    void AT_950_7_E_2_everyObservationStringFieldRejectsBlankPipeControlsAndTooLongValues() {
        for (String field : List.of("context", "symptom", "evidence")) {
            for (String bad : List.of("   ", "含|豎線", "含\n換行", "含\r回車", "含\tTAB", "含\0NUL", "含\u007fDEL", repeat("字", 301))) {
                expectFields(field + "=" + bad.length(), rejected(() -> SiWriteGates.observation("admin", withField(field, bad))), field);
            }
            expectFields(field + " 為 null", rejected(() -> SiWriteGates.observation("admin", withField(field, null))), field);
            assertThat(SiWriteGates.observation("admin", withField(field, repeat("a", 300)))).as("%s 單欄恰 300", field).isNotNull();
        }
    }

    @Test
    void AT_950_7_E_2_theUtf8ByteSumOfTheThreeFieldsIsCappedAtSevenHundredAndCountedInBytesNotCharacters() {
        ObservationInput exactly700 = obs(repeat("a", 300), repeat("b", 300), repeat("c", 100), "bug", "P3", "產品", null, false, null);
        ObservationInput over701 = obs(repeat("a", 300), repeat("b", 300), repeat("c", 101), "bug", "P3", "產品", null, false, null);
        ObservationInput cjk = obs(repeat("字", 78), repeat("字", 78), repeat("字", 78), "bug", "P3", "產品", null, false, null);   // 各 78 字、共 702 位元組
        ObservationInput cjkOk = obs(repeat("字", 78), repeat("字", 78), repeat("字", 77) + "a", "bug", "P3", "產品", null, false, null);   // 234＋234＋232＝700

        assertThat(SiWriteGates.observation("admin", exactly700)).as("恰 700 通過").isNotNull();
        expectFields("701", rejected(() -> SiWriteGates.observation("admin", over701)), "context", "symptom", "evidence");
        expectFields("CJK 702 位元組", rejected(() -> SiWriteGates.observation("admin", cjk)), "context", "symptom", "evidence");
        assertThat(SiWriteGates.observation("admin", cjkOk)).as("CJK 恰 700 位元組通過（以位元組計、不是字元）").isNotNull();
        assertThat(rejected(() -> SiWriteGates.observation("admin", over701)).violations().get(0).message()).contains("701").contains("700");
    }

    @Test
    void AT_950_7_E_2_enumsGuardExposureCorrectsAndExternalDerivedAreChecked() {
        ObservationInput v = validObs();
        expectFields("category", rejected(() -> SiWriteGates.observation("admin", obs(v.context(), v.symptom(), v.evidence(), "oops", "P3", "產品", null, false, null))), "category");
        expectFields("severity", rejected(() -> SiWriteGates.observation("admin", obs(v.context(), v.symptom(), v.evidence(), "bug", "P5", "產品", null, false, null))), "severity");
        expectFields("face", rejected(() -> SiWriteGates.observation("admin", obs(v.context(), v.symptom(), v.evidence(), "bug", "P3", "未知", null, false, null))), "face");
        expectFields("exposure 不在列舉", rejected(() -> SiWriteGates.observation("admin", obs(v.context(), v.symptom(), v.evidence(), "bug", "P3", "守衛", "z", false, null))), "exposure");
        expectFields("守衛缺 exposure", rejected(() -> SiWriteGates.observation("admin", obs(v.context(), v.symptom(), v.evidence(), "bug", "P2", "守衛", null, false, null))), "exposure");
        expectFields("非守衛帶 exposure", rejected(() -> SiWriteGates.observation("admin", obs(v.context(), v.symptom(), v.evidence(), "bug", "P3", "產品", "a", false, null))), "exposure");
        expectFields("externalDerived 缺", rejected(() -> SiWriteGates.observation("admin", obs(v.context(), v.symptom(), v.evidence(), "bug", "P3", "產品", null, null, null))), "externalDerived");
        for (String corrects : new String[] {obsId("01"), "obs-si-001", "PROP-SI-001", obsId("00a"), " ", "OBS-SI-001 \n"}) {
            expectFields("corrects=" + corrects, rejected(() -> SiWriteGates.observation("admin", obs(v.context(), v.symptom(), v.evidence(), "bug", "P3", "產品", null, false, corrects))), "corrects");
        }
        assertThat(SiWriteGates.observation("admin", obs(v.context(), v.symptom(), v.evidence(), "bug", "P3", "產品", null, false, FOUR_OBS)).corrects())
                .as("四位數也合格").isEqualTo(FOUR_OBS);
        UnprocessableException all = rejected(() -> SiWriteGates.observation("bad name", obs(" ", "含|豎線", null, "x", "y", "z", "q", null, "bad")));
        expectFields("一次全列", all, "user", "context", "symptom", "evidence", "category", "severity", "face", "exposure", "externalDerived", "corrects");
    }

    // ── AT-950-7-E-3：關閉違規 ──────────────────────────────────────────────────────────────

    @Test
    void AT_950_7_E_3_closeRejectsOpenUnknownTerminalsAndEveryRefAndTextViolation() {
        expectFields("open", rejected(() -> SiWriteGates.close("admin", OBS, new CloseInput("open", null, null))), "terminal");
        assertThat(rejected(() -> SiWriteGates.close("admin", OBS, new CloseInput(" open ", null, null))).violations().get(0).message()).contains("open");
        for (String terminal : new String[] {"closed", "FIXED", "", null}) {
            expectFields("terminal=" + terminal, rejected(() -> SiWriteGates.close("admin", OBS, new CloseInput(terminal, "2b2b0b3d", null))), "terminal");
        }
        // ref 類缺 ref
        for (String terminal : List.of("fixed", "def", "merged", "proposed")) {
            expectFields(terminal + " 缺 ref", rejected(() -> SiWriteGates.close("admin", OBS, new CloseInput(terminal, null, null))), "ref");
        }
        // ref 格式
        Map<String, List<String>> badRefs = Map.of(
                "fixed", List.of("abc123", repeat("a", 41), "2b2b0b3g", "2B2B0B3D", "2b2b 0b3d"),
                "def", List.of("DEF-200", "DEF-200-", "def-200-559", "DEF-x-1", "DEF-200-559-1"),
                "merged", List.of("PROP-SI-004", obsId("01"), "obs-si-001"),
                "proposed", List.of("OBS-SI-001", "PROP-SI-04", "prop-si-004"));
        badRefs.forEach((terminal, refs) -> refs.forEach(ref ->
                expectFields(terminal + " ref=" + ref, rejected(() -> SiWriteGates.close("admin", OBS, new CloseInput(terminal, ref, null))), "ref")));
        // text 類缺 text、多帶 ref；ref 類多帶 text
        for (String terminal : List.of("deferred", "retired", "decided")) {
            expectFields(terminal + " 缺 text", rejected(() -> SiWriteGates.close("admin", OBS, new CloseInput(terminal, null, null))), "text");
            expectFields(terminal + " 帶 ref", rejected(() -> SiWriteGates.close("admin", OBS, new CloseInput(terminal, "2b2b0b3d", "文字"))), "ref");
        }
        expectFields("fixed 帶 text", rejected(() -> SiWriteGates.close("admin", OBS, new CloseInput("fixed", "2b2b0b3d", "多餘"))), "text");
        // text 內容
        for (String text : List.of("含|豎線", "含\n換行", "含\0NUL", "   ", "之後再看", "晚點，之後再看吧", repeat("字", 121))) {
            expectFields("text=" + text.length(), rejected(() -> SiWriteGates.close("admin", OBS, new CloseInput("decided", null, text))), "text");
        }
        assertThat(SiWriteGates.close("admin", OBS, new CloseInput("decided", null, repeat("字", 120))).disposition())
                .as("恰 120 個字元通過").isEqualTo("decided：" + repeat("字", 120));
        // 路徑 id
        for (String id : new String[] {obsId("05"), "obs-si-005", "PROP-SI-005", "OBS-SI-005 ", "", null}) {
            expectFields("id=" + id, rejected(() -> SiWriteGates.close("admin", id, new CloseInput("fixed", "2b2b0b3d", null))), "id");
        }
        expectFields("帳號名", rejected(() -> SiWriteGates.close("bad name", OBS, new CloseInput("fixed", "2b2b0b3d", null))), "user");
    }

    @Test
    void AT_950_7_E_3_theSameObservationViolationsComeOutForObsAddAndValidateBecauseTheyShareOneGate() {
        ObservationInput bad = obs("   ", "含|豎線", repeat("字", 301), "x", "P3", "守衛", null, null, "bad");

        UnprocessableException first = rejected(() -> SiWriteGates.observation("admin", bad));
        UnprocessableException second = rejected(() -> SiWriteGates.observation("admin", bad));

        assertThat(second.violations()).isEqualTo(first.violations());
        assertThat(first.violations()).hasSizeGreaterThanOrEqualTo(6);
    }
}
