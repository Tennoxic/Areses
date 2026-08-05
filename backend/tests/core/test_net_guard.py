import pytest

from app.services.net_guard import UnsafeUrlError, assert_safe_url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://localhost/",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://[::1]/",
        "ftp://example.com/",
        "file:///etc/passwd",
    ],
)
def test_assert_safe_url_blocks_private_and_disallowed_targets(url):
    with pytest.raises(UnsafeUrlError):
        assert_safe_url(url)


def test_assert_safe_url_allows_public_host():
    assert_safe_url("http://example.com/feed.xml") is None
