package com.aisdlc.console.domain.model.signoff;

import java.util.List;

/** {@code GET /signoffs/pending} 的結果：四種草案的計數（不受 limit 影響）與依建立時間升冪的前 limit 筆清單。 */
public record PendingSignoffs(PendingSignoffCounts counts, List<PendingSignoffItem> items) {

    public PendingSignoffs {
        items = items == null ? List.of() : List.copyOf(items);
    }
}
