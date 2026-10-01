import time
import uuid

from flask import Flask, g, render_template, request
from user_agents import parse as parse_user_agent

import db
import geo

app = Flask(__name__)

# Pracovní doba: 8 hodin 30 minut
WORK_MINUTES = 8 * 60 + 30

VISITOR_COOKIE_NAME = "visitor_id"
VISITOR_COOKIE_MAX_AGE = 10 * 365 * 24 * 60 * 60  # 10 let

# Requesty s těmito User-Agenty (např. healthcheck) se do visits nelogují.
_SKIP_LOG_UA_PREFIXES = ("Python-urllib", "curl/")

# Citlivé hlavičky, které se do raw_headers neukládají.
_SENSITIVE_HEADERS = {"Cookie", "Authorization", "Proxy-Authorization"}


def _get_client_ip() -> str:
    return (
        request.headers.get("CF-Connecting-IP")
        or request.headers.get("X-Real-IP")
        or (request.headers.get("X-Forwarded-For", "").split(",")[0].strip())
        or request.remote_addr
        or ""
    )


@app.before_request
def _start_timer():
    g.start_time = time.time()


@app.after_request
def _log_visit(response):
    try:
        if request.path.startswith("/static/"):
            return response
        ua_string = request.headers.get("User-Agent", "")
        if ua_string.startswith(_SKIP_LOG_UA_PREFIXES):
            return response

        visitor_id = request.cookies.get(VISITOR_COOKIE_NAME)
        set_cookie = visitor_id is None
        if visitor_id is None:
            visitor_id = str(uuid.uuid4())

        ip = _get_client_ip()
        ua = parse_user_agent(ua_string)
        geo_data = geo.get_geo(ip, request.headers)

        device_type = (
            "bot" if ua.is_bot
            else "mobile" if ua.is_mobile
            else "tablet" if ua.is_tablet
            else "pc" if ua.is_pc
            else "other"
        )

        db.log_visit({
            "visitor_id": visitor_id,
            "ip_address": ip,
            "forwarded_for": request.headers.get("X-Forwarded-For"),
            "method": request.method,
            "path": request.path,
            "query_string": request.query_string.decode("utf-8", "ignore"),
            "host": request.host,
            "scheme": request.scheme,
            "http_version": request.environ.get("SERVER_PROTOCOL"),
            "referrer": request.referrer,
            "user_agent": ua_string,
            "accept_language": request.headers.get("Accept-Language"),
            "browser_name": ua.browser.family,
            "browser_version": ua.browser.version_string,
            "os_name": ua.os.family,
            "os_version": ua.os.version_string,
            "device_type": device_type,
            "is_bot": ua.is_bot,
            "country": geo_data.get("country"),
            "country_code": geo_data.get("country_code"),
            "region": geo_data.get("region"),
            "city": geo_data.get("city"),
            "postal_code": geo_data.get("postal_code"),
            "latitude": geo_data.get("latitude"),
            "longitude": geo_data.get("longitude"),
            "timezone": geo_data.get("timezone"),
            "isp": geo_data.get("isp"),
            "org": geo_data.get("org"),
            "asn": geo_data.get("asn"),
            "geo_source": geo_data.get("geo_source"),
            "cf_ray": request.headers.get("CF-Ray"),
            "response_status_code": response.status_code,
            "duration_ms": int((time.time() - g.start_time) * 1000),
            "raw_headers": {
                k: v for k, v in request.headers.items() if k not in _SENSITIVE_HEADERS
            },
        })

        if set_cookie:
            response.set_cookie(
                VISITOR_COOKIE_NAME,
                visitor_id,
                max_age=VISITOR_COOKIE_MAX_AGE,
                httponly=True,
                samesite="Lax",
            )
    except Exception as exc:  # noqa: BLE001
        # Logování nesmí za žádných okolností shodit odpověď uživateli.
        print(f"[app] Logování návštěvy selhalo: {exc}")

    return response


@app.route("/")
def index():
    return render_template("index.html", work_minutes=WORK_MINUTES)


db.init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=13400, debug=False)
