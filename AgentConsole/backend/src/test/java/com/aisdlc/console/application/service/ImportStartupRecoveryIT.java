package com.aisdlc.console.application.service;

import com.aisdlc.console.support.AbstractApiIT;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.core.annotation.AnnotatedElementUtils;

import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 啟動復原（契約 §1.1.3 的失敗語意延伸）。為什麼重要：{@code parse} 是同步呼叫，PARSING 只存在於「處理該請求的執行緒」活著的期間；
 * 行程在解析途中重啟或當機，資料庫裡就會留下永遠的 PARSING——之後再 parse 回 409「解析中」、reject 也回 409，
 * 這筆記錄就死了、使用者只能重新貼一次。console-api 是單一實例，所以啟動完成時殘留的 PARSING 一律退回 UPLOADED。
 */
class ImportStartupRecoveryIT extends AbstractApiIT {

    @Autowired
    private ImportStartupRecovery recovery;

    private String record(String status) {
        String id = api.post(operator(), "/api/v1/import/text", Map.of("content", "做一個待辦清單")).id();
        jdbc.update("update console.import_records set status = ? where id = ?::uuid", status, id);
        return id;
    }

    private String statusOf(String id) {
        return jdbc.queryForObject("select status from console.import_records where id = ?::uuid", String.class, id);
    }

    @Test
    void recordsStuckInParsingGoBackToUploadedAndEveryOtherStatusIsLeftAlone() {
        String stuckOne = record("PARSING");
        String stuckTwo = record("PARSING");
        String uploaded = record("UPLOADED");
        String parsed = record("PARSED");
        String reviewing = record("REVIEWING");
        String imported = record("IMPORTED");
        String rejected = record("REJECTED");

        recovery.resetStaleParsing();

        assertThat(statusOf(stuckOne)).isEqualTo("UPLOADED");
        assertThat(statusOf(stuckTwo)).isEqualTo("UPLOADED");
        assertThat(statusOf(uploaded)).isEqualTo("UPLOADED");
        assertThat(statusOf(parsed)).isEqualTo("PARSED");
        assertThat(statusOf(reviewing)).isEqualTo("REVIEWING");
        assertThat(statusOf(imported)).isEqualTo("IMPORTED");
        assertThat(statusOf(rejected)).isEqualTo("REJECTED");
    }

    @Test
    void aRecoveredRecordIsUsableAgainWhereItWasDeadBefore() {
        String id = record("PARSING");
        assertThat(api.post(operator(), "/api/v1/import/" + id + "/reject").status())
                .as("復原前：解析中不可放棄").isEqualTo(409);

        recovery.resetStaleParsing();

        assertThat(api.post(operator(), "/api/v1/import/" + id + "/reject").status()).isEqualTo(200);
    }

    @Test
    void recoveryKeepsTheLastGateErrorsAndAnyPreviousResultOfTheRecord() {
        String id = record("PARSING");
        jdbc.update("update console.import_records set parse_path = 'LLM', last_parse_errors = "
                + "'[{\"gate\":\"max_steps\",\"detail\":\"x\"}]'::jsonb where id = ?::uuid", id);

        recovery.resetStaleParsing();

        Map<String, Object> row = jdbc.queryForMap("select parse_path, last_parse_errors::text as errors from "
                + "console.import_records where id = ?::uuid", id);
        assertThat(row).containsEntry("parse_path", "LLM");
        assertThat(String.valueOf(row.get("errors"))).contains("max_steps");
    }

    @Test
    void runningItTwiceOrWithNothingToDoIsHarmless() {
        recovery.resetStaleParsing();
        String id = record("PARSING");
        recovery.resetStaleParsing();
        recovery.resetStaleParsing();
        assertThat(statusOf(id)).isEqualTo("UPLOADED");
        assertThat(UUID.fromString(id)).isNotNull();
    }

    @Test
    void itIsWiredToRunOnceTheApplicationIsReady() throws Exception {
        Method method = ImportStartupRecovery.class.getDeclaredMethod("resetStaleParsing");
        // value 與 classes 是別名：用 Spring 的合併註解讀法才會看到統一的結果
        EventListener listener = AnnotatedElementUtils.findMergedAnnotation(method, EventListener.class);
        assertThat(listener).as("沒有掛在 ApplicationReadyEvent 上，啟動復原就永遠不會執行").isNotNull();
        assertThat(Arrays.asList(listener.classes())).containsExactly(ApplicationReadyEvent.class);
    }
}
