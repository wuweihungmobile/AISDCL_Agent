package com.aisdlc.console.domain.service;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 專案根與規格路徑的純字串運算（契約 §1.10.2、§1.10.8）。為什麼重要：Console 跑在 Linux 容器、專案路徑卻可能是 Windows 主機上的
 * {@code D:\work\proj} 或 UNC，用 {@code java.nio.file.Path} 在不同平台會得到不同答案——併入既有專案的「規格根在專案根之下」判定與核准凍結的
 * 「docs 相對專案根」換算，都必須在任何平台上同一個結果。
 */
class SpecPathsTest {

    @Test
    void bothSeparatorsAndTrailingSeparatorsAreTheSamePlace() {
        assertThat(SpecPaths.same("/work/proj", "/work/proj/")).isTrue();
        assertThat(SpecPaths.same("D:\\work\\proj\\", "D:/work/proj")).isTrue();
        assertThat(SpecPaths.same("  /work/proj  ", "/work/proj")).as("去前後空白").isTrue();
        assertThat(SpecPaths.same("/work/proj", "/work/proj2")).isFalse();
        assertThat(SpecPaths.same("/", "/")).isTrue();
        assertThat(SpecPaths.same("C:\\", "C:/")).as("磁碟機根保留").isTrue();
        assertThat(SpecPaths.same(null, "/x")).isFalse();
        assertThat(SpecPaths.same("/x", null)).isFalse();
    }

    @Test
    void posixPathsAreCaseSensitiveButWindowsStylePathsAreNot() {
        assertThat(SpecPaths.same("/work/Proj", "/work/proj")).isFalse();
        assertThat(SpecPaths.same("D:\\Work\\Proj", "d:/work/proj")).isTrue();
        assertThat(SpecPaths.same("\\\\Server\\Share\\x", "//server/share/X")).as("UNC 也不分大小寫").isTrue();
        assertThat(SpecPaths.same("D:/work", "/work")).as("任一個是 Windows 風格就不分大小寫，但路徑本身不同").isFalse();
    }

    @Test
    void relativeToKeepsTheChildsCaseAndOnlyAnswersForStrictDescendants() {
        assertThat(SpecPaths.relativeTo("/work/proj", "/work/proj/docs/a.md")).contains("docs/a.md");
        assertThat(SpecPaths.relativeTo("/work/proj/", "/work/proj/a.md")).contains("a.md");
        assertThat(SpecPaths.relativeTo("D:\\Work\\Proj", "d:/work/proj/Docs/A.md")).contains("Docs/A.md");
        assertThat(SpecPaths.relativeTo("/work/proj", "/work/proj")).as("相同不是 descendant").isEmpty();
        assertThat(SpecPaths.relativeTo("/work/proj", "/work/proj2/a.md")).as("前綴相同但不是目錄邊界").isEmpty();
        assertThat(SpecPaths.relativeTo("/work/proj", "/other/a.md")).isEmpty();
        assertThat(SpecPaths.relativeTo(null, "/x")).isEmpty();
        assertThat(SpecPaths.relativeTo("/x", null)).isEmpty();
        assertThat(SpecPaths.relativeTo("/", "/a.md")).as("根目錄的子孫").contains("a.md");
        assertThat(SpecPaths.relativeTo("/work/proj", "/work/proj//docs\\a.md")).as("重複與混用的分隔符").contains("docs/a.md");
    }

    @Test
    void isUnderAcceptsTheBaseItselfAndItsDescendants() {
        assertThat(SpecPaths.isUnder("/work/proj", "/work/proj")).isTrue();
        assertThat(SpecPaths.isUnder("/work/proj/spec", "/work/proj")).isTrue();
        assertThat(SpecPaths.isUnder("D:\\work\\proj\\spec", "d:/WORK/proj")).isTrue();
        assertThat(SpecPaths.isUnder("/work/other", "/work/proj")).isFalse();
        assertThat(SpecPaths.isUnder("/work", "/work/proj")).as("父目錄不在子目錄之下").isFalse();
    }

    @Test
    void parentOfKeepsTheSeparatorStyleAndHandlesRoots() {
        assertThat(SpecPaths.parentOf("/spec/cart.md")).isEqualTo("/spec");
        assertThat(SpecPaths.parentOf("D:\\a\\b.md")).isEqualTo("D:\\a");
        assertThat(SpecPaths.parentOf("/x.md")).isEqualTo("/");
        assertThat(SpecPaths.parentOf("D:\\x.md")).isEqualTo("D:\\");
        assertThat(SpecPaths.parentOf("x.md")).as("沒有分隔符").isEmpty();
        assertThat(SpecPaths.parentOf("  /a/b/c.md  ")).isEqualTo("/a/b");
    }
}
