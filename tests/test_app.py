import app as app_module
import db

CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
IPHONE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
)
BOT_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"


def test_index_renders(client, logged):
    resp = client.get("/", headers={"User-Agent": CHROME_UA})
    assert resp.status_code == 200
    assert str(app_module.WORK_MINUTES).encode() in resp.data


def test_index_logs_visit(client, logged):
    client.get(
        "/?x=1",
        headers={
            "User-Agent": CHROME_UA,
            "Accept-Language": "cs-CZ,cs;q=0.9",
            "Referer": "https://example.org/",
            "CF-Ray": "abc123-PRG",
        },
    )
    assert len(logged) == 1
    row = logged[0]
    assert row["method"] == "GET"
    assert row["path"] == "/"
    assert row["query_string"] == "x=1"
    assert row["user_agent"] == CHROME_UA
    assert row["accept_language"] == "cs-CZ,cs;q=0.9"
    assert row["referrer"] == "https://example.org/"
    assert row["cf_ray"] == "abc123-PRG"
    assert row["browser_name"] == "Chrome"
    assert row["os_name"] == "Windows"
    assert row["device_type"] == "pc"
    assert row["is_bot"] is False
    assert row["response_status_code"] == 200
    assert isinstance(row["duration_ms"], int) and row["duration_ms"] >= 0
    assert row["raw_headers"]["User-Agent"] == CHROME_UA
    # Všechny sloupce z INSERTu musí být v záznamu přítomné.
    for column in db.INSERT_SQL.split("VALUES")[0].split("(")[1].split(")")[0].split(","):
        assert column.strip() in row


def test_device_type_mobile_and_bot(client, logged):
    client.get("/", headers={"User-Agent": IPHONE_UA})
    client.get("/", headers={"User-Agent": BOT_UA})
    assert logged[0]["device_type"] == "mobile"
    assert logged[0]["os_name"] == "iOS"
    assert logged[1]["device_type"] == "bot"
    assert logged[1]["is_bot"] is True


def test_404_is_logged_with_status(client, logged):
    resp = client.get("/neexistuje", headers={"User-Agent": CHROME_UA})
    assert resp.status_code == 404
    assert logged[0]["response_status_code"] == 404


def test_static_not_logged(client, logged):
    resp = client.get("/static/style.css", headers={"User-Agent": CHROME_UA})
    assert resp.status_code == 200
    assert logged == []


def test_healthcheck_and_curl_not_logged(client, logged):
    client.get("/", headers={"User-Agent": "Python-urllib/3.12"})
    client.get("/", headers={"User-Agent": "curl/8.9.1"})
    assert logged == []


def test_visitor_cookie_set_once_and_reused(client, logged):
    first = client.get("/", headers={"User-Agent": CHROME_UA})
    cookie = first.headers.get("Set-Cookie", "")
    assert cookie.startswith(f"{app_module.VISITOR_COOKIE_NAME}=")
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie

    second = client.get("/", headers={"User-Agent": CHROME_UA})
    assert "Set-Cookie" not in second.headers
    assert logged[0]["visitor_id"] == logged[1]["visitor_id"]
    assert len(logged[0]["visitor_id"]) == 36


def test_client_ip_priority(client, logged):
    ua = {"User-Agent": CHROME_UA}
    client.get("/", headers={**ua, "CF-Connecting-IP": "1.1.1.1",
                             "X-Real-IP": "2.2.2.2", "X-Forwarded-For": "3.3.3.3"})
    client.get("/", headers={**ua, "X-Real-IP": "2.2.2.2", "X-Forwarded-For": "3.3.3.3"})
    client.get("/", headers={**ua, "X-Forwarded-For": "3.3.3.3, 10.0.0.1"})
    client.get("/", headers=ua, environ_base={"REMOTE_ADDR": "4.4.4.4"})
    assert [r["ip_address"] for r in logged] == ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"]
    assert logged[2]["forwarded_for"] == "3.3.3.3, 10.0.0.1"


def test_cloudflare_geo_is_logged(client, logged):
    client.get("/", headers={
        "User-Agent": CHROME_UA,
        "CF-Connecting-IP": "5.5.5.5",
        "CF-IPCountry": "CZ",
        "CF-IPCity": "Brno",
    })
    assert logged[0]["country_code"] == "CZ"
    assert logged[0]["city"] == "Brno"
    assert logged[0]["geo_source"] == "cloudflare"


def test_logging_failure_does_not_break_response(client, monkeypatch):
    def boom(_data):
        raise RuntimeError("db down")

    monkeypatch.setattr(db, "log_visit", boom)
    resp = client.get("/", headers={"User-Agent": CHROME_UA})
    assert resp.status_code == 200


def test_sensitive_headers_not_stored(client, logged):
    client.set_cookie("visitor_id", "11111111-1111-1111-1111-111111111111")
    client.get("/", headers={
        "User-Agent": CHROME_UA,
        "Authorization": "Bearer secret",
        "Proxy-Authorization": "Basic secret",
    })
    headers = logged[0]["raw_headers"]
    assert "Cookie" not in headers
    assert "Authorization" not in headers
    assert "Proxy-Authorization" not in headers
    assert headers["User-Agent"] == CHROME_UA
    assert logged[0]["visitor_id"] == "11111111-1111-1111-1111-111111111111"
