package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.research.ResearchViews.PrdVersion;
import com.aisdlc.console.domain.model.research.ResearchViews.Round;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** PRD 版本與審查輪的<b>唯讀</b>埠（同 {@link ResearchProjectReadPort}：JDBC、零寫入）。審查輪列只在輪有結果時存在（D-57），所以這裡沒有「進行中的輪」。 */
public interface ResearchReviewReadPort {

    /** PRD 版本清單（依 version_no 遞增；{@code content} 為 null）。 */
    List<PrdVersion> prdVersions(UUID researchId);

    /** 單筆 PRD 版本（含 {@code content}）。 */
    Optional<PrdVersion> prdVersion(UUID researchId, int versionNo);

    /** 審查輪清單（依 round_no 遞增，各帶分數與缺陷）。 */
    List<Round> rounds(UUID researchId);

    /** 單筆審查輪；{@code roundNo} 指向沒有列的輪（進行中、取消、無效輸出）則 empty。 */
    Optional<Round> round(UUID researchId, int roundNo);
}
