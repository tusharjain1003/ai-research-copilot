import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

ALLOWED_SCHEMES = {"http", "https"}


def validate_external_url(url: str) -> str:
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(
            f"URL scheme '{parsed.scheme}' is not allowed. "
            "Only http and https URLs are supported."
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must have a valid hostname.")

    try:
        addrinfo = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise ValueError(
            f"Could not resolve hostname '{hostname}': {e}"
        )

    seen: set[str] = set()
    for family, _, _, _, sockaddr in addrinfo:
        ip_str = sockaddr[0]
        if ip_str in seen:
            continue
        seen.add(ip_str)

        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue

        if ip.is_loopback:
            raise ValueError(
                f"URL resolves to a loopback address ({ip_str}). "
                "External requests to loopback addresses are not allowed."
            )
        if ip.is_link_local:
            raise ValueError(
                f"URL resolves to a link-local address ({ip_str}). "
                "External requests to link-local addresses are not allowed."
            )
        if ip.is_unspecified:
            raise ValueError(
                f"URL resolves to an unspecified address ({ip_str}). "
                "External requests to unspecified addresses are not allowed."
            )
        if ip.is_multicast:
            raise ValueError(
                f"URL resolves to a multicast address ({ip_str}). "
                "External requests to multicast addresses are not allowed."
            )
        if ip.is_private:
            raise ValueError(
                f"URL resolves to a private address ({ip_str}). "
                "External requests to private addresses are not allowed."
            )
        if ip.is_reserved:
            raise ValueError(
                f"URL resolves to a reserved address ({ip_str}). "
                "External requests to reserved addresses are not allowed."
            )

    return url
