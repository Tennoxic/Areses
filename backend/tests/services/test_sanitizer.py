from app.services.sanitizer import sanitize_html, sanitize_plain_text, strip_tags


def test_sanitize_plain_text_strips_all_markup():
    assert sanitize_plain_text("<b>Breaking</b> news") == "Breaking news"


def test_sanitize_plain_text_removes_script_and_its_content():
    assert sanitize_plain_text("<script>alert(1)</script>Headline") == "Headline"


def test_sanitize_plain_text_trims_surrounding_whitespace():
    assert sanitize_plain_text("  Title here  ") == "Title here"


def test_sanitize_plain_text_normalizes_nbsp_entity_to_space():
    assert sanitize_plain_text("Title\xa0here") == "Title here"


def test_sanitize_plain_text_passes_through_empty_string():
    assert sanitize_plain_text("") == ""


def test_sanitize_html_keeps_allowlisted_formatting_tags():
    result = sanitize_html("<p>Hello <b>world</b></p>")
    assert "<p>" in result
    assert "<b>world</b>" in result


def test_sanitize_html_strips_script_tags():
    result = sanitize_html("<p>Text</p><script>alert('xss')</script>")
    assert "<script>" not in result
    assert "alert" not in result


def test_sanitize_html_strips_inline_event_handlers():
    result = sanitize_html('<img src="x.jpg" onerror="alert(1)">')
    assert "onerror" not in result


def test_sanitize_html_strips_javascript_uri_links():
    result = sanitize_html('<a href="javascript:alert(1)">click</a>')
    assert "javascript:" not in result


def test_sanitize_html_allows_http_and_https_links():
    result = sanitize_html('<a href="https://example.com">link</a>')
    assert 'href="https://example.com"' in result


def test_sanitize_html_allows_youtube_iframe_embed():
    result = sanitize_html('<iframe src="https://www.youtube.com/embed/abc123"></iframe>')
    assert "<iframe" in result
    assert "youtube.com" in result


def test_sanitize_html_strips_iframe_from_disallowed_host():
    result = sanitize_html('<iframe src="https://evil.example.com/payload"></iframe>')
    assert "evil.example.com" not in result


def test_sanitize_html_passes_through_empty_string():
    assert sanitize_html("") == ""


def test_strip_tags_returns_plain_text_projection():
    assert strip_tags("<p>Hello <b>world</b></p>") == "Hello world"


def test_strip_tags_handles_empty_input():
    assert strip_tags("") == ""
