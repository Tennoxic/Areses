from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, status

_ALLOWED_SCHEMES = {"http", "https"}
_MAX_REDIRECTS = 5


class UnsafeUrlError(Exception):
    pass


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or (ip.version == 6 and ip.is_site_local)
    )


def assert_safe_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"scheme not allowed: {parsed.scheme!r}")
    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("URL has no hostname")

    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"could not resolve host: {host}") from exc

    for _family, _, _, _, sockaddr in infos:
        raw_ip = sockaddr[0]
        try:
            ip = ipaddress.ip_address(raw_ip)
        except ValueError:
            raise UnsafeUrlError(f"unparseable resolved address: {raw_ip}") from None
        if _is_blocked_ip(ip):
            raise UnsafeUrlError(f"host {host!r} resolves to a disallowed address: {ip}")


async def safe_get(
    url: str,
    *,
    auth: tuple[str, str] | None = None,
    timeout: float = 15.0,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    current_url = url
    async with httpx.AsyncClient(follow_redirects=False, timeout=timeout, auth=auth) as client:
        for _ in range(_MAX_REDIRECTS + 1):
            try:
                assert_safe_url(current_url)
            except UnsafeUrlError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail={
                        "code": "unsafe_url",
                        "message": "URL points to a disallowed host",
                    },
                ) from exc
            try:
                response = await client.get(current_url, headers=headers)
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail={
                        "code": "fetch_failed",
                        "message": f"could not fetch URL: {exc}",
                    },
                ) from exc
            if response.is_redirect:
                next_url = response.headers.get("location")
                if not next_url:
                    return response
                current_url = httpx.URL(current_url).join(next_url).human_repr()
                continue
            return response
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={"code": "too_many_redirects", "message": "too many redirects"},
    )
