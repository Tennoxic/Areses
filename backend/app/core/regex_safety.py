import re

MAX_PATTERN_LENGTH = 200
MAX_SCAN_LENGTH = 5000

_CATASTROPHIC_BACKTRACKING_SHAPE = re.compile(
    r"\([^()]*[+*]\)[+*]|\([^()]*\{\d*,\}[^()]*\)[+*]"
)


def is_unsafe_pattern(pattern: str) -> bool:
    if len(pattern) > MAX_PATTERN_LENGTH:
        return True
    return _CATASTROPHIC_BACKTRACKING_SHAPE.search(pattern) is not None


def safe_search(pattern: str, value: str | None) -> bool:
    if value is None:
        return False
    if is_unsafe_pattern(pattern):
        return False
    try:
        return re.search(pattern, value[:MAX_SCAN_LENGTH], re.IGNORECASE) is not None
    except re.error:
        return False
