"""Zjištění geolokace návštěvníka z Cloudflare hlaviček nebo externího API."""
import time

import requests

# Jednoduchá in-memory cache, aby se nevolal externí API pro stejnou IP opakovaně.
_CACHE_TTL = 3600  # 1 hodina
_CACHE_MAX_SIZE = 10_000  # po překročení se cache vyprázdní
_cache: dict[str, tuple[float, dict]] = {}

EMPTY_GEO = {
    "country": None,
    "country_code": None,
    "region": None,
    "city": None,
    "postal_code": None,
    "latitude": None,
    "longitude": None,
    "timezone": None,
    "isp": None,
    "org": None,
    "asn": None,
    "geo_source": None,
}


def _from_cloudflare_headers(headers) -> dict | None:
    country_code = headers.get("CF-IPCountry")
    if not country_code or country_code in ("XX", "T1"):
        return None
    return {
        "country": None,
        "country_code": country_code,
        "region": headers.get("CF-Region") or headers.get("CF-Region-Code"),
        "city": headers.get("CF-IPCity"),
        "postal_code": headers.get("CF-Postal-Code"),
        "latitude": headers.get("CF-IPLatitude"),
        "longitude": headers.get("CF-IPLongitude"),
        "timezone": headers.get("CF-Timezone"),
        "isp": None,
        "org": None,
        "asn": None,
        "geo_source": "cloudflare",
    }


def _from_ip_api(ip: str) -> dict | None:
    if not ip or ip in ("127.0.0.1", "::1"):
        return None
    try:
        resp = requests.get(
            f"http://ip-api.com/json/{ip}",
            params={
                "fields": "status,country,countryCode,regionName,city,zip,"
                "lat,lon,timezone,isp,org,as"
            },
            timeout=2,
        )
        data = resp.json()
    except Exception:  # noqa: BLE001
        return None
    if data.get("status") != "success":
        return None
    return {
        "country": data.get("country"),
        "country_code": data.get("countryCode"),
        "region": data.get("regionName"),
        "city": data.get("city"),
        "postal_code": data.get("zip"),
        "latitude": data.get("lat"),
        "longitude": data.get("lon"),
        "timezone": data.get("timezone"),
        "isp": data.get("isp"),
        "org": data.get("org"),
        "asn": data.get("as"),
        "geo_source": "ip-api",
    }


def get_geo(ip: str, headers) -> dict:
    """Vrátí geolokační údaje: nejprve Cloudflare hlavičky, jinak fallback na ip-api.com."""
    cached = _cache.get(ip)
    if cached and time.time() - cached[0] < _CACHE_TTL:
        return cached[1]

    geo = _from_cloudflare_headers(headers) or _from_ip_api(ip) or dict(EMPTY_GEO)
    if len(_cache) >= _CACHE_MAX_SIZE:
        _cache.clear()
    _cache[ip] = (time.time(), geo)
    return geo
