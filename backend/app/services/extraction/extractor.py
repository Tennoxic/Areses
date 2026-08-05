from curl_cffi.requests import AsyncSession as CurlAsyncSession
from readability import Document
from trafilatura import extract as trafilatura_extract

from app.services.net_guard import UnsafeUrlError, assert_safe_url, safe_get
from app.services.sanitizer import sanitize_html

_USER_AGENT = "ARESES/0.1 (+https://github.com/areses)"
_MIN_CONTENT_LENGTH = 200


async def _fetch_html_httpx(url: str, auth: tuple[str, str] | None) -> str | None:
    response = await safe_get(url, auth=auth, timeout=15.0, headers={"User-Agent": _USER_AGENT})
    response.raise_for_status()
    return response.text


async def _fetch_html_curl_cffi(url: str, auth: tuple[str, str] | None) -> str | None:
    assert_safe_url(url)
    async with CurlAsyncSession() as session:
        response = await session.get(
            url,
            impersonate="chrome",
            timeout=15.0,
            headers={"User-Agent": _USER_AGENT},
            auth=auth,
            allow_redirects=False,
        )
        response.raise_for_status()
        return response.text


async def _fetch_html(url: str, auth: tuple[str, str] | None) -> str | None:
    try:
        return await _fetch_html_httpx(url, auth)
    except Exception:
        pass
    try:
        return await _fetch_html_curl_cffi(url, auth)
    except Exception:
        return None


def _text_length(html: str) -> int:
    import re

    return len(re.sub(r"<[^>]+>", " ", html).strip())


async def _extract_with_playwright(url: str) -> str | None:
    try:
        from playwright.async_api import async_playwright
    except Exception:
        return None
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(user_agent=_USER_AGENT)
            await page.goto(url, timeout=15000, wait_until="networkidle")
            html = await page.content()
            await browser.close()
            content = trafilatura_extract(html, output_format="html", include_images=True)
            if content and _text_length(content) > _MIN_CONTENT_LENGTH:
                return sanitize_html(content)
            content = Document(html).summary()
            if content and _text_length(content) > _MIN_CONTENT_LENGTH:
                return sanitize_html(content)
            return None
    except Exception:
        return None


async def extract_article_content(
    url: str, auth: tuple[str, str] | None = None
) -> str | None:
    try:
        assert_safe_url(url)
    except UnsafeUrlError:
        return None

    html = await _fetch_html(url, auth)
    if html is None:
        return await _extract_with_playwright(url)

    content = trafilatura_extract(html, output_format="html", include_images=True)
    if content and _text_length(content) > _MIN_CONTENT_LENGTH:
        return sanitize_html(content)

    try:
        readable_content = Document(html).summary()
        if readable_content and _text_length(readable_content) > _MIN_CONTENT_LENGTH:
            return sanitize_html(readable_content)
    except Exception:
        pass

    return await _extract_with_playwright(url)
