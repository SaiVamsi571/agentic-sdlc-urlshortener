"""
URL Validation, SSRF Protection, Loop Detection, and Reserved Alias Filtering.
"""
import ipaddress
import re
from urllib.parse import urlparse
from typing import Optional, Set

from src.constants import (
    ALIAS_PATTERN,
    ALLOWED_URL_SCHEMES,
    BLOCKED_HOSTNAMES,
    DEFAULT_SERVICE_DOMAINS,
    MAX_URL_LENGTH,
    RESERVED_ALIASES,
)

ALIAS_REGEX = re.compile(ALIAS_PATTERN)


class ValidationError(Exception):
    """Raised when URL or alias validation fails."""
    pass


class URLValidator:
    """Validates destination URLs for security, correctness, and self-loop prevention."""

    def __init__(self, service_domains: Optional[Set[str]] = None):
        self.service_domains = service_domains or set(DEFAULT_SERVICE_DOMAINS)

    def validate_url(self, url: str) -> str:
        """
        Validates URL syntax, protocol, SSRF targets, and self-loopback redirects.
        Returns the sanitized, normalized URL.
        """
        if not url or len(url) > MAX_URL_LENGTH:
            raise ValidationError(
                f"URL must be between 1 and {MAX_URL_LENGTH} characters."
            )

        parsed = urlparse(url.strip())

        # 1. Scheme check
        if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES:
            raise ValidationError(
                f"Invalid URL scheme. Only {', '.join(s.upper() for s in ALLOWED_URL_SCHEMES)} are permitted."
            )

        # 2. Host check
        host = (parsed.hostname or "").lower()
        if not host:
            raise ValidationError("URL must include a valid host.")

        if host in BLOCKED_HOSTNAMES:
            raise ValidationError(
                f"Prohibited host: '{host}' is blocked for SSRF protection."
            )

        # 3. Private IP subnet checks
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise ValidationError(
                    f"Prohibited destination: '{host}' is in a private/restricted IP range."
                )
        except ValueError:
            # Not a raw IP literal, it's a domain name - acceptable
            pass

        # 4. Self-loop redirect prevention
        port_suffix = f":{parsed.port}" if parsed.port else ""
        host_with_port = f"{host}{port_suffix}"
        if host_with_port in self.service_domains or host in self.service_domains:
            raise ValidationError(
                "Self-referencing loop detected: Cannot shorten a URL pointing to this shortener service."
            )

        return parsed.geturl()

    def validate_custom_alias(self, alias: Optional[str]) -> Optional[str]:
        """Validates custom alias format and reserved keyword conflicts."""
        if not alias:
            return None

        alias_clean = alias.strip()
        if not ALIAS_REGEX.match(alias_clean):
            raise ValidationError(
                "Custom alias must be 3-30 alphanumeric characters, dashes, or underscores."
            )

        if alias_clean.lower() in RESERVED_ALIASES:
            raise ValidationError(
                f"The alias '{alias_clean}' is a system-reserved keyword and cannot be claimed."
            )

        return alias_clean
