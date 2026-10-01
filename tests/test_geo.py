import geo


class FakeResp:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def test_cloudflare_headers():
    result = geo.get_geo("8.8.8.8", {
        "CF-IPCountry": "CZ",
        "CF-IPCity": "Praha",
        "CF-Region": "Prague",
        "CF-Postal-Code": "11000",
        "CF-IPLatitude": "50.08",
        "CF-IPLongitude": "14.42",
        "CF-Timezone": "Europe/Prague",
    })
    assert result["geo_source"] == "cloudflare"
    assert result["country_code"] == "CZ"
    assert result["city"] == "Praha"
    assert result["latitude"] == "50.08"
    assert set(result) == set(geo.EMPTY_GEO)


def test_cloudflare_unknown_country_falls_back(monkeypatch):
    calls = []
    monkeypatch.setattr(geo, "_from_ip_api", lambda ip: calls.append(ip))
    for code in ("XX", "T1"):
        geo._cache.clear()
        result = geo.get_geo("8.8.8.8", {"CF-IPCountry": code})
        assert result == geo.EMPTY_GEO
    assert calls == ["8.8.8.8", "8.8.8.8"]


def test_ip_api_success(monkeypatch):
    def fake_get(url, params, timeout):
        assert url == "http://ip-api.com/json/8.8.8.8"
        return FakeResp({
            "status": "success", "country": "United States", "countryCode": "US",
            "regionName": "Virginia", "city": "Ashburn", "zip": "20149",
            "lat": 39.03, "lon": -77.5, "timezone": "America/New_York",
            "isp": "Google LLC", "org": "Google Public DNS", "as": "AS15169 Google LLC",
        })

    monkeypatch.setattr(geo.requests, "get", fake_get)
    result = geo.get_geo("8.8.8.8", {})
    assert result["geo_source"] == "ip-api"
    assert result["country"] == "United States"
    assert result["asn"] == "AS15169 Google LLC"
    assert set(result) == set(geo.EMPTY_GEO)


def test_ip_api_fail_status(monkeypatch):
    monkeypatch.setattr(geo.requests, "get",
                        lambda *a, **k: FakeResp({"status": "fail", "message": "private range"}))
    assert geo.get_geo("10.0.0.1", {}) == geo.EMPTY_GEO


def test_ip_api_exception(monkeypatch):
    def fail(*a, **k):
        raise geo.requests.ConnectionError("offline")

    monkeypatch.setattr(geo.requests, "get", fail)
    assert geo.get_geo("8.8.8.8", {}) == geo.EMPTY_GEO


def test_localhost_skips_api(monkeypatch):
    def fail(*a, **k):
        raise AssertionError("API nemá být voláno pro localhost")

    monkeypatch.setattr(geo.requests, "get", fail)
    assert geo.get_geo("127.0.0.1", {}) == geo.EMPTY_GEO
    assert geo.get_geo("::1", {}) == geo.EMPTY_GEO
    assert geo.get_geo("", {}) == geo.EMPTY_GEO


def test_result_is_cached(monkeypatch):
    calls = []

    def fake_get(*a, **k):
        calls.append(1)
        return FakeResp({"status": "success", "countryCode": "DE"})

    monkeypatch.setattr(geo.requests, "get", fake_get)
    geo.get_geo("9.9.9.9", {})
    geo.get_geo("9.9.9.9", {})
    assert len(calls) == 1


def test_empty_geo_not_shared_mutable(monkeypatch):
    monkeypatch.setattr(geo, "_from_ip_api", lambda ip: None)
    result = geo.get_geo("8.8.4.4", {})
    result["city"] = "X"
    assert geo.EMPTY_GEO["city"] is None


def test_cache_is_bounded(monkeypatch):
    monkeypatch.setattr(geo, "_CACHE_MAX_SIZE", 3)
    monkeypatch.setattr(geo, "_from_ip_api", lambda ip: None)
    for i in range(10):
        geo.get_geo(f"10.0.0.{i}", {})
        assert len(geo._cache) <= 3
    assert "10.0.0.9" in geo._cache
