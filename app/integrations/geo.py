from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import get_settings


@dataclass(frozen=True)
class GeoResult:
    country: str
    city: str | None
    provider: str


class GeoProvider(Protocol):
    name: str

    def lookup(self, ip: str) -> GeoResult | None: ...


class NullGeoProvider:
    """Safe local default; replace with HTTP adapters only for manual development."""
    name = "disabled"

    def lookup(self, ip: str) -> GeoResult | None:
        return None


class IpApiProvider:
    """Development adapter for ip-api.com. It has no credentials or user data."""
    name = "ip-api"

    def lookup(self, ip: str) -> GeoResult | None:
        response = httpx.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,country,city"},
            timeout=get_settings().geo_request_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "success" or not data.get("country"):
            return None
        return GeoResult(country=data["country"], city=data.get("city"), provider=self.name)


class IpWhoIsProvider:
    """Fallback development adapter for ipwho.is. It is intentionally best-effort."""
    name = "ipwho.is"

    def lookup(self, ip: str) -> GeoResult | None:
        response = httpx.get(f"https://ipwho.is/{ip}", timeout=get_settings().geo_request_timeout_seconds)
        response.raise_for_status()
        data = response.json()
        if data.get("success") is False or not data.get("country"):
            return None
        return GeoResult(country=data["country"], city=data.get("city"), provider=self.name)


def configured_geo_providers() -> list[GeoProvider]:
    """Keep network enrichment opt-in so local test/demo runs remain deterministic."""
    if not get_settings().geo_enrichment_enabled:
        return [NullGeoProvider()]
    return [IpApiProvider(), IpWhoIsProvider()]


def resolve_geo(ip: str, providers: list[GeoProvider]) -> GeoResult | None:
    for provider in providers:
        try:
            result = provider.lookup(ip)
            if result:
                return result
        except Exception:
            # An enrichment dependency is never allowed to fail lead capture.
            continue
    return None
