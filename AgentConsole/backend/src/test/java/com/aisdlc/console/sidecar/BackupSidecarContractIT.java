package com.aisdlc.console.sidecar;

import org.junit.jupiter.api.Test;
import org.testcontainers.containers.Container.ExecResult;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.images.builder.ImageFromDockerfile;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.utility.MountableFile;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * sidecar 控制面的契約測試（Testcontainers Linux 容器加 stub；TCS-SysAdminBackup-20261027 §5.4 的 BS 載具）。
 * 涵蓋階一的二十四個 BS AT 全部，另加階二編號的 AT-BK-09-6-5（孤兒 results 清掃，S 包階一的匯出腳本已實作它）與一個補 AT
 * AT-BK-09-2-S-1（runner 啟動清逾 24 小時殘留請求檔；TCS 無此編號，見交卷偏離）。階二其餘 BS AT（runner 請求處理）要等 runner 實作請求撿取才能跑。
 *
 * <p>為什麼重要：sidecar 的 {@code job-run.sh} 包在<b>每一條排程備份的路徑上</b>（PRD R1：包裝出錯＝排程備份失敗），而控制面檔案（匯出、狀態、心跳）是 console-api 唯一的真相來源——
 * 包裝若吞掉 rc、把 stdout 與 stderr 混在一起、改了既有的 {@code .last_backup_status}，備份本身就被它弄壞；匯出若直接覆寫目的檔（非原子）、被 pgbackrest 卡住時連心跳一起停，
 * 畫面就會說謊（讀到半個檔、或誤報「控制面無回應」）；維護鎖若以「取鎖探測」判斷持有者，就會讓同時抵達的手動請求被誤判成 busy。這些行為必須在<b>真的 Linux 容器、真的 flock、
 * 真的 /proc/locks</b> 上驗，Windows 與 macOS 的 Git Bash 都驗不了。
 *
 * <p>容器：以 {@code pgvector/pgvector:pg18}（Debian bookworm，與 sidecar 映像同系；整套整合測試已在用的映像）加 jq 與 procps 預建，<b>同類別共用一個容器</b>
 * （靜態 {@code @Container}，各測試用各自的 {@code /tmp/ctl/<測試名>} 目錄，測試方法依序執行、不並行），<b>以非 root 的 {@code postgres} 執行</b>（與 sidecar 的 gosu postgres 同身分，
 * 檔案權限類斷言才有意義）；三支新腳本與 {@code pgbackrest-metrics.sh}、四支 stub 工作腳本、{@code pgbackrest}／{@code mc} stub 與夾具以 {@code withCopyFileToContainer} 放入；
 * {@code flock}、{@code mv} 兩支 stub 另放在 {@code /opt/sidecar/pathstubs}，只在 AT-BK-09-5-5、AT-BK-09-3-7 放進 PATH。請求、輸出目錄與鎖檔一律建在容器內本地檔案系統
 * （與生產的 {@code /run/backup-ctl}、{@code /backup-out} 同為容器的 overlay 根，才支援 {@code /proc/locks} 比對與 {@code chmod}）。
 * Docker 不在線時本類別<b>失敗</b>（不是 skip）：零測試與跳過都不算通過。
 *
 * <p>寫法紀律：腳本內以 {@code pkill -f}／{@code pgrep -f} 找行程一律用字元類（例 {@code sleep [8]}）——否則樣式字串會出現在父殼 {@code bash -c} 的命令列上而自己殺自己（或永遠比對到）；
 * 背景啟動的行程一律重導 stdout／stderr，否則 {@code execInContainer} 會一直等到它結束才返回。
 */
@Testcontainers
class BackupSidecarContractIT {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final Path SIDECAR = Path.of("..", "docker", "pgbackrest").toAbsolutePath().normalize();
    private static final Pattern ISO_Z = Pattern.compile("[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z");
    private static final String UUID_A = "11111111-1111-4111-8111-111111111111";

    // 容器壽命＝本類別（Testcontainers 的 JUnit 擴充在類別結束時關閉）；與 SharedRedis 同寫法抑制 resource 警告
    @SuppressWarnings("resource")
    @Container
    static final GenericContainer<?> CTL = new GenericContainer<>(new ImageFromDockerfile("aisdlc-backup-ctl-test", false)
            .withDockerfileFromBuilder(builder -> builder.from("pgvector/pgvector:pg18")
                    .run("apt-get update && apt-get install -y --no-install-recommends jq procps && rm -rf /var/lib/apt/lists/* "
                            + "&& mkdir -p /var/lib/pgbackrest /tmp/ctl && chown -R postgres:postgres /var/lib/pgbackrest /tmp/ctl")))
            .withCreateContainerCmdModifier(cmd -> cmd.withEntrypoint("sleep").withCmd("infinity").withUser("postgres"))
            .withCopyFileToContainer(script("scripts/job-run.sh"), "/opt/sidecar/scripts/job-run.sh")
            .withCopyFileToContainer(script("scripts/backup-ctl-export.sh"), "/opt/sidecar/scripts/backup-ctl-export.sh")
            .withCopyFileToContainer(script("scripts/backup-ctl-runner.sh"), "/opt/sidecar/scripts/backup-ctl-runner.sh")
            .withCopyFileToContainer(script("scripts/pgbackrest-metrics.sh"), "/opt/sidecar/scripts/pgbackrest-metrics.sh")
            .withCopyFileToContainer(script("crontab"), "/opt/sidecar/crontab")
            .withCopyFileToContainer(script("tests/stubs/backup-full.sh"), "/opt/sidecar/work/backup-full.sh")
            .withCopyFileToContainer(script("tests/stubs/backup-incr.sh"), "/opt/sidecar/work/backup-incr.sh")
            .withCopyFileToContainer(script("tests/stubs/pg_dump-offsite.sh"), "/opt/sidecar/work/pg_dump-offsite.sh")
            .withCopyFileToContainer(script("tests/stubs/verify-backup.sh"), "/opt/sidecar/work/verify-backup.sh")
            .withCopyFileToContainer(script("tests/stubs/_stub_job_common.sh"), "/opt/sidecar/work/_stub_job_common.sh")
            .withCopyFileToContainer(script("tests/stubs/pgbackrest"), "/opt/sidecar/stubs/pgbackrest")
            .withCopyFileToContainer(script("tests/stubs/mc"), "/opt/sidecar/stubs/mc")
            .withCopyFileToContainer(script("tests/stubs/flock"), "/opt/sidecar/pathstubs/flock")
            .withCopyFileToContainer(script("tests/stubs/mv"), "/opt/sidecar/pathstubs/mv")
            .withCopyFileToContainer(script("tests/fixtures/info-2repo.json"), "/opt/sidecar/fixtures/info-2repo.json")
            .withCopyFileToContainer(script("tests/fixtures/logical-2.json"), "/opt/sidecar/fixtures/logical-2.json")
            .withCopyFileToContainer(script("tests/fixtures/mask-probes.txt"), "/opt/sidecar/fixtures/mask-probes.txt");

    private static MountableFile script(String relative) {
        return MountableFile.forHostPath(SIDECAR.resolve(relative), 0755);
    }

    // ── 在容器內執行 ────────────────────────────────────────────────────────────────────────

    /** 一次 exec 的結果。 */
    private record Out(int rc, String out, String err) {
    }

    /**
     * 每個測試的前置：乾淨的 {@code /tmp/ctl/<name>}、環境變數的預設值（生產值指向本測試目錄）、PATH 前綴 stub 目錄（pgbackrest、mc）。
     * 先 chmod 再刪：上一次若留下唯讀目錄（AT-BK-09-3-5 的 chmod 555），rm -rf 才刪得掉。
     */
    private static String pre(String name) {
        return "D=/tmp/ctl/" + name + "; [ -d \"$D\" ] && chmod -R u+rwx \"$D\" 2> /dev/null; rm -rf \"$D\"; mkdir -p \"$D/out\" \"$D/req\" \"$D/lock\"; cd \"$D\" || exit 99; "
                + "export BACKUP_CTL_OUT_DIR=\"$D/out\" BACKUP_CTL_REQ_DIR=\"$D/req\" BACKUP_CTL_LOCK_FILE=\"$D/lock/maintenance.lock\" "
                + "BACKUP_CTL_SCRIPT_DIR=/opt/sidecar/work PATH=/opt/sidecar/stubs:$PATH; S=/opt/sidecar/scripts; ";
    }

    private static Out run(String name, String body) {
        try {
            ExecResult result = CTL.execInContainer("bash", "-c", pre(name) + body);
            return new Out(result.getExitCode(), result.getStdout(), result.getStderr());
        } catch (IOException e) {
            throw new IllegalStateException("容器內執行失敗", e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(e);
        }
    }

    /** 讀容器內 {@code /tmp/ctl/<name>/<relative>}。 */
    private static String readFile(String name, String relative) {
        try {
            ExecResult result = CTL.execInContainer("cat", "/tmp/ctl/" + name + "/" + relative);
            assertThat(result.getExitCode()).as("cat %s：%s", relative, result.getStderr()).isZero();
            return result.getStdout();
        } catch (IOException e) {
            throw new IllegalStateException(e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(e);
        }
    }

    /** 讀輸出目錄（{@code BACKUP_CTL_OUT_DIR}）內的檔。 */
    private static String cat(String name, String relativeToOut) {
        return readFile(name, "out/" + relativeToOut);
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> json(String text) {
        return (Map<String, Object>) JSON.readValue(text, Object.class);
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> map(Object value) {
        return (Map<String, Object>) value;
    }

    @SuppressWarnings("unchecked")
    private static List<Object> list(Object value) {
        return (List<Object>) value;
    }

    private static Object parse(String text) {
        return JSON.readValue(text, Object.class);
    }

    private static String fixture(String name) {
        try {
            return Files.readString(SIDECAR.resolve("tests/fixtures").resolve(name), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }

    private static String sourceWithoutComments(String relative) throws IOException {
        return String.join("\n", Files.readString(SIDECAR.resolve(relative), StandardCharsets.UTF_8).lines()
                .filter(line -> !line.strip().startsWith("#")).toList());
    }

    /** 以背景方式持鎖（命令形 flock -o，與 job-run.sh 同形）：先確保鎖檔存在，睡 0.5 秒讓持鎖者就位；重導輸出，exec 才不會等它。 */
    private static String holdLock(int seconds) {
        return "touch \"$D/lock/maintenance.lock\"; /usr/bin/flock -o \"$D/lock/maintenance.lock\" sleep " + seconds + " > /dev/null 2>&1 & sleep 0.5; ";
    }

    /** jobs/&lt;job&gt;.json 的「已結束」狀態：{@code last_success_at} 由參數決定。 */
    private static String finishedState(String job, String status, String successAt) {
        return "{\"schema_rev\":1,\"job\":\"" + job + "\",\"last\":{\"trigger\":\"scheduled\",\"status\":\"" + status + "\",\"rc\":0,\"reason\":null,"
                + "\"started_at\":\"2026-10-26T18:00:00Z\",\"finished_at\":\"2026-10-26T18:10:00Z\",\"detail_tail\":\"old\",\"note\":null},"
                + "\"last_success_at\":\"" + successAt + "\"}";
    }

    /** jobs/&lt;job&gt;.json 的「進行中」狀態：last_success_at 固定為 2026-10-26T18:10:00Z。 */
    private static String runningState(String job, String startedAt) {
        return "{\"schema_rev\":1,\"job\":\"" + job + "\",\"last\":{\"trigger\":\"scheduled\",\"status\":\"running\",\"rc\":null,\"reason\":null,"
                + "\"started_at\":\"" + startedAt + "\",\"finished_at\":null,\"detail_tail\":\"\",\"note\":null},\"last_success_at\":\"2026-10-26T18:10:00Z\"}";
    }

    /** results/&lt;id&gt;.json 的 running 形（階段二的 runner 寫「撿起」時的形狀）。 */
    private static String runningResults(String id, String type, String startedAt) {
        return "{\"schema_rev\":1,\"id\":\"" + id + "\",\"type\":\"" + type + "\",\"status\":\"running\",\"reason\":null,\"rc\":null,"
                + "\"started_at\":\"" + startedAt + "\",\"finished_at\":null,\"detail_tail\":\"\"}";
    }

    // ══════════════════════════════════════════════════════════════════════════════════════════
    // 匯出（backup-ctl-export.sh）
    // ══════════════════════════════════════════════════════════════════════════════════════════

    @Test
    void AT_BK_02_6_1_theExporterDecidesWhichRepoIsLocalFromTheEndpointHostAlone() {
        // endpoint → 「去埠號與括號的主機名|local」
        Map<String, String> expected = new LinkedHashMap<>();
        expected.put("minio:9000", "minio|true");
        expected.put("localhost:9000", "localhost|true");
        expected.put("127.0.0.1:9000", "127.0.0.1|true");
        expected.put("[::1]:9000", "::1|true");
        expected.put("host.docker.internal:9000", "host.docker.internal|true");
        expected.put("s3.amazonaws.com", "s3.amazonaws.com|false");
        expected.put("s3.ap-northeast-1.amazonaws.com:443", "s3.ap-northeast-1.amazonaws.com|false");
        expected.put("minio.example.internal:9000", "minio.example.internal|false");
        StringBuilder endpoints = new StringBuilder();
        expected.keySet().forEach(endpoint -> endpoints.append('\'').append(endpoint).append("' "));
        String script = "for ep in " + endpoints + "; do OFFSITE_S3_ENDPOINT=\"$ep\" bash $S/backup-ctl-export.sh; echo \"$ep|$(jq -c .repos out/export/info.json)\"; done";

        Out out = run("at_bk_02_6_1", script);

        assertThat(out.rc()).isZero();
        List<String> lines = out.out().lines().toList();
        assertThat(lines).as("八個端點各一行").hasSize(8);
        for (String line : lines) {
            int bar = line.indexOf('|');
            String endpoint = line.substring(0, bar);
            List<Object> repos = list(parse(line.substring(bar + 1)));
            String[] hostAndLocal = expected.get(endpoint).split("\\|");
            assertThat(repos).as(endpoint).hasSize(2);
            assertThat(map(repos.get(0))).as(endpoint + " repo1 恆為本地 posix").containsEntry("repo", 1).containsEntry("type", "posix")
                    .containsEntry("endpoint_host", null).containsEntry("local", true);
            assertThat(map(repos.get(1))).as(endpoint + " repo2").containsEntry("repo", 2).containsEntry("type", "s3")
                    .containsEntry("endpoint_host", hostAndLocal[0]).containsEntry("local", Boolean.parseBoolean(hostAndLocal[1]));
        }
    }

    @Test
    void AT_BK_03_4_1_theRetentionComesFromWhatPgBackRestReportsInEveryHelpForm() throws IOException {
        String script = "for form in a b c; do STUB_HELP_FORM=$form LOGICAL_BACKUP_RETENTION_DAYS=28 bash $S/backup-ctl-export.sh; "
                + "echo \"$form|$(jq -c .retention out/export/info.json)\"; done";

        Out out = run("at_bk_03_4_1", script);

        assertThat(out.rc()).isZero();
        Map<String, String> byForm = new LinkedHashMap<>();
        out.out().lines().forEach(line -> byForm.put(line.substring(0, 1), line.substring(2)));
        assertThat(byForm.get("a")).as("(a) full 單值套用全部 repo、diff 只有 repo1").isEqualTo("{\"repo1\":{\"full\":4,\"diff\":7},\"repo2\":{\"full\":4,\"diff\":null},\"logical_days\":28}");
        assertThat(byForm.get("b")).as("(b) 兩者皆逐 repo 列：各取各的").isEqualTo("{\"repo1\":{\"full\":4,\"diff\":7},\"repo2\":{\"full\":6,\"diff\":3},\"logical_days\":28}");
        assertThat(byForm.get("c")).as("(c) diff 沒有 repo2 列 ⇒ repo2.diff 為 null（未設）").isEqualTo("{\"repo1\":{\"full\":4,\"diff\":7},\"repo2\":{\"full\":4,\"diff\":null},\"logical_days\":28}");
        assertThat(sourceWithoutComments("scripts/backup-ctl-export.sh").lines().toList()).as("只取 pgBackRest 自報值，不自己讀 pgbackrest.conf（環境變數優先於 conf 的語意由「問 pgBackRest」達成）")
                .noneMatch(line -> line.contains("pgbackrest.conf") || line.contains("/etc/pgbackrest"));
    }

    @Test
    void AT_BK_03_4_2_anUnparsableRetentionIsNullNeverADefaultAndTheRestOfTheExportIsIntact() {
        String script = "for form in empty nonnumeric fail conflict; do STUB_HELP_FORM=$form bash $S/backup-ctl-export.sh; rc=$?; "
                + "echo \"$form|$rc|$(jq -c '[.ok, (.info|length), (.repos|length), .retention]' out/export/info.json)\"; done";

        Out out = run("at_bk_03_4_2", script);

        assertThat(out.rc()).isZero();
        assertThat(out.out().lines().toList()).as("每種不可解析的形態：匯出結束碼 0、其餘內容照常、retention 為 JSON null（不是物件、不填預設值）").containsExactly(
                "empty|0|[true,1,2,null]", "nonnumeric|0|[true,1,2,null]", "fail|0|[true,1,2,null]", "conflict|0|[true,1,2,null]");
    }

    @Test
    void AT_BK_04_4_1_theSweepTurnsARunningStateWithNoLockHolderIntoInterruptedAndKeepsTheLastSuccess() {
        String script = "mkdir -p out/export/jobs; printf '%s' '" + runningState("full", "2026-10-27T01:00:00Z") + "' > out/export/jobs/full.json; "
                + "bash $S/backup-ctl-export.sh; echo rc=$?; ls out/export/jobs";

        Out out = run("at_bk_04_4_1", script);

        assertThat(out.out().lines().toList()).as("結束碼 0、目錄內只有 full.json（原子寫：沒有殘留 .tmp）").containsExactly("rc=0", "full.json");
        Map<String, Object> state = json(cat("at_bk_04_4_1", "export/jobs/full.json"));
        Map<String, Object> last = map(state.get("last"));
        assertThat(last).containsEntry("status", "interrupted").containsEntry("reason", "interrupted").containsEntry("trigger", "scheduled");
        assertThat((String) last.get("finished_at")).matches(ISO_Z);
        assertThat(state).as("last_success_at 保持不變").containsEntry("last_success_at", "2026-10-26T18:10:00Z");
    }

    @Test
    void AT_BK_09_5_1_theExportIsAtomicNoReaderEverSeesAHalfWrittenFileAndEveryRoundReplacesTheInode() {
        String script = "export OFFSITE_S3_ENDPOINT=minio:9000 LOGICAL_BACKUP_RETENTION_DAYS=28; bash $S/backup-ctl-export.sh; "
                + "( for i in $(seq 1 300); do jq -e '.schema_rev==1' out/export/info.json > /dev/null 2>&1 || echo FAIL >> readfail; sleep 0.01; done ) & rd=$!; "
                + "for i in $(seq 1 10); do bash $S/backup-ctl-export.sh; stat -c %i out/export/info.json >> inodes; done; wait $rd; "
                + "echo \"fails=$(cat readfail 2> /dev/null | wc -l)\"; echo \"inodes=$(tr '\\n' ' ' < inodes)\"; echo \"files=$(ls out/export | tr '\\n' ' ')\"";

        Out out = run("at_bk_09_5_1", script);

        List<String> lines = out.out().lines().toList();
        assertThat(lines.get(0)).as("300 次 jq -e 全部成功（永遠看不到半個檔）").isEqualTo("fails=0");
        List<String> inodes = List.of(lines.get(1).substring("inodes=".length()).trim().split(" "));
        assertThat(inodes).hasSize(10);
        for (int i = 1; i < inodes.size(); i++) {
            assertThat(inodes.get(i)).as("第 %d 輪的 inode 異於前一輪（先寫 .tmp 再改名；直接 > 覆寫會保持同一 inode）", i + 1).isNotEqualTo(inodes.get(i - 1));
        }
        assertThat(lines.get(2)).as("目錄內沒有殘留 .tmp").doesNotContain(".tmp");
        Map<String, Object> info = json(cat("at_bk_09_5_1", "export/info.json"));
        assertThat(info.keySet()).containsExactly("schema_rev", "generated_at", "ok", "info", "retention", "repos");
        assertThat(info).containsEntry("schema_rev", 1).containsEntry("ok", true);
        assertThat((String) info.get("generated_at")).matches(ISO_Z);
        assertThat(info.get("info")).as("pgBackRest 原輸出逐值嵌入（含 64 位元 system-id）").isEqualTo(parse(fixture("info-2repo.json")));
        assertThat(info.get("retention")).isEqualTo(parse("{\"repo1\":{\"full\":4,\"diff\":7},\"repo2\":{\"full\":4,\"diff\":null},\"logical_days\":28}"));
        assertThat(info.get("repos")).isEqualTo(parse("[{\"repo\":1,\"type\":\"posix\",\"endpoint_host\":null,\"local\":true},"
                + "{\"repo\":2,\"type\":\"s3\",\"endpoint_host\":\"minio\",\"local\":true}]"));
    }

    @Test
    void AT_BK_09_5_2_theLogicalListIsThrottledAndAFailureWritesOkFalseWithoutAStaleOrPartialList() {
        String script = "bash $S/backup-ctl-export.sh; cp out/export/logical.json first.json; m1=$(stat -c %Y out/export/logical.json); sleep 1.2; "
                + "bash $S/backup-ctl-export.sh; m2=$(stat -c %Y out/export/logical.json); echo \"same=$([ \"$m1\" = \"$m2\" ] && echo yes || echo no)\"; "
                + "cmp -s first.json out/export/logical.json && echo identical=yes || echo identical=no; "
                + "STUB_MC_MODE=fail BACKUP_CTL_LOGICAL_MIN_SECONDS=0 bash $S/backup-ctl-export.sh; echo rc=$?";

        Out out = run("at_bk_09_5_2", script);

        assertThat(out.out().lines().toList()).as("第二次（<300 秒）不重寫；mc 失敗那次匯出結束碼仍為 0").containsExactly("same=yes", "identical=yes", "rc=0");
        Map<String, Object> failed = json(cat("at_bk_09_5_2", "export/logical.json"));
        assertThat(failed.keySet()).as("失敗：沒有 objects 鍵、不寫部分清單、不保留舊清單").containsExactly("schema_rev", "generated_at", "ok");
        assertThat(failed).containsEntry("ok", false);

        Out again = run("at_bk_09_5_2b", "bash $S/backup-ctl-export.sh");
        assertThat(again.rc()).isZero();
        Map<String, Object> ok = json(cat("at_bk_09_5_2b", "export/logical.json"));
        assertThat(ok.keySet()).containsExactly("schema_rev", "generated_at", "ok", "objects");
        assertThat(ok).containsEntry("ok", true);
        assertThat(ok.get("objects")).isEqualTo(parse("[{\"name\":\"aisdlc-20261025-183000.dump\",\"size\":1048576,\"modified\":\"2026-10-25T18:30:05Z\"},"
                + "{\"name\":\"aisdlc-20261026-183000.dump\",\"size\":1049600,\"modified\":\"2026-10-26T18:30:05Z\"}]"));
    }

    @Test
    void AT_BK_09_5_3_aSecondConcurrentExportReturnsAtOnceAndPgBackRestIsOnlyCalledOnce() {
        String script = "STUB_INFO_SLEEP=3 STUB_CALL_LOG=\"$D/calls.log\" bash $S/backup-ctl-export.sh & p1=$!; sleep 0.5; t0=$(date +%s%3N); "
                + "STUB_INFO_SLEEP=3 STUB_CALL_LOG=\"$D/calls.log\" bash $S/backup-ctl-export.sh; rc2=$?; t1=$(date +%s%3N); wait $p1; "
                + "echo \"rc2=$rc2\"; echo \"elapsed=$((t1 - t0))\"; echo \"starts=$(grep -c ' start ' calls.log)\"; "
                + "jq -e '.schema_rev==1 and .ok==true' out/export/info.json > /dev/null && echo valid=yes";

        Out out = run("at_bk_09_5_3", script);

        List<String> lines = out.out().lines().toList();
        assertThat(lines.get(0)).as("後啟動者結束碼 0").isEqualTo("rc2=0");
        assertThat(Long.parseLong(lines.get(1).substring("elapsed=".length()))).as("不等待：立即結束（毫秒）").isLessThan(1500);
        assertThat(lines.get(2)).as("stub info 只被呼叫 1 次").isEqualTo("starts=1");
        assertThat(lines.get(3)).as("info.json 完整有效").isEqualTo("valid=yes");
    }

    @Test
    void AT_BK_09_5_4_theScheduleIsDerivedFromTheRealCrontabAndAnUnknownLineIsSkippedWithAWarning() {
        String script = "TZ=Asia/Taipei BACKUP_CTL_CRONTAB=/opt/sidecar/crontab bash $S/backup-ctl-export.sh schedule 2> warn1.txt; echo \"rc1=$?\"; cp out/export/schedule.json first.json; "
                + "cp /opt/sidecar/crontab \"$D/crontab.extra\"; printf '* * * * * echo hello-unknown\\n' >> \"$D/crontab.extra\"; "
                + "TZ=Asia/Taipei BACKUP_CTL_CRONTAB=\"$D/crontab.extra\" bash $S/backup-ctl-export.sh schedule 2> warn2.txt; echo \"rc2=$?\"; "
                + "echo \"warn1=$(grep -c WARN warn1.txt)\"; echo \"warn2=$(grep -c WARN warn2.txt)\"; echo \"leak=$(grep -c hello-unknown warn2.txt)\"";

        Out out = run("at_bk_09_5_4", script);

        assertThat(out.out().lines().toList()).as("真 crontab 零 WARN；多一條無法辨識的列恰一行 WARN 且不回顯該列內容").containsExactly("rc1=0", "rc2=0", "warn1=0", "warn2=1", "leak=0");
        Object expectedEntries = parse("[{\"job\":\"full\",\"cron\":\"0 2 * * 0\"},{\"job\":\"diff\",\"cron\":\"0 2 * * 1-6\"},"
                + "{\"job\":\"dump\",\"cron\":\"30 2 * * *\"},{\"job\":\"verify\",\"cron\":\"0 4 * * 3\"},{\"job\":\"expire\",\"cron\":\"0 3 * * *\"},"
                + "{\"job\":\"wal_clean\",\"cron\":\"30 3 * * *\"}]");
        for (String text : List.of(readFile("at_bk_09_5_4", "first.json"), cat("at_bk_09_5_4", "export/schedule.json"))) {
            Map<String, Object> schedule = json(text);
            assertThat(schedule.keySet()).containsExactly("schema_rev", "tz", "entries");
            assertThat(schedule).containsEntry("schema_rev", 1).containsEntry("tz", "Asia/Taipei");
            assertThat(schedule.get("entries")).as("六條，順序＝crontab 列序（無法辨識的列被略過、其餘照常）").isEqualTo(expectedEntries);
        }
    }

    @Test
    void AT_BK_09_5_E_1_whenPgBackRestFailsTheInfoFileSaysOkFalseAndNothingElse() {
        String script = "for mode in fail nonjson notarray; do STUB_INFO_MODE=$mode bash $S/backup-ctl-export.sh; rc=$?; "
                + "echo \"$mode|$rc|$(jq -c 'keys_unsorted' out/export/info.json)|$(jq -r .ok out/export/info.json)\"; done";

        Out out = run("at_bk_09_5_e_1", script);

        assertThat(out.out().lines().toList()).as("三種失敗：結束碼 0、鍵恰為 schema_rev／generated_at／ok（無 info、retention、repos）、ok 為 false").containsExactly(
                "fail|0|[\"schema_rev\",\"generated_at\",\"ok\"]|false", "nonjson|0|[\"schema_rev\",\"generated_at\",\"ok\"]|false",
                "notarray|0|[\"schema_rev\",\"generated_at\",\"ok\"]|false");
    }

    // ══════════════════════════════════════════════════════════════════════════════════════════
    // 包裝（job-run.sh）
    // ══════════════════════════════════════════════════════════════════════════════════════════

    @Test
    void AT_BK_09_3_1_scheduledJobsWaitForEachOtherAndNeverOverlap() {
        String script = "export STUB_JOB_SLEEP=3 STUB_JOB_TIMELOG=\"$D/time.log\"; bash $S/job-run.sh full scheduled > full.out 2>&1 & p1=$!; sleep 1; "
                + "bash $S/job-run.sh diff scheduled > diff.out 2>&1; rc2=$?; wait $p1; rc1=$?; echo \"rc1=$rc1 rc2=$rc2\"; cat time.log; "
                + "jq -r '.last | .status + \"/\" + .trigger' out/export/jobs/full.json out/export/jobs/diff.json";

        Out out = run("at_bk_09_3_1", script);

        List<String> lines = out.out().lines().toList();
        assertThat(lines.get(0)).isEqualTo("rc1=0 rc2=0");
        Map<String, Long> times = new LinkedHashMap<>();
        lines.stream().filter(line -> line.contains(" start ") || line.contains(" end ")).forEach(line -> {
            String[] parts = line.split(" ");
            times.put(parts[0] + " " + parts[1], Long.parseLong(parts[2]));
        });
        assertThat(times).as("四筆起迄記錄").containsOnlyKeys("full start", "full end", "diff start", "diff end");
        assertThat(times.get("diff start")).as("diff 的起點 ≥ full 的迄點（排程互相等待、不重疊）").isGreaterThanOrEqualTo(times.get("full end"));
        assertThat(lines.subList(lines.size() - 2, lines.size())).containsExactly("succeeded/scheduled", "succeeded/scheduled");
    }

    @Test
    void AT_BK_09_3_2_aManualRequestNeverWaitsForTheLockItAnswersBusyWithRc75AndTouchesNoState() {
        String script = holdLock(8) + "export STUB_JOB_RUNLOG=\"$D/runlog\"; t0=$(date +%s%3N); bash $S/job-run.sh full manual " + UUID_A
                + " 2> err.txt; rc=$?; t1=$(date +%s%3N); echo \"rc=$rc\"; echo \"elapsed=$((t1 - t0))\"; "
                + "echo \"ran=$([ -e runlog ] && echo yes || echo no)\"; echo \"state=$([ -e out/export/jobs/full.json ] && echo yes || echo no)\"; "
                + "echo \"results=$([ -e out/results/" + UUID_A + ".json ] && echo yes || echo no)\"; echo \"errlines=$(grep -c . err.txt)\"; echo \"busy=$(grep -c busy err.txt)\"; "
                + "pkill -f 'sleep [8]' || true";

        Out out = run("at_bk_09_3_2", script);

        List<String> lines = out.out().lines().toList();
        assertThat(lines.get(0)).as("結束碼 75（EX_TEMPFAIL＝busy）").isEqualTo("rc=75");
        assertThat(Long.parseLong(lines.get(1).substring("elapsed=".length()))).as("2 秒內返回（手動不等鎖，毫秒）").isLessThan(2000);
        assertThat(lines.subList(2, 7)).as("stub 未執行、狀態檔與 results 都不被建立、stderr 恰一行且含 busy").containsExactly("ran=no", "state=no", "results=no", "errlines=1", "busy=1");
    }

    @Test
    void AT_BK_09_3_3_aScheduledJobThatCannotGetTheLockRecordsLockTimeoutAndKeepsTheLastSuccess() {
        String script = "mkdir -p out/export/jobs; printf '%s' '" + finishedState("dump", "succeeded", "2026-10-26T18:30:30Z") + "' > out/export/jobs/dump.json; " + holdLock(6)
                + "export JOB_LOCK_WAIT_SECONDS=2 STUB_JOB_RUNLOG=\"$D/runlog\"; bash $S/job-run.sh dump scheduled 2> err.txt; echo \"rc=$?\"; "
                + "echo \"ran=$([ -e runlog ] && echo yes || echo no)\"; echo \"errlines=$(grep -c . err.txt)\"; pkill -f 'sleep [6]' || true";

        Out out = run("at_bk_09_3_3", script);

        assertThat(out.out().lines().toList()).containsExactly("rc=75", "ran=no", "errlines=1");
        Map<String, Object> state = json(cat("at_bk_09_3_3", "export/jobs/dump.json"));
        Map<String, Object> last = map(state.get("last"));
        assertThat(last).containsEntry("trigger", "scheduled").containsEntry("status", "failed").containsEntry("rc", 75).containsEntry("reason", "lock_timeout");
        assertThat((String) last.get("started_at")).matches(ISO_Z);
        assertThat((String) last.get("finished_at")).matches(ISO_Z);
        assertThat(state).as("失敗不覆蓋成功時間").containsEntry("last_success_at", "2026-10-26T18:30:30Z");
    }

    @Test
    void AT_BK_09_3_4_whenTheLockFileCannotBeOpenedTheJobStillRunsAndTheStateSaysLockingUnavailable() {
        String script = "mkdir -p out/export/jobs; printf '%s' '" + finishedState("full", "succeeded", "2026-10-26T18:10:00Z") + "' > out/export/jobs/full.json; "
                + "export BACKUP_CTL_LOCK_FILE=/proc/self/nonexistent-dir/maintenance.lock STUB_JOB_RC=3; bash $S/job-run.sh full scheduled; echo \"rc=$?\"";

        Out out = run("at_bk_09_3_4", script);

        assertThat(out.out().lines().toList()).as("fail-open：stub 照常執行（印 stub full done）、結束碼 3 原樣回傳").containsExactly("stub full done", "rc=3");
        assertThat(out.err()).contains("WARN");
        Map<String, Object> state = json(cat("at_bk_09_3_4", "export/jobs/full.json"));
        assertThat(map(state.get("last"))).containsEntry("note", "locking:unavailable").containsEntry("status", "failed").containsEntry("rc", 3);
        assertThat(state).as("失敗不覆蓋成功時間").containsEntry("last_success_at", "2026-10-26T18:10:00Z");
    }

    @Test
    void AT_BK_09_3_5_aStateFileThatCannotBeWrittenOnlyWarnsAndNeverChangesTheScriptsRcOrOutput() {
        String script = "chmod 555 out; export STUB_JOB_OUT=OUT-LINE STUB_JOB_ERR=ERR-LINE STUB_JOB_RC=7; bash $S/job-run.sh diff scheduled";

        Out out = run("at_bk_09_3_5", script);

        assertThat(out.rc()).as("結束碼＝腳本 rc").isEqualTo(7);
        assertThat(out.out()).contains("OUT-LINE").doesNotContain("ERR-LINE");
        assertThat(out.err()).contains("ERR-LINE").contains("WARN");
    }

    @Test
    void AT_BK_09_3_6_aBackgroundChildOfTheJobDoesNotKeepTheLockHeld() {
        String script = "STUB_JOB_BG_SLEEP=20 bash $S/job-run.sh verify scheduled; echo \"rc=$?\"; "
                + "pgrep -f 'sleep 2[0]' > /dev/null && echo bg=alive || echo bg=dead; /usr/bin/flock -n \"$D/lock/maintenance.lock\" true; echo \"flock=$?\"; pkill -f 'sleep 2[0]' || true";

        Out out = run("at_bk_09_3_6", script);

        assertThat(out.out().lines().toList()).as("工作自己的輸出照常透傳；返回後背景 sleep 仍存活，鎖不被它繼承而卡住（命令形 flock -o）")
                .containsExactly("stub verify done", "rc=0", "bg=alive", "flock=0");
    }

    @Test
    void AT_BK_09_3_7_theTerminalStateIsWrittenInsideTheLockSoTheSweepNeverMisreadsAFinishedJob() {
        String script = "export PATH=/opt/sidecar/pathstubs:$PATH STUB_MV_DELAY=1.5 STUB_JOB_SLEEP=1; mkdir -p out/export/jobs out/results; : > samples; "
                + "( for i in $(seq 1 28); do bash $S/backup-ctl-export.sh > /dev/null 2>&1; for f in out/export/jobs/*.json; do [ -f \"$f\" ] && jq -r '.last.status' \"$f\" >> samples; done; sleep 0.2; done ) & sp=$!; "
                + "bash $S/job-run.sh full scheduled > /dev/null 2>&1; echo \"rc1=$?\"; "
                + "printf '%s' '" + runningResults(UUID_A, "diff", "'\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"'") + "' > out/results/" + UUID_A + ".json; "
                + "bash $S/job-run.sh diff manual " + UUID_A + " > /dev/null 2>&1; echo \"rc2=$?\"; wait $sp; "
                + "echo \"samples=$(wc -l < samples)\"; echo \"interrupted_samples=$(grep -c interrupted samples)\"; echo \"full=$(jq -r .last.status out/export/jobs/full.json)\"; "
                + "echo \"diff=$(jq -r .last.status out/export/jobs/diff.json)\"; echo \"results=$(jq -r .status out/results/" + UUID_A + ".json)\"";

        Out out = run("at_bk_09_3_7", script);

        List<String> lines = out.out().lines().toList();
        assertThat(lines.subList(0, 2)).containsExactly("rc1=0", "rc2=0");
        assertThat(Integer.parseInt(lines.get(2).substring("samples=".length()).strip())).as("防反空轉：清掃行程確實取樣到了狀態檔").isGreaterThan(10);
        assertThat(lines.subList(3, 7)).as("整段期間沒有任何一次被改寫為 interrupted；(a)(b) 終態皆 succeeded、(b) 的 results 也是")
                .containsExactly("interrupted_samples=0", "full=succeeded", "diff=succeeded", "results=succeeded");
    }

    @Test
    void AT_BK_09_4_3_theWrapperPassesRcAndBothStreamsThroughSeparatelyAndNeverTouchesTheLastBackupStatusFile() throws IOException {
        Out before = run("at_bk_09_4_3a", "printf 'type=full\\nstatus=0\\ntimestamp=1793000000\\n' > /var/lib/pgbackrest/.last_backup_status; sha256sum /var/lib/pgbackrest/.last_backup_status");
        assertThat(before.rc()).isZero();

        Out out = run("at_bk_09_4_3", "STUB_JOB_OUT=OUT-LINE STUB_JOB_ERR=ERR-LINE STUB_JOB_RC=3 bash $S/job-run.sh full scheduled");

        assertThat(out.rc()).isEqualTo(3);
        assertThat(out.out()).contains("OUT-LINE").doesNotContain("ERR-LINE");
        assertThat(out.err()).contains("ERR-LINE").doesNotContain("OUT-LINE");
        Out after = run("at_bk_09_4_3b", "sha256sum /var/lib/pgbackrest/.last_backup_status");
        assertThat(after.out()).as("狀態檔逐位元不變").isEqualTo(before.out());
        assertThat(sourceWithoutComments("scripts/job-run.sh").lines().toList()).as("寫它是各備份腳本本體的事，包裝的程式碼不含該字樣")
                .noneMatch(line -> line.contains(".last_backup_status"));
    }

    // ══════════════════════════════════════════════════════════════════════════════════════════
    // 指標（pgbackrest-metrics.sh）
    // ══════════════════════════════════════════════════════════════════════════════════════════

    private static final List<String> EXISTING_METRICS = List.of("pgbackrest_exporter_info_ok", "pgbackrest_exporter_scrape_timestamp_seconds",
            "pgbackrest_stanza_status", "pgbackrest_repo_status", "pgbackrest_backup_count", "pgbackrest_backup_since_last_full_seconds",
            "pgbackrest_backup_since_last_backup_seconds", "pgbackrest_backup_last_duration_seconds", "pgbackrest_backup_last_database_size_bytes",
            "pgbackrest_backup_last_repo_size_bytes", "pgbackrest_backup_last_status", "pgbackrest_backup_last_run_timestamp_seconds", "aisdlc_storage_bytes",
            "aisdlc_storage_used_ratio");

    private static final String LAST_STATUS = "printf 'type=diff\\nstatus=0\\ntimestamp=1793037602\\n' > /var/lib/pgbackrest/.last_backup_status; ";

    @Test
    void AT_BK_09_4_E_1_theExistingFourteenMetricsAreUnchangedAndTheLastStatusLinesAreVerbatim() {
        Out out = run("at_bk_09_4_e_1", LAST_STATUS + "bash $S/pgbackrest-metrics.sh \"$D/metrics.prom\"; echo \"rc=$?\"; cat \"$D/metrics.prom\"");

        List<String> lines = out.out().lines().toList();
        assertThat(lines.get(0)).as(out.err()).isEqualTo("rc=0");
        List<String> names = lines.stream().filter(line -> !line.startsWith("#") && !line.startsWith("rc=") && !line.isBlank())
                .map(line -> line.replaceAll("[{ ].*$", "")).distinct().toList();
        assertThat(names).as("輸出中的指標名集合 ⊇ 既有 14 個名稱").containsAll(EXISTING_METRICS);
        assertThat(lines).as("兩行逐字不變").contains("pgbackrest_backup_last_status{stanza=\"aisdlc\",type=\"diff\"} 0",
                "pgbackrest_backup_last_run_timestamp_seconds{stanza=\"aisdlc\",type=\"diff\"} 1793037602");
    }

    @Test
    void AT_BK_09_7_1_theNewMetricsCarryTheBackupJobLabelAndNoStateFileMeansNoSeries() {
        String state = "mkdir -p out/export/jobs; "
                + "w() { printf '{\"schema_rev\":1,\"job\":\"%s\",\"last\":{\"trigger\":\"scheduled\",\"status\":\"%s\",\"rc\":0,\"reason\":null,\"started_at\":\"2026-10-20T20:00:00Z\","
                + "\"finished_at\":\"%s\",\"detail_tail\":\"\",\"note\":null},\"last_success_at\":null}' \"$1\" \"$2\" \"$3\" > out/export/jobs/$1.json; }; "
                + "w full succeeded 2026-10-27T18:10:00Z; w diff succeeded 2026-10-27T18:02:00Z; w dump failed 2026-10-27T18:30:40Z; w verify succeeded 2026-10-20T20:05:00Z; "
                + "printf '{\"schema_rev\":1,\"ts\":\"2026-10-27T18:31:00Z\",\"lock_held\":false}' > out/export/heartbeat; ";

        Out out = run("at_bk_09_7_1", LAST_STATUS + state + "bash $S/pgbackrest-metrics.sh \"$D/metrics.prom\"; echo \"rc=$?\"; cat \"$D/metrics.prom\"; "
                + "echo ---; rm out/export/jobs/diff.json; bash $S/pgbackrest-metrics.sh \"$D/metrics2.prom\"; cat \"$D/metrics2.prom\"");

        String[] parts = out.out().split("---\n", 2);
        assertThat(parts).hasSize(2);
        List<String> first = parts[0].lines().toList();
        assertThat(first.get(0)).as(out.err()).isEqualTo("rc=0");
        assertThat(first).contains("# TYPE aisdlc_backup_job_last_status gauge", "# TYPE aisdlc_backup_job_last_finished_timestamp_seconds gauge",
                "# TYPE aisdlc_backup_ctl_heartbeat_timestamp_seconds gauge");
        assertThat(first.stream().filter(line -> line.startsWith("# HELP aisdlc_backup_")).count()).as("三個新指標各帶 HELP").isEqualTo(3);
        assertThat(first).contains("aisdlc_backup_job_last_status{backup_job=\"dump\"} 1", "aisdlc_backup_job_last_status{backup_job=\"full\"} 0",
                "aisdlc_backup_job_last_status{backup_job=\"diff\"} 0", "aisdlc_backup_job_last_status{backup_job=\"verify\"} 0",
                "aisdlc_backup_job_last_finished_timestamp_seconds{backup_job=\"dump\"} 1793125840",
                "aisdlc_backup_job_last_finished_timestamp_seconds{backup_job=\"verify\"} 1792526700", "aisdlc_backup_ctl_heartbeat_timestamp_seconds 1793125860");
        assertThat(first.stream().filter(line -> line.contains("{job=")).toList()).as("標籤名是 backup_job，不是 job（會與抓取目標標籤相撞）").isEmpty();
        assertThat(parts[1].lines().toList()).as("沒有狀態檔的 job 不產生序列").noneMatch(line -> line.contains("backup_job=\"diff\""));
        assertThat(first).as("既有指標不變").contains("pgbackrest_backup_last_status{stanza=\"aisdlc\",type=\"diff\"} 0");
    }

    // ══════════════════════════════════════════════════════════════════════════════════════════
    // runner（backup-ctl-runner.sh）：心跳、清掃、權限
    // ══════════════════════════════════════════════════════════════════════════════════════════

    @Test
    void AT_BK_09_5_5_theHeartbeatReadsTheLockHolderFromProcLocksAndNeverProbesTheLockWithFlock() {
        String script = holdLock(6) + "export PATH=/opt/sidecar/pathstubs:$PATH STUB_FLOCK_LOG=\"$D/flock.log\"; : > flock.log; "
                + "bash $S/backup-ctl-runner.sh --once; cp out/export/heartbeat hb.a; ta=$(date -u +%s); wait; "
                + "bash $S/backup-ctl-runner.sh --once; cp out/export/heartbeat hb.b; tb=$(date -u +%s); rm -f \"$D/lock/maintenance.lock\"; "
                + "bash $S/backup-ctl-runner.sh --once; cp out/export/heartbeat hb.c; tc=$(date -u +%s); sleep 1; "
                + "echo \"maintenance_calls=$(grep -c maintenance.lock flock.log)\"; echo \"export_calls=$(grep -c export.lock flock.log)\"; "
                + "echo \"a|$ta|$(cat hb.a)\"; echo \"b|$tb|$(cat hb.b)\"; echo \"c|$tc|$(cat hb.c)\"";

        Out out = run("at_bk_09_5_5", script);

        List<String> lines = out.out().lines().toList();
        assertThat(lines.get(0)).as("對維護鎖零筆 flock 呼叫（任何 flock -n／-w 探測即紅）").isEqualTo("maintenance_calls=0");
        assertThat(Integer.parseInt(lines.get(1).substring("export_calls=".length()))).as("防反空轉：flock stub 確實攔到匯出對 export.lock 的呼叫").isPositive();
        boolean[] expectedLockHeld = {true, false, false};
        for (int i = 0; i < 3; i++) {
            String[] parts = lines.get(2 + i).split("\\|", 3);
            Map<String, Object> heartbeat = json(parts[2]);
            assertThat(heartbeat.keySet()).containsExactly("schema_rev", "ts", "lock_held");
            assertThat(heartbeat).as("(%s) lock_held", parts[0]).containsEntry("schema_rev", 1).containsEntry("lock_held", expectedLockHeld[i]);
            assertThat((String) heartbeat.get("ts")).matches(ISO_Z);
            assertThat(Long.parseLong(parts[1]) - Instant.parse((String) heartbeat.get("ts")).getEpochSecond()).as("(%s) ts 在 5 秒內", parts[0]).isBetween(0L, 5L);
        }
    }

    @Test
    void AT_BK_09_6_3_theSweepInterruptsOnlyTheRunningJobsThatAreNotTheLiveLockHolder() {
        String script = "mkdir -p out/export/jobs out/results; printf '%s' '" + runningState("full", "2026-10-27T01:00:00Z") + "' > out/export/jobs/full.json; "
                + "printf '%s' '" + runningState("diff", "2026-10-27T02:00:00Z") + "' > out/export/jobs/diff.json; "
                + "printf '%s' '" + runningResults(UUID_A, "full", "2026-10-27T01:00:00Z") + "' > out/results/" + UUID_A + ".json; " + holdLock(6)
                + "bash $S/backup-ctl-runner.sh --once; echo \"rc=$?\"; "
                + "cp out/export/jobs/full.json snap.full.json; cp out/export/jobs/diff.json snap.diff.json; cp out/results/" + UUID_A + ".json snap.results.json; "
                + "pkill -f 'sleep [6]' || true";

        Out out = run("at_bk_09_6_3", script);

        assertThat(out.out().lines().toList()).containsExactly("rc=0");
        Map<String, Object> full = json(readFile("at_bk_09_6_3", "snap.full.json"));
        assertThat(map(full.get("last"))).containsEntry("status", "interrupted").containsEntry("reason", "interrupted");
        assertThat((String) map(full.get("last")).get("finished_at")).matches(ISO_Z);
        assertThat(full).as("last_success_at 不被清掃改動").containsEntry("last_success_at", "2026-10-26T18:10:00Z");
        assertThat(map(json(readFile("at_bk_09_6_3", "snap.diff.json")).get("last"))).as("鎖仍被活的持有者持有，started_at 較新者保持 running")
                .containsEntry("status", "running");
        assertThat(json(readFile("at_bk_09_6_3", "snap.results.json"))).as("對應 results 改為 failed／interrupted")
                .containsEntry("status", "failed").containsEntry("reason", "interrupted");
    }

    @Test
    void AT_BK_09_6_4_everyFileIsReadableByTheOtherUidEvenUnderAStrictUmask() {
        String script = "umask 077; TZ=Asia/Taipei BACKUP_CTL_CRONTAB=/opt/sidecar/crontab bash $S/backup-ctl-export.sh schedule; bash $S/backup-ctl-export.sh; "
                + "bash $S/backup-ctl-runner.sh --once; bash $S/job-run.sh full scheduled; bash $S/job-run.sh diff manual " + UUID_A + "; "
                + "for p in out/export out/export/jobs out/results out/export/info.json out/export/logical.json out/export/schedule.json out/export/heartbeat "
                + "out/export/jobs/full.json out/export/jobs/diff.json out/results/" + UUID_A + ".json; do echo \"$p $(stat -c %a \"$p\")\"; done";

        Out out = run("at_bk_09_6_4", script);

        List<String> lines = out.out().lines().filter(line -> line.startsWith("out/")).toList();
        assertThat(lines).hasSize(10);
        for (String line : lines) {
            String[] parts = line.split(" ");
            boolean directory = !parts[0].endsWith(".json") && !parts[0].endsWith("heartbeat");
            assertThat(parts[1]).as(parts[0]).isEqualTo(directory ? "755" : "644");
        }
    }

    @Test
    void AT_BK_09_6_5_anOrphanedResultsMarkerIsInterruptedOnlyAfterTheGracePeriod() {
        String script = "mkdir -p out/results; old=$(date -u -d '31 seconds ago' +%Y-%m-%dT%H:%M:%SZ); fresh=$(date -u -d '5 seconds ago' +%Y-%m-%dT%H:%M:%SZ); "
                + "for pair in \"11111111-1111-4111-8111-111111111111 $old\" \"22222222-2222-4222-8222-222222222222 $fresh\"; do set -- $pair; "
                + "printf '{\"schema_rev\":1,\"id\":\"%s\",\"type\":\"diff\",\"status\":\"running\",\"reason\":null,\"rc\":null,\"started_at\":\"%s\",\"finished_at\":null,\"detail_tail\":\"\"}' "
                + "\"$1\" \"$2\" > out/results/$1.json; done; bash $S/backup-ctl-export.sh sweep; echo \"rc=$?\"";

        Out out = run("at_bk_09_6_5", script);

        assertThat(out.out().lines().toList()).containsExactly("rc=0");
        Map<String, Object> orphan = json(cat("at_bk_09_6_5", "results/11111111-1111-4111-8111-111111111111.json"));
        assertThat(orphan).as("31 秒者（寬限＝6×5 秒）改寫為 failed／interrupted，rc 為 null").containsEntry("status", "failed").containsEntry("reason", "interrupted").containsEntry("rc", null);
        assertThat((String) orphan.get("finished_at")).matches(ISO_Z);
        assertThat(json(cat("at_bk_09_6_5", "results/22222222-2222-4222-8222-222222222222.json"))).as("寬限內（5 秒）不動").containsEntry("status", "running");
    }

    @Test
    void AT_BK_09_2_S_1_theRunnerStartupRemovesRequestFilesOlderThan24HoursAndKeepsTheRest() {
        String script = "printf '{}' > req/22222222-2222-4222-8222-222222222222.json; printf '{}' > req/33333333-3333-4333-8333-333333333333.json; "
                + "touch -d '25 hours ago' req/22222222-2222-4222-8222-222222222222.json; touch -d '23 hours ago' req/33333333-3333-4333-8333-333333333333.json; "
                + "bash $S/backup-ctl-runner.sh --once 2> err.txt; echo \"rc=$?\"; echo \"left=$(ls req | tr '\\n' ' ')\"; echo \"warn=$(grep -c WARN err.txt)\"; echo \"leak=$(grep -c 22222222 err.txt)\"";

        Out out = run("at_bk_09_2_s_1", script);

        assertThat(out.out().lines().toList()).as("只刪逾 24 小時者、結束碼 0、只記一行 WARN 且不回顯檔名").containsExactly(
                "rc=0", "left=33333333-3333-4333-8333-333333333333.json ", "warn=1", "leak=0");
    }

    // ══════════════════════════════════════════════════════════════════════════════════════════
    // runner 迴圈的心跳：不被匯出逾時阻塞、停住時真的能被偵測
    // ══════════════════════════════════════════════════════════════════════════════════════════

    /** 取樣器的輸出（每行一個 ts）→ 相鄰「不同」ts 的最大間隔（秒）。 */
    private static long maxGapSeconds(List<String> samples) {
        List<Instant> distinct = new ArrayList<>();
        for (String sample : samples) {
            if (ISO_Z.matcher(sample.strip()).matches()) {
                Instant ts = Instant.parse(sample.strip());
                if (distinct.isEmpty() || !distinct.get(distinct.size() - 1).equals(ts)) {
                    distinct.add(ts);
                }
            }
        }
        long max = 0;
        for (int i = 1; i < distinct.size(); i++) {
            max = Math.max(max, distinct.get(i).getEpochSecond() - distinct.get(i - 1).getEpochSecond());
        }
        return max;
    }

    /** 取樣器：每 0.5 秒讀一次心跳的 ts，共 $1 次，追加到 hb.samples。 */
    private static final String SAMPLER = "sample() { for i in $(seq 1 $1); do jq -r .ts out/export/heartbeat 2> /dev/null >> hb.samples || true; sleep 0.5; done; }; ";

    @Test
    void AT_BK_09_8_2_aHungExportIsKilledByTheTimeoutWithoutStoppingTheHeartbeatOrOverlapping() {
        String script = SAMPLER + "export BACKUP_CTL_POLL_SECONDS=1 BACKUP_CTL_EXPORT_SECONDS=1 BACKUP_CTL_EXPORT_TIMEOUT_SECONDS=3 STUB_INFO_SLEEP=30 "
                + "STUB_CALL_LOG=\"$D/calls.log\"; bash $S/backup-ctl-runner.sh > runner.log 2>&1 & rp=$!; sample 20; "
                + "kill -0 $rp 2> /dev/null && echo alive=yes || echo alive=no; echo \"info_ok=$(jq -r .ok out/export/info.json 2> /dev/null)\"; "
                + "echo \"seq=$(awk '$2==\"start\" || $2==\"end\" { printf \"%s,\", $2 }' calls.log)\"; echo ---; cat hb.samples; "
                + "kill $rp 2> /dev/null; pkill -f 'sleep 3[0]' || true; pkill -f 'backup-ctl-expor[t]' || true";

        Out out = run("at_bk_09_8_2", script);

        String[] parts = out.out().split("---\n", 2);
        assertThat(parts).hasSize(2);
        List<String> head = parts[0].lines().toList();
        assertThat(head.get(0)).as("迴圈仍存活").isEqualTo("alive=yes");
        assertThat(head.get(1)).as("約 3 秒後匯出被 timeout 終止，info.json 記 ok:false").isEqualTo("info_ok=false");
        assertThat(maxGapSeconds(parts[1].lines().toList())).as("匯出被卡住期間，心跳相鄰 ts 的間隔 ≤3 秒").isLessThanOrEqualTo(3);
        assertThat(head.get(2)).as("stub 呼叫的起迄記錄沒有重疊區間（start、end 嚴格交替，最後一個可以尚未結束）").matches("^seq=(start,end,)*(start,)?$");
        assertThat(head.get(2).split("start", -1).length - 1).as("防反空轉：10 秒內至少起過兩次匯出（逾時後下一輪才會再起）").isGreaterThanOrEqualTo(2);
    }

    @Test
    void AT_BK_09_8_E_1_theHeartbeatSamplerReallyDetectsAStalledRunner() {
        String script = SAMPLER + "export BACKUP_CTL_POLL_SECONDS=1; bash $S/backup-ctl-runner.sh > runner.log 2>&1 & rp=$!; "
                + "( sleep 2; kill -STOP $rp; sleep 6; kill -CONT $rp ) > /dev/null 2>&1 & ctl=$!; sample 24; wait $ctl; "
                + "kill $rp 2> /dev/null; pkill -f 'backup-ctl-expor[t]' || true; cat hb.samples";

        Out out = run("at_bk_09_8_e_1", script);

        List<String> samples = out.out().lines().toList();
        assertThat(maxGapSeconds(samples)).as("暫停 6 秒：取樣器記錄到 >3 秒的間隔（證明「≤3 秒」斷言真的能偵測心跳中斷）").isGreaterThan(3);
        List<Instant> distinct = samples.stream().filter(s -> ISO_Z.matcher(s.strip()).matches()).map(s -> Instant.parse(s.strip())).distinct().toList();
        assertThat(distinct.get(distinct.size() - 1)).as("-CONT 後心跳恢復").isAfter(distinct.get(0).plusSeconds(8));
    }
}
