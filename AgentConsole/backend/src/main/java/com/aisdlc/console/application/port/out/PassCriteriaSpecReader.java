package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.execution.SddTaskSpec;

/**
 * 讀任務 {@code passCriteriaSpec}（JSON 文字）的 SDD 欄位（契約 §1.10.5 資格第 3 項）。domain 與 application 都不依賴 JSON 函式庫
 * （{@code Task.passCriteriaSpec} 在 domain 只是原樣保存的文字），所以解析放在埠後面，由 persistence 介面卡實作。
 */
public interface PassCriteriaSpecReader {

    /**
     * 解析 {@code passCriteriaSpecJson}：{@code null}、空白、不是 JSON 物件、或壞掉的 JSON 一律回 {@link SddTaskSpec#NONE}
     * （「不是 SDD 來源」；不丟例外——一個壞掉的 spec 不應讓整個 execute 變成 500）。欄位型別不對（例如 {@code stepId} 不是字串）視為缺。
     */
    SddTaskSpec read(String passCriteriaSpecJson);
}
