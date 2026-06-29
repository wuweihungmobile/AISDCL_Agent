import pytest

from strutils import slugify, truncate


def test_slugify_basic_space():
    assert slugify("Hello World") == "hello-world"


def test_slugify_punctuation_removed():
    assert slugify("Hello, World!") == "hello-world"


def test_slugify_underscores_and_spaces_to_hyphen():
    assert slugify("  Hello___World  ") == "hello-world"


def test_slugify_collapse_consecutive_hyphens():
    assert slugify("Hello---World") == "hello-world"


def test_slugify_mixed_underscore_and_space():
    assert slugify("foo_bar baz") == "foo-bar-baz"


def test_slugify_only_underscores_returns_empty():
    assert slugify("___") == ""


def test_slugify_only_hyphens_returns_empty():
    assert slugify("---") == ""


def test_slugify_only_punctuation_returns_empty():
    assert slugify("!!!") == ""


def test_slugify_empty_string():
    assert slugify("") == ""


def test_slugify_single_char():
    assert slugify("a") == "a"


def test_slugify_alphanumeric_with_space():
    assert slugify("A1 B2") == "a1-b2"


def test_slugify_strips_non_ascii():
    assert slugify("café") == "caf"


def test_slugify_strips_leading_and_trailing_spaces():
    assert slugify("  leading and trailing  ") == "leading-and-trailing"


def test_slugify_strips_leading_and_trailing_hyphens():
    assert slugify("--hello--") == "hello"


def test_slugify_tabs_and_newlines_as_whitespace():
    assert slugify("hello\tworld\nfoo") == "hello-world-foo"


def test_slugify_uppercase_to_lowercase():
    assert slugify("HELLO") == "hello"


def test_slugify_digits_kept():
    assert slugify("123") == "123"


def test_slugify_no_consecutive_hyphens_in_output():
    result = slugify("a___b   c---d!!!e")
    assert "--" not in result
    assert result == "a-b-c-de"


def test_slugify_output_does_not_start_or_end_with_hyphen():
    result = slugify("---hello world---")
    assert not result.startswith("-")
    assert not result.endswith("-")
    assert result == "hello-world"


def test_slugify_returns_str_type():
    assert isinstance(slugify(""), str)
    assert isinstance(slugify("Hello"), str)


# ----------------------------- truncate tests -----------------------------


def test_truncate_shorter_than_n_returns_original():
    assert truncate("hello", 10) == "hello"


def test_truncate_equal_to_n_returns_original():
    assert truncate("hello", 5) == "hello"


def test_truncate_longer_than_n_uses_ellipsis():
    assert truncate("hello world", 8) == "hello w…"


def test_truncate_n_equals_1_with_truncation():
    assert truncate("abc", 1) == "…"


def test_truncate_n_equals_2_with_truncation():
    assert truncate("abcdef", 2) == "a…"


def test_truncate_output_length_equals_n_when_truncated():
    result = truncate("abcdefghij", 6)
    assert len(result) == 6
    assert result == "abcde…"


def test_truncate_empty_string_with_positive_n():
    assert truncate("", 5) == ""


def test_truncate_empty_string_with_n_one():
    assert truncate("", 1) == ""


def test_truncate_n_zero_raises_value_error():
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_n_raises_value_error():
    with pytest.raises(ValueError):
        truncate("hello", -1)


def test_truncate_negative_n_with_empty_string_raises():
    with pytest.raises(ValueError):
        truncate("", -1)


def test_truncate_uses_single_unicode_ellipsis_not_three_dots():
    result = truncate("hello world", 8)
    assert "…" in result
    assert "..." not in result
    assert len(result) == 8


def test_truncate_no_truncation_keeps_original_unchanged():
    s = "short"
    assert truncate(s, 100) == s


def test_truncate_returns_str_type():
    assert isinstance(truncate("hello", 3), str)
    assert isinstance(truncate("", 1), str)


def test_truncate_does_not_append_ellipsis_when_not_truncating():
    assert truncate("abc", 3) == "abc"
    assert truncate("abc", 5) == "abc"
    assert "…" not in truncate("abc", 3)
