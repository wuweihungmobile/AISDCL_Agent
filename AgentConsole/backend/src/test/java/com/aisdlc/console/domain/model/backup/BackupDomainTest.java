package com.aisdlc.console.domain.model.backup;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 遮罩函式 {@link BackupMasker}（TCS-SysAdminBackup-20261027 R-BK-42、D-BK-T15；AT-BK-07-3-2、AT-BK-07-3-E-1）。為什麼重要：輸出尾段來自備份腳本，
 * 可能含連線字串、金鑰與權杖；遮罩有兩道（sidecar 的 perl 與 console-api 的這支），<b>兩邊必須對同一份探針檔產出逐字相同的輸出</b>——
 * 否則 API 回應與資料庫裡的 {@code detail} 會與 sidecar 寫的尾段不一致，或某一道漏遮就讓機密外洩。探針單一來源
 * {@code docker/pgbackrest/tests/fixtures/mask-probes.txt}（{@code BackupSidecarContractIT} 共讀，沒有第二份副本）。
 */
class BackupDomainTest {

    /** 一列探針：輸入行、機密片段（負向探針為空）、期望輸出。 */
    private record Probe(String input, String secret, String expected) {
    }

    private static List<Probe> probes() {
        Path file = Path.of("..", "docker", "pgbackrest", "tests", "fixtures", "mask-probes.txt");
        List<Probe> probes = new ArrayList<>();
        try {
            for (String line : Files.readAllLines(file, StandardCharsets.UTF_8)) {
                if (line.isEmpty() || line.startsWith("#")) {
                    continue;
                }
                String[] columns = line.split("\t", -1);
                assertThat(columns).as("探針列必須恰三欄（輸入行、機密片段、期望輸出）：%s", line).hasSize(3);
                probes.add(new Probe(columns[0], columns[1], columns[2]));
            }
        } catch (IOException e) {
            throw new UncheckedIOException("讀不到遮罩探針檔 " + file.toAbsolutePath().normalize(), e);
        }
        return probes;
    }

    @Test
    void AT_BK_07_3_2_everyProbeLineGetsTheVerbatimExpectedOutputAndTheMaskerIsIdempotent() {
        List<Probe> probes = probes();
        assertThat(probes).as("防反空轉：探針檔至少 16 列（10 個正向、6 個負向）").hasSizeGreaterThanOrEqualTo(16);
        long positives = probes.stream().filter(p -> !p.secret().isEmpty()).count();
        assertThat(positives).as("正向探針").isGreaterThanOrEqualTo(10);

        for (Probe probe : probes) {
            String masked = BackupMasker.mask(probe.input());
            assertThat(masked).as("探針 %s 的輸出逐字等於期望", probe.input()).isEqualTo(probe.expected());
            if (probe.secret().isEmpty()) {
                assertThat(masked).as("負向探針原樣保留").isEqualTo(probe.input());
            } else {
                assertThat(masked).as("正向探針不含機密片段").doesNotContain(probe.secret());
            }
            assertThat(BackupMasker.mask(masked)).as("冪等：遮罩後再遮罩不變（%s）", probe.input()).isEqualTo(masked);
        }

        // 遮罩器只認形狀，不因 example／fake 之類的佔位詞放行
        assertThat(BackupMasker.mask("pass=example")).isEqualTo("pass=***");
        assertThat(BackupMasker.mask("password=fake")).isEqualTo("password=***");
        // 大小寫不分；鍵名可帶前後綴
        assertThat(BackupMasker.mask("AWS_Secret_Access_Key=fake-1")).isEqualTo("AWS_Secret_Access_Key=***");
        assertThat(BackupMasker.mask("TOKEN: fake-2")).isEqualTo("TOKEN: ***");
        // 逐行處理，CRLF 與多行文字：每行各自遮罩、行尾符號保留
        String multi = "start\r\npass=fake-pass-example-1\r\nmiddle ok\nkey=fake-key-example-5\r\nend";
        assertThat(BackupMasker.mask(multi)).isEqualTo("start\r\npass=***\r\nmiddle ok\nkey=***\r\nend");
        // 引號字串（含空白）整個換掉；值到空白、逗號、分號、& 為止
        assertThat(BackupMasker.mask("a=1 token=fake-3, b=2")).isEqualTo("a=1 token=***, b=2");
        assertThat(BackupMasker.mask("url?key=fake-4&x=1")).isEqualTo("url?key=***&x=1");
        // 結果長度由呼叫端另裁：本函式不截斷
        String longText = "line ok\n".repeat(1000) + "pass=fake-last-example";
        assertThat(BackupMasker.mask(longText)).endsWith("pass=***").hasSize(longText.length() - "fake-last-example".length() + 3);
    }

    @Test
    void AT_BK_07_3_E_1_nullBecomesEmptyTheTailCountsCodePointsAndMaskingComesBeforeTruncation() {
        assertThat(BackupMasker.mask(null)).isEmpty();
        assertThat(BackupMasker.tail(null, 2000)).isEmpty();
        assertThat(BackupMasker.maskedTail(null, 2000)).isEmpty();
        assertThat(BackupMasker.mask("")).isEmpty();
        assertThat(BackupMasker.mask("   \t  ")).isEqualTo("   \t  ");
        assertThat(BackupMasker.maskedTail("   ", 2000)).isEqualTo("   ");

        // 4000 個字元的長文：含全形字與 U+1F600（代理對），尾端有探針行；最後 2000 個「code point」，不是 UTF-16 單元，也不截出孤立代理
        String emoji = new String(Character.toChars(0x1F600));
        String body = ("字" + emoji).repeat(1999) + "\n" + "pass=fake-tail-example";
        assertThat(body.codePointCount(0, body.length())).isGreaterThan(2000);
        String tail = BackupMasker.maskedTail(body, 2000);
        assertThat(tail.codePointCount(0, tail.length())).as("以 code point 計恰 2000").isEqualTo(2000);
        assertThat(tail).endsWith("pass=***").doesNotContain("fake-tail-example");
        assertThat(tail.chars().filter(c -> Character.isSurrogate((char) c)).count() % 2).as("沒有孤立的代理字元").isZero();
        assertThat(Character.isLowSurrogate(tail.charAt(0))).as("尾段不以孤立的低代理開頭").isFalse();
        String masked = BackupMasker.mask(body);
        assertThat(masked).as("tail 就是遮罩後文字的最後 2000 個 code point").endsWith(tail);

        // 探針行位於第 1 行與最後一行、CRLF 與 LF 混用：各行獨立遮罩
        String mixed = "pass=fake-first-example\r\nmiddle line\nkey=fake-last-example";
        assertThat(BackupMasker.mask(mixed)).isEqualTo("pass=***\r\nmiddle line\nkey=***");

        // 順序鎖：機密跨過 2000 字元邊界時，「先遮罩、後取尾段」不洩漏；顛倒（先取尾段、後遮罩）會把被截斷的半個機密留在輸出裡
        String crossing = "key=fake-boundary-example-secret\n" + "x".repeat(1977);
        assertThat(crossing.length()).isGreaterThan(2000);
        String safe = BackupMasker.maskedTail(crossing, 2000);
        assertThat(safe).doesNotContain("fake-boundary").doesNotContain("ample-secret").contains("key=***");
        String reversedOrder = BackupMasker.mask(BackupMasker.tail(crossing, 2000));
        assertThat(reversedOrder).as("夾具有鑑別力：順序顛倒時被截斷的機密片段會漏出").contains("ample-secret");
    }
}
