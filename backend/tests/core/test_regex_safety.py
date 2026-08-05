from app.core.regex_safety import (
    MAX_PATTERN_LENGTH,
    is_unsafe_pattern,
    safe_search,
)


def test_is_unsafe_pattern_flags_nested_quantifier_backtracking_shape():
    assert is_unsafe_pattern("(a+)+") is True


def test_is_unsafe_pattern_flags_bounded_repetition_backtracking_shape():
    assert is_unsafe_pattern("(a{2,}b)+") is True


def test_is_unsafe_pattern_flags_oversized_pattern():
    assert is_unsafe_pattern("a" * (MAX_PATTERN_LENGTH + 1)) is True


def test_is_unsafe_pattern_allows_ordinary_patterns():
    assert is_unsafe_pattern("^breaking news") is False
    assert is_unsafe_pattern("[Ee]lection\\s+result") is False


def test_safe_search_matches_ordinary_pattern():
    assert safe_search("elon musk", "Elon Musk announces new project") is True


def test_safe_search_is_case_insensitive():
    assert safe_search("BREAKING", "breaking: markets open lower") is True


def test_safe_search_returns_false_for_no_match():
    assert safe_search("quantum computing", "local weather forecast") is False


def test_safe_search_returns_false_for_none_value():
    assert safe_search("anything", None) is False


def test_safe_search_refuses_unsafe_pattern_instead_of_hanging():
    assert safe_search("(a+)+$", "a" * 40) is False


def test_safe_search_returns_false_on_invalid_regex_syntax():
    assert safe_search("(unclosed", "some text") is False


def test_safe_search_truncates_oversized_input_instead_of_scanning_it_all():
    huge_value = "x" * 10_000 + "needle"
    assert safe_search("needle", huge_value) is False
