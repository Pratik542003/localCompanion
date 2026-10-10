"""Enforce the on-device boundary before a client can make a request."""
from urllib.parse import urlsplit
import ipaddress


def require_local_url(url: str) -> str:
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    try:
        local = ipaddress.ip_address(host).is_loopback
    except ValueError:
        local = host.lower() == "localhost"
    if (parsed.scheme not in {"http", "https"} or not local
            or parsed.username or parsed.password):
        raise ValueError("Reasoning and speech servers must run on this device (localhost).")
    return url.rstrip("/")


def require_lookup_url(url: str, hostname: str) -> str:
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname != hostname
            or parsed.username or parsed.password or parsed.port not in (None, 443)):
        raise ValueError(f"This lookup provider is restricted to https://{hostname}.")
    return url.rstrip("/")
