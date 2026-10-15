package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractOutboundIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.DocumentFixtures;
import com.aisdlc.console.support.FakeHttpServer.Response;
import com.aisdlc.console.support.ImportFixtures;
import com.aisdlc.console.support.OutboundFakes;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 檔案上傳匯入（API-IMP-01／07；契約 §1.1.1）。為什麼重要：上傳是使用者資料進入系統的第一道門——副檔名與內容必須互相印證
 * （改副檔名偷渡的檔案要被擋下）、文字擷取失敗（加密、損毀、掃描檔）要有可行動的說明而不是空白草案、
 * 大小上限要在「剛好 10MB」與「多 1 byte」兩側都有證據、被擷取出來的原文就是之後 AI 解析的唯一輸入。
 */
class ImportUploadApiIT extends AbstractOutboundIT {

    private static final String UPLOAD = "/api/v1/import/upload";
    private static final int TEN_MB = 10 * 1024 * 1024;

    private Resp upload(String filename, byte[] content) {
        return api.multipart(operator(), UPLOAD, "file", filename, "application/octet-stream", content);
    }

    private static byte[] utf8(String text) {
        return text.getBytes(StandardCharsets.UTF_8);
    }

    private String sourceContentOf(String id) {
        return api.get(viewer(), "/api/v1/import/" + id).read("$.data.sourceContent");
    }

    private void assertRejected(Resp resp, int status, String reason) {
        assertThat(resp.status()).isEqualTo(status);
        assertThat(resp.<String>read("$.reason")).isEqualTo(reason);
        assertThat(jdbc.queryForObject("select count(*) from console.import_records", Integer.class))
                .as("被拒絕的上傳不得留下記錄").isZero();
    }

    // ── 成功 ─────────────────────────────────────────────────────────────────

    @Test
    void aMarkdownFileBecomesAnUploadedRecordWhoseSourceContentIsTheFileText() {
        String text = "# BRD\n\n## 需求\n- 使用者可以登入\n";
        Resp resp = upload("e2e-brd.md", utf8(text));

        assertThat(resp.status()).isEqualTo(201);
        assertThat(resp.<String>read("$.data.sourceType")).isEqualTo("MARKDOWN");
        assertThat(resp.<String>read("$.data.sourceFileName")).isEqualTo("e2e-brd.md");
        assertThat(resp.<String>read("$.data.status")).isEqualTo("UPLOADED");
        assertThat(resp.<Boolean>read("$.data.signedOff")).isFalse();
        assertThat(resp.<String>read("$.data.createdAt")).isNotBlank();
        assertThat(resp.body()).doesNotContain("sourceContent");
        assertThat(sourceContentOf(resp.id())).isEqualTo(text);
    }

    @Test
    void theExtensionIsCaseInsensitiveAndOnlyTheBaseNameIsKept() {
        assertThat(upload("NOTES.MD", utf8("# a")).<String>read("$.data.sourceType")).isEqualTo("MARKDOWN");
        for (String filename : List.of("C:\\docs\\sub\\brd.md", "../../etc/brd.md", "/var/tmp/brd.md",
                "  spaced\\brd.md  ")) {
            Resp resp = upload(filename, utf8("# a"));
            assertThat(resp.status()).as(filename).isEqualTo(201);
            assertThat(resp.<String>read("$.data.sourceFileName")).as(filename).isEqualTo("brd.md");
        }
    }

    @Test
    void aUtf8ByteOrderMarkIsToleratedAndNotStoredAsContent() {
        byte[] bom = {(byte) 0xEF, (byte) 0xBB, (byte) 0xBF};
        byte[] body = utf8("# 含 BOM 的文件");
        byte[] content = new byte[bom.length + body.length];
        System.arraycopy(bom, 0, content, 0, bom.length);
        System.arraycopy(body, 0, content, bom.length, body.length);

        Resp resp = upload("bom.md", content);

        assertThat(resp.status()).isEqualTo(201);
        assertThat(sourceContentOf(resp.id())).isEqualTo("# 含 BOM 的文件");
    }

    @Test
    void aFileNameIsClippedToFiveHundredCharacters() {
        Resp resp = upload("n".repeat(600) + ".md", utf8("# a"));
        assertThat(resp.status()).isEqualTo(201);
        assertThat(resp.<String>read("$.data.sourceFileName")).hasSize(500);
    }

    @Test
    void aPdfYieldsItsTextLayer() {
        Resp resp = upload("brd.pdf", DocumentFixtures.pdfWith("Requirement One", "Requirement Two"));

        assertThat(resp.status()).isEqualTo(201);
        assertThat(resp.<String>read("$.data.sourceType")).isEqualTo("PDF");
        String content = sourceContentOf(resp.id());
        assertThat(content).contains("Requirement One").contains("Requirement Two");
        assertThat(content.indexOf("Requirement One")).isLessThan(content.indexOf("Requirement Two"));
    }

    @Test
    void aDocxYieldsItsParagraphsInOrder() {
        Resp resp = upload("brd.docx", DocumentFixtures.docxWith("需求標題", "第一段內容", "第二段內容"));

        assertThat(resp.status()).isEqualTo(201);
        assertThat(resp.<String>read("$.data.sourceType")).isEqualTo("DOCX");
        String content = sourceContentOf(resp.id());
        assertThat(content).contains("需求標題").contains("第一段內容").contains("第二段內容");
        assertThat(content.indexOf("第一段內容")).isLessThan(content.indexOf("第二段內容"));
    }

    @Test
    void theSameFileUploadedTwiceMakesTwoIndependentRecords() {
        String first = upload("a.md", utf8("# a")).id();
        String second = upload("a.md", utf8("# a")).id();
        assertThat(second).isNotEqualTo(first);
        assertThat(jdbc.queryForObject("select count(*) from console.import_records", Integer.class)).isEqualTo(2);
    }

    // ── 驗證與拒絕 ─────────────────────────────────────────────────────────────

    @Test
    void anEmptyFileIs400AndAMissingFilePartIs400() {
        assertRejected(upload("empty.md", new byte[0]), 400, "檔案是空的");
        assertRejected(api.multipartWithoutParts(operator(), UPLOAD), 400, "未提供檔案");
        assertRejected(api.multipart(operator(), UPLOAD, "wrongName", "a.md", "text/markdown", utf8("# a")), 400,
                "未提供檔案");
    }

    @Test
    void onlyMdPdfAndDocxExtensionsAreAcceptedAnythingElseIs415WithTheAllowedList() {
        for (String filename : List.of("notes.txt", "noextension", "brd.md.exe", "brd.markdown", "brd.pdf.txt",
                "brd.doc", "brd.xlsx", ".md.bak", "brd.")) {
            Resp resp = upload(filename, utf8("hello"));
            assertThat(resp.status()).as(filename).isEqualTo(415);
            assertThat(resp.<String>read("$.reason")).isEqualTo("只支援 .md／.pdf／.docx 檔案");
            assertThat(resp.<List<String>>read("$.details.allowed")).containsExactly(".md", ".pdf", ".docx");
        }
        assertThat(upload("notes.txt", utf8("hello")).<String>read("$.details.extension")).isEqualTo(".txt");
        assertThat(jdbc.queryForObject("select count(*) from console.import_records", Integer.class)).isZero();
    }

    @Test
    void theLimitIsExactlyTenMegabytes() {
        byte[] atLimit = new byte[TEN_MB];
        Arrays.fill(atLimit, (byte) 'a');
        Resp ok = upload("limit.md", atLimit);
        assertThat(ok.status()).as("剛好 10MB").isEqualTo(201);

        byte[] over = new byte[TEN_MB + 1];
        Arrays.fill(over, (byte) 'a');
        Resp tooBig = upload("over.md", over);
        assertThat(tooBig.status()).as("多 1 byte").isEqualTo(413);
        assertThat(tooBig.<String>read("$.reason")).isEqualTo("檔案超過 10MB 上限");
        assertThat(tooBig.<Integer>read("$.details.limitBytes")).isEqualTo(10_485_760);
        assertThat(jdbc.queryForObject("select count(*) from console.import_records", Integer.class)).isEqualTo(1);
    }

    @Test
    void theExtensionIsCheckedBeforeTheSizeSoAnOversizedWrongTypeIs415() {
        Resp resp = upload("huge.txt", new byte[TEN_MB + 1]);
        assertThat(resp.status()).isEqualTo(415);
    }

    @Test
    void aMarkdownFileThatIsNotUtf8IsRejectedInsteadOfBeingSilentlyMangled() {
        byte[] latin1 = {'#', ' ', (byte) 0xE9, (byte) 0xFF, (byte) 0xFE, 'x'};
        assertRejected(upload("latin1.md", latin1), 422, "檔案不是有效的 UTF-8 文字");
    }

    @Test
    void aFileWithNoTextAtAllIsRejectedWithAnActionableReason() {
        assertRejected(upload("blank.md", utf8("  \n\t \n")), 422, "無法從檔案擷取文字");
        assertRejected(upload("scan.pdf", DocumentFixtures.pdfWithoutText()), 422, "無法從檔案擷取文字");
        assertRejected(upload("blank.docx", DocumentFixtures.docxWith("  ", "")), 422, "無法從檔案擷取文字");
    }

    @Test
    void theContentMustMatchTheExtension() {
        Resp helloPdf = upload("fake.pdf", utf8("hello"));
        assertRejected(helloPdf, 422, "檔案內容與副檔名不符");
        assertThat(helloPdf.<String>read("$.details.extension")).isEqualTo(".pdf");
        assertRejected(upload("fake.docx", utf8("hello")), 422, "檔案內容與副檔名不符");
        assertRejected(upload("renamed.docx", DocumentFixtures.pdfWith("x")), 422, "檔案內容與副檔名不符");
        assertRejected(upload("renamed.pdf", DocumentFixtures.docxWith("x")), 422, "檔案內容與副檔名不符");
        assertRejected(upload("short.pdf", utf8("%PDF")), 422, "檔案內容與副檔名不符");
    }

    @Test
    void aFileThatPassesTheMagicBytesButCannotBeParsedIsCorrupt() {
        assertRejected(upload("broken.pdf", utf8("%PDF-1.7\nnot really a pdf")), 422, "檔案已損毀，無法讀取");
        byte[] brokenZip = {'P', 'K', 3, 4, 1, 2, 3, 4, 5, 6, 7, 8};
        assertRejected(upload("broken.docx", brokenZip), 422, "檔案已損毀，無法讀取");
    }

    @Test
    void aPasswordProtectedPdfIsReportedAsEncrypted() {
        assertRejected(upload("secret.pdf", DocumentFixtures.passwordProtectedPdf("user-pw")), 422,
                "PDF 已加密，無法擷取文字");
    }

    // ── 上傳之後 ───────────────────────────────────────────────────────────────

    @Test
    void anUploadedDocumentTooLongForTheModelIsRefusedByTheLengthGateBeforeAnythingIsSent() {
        configureFakeModel();
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH,
                Response.json(200, ImportFixtures.chatCompletion(ImportFixtures.okTree())));
        String text = "# 長文件\n" + "需求內容。".repeat(30_000);
        Resp uploaded = upload("long.md", utf8(text));
        assertThat(uploaded.status()).as("3MB 以內的長文件可以上傳（上限只有 10MB 檔案大小）").isEqualTo(201);

        Resp parsed = api.post(operator(), "/api/v1/import/" + uploaded.id() + "/parse",
                Map.of("executionPath", "/work/proj"));

        assertThat(parsed.status()).isEqualTo(422);
        assertThat(parsed.<String>read("$.reason")).isEqualTo("解析結果未通過有界閘");
        assertThat(parsed.<List<String>>read("$.errors[*].gate")).containsExactly("prompt_too_long");
        assertThat(parsed.<String>read("$.errors[0].location")).isEqualTo("sourceContent");
        assertThat(parsed.<String>read("$.errors[0].detail")).startsWith("文件過長：").endsWith("，上限 120000");
        assertThat(OutboundFakes.LLM.received()).as("太長的文件不會送給模型").isEmpty();
        assertThat(api.get(viewer(), "/api/v1/import/" + uploaded.id()).<String>read("$.data.status"))
                .isEqualTo("UPLOADED");
    }

    @Test
    void anUploadedPdfFlowsThroughParseLikeAnyOtherDocument() {
        configureFakeModel();
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH,
                Response.json(200, ImportFixtures.chatCompletion(ImportFixtures.okTree())));
        Resp uploaded = upload("brd.pdf", DocumentFixtures.pdfWith("Login", "Logout"));

        Resp parsed = api.post(operator(), "/api/v1/import/" + uploaded.id() + "/parse",
                Map.of("executionPath", "/work/proj"));

        assertThat(parsed.status()).isEqualTo(200);
        assertThat(parsed.<String>read("$.data.path")).as("PDF 一律不會走高階目標路徑").isEqualTo("LLM");
        assertThat(OutboundFakes.LLM.received().get(0).body()).contains("Login");
    }

    // ── 角色與審計 ─────────────────────────────────────────────────────────────

    @Test
    void viewersAndAnonymousCallersCannotUploadAndOperatorsAndAdminsCan() {
        byte[] content = utf8("# a");
        assertThat(api.multipart(viewer(), UPLOAD, "file", "a.md", "text/markdown", content).status())
                .isEqualTo(403);
        assertThat(api.multipart(null, UPLOAD, "file", "a.md", "text/markdown", content).status()).isEqualTo(401);
        assertThat(api.multipart(admin(), UPLOAD, "file", "a.md", "text/markdown", content).status())
                .isEqualTo(201);
        assertThat(api.multipart(operator(), UPLOAD, "file", "a.md", "text/markdown", content).status())
                .isEqualTo(201);
        assertThat(jdbc.queryForObject("select count(*) from console.import_records", Integer.class)).isEqualTo(2);
    }

    @Test
    void anUploadLeavesAnAuditRowNamingTheRecordButNeverItsContent() {
        Resp resp = upload("audited.md", utf8("# 機密需求內容 SECRET-MARKER"));

        List<Map<String, Object>> rows = jdbc.queryForList("select subject, role, method, path, entity_type, "
                + "entity_id, http_status from console.audit_log where path = '/api/v1/import/upload'");
        assertThat(rows).hasSize(1);
        assertThat(rows.get(0)).containsEntry("subject", "operator").containsEntry("method", "POST")
                .containsEntry("entity_type", "import").containsEntry("entity_id", resp.id())
                .containsEntry("http_status", 201);
        assertThat(rows.toString()).doesNotContain("SECRET-MARKER");
    }
}
