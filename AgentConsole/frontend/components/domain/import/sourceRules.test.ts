import { describe, expect, it } from "vitest";

import { REASONS } from "@/lib/api/reasons";
import { MAX_UPLOAD_BYTES, validateSourceFile } from "./sourceRules";

describe("匯入檔案預檢（US-I-01：.md／.pdf／.docx、≤10MB）", () => {
  it.each(["brd.md", "brd.MD", "spec.pdf", "SPEC.PDF", "需求.docx", "a.b.c.docx"])("%s 通過", (name) => {
    expect(validateSourceFile({ name, size: 1024 })).toBeNull();
  });

  it.each(["notes.txt", "brd.md.exe", "brd", "brd.doc", "brd.markdown"])("%s → 副檔名不支援（契約 reason 逐字）", (name) => {
    expect(validateSourceFile({ name, size: 1024 })).toBe(REASONS.IMPORT_UNSUPPORTED_EXTENSION);
  });

  it("0 byte → 檔案是空的；恰好 10MB 通過；多 1 byte → 超過 10MB 上限", () => {
    expect(validateSourceFile({ name: "a.md", size: 0 })).toBe(REASONS.IMPORT_EMPTY_FILE);
    expect(MAX_UPLOAD_BYTES).toBe(10_485_760);
    expect(validateSourceFile({ name: "a.md", size: MAX_UPLOAD_BYTES })).toBeNull();
    expect(validateSourceFile({ name: "a.md", size: MAX_UPLOAD_BYTES + 1 })).toBe(REASONS.IMPORT_FILE_TOO_LARGE);
  });

  it("副檔名不符優先於大小（與後端先驗副檔名再驗大小的順序一致）", () => {
    expect(validateSourceFile({ name: "big.txt", size: MAX_UPLOAD_BYTES + 1 })).toBe(REASONS.IMPORT_UNSUPPORTED_EXTENSION);
  });

});
