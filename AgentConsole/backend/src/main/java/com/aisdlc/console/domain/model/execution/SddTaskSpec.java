package com.aisdlc.console.domain.model.execution;

/**
 * 任務的 {@code passCriteriaSpec}（JSON）裡 SDD 批次判定與送出需要的欄位（契約 §1.10.5 資格第 3 項、§3.4.1 v1.5 補充）。路徑 A 的 confirm 把這些值
 * 放進任務（{@code {source:"sdd", specDigest, stepId, weakRegex, maintainContext?}}）；domain 只保存 JSON 文字、不解析，解析由
 * {@code PassCriteriaSpecReader} 埠完成。
 *
 * @param source          {@code sdd}＝路徑 A（規格驅動）產生的任務；其餘（{@code decompose}、缺）不是
 * @param stepId          規格編譯出的 step_id（{@code sdd-<場景>-<at id 小寫>}）；SDD 批次沿用它當 playbook 的 {@code step_id}
 * @param specDigest      匯入當下的規格摘要（Bridge 預檢第 4 項的「匯入時」摘要）
 * @param weakRegex       Bridge 判定驗收 regex 太弱；缺為 null（不送）
 * @param maintainContext 跨 AC 脈絡隔離；缺為 null（不送）
 */
public record SddTaskSpec(String source, String stepId, String specDigest, Boolean weakRegex, Boolean maintainContext) {

    public static final String SOURCE_SDD = "sdd";

    /** 沒有（或讀不出）{@code passCriteriaSpec}：不是 SDD 來源。 */
    public static final SddTaskSpec NONE = new SddTaskSpec(null, null, null, null, null);

    /** 這個任務是路徑 A（規格驅動）產生的。 */
    public boolean sddSource() {
        return SOURCE_SDD.equals(source);
    }

    /** 可以進 SDD 批次：SDD 來源，且 {@code stepId}、{@code specDigest} 皆為非空字串（資格第 3 項）。 */
    public boolean eligible() {
        return sddSource() && stepId != null && !stepId.isBlank() && specDigest != null && !specDigest.isBlank();
    }
}
