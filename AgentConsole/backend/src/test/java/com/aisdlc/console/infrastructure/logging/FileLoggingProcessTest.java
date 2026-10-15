package com.aisdlc.console.infrastructure.logging;

import com.aisdlc.logprobe.LogProbeApp;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 檔案日誌的端到端驗證（契約附錄 D.2；C-16）：<b>真的起一個 Spring Boot（獨立 JVM、真實的 application.yml 與 spring.factories）</b>，
 * 看 {@code LOG_DIR} 有沒有值時日誌檔的有無與內容。為什麼重要：處理器有沒有被 Boot 呼叫、屬性有沒有被日誌系統採用，單元測試看不到——
 * 登記錯誤時症狀只是「容器裡沒有日誌檔」，而且沒有任何錯誤訊息。獨立 JVM 的理由見 {@link LogProbeApp}。
 */
class FileLoggingProcessTest {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final TypeReference<Map<String, Object>> OBJECT = new TypeReference<>() { };

    @TempDir
    Path logDir;
    @TempDir
    Path workDir;
    @TempDir
    Path scratch;

    private record Outcome(int exit, String console) {
    }

    /** 以目前測試 JVM 的 classpath 起 {@link LogProbeApp}（classpath 超過 Windows 的命令列長度上限，所以走 {@code @argfile}）。 */
    private Outcome runProbe(Map<String, String> environment, String... applicationArgs)
            throws IOException, InterruptedException {
        Path argFile = scratch.resolve("java.args");
        Files.writeString(argFile, "-cp \"" + System.getProperty("java.class.path").replace("\\", "\\\\") + "\"\n",
                StandardCharsets.UTF_8);
        String java = ProcessHandle.current().info().command()
                .orElse(Path.of(System.getProperty("java.home"), "bin", "java").toString());
        List<String> command = new ArrayList<>(List.of(java, "@" + argFile, LogProbeApp.class.getName()));
        command.addAll(List.of(applicationArgs));
        Path console = scratch.resolve("console-" + System.nanoTime() + ".txt");
        ProcessBuilder builder = new ProcessBuilder(command).directory(workDir.toFile()).redirectErrorStream(true)
                .redirectOutput(console.toFile());
        builder.environment().keySet().removeIf(key -> key.equals("LOG_DIR") || key.startsWith("SPRING_"));
        builder.environment().putAll(environment);
        Process process = builder.start();
        if (!process.waitFor(120, TimeUnit.SECONDS)) {
            process.destroyForcibly();
            throw new AssertionError("探針 120 秒內沒有結束：" + Files.readString(console, StandardCharsets.UTF_8));
        }
        return new Outcome(process.exitValue(), Files.readString(console, StandardCharsets.UTF_8));
    }

    private static List<Map<String, Object>> jsonLines(Path file) throws IOException {
        List<Map<String, Object>> lines = new ArrayList<>();
        for (String line : Files.readAllLines(file, StandardCharsets.UTF_8)) {
            if (!line.isBlank()) {
                lines.add(JSON.readValue(line, OBJECT));
            }
        }
        return lines;
    }

    private static Map<String, Object> lineWith(List<Map<String, Object>> lines, String message) {
        return lines.stream().filter(l -> message.equals(l.get("message"))).findFirst()
                .orElseThrow(() -> new AssertionError("日誌檔裡找不到訊息 " + message + "：" + lines));
    }

    @Test
    void withALogDirTheServiceWritesJsonLinesToConsoleLogAndTheConsoleOutputIsUnchanged() throws Exception {
        Outcome run = runProbe(Map.of("LOG_DIR", logDir.toString()));

        assertThat(run.exit()).as(run.console()).isZero();
        Path file = logDir.resolve("console.log");
        assertThat(file).as("${LOG_DIR}/console.log").exists();
        List<Map<String, Object>> lines = jsonLines(file);
        assertThat(lines).as("每一行都是一個 JSON 物件（jsonLines 逐行解析，不是 JSON 就會丟例外）").isNotEmpty();

        Map<String, Object> withTrace = lineWith(lines, LogProbeApp.LINE_WITH_TRACE);
        assertThat(withTrace).containsEntry("level", "INFO").containsEntry("logger_name", "probe")
                .as("MDC 的 traceId 成為 JSON 欄位（NFR-9.4-04：日誌含 traceId 串聯）")
                .containsEntry("traceId", LogProbeApp.TRACE_ID);
        Map<String, Object> withoutTrace = lineWith(lines, LogProbeApp.LINE_WITHOUT_TRACE);
        assertThat(withoutTrace).containsEntry("level", "WARN").doesNotContainKey("traceId");

        assertThat(run.console()).as("console 輸出照舊：純文字，不是 JSON")
                .contains(LogProbeApp.LINE_WITH_TRACE).contains("[traceId=" + LogProbeApp.TRACE_ID + "]")
                .doesNotContain("\"logger_name\"");
    }

    @Test
    void withoutALogDirNoLogFileIsWrittenAnywhereAndTheConsoleStillShowsTheLogs() throws Exception {
        Outcome run = runProbe(Map.of());

        assertThat(run.exit()).as(run.console()).isZero();
        assertThat(workDir).as("工作目錄（程序的 cwd）沒有任何檔案").isEmptyDirectory();
        assertThat(logDir).as("沒設 LOG_DIR：不會有人去動別的目錄").isEmptyDirectory();
        assertThat(run.console()).contains(LogProbeApp.LINE_WITH_TRACE).contains(LogProbeApp.LINE_WITHOUT_TRACE);
    }

    @Test
    void anExplicitLoggingFileNameBeatsTheDefaultsTheProcessorAdds() throws Exception {
        Path custom = logDir.resolve("custom.log");

        Outcome run = runProbe(Map.of("LOG_DIR", logDir.toString()), "--logging.file.name=" + custom);

        assertThat(run.exit()).as(run.console()).isZero();
        assertThat(custom).exists();
        assertThat(logDir.resolve("console.log")).as("部署者明確指定檔名：預設的 console.log 不出現").doesNotExist();
        assertThat(lineWith(jsonLines(custom), LogProbeApp.LINE_WITH_TRACE)).containsEntry("traceId",
                LogProbeApp.TRACE_ID);
    }
}
