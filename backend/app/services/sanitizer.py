from urllib.parse import urlparse

import nh3

_ALLOWED_TAGS = {
    "p", "br", "hr", "a", "b", "strong", "i", "em", "u", "s", "mark",
    "blockquote", "code", "pre", "ul", "ol", "li",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "img", "figure", "figcaption",
    "table", "thead", "tbody", "tr", "th", "td",
    "iframe",
}

_ALLOWED_ATTRS = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title", "loading"},
    "iframe": {"src", "width", "height", "frameborder", "allowfullscreen", "allow"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
}

_EMBED_HOST_ALLOWLIST = {
    "www.youtube.com",
    "youtube.com",
    "www.youtube-nocookie.com",
    "youtube-nocookie.com",
    "player.vimeo.com",
}


def _attribute_filter(tag: str, attr: str, value: str) -> str | None:
    if tag == "iframe" and attr == "src":
        host = urlparse(value).hostname or ""
        if host not in _EMBED_HOST_ALLOWLIST:
            return None
        return value
    return value


def sanitize_plain_text(text: str) -> str:
    if not text:
        return text
    cleaned = nh3.clean(text, tags=set(), clean_content_tags={"script", "style"})
    return cleaned.replace("\xa0", " ").replace("&nbsp;", " ").strip()


def strip_tags(html: str) -> str:
    if not html:
        return ""
    return nh3.clean(html, tags=set()).replace("\xa0", " ")


def sanitize_html(html: str) -> str:
    if not html:
        return html
    return nh3.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        attribute_filter=_attribute_filter,
        url_schemes={"http", "https"},
        link_rel="noopener noreferrer nofollow",
    )
