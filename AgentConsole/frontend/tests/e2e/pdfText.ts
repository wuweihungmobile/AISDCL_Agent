import { inflateSync } from "node:zlib";

/**
 * 最小的 PDF 文字抽取（QA 驗證用，不依賴任何 PDF 套件）：只為了回答「報表 PDF 內容是不是真的有中文字」。
 *
 * 後端（PDFBox 3）以 PDType0Font 內嵌 Noto Sans TC 子集：內容串流用 2 位元組的字形編號（`<00A1> Tj`），
 * 字形編號 → Unicode 的對照放在 ToUnicode CMap 串流（`beginbfchar`／`beginbfrange`）。做法：
 *   1. 掃出所有 `stream … endstream`，能 Flate 解壓的就解壓（PDF 1.6 的物件串流與內容串流都壓縮）；
 *   2. 含 `beginbfchar`／`beginbfrange` 的是 CMap，合併成「字形編號 → 字串」；
 *   3. 含 `BT … ET` 的是內容串流，把 `<hex>` 以 2 位元組切開、查 CMap；`(…)` 字面字串（單位元組字型）原樣收下。
 * 限制：假設整份文件只有一個內嵌字型（本報表如此）；多字型時 CMap 會互相覆蓋。
 */

function hexToUnits(hex: string): number[] {
  const clean = hex.replace(/\s+/g, "");
  const units: number[] = [];
  for (let i = 0; i + 4 <= clean.length; i += 4) units.push(parseInt(clean.slice(i, i + 4), 16));
  return units;
}

/** UTF-16BE 的十六進位字串 → 字串（ToUnicode 的目的端）。 */
function utf16Hex(hex: string): string {
  return hexToUnits(hex)
    .map((u) => String.fromCharCode(u))
    .join("");
}

function streamsOf(pdf: Buffer): string[] {
  const latin = pdf.toString("latin1");
  const out: string[] = [];
  const re = /(?<!end)stream\r?\n/g;
  for (let m = re.exec(latin); m; m = re.exec(latin)) {
    const start = m.index + m[0].length;
    const end = latin.indexOf("endstream", start);
    if (end < 0) break;
    const raw = pdf.subarray(start, end);
    try {
      out.push(inflateSync(raw).toString("latin1"));
    } catch {
      out.push(raw.toString("latin1")); // 沒壓縮（或不是 Flate）：原樣留著，後面的分類會自己篩掉
    }
    re.lastIndex = end;
  }
  return out;
}

function parseCMap(text: string, into: Map<number, string>): void {
  for (const block of text.matchAll(/beginbfchar([\s\S]*?)endbfchar/g)) {
    for (const m of block[1].matchAll(/<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>/g)) into.set(parseInt(m[1], 16), utf16Hex(m[2]));
  }
  for (const block of text.matchAll(/beginbfrange([\s\S]*?)endbfrange/g)) {
    for (const m of block[1].matchAll(/<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(?:<([0-9A-Fa-f]+)>|\[([^\]]*)\])/g)) {
      const lo = parseInt(m[1], 16);
      const hi = parseInt(m[2], 16);
      if (m[3] !== undefined) {
        const base = utf16Hex(m[3]);
        for (let c = lo; c <= hi; c += 1) into.set(c, base.slice(0, -1) + String.fromCharCode(base.charCodeAt(base.length - 1) + (c - lo)));
      } else {
        const list = [...(m[4] ?? "").matchAll(/<([0-9A-Fa-f]+)>/g)].map((x) => utf16Hex(x[1]));
        list.forEach((s, i) => into.set(lo + i, s));
      }
    }
  }
}

/** 字面字串 `(…)` 的內文（已去掉外層括號）→ 位元組：處理 `\n \r \t \b \f \( \) \\` 與 `\ddd` 八進位跳脫。 */
function literalBytes(body: string): number[] {
  const out: number[] = [];
  const simple: Record<string, number> = { n: 10, r: 13, t: 9, b: 8, f: 12 };
  for (let i = 0; i < body.length; i += 1) {
    const c = body[i];
    if (c !== "\\") {
      out.push(body.charCodeAt(i) & 0xff);
      continue;
    }
    const next = body[i + 1] ?? "";
    const octal = /^[0-7]{1,3}/.exec(body.slice(i + 1, i + 4));
    if (octal) {
      out.push(parseInt(octal[0], 8) & 0xff);
      i += octal[0].length;
    } else if (next in simple) {
      out.push(simple[next]);
      i += 1;
    } else {
      out.push(next.charCodeAt(0) & 0xff); // `\(`、`\)`、`\\`，或換行接續
      i += 1;
    }
  }
  return out;
}

/** 兩個位元組一組的字形編號（Identity-H）。PDFBox 在「所有位元組都是 ASCII」時把 2 位元組編號寫成字面字串（含 NUL），否則寫成十六進位。 */
function glyphsOf(bytes: number[]): number[] {
  const units: number[] = [];
  for (let i = 0; i + 1 < bytes.length; i += 2) units.push((bytes[i] << 8) | bytes[i + 1]);
  return units;
}

/** PDF 內所有顯示出來的文字（依內容串流出現順序；每個 Tj／TJ 之間以換行隔開）。 */
export function extractPdfText(pdf: Buffer): string {
  const decoded = streamsOf(pdf);
  const cmap = new Map<number, string>();
  for (const s of decoded) if (s.includes("beginbfchar") || s.includes("beginbfrange")) parseCMap(s, cmap);
  const lines: string[] = [];
  for (const s of decoded) {
    // 內容串流：有文字運算子、且不是二進位（字型檔、xref 串流含 NUL 與大量高位元組）
    if (!/\bBT\b/.test(s) || !/\b(Tj|TJ)\b/.test(s) || !/^[\x20-\x7e\r\n\t]{20}/.test(s)) continue;
    for (const op of s.matchAll(/(\[(?:[^\]\\]|\\.)*\]|<[0-9A-Fa-f\s]+>|\((?:[^()\\]|\\[\s\S])*\))\s*T[jJ]/g)) {
      let line = "";
      for (const tok of op[1].matchAll(/<([0-9A-Fa-f\s]+)>|\(((?:[^()\\]|\\[\s\S])*)\)/g)) {
        const units = tok[1] !== undefined ? hexToUnits(tok[1]) : glyphsOf(literalBytes(tok[2] ?? ""));
        line += units.map((g) => cmap.get(g) ?? "").join("");
      }
      lines.push(line);
    }
  }
  return lines.join("\n");
}
