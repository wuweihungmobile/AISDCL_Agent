package com.aisdlc.console.application.service;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * traceId 的 MDC 約定（契約 §0.4 第 6 點，C-12）。為什麼重要：背景執行緒（事件消費者、啟動對帳）借用 MDC 把「該 run 的 traceId」
 * 帶給出站的 Bridge 呼叫；借完必須還原，否則在執行緒池裡跑的下一個任務會掛著上一個 run 的 traceId，Bridge 日誌就串錯人。
 */
class TraceIdsTest {

    @AfterEach
    void clean() {
        MDC.remove(TraceIds.MDC_KEY);
    }

    @Test
    void theKeyIsTheOneTheRequestFilterWrites() {
        assertThat(TraceIds.MDC_KEY).isEqualTo("traceId");
    }

    @Test
    void currentIsWhateverTheThreadsMdcHoldsAndNullWhenThereIsNone() {
        assertThat(TraceIds.current()).isNull();

        MDC.put("traceId", "t-1");

        assertThat(TraceIds.current()).isEqualTo("t-1");
    }

    @Test
    void withinSetsTheTraceIdForTheActionAndRemovesItAfterwardsWhenThereWasNone() {
        List<String> inside = new ArrayList<>();

        String result = TraceIds.within("run-trace", () -> {
            inside.add(TraceIds.current());
            return "value";
        });

        assertThat(result).isEqualTo("value");
        assertThat(inside).containsExactly("run-trace");
        assertThat(TraceIds.current()).isNull();
    }

    @Test
    void withinRestoresThePreviousValueEvenWhenTheActionThrows() {
        MDC.put("traceId", "caller");

        assertThatThrownBy(() -> TraceIds.within("run-trace", () -> {
            throw new IllegalStateException("boom");
        })).isInstanceOf(IllegalStateException.class).hasMessage("boom");

        assertThat(TraceIds.current()).isEqualTo("caller");
    }

    @Test
    void theRunnableOverloadWorksTheSameWay() {
        List<String> inside = new ArrayList<>();
        MDC.put("traceId", "caller");

        TraceIds.within("run-trace", () -> {
            inside.add(TraceIds.current());
        });

        assertThat(inside).containsExactly("run-trace");
        assertThat(TraceIds.current()).isEqualTo("caller");
    }
}
