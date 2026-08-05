import feedparser

from app.services.scheduler import _feed_provided_content

_FEED_WITH_CONTENT_ENCODED = """<?xml version="1.0"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel><title>Feed</title><link>https://example.test</link>
<item>
  <title>Entry</title>
  <link>https://example.test/a1</link>
  <content:encoded><![CDATA[<p>Full body text</p>]]></content:encoded>
  <description>Short summary text</description>
</item>
</channel></rss>"""

_FEED_WITH_SUMMARY_ONLY = """<?xml version="1.0"?>
<rss version="2.0">
<channel><title>Feed</title><link>https://example.test</link>
<item>
  <title>Entry</title>
  <link>https://example.test/a1</link>
  <description>Only a short summary here</description>
</item>
</channel></rss>"""

_FEED_WITH_NOTHING = """<?xml version="1.0"?>
<rss version="2.0">
<channel><title>Feed</title><link>https://example.test</link>
<item>
  <title>Entry</title>
  <link>https://example.test/a1</link>
</item>
</channel></rss>"""

_FEED_WITH_SCRIPT_IN_CONTENT = """<?xml version="1.0"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel><title>Feed</title><link>https://example.test</link>
<item>
  <title>Entry</title>
  <link>https://example.test/a1</link>
  <content:encoded><![CDATA[<p>Body</p><script>alert(1)</script>]]></content:encoded>
</item>
</channel></rss>"""


def _first_entry(xml):
    return feedparser.parse(xml).entries[0]


def test_prefers_content_encoded_over_description():
    result = _feed_provided_content(_first_entry(_FEED_WITH_CONTENT_ENCODED))
    assert "Full body text" in result
    assert "Short summary text" not in result


def test_falls_back_to_summary_when_no_content_encoded():
    result = _feed_provided_content(_first_entry(_FEED_WITH_SUMMARY_ONLY))
    assert "Only a short summary here" in result


def test_returns_none_when_entry_has_neither():
    assert _feed_provided_content(_first_entry(_FEED_WITH_NOTHING)) is None


def test_output_is_sanitized():
    result = _feed_provided_content(_first_entry(_FEED_WITH_SCRIPT_IN_CONTENT))
    assert "<script>" not in result
    assert "alert" not in result
    assert "Body" in result
