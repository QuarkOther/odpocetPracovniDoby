"""MySQL logování návštěv."""
import json
import os
import re
import time

import pymysql

MYSQL_HOST = os.environ.get("MYSQL_HOST", "mysql")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "odpocet")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "changeme")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "odpocet")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS visits (
    id                   BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    visited_at           DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    visitor_id           CHAR(36),
    ip_address           VARCHAR(45),
    forwarded_for        VARCHAR(255),
    method               VARCHAR(10),
    path                 VARCHAR(255),
    query_string         VARCHAR(1024),
    host                 VARCHAR(255),
    scheme               VARCHAR(10),
    http_version         VARCHAR(10),
    referrer             VARCHAR(512),
    user_agent           VARCHAR(512),
    accept_language      VARCHAR(255),
    browser_name         VARCHAR(64),
    browser_version      VARCHAR(32),
    os_name              VARCHAR(64),
    os_version           VARCHAR(32),
    device_type          VARCHAR(16),
    is_bot               TINYINT(1) DEFAULT 0,
    country              VARCHAR(100),
    country_code         VARCHAR(5),
    region               VARCHAR(100),
    city                 VARCHAR(100),
    postal_code          VARCHAR(20),
    latitude             DECIMAL(9,6),
    longitude            DECIMAL(9,6),
    timezone             VARCHAR(64),
    isp                  VARCHAR(255),
    org                  VARCHAR(255),
    asn                  VARCHAR(64),
    geo_source           VARCHAR(20),
    cf_ray               VARCHAR(64),
    response_status_code SMALLINT,
    duration_ms          INT,
    raw_headers          JSON,
    INDEX idx_visited_at (visited_at),
    INDEX idx_ip (ip_address),
    INDEX idx_visitor_id (visitor_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

INSERT_SQL = """
INSERT INTO visits (
    visitor_id, ip_address, forwarded_for, method, path, query_string, host,
    scheme, http_version, referrer, user_agent, accept_language,
    browser_name, browser_version, os_name, os_version, device_type, is_bot,
    country, country_code, region, city, postal_code, latitude, longitude,
    timezone, isp, org, asn, geo_source, cf_ray, response_status_code,
    duration_ms, raw_headers
) VALUES (
    %(visitor_id)s, %(ip_address)s, %(forwarded_for)s, %(method)s, %(path)s,
    %(query_string)s, %(host)s, %(scheme)s, %(http_version)s, %(referrer)s,
    %(user_agent)s, %(accept_language)s, %(browser_name)s, %(browser_version)s,
    %(os_name)s, %(os_version)s, %(device_type)s, %(is_bot)s, %(country)s,
    %(country_code)s, %(region)s, %(city)s, %(postal_code)s, %(latitude)s,
    %(longitude)s, %(timezone)s, %(isp)s, %(org)s, %(asn)s, %(geo_source)s,
    %(cf_ray)s, %(response_status_code)s, %(duration_ms)s, %(raw_headers)s
);
"""

# Maximální délky textových sloupců – MySQL ve strict módu jinak insert odmítne.
_COLUMN_MAX_LENGTHS = {
    name: int(length)
    for name, length in re.findall(r"^\s*(\w+)\s+(?:VAR)?CHAR\((\d+)\)", CREATE_TABLE_SQL, re.M)
}


def get_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        autocommit=True,
        connect_timeout=5,
    )


def init_db(retries: int = 10, delay: float = 3.0) -> None:
    """Vytvoří tabulku visits, pokud neexistuje. Počká na start MySQL kontejneru."""
    last_error = None
    for _ in range(retries):
        try:
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(CREATE_TABLE_SQL)
            finally:
                conn.close()
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(delay)
    print(f"[db] Nepodařilo se inicializovat databázi: {last_error}")


def log_visit(data: dict) -> None:
    """Uloží záznam o návštěvě. Chyby pouze zaloguje, request tím nesmí selhat."""
    row = dict(data)
    for column, max_len in _COLUMN_MAX_LENGTHS.items():
        if isinstance(row.get(column), str):
            row[column] = row[column][:max_len]
    if row.get("raw_headers") is not None:
        row["raw_headers"] = json.dumps(row["raw_headers"], ensure_ascii=False)
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(INSERT_SQL, row)
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        print(f"[db] Nepodařilo se zalogovat návštěvu: {exc}")
