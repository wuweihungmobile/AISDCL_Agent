package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.domain.model.execution.SddTaskSpec;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 任務 {@code passCriteriaSpec}（JSON 文字）的 SDD 欄位讀取（契約 §1.10.5 資格第 3 項）。為什麼重要：execute 的資格判定吃這裡的輸出——
 * 一個壞掉或型別不對的 spec 只能被當成「不是 SDD 來源」，絕不能讓 execute 變成 500，也絕不能把「看起來像 SDD」的垃圾放行成 SDD 批次。
 */
class JsonPassCriteriaSpecReaderTest {

    private final JsonPassCriteriaSpecReader reader = new JsonPassCriteriaSpecReader();

    @Test
    void aPathASpecYieldsEveryField() {
        SddTaskSpec spec = reader.read("{\"source\":\"sdd\",\"specDigest\":\"sha256:abc\",\"stepId\":\"sdd-x-at-001-1-1\","
                + "\"weakRegex\":true,\"maintainContext\":false}");

        assertThat(spec).isEqualTo(new SddTaskSpec("sdd", "sdd-x-at-001-1-1", "sha256:abc", true, false));
        assertThat(spec.sddSource()).isTrue();
        assertThat(spec.eligible()).isTrue();
    }

    @Test
    void missingOptionalBooleansStayNullSoTheyAreNotSentLater() {
        SddTaskSpec spec = reader.read("{\"source\":\"sdd\",\"specDigest\":\"d\",\"stepId\":\"s\"}");

        assertThat(spec.weakRegex()).isNull();
        assertThat(spec.maintainContext()).isNull();
    }

    @Test
    void anotherSourceIsReadAsIsButIsNotEligible() {
        SddTaskSpec spec = reader.read("{\"source\":\"decompose\",\"draftId\":\"d-1\",\"stepId\":\"s1\"}");

        assertThat(spec.source()).isEqualTo("decompose");
        assertThat(spec.sddSource()).isFalse();
        assertThat(spec.eligible()).isFalse();
    }

    @Test
    void nullBlankBrokenOrNonObjectJsonIsNoneNeverAnException() {
        for (String bad : new String[] {null, "", "   ", "{not json", "[1,2]", "\"text\"", "42", "null", "true"}) {
            assertThat(reader.read(bad)).as(String.valueOf(bad)).isEqualTo(SddTaskSpec.NONE);
        }
    }

    @Test
    void fieldsOfTheWrongTypeAreTreatedAsMissing() {
        SddTaskSpec spec = reader.read("{\"source\":\"sdd\",\"stepId\":123,\"specDigest\":[\"x\"],\"weakRegex\":\"yes\","
                + "\"maintainContext\":1}");

        assertThat(spec.sddSource()).isTrue();
        assertThat(spec.stepId()).isNull();
        assertThat(spec.specDigest()).isNull();
        assertThat(spec.weakRegex()).isNull();
        assertThat(spec.maintainContext()).isNull();
        assertThat(spec.eligible()).as("缺 stepId／specDigest 不可進 SDD 批次").isFalse();
    }

    @Test
    void blankStepIdOrDigestIsNotEligible() {
        assertThat(reader.read("{\"source\":\"sdd\",\"stepId\":\" \",\"specDigest\":\"d\"}").eligible()).isFalse();
        assertThat(reader.read("{\"source\":\"sdd\",\"stepId\":\"s\",\"specDigest\":\"\"}").eligible()).isFalse();
    }
}
