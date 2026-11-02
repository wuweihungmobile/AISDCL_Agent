package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.research.ResearchViews.Matrix;
import com.aisdlc.console.domain.model.research.ResearchViews.Source;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** 來源與證據矩陣的<b>唯讀</b>埠（同 {@link ResearchProjectReadPort}：JDBC、零寫入）。 */
public interface ResearchEvidenceReadPort {

    /** 全部來源（依 source_no）；每筆帶它的抓取紀錄（依抓取時間遞增）。 */
    List<Source> sources(UUID researchId);

    /** 一個矩陣版本；{@code matrixVersion} 為 null＝最新版。沒有任何證據列也沒有矩陣產物則 empty。 */
    Optional<Matrix> matrix(UUID researchId, Integer matrixVersion);
}
