"""SSRF guard — ported & adapted from EventRelay apps/web/src/lib/ssrf-guard.ts

Rejects non-public hosts, private/link-local/CGNAT/metadata IPs, and non-http(s)
schemes before any outbound fetch or yt-dlp call.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import socket
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal", "metadata"}
YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}


def _is_private_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        )
    except ValueError:
        return True  # fail closed


async def assert_public_http_url(url: str) -> str:
    """Validate that url is a public http(s) URL. Returns normalized URL or raises."""
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValueError(f"Invalid URL: {e}") from e

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Blocked URL scheme: {parsed.scheme}")

    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise ValueError("URL missing host")

    if host in BLOCKED_HOSTNAMES or host.endswith(".internal") or host.endswith(".local"):
        raise ValueError("Blocked host")

    # Literal IP?
    try:
        if _is_private_ip(host):
            raise ValueError("Blocked private IP literal")
        return url
    except ValueError as e:
        if "private" in str(e).lower() or "blocked" in str(e).lower():
            raise
        # not an IP literal — continue to DNS

    # DNS resolve and check every A/AAAA
    try:
        loop = asyncio.get_event_loop()
        infos = await loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        logger.error("[ssrf] DNS lookup failed for %s: %s", host, e)
        raise ValueError("Host does not resolve to a public address") from e

    if not infos:
        raise ValueError("Host does not resolve to a public address")

    for info in infos:
        addr = info[4][0]
        if _is_private_ip(addr):
            logger.error("[ssrf] host %s resolved to non-public %s", host, addr)
            raise ValueError("Host does not resolve to a public address")

    return url


async def assert_public_youtube_url(url: str) -> str:
    """Strict YouTube-only public URL check (used by Ingest)."""
    normalized = await assert_public_http_url(url)
    parsed = urlparse(normalized)
    host = (parsed.hostname or "").lower().rstrip(".")
    # Allow bare youtube + www + youtu.be + nocookie
    if host not in YOUTUBE_HOSTS and not host.endswith(".youtube.com"):
        raise ValueError(f"Only YouTube URLs are accepted (got host={host})")
    return normalized
