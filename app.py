from __future__ import annotations

import base64
import csv
import hashlib
import hmac
import io
import ipaddress
import json
import os
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen

try:
    import pymysql
except ImportError:  # MySQL is optional; JSON storage remains available.
    pymysql = None


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
DATA_DIR = ROOT / "data"
ENV_FILE = ROOT / ".env"


def load_env_file() -> None:
    if not ENV_FILE.exists():
        return

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_env_file()


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


CARD_EXPIRE_MINUTE_OPTIONS = (1440, 2880, 4320)


def normalize_card_expire_minutes(value: Any, default: int = 1440) -> int:
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        minutes = default
    return minutes if minutes in CARD_EXPIRE_MINUTE_OPTIONS else 1440


HOST = os.getenv("DASHBOARD_HOST", "127.0.0.1")
PORT = env_int("PORT", 8787)
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "change-me")
WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN", "change-me-token")
WEBHOOK_SIGNING_KEY = os.getenv("WEBHOOK_SIGNING_KEY", "").strip()
WEBHOOK_SIGNATURE_MAX_AGE = max(env_int("WEBHOOK_SIGNATURE_MAX_AGE", 300), 30)
ALLOW_WEBHOOK_GET = env_bool("ALLOW_WEBHOOK_GET", False)
MAX_REQUEST_BYTES = max(env_int("MAX_REQUEST_BYTES", 1_048_576), 1024)
MESSAGE_RETENTION_DAYS = max(env_int("MESSAGE_RETENTION_DAYS", 30), 1)
MESSAGE_QUERY_LIMIT = max(min(env_int("MESSAGE_QUERY_LIMIT", 500), 5000), 20)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
ALLOW_INSECURE_DEFAULTS = env_bool("ALLOW_INSECURE_DEFAULTS", False)
WEBHOOK_FILTER_KEYWORDS = [
    keyword.strip().casefold()
    for keyword in os.getenv("WEBHOOK_FILTER_KEYWORDS", "").split(",")
    if keyword.strip()
]
DATA_FILE = Path(os.getenv("DATA_FILE", str(DATA_DIR / "messages.json")))
CARDS_FILE = Path(os.getenv("CARDS_FILE", str(DATA_DIR / "cards.json")))
PHONES_FILE = Path(os.getenv("PHONES_FILE", str(DATA_DIR / "phones.json")))
CLAIMS_FILE = Path(os.getenv("CLAIMS_FILE", str(DATA_DIR / "claims.json")))
XGJ_ORDERS_FILE = Path(os.getenv("XGJ_ORDERS_FILE", str(DATA_DIR / "xgj_orders.json")))
GOODS_FILE = Path(os.getenv("GOODS_FILE", str(DATA_DIR / "goods.json")))
STOCK_FILE = Path(os.getenv("STOCK_FILE", str(DATA_DIR / "stock_items.json")))
SETTINGS_FILE = Path(os.getenv("SETTINGS_FILE", str(DATA_DIR / "settings.json")))
AUDIT_FILE = Path(os.getenv("AUDIT_FILE", str(DATA_DIR / "audit_logs.json")))
AGENTS_FILE = Path(os.getenv("AGENTS_FILE", str(DATA_DIR / "agents.json")))
DB_BACKEND = os.getenv("DB_BACKEND", "json").strip().lower()
MYSQL_HOST = os.getenv("MYSQL_HOST", "").strip()
MYSQL_PORT = env_int("MYSQL_PORT", 3306)
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "sms_dashboard").strip()
MYSQL_USER = os.getenv("MYSQL_USER", "sms_dashboard").strip()
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "").strip()
MYSQL_CHARSET = os.getenv("MYSQL_CHARSET", "utf8mb4").strip() or "utf8mb4"
MYSQL_IMPORT_JSON = env_bool("MYSQL_IMPORT_JSON", True)
BASE_PATH = os.getenv("BASE_PATH", "").strip().rstrip("/")
if BASE_PATH and not BASE_PATH.startswith("/"):
    BASE_PATH = f"/{BASE_PATH}"

SMS_GATEWAY_BASE_URL = os.getenv("SMS_GATEWAY_BASE_URL", "").rstrip("/")
SMS_GATEWAY_USER = os.getenv("SMS_GATEWAY_USER", "")
SMS_GATEWAY_PASSWORD = os.getenv("SMS_GATEWAY_PASSWORD", "")
POLL_SECONDS = env_int("POLL_SECONDS", 8)
POLL_LIMIT = env_int("POLL_LIMIT", 80)

USER_CARDS_JSON = os.getenv("USER_CARDS_JSON", "").strip()
USER_CARD_TOKEN = os.getenv("USER_CARD_TOKEN", "").strip()
USER_COUNTRY_CODE = os.getenv("USER_COUNTRY_CODE", "+86").strip() or "+86"
USER_PHONE_NUMBER = os.getenv("USER_PHONE_NUMBER", "").strip()
USER_EXPIRES_AT = os.getenv("USER_EXPIRES_AT", "").strip()
USER_RECEIVE_LIMIT = env_int("USER_RECEIVE_LIMIT", 2)
USER_WAIT_SECONDS = env_int("USER_WAIT_SECONDS", 60)
USER_SERVICE_NAME = os.getenv("USER_SERVICE_NAME", "腾讯视频APP").strip() or "腾讯视频APP"
USER_FILTER_KEYWORDS = [
    keyword.strip()
    for keyword in os.getenv("USER_FILTER_KEYWORDS", "").split(",")
    if keyword.strip()
]

XGJ_APP_ID = os.getenv("XGJ_APP_ID", "").strip()
XGJ_APP_SECRET = os.getenv("XGJ_APP_SECRET", "").strip()
XGJ_MCH_ID = os.getenv("XGJ_MCH_ID", "sms-dashboard").strip()
XGJ_MCH_SECRET = os.getenv("XGJ_MCH_SECRET", "").strip()
XGJ_SIGNATURE_MAX_AGE = max(env_int("XGJ_SIGNATURE_MAX_AGE", 300), 30)
XGJ_MERCHANT_BALANCE_CENTS = max(env_int("XGJ_MERCHANT_BALANCE_CENTS", 999_999_999), 1)
XGJ_GOODS_NO = os.getenv("XGJ_GOODS_NO", "sms-code-link").strip() or "sms-code-link"
XGJ_GOODS_NAME = os.getenv("XGJ_GOODS_NAME", "短信验证码接码链接").strip() or "短信验证码接码链接"
XGJ_GOODS_PRICE_CENTS = max(env_int("XGJ_GOODS_PRICE_CENTS", 100), 0)
XGJ_GOODS_ENABLED = env_bool("XGJ_GOODS_ENABLED", True)
XGJ_CARD_EXPIRE_MINUTES = normalize_card_expire_minutes(env_int("XGJ_CARD_EXPIRE_MINUTES", 1440))
XGJ_CARD_RECEIVE_LIMIT = max(min(env_int("XGJ_CARD_RECEIVE_LIMIT", 1), 100), 1)
XGJ_CARD_WAIT_SECONDS = max(min(env_int("XGJ_CARD_WAIT_SECONDS", 60), 3600), 10)
XGJ_CARD_KEYWORDS = [
    keyword.strip()
    for keyword in os.getenv("XGJ_CARD_KEYWORDS", "").split(",")
    if keyword.strip()
]

DEFAULT_CARD_EXPIRE_MINUTES = normalize_card_expire_minutes(XGJ_CARD_EXPIRE_MINUTES)
DEFAULT_CARD_RECEIVE_LIMIT = max(min(XGJ_CARD_RECEIVE_LIMIT, 100), 1)
DELIVERY_SMS_LINK = "sms_link"
DELIVERY_STOCK_CODE = "stock_code"
STOCK_AVAILABLE = "available"
STOCK_SOLD = "sold"
STOCK_DISABLED = "disabled"
XGJ_TRUSTED_IP_RANGES = [
    item.strip()
    for item in os.getenv(
        "XGJ_TRUSTED_IP_RANGES",
        ",".join(
            [
                "112.74.0.0/16",
                "120.24.0.0/16",
                "120.78.0.0/16",
                "120.79.0.0/16",
                "39.108.0.0/16",
                "47.106.0.0/16",
                "120.77.0.0/16",
            ]
        ),
    ).split(",")
    if item.strip()
]

STORE_LOCK = threading.RLock()
MYSQL_SCHEMA_LOCK = threading.Lock()
RATE_LOCK = threading.Lock()
MYSQL_SCHEMA_READY = False
MYSQL_BOOTSTRAPPED = False
RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
POLL_STATE: dict[str, Any] = {
    "lastPollAt": None,
    "lastPollOk": None,
    "lastPollError": None,
    "nextPollAt": None,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def read_request_body(handler: SimpleHTTPRequestHandler) -> bytes:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError as exc:
        raise ValueError("Content-Length 不正确") from exc
    if length <= 0:
        return b""
    if length > MAX_REQUEST_BYTES:
        raise ValueError(f"请求体不能超过 {MAX_REQUEST_BYTES} 字节")
    body = handler.rfile.read(length)
    return body


def read_json_body(handler: SimpleHTTPRequestHandler) -> Any:
    if "application/json" not in handler.headers.get("Content-Type", "").lower():
        raise ValueError("Content-Type 必须是 application/json")
    body = read_request_body(handler)
    if not body:
        return {}
    return json.loads(body.decode("utf-8"))


def parse_webhook_body(body: bytes, content_type: str = "") -> Any:
    if not body:
        return {}

    text = body.decode("utf-8")
    content_type = content_type.lower()
    if "application/json" in content_type or text.lstrip().startswith(("{", "[")):
        return json.loads(text)

    parsed = parse_qs(text, keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def add_security_headers(handler: SimpleHTTPRequestHandler) -> None:
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("X-Frame-Options", "DENY")
    handler.send_header("Referrer-Policy", "no-referrer")
    handler.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    handler.send_header(
        "Content-Security-Policy",
        "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
        "connect-src 'self' http: https:; frame-ancestors 'none'; base-uri 'none'",
    )


def json_response(handler: SimpleHTTPRequestHandler, status: int, data: Any) -> None:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    add_security_headers(handler)
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def text_response(handler: SimpleHTTPRequestHandler, status: int, text: str) -> None:
    payload = text.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/plain; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    add_security_headers(handler)
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def download_response(
    handler: SimpleHTTPRequestHandler,
    filename: str,
    content: str,
    content_type: str,
    bom: bool = False,
) -> None:
    payload = content.encode("utf-8-sig" if bom else "utf-8")
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Cache-Control", "no-store")
    add_security_headers(handler)
    handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def unauthorized(handler: SimpleHTTPRequestHandler) -> None:
    handler.send_response(HTTPStatus.UNAUTHORIZED)
    handler.send_header("WWW-Authenticate", 'Basic realm="SMS Dashboard"')
    add_security_headers(handler)
    handler.send_header("Content-Length", "0")
    handler.end_headers()


def auth_ok(handler: SimpleHTTPRequestHandler) -> bool:
    auth_header = handler.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        return False

    try:
        decoded = base64.b64decode(auth_header.removeprefix("Basic ").strip()).decode("utf-8")
    except Exception:
        return False

    user, sep, password = decoded.partition(":")
    if not sep:
        return False
    return hmac.compare_digest(user, DASHBOARD_USER) and hmac.compare_digest(
        password, DASHBOARD_PASSWORD
    )


def rate_limit_ok(scope: str, client: str, limit: int, window_seconds: int) -> bool:
    now = time.time()
    key = f"{scope}:{client}"
    with RATE_LOCK:
        bucket = RATE_BUCKETS[key]
        cutoff = now - window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


def verify_webhook_signature(headers: Any, body: bytes) -> bool:
    if not WEBHOOK_SIGNING_KEY:
        return True
    signature = str(headers.get("X-Signature", "")).strip().lower()
    timestamp = str(headers.get("X-Timestamp", "")).strip()
    if not signature or not timestamp:
        return False
    try:
        signed_at = int(timestamp)
    except ValueError:
        return False
    if abs(int(time.time()) - signed_at) > WEBHOOK_SIGNATURE_MAX_AGE:
        return False
    expected = hmac.new(
        WEBHOOK_SIGNING_KEY.encode("utf-8"),
        body + timestamp.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, expected)


def wants_mysql() -> bool:
    return DB_BACKEND == "mysql" or (DB_BACKEND == "auto" and bool(MYSQL_HOST))


def mysql_ready() -> bool:
    return bool(wants_mysql() and pymysql and MYSQL_HOST and MYSQL_DATABASE and MYSQL_USER)


def storage_backend() -> str:
    return "mysql" if mysql_ready() else "json"


def mysql_connection() -> Any:
    if not mysql_ready():
        raise RuntimeError("MySQL 未配置或 PyMySQL 未安装")
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset=MYSQL_CHARSET,
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
        init_command="SET time_zone = '+00:00'",
    )


def ensure_mysql_schema() -> None:
    global MYSQL_SCHEMA_READY
    if MYSQL_SCHEMA_READY or not mysql_ready():
        return

    with MYSQL_SCHEMA_LOCK:
        if MYSQL_SCHEMA_READY:
            return
        with mysql_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sms_message (
                      id VARCHAR(96) NOT NULL,
                      source VARCHAR(64) NOT NULL DEFAULT '',
                      event VARCHAR(128) NOT NULL DEFAULT '',
                      sender VARCHAR(128) NOT NULL DEFAULT '',
                      recipient VARCHAR(128) NOT NULL DEFAULT '',
                      device_id VARCHAR(128) NOT NULL DEFAULT '',
                      sim_number VARCHAR(32) NOT NULL DEFAULT '',
                      message TEXT NOT NULL,
                      code VARCHAR(16) NOT NULL DEFAULT '',
                      received_at VARCHAR(64) NOT NULL DEFAULT '',
                      created_at VARCHAR(64) NOT NULL DEFAULT '',
                      raw_json JSON NULL,
                      updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP,
                      PRIMARY KEY (id),
                      KEY idx_received_at (received_at),
                      KEY idx_sender (sender),
                      KEY idx_recipient (recipient),
                      KEY idx_device_sim (device_id, sim_number),
                      KEY idx_code (code)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_card (
                      card VARCHAR(128) NOT NULL,
                      phone_id VARCHAR(64) NOT NULL DEFAULT '',
                      country_code VARCHAR(16) NOT NULL DEFAULT '+86',
                      phone_number VARCHAR(32) NOT NULL DEFAULT '',
                      expires_at VARCHAR(64) NOT NULL DEFAULT '',
                      receive_limit INT NOT NULL DEFAULT 2,
                      used_count INT NOT NULL DEFAULT 0,
                      wait_seconds INT NOT NULL DEFAULT 60,
                      service_name VARCHAR(128) NOT NULL DEFAULT '腾讯视频APP',
                      keywords_json JSON NULL,
                      enabled TINYINT(1) NOT NULL DEFAULT 1,
                      created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                      updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                        ON UPDATE CURRENT_TIMESTAMP(6),
                      PRIMARY KEY (card),
                      KEY idx_phone_id (phone_id),
                      KEY idx_phone_number (phone_number),
                      KEY idx_enabled (enabled)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS phone_pool (
                      id VARCHAR(64) NOT NULL,
                      country_code VARCHAR(16) NOT NULL DEFAULT '+86',
                      phone_number VARCHAR(32) NOT NULL DEFAULT '',
                      device_id VARCHAR(128) NOT NULL DEFAULT '',
                      sim_number VARCHAR(32) NOT NULL DEFAULT '',
                      label VARCHAR(128) NOT NULL DEFAULT '',
                      provider VARCHAR(128) NOT NULL DEFAULT '',
                      enabled TINYINT(1) NOT NULL DEFAULT 1,
                      note TEXT NULL,
                      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP,
                      PRIMARY KEY (id),
                      UNIQUE KEY uk_phone_number (phone_number),
                      KEY idx_device_sim (device_id, sim_number),
                      KEY idx_enabled (enabled)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS card_message_claim (
                      message_id VARCHAR(96) NOT NULL,
                      card VARCHAR(128) NOT NULL,
                      claimed_at VARCHAR(64) NOT NULL DEFAULT '',
                      PRIMARY KEY (message_id),
                      KEY idx_card (card),
                      KEY idx_claimed_at (claimed_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS xgj_order (
                      order_no VARCHAR(128) NOT NULL,
                      out_order_no VARCHAR(128) NOT NULL DEFAULT '',
                      order_type INT NOT NULL DEFAULT 2,
                      goods_no VARCHAR(128) NOT NULL DEFAULT '',
                      goods_name VARCHAR(255) NOT NULL DEFAULT '',
                      buy_quantity INT NOT NULL DEFAULT 1,
                      order_status INT NOT NULL DEFAULT 20,
                      order_amount BIGINT NOT NULL DEFAULT 0,
                      order_time INT NOT NULL DEFAULT 0,
                      end_time INT NOT NULL DEFAULT 0,
                      card_items_json JSON NULL,
                      request_json JSON NULL,
                      remark TEXT NULL,
                      created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                      updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                        ON UPDATE CURRENT_TIMESTAMP(6),
                      PRIMARY KEY (order_no),
                      UNIQUE KEY uk_out_order_no (out_order_no),
                      KEY idx_goods_no (goods_no),
                      KEY idx_order_status (order_status)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS xgj_goods (
                      goods_no VARCHAR(128) NOT NULL,
                      goods_name VARCHAR(255) NOT NULL DEFAULT '',
                      delivery_mode VARCHAR(32) NOT NULL DEFAULT 'stock_code',
                      price BIGINT NOT NULL DEFAULT 0,
                      enabled TINYINT(1) NOT NULL DEFAULT 1,
                      note TEXT NULL,
                      created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                      updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                        ON UPDATE CURRENT_TIMESTAMP(6),
                      PRIMARY KEY (goods_no),
                      KEY idx_delivery_mode (delivery_mode),
                      KEY idx_enabled (enabled)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS xgj_stock_item (
                      id VARCHAR(64) NOT NULL,
                      goods_no VARCHAR(128) NOT NULL,
                      card_no VARCHAR(255) NOT NULL DEFAULT '',
                      card_pwd TEXT NOT NULL,
                      status VARCHAR(32) NOT NULL DEFAULT 'available',
                      order_no VARCHAR(128) NOT NULL DEFAULT '',
                      sold_at VARCHAR(64) NOT NULL DEFAULT '',
                      note TEXT NULL,
                      created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                      updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                        ON UPDATE CURRENT_TIMESTAMP(6),
                      PRIMARY KEY (id),
                      KEY idx_goods_status (goods_no, status),
                      KEY idx_order_no (order_no)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS agent_profile (
                      id VARCHAR(64) NOT NULL,
                      name VARCHAR(128) NOT NULL DEFAULT '',
                      contact VARCHAR(128) NOT NULL DEFAULT '',
                      rate_percent INT NOT NULL DEFAULT 0,
                      enabled TINYINT(1) NOT NULL DEFAULT 1,
                      note TEXT NULL,
                      created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                      updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                        ON UPDATE CURRENT_TIMESTAMP(6),
                      PRIMARY KEY (id),
                      KEY idx_enabled (enabled),
                      KEY idx_name (name)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
                try:
                    cursor.execute("ALTER TABLE user_card ADD COLUMN phone_id VARCHAR(64) NOT NULL DEFAULT ''")
                except Exception as exc:
                    if "Duplicate column" not in str(exc):
                        raise
                try:
                    cursor.execute("ALTER TABLE user_card ADD COLUMN used_count INT NOT NULL DEFAULT 0")
                except Exception as exc:
                    if "Duplicate column" not in str(exc):
                        raise
                for statement in (
                    "ALTER TABLE sms_message ADD COLUMN device_id VARCHAR(128) NOT NULL DEFAULT ''",
                    "ALTER TABLE sms_message ADD COLUMN sim_number VARCHAR(32) NOT NULL DEFAULT ''",
                    "ALTER TABLE phone_pool ADD COLUMN device_id VARCHAR(128) NOT NULL DEFAULT ''",
                    "ALTER TABLE phone_pool ADD COLUMN sim_number VARCHAR(32) NOT NULL DEFAULT ''",
                ):
                    try:
                        cursor.execute(statement)
                    except Exception as exc:
                        if "Duplicate column" not in str(exc):
                            raise
                for statement in (
                    "ALTER TABLE sms_message ADD INDEX idx_device_sim (device_id, sim_number)",
                    "ALTER TABLE phone_pool ADD INDEX idx_device_sim (device_id, sim_number)",
                ):
                    try:
                        cursor.execute(statement)
                    except Exception as exc:
                        if "Duplicate key name" not in str(exc):
                            raise
                cursor.execute(
                    "ALTER TABLE user_card MODIFY created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)"
                )
                cursor.execute(
                    """
                    ALTER TABLE user_card MODIFY updated_at TIMESTAMP(6) NOT NULL
                    DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
                    """
                )
        MYSQL_SCHEMA_READY = True


def bootstrap_mysql_storage() -> None:
    global MYSQL_BOOTSTRAPPED
    if MYSQL_BOOTSTRAPPED or not mysql_ready():
        return

    with STORE_LOCK:
        if MYSQL_BOOTSTRAPPED:
            return
        if MYSQL_IMPORT_JSON:
            if DATA_FILE.exists() and count_messages_mysql() == 0:
                messages = load_messages_json()
                if messages:
                    upsert_messages_mysql(messages)
            if CARDS_FILE.exists() and count_user_cards_mysql() == 0:
                cards = load_user_cards_json(include_disabled=True)
                if cards:
                    upsert_user_cards_mysql(cards)
            if PHONES_FILE.exists() and count_phones_mysql() == 0:
                phones = load_phones_json(include_disabled=True)
                if phones:
                    upsert_phones_mysql(phones)
            if CLAIMS_FILE.exists() and count_claims_mysql() == 0:
                claims = load_claims_json()
                if claims:
                    upsert_claims_mysql(claims)
            if XGJ_ORDERS_FILE.exists() and count_xgj_orders_mysql() == 0:
                orders = load_xgj_orders_json()
                if orders:
                    upsert_xgj_orders_mysql(orders)
            if GOODS_FILE.exists() and count_goods_mysql() == 0:
                goods = load_goods_json(include_disabled=True)
                if goods:
                    upsert_goods_mysql(goods)
            if STOCK_FILE.exists() and count_stock_items_mysql() == 0:
                stock_items = load_stock_items_json(limit=50000)
                if stock_items:
                    upsert_stock_items_mysql(stock_items)
            if AGENTS_FILE.exists() and count_agents_mysql() == 0:
                agents = load_agents_json()
                if agents:
                    upsert_agents_mysql(agents)
        cards = env_user_cards()
        if cards:
            upsert_user_cards_mysql(cards)
        sync_claim_counts_mysql()
        MYSQL_BOOTSTRAPPED = True


def ensure_store() -> None:
    if mysql_ready():
        ensure_mysql_schema()
        bootstrap_mysql_storage()
        return
    ensure_json_store()


def ensure_json_store() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]\n", encoding="utf-8")


def load_messages() -> list[dict[str, Any]]:
    if mysql_ready():
        return load_messages_mysql()
    return load_messages_json()


def load_messages_json() -> list[dict[str, Any]]:
    ensure_json_store()
    with STORE_LOCK:
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            backup = DATA_FILE.with_suffix(f".broken-{int(time.time())}.json")
            DATA_FILE.replace(backup)
            DATA_FILE.write_text("[]\n", encoding="utf-8")
            return []
    if not isinstance(data, list):
        return []
    cutoff = datetime.now(timezone.utc).timestamp() - MESSAGE_RETENTION_DAYS * 86400
    messages = []
    for item in data:
        if not isinstance(item, dict):
            continue
        received = parse_datetime(str(item.get("receivedAt") or item.get("createdAt") or ""))
        if received and received.timestamp() < cutoff:
            continue
        messages.append(item)
    return sorted(
        messages,
        key=lambda item: item.get("receivedAt") or item.get("createdAt") or "",
        reverse=True,
    )[:MESSAGE_QUERY_LIMIT]


def save_messages(messages: list[dict[str, Any]]) -> None:
    if mysql_ready():
        save_messages_mysql(messages)
        return
    save_messages_json(messages)


def save_messages_json(messages: list[dict[str, Any]]) -> None:
    ensure_json_store()
    ordered = sorted(messages, key=lambda item: item.get("receivedAt") or "", reverse=True)
    with STORE_LOCK:
        tmp = DATA_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(DATA_FILE)


def ensure_json_cards_store() -> None:
    CARDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not CARDS_FILE.exists():
        CARDS_FILE.write_text("[]\n", encoding="utf-8")


def load_user_cards_json(include_disabled: bool = False) -> list[dict[str, Any]]:
    ensure_json_cards_store()
    with STORE_LOCK:
        try:
            data = json.loads(CARDS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            backup = CARDS_FILE.with_suffix(f".broken-{int(time.time())}.json")
            CARDS_FILE.replace(backup)
            CARDS_FILE.write_text("[]\n", encoding="utf-8")
            return []
    if not isinstance(data, list):
        return []
    cards = [normalize_user_card(item) for item in data if isinstance(item, dict)]
    result = [card for card in cards if card]
    if include_disabled:
        return result
    return [card for card in result if card.get("enabled", True)]


def save_user_cards_json(cards: list[dict[str, Any]]) -> None:
    ensure_json_cards_store()
    ordered = sorted(cards, key=lambda item: item.get("updatedAt") or item.get("createdAt") or "", reverse=True)
    with STORE_LOCK:
        tmp = CARDS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(CARDS_FILE)


def ensure_json_phones_store() -> None:
    PHONES_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not PHONES_FILE.exists():
        PHONES_FILE.write_text("[]\n", encoding="utf-8")


def load_phones_json(include_disabled: bool = False) -> list[dict[str, Any]]:
    ensure_json_phones_store()
    with STORE_LOCK:
        try:
            data = json.loads(PHONES_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            backup = PHONES_FILE.with_suffix(f".broken-{int(time.time())}.json")
            PHONES_FILE.replace(backup)
            PHONES_FILE.write_text("[]\n", encoding="utf-8")
            return []
    if not isinstance(data, list):
        return []
    phones = [normalize_phone(item) for item in data if isinstance(item, dict)]
    result = [phone for phone in phones if phone]
    if include_disabled:
        return result
    return [phone for phone in result if phone.get("enabled", True)]


def save_phones_json(phones: list[dict[str, Any]]) -> None:
    ensure_json_phones_store()
    ordered = sorted(phones, key=lambda item: item.get("updatedAt") or item.get("createdAt") or "", reverse=True)
    with STORE_LOCK:
        tmp = PHONES_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(PHONES_FILE)


def ensure_json_claims_store() -> None:
    CLAIMS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not CLAIMS_FILE.exists():
        CLAIMS_FILE.write_text("[]\n", encoding="utf-8")


def ensure_json_xgj_orders_store() -> None:
    XGJ_ORDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not XGJ_ORDERS_FILE.exists():
        XGJ_ORDERS_FILE.write_text("[]\n", encoding="utf-8")


def ensure_json_goods_store() -> None:
    GOODS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not GOODS_FILE.exists():
        GOODS_FILE.write_text("[]\n", encoding="utf-8")


def ensure_json_stock_store() -> None:
    STOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not STOCK_FILE.exists():
        STOCK_FILE.write_text("[]\n", encoding="utf-8")


def ensure_json_agents_store() -> None:
    AGENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not AGENTS_FILE.exists():
        AGENTS_FILE.write_text("[]\n", encoding="utf-8")


def ensure_audit_store() -> None:
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not AUDIT_FILE.exists():
        AUDIT_FILE.write_text("[]\n", encoding="utf-8")


def normalize_audit_log(raw: dict[str, Any]) -> dict[str, Any] | None:
    action = str(raw.get("action", "")).strip()
    if not action:
        return None
    detail = raw.get("detail")
    if not isinstance(detail, dict):
        detail = {}
    return {
        "id": str(raw.get("id") or stable_id("audit", action, raw.get("createdAt"), detail, time.time())),
        "action": action,
        "target": str(raw.get("target", "")).strip(),
        "detail": detail,
        "clientIp": str(raw.get("clientIp", "")).strip(),
        "createdAt": str(raw.get("createdAt") or utc_now_iso()),
    }


def load_audit_logs(limit: int = 200) -> list[dict[str, Any]]:
    ensure_audit_store()
    with STORE_LOCK:
        try:
            data = json.loads(AUDIT_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            backup = AUDIT_FILE.with_suffix(f".broken-{int(time.time())}.json")
            AUDIT_FILE.replace(backup)
            AUDIT_FILE.write_text("[]\n", encoding="utf-8")
            return []
    if not isinstance(data, list):
        return []
    logs = [normalize_audit_log(item) for item in data if isinstance(item, dict)]
    normalized = [log for log in logs if log]
    return sorted(normalized, key=lambda item: item.get("createdAt") or "", reverse=True)[:limit]


def save_audit_logs(logs: list[dict[str, Any]]) -> None:
    ensure_audit_store()
    ordered = sorted(logs, key=lambda item: item.get("createdAt") or "", reverse=True)[:1000]
    with STORE_LOCK:
        tmp = AUDIT_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(AUDIT_FILE)


def append_audit_log(
    action: str,
    target: str = "",
    detail: dict[str, Any] | None = None,
    client_ip: str = "",
) -> dict[str, Any]:
    entry = normalize_audit_log(
        {
            "id": stable_id("audit", action, target, detail or {}, utc_now_iso(), secrets.token_hex(4)),
            "action": action,
            "target": target,
            "detail": detail or {},
            "clientIp": client_ip,
            "createdAt": utc_now_iso(),
        }
    )
    if not entry:
        raise ValueError("日志内容不正确")
    logs = load_audit_logs(limit=999)
    logs.insert(0, entry)
    save_audit_logs(logs)
    return entry


def record_audit_log(
    action: str,
    target: str = "",
    detail: dict[str, Any] | None = None,
    client_ip: str = "",
) -> None:
    try:
        append_audit_log(action, target, detail, client_ip)
    except Exception as exc:
        print(f"audit log failed: {exc}")


def normalize_admin_settings(raw: dict[str, Any] | None = None) -> dict[str, Any]:
    source = raw or {}
    expire_minutes = coerce_int(source.get("defaultCardExpireMinutes"), DEFAULT_CARD_EXPIRE_MINUTES)
    receive_limit = coerce_int(source.get("defaultCardReceiveLimit"), DEFAULT_CARD_RECEIVE_LIMIT)
    return {
        "defaultCardExpireMinutes": normalize_card_expire_minutes(expire_minutes),
        "defaultCardReceiveLimit": max(min(receive_limit, 100), 1),
    }


def ensure_settings_store() -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.write_text(
            json.dumps(normalize_admin_settings(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def load_admin_settings() -> dict[str, Any]:
    ensure_settings_store()
    with STORE_LOCK:
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            backup = SETTINGS_FILE.with_suffix(f".broken-{int(time.time())}.json")
            SETTINGS_FILE.replace(backup)
            SETTINGS_FILE.write_text(
                json.dumps(normalize_admin_settings(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return normalize_admin_settings()
    return normalize_admin_settings(data if isinstance(data, dict) else {})


def save_admin_settings(raw: dict[str, Any]) -> dict[str, Any]:
    settings = normalize_admin_settings(raw)
    with STORE_LOCK:
        ensure_settings_store()
        payload = {
            **settings,
            "updatedAt": utc_now_iso(),
        }
        tmp = SETTINGS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(SETTINGS_FILE)
    return settings


def default_card_expires_at(expire_minutes: int | None = None) -> str:
    minutes = expire_minutes if expire_minutes is not None else coerce_int(
        load_admin_settings().get("defaultCardExpireMinutes"),
        DEFAULT_CARD_EXPIRE_MINUTES,
    )
    minutes = normalize_card_expire_minutes(coerce_int(minutes, DEFAULT_CARD_EXPIRE_MINUTES))
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def load_claims_json() -> list[dict[str, Any]]:
    ensure_json_claims_store()
    with STORE_LOCK:
        try:
            data = json.loads(CLAIMS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            backup = CLAIMS_FILE.with_suffix(f".broken-{int(time.time())}.json")
            CLAIMS_FILE.replace(backup)
            CLAIMS_FILE.write_text("[]\n", encoding="utf-8")
            return []
    if not isinstance(data, list):
        return []
    claims = [normalize_claim(item) for item in data if isinstance(item, dict)]
    return [claim for claim in claims if claim]


def save_claims_json(claims: list[dict[str, Any]]) -> None:
    ensure_json_claims_store()
    by_message = {str(claim.get("messageId", "")): claim for claim in claims if claim.get("messageId")}
    ordered = sorted(by_message.values(), key=lambda item: item.get("claimedAt") or "", reverse=True)
    with STORE_LOCK:
        tmp = CLAIMS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(CLAIMS_FILE)


def stable_id(*parts: Any) -> str:
    source = "\n".join("" if part is None else str(part) for part in parts)
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:24]


def first_present(source: dict[str, Any], keys: list[str], default: str = "") -> str:
    for key in keys:
        value = source.get(key)
        if value is not None and value != "":
            return str(value)
    return default


def coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def coerce_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() not in {"0", "false", "no", "off", "disabled"}


def split_keywords(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def normalize_user_card(raw: dict[str, Any], default_token: str = "") -> dict[str, Any] | None:
    token = first_present(raw, ["card", "token", "cardToken", "id"], default_token).strip()
    if not token:
        return None

    keywords = split_keywords(raw.get("keywords"))
    if not keywords:
        keywords = USER_FILTER_KEYWORDS

    return {
        "card": token,
        "phoneId": first_present(raw, ["phoneId", "phone_id"], ""),
        "countryCode": first_present(raw, ["countryCode", "country"], USER_COUNTRY_CODE),
        "phoneNumber": first_present(raw, ["phoneNumber", "phone", "number"], USER_PHONE_NUMBER),
        "expiresAt": first_present(raw, ["expiresAt", "expireAt", "expires", "expire"], USER_EXPIRES_AT),
        "receiveLimit": coerce_int(
            raw.get("receiveLimit", raw.get("receiveCount")),
            USER_RECEIVE_LIMIT,
        ),
        "usedCount": coerce_int(raw.get("usedCount", raw.get("used_count")), 0),
        "waitSeconds": coerce_int(raw.get("waitSeconds"), USER_WAIT_SECONDS),
        "serviceName": first_present(raw, ["serviceName", "appName", "service"], USER_SERVICE_NAME),
        "keywords": keywords,
        "enabled": coerce_bool(raw.get("enabled"), True),
        "createdAt": str(raw.get("createdAt") or raw.get("created_at") or ""),
        "updatedAt": str(raw.get("updatedAt") or raw.get("updated_at") or ""),
    }


def normalize_phone(raw: dict[str, Any], default_id: str = "") -> dict[str, Any] | None:
    phone_number = first_present(raw, ["phoneNumber", "phone", "number", "phone_number"]).strip()
    if not phone_number:
        return None
    phone_id = first_present(raw, ["id", "phoneId", "phone_id"], default_id).strip()
    if not phone_id:
        phone_id = stable_id("phone", phone_number)
    return {
        "id": phone_id,
        "countryCode": first_present(raw, ["countryCode", "country", "country_code"], USER_COUNTRY_CODE),
        "phoneNumber": phone_number,
        "deviceId": first_present(raw, ["deviceId", "device_id"], ""),
        "simNumber": first_present(raw, ["simNumber", "sim_number"], ""),
        "label": first_present(raw, ["label", "name"], ""),
        "provider": first_present(raw, ["provider"], ""),
        "note": first_present(raw, ["note", "remark"], ""),
        "enabled": coerce_bool(raw.get("enabled"), True),
        "createdAt": str(raw.get("createdAt") or raw.get("created_at") or ""),
        "updatedAt": str(raw.get("updatedAt") or raw.get("updated_at") or ""),
    }


def normalize_claim(raw: dict[str, Any]) -> dict[str, Any] | None:
    message_id = first_present(raw, ["messageId", "message_id", "id"]).strip()
    card = first_present(raw, ["card", "cardToken", "token"]).strip()
    if not message_id or not card:
        return None
    return {
        "messageId": message_id,
        "card": card,
        "claimedAt": first_present(raw, ["claimedAt", "claimed_at"], utc_now_iso()),
    }


def normalize_xgj_order(raw: dict[str, Any]) -> dict[str, Any] | None:
    order_no = first_present(raw, ["orderNo", "order_no"]).strip()
    out_order_no = first_present(raw, ["outOrderNo", "out_order_no"]).strip()
    if not order_no or not out_order_no:
        return None

    card_items = raw.get("cardItems", raw.get("card_items"))
    if not isinstance(card_items, list):
        card_items = []
    request_body = raw.get("request", raw.get("request_json"))
    if not isinstance(request_body, dict):
        request_body = {}
    return {
        "orderNo": order_no,
        "outOrderNo": out_order_no,
        "orderType": coerce_int(raw.get("orderType", raw.get("order_type")), 2),
        "goodsNo": first_present(raw, ["goodsNo", "goods_no"], XGJ_GOODS_NO),
        "goodsName": first_present(raw, ["goodsName", "goods_name"], XGJ_GOODS_NAME),
        "buyQuantity": max(coerce_int(raw.get("buyQuantity", raw.get("buy_quantity")), 1), 1),
        "orderStatus": coerce_int(raw.get("orderStatus", raw.get("order_status")), 20),
        "orderAmount": max(coerce_int(raw.get("orderAmount", raw.get("order_amount")), 0), 0),
        "orderTime": max(coerce_int(raw.get("orderTime", raw.get("order_time")), 0), 0),
        "endTime": max(coerce_int(raw.get("endTime", raw.get("end_time")), 0), 0),
        "cardItems": [
            {
                **({"card_no": str(item.get("card_no", ""))} if item.get("card_no") else {}),
                "card_pwd": str(item.get("card_pwd", "")),
            }
            for item in card_items
            if isinstance(item, dict) and str(item.get("card_pwd", "")).strip()
        ],
        "request": request_body,
        "remark": first_present(raw, ["remark"], ""),
        "createdAt": first_present(raw, ["createdAt", "created_at"], utc_now_iso()),
        "updatedAt": first_present(raw, ["updatedAt", "updated_at"], utc_now_iso()),
    }


def normalize_delivery_mode(value: Any) -> str:
    mode = str(value or DELIVERY_STOCK_CODE).strip().lower()
    return mode if mode in {DELIVERY_SMS_LINK, DELIVERY_STOCK_CODE} else DELIVERY_STOCK_CODE


def normalize_stock_status(value: Any) -> str:
    status = str(value or STOCK_AVAILABLE).strip().lower()
    return status if status in {STOCK_AVAILABLE, STOCK_SOLD, STOCK_DISABLED} else STOCK_AVAILABLE


def normalize_goods_product(raw: dict[str, Any]) -> dict[str, Any] | None:
    goods_no = first_present(raw, ["goodsNo", "goods_no", "no", "id"]).strip()
    if not goods_no:
        return None
    goods_name = first_present(raw, ["goodsName", "goods_name", "name"], goods_no).strip() or goods_no
    return {
        "goodsNo": goods_no,
        "goodsType": 2,
        "goodsName": goods_name,
        "deliveryMode": normalize_delivery_mode(raw.get("deliveryMode", raw.get("delivery_mode"))),
        "priceCents": max(coerce_int(raw.get("priceCents", raw.get("price")), 0), 0),
        "enabled": coerce_bool(raw.get("enabled"), True),
        "note": str(raw.get("note", "") or "").strip(),
        "createdAt": first_present(raw, ["createdAt", "created_at"], utc_now_iso()),
        "updatedAt": first_present(raw, ["updatedAt", "updated_at"], utc_now_iso()),
    }


def normalize_stock_item(raw: dict[str, Any]) -> dict[str, Any] | None:
    goods_no = first_present(raw, ["goodsNo", "goods_no"]).strip()
    card_pwd = first_present(raw, ["cardPwd", "card_pwd", "content", "password", "pwd"]).strip()
    if not goods_no or not card_pwd:
        return None
    created_at = first_present(raw, ["createdAt", "created_at"], utc_now_iso())
    stock_id = first_present(raw, ["id"], "").strip()
    if not stock_id:
        stock_id = stable_id("stock", goods_no, raw.get("cardNo", raw.get("card_no", "")), card_pwd, created_at)
    return {
        "id": stock_id,
        "goodsNo": goods_no,
        "cardNo": first_present(raw, ["cardNo", "card_no", "number", "no"], "").strip(),
        "cardPwd": card_pwd,
        "status": normalize_stock_status(raw.get("status")),
        "orderNo": first_present(raw, ["orderNo", "order_no"], "").strip(),
        "soldAt": first_present(raw, ["soldAt", "sold_at"], "").strip(),
        "note": str(raw.get("note", "") or "").strip(),
        "createdAt": created_at,
        "updatedAt": first_present(raw, ["updatedAt", "updated_at"], utc_now_iso()),
    }


def normalize_agent(raw: dict[str, Any]) -> dict[str, Any] | None:
    name = first_present(raw, ["name", "agentName", "agent_name"]).strip()
    contact = first_present(raw, ["contact", "phone", "wechat", "account"]).strip()
    if not name:
        return None
    agent_id = first_present(raw, ["id", "agentId", "agent_id"], "").strip()
    if not agent_id:
        agent_id = stable_id("agent", name, contact)
    rate = max(min(coerce_int(raw.get("ratePercent", raw.get("rate_percent")), 0), 100), 0)
    return {
        "id": agent_id,
        "name": name,
        "contact": contact,
        "ratePercent": rate,
        "enabled": coerce_bool(raw.get("enabled"), True),
        "note": str(raw.get("note", "") or "").strip(),
        "createdAt": first_present(raw, ["createdAt", "created_at"], utc_now_iso()),
        "updatedAt": first_present(raw, ["updatedAt", "updated_at"], utc_now_iso()),
    }


def load_agents_json() -> list[dict[str, Any]]:
    ensure_json_agents_store()
    with STORE_LOCK:
        try:
            data = json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            backup = AGENTS_FILE.with_suffix(f".broken-{int(time.time())}.json")
            AGENTS_FILE.replace(backup)
            AGENTS_FILE.write_text("[]\n", encoding="utf-8")
            return []
    if not isinstance(data, list):
        return []
    agents = [normalize_agent(item) for item in data if isinstance(item, dict)]
    return sorted(
        [agent for agent in agents if agent],
        key=lambda item: item.get("updatedAt") or item.get("createdAt") or "",
        reverse=True,
    )


def save_agents_json(agents: list[dict[str, Any]]) -> None:
    ensure_json_agents_store()
    normalized = [normalize_agent(agent) for agent in agents]
    ordered = sorted(
        [agent for agent in normalized if agent],
        key=lambda item: item.get("updatedAt") or item.get("createdAt") or "",
        reverse=True,
    )
    with STORE_LOCK:
        tmp = AGENTS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(AGENTS_FILE)


def load_agents_mysql() -> list[dict[str, Any]]:
    ensure_mysql_schema()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, contact, rate_percent, enabled, note, created_at, updated_at
                FROM agent_profile
                ORDER BY updated_at DESC, created_at DESC
                """
            )
            rows = cursor.fetchall()
    agents = [
        normalize_agent(
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "contact": row.get("contact"),
                "ratePercent": row.get("rate_percent"),
                "enabled": bool(row.get("enabled")),
                "note": row.get("note"),
                "createdAt": row.get("created_at"),
                "updatedAt": row.get("updated_at"),
            }
        )
        for row in rows
    ]
    return [agent for agent in agents if agent]


def count_agents_mysql() -> int:
    ensure_mysql_schema()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM agent_profile")
            row = cursor.fetchone() or {}
    return int(row.get("total") or 0)


def upsert_agents_mysql(agents: list[dict[str, Any]]) -> None:
    if not agents:
        return
    ensure_mysql_schema()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            for agent in agents:
                cursor.execute(
                    """
                    INSERT INTO agent_profile (
                      id, name, contact, rate_percent, enabled, note, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                      name = VALUES(name),
                      contact = VALUES(contact),
                      rate_percent = VALUES(rate_percent),
                      enabled = VALUES(enabled),
                      note = VALUES(note)
                    """,
                    (
                        str(agent.get("id", "")),
                        str(agent.get("name", "")),
                        str(agent.get("contact", "")),
                        coerce_int(agent.get("ratePercent"), 0),
                        1 if agent.get("enabled", True) else 0,
                        str(agent.get("note", "")),
                        parse_datetime(str(agent.get("createdAt", ""))) or datetime.now(timezone.utc),
                    ),
                )


def load_agents() -> list[dict[str, Any]]:
    if mysql_ready():
        bootstrap_mysql_storage()
        return load_agents_mysql()
    return load_agents_json()


def save_agents(agents: list[dict[str, Any]]) -> None:
    if mysql_ready():
        bootstrap_mysql_storage()
        upsert_agents_mysql(agents)
        return
    save_agents_json(agents)


def agent_from_body(body: dict[str, Any]) -> dict[str, Any]:
    agent = normalize_agent(
        {
            "id": body.get("id", ""),
            "name": body.get("name", body.get("agentName", "")),
            "contact": body.get("contact", ""),
            "ratePercent": body.get("ratePercent", 0),
            "note": body.get("note", ""),
            "enabled": body.get("enabled", True),
        }
    )
    if not agent:
        raise ValueError("代理名称不能为空")
    return agent


def save_agent(agent: dict[str, Any]) -> dict[str, Any]:
    with STORE_LOCK:
        agents = load_agents()
        now = utc_now_iso()
        existing = next(
            (item for item in agents if hmac.compare_digest(str(item.get("id", "")), str(agent.get("id", "")))),
            None,
        )
        agent["createdAt"] = existing.get("createdAt") if existing else now
        agent["updatedAt"] = now
        by_id = {str(item.get("id", "")): item for item in agents}
        by_id[str(agent.get("id", ""))] = agent
        save_agents(list(by_id.values()))
    return agent


def set_agent_enabled(agent_id: str, enabled: bool) -> bool:
    with STORE_LOCK:
        agents = load_agents()
        changed = False
        for agent in agents:
            if hmac.compare_digest(agent_id, str(agent.get("id", ""))):
                agent["enabled"] = enabled
                agent["updatedAt"] = utc_now_iso()
                changed = True
                break
        if changed:
            save_agents(agents)
        return changed


def delete_agent(agent_id: str) -> bool:
    with STORE_LOCK:
        if mysql_ready():
            bootstrap_mysql_storage()
            with mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM agent_profile WHERE id = %s", (agent_id,))
                    return cursor.rowcount > 0
        agents = load_agents()
        kept = [agent for agent in agents if not hmac.compare_digest(agent_id, str(agent.get("id", "")))]
        if len(kept) == len(agents):
            return False
        save_agents(kept)
        return True


def load_xgj_orders_json() -> list[dict[str, Any]]:
    ensure_json_xgj_orders_store()
    with STORE_LOCK:
        try:
            data = json.loads(XGJ_ORDERS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            backup = XGJ_ORDERS_FILE.with_suffix(f".broken-{int(time.time())}.json")
            XGJ_ORDERS_FILE.replace(backup)
            XGJ_ORDERS_FILE.write_text("[]\n", encoding="utf-8")
            return []
    if not isinstance(data, list):
        return []
    orders = [normalize_xgj_order(item) for item in data if isinstance(item, dict)]
    return [order for order in orders if order]


def save_xgj_orders_json(orders: list[dict[str, Any]]) -> None:
    ensure_json_xgj_orders_store()
    by_order = {str(order.get("orderNo", "")): order for order in orders if order.get("orderNo")}
    ordered = sorted(by_order.values(), key=lambda item: item.get("createdAt") or "", reverse=True)
    with STORE_LOCK:
        tmp = XGJ_ORDERS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(XGJ_ORDERS_FILE)


def load_goods_json(include_disabled: bool = False) -> list[dict[str, Any]]:
    ensure_json_goods_store()
    with STORE_LOCK:
        try:
            data = json.loads(GOODS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            backup = GOODS_FILE.with_suffix(f".broken-{int(time.time())}.json")
            GOODS_FILE.replace(backup)
            GOODS_FILE.write_text("[]\n", encoding="utf-8")
            return []
    if not isinstance(data, list):
        return []
    goods = [normalize_goods_product(item) for item in data if isinstance(item, dict)]
    result = [item for item in goods if item]
    if include_disabled:
        return result
    return [item for item in result if item.get("enabled", True)]


def save_goods_json(goods: list[dict[str, Any]]) -> None:
    ensure_json_goods_store()
    by_goods = {str(item.get("goodsNo", "")): item for item in goods if item.get("goodsNo")}
    ordered = sorted(by_goods.values(), key=lambda item: item.get("updatedAt") or "", reverse=True)
    with STORE_LOCK:
        tmp = GOODS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(GOODS_FILE)


def load_stock_items_json(
    goods_no: str = "",
    status: str = "",
    limit: int = 1000,
) -> list[dict[str, Any]]:
    ensure_json_stock_store()
    with STORE_LOCK:
        try:
            data = json.loads(STOCK_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            backup = STOCK_FILE.with_suffix(f".broken-{int(time.time())}.json")
            STOCK_FILE.replace(backup)
            STOCK_FILE.write_text("[]\n", encoding="utf-8")
            return []
    if not isinstance(data, list):
        return []
    items = [normalize_stock_item(item) for item in data if isinstance(item, dict)]
    normalized = [item for item in items if item]
    if goods_no:
        normalized = [item for item in normalized if item.get("goodsNo") == goods_no]
    if status:
        normalized = [item for item in normalized if item.get("status") == status]
    safe_limit = max(min(coerce_int(limit, 1000), 50000), 1)
    return sorted(normalized, key=lambda item: item.get("createdAt") or "", reverse=True)[:safe_limit]


def save_stock_items_json(items: list[dict[str, Any]]) -> None:
    ensure_json_stock_store()
    by_id = {str(item.get("id", "")): item for item in items if item.get("id")}
    ordered = sorted(by_id.values(), key=lambda item: item.get("createdAt") or "", reverse=True)
    with STORE_LOCK:
        tmp = STOCK_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(STOCK_FILE)


def load_user_cards_mysql(include_disabled: bool = False) -> list[dict[str, Any]]:
    ensure_mysql_schema()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            where = "" if include_disabled else "WHERE enabled = 1"
            cursor.execute(
                f"""
                SELECT card, phone_id, country_code, phone_number, expires_at, receive_limit,
                       used_count, wait_seconds, service_name, keywords_json, enabled,
                       created_at, updated_at
                FROM user_card
                {where}
                ORDER BY created_at DESC
                """
            )
            rows = cursor.fetchall()

    cards: list[dict[str, Any]] = []
    for row in rows:
        keywords = []
        raw_keywords = row.get("keywords_json")
        if raw_keywords:
            try:
                parsed = json.loads(raw_keywords) if isinstance(raw_keywords, str) else raw_keywords
            except json.JSONDecodeError:
                parsed = []
            keywords = split_keywords(parsed)
        card = normalize_user_card(
            {
                "card": row.get("card"),
                "phoneId": row.get("phone_id"),
                "countryCode": row.get("country_code"),
                "phoneNumber": row.get("phone_number"),
                "expiresAt": row.get("expires_at"),
                "receiveLimit": row.get("receive_limit"),
                "usedCount": row.get("used_count"),
                "waitSeconds": row.get("wait_seconds"),
                "serviceName": row.get("service_name"),
                "keywords": keywords,
                "enabled": bool(row.get("enabled")),
                "createdAt": row.get("created_at"),
                "updatedAt": row.get("updated_at"),
            }
        )
        if card:
            cards.append(card)
    return cards


def count_user_cards_mysql() -> int:
    ensure_mysql_schema()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM user_card")
            row = cursor.fetchone() or {}
    return int(row.get("total") or 0)


def upsert_user_cards_mysql(cards: list[dict[str, Any]]) -> None:
    if not cards:
        return
    ensure_mysql_schema()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            for card in cards:
                cursor.execute(
                    """
                    INSERT INTO user_card (
                      card, phone_id, country_code, phone_number, expires_at, receive_limit,
                      used_count, wait_seconds, service_name, keywords_json, enabled, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                      phone_id = VALUES(phone_id),
                      country_code = VALUES(country_code),
                      phone_number = VALUES(phone_number),
                      expires_at = VALUES(expires_at),
                      receive_limit = VALUES(receive_limit),
                      used_count = VALUES(used_count),
                      wait_seconds = VALUES(wait_seconds),
                      service_name = VALUES(service_name),
                      keywords_json = VALUES(keywords_json),
                      enabled = VALUES(enabled)
                    """,
                    (
                        str(card.get("card", "")),
                        str(card.get("phoneId", "")),
                        str(card.get("countryCode", "+86")),
                        str(card.get("phoneNumber", "")),
                        str(card.get("expiresAt", "")),
                        int(card.get("receiveLimit", USER_RECEIVE_LIMIT)),
                        int(card.get("usedCount", 0)),
                        int(card.get("waitSeconds", USER_WAIT_SECONDS)),
                        str(card.get("serviceName", USER_SERVICE_NAME)),
                        json.dumps(card.get("keywords", []), ensure_ascii=False),
                        1 if card.get("enabled", True) else 0,
                        parse_datetime(str(card.get("createdAt", ""))) or datetime.now(timezone.utc),
                    ),
                )


def load_phones_mysql(include_disabled: bool = False) -> list[dict[str, Any]]:
    ensure_mysql_schema()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            where = "" if include_disabled else "WHERE enabled = 1"
            cursor.execute(
                f"""
                SELECT id, country_code, phone_number, device_id, sim_number, label, provider, note,
                       enabled, created_at, updated_at
                FROM phone_pool
                {where}
                ORDER BY created_at DESC
                """
            )
            rows = cursor.fetchall()

    phones: list[dict[str, Any]] = []
    for row in rows:
        phone = normalize_phone(
            {
                "id": row.get("id"),
                "countryCode": row.get("country_code"),
                "phoneNumber": row.get("phone_number"),
                "deviceId": row.get("device_id"),
                "simNumber": row.get("sim_number"),
                "label": row.get("label"),
                "provider": row.get("provider"),
                "note": row.get("note"),
                "enabled": bool(row.get("enabled")),
                "createdAt": row.get("created_at"),
                "updatedAt": row.get("updated_at"),
            }
        )
        if phone:
            phones.append(phone)
    return phones


def count_phones_mysql() -> int:
    ensure_mysql_schema()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM phone_pool")
            row = cursor.fetchone() or {}
    return int(row.get("total") or 0)


def upsert_phones_mysql(phones: list[dict[str, Any]]) -> None:
    if not phones:
        return
    ensure_mysql_schema()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            for phone in phones:
                cursor.execute(
                    """
                    INSERT INTO phone_pool (
                      id, country_code, phone_number, device_id, sim_number, label, provider, note, enabled
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                      country_code = VALUES(country_code),
                      phone_number = VALUES(phone_number),
                      device_id = VALUES(device_id),
                      sim_number = VALUES(sim_number),
                      label = VALUES(label),
                      provider = VALUES(provider),
                      note = VALUES(note),
                      enabled = VALUES(enabled)
                    """,
                    (
                        str(phone.get("id", "")),
                        str(phone.get("countryCode", "+86")),
                        str(phone.get("phoneNumber", "")),
                        str(phone.get("deviceId", "")),
                        str(phone.get("simNumber", "")),
                        str(phone.get("label", "")),
                        str(phone.get("provider", "")),
                        str(phone.get("note", "")),
                        1 if phone.get("enabled", True) else 0,
                    ),
                )


def count_claims_mysql() -> int:
    ensure_mysql_schema()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM card_message_claim")
            row = cursor.fetchone() or {}
    return int(row.get("total") or 0)


def count_xgj_orders_mysql(min_status: int | None = None) -> int:
    ensure_mysql_schema()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            if min_status is None:
                cursor.execute("SELECT COUNT(*) AS total FROM xgj_order")
            else:
                cursor.execute("SELECT COUNT(*) AS total FROM xgj_order WHERE order_status >= %s", (min_status,))
            row = cursor.fetchone() or {}
    return int(row.get("total") or 0)


def load_claims_mysql(card: str = "") -> list[dict[str, Any]]:
    ensure_mysql_schema()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            if card:
                cursor.execute(
                    """
                    SELECT message_id, card, claimed_at
                    FROM card_message_claim
                    WHERE card = %s
                    ORDER BY claimed_at DESC
                    """,
                    (card,),
                )
            else:
                cursor.execute(
                    """
                    SELECT message_id, card, claimed_at
                    FROM card_message_claim
                    ORDER BY claimed_at DESC
                    """
                )
            rows = cursor.fetchall()
    claims = [
        normalize_claim(
            {
                "messageId": row.get("message_id"),
                "card": row.get("card"),
                "claimedAt": row.get("claimed_at"),
            }
        )
        for row in rows
    ]
    return [claim for claim in claims if claim]


def row_to_xgj_order(row: dict[str, Any]) -> dict[str, Any] | None:
    card_items = parse_db_json(row.get("card_items_json"))
    request_body = parse_db_json(row.get("request_json"))
    return normalize_xgj_order(
        {
            "orderNo": row.get("order_no"),
            "outOrderNo": row.get("out_order_no"),
            "orderType": row.get("order_type"),
            "goodsNo": row.get("goods_no"),
            "goodsName": row.get("goods_name"),
            "buyQuantity": row.get("buy_quantity"),
            "orderStatus": row.get("order_status"),
            "orderAmount": row.get("order_amount"),
            "orderTime": row.get("order_time"),
            "endTime": row.get("end_time"),
            "cardItems": card_items if isinstance(card_items, list) else [],
            "request": request_body if isinstance(request_body, dict) else {},
            "remark": row.get("remark"),
            "createdAt": row.get("created_at"),
            "updatedAt": row.get("updated_at"),
        }
    )


def find_xgj_order_mysql(order_no: str = "", out_order_no: str = "") -> dict[str, Any] | None:
    ensure_mysql_schema()
    if not order_no and not out_order_no:
        return None
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            if order_no:
                cursor.execute("SELECT * FROM xgj_order WHERE order_no = %s", (order_no,))
            else:
                cursor.execute("SELECT * FROM xgj_order WHERE out_order_no = %s", (out_order_no,))
            row = cursor.fetchone()
    return row_to_xgj_order(row) if row else None


def load_xgj_orders_mysql(limit: int = 500) -> list[dict[str, Any]]:
    ensure_mysql_schema()
    safe_limit = max(min(coerce_int(limit, 500), 5000), 1)
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT *
                FROM xgj_order
                ORDER BY created_at DESC
                LIMIT {safe_limit}
                """
            )
            rows = cursor.fetchall()
    orders = [row_to_xgj_order(row) for row in rows]
    return [order for order in orders if order]


def upsert_xgj_orders_mysql(orders: list[dict[str, Any]]) -> None:
    if not orders:
        return
    ensure_mysql_schema()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            for order in orders:
                cursor.execute(
                    """
                    INSERT INTO xgj_order (
                      order_no, out_order_no, order_type, goods_no, goods_name,
                      buy_quantity, order_status, order_amount, order_time, end_time,
                      card_items_json, request_json, remark
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                      out_order_no = VALUES(out_order_no),
                      order_type = VALUES(order_type),
                      goods_no = VALUES(goods_no),
                      goods_name = VALUES(goods_name),
                      buy_quantity = VALUES(buy_quantity),
                      order_status = VALUES(order_status),
                      order_amount = VALUES(order_amount),
                      order_time = VALUES(order_time),
                      end_time = VALUES(end_time),
                      card_items_json = VALUES(card_items_json),
                      request_json = VALUES(request_json),
                      remark = VALUES(remark)
                    """,
                    (
                        str(order.get("orderNo", "")),
                        str(order.get("outOrderNo", "")),
                        coerce_int(order.get("orderType"), 2),
                        str(order.get("goodsNo", "")),
                        str(order.get("goodsName", "")),
                        coerce_int(order.get("buyQuantity"), 1),
                        coerce_int(order.get("orderStatus"), 20),
                        coerce_int(order.get("orderAmount"), 0),
                        coerce_int(order.get("orderTime"), 0),
                        coerce_int(order.get("endTime"), 0),
                        json.dumps(order.get("cardItems", []), ensure_ascii=False),
                        json.dumps(order.get("request", {}), ensure_ascii=False),
                        str(order.get("remark", "")),
                    ),
                )


def row_to_goods_product(row: dict[str, Any]) -> dict[str, Any] | None:
    return normalize_goods_product(
        {
            "goodsNo": row.get("goods_no"),
            "goodsName": row.get("goods_name"),
            "deliveryMode": row.get("delivery_mode"),
            "priceCents": row.get("price"),
            "enabled": bool(row.get("enabled")),
            "note": row.get("note"),
            "createdAt": row.get("created_at"),
            "updatedAt": row.get("updated_at"),
        }
    )


def row_to_stock_item(row: dict[str, Any]) -> dict[str, Any] | None:
    return normalize_stock_item(
        {
            "id": row.get("id"),
            "goodsNo": row.get("goods_no"),
            "cardNo": row.get("card_no"),
            "cardPwd": row.get("card_pwd"),
            "status": row.get("status"),
            "orderNo": row.get("order_no"),
            "soldAt": row.get("sold_at"),
            "note": row.get("note"),
            "createdAt": row.get("created_at"),
            "updatedAt": row.get("updated_at"),
        }
    )


def load_goods_mysql(include_disabled: bool = False) -> list[dict[str, Any]]:
    ensure_mysql_schema()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            where = "" if include_disabled else "WHERE enabled = 1"
            cursor.execute(
                f"""
                SELECT *
                FROM xgj_goods
                {where}
                ORDER BY created_at DESC
                """
            )
            rows = cursor.fetchall()
    goods = [row_to_goods_product(row) for row in rows]
    return [item for item in goods if item]


def count_goods_mysql() -> int:
    ensure_mysql_schema()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM xgj_goods")
            row = cursor.fetchone() or {}
    return int(row.get("total") or 0)


def upsert_goods_mysql(goods: list[dict[str, Any]]) -> None:
    if not goods:
        return
    ensure_mysql_schema()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            for item in goods:
                cursor.execute(
                    """
                    INSERT INTO xgj_goods (
                      goods_no, goods_name, delivery_mode, price, enabled, note, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                      goods_name = VALUES(goods_name),
                      delivery_mode = VALUES(delivery_mode),
                      price = VALUES(price),
                      enabled = VALUES(enabled),
                      note = VALUES(note)
                    """,
                    (
                        str(item.get("goodsNo", "")),
                        str(item.get("goodsName", "")),
                        normalize_delivery_mode(item.get("deliveryMode")),
                        coerce_int(item.get("priceCents"), 0),
                        1 if item.get("enabled", True) else 0,
                        str(item.get("note", "")),
                        parse_datetime(str(item.get("createdAt", ""))) or datetime.now(timezone.utc),
                    ),
                )


def load_stock_items_mysql(
    goods_no: str = "",
    status: str = "",
    limit: int = 1000,
) -> list[dict[str, Any]]:
    ensure_mysql_schema()
    safe_limit = max(min(coerce_int(limit, 1000), 50000), 1)
    clauses = []
    params: list[Any] = []
    if goods_no:
        clauses.append("goods_no = %s")
        params.append(goods_no)
    if status:
        clauses.append("status = %s")
        params.append(status)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT *
                FROM xgj_stock_item
                {where}
                ORDER BY created_at DESC
                LIMIT {safe_limit}
                """,
                params,
            )
            rows = cursor.fetchall()
    items = [row_to_stock_item(row) for row in rows]
    return [item for item in items if item]


def count_stock_items_mysql(goods_no: str = "", status: str = "") -> int:
    ensure_mysql_schema()
    clauses = []
    params: list[Any] = []
    if goods_no:
        clauses.append("goods_no = %s")
        params.append(goods_no)
    if status:
        clauses.append("status = %s")
        params.append(status)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) AS total FROM xgj_stock_item {where}", params)
            row = cursor.fetchone() or {}
    return int(row.get("total") or 0)


def upsert_stock_items_mysql(items: list[dict[str, Any]]) -> None:
    if not items:
        return
    ensure_mysql_schema()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            for item in items:
                cursor.execute(
                    """
                    INSERT INTO xgj_stock_item (
                      id, goods_no, card_no, card_pwd, status, order_no, sold_at, note, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                      goods_no = VALUES(goods_no),
                      card_no = VALUES(card_no),
                      card_pwd = VALUES(card_pwd),
                      status = VALUES(status),
                      order_no = VALUES(order_no),
                      sold_at = VALUES(sold_at),
                      note = VALUES(note)
                    """,
                    (
                        str(item.get("id", "")),
                        str(item.get("goodsNo", "")),
                        str(item.get("cardNo", "")),
                        str(item.get("cardPwd", "")),
                        normalize_stock_status(item.get("status")),
                        str(item.get("orderNo", "")),
                        str(item.get("soldAt", "")),
                        str(item.get("note", "")),
                        parse_datetime(str(item.get("createdAt", ""))) or datetime.now(timezone.utc),
                    ),
                )


def upsert_claims_mysql(claims: list[dict[str, Any]]) -> None:
    if not claims:
        return
    ensure_mysql_schema()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            for claim in claims:
                cursor.execute(
                    """
                    INSERT IGNORE INTO card_message_claim (message_id, card, claimed_at)
                    VALUES (%s, %s, %s)
                    """,
                    (
                        str(claim.get("messageId", "")),
                        str(claim.get("card", "")),
                        str(claim.get("claimedAt", "")),
                    ),
                )


def sync_claim_counts_mysql() -> None:
    ensure_mysql_schema()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE user_card AS user_cards
                LEFT JOIN (
                  SELECT card, COUNT(*) AS total
                  FROM card_message_claim
                  GROUP BY card
                ) AS claims ON claims.card = user_cards.card
                SET user_cards.used_count = GREATEST(
                  user_cards.used_count,
                  COALESCE(claims.total, 0)
                )
                """
            )


def env_user_cards() -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []

    if USER_CARDS_JSON:
        try:
            payload = json.loads(USER_CARDS_JSON)
        except json.JSONDecodeError:
            payload = None

        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    card = normalize_user_card(item)
                    if card:
                        cards.append(card)
        elif isinstance(payload, dict):
            direct_keys = {"card", "token", "cardToken", "phone", "phoneNumber", "number"}
            if direct_keys.intersection(payload):
                card = normalize_user_card(payload)
                if card:
                    cards.append(card)
            else:
                for token, item in payload.items():
                    if isinstance(item, dict):
                        card = normalize_user_card(item, str(token))
                    else:
                        card = normalize_user_card({"phoneNumber": str(item)}, str(token))
                    if card:
                        cards.append(card)

    if USER_CARD_TOKEN:
        card = normalize_user_card(
            {
                "card": USER_CARD_TOKEN,
                "countryCode": USER_COUNTRY_CODE,
                "phoneNumber": USER_PHONE_NUMBER,
                "expiresAt": USER_EXPIRES_AT,
                "receiveLimit": USER_RECEIVE_LIMIT,
                "usedCount": 0,
                "waitSeconds": USER_WAIT_SECONDS,
                "serviceName": USER_SERVICE_NAME,
                "keywords": USER_FILTER_KEYWORDS,
                "enabled": True,
            }
        )
        if card:
            cards.append(card)

    return cards


def configured_user_cards() -> list[dict[str, Any]]:
    if mysql_ready():
        bootstrap_mysql_storage()
        cards = load_user_cards_mysql()
        if cards:
            return cards
    json_cards = load_user_cards_json() if CARDS_FILE.exists() else []
    return json_cards or env_user_cards()


def find_user_card(token: str) -> dict[str, Any] | None:
    for card in load_admin_cards():
        if hmac.compare_digest(token, str(card.get("card", ""))):
            return card
    return None


def generate_card_token() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(10))


def generate_unique_card_token(existing_tokens: set[str]) -> str:
    for _ in range(1000):
        token = generate_card_token()
        if token not in existing_tokens:
            existing_tokens.add(token)
            return token
    raise RuntimeError("无法生成唯一卡密")


def load_admin_cards() -> list[dict[str, Any]]:
    if mysql_ready():
        bootstrap_mysql_storage()
        return load_user_cards_mysql(include_disabled=True)
    cards = load_user_cards_json(include_disabled=True)
    return cards or env_user_cards()


def load_admin_phones(include_disabled: bool = True) -> list[dict[str, Any]]:
    if mysql_ready():
        bootstrap_mysql_storage()
        phones = load_phones_mysql(include_disabled=include_disabled)
    else:
        phones = load_phones_json(include_disabled=include_disabled)
    return phones


def load_xgj_orders(limit: int = 500) -> list[dict[str, Any]]:
    if mysql_ready():
        bootstrap_mysql_storage()
        return load_xgj_orders_mysql(limit=limit)
    return load_xgj_orders_json()[: max(min(coerce_int(limit, 500), 5000), 1)]


def count_xgj_orders(min_status: int | None = None) -> int:
    if mysql_ready():
        bootstrap_mysql_storage()
        return count_xgj_orders_mysql(min_status=min_status)
    orders = load_xgj_orders_json()
    if min_status is None:
        return len(orders)
    return len([order for order in orders if coerce_int(order.get("orderStatus"), 20) >= min_status])


def save_admin_phone(phone: dict[str, Any]) -> dict[str, Any]:
    with STORE_LOCK:
        return _save_admin_phone_locked(phone)


def _save_admin_phone_locked(phone: dict[str, Any]) -> dict[str, Any]:
    validate_phone_input(phone)
    now = utc_now_iso()
    existing = find_admin_phone(str(phone.get("id", "")))
    if existing:
        if active_cards_for_phone(existing) and phone_key(existing) != phone_key(phone):
            raise ValueError("手机号有有效卡密时不能修改号码")
        phone["createdAt"] = existing.get("createdAt") or now
    else:
        phone["createdAt"] = now
    phone["updatedAt"] = now

    if mysql_ready():
        bootstrap_mysql_storage()
        upsert_phones_mysql([phone])
    else:
        phones = load_phones_json(include_disabled=True)
        by_id = {str(item.get("id", "")): item for item in phones}
        by_id[str(phone.get("id", ""))] = phone
        save_phones_json(list(by_id.values()))
    return phone


def find_admin_phone(phone_id: str) -> dict[str, Any] | None:
    for phone in load_admin_phones(include_disabled=True):
        if hmac.compare_digest(phone_id, str(phone.get("id", ""))):
            return phone
    return None


def find_admin_phone_by_number(phone_number: str) -> dict[str, Any] | None:
    digits = re.sub(r"\D+", "", str(phone_number))
    for phone in load_admin_phones(include_disabled=True):
        if digits and phone_key(phone) == f"phone:{digits}":
            return phone
    return None


def delete_admin_phone(phone_id: str) -> bool:
    with STORE_LOCK:
        return _delete_admin_phone_locked(phone_id)


def _delete_admin_phone_locked(phone_id: str) -> bool:
    phone = find_admin_phone(phone_id)
    if phone and active_cards_for_phone(phone):
        raise ValueError("手机号仍有有效卡密，不能删除")
    if mysql_ready():
        bootstrap_mysql_storage()
        with mysql_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM phone_pool WHERE id = %s", (phone_id,))
                return cursor.rowcount > 0

    phones = load_phones_json(include_disabled=True)
    kept = [phone for phone in phones if not hmac.compare_digest(phone_id, str(phone.get("id", "")))]
    if len(kept) == len(phones):
        return False
    save_phones_json(kept)
    return True


def set_admin_phone_enabled(phone_id: str, enabled: bool) -> bool:
    with STORE_LOCK:
        return _set_admin_phone_enabled_locked(phone_id, enabled)


def _set_admin_phone_enabled_locked(phone_id: str, enabled: bool) -> bool:
    phone = find_admin_phone(phone_id)
    if not phone:
        return False
    if not enabled and active_cards_for_phone(phone):
        raise ValueError("手机号仍有有效卡密，不能禁用")
    phone["enabled"] = enabled
    save_admin_phone(phone)
    return True


def phone_from_body(body: dict[str, Any]) -> dict[str, Any]:
    phone = normalize_phone(
        {
            "id": body.get("id", ""),
            "countryCode": body.get("countryCode", USER_COUNTRY_CODE),
            "phoneNumber": body.get("phoneNumber", ""),
            "deviceId": body.get("deviceId", ""),
            "simNumber": body.get("simNumber", ""),
            "label": body.get("label", ""),
            "provider": body.get("provider", ""),
            "note": body.get("note", ""),
            "enabled": body.get("enabled", True),
        }
    )
    if not phone:
        raise ValueError("手机号不能为空")
    validate_phone_input(phone)
    return phone


def phone_key(phone: dict[str, Any]) -> str:
    digits = re.sub(r"\D+", "", str(phone.get("phoneNumber", "")))
    if digits:
        return f"phone:{digits}"
    phone_id = str(phone.get("id", "")).strip()
    if phone_id:
        return f"id:{phone_id}"
    return "phone:"


def active_cards_for_phone(phone: dict[str, Any]) -> list[dict[str, Any]]:
    phone_id = str(phone.get("id", "")).strip()
    key = phone_key(phone)
    return [
        card
        for card in load_admin_cards()
        if card_holds_phone_lease(card)
        and (
            (phone_id and hmac.compare_digest(phone_id, str(card.get("phoneId", "")).strip()))
            or card_phone_key(card) == key
        )
    ]


def validate_phone_input(phone: dict[str, Any]) -> None:
    digits = re.sub(r"\D+", "", str(phone.get("phoneNumber", "")))
    if len(digits) < 6 or len(digits) > 20:
        raise ValueError("手机号格式不正确")
    device_id = str(phone.get("deviceId", "")).strip()
    sim_number = str(phone.get("simNumber", "")).strip()
    if sim_number and not device_id:
        raise ValueError("填写 SIM 卡槽时必须同时填写设备 ID")
    for existing in load_admin_phones(include_disabled=True):
        if hmac.compare_digest(str(existing.get("id", "")), str(phone.get("id", ""))):
            continue
        if phone_key(existing) == phone_key(phone):
            raise ValueError("手机号已存在")
        existing_device = str(existing.get("deviceId", "")).strip()
        existing_sim = str(existing.get("simNumber", "")).strip()
        if device_id and device_id == existing_device and (
            not sim_number or not existing_sim or sim_number == existing_sim
        ):
            raise ValueError("该设备路由与其他手机号冲突，请填写唯一的 SIM 卡槽")


def card_phone_key(card: dict[str, Any]) -> str:
    digits = re.sub(r"\D+", "", str(card.get("phoneNumber", "")))
    if digits:
        return f"phone:{digits}"
    phone_id = str(card.get("phoneId", "")).strip()
    if phone_id:
        return f"id:{phone_id}"
    return "phone:"


def card_holds_phone_lease(card: dict[str, Any]) -> bool:
    expires_at = parse_datetime(str(card.get("expiresAt", "")))
    return coerce_bool(card.get("enabled"), True) and bool(expires_at and expires_at > datetime.now(timezone.utc))


def phone_usage_map(cards: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    usage: dict[str, dict[str, int]] = {}
    for card in cards:
        key = card_phone_key(card)
        if key in {"id:", "phone:"}:
            continue
        bucket = usage.setdefault(key, {"cards": 0, "activeCards": 0})
        bucket["cards"] += 1
        if card_holds_phone_lease(card):
            bucket["activeCards"] += 1
    return usage


def active_phone_leases(cards: list[dict[str, Any]], exclude_card: str = "") -> dict[str, dict[str, Any]]:
    leases: dict[str, dict[str, Any]] = {}
    for card in cards:
        token = str(card.get("card", ""))
        if exclude_card and hmac.compare_digest(token, exclude_card):
            continue
        if not card_holds_phone_lease(card):
            continue
        key = card_phone_key(card)
        if key not in {"id:", "phone:"}:
            leases.setdefault(key, card)
    return leases


def assert_card_phone_available(card: dict[str, Any], cards: list[dict[str, Any]]) -> None:
    key = card_phone_key(card)
    if key in {"id:", "phone:"}:
        raise ValueError("卡密必须绑定手机号")
    phone_id = str(card.get("phoneId", "")).strip()
    pool_phone = find_admin_phone(phone_id) if phone_id else find_admin_phone_by_number(
        str(card.get("phoneNumber", ""))
    )
    if pool_phone and not pool_phone.get("enabled", True):
        raise ValueError("卡密不能绑定已禁用的号池手机号")
    lease = active_phone_leases(cards, exclude_card=str(card.get("card", ""))).get(key)
    if lease:
        raise ValueError(f"手机号已有有效卡密：{lease.get('card', '')}")


def phone_payload(phone: dict[str, Any]) -> dict[str, Any]:
    usage = phone_usage_map(load_admin_cards()).get(phone_key(phone), {"cards": 0, "activeCards": 0})
    return {
        **phone,
        "cards": usage["cards"],
        "activeCards": usage["activeCards"],
    }


def admin_phone_payloads() -> list[dict[str, Any]]:
    usage = phone_usage_map(load_admin_cards())
    payloads = []
    for phone in load_admin_phones(include_disabled=True):
        item_usage = usage.get(phone_key(phone), {"cards": 0, "activeCards": 0})
        payloads.append({**phone, "cards": item_usage["cards"], "activeCards": item_usage["activeCards"]})
    return payloads


def apply_phone_to_card(card: dict[str, Any], phone: dict[str, Any]) -> dict[str, Any]:
    return {
        **card,
        "phoneId": phone.get("id", ""),
        "countryCode": phone.get("countryCode", "+86"),
        "phoneNumber": phone.get("phoneNumber", ""),
    }


def choose_phone_from_pool(cards: list[dict[str, Any]]) -> dict[str, Any]:
    phones = [phone for phone in load_admin_phones(include_disabled=False) if phone.get("enabled", True)]
    leases = active_phone_leases(cards)
    phones = [phone for phone in phones if phone_key(phone) not in leases]
    if not phones:
        raise ValueError("号池没有空闲手机号")

    usage = phone_usage_map(cards)
    return min(
        phones,
        key=lambda phone: (
            usage.get(phone_key(phone), {}).get("activeCards", 0),
            usage.get(phone_key(phone), {}).get("cards", 0),
            str(phone.get("createdAt", "")),
            str(phone.get("phoneNumber", "")),
        ),
    )


def save_admin_card(card: dict[str, Any]) -> dict[str, Any]:
    with STORE_LOCK:
        return _save_admin_card_locked(card)


def _save_admin_card_locked(card: dict[str, Any]) -> dict[str, Any]:
    now = utc_now_iso()
    existing = find_admin_card(str(card.get("card", "")))
    if existing:
        if (
            coerce_int(existing.get("usedCount"), 0) > 0
            and card_phone_key(existing) != card_phone_key(card)
        ):
            raise ValueError("已接码卡密不能修改手机号，请删除后新建卡密")
        card["createdAt"] = existing.get("createdAt") or now
        card["usedCount"] = max(
            coerce_int(existing.get("usedCount"), 0),
            coerce_int(card.get("usedCount"), 0),
        )
    else:
        card["createdAt"] = now
    card["updatedAt"] = now
    if card_holds_phone_lease(card):
        assert_card_phone_available(card, load_admin_cards())

    if mysql_ready():
        bootstrap_mysql_storage()
        upsert_user_cards_mysql([card])
    else:
        cards = load_user_cards_json(include_disabled=True)
        by_card = {str(item.get("card", "")): item for item in cards}
        by_card[str(card.get("card", ""))] = card
        save_user_cards_json(list(by_card.values()))
    return card


def find_admin_card(token: str) -> dict[str, Any] | None:
    for card in load_admin_cards():
        if hmac.compare_digest(token, str(card.get("card", ""))):
            return card
    return None


def delete_admin_card(token: str) -> bool:
    with STORE_LOCK:
        return _delete_admin_card_locked(token)


def _delete_admin_card_locked(token: str) -> bool:
    if mysql_ready():
        bootstrap_mysql_storage()
        with mysql_connection() as conn:
            conn.begin()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM card_message_claim WHERE card = %s", (token,))
                    cursor.execute("DELETE FROM user_card WHERE card = %s", (token,))
                    deleted = cursor.rowcount > 0
                conn.commit()
                return deleted
            except Exception:
                conn.rollback()
                raise

    cards = load_user_cards_json(include_disabled=True)
    kept = [card for card in cards if not hmac.compare_digest(token, str(card.get("card", "")))]
    if len(kept) == len(cards):
        return False
    claims = [
        claim
        for claim in load_claims_json()
        if not hmac.compare_digest(token, str(claim.get("card", "")))
    ]
    save_claims_json(claims)
    save_user_cards_json(kept)
    return True


def set_admin_card_enabled(token: str, enabled: bool) -> bool:
    with STORE_LOCK:
        return _set_admin_card_enabled_locked(token, enabled)


def _set_admin_card_enabled_locked(token: str, enabled: bool) -> bool:
    card = find_admin_card(token)
    if not card:
        return False
    card["enabled"] = enabled
    save_admin_card(card)
    return True


def make_card_from_template(body: dict[str, Any], token: str) -> dict[str, Any]:
    settings = load_admin_settings()
    expires_at = body.get("expiresAt") or default_card_expires_at(
        coerce_int(settings.get("defaultCardExpireMinutes"), DEFAULT_CARD_EXPIRE_MINUTES)
    )
    receive_limit = body.get("receiveLimit")
    if receive_limit in {None, ""}:
        receive_limit = settings.get("defaultCardReceiveLimit", DEFAULT_CARD_RECEIVE_LIMIT)
    card = normalize_user_card(
        {
            "card": token,
            "phoneId": body.get("phoneId", ""),
            "countryCode": body.get("countryCode", USER_COUNTRY_CODE),
            "phoneNumber": body.get("phoneNumber", ""),
            "expiresAt": expires_at,
            "receiveLimit": receive_limit,
            "usedCount": 0,
            "waitSeconds": body.get("waitSeconds", USER_WAIT_SECONDS),
            "serviceName": body.get("serviceName", USER_SERVICE_NAME),
            "keywords": body.get("keywords", body.get("keywordsText", "")),
            "enabled": body.get("enabled", True),
        }
    )
    if not card:
        raise ValueError("卡密不能为空")
    return card


def validate_card_input(card: dict[str, Any]) -> None:
    token = str(card.get("card", "")).strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", token):
        raise ValueError("卡密必须是 8-64 位字母、数字、下划线或短横线")
    phone = re.sub(r"\D+", "", str(card.get("phoneNumber", "")))
    if len(phone) < 6 or len(phone) > 20:
        raise ValueError("手机号格式不正确")
    expires_at = parse_datetime(str(card.get("expiresAt", "")))
    if not expires_at:
        raise ValueError("必须设置有效的到期时间")
    if expires_at <= datetime.now(timezone.utc):
        raise ValueError("到期时间必须晚于当前时间")
    receive_limit = coerce_int(card.get("receiveLimit"), 0)
    if receive_limit < 1 or receive_limit > 100:
        raise ValueError("可接码次数必须在 1-100 之间")
    wait_seconds = coerce_int(card.get("waitSeconds"), 0)
    if wait_seconds < 10 or wait_seconds > 3600:
        raise ValueError("等待秒数必须在 10-3600 之间")
    if not card.get("keywords"):
        raise ValueError("至少设置一个过滤关键词")


def create_admin_cards(body: dict[str, Any]) -> list[dict[str, Any]]:
    with STORE_LOCK:
        return _create_admin_cards_locked(body)


def _create_admin_cards_locked(body: dict[str, Any]) -> list[dict[str, Any]]:
    count = coerce_int(body.get("count"), 1)
    if count < 1:
        raise ValueError("生成数量至少为 1")
    if count > 500:
        raise ValueError("单次最多生成 500 张卡密")

    now = utc_now_iso()
    existing_cards = load_admin_cards()
    existing_tokens = {str(card.get("card", "")) for card in existing_cards}
    assignment_mode = str(body.get("assignmentMode", "manual")).strip().lower()
    selected_phone = find_admin_phone(str(body.get("phoneId", ""))) if body.get("phoneId") else None
    cards = []
    for _ in range(count):
        token = generate_unique_card_token(existing_tokens)
        card = make_card_from_template(body, token)
        if assignment_mode == "pool":
            card = apply_phone_to_card(card, choose_phone_from_pool(existing_cards + cards))
        elif assignment_mode == "selected":
            if not selected_phone:
                raise ValueError("请选择号池手机号")
            card = apply_phone_to_card(card, selected_phone)
        validate_card_input(card)
        if card_holds_phone_lease(card):
            assert_card_phone_available(card, existing_cards + cards)
        card["createdAt"] = now
        card["updatedAt"] = now
        cards.append(card)

    if mysql_ready():
        bootstrap_mysql_storage()
        upsert_user_cards_mysql(cards)
    else:
        current = load_user_cards_json(include_disabled=True)
        by_card = {str(item.get("card", "")): item for item in current}
        for card in cards:
            by_card[str(card.get("card", ""))] = card
        save_user_cards_json(list(by_card.values()))
    return cards


def extract_code(text: str) -> str:
    matches = re.findall(r"(?<!\d)\d{4,8}(?!\d)", str(text or ""))
    return matches[0] if matches else ""


def message_matches_user_card(message: dict[str, Any], card: dict[str, Any]) -> bool:
    keywords = [keyword.casefold() for keyword in card.get("keywords", []) if keyword]
    haystack = json.dumps(message, ensure_ascii=False, default=str).casefold()
    if keywords and not any(keyword in haystack for keyword in keywords):
        return False

    phone = re.sub(r"\D+", "", str(card.get("phoneNumber", "")))
    recipient = re.sub(r"\D+", "", str(message.get("recipient", "")))
    if phone and recipient:
        shorter = min(len(phone), len(recipient))
        if phone != recipient and not (
            shorter >= 8 and (phone.endswith(recipient) or recipient.endswith(phone))
        ):
            return False
    elif phone:
        phone_id = str(card.get("phoneId", "")).strip()
        pool_phone = find_admin_phone(phone_id) if phone_id else find_admin_phone_by_number(
            str(card.get("phoneNumber", ""))
        )
        if not pool_phone:
            return False
        expected_device = str(pool_phone.get("deviceId", "")).strip()
        expected_sim = str(pool_phone.get("simNumber", "")).strip()
        message_device = str(message.get("deviceId", "")).strip()
        message_sim = str(message.get("simNumber", "")).strip()
        if not expected_device or not message_device or expected_device != message_device:
            return False
        if expected_sim and expected_sim != message_sim:
            return False

    return True


def format_user_message(message: dict[str, Any]) -> dict[str, Any]:
    body = str(message.get("message", ""))
    return {
        "id": str(message.get("id", "")),
        "code": extract_code(body),
        "receivedAt": str(message.get("receivedAt", "")),
    }


def parse_datetime(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        parsed = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def is_card_expired(card: dict[str, Any]) -> bool:
    expires_at = parse_datetime(str(card.get("expiresAt", "")))
    return bool(expires_at and expires_at <= datetime.now(timezone.utc))


def card_usage(card: dict[str, Any]) -> dict[str, Any]:
    used_count = max(coerce_int(card.get("usedCount"), 0), 0)
    receive_limit = max(coerce_int(card.get("receiveLimit"), USER_RECEIVE_LIMIT), 0)
    remaining = max(receive_limit - used_count, 0)
    expires_at = parse_datetime(str(card.get("expiresAt", "")))
    expired = bool(expires_at and expires_at <= datetime.now(timezone.utc))
    enabled = coerce_bool(card.get("enabled"), True)

    reason = ""
    if not enabled:
        reason = "卡密已禁用"
    elif not expires_at:
        reason = "卡密到期时间未配置"
    elif expired:
        reason = "卡密已过期"
    elif receive_limit <= 0:
        reason = "接码次数未配置"
    elif remaining <= 0:
        reason = "接码次数已用完"

    return {
        "usedCount": used_count,
        "receiveLimit": receive_limit,
        "remainingCount": remaining,
        "expired": expired,
        "enabled": enabled,
        "available": enabled and bool(expires_at) and not expired and receive_limit > 0 and remaining > 0,
        "unavailableReason": reason,
    }


def message_is_after_card_creation(message: dict[str, Any], card: dict[str, Any]) -> bool:
    card_created = parse_datetime(str(card.get("createdAt", "")))
    message_received = parse_datetime(str(message.get("receivedAt") or message.get("createdAt") or ""))
    return bool(card_created and message_received and message_received >= card_created)


def claim_candidates(card: dict[str, Any], messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [
        message
        for message in messages
        if extract_code(str(message.get("message", "")))
        and message_is_after_card_creation(message, card)
        and message_matches_user_card(message, card)
    ]
    return sorted(candidates, key=lambda item: item.get("receivedAt") or item.get("createdAt") or "")


def claimed_messages_from_ids(messages: list[dict[str, Any]], message_ids: set[str]) -> list[dict[str, Any]]:
    claimed = [message for message in messages if str(message.get("id", "")) in message_ids]
    return sorted(claimed, key=lambda item: item.get("receivedAt") or item.get("createdAt") or "", reverse=True)


def claim_messages_for_card_json(card: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    token = str(card.get("card", ""))
    with STORE_LOCK:
        cards = load_user_cards_json(include_disabled=True)
        if not cards:
            cards = env_user_cards()
        current = next(
            (item for item in cards if hmac.compare_digest(token, str(item.get("card", "")))),
            card,
        )
        if not current.get("createdAt"):
            current["createdAt"] = utc_now_iso()

        messages = load_messages_json()
        claims = load_claims_json()
        claimed_ids = {
            str(claim.get("messageId", ""))
            for claim in claims
            if hmac.compare_digest(token, str(claim.get("card", "")))
        }
        used_count = max(coerce_int(current.get("usedCount"), 0), len(claimed_ids))
        current["usedCount"] = used_count
        usage = card_usage(current)

        if usage["available"]:
            all_claimed_ids = {str(claim.get("messageId", "")) for claim in claims}
            for message in claim_candidates(current, messages):
                message_id = str(message.get("id", ""))
                if not message_id or message_id in all_claimed_ids:
                    continue
                if used_count >= usage["receiveLimit"]:
                    break
                claims.append({"messageId": message_id, "card": token, "claimedAt": utc_now_iso()})
                all_claimed_ids.add(message_id)
                claimed_ids.add(message_id)
                used_count += 1

        current["usedCount"] = used_count
        current["updatedAt"] = utc_now_iso()
        by_card = {str(item.get("card", "")): item for item in cards}
        by_card[token] = current
        save_user_cards_json(list(by_card.values()))
        save_claims_json(claims)

        final_usage = card_usage(current)
        if not final_usage["enabled"] or final_usage["expired"]:
            return current, []
        return current, claimed_messages_from_ids(messages, claimed_ids)


def claim_messages_for_card_mysql(card: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ensure_mysql_schema()
    token = str(card.get("card", ""))
    messages = load_messages_mysql()
    current = dict(card)
    claimed_ids: set[str] = set()

    with mysql_connection() as conn:
        conn.begin()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT used_count, receive_limit, expires_at, enabled, created_at
                    FROM user_card
                    WHERE card = %s
                    FOR UPDATE
                    """,
                    (token,),
                )
                row = cursor.fetchone()
                if not row:
                    conn.rollback()
                    return card, []

                current["usedCount"] = int(row.get("used_count") or 0)
                current["receiveLimit"] = int(row.get("receive_limit") or 0)
                current["expiresAt"] = str(row.get("expires_at") or "")
                current["enabled"] = bool(row.get("enabled"))
                current["createdAt"] = str(row.get("created_at") or current.get("createdAt") or "")

                cursor.execute(
                    "SELECT message_id FROM card_message_claim WHERE card = %s",
                    (token,),
                )
                claimed_ids = {str(item.get("message_id", "")) for item in cursor.fetchall()}
                used_count = max(coerce_int(current.get("usedCount"), 0), len(claimed_ids))
                current["usedCount"] = used_count
                usage = card_usage(current)

                if usage["available"]:
                    for message in claim_candidates(current, messages):
                        if used_count >= usage["receiveLimit"]:
                            break
                        message_id = str(message.get("id", ""))
                        if not message_id:
                            continue
                        cursor.execute(
                            """
                            INSERT IGNORE INTO card_message_claim (message_id, card, claimed_at)
                            VALUES (%s, %s, %s)
                            """,
                            (message_id, token, utc_now_iso()),
                        )
                        if cursor.rowcount > 0:
                            claimed_ids.add(message_id)
                            used_count += 1

                current["usedCount"] = used_count
                cursor.execute(
                    "UPDATE user_card SET used_count = %s WHERE card = %s",
                    (used_count, token),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    usage = card_usage(current)
    if not usage["enabled"] or usage["expired"]:
        return current, []
    return current, claimed_messages_from_ids(messages, claimed_ids)


def claim_messages_for_card(card: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if mysql_ready():
        return claim_messages_for_card_mysql(card)
    return claim_messages_for_card_json(card)


def admin_card_payload(card: dict[str, Any], handler: SimpleHTTPRequestHandler | None = None) -> dict[str, Any]:
    usage = card_usage(card)
    token = str(card.get("card", ""))
    user_url = f"{with_base_path('/user')}?card={quote(token)}"
    if handler:
        user_url = f"{request_origin(handler)}{user_url}"
    return {
        **card,
        **usage,
        "keywordsText": ",".join(card.get("keywords", [])),
        "userUrl": user_url,
    }


def exportable_cards(handler: SimpleHTTPRequestHandler, scope: str) -> list[dict[str, Any]]:
    cards = [admin_card_payload(card, handler) for card in load_admin_cards()]
    if scope == "all":
        return cards
    if scope == "enabled":
        return [card for card in cards if card.get("enabled")]
    return [card for card in cards if card.get("available")]


def cards_export_text(cards: list[dict[str, Any]], export_format: str) -> tuple[str, str, str]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    if export_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "card",
                "phone_id",
                "user_url",
                "phone_number",
                "expires_at",
                "receive_limit",
                "remaining_count",
                "service_name",
                "keywords",
                "enabled",
            ]
        )
        for card in cards:
            writer.writerow(
                [
                    card.get("card", ""),
                    card.get("phoneId", ""),
                    card.get("userUrl", ""),
                    card.get("phoneNumber", ""),
                    card.get("expiresAt", ""),
                    card.get("receiveLimit", ""),
                    card.get("remainingCount", ""),
                    card.get("serviceName", ""),
                    card.get("keywordsText", ""),
                    "1" if card.get("enabled") else "0",
                ]
            )
        return (
            f"cards-{timestamp}.csv",
            output.getvalue(),
            "text/csv; charset=utf-8",
        )

    content = "\n".join(str(card.get("userUrl", "")) for card in cards if card.get("userUrl"))
    if content:
        content += "\n"
    return (
        f"xianyu-cards-{timestamp}.txt",
        content,
        "text/plain; charset=utf-8",
    )


def builtin_sms_goods_product() -> dict[str, Any]:
    return {
        "goodsNo": XGJ_GOODS_NO,
        "goodsType": 2,
        "goodsName": XGJ_GOODS_NAME,
        "deliveryMode": DELIVERY_SMS_LINK,
        "priceCents": XGJ_GOODS_PRICE_CENTS,
        "enabled": XGJ_GOODS_ENABLED,
        "note": "系统内置接码链接商品",
        "createdAt": "",
        "updatedAt": "",
        "builtin": True,
    }


def load_stock_goods(include_disabled: bool = False) -> list[dict[str, Any]]:
    if mysql_ready():
        bootstrap_mysql_storage()
        return load_goods_mysql(include_disabled=include_disabled)
    return load_goods_json(include_disabled=include_disabled)


def load_all_goods(include_disabled: bool = False) -> list[dict[str, Any]]:
    goods = [builtin_sms_goods_product()]
    goods.extend(load_stock_goods(include_disabled=True))
    if not include_disabled:
        goods = [item for item in goods if item.get("enabled", True)]
    return goods


def find_goods_product(goods_no: str, include_disabled: bool = True) -> dict[str, Any] | None:
    for item in load_all_goods(include_disabled=include_disabled):
        if hmac.compare_digest(str(item.get("goodsNo", "")), goods_no):
            return item
    return None


def validate_goods_product(product: dict[str, Any]) -> None:
    goods_no = str(product.get("goodsNo", "")).strip()
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{3,128}", goods_no):
        raise ValueError("商品编号必须是 3-128 位字母、数字、点、冒号、下划线或短横线")
    if hmac.compare_digest(goods_no, XGJ_GOODS_NO):
        raise ValueError("不能覆盖系统内置接码链接商品编号")
    if normalize_delivery_mode(product.get("deliveryMode")) != DELIVERY_STOCK_CODE:
        raise ValueError("后台新增商品当前只支持库存卡密模式")
    if not str(product.get("goodsName", "")).strip():
        raise ValueError("商品名称不能为空")
    if coerce_int(product.get("priceCents"), 0) < 0:
        raise ValueError("商品价格不能小于 0")


def goods_from_body(body: dict[str, Any]) -> dict[str, Any]:
    product = normalize_goods_product(
        {
            "goodsNo": body.get("goodsNo", body.get("goods_no", "")),
            "goodsName": body.get("goodsName", body.get("goods_name", "")),
            "deliveryMode": DELIVERY_STOCK_CODE,
            "priceCents": body.get("priceCents", body.get("price", 0)),
            "enabled": body.get("enabled", True),
            "note": body.get("note", ""),
            "createdAt": body.get("createdAt", ""),
        }
    )
    if not product:
        raise ValueError("商品编号不能为空")
    validate_goods_product(product)
    return product


def save_goods_product(product: dict[str, Any]) -> dict[str, Any]:
    with STORE_LOCK:
        now = utc_now_iso()
        existing = find_goods_product(str(product.get("goodsNo", "")), include_disabled=True)
        if existing and existing.get("builtin"):
            raise ValueError("内置接码链接商品不能编辑")
        product["createdAt"] = existing.get("createdAt") if existing else now
        product["updatedAt"] = now
        if mysql_ready():
            bootstrap_mysql_storage()
            upsert_goods_mysql([product])
        else:
            goods = load_goods_json(include_disabled=True)
            by_no = {str(item.get("goodsNo", "")): item for item in goods}
            by_no[str(product.get("goodsNo", ""))] = product
            save_goods_json(list(by_no.values()))
        return product


def set_goods_enabled(goods_no: str, enabled: bool) -> bool:
    with STORE_LOCK:
        product = find_goods_product(goods_no, include_disabled=True)
        if not product or product.get("builtin"):
            return False
        product["enabled"] = enabled
        save_goods_product(product)
        return True


def delete_goods_product(goods_no: str) -> bool:
    with STORE_LOCK:
        product = find_goods_product(goods_no, include_disabled=True)
        if not product or product.get("builtin"):
            return False
        if count_stock_items(goods_no):
            raise ValueError("商品仍有库存记录，不能删除；可以先禁用商品")
        if mysql_ready():
            bootstrap_mysql_storage()
            with mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM xgj_goods WHERE goods_no = %s", (goods_no,))
                    return cursor.rowcount > 0
        goods = load_goods_json(include_disabled=True)
        kept = [item for item in goods if not hmac.compare_digest(goods_no, str(item.get("goodsNo", "")))]
        if len(kept) == len(goods):
            return False
        save_goods_json(kept)
        return True


def load_stock_items(goods_no: str = "", status: str = "", limit: int = 1000) -> list[dict[str, Any]]:
    if mysql_ready():
        bootstrap_mysql_storage()
        return load_stock_items_mysql(goods_no=goods_no, status=status, limit=limit)
    return load_stock_items_json(goods_no=goods_no, status=status, limit=limit)


def count_stock_items(goods_no: str = "", status: str = "") -> int:
    if mysql_ready():
        bootstrap_mysql_storage()
        return count_stock_items_mysql(goods_no=goods_no, status=status)
    return len(load_stock_items_json(goods_no=goods_no, status=status, limit=50000))


def stock_counts(goods_no: str) -> dict[str, int]:
    return {
        "stockTotal": count_stock_items(goods_no),
        "stockAvailable": count_stock_items(goods_no, STOCK_AVAILABLE),
        "stockSold": count_stock_items(goods_no, STOCK_SOLD),
        "stockDisabled": count_stock_items(goods_no, STOCK_DISABLED),
    }


def admin_goods_payload(product: dict[str, Any]) -> dict[str, Any]:
    goods_no = str(product.get("goodsNo", ""))
    counts = {"stockTotal": 0, "stockAvailable": 0, "stockSold": 0, "stockDisabled": 0}
    if normalize_delivery_mode(product.get("deliveryMode")) == DELIVERY_SMS_LINK:
        counts["stockAvailable"] = xgj_available_stock()
    else:
        counts = stock_counts(goods_no)
    return {
        **product,
        **counts,
        "priceYuan": round(coerce_int(product.get("priceCents"), 0) / 100, 2),
    }


def admin_goods_payloads() -> list[dict[str, Any]]:
    goods = [admin_goods_payload(item) for item in load_all_goods(include_disabled=True)]
    return sorted(
        goods,
        key=lambda item: (
            1 if item.get("builtin") else 2,
            str(item.get("createdAt", "")),
            str(item.get("goodsNo", "")),
        ),
    )


def parse_stock_import_line(line: str) -> tuple[str, str]:
    text = line.strip()
    if not text:
        return "", ""
    if "\t" in text:
        left, right = text.split("\t", 1)
        return left.strip(), right.strip()
    if "," in text:
        try:
            row = next(csv.reader([text]))
        except (csv.Error, StopIteration):
            row = []
        if len(row) >= 2 and row[1].strip():
            return row[0].strip(), ",".join(row[1:]).strip()
    return "", text


def import_stock_items(goods_no: str, raw_text: str, note: str = "") -> list[dict[str, Any]]:
    product = find_goods_product(goods_no, include_disabled=True)
    if not product or normalize_delivery_mode(product.get("deliveryMode")) != DELIVERY_STOCK_CODE:
        raise ValueError("库存商品不存在")
    now = utc_now_iso()
    items: list[dict[str, Any]] = []
    existing = {
        (str(item.get("goodsNo", "")), str(item.get("cardNo", "")), str(item.get("cardPwd", "")))
        for item in load_stock_items(goods_no=goods_no, limit=50000)
    }
    for raw_line in str(raw_text or "").splitlines():
        card_no, card_pwd = parse_stock_import_line(raw_line)
        if not card_pwd:
            continue
        key = (goods_no, card_no, card_pwd)
        if key in existing:
            continue
        item = normalize_stock_item(
            {
                "id": stable_id("stock", goods_no, card_no, card_pwd, now, len(items)),
                "goodsNo": goods_no,
                "cardNo": card_no,
                "cardPwd": card_pwd,
                "status": STOCK_AVAILABLE,
                "note": note,
                "createdAt": now,
                "updatedAt": now,
            }
        )
        if item:
            items.append(item)
            existing.add(key)
    if not items:
        return []
    if mysql_ready():
        bootstrap_mysql_storage()
        upsert_stock_items_mysql(items)
    else:
        current = load_stock_items_json(limit=50000)
        save_stock_items_json(current + items)
    return items


def set_stock_item_status(stock_id: str, status: str) -> bool:
    normalized_status = normalize_stock_status(status)
    with STORE_LOCK:
        if mysql_ready():
            bootstrap_mysql_storage()
            with mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE xgj_stock_item
                        SET status = %s, updated_at = CURRENT_TIMESTAMP(6)
                        WHERE id = %s AND status != %s
                        """,
                        (normalized_status, stock_id, STOCK_SOLD),
                    )
                    return cursor.rowcount > 0
        items = load_stock_items_json(limit=50000)
        changed = False
        for item in items:
            if hmac.compare_digest(stock_id, str(item.get("id", ""))) and item.get("status") != STOCK_SOLD:
                item["status"] = normalized_status
                item["updatedAt"] = utc_now_iso()
                changed = True
        if changed:
            save_stock_items_json(items)
        return changed


def delete_stock_item(stock_id: str) -> bool:
    with STORE_LOCK:
        if mysql_ready():
            bootstrap_mysql_storage()
            with mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM xgj_stock_item WHERE id = %s AND status != %s", (stock_id, STOCK_SOLD))
                    return cursor.rowcount > 0
        items = load_stock_items_json(limit=50000)
        kept = [
            item
            for item in items
            if not (
                hmac.compare_digest(stock_id, str(item.get("id", "")))
                and item.get("status") != STOCK_SOLD
            )
        ]
        if len(kept) == len(items):
            return False
        save_stock_items_json(kept)
        return True


def stock_items_to_card_items(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "card_no": str(item.get("cardNo") or item.get("id") or ""),
            "card_pwd": str(item.get("cardPwd", "")),
        }
        for item in items
    ]


def allocate_stock_items(goods_no: str, count: int, order_no: str) -> list[dict[str, Any]]:
    if count < 1:
        raise ValueError("下单数量错误")
    now = utc_now_iso()
    with STORE_LOCK:
        if mysql_ready():
            bootstrap_mysql_storage()
            with mysql_connection() as conn:
                conn.begin()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT *
                            FROM xgj_stock_item
                            WHERE goods_no = %s AND status = %s
                            ORDER BY created_at ASC
                            LIMIT %s
                            FOR UPDATE
                            """,
                            (goods_no, STOCK_AVAILABLE, count),
                        )
                        rows = cursor.fetchall()
                        if len(rows) < count:
                            conn.rollback()
                            raise ValueError("商品库存不足")
                        ids = [str(row.get("id", "")) for row in rows]
                        placeholders = ",".join(["%s"] * len(ids))
                        cursor.execute(
                            f"""
                            UPDATE xgj_stock_item
                            SET status = %s, order_no = %s, sold_at = %s
                            WHERE id IN ({placeholders})
                            """,
                            [STOCK_SOLD, order_no, now, *ids],
                        )
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
            return [item for item in (row_to_stock_item(row) for row in rows) if item]

        items = load_stock_items_json(limit=50000)
        selected = [
            item
            for item in sorted(items, key=lambda entry: entry.get("createdAt") or "")
            if item.get("goodsNo") == goods_no and item.get("status") == STOCK_AVAILABLE
        ][:count]
        if len(selected) < count:
            raise ValueError("商品库存不足")
        selected_ids = {str(item.get("id", "")) for item in selected}
        for item in items:
            if str(item.get("id", "")) in selected_ids:
                item["status"] = STOCK_SOLD
                item["orderNo"] = order_no
                item["soldAt"] = now
                item["updatedAt"] = now
        save_stock_items_json(items)
        return selected


def xgj_response(data: Any | None = None, code: int = 0, msg: str = "OK") -> dict[str, Any]:
    payload: dict[str, Any] = {"code": int(code), "msg": str(msg)}
    if data is not None:
        payload["data"] = data
    return payload


def xgj_route_path(path: str) -> str:
    prefix = "/api/xianguanjia"
    if path == prefix:
        return "/"
    if path.startswith(f"{prefix}/"):
        return path[len(prefix) :]
    return path


def md5_hex(value: bytes | str) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.md5(data).hexdigest()


def xgj_sign_raw_body(raw_body: bytes, timestamp: str, mch_id: str) -> str:
    body_md5 = md5_hex(raw_body)
    source = ",".join(
        [
            XGJ_APP_ID,
            XGJ_APP_SECRET,
            body_md5,
            str(timestamp),
            str(mch_id),
            XGJ_MCH_SECRET,
        ]
    )
    return md5_hex(source)


def xgj_query_value(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key, [])
    return str(values[-1]).strip() if values else ""


def forwarded_client_ip(handler: SimpleHTTPRequestHandler) -> str:
    return (
        str(handler.headers.get("X-Real-IP", "")).split(",", 1)[0].strip()
        or str(handler.headers.get("X-Forwarded-For", "")).split(",", 1)[0].strip()
        or (handler.client_address[0] if handler.client_address else "")
    )


def xgj_trusted_client_ip(client_ip: str) -> bool:
    try:
        address = ipaddress.ip_address(client_ip)
    except ValueError:
        return False
    for item in XGJ_TRUSTED_IP_RANGES:
        try:
            if address in ipaddress.ip_network(item, strict=False):
                return True
        except ValueError:
            continue
    return False


def verify_xgj_signature(query: dict[str, list[str]], raw_body: bytes) -> tuple[bool, int, str]:
    if not all([XGJ_APP_ID, XGJ_APP_SECRET, XGJ_MCH_ID, XGJ_MCH_SECRET]):
        return False, 500, "闲管家虚拟货源未配置"

    mch_id = xgj_query_value(query, "mch_id")
    timestamp = xgj_query_value(query, "timestamp")
    sign = xgj_query_value(query, "sign").lower()
    if not hmac.compare_digest(mch_id, XGJ_MCH_ID):
        return False, 1000, "商户不存在"
    if not timestamp or not sign:
        return False, 401, "签名错误"
    try:
        signed_at = int(timestamp)
    except ValueError:
        return False, 408, "时间戳已超过有效期"
    if abs(int(time.time()) - signed_at) > XGJ_SIGNATURE_MAX_AGE:
        return False, 408, "时间戳已超过有效期"

    expected = xgj_sign_raw_body(raw_body, timestamp, mch_id)
    if not hmac.compare_digest(sign, expected.lower()):
        return False, 401, "签名错误"
    return True, 0, "OK"


def parse_xgj_body(raw_body: bytes) -> dict[str, Any]:
    if not raw_body:
        return {}
    body = json.loads(raw_body.decode("utf-8"))
    if not isinstance(body, dict):
        raise ValueError("请求内容不正确")
    return body


def xgj_available_stock() -> int:
    phones = [phone for phone in load_admin_phones(include_disabled=False) if phone.get("enabled", True)]
    leases = active_phone_leases(load_admin_cards())
    return len([phone for phone in phones if phone_key(phone) not in leases])


def xgj_goods_payload(product: dict[str, Any] | None = None) -> dict[str, Any]:
    product = product or builtin_sms_goods_product()
    goods_no = str(product.get("goodsNo", ""))
    delivery_mode = normalize_delivery_mode(product.get("deliveryMode"))
    stock = (
        xgj_available_stock()
        if delivery_mode == DELIVERY_SMS_LINK
        else count_stock_items(goods_no, STOCK_AVAILABLE)
    )
    return {
        "goods_no": goods_no,
        "goods_type": 2,
        "goods_name": str(product.get("goodsName", "")),
        "price": coerce_int(product.get("priceCents"), 0),
        "stock": stock,
        "status": 1 if product.get("enabled", True) else 2,
        "delivery_mode": delivery_mode,
        "update_time": int(time.time()),
    }


def xgj_filtered_goods(body: dict[str, Any]) -> list[dict[str, Any]]:
    goods_type = coerce_int(body.get("goods_type"), 0)
    if goods_type and goods_type != 2:
        return []
    keyword = str(body.get("keyword", "")).strip().casefold()
    goods = [xgj_goods_payload(item) for item in load_all_goods(include_disabled=False)]
    if keyword:
        goods = [
            item
            for item in goods
            if keyword in str(item.get("goods_no", "")).casefold()
            or keyword in str(item.get("goods_name", "")).casefold()
        ]
    return goods


def xgj_total_available_stock() -> int:
    return sum(coerce_int(xgj_goods_payload(item).get("stock"), 0) for item in load_all_goods(include_disabled=False))


def find_xgj_order(order_no: str = "", out_order_no: str = "") -> dict[str, Any] | None:
    if mysql_ready():
        bootstrap_mysql_storage()
        return find_xgj_order_mysql(order_no, out_order_no)
    for order in load_xgj_orders_json():
        if order_no and hmac.compare_digest(order_no, str(order.get("orderNo", ""))):
            return order
        if out_order_no and hmac.compare_digest(out_order_no, str(order.get("outOrderNo", ""))):
            return order
    return None


def save_xgj_order(order: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_xgj_order(order)
    if not normalized:
        raise ValueError("订单内容不正确")
    normalized["updatedAt"] = utc_now_iso()
    if mysql_ready():
        bootstrap_mysql_storage()
        upsert_xgj_orders_mysql([normalized])
    else:
        orders = load_xgj_orders_json()
        by_order = {str(item.get("orderNo", "")): item for item in orders}
        by_order[str(normalized.get("orderNo", ""))] = normalized
        save_xgj_orders_json(list(by_order.values()))
    return normalized


def xgj_order_uses_sms_link(order: dict[str, Any]) -> bool:
    request_body = order.get("request")
    if isinstance(request_body, dict):
        delivery_mode = request_body.get("delivery_mode") or request_body.get("deliveryMode")
        if delivery_mode:
            return normalize_delivery_mode(delivery_mode) == DELIVERY_SMS_LINK
    goods_no = str(order.get("goodsNo", ""))
    if goods_no == XGJ_GOODS_NO:
        return True
    product = find_goods_product(goods_no, include_disabled=True) if goods_no else None
    return bool(product and normalize_delivery_mode(product.get("deliveryMode")) == DELIVERY_SMS_LINK)


def xgj_order_card_items(order: dict[str, Any]) -> list[dict[str, str]]:
    card_items = order.get("cardItems", [])
    if not isinstance(card_items, list):
        return []
    if not xgj_order_uses_sms_link(order):
        return card_items
    return [
        {"card_pwd": str(item.get("card_pwd", ""))}
        for item in card_items
        if isinstance(item, dict) and str(item.get("card_pwd", "")).strip()
    ]


def xgj_order_payload(order: dict[str, Any], include_detail_fields: bool = True) -> dict[str, Any]:
    if include_detail_fields:
        payload = {
            "order_type": coerce_int(order.get("orderType"), 2),
            "order_no": str(order.get("orderNo", "")),
            "out_order_no": str(order.get("outOrderNo", "")),
            "order_status": coerce_int(order.get("orderStatus"), 20),
            "order_amount": coerce_int(order.get("orderAmount"), 0),
            "goods_no": str(order.get("goodsNo", "")),
            "goods_name": str(order.get("goodsName", "")),
            "buy_quantity": coerce_int(order.get("buyQuantity"), 1),
            "order_time": coerce_int(order.get("orderTime"), 0),
            "card_items": xgj_order_card_items(order),
        }
    else:
        payload = {
            "out_order_no": str(order.get("outOrderNo", "")),
            "order_no": str(order.get("orderNo", "")),
            "order_status": coerce_int(order.get("orderStatus"), 20),
            "order_amount": coerce_int(order.get("orderAmount"), 0),
            "order_time": coerce_int(order.get("orderTime"), 0),
            "card_items": xgj_order_card_items(order),
        }
    end_time = coerce_int(order.get("endTime"), 0)
    if end_time:
        payload["end_time"] = end_time
    remark = str(order.get("remark", ""))
    if remark:
        payload["remark"] = remark
    return payload


def xgj_order_status_text(status: int) -> str:
    return {
        10: "待处理",
        20: "已发货",
        30: "已完成",
        40: "已关闭",
    }.get(status, f"状态 {status}")


def admin_order_payload(order: dict[str, Any]) -> dict[str, Any]:
    status = coerce_int(order.get("orderStatus"), 20)
    return {
        "orderNo": str(order.get("orderNo", "")),
        "outOrderNo": str(order.get("outOrderNo", "")),
        "goodsNo": str(order.get("goodsNo", "")),
        "goodsName": str(order.get("goodsName", "")),
        "buyQuantity": coerce_int(order.get("buyQuantity"), 1),
        "orderStatus": status,
        "statusText": xgj_order_status_text(status),
        "orderAmount": coerce_int(order.get("orderAmount"), 0),
        "orderTime": coerce_int(order.get("orderTime"), 0),
        "endTime": coerce_int(order.get("endTime"), 0),
        "cardItems": xgj_order_card_items(order),
        "createdAt": str(order.get("createdAt", "")),
        "updatedAt": str(order.get("updatedAt", "")),
    }


def date_key(value: str) -> str:
    parsed = parse_datetime(str(value or ""))
    if not parsed:
        return ""
    return parsed.astimezone(timezone.utc).date().isoformat()


def timestamp_date_key(value: int) -> str:
    if not value:
        return ""
    return datetime.fromtimestamp(value, tz=timezone.utc).date().isoformat()


def dashboard_payload() -> dict[str, Any]:
    today = datetime.now(timezone.utc).date().isoformat()
    messages = load_messages()
    cards = [admin_card_payload(card) for card in load_admin_cards()]
    phones = admin_phone_payloads()
    orders = [admin_order_payload(order) for order in load_xgj_orders(limit=200)]
    audit_logs = load_audit_logs(limit=8)
    orders_total = count_xgj_orders()
    failed_orders_total = count_xgj_orders(min_status=40)

    active_cards = [card for card in cards if card.get("available")]
    exhausted_cards = [
        card
        for card in cards
        if card.get("enabled") and not card.get("expired") and coerce_int(card.get("remainingCount"), 0) <= 0
    ]
    today_messages = [
        item
        for item in messages
        if date_key(str(item.get("receivedAt") or item.get("createdAt") or "")) == today
    ]
    today_cards = [card for card in cards if date_key(str(card.get("createdAt", ""))) == today]
    today_orders = [
        order
        for order in orders
        if date_key(str(order.get("createdAt", ""))) == today
        or timestamp_date_key(coerce_int(order.get("orderTime"), 0)) == today
    ]

    return {
        "summary": {
            "messagesTotal": len(messages),
            "messagesToday": len(today_messages),
            "cardsTotal": len(cards),
            "cardsToday": len(today_cards),
            "cardsActive": len(active_cards),
            "cardsExhausted": len(exhausted_cards),
            "phonesTotal": len(phones),
            "phonesEnabled": len([phone for phone in phones if phone.get("enabled")]),
            "ordersTotal": orders_total,
            "ordersToday": len(today_orders),
            "ordersFailed": failed_orders_total,
            "stock": xgj_total_available_stock(),
        },
        "recentOrders": orders[:8],
        "recentAuditLogs": audit_logs,
    }


def create_xgj_stock_order(
    body: dict[str, Any],
    handler: SimpleHTTPRequestHandler,
    product: dict[str, Any],
) -> dict[str, Any]:
    order_no = str(body.get("order_no", "")).strip()
    buy_quantity = coerce_int(body.get("buy_quantity"), 0)
    goods_no = str(product.get("goodsNo", ""))
    amount = coerce_int(product.get("priceCents"), 0) * buy_quantity
    max_amount = coerce_int(body.get("max_amount"), 0)
    if max_amount and amount > max_amount:
        return xgj_response(code=1202, msg="下单金额低于成本价")
    if count_stock_items(goods_no, STOCK_AVAILABLE) < buy_quantity:
        return xgj_response(code=1102, msg="商品库存不足")

    try:
        stock_items = allocate_stock_items(goods_no, buy_quantity, order_no)
    except ValueError as exc:
        return xgj_response(code=1102, msg=str(exc))

    order_time = int(time.time())
    order = save_xgj_order(
        {
            "orderNo": order_no,
            "outOrderNo": f"XGJ{stable_id('xgj-order', order_no)}",
            "orderType": 2,
            "goodsNo": goods_no,
            "goodsName": str(product.get("goodsName", "")),
            "buyQuantity": buy_quantity,
            "orderStatus": 20,
            "orderAmount": amount,
            "orderTime": order_time,
            "endTime": order_time,
            "cardItems": stock_items_to_card_items(stock_items),
            "request": {**body, "delivery_mode": DELIVERY_STOCK_CODE},
            "remark": "库存卡密自动发货",
            "createdAt": utc_now_iso(),
            "updatedAt": utc_now_iso(),
        }
    )
    record_audit_log(
        "xgj_stock_order_created",
        order_no,
        {
            "goodsNo": goods_no,
            "buyQuantity": buy_quantity,
            "stockIds": [str(item.get("id", "")) for item in stock_items],
        },
        handler.client_address[0] if getattr(handler, "client_address", None) else "",
    )
    return xgj_response(xgj_order_payload(order, include_detail_fields=False))


def create_xgj_card_order(body: dict[str, Any], handler: SimpleHTTPRequestHandler) -> dict[str, Any]:
    with STORE_LOCK:
        return _create_xgj_card_order_locked(body, handler)


def _create_xgj_card_order_locked(body: dict[str, Any], handler: SimpleHTTPRequestHandler) -> dict[str, Any]:
    order_no = str(body.get("order_no", "")).strip()
    goods_no = str(body.get("goods_no", "")).strip()
    buy_quantity = coerce_int(body.get("buy_quantity"), 0)
    if not order_no or not goods_no or buy_quantity < 1:
        return xgj_response(code=1201, msg="下单参数错误")
    if buy_quantity > 100:
        return xgj_response(code=1201, msg="下单数量过大")
    product = find_goods_product(goods_no, include_disabled=True)
    if not product:
        return xgj_response(code=1100, msg="商品不存在")
    if not product.get("enabled", True):
        return xgj_response(code=1101, msg="商品不可用")

    existing = find_xgj_order(order_no=order_no)
    if existing:
        record_audit_log(
            "xgj_order_duplicate",
            order_no,
            {"goodsNo": goods_no, "buyQuantity": buy_quantity},
            handler.client_address[0] if getattr(handler, "client_address", None) else "",
        )
        return xgj_response(xgj_order_payload(existing, include_detail_fields=False))

    if normalize_delivery_mode(product.get("deliveryMode")) == DELIVERY_STOCK_CODE:
        return create_xgj_stock_order(body, handler, product)

    amount = coerce_int(product.get("priceCents"), XGJ_GOODS_PRICE_CENTS) * buy_quantity
    max_amount = coerce_int(body.get("max_amount"), 0)
    if max_amount and amount > max_amount:
        return xgj_response(code=1202, msg="下单金额低于成本价")
    if xgj_available_stock() < buy_quantity:
        return xgj_response(code=1102, msg="商品库存不足")

    settings = load_admin_settings()
    expires_at = default_card_expires_at(
        coerce_int(settings.get("defaultCardExpireMinutes"), DEFAULT_CARD_EXPIRE_MINUTES)
    )
    receive_limit = coerce_int(
        settings.get("defaultCardReceiveLimit"),
        DEFAULT_CARD_RECEIVE_LIMIT,
    )
    try:
        cards = create_admin_cards(
            {
                "assignmentMode": "pool",
                "count": buy_quantity,
                "expiresAt": expires_at,
                "receiveLimit": receive_limit,
                "waitSeconds": XGJ_CARD_WAIT_SECONDS,
                "serviceName": XGJ_GOODS_NAME,
                "keywords": XGJ_CARD_KEYWORDS or USER_FILTER_KEYWORDS or ["验证码"],
                "enabled": True,
            }
        )
    except ValueError as exc:
        message = str(exc)
        code = 1102 if "号池" in message or "手机号" in message else 1201
        return xgj_response(code=code, msg=message)
    except RuntimeError as exc:
        return xgj_response(code=500, msg=str(exc))

    order_time = int(time.time())
    card_items = [
        {
            "card_pwd": admin_card_payload(card, handler).get("userUrl", ""),
        }
        for card in cards
    ]
    order = save_xgj_order(
        {
            "orderNo": order_no,
            "outOrderNo": f"XGJ{stable_id('xgj-order', order_no)}",
            "orderType": 2,
            "goodsNo": goods_no,
            "goodsName": str(product.get("goodsName", XGJ_GOODS_NAME)),
            "buyQuantity": buy_quantity,
            "orderStatus": 20,
            "orderAmount": amount,
            "orderTime": order_time,
            "endTime": order_time,
            "cardItems": card_items,
            "request": {**body, "delivery_mode": DELIVERY_SMS_LINK},
            "createdAt": utc_now_iso(),
            "updatedAt": utc_now_iso(),
        }
    )
    record_audit_log(
        "xgj_order_created",
        order_no,
        {
            "outOrderNo": order.get("outOrderNo", ""),
            "buyQuantity": buy_quantity,
            "cards": [str(card.get("card", "")) for card in cards],
        },
        handler.client_address[0] if getattr(handler, "client_address", None) else "",
    )
    return xgj_response(xgj_order_payload(order, include_detail_fields=False))


def reissue_xgj_stock_order(order_no: str, handler: SimpleHTTPRequestHandler) -> dict[str, Any]:
    order = find_xgj_order(order_no=order_no)
    if not order:
        raise ValueError("订单不存在")
    goods_no = str(order.get("goodsNo", ""))
    product = find_goods_product(goods_no, include_disabled=True)
    if not product or normalize_delivery_mode(product.get("deliveryMode")) != DELIVERY_STOCK_CODE:
        raise ValueError("只有库存卡密订单支持补发")
    quantity = max(coerce_int(order.get("buyQuantity"), 1), 1)
    if count_stock_items(goods_no, STOCK_AVAILABLE) < quantity:
        raise ValueError("商品库存不足，无法补发")
    stock_items = allocate_stock_items(goods_no, quantity, order_no)
    now = utc_now_iso()
    remark = str(order.get("remark", "") or "")
    suffix = f"补发于 {now}"
    order = save_xgj_order(
        {
            **order,
            "cardItems": stock_items_to_card_items(stock_items),
            "orderStatus": 20,
            "endTime": int(time.time()),
            "remark": f"{remark}; {suffix}" if remark else suffix,
            "updatedAt": now,
        }
    )
    record_audit_log(
        "xgj_order_reissued",
        order_no,
        {
            "goodsNo": goods_no,
            "stockIds": [str(item.get("id", "")) for item in stock_items],
        },
        handler.client_address[0] if getattr(handler, "client_address", None) else "",
    )
    return admin_order_payload(order)


def query_xgj_order(body: dict[str, Any]) -> dict[str, Any]:
    order_type = coerce_int(body.get("order_type"), 0)
    if order_type and order_type != 2:
        return xgj_response(code=1200, msg="订单不存在")
    order_no = str(body.get("order_no", "")).strip()
    out_order_no = str(body.get("out_order_no", "")).strip()
    if not order_no and not out_order_no:
        return xgj_response(code=1201, msg="下单参数错误")
    order = find_xgj_order(order_no=order_no, out_order_no=out_order_no)
    if not order:
        return xgj_response(code=1200, msg="订单不存在")
    return xgj_response(xgj_order_payload(order))


def handle_xgj_request(
    handler: SimpleHTTPRequestHandler,
    path: str,
    query: dict[str, list[str]],
) -> None:
    raw_body = read_request_body(handler)

    if path == "/goofish/open/info":
        app_id = coerce_int(XGJ_APP_ID, 0)
        if app_id <= 0:
            json_response(handler, HTTPStatus.OK, xgj_response(code=500, msg="XGJ_APP_ID 未配置"))
            return
        json_response(handler, HTTPStatus.OK, xgj_response({"app_id": app_id}))
        return

    ok, code, msg = verify_xgj_signature(query, raw_body)
    if not ok:
        json_response(handler, HTTPStatus.OK, xgj_response(code=code, msg=msg))
        return

    try:
        body = parse_xgj_body(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        json_response(handler, HTTPStatus.OK, xgj_response(code=1201, msg="下单参数错误"))
        return

    if path == "/goofish/user/info":
        json_response(handler, HTTPStatus.OK, xgj_response({"balance": XGJ_MERCHANT_BALANCE_CENTS}))
        return
    if path == "/goofish/goods/list":
        page_no = max(coerce_int(body.get("page_no"), 1), 1)
        page_size = max(min(coerce_int(body.get("page_size"), 50), 100), 1)
        goods = xgj_filtered_goods(body)
        start = (page_no - 1) * page_size
        json_response(
            handler,
            HTTPStatus.OK,
            xgj_response({"list": goods[start : start + page_size], "count": len(goods)}),
        )
        return
    if path == "/goofish/goods/detail":
        goods_no = str(body.get("goods_no", "")).strip()
        product = find_goods_product(goods_no, include_disabled=True)
        if coerce_int(body.get("goods_type"), 0) != 2 or not product:
            json_response(handler, HTTPStatus.OK, xgj_response(code=1100, msg="商品不存在"))
            return
        json_response(handler, HTTPStatus.OK, xgj_response(xgj_goods_payload(product)))
        return
    if path == "/goofish/order/purchase/create":
        json_response(handler, HTTPStatus.OK, create_xgj_card_order(body, handler))
        return
    if path == "/goofish/order/recharge/create":
        json_response(handler, HTTPStatus.OK, xgj_response(code=1101, msg="仅支持卡密商品"))
        return
    if path == "/goofish/order/detail":
        json_response(handler, HTTPStatus.OK, query_xgj_order(body))
        return

    json_response(handler, HTTPStatus.OK, xgj_response(code=1, msg="请求错误"))


def parse_db_json(value: Any) -> Any:
    if value in (None, ""):
        return {}
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return {}


def db_message_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id", "")),
        "source": str(row.get("source", "")),
        "event": str(row.get("event", "")),
        "sender": str(row.get("sender", "")),
        "recipient": str(row.get("recipient", "")),
        "deviceId": str(row.get("device_id", "")),
        "simNumber": str(row.get("sim_number", "")),
        "message": str(row.get("message", "")),
        "receivedAt": str(row.get("received_at", "")),
        "createdAt": str(row.get("created_at", "")),
        "raw": parse_db_json(row.get("raw_json")),
    }


def load_messages_mysql() -> list[dict[str, Any]]:
    ensure_mysql_schema()
    cutoff = datetime.fromtimestamp(
        time.time() - MESSAGE_RETENTION_DAYS * 86400,
        timezone.utc,
    ).isoformat(timespec="seconds")
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, source, event, sender, recipient, device_id, sim_number, message,
                       received_at, created_at, raw_json
                FROM sms_message
                WHERE received_at >= %s
                ORDER BY received_at DESC, created_at DESC
                LIMIT %s
                """
                ,
                (
                    cutoff,
                    MESSAGE_QUERY_LIMIT,
                ),
            )
            rows = cursor.fetchall()
    return [db_message_row(row) for row in rows]


def save_messages_mysql(messages: list[dict[str, Any]]) -> None:
    upsert_messages_mysql(messages)


def count_messages_mysql() -> int:
    ensure_mysql_schema()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM sms_message")
            row = cursor.fetchone() or {}
    return int(row.get("total") or 0)


def upsert_messages_mysql(new_messages: list[dict[str, Any]]) -> dict[str, int]:
    ensure_mysql_schema()
    cutoff = datetime.fromtimestamp(
        time.time() - MESSAGE_RETENTION_DAYS * 86400,
        timezone.utc,
    ).isoformat(timespec="seconds")
    unique: dict[str, dict[str, Any]] = {}
    for item in new_messages:
        key = str(item.get("id") or "").strip()
        if not key:
            key = stable_id(item.get("sender"), item.get("recipient"), item.get("message"), item.get("receivedAt"))
            item = {**item, "id": key}
        unique[key] = item

    if not unique:
        return {"added": 0, "updated": 0, "total": count_messages_mysql()}

    ids = list(unique)
    existing: set[str] = set()
    with mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM card_message_claim
                WHERE message_id IN (
                  SELECT id FROM sms_message WHERE received_at < %s
                )
                """,
                (cutoff,),
            )
            cursor.execute("DELETE FROM sms_message WHERE received_at < %s", (cutoff,))
            placeholders = ",".join(["%s"] * len(ids))
            cursor.execute(f"SELECT id FROM sms_message WHERE id IN ({placeholders})", ids)
            existing = {str(row.get("id")) for row in cursor.fetchall()}

            for item in unique.values():
                body = str(item.get("message", ""))
                cursor.execute(
                    """
                    INSERT INTO sms_message (
                      id, source, event, sender, recipient, device_id, sim_number, message, code,
                      received_at, created_at, raw_json
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                      source = VALUES(source),
                      event = VALUES(event),
                      sender = VALUES(sender),
                      recipient = VALUES(recipient),
                      device_id = VALUES(device_id),
                      sim_number = VALUES(sim_number),
                      message = VALUES(message),
                      code = VALUES(code),
                      received_at = VALUES(received_at),
                      created_at = IF(sms_message.created_at = '', VALUES(created_at), sms_message.created_at),
                      raw_json = VALUES(raw_json)
                    """,
                    (
                        str(item.get("id", "")),
                        str(item.get("source", "")),
                        str(item.get("event", "")),
                        str(item.get("sender", "")),
                        str(item.get("recipient", "")),
                        str(item.get("deviceId", "")),
                        str(item.get("simNumber", "")),
                        body,
                        extract_code(body),
                        str(item.get("receivedAt", "")),
                        str(item.get("createdAt", "")),
                        json.dumps(item.get("raw", {}), ensure_ascii=False),
                    ),
                )

            cursor.execute("SELECT COUNT(*) AS total FROM sms_message")
            total_row = cursor.fetchone() or {}

    return {
        "added": len(set(ids) - existing),
        "updated": len(existing.intersection(ids)),
        "total": int(total_row.get("total") or 0),
    }


def user_card_payload(card: dict[str, Any]) -> dict[str, Any]:
    if card_usage(card)["available"]:
        poll_once(force=False)
    card, claimed_messages = claim_messages_for_card(card)
    usage = card_usage(card)
    messages = [format_user_message(message) for message in claimed_messages]
    return {
        "ok": True,
        "now": utc_now_iso(),
        "card": {
            "countryCode": card.get("countryCode", "+86"),
            "phoneNumber": card.get("phoneNumber", ""),
            "expiresAt": card.get("expiresAt", ""),
            "receiveLimit": usage["receiveLimit"],
            "usedCount": usage["usedCount"],
            "remainingCount": usage["remainingCount"],
            "available": usage["available"],
            "unavailableReason": usage["unavailableReason"],
            "waitSeconds": card.get("waitSeconds", USER_WAIT_SECONDS),
            "serviceName": card.get("serviceName", USER_SERVICE_NAME),
        },
        "messages": messages[:20],
    }


def normalize_received_at(value: str) -> str:
    stripped = value.strip()
    if stripped.isdigit():
        timestamp = int(stripped)
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        try:
            return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec="microseconds")
        except (OverflowError, OSError, ValueError):
            return value
    parsed = parse_datetime(stripped)
    if parsed:
        return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds")
    return value


def normalize_message(raw: dict[str, Any], source: str = "webhook") -> dict[str, Any]:
    payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else raw
    body = payload if isinstance(payload, dict) else {}

    content = first_present(
        body,
        ["message", "msg", "text", "content", "contentPreview", "body", "description"],
    )
    sender = first_present(body, ["sender", "from", "phoneNumber", "address", "originatingAddress"])
    recipient = first_present(body, ["recipient", "to", "receiver"])
    device_id = first_present(body, ["deviceId", "device_id"], first_present(raw, ["deviceId", "device_id"]))
    sim_number = first_present(body, ["simNumber", "sim_number"], first_present(raw, ["simNumber", "sim_number"]))
    received_at = first_present(
        body,
        ["receivedAt", "sentAt", "createdAt", "date", "timestamp"],
        utc_now_iso(),
    )
    received_at = normalize_received_at(received_at)

    message_id = first_present(raw, ["id"]) if payload is not raw else ""
    if not message_id:
        message_id = first_present(body, ["id", "messageId", "_id"])
    if not message_id:
        message_id = stable_id(sender, recipient, content, received_at)

    return {
        "id": message_id,
        "source": source,
        "event": str(raw.get("event", "")),
        "sender": sender,
        "recipient": recipient,
        "deviceId": device_id,
        "simNumber": sim_number,
        "message": content,
        "receivedAt": received_at,
        "createdAt": utc_now_iso(),
        "raw": raw,
    }


def filter_webhook_messages(messages: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    accepted: list[dict[str, Any]] = []
    for message in messages:
        event = str(message.get("event", "")).strip()
        if event and event != "sms:received":
            continue
        searchable = json.dumps(message, ensure_ascii=False, default=str).casefold()
        if WEBHOOK_FILTER_KEYWORDS and not any(keyword in searchable for keyword in WEBHOOK_FILTER_KEYWORDS):
            continue
        accepted.append(message)

    return accepted, len(messages) - len(accepted)


def upsert_messages(new_messages: list[dict[str, Any]]) -> dict[str, int]:
    if mysql_ready():
        return upsert_messages_mysql(new_messages)
    with STORE_LOCK:
        return _upsert_messages_json_locked(new_messages)


def _upsert_messages_json_locked(new_messages: list[dict[str, Any]]) -> dict[str, int]:
    if not new_messages:
        return {"added": 0, "updated": 0, "total": len(load_messages())}

    current = load_messages()
    by_id = {str(item.get("id")): item for item in current if item.get("id")}
    added = 0
    updated = 0

    for item in new_messages:
        key = str(item.get("id") or "").strip()
        if not key:
            key = stable_id(item.get("sender"), item.get("recipient"), item.get("message"), item.get("receivedAt"))
            item = {**item, "id": key}
        if key in by_id:
            merged = {**by_id[key], **item}
            merged["createdAt"] = by_id[key].get("createdAt") or item.get("createdAt")
            by_id[key] = merged
            updated += 1
        else:
            by_id[key] = item
            added += 1

    kept = sorted(
        by_id.values(),
        key=lambda item: item.get("receivedAt") or item.get("createdAt") or "",
        reverse=True,
    )[:MESSAGE_QUERY_LIMIT]
    save_messages(kept)
    return {"added": added, "updated": updated, "total": len(kept)}


def gateway_configured() -> bool:
    return bool(SMS_GATEWAY_BASE_URL and SMS_GATEWAY_USER and SMS_GATEWAY_PASSWORD)


def fetch_gateway_inbox() -> dict[str, Any]:
    if not gateway_configured():
        return {"ok": False, "error": "SMS_GATEWAY_BASE_URL/SMS_GATEWAY_USER/SMS_GATEWAY_PASSWORD 未配置"}

    url = f"{SMS_GATEWAY_BASE_URL}/inbox?type=SMS&limit={POLL_LIMIT}"
    token = base64.b64encode(f"{SMS_GATEWAY_USER}:{SMS_GATEWAY_PASSWORD}".encode("utf-8")).decode(
        "ascii"
    )
    request = Request(url, headers={"Authorization": f"Basic {token}", "Accept": "application/json"})

    try:
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return {"ok": False, "error": f"手机网关返回 HTTP {exc.code}"}
    except URLError as exc:
        return {"ok": False, "error": f"无法连接手机网关：{exc.reason}"}
    except Exception as exc:
        return {"ok": False, "error": f"读取手机短信失败：{exc}"}

    items: list[Any]
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        data = payload.get("data") or payload.get("messages") or payload.get("items") or []
        items = data if isinstance(data, list) else []
    else:
        items = []

    normalized = [normalize_message(item, "gateway") for item in items if isinstance(item, dict)]
    result = upsert_messages(normalized)
    return {"ok": True, **result}


def poll_once(force: bool = False) -> dict[str, Any]:
    if not gateway_configured():
        POLL_STATE.update(
            {
                "lastPollOk": False,
                "lastPollError": "手机网关未配置",
                "nextPollAt": None,
            }
        )
        return {"ok": False, "error": POLL_STATE["lastPollError"]}

    now = time.time()
    next_poll_at = POLL_STATE.get("nextPollAt")
    if not force and next_poll_at and now < float(next_poll_at):
        return {"ok": True, "skipped": True}

    result = fetch_gateway_inbox()
    POLL_STATE.update(
        {
            "lastPollAt": utc_now_iso(),
            "lastPollOk": bool(result.get("ok")),
            "lastPollError": None if result.get("ok") else result.get("error"),
            "nextPollAt": now + max(POLL_SECONDS, 3),
        }
    )
    return result


def format_public_config() -> dict[str, Any]:
    card_defaults = load_admin_settings()
    return {
        "gatewayConfigured": gateway_configured(),
        "gatewayBaseUrl": SMS_GATEWAY_BASE_URL,
        "pollSeconds": POLL_SECONDS,
        "basePath": BASE_PATH,
        "cardDefaults": card_defaults,
        "storageBackend": storage_backend(),
        "mysqlRequested": wants_mysql(),
        "mysqlReady": mysql_ready(),
        "mysqlDatabase": MYSQL_DATABASE if mysql_ready() else "",
        "webhookPath": with_base_path("/api/sms-webhook"),
        "webhookTokenSet": bool(WEBHOOK_TOKEN and WEBHOOK_TOKEN != "change-me-token"),
        "webhookSignatureEnabled": bool(WEBHOOK_SIGNING_KEY),
        "webhookFilterEnabled": bool(WEBHOOK_FILTER_KEYWORDS),
        "poll": POLL_STATE,
    }


def health_status() -> dict[str, Any]:
    database_ok = True
    database_error = ""
    if wants_mysql():
        try:
            with mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1 AS ok")
                    cursor.fetchone()
        except Exception as exc:
            database_ok = False
            database_error = str(exc)
    return {
        "ok": database_ok,
        "storageBackend": storage_backend(),
        "databaseOk": database_ok,
        "databaseError": "database unavailable" if database_error else "",
        "gatewayConfigured": gateway_configured(),
        "lastPollOk": POLL_STATE.get("lastPollOk"),
        "lastPollAt": POLL_STATE.get("lastPollAt"),
    }


def validate_runtime_security() -> None:
    public_bind = HOST not in {"127.0.0.1", "localhost", "::1"}
    if not public_bind or ALLOW_INSECURE_DEFAULTS:
        return
    problems = []
    if DASHBOARD_PASSWORD in {"", "change-me", "change-this-password"}:
        problems.append("DASHBOARD_PASSWORD")
    if WEBHOOK_TOKEN in {"", "change-me-token", "change-this-token"}:
        problems.append("WEBHOOK_TOKEN")
    if WEBHOOK_SIGNING_KEY in {"change-me-signing-key", "change-this-signing-key"}:
        problems.append("WEBHOOK_SIGNING_KEY")
    if USER_CARD_TOKEN in {"change-me-user-card", "change-this-user-card"}:
        problems.append("USER_CARD_TOKEN")
    if not PUBLIC_BASE_URL or "your-domain.example" in PUBLIC_BASE_URL:
        problems.append("PUBLIC_BASE_URL")
    if problems:
        raise RuntimeError(f"公网绑定前必须修改：{', '.join(problems)}")


def safe_query(path: str) -> tuple[str, dict[str, list[str]]]:
    parsed = urlparse(path)
    clean_path = parsed.path
    if BASE_PATH:
        if clean_path == BASE_PATH:
            clean_path = "/"
        elif clean_path.startswith(f"{BASE_PATH}/"):
            clean_path = clean_path[len(BASE_PATH) :]
    return clean_path, parse_qs(parsed.query)


def with_base_path(path: str) -> str:
    if not BASE_PATH:
        return path
    if path == "/":
        return f"{BASE_PATH}/"
    return f"{BASE_PATH}{path}"


def request_origin(handler: SimpleHTTPRequestHandler) -> str:
    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL
    scheme = str(handler.headers.get("X-Forwarded-Proto") or "http").split(",", 1)[0].strip().lower()
    if scheme not in {"http", "https"}:
        scheme = "http"
    host = re.sub(r"[\r\n\s]+", "", str(handler.headers.get("Host") or f"{HOST}:{PORT}"))
    return f"{scheme}://{host}"


def webhook_url(handler: SimpleHTTPRequestHandler) -> str:
    url = f"{request_origin(handler)}{with_base_path('/api/sms-webhook')}"
    return url if WEBHOOK_SIGNING_KEY else f"{url}?token={WEBHOOK_TOKEN}"


def card_from_body(body: dict[str, Any]) -> dict[str, Any]:
    token = str(body.get("card") or "").strip() or generate_card_token()
    settings = load_admin_settings()
    expires_at = body.get("expiresAt") or default_card_expires_at(
        coerce_int(settings.get("defaultCardExpireMinutes"), DEFAULT_CARD_EXPIRE_MINUTES)
    )
    receive_limit = body.get("receiveLimit")
    if receive_limit in {None, ""}:
        receive_limit = settings.get("defaultCardReceiveLimit", DEFAULT_CARD_RECEIVE_LIMIT)
    card = normalize_user_card(
        {
            "card": token,
            "phoneId": body.get("phoneId", ""),
            "countryCode": body.get("countryCode", USER_COUNTRY_CODE),
            "phoneNumber": body.get("phoneNumber", ""),
            "expiresAt": expires_at,
            "receiveLimit": receive_limit,
            "usedCount": body.get("usedCount", 0),
            "waitSeconds": body.get("waitSeconds", USER_WAIT_SECONDS),
            "serviceName": body.get("serviceName", USER_SERVICE_NAME),
            "keywords": body.get("keywords", body.get("keywordsText", "")),
            "enabled": body.get("enabled", True),
        }
    )
    if not card:
        raise ValueError("卡密不能为空")
    assignment_mode = str(body.get("assignmentMode", "manual")).strip().lower()
    if assignment_mode == "pool":
        card = apply_phone_to_card(card, choose_phone_from_pool(load_admin_cards()))
    elif assignment_mode == "selected":
        phone = find_admin_phone(str(body.get("phoneId", "")))
        if not phone:
            raise ValueError("请选择号池手机号")
        card = apply_phone_to_card(card, phone)
    validate_card_input(card)
    return card


class SmsDashboardHandler(SimpleHTTPRequestHandler):
    server_version = "SmsDashboard/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        message = format % args
        message = re.sub(r"([?&](?:card|token)=)[^&\s]+", r"\1[redacted]", message)
        print(f"{self.address_string()} - {message}")

    def require_auth(self) -> bool:
        if auth_ok(self):
            return True
        client = self.client_address[0] if self.client_address else "unknown"
        if not rate_limit_ok("admin-auth", client, 20, 300):
            json_response(self, HTTPStatus.TOO_MANY_REQUESTS, {"ok": False, "error": "尝试次数过多"})
            return False
        unauthorized(self)
        return False

    def serve_static_file(self, local_path: Path, content_type: str) -> None:
        if not local_path.exists():
            text_response(self, HTTPStatus.NOT_FOUND, "Not found")
            return
        data = local_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        add_security_headers(self)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        path, query = safe_query(self.path)

        if path == "/health":
            health = health_status()
            json_response(self, HTTPStatus.OK if health["ok"] else HTTPStatus.SERVICE_UNAVAILABLE, health)
            return

        if path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            add_security_headers(self)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if path == "/logout":
            unauthorized(self)
            return

        if path == "/api/sms-webhook":
            if not ALLOW_WEBHOOK_GET:
                json_response(self, HTTPStatus.METHOD_NOT_ALLOWED, {"ok": False, "error": "GET webhook 未启用"})
                return
            client = self.client_address[0] if self.client_address else "unknown"
            if not rate_limit_ok("webhook", client, 120, 60):
                json_response(self, HTTPStatus.TOO_MANY_REQUESTS, {"ok": False, "error": "请求过于频繁"})
                return
            supplied_token = query.get("token", [""])[0]
            if not hmac.compare_digest(supplied_token, WEBHOOK_TOKEN):
                json_response(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "bad token"})
                return
            raw = {key: values[-1] if values else "" for key, values in query.items() if key != "token"}
            items, ignored = filter_webhook_messages([normalize_message(raw, "smsforwarder")])
            result = upsert_messages(items)
            json_response(self, HTTPStatus.OK, {"ok": True, "ignored": ignored, **result})
            return

        if path in {"/user", "/user/"}:
            self.serve_static_file(STATIC_DIR / "user.html", "text/html; charset=utf-8")
            return
        if path == "/static/user.css":
            self.serve_static_file(STATIC_DIR / "user.css", "text/css; charset=utf-8")
            return
        if path == "/static/user.js":
            self.serve_static_file(STATIC_DIR / "user.js", "text/javascript; charset=utf-8")
            return
        if path == "/api/user-card":
            client = self.client_address[0] if self.client_address else "unknown"
            if not rate_limit_ok("user-card", client, 120, 60):
                json_response(self, HTTPStatus.TOO_MANY_REQUESTS, {"ok": False, "error": "请求过于频繁"})
                return
            supplied_card = query.get("card", [""])[0].strip()
            card = find_user_card(supplied_card)
            if not load_admin_cards():
                json_response(
                    self,
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"ok": False, "error": "客户卡密未配置"},
                )
                return
            if not supplied_card or not card:
                json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "卡密无效"})
                return
            json_response(self, HTTPStatus.OK, user_card_payload(card))
            return

        if not self.require_auth():
            return

        if path == "/":
            self.serve_static_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return
        if path == "/register":
            self.serve_static_file(STATIC_DIR / "register.html", "text/html; charset=utf-8")
            return
        if path == "/static/style.css":
            self.serve_static_file(STATIC_DIR / "style.css", "text/css; charset=utf-8")
            return
        if path == "/static/app.js":
            self.serve_static_file(STATIC_DIR / "app.js", "text/javascript; charset=utf-8")
            return
        if path == "/api/config":
            json_response(self, HTTPStatus.OK, format_public_config())
            return
        if path == "/api/settings":
            json_response(self, HTTPStatus.OK, {"ok": True, "settings": load_admin_settings()})
            return
        if path == "/api/dashboard":
            json_response(self, HTTPStatus.OK, {"ok": True, **dashboard_payload()})
            return
        if path == "/api/orders":
            orders = [admin_order_payload(order) for order in load_xgj_orders(limit=500)]
            json_response(self, HTTPStatus.OK, {"ok": True, "orders": orders, "config": format_public_config()})
            return
        if path == "/api/goods":
            json_response(
                self,
                HTTPStatus.OK,
                {"ok": True, "goods": admin_goods_payloads(), "config": format_public_config()},
            )
            return
        if path == "/api/stock":
            goods_no = query.get("goodsNo", [""])[0].strip()
            status = query.get("status", [""])[0].strip()
            items = load_stock_items(goods_no=goods_no, status=status, limit=500)
            json_response(
                self,
                HTTPStatus.OK,
                {"ok": True, "items": items, "goods": admin_goods_payloads()},
            )
            return
        if path == "/api/audit-logs":
            json_response(self, HTTPStatus.OK, {"ok": True, "logs": load_audit_logs(limit=300)})
            return
        if path == "/api/agents":
            json_response(self, HTTPStatus.OK, {"ok": True, "agents": load_agents()})
            return
        if path == "/api/cards/export":
            export_format = query.get("format", ["txt"])[0].strip().lower()
            scope = query.get("scope", ["available"])[0].strip().lower()
            if export_format not in {"txt", "csv"}:
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "导出格式不支持"})
                return
            if scope not in {"available", "enabled", "all"}:
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "导出范围不支持"})
                return
            filename, content, content_type = cards_export_text(
                exportable_cards(self, scope),
                export_format,
            )
            record_audit_log(
                "cards_exported",
                export_format,
                {"scope": scope, "filename": filename},
                self.client_address[0] if self.client_address else "",
            )
            download_response(self, filename, content, content_type, bom=export_format == "csv")
            return
        if path == "/api/cards":
            cards = [admin_card_payload(card, self) for card in load_admin_cards()]
            json_response(
                self,
                HTTPStatus.OK,
                {"cards": cards, "config": format_public_config()},
            )
            return
        if path == "/api/phones":
            json_response(
                self,
                HTTPStatus.OK,
                {"phones": admin_phone_payloads(), "config": format_public_config()},
            )
            return
        if path == "/api/register-info":
            url = webhook_url(self)
            json_response(
                self,
                HTTPStatus.OK,
                {
                    "webhookUrl": url,
                    "webhookBody": {
                        "id": "sms-dashboard",
                        "url": url,
                        "event": "sms:received",
                    },
                    "phoneApiDefaults": [
                        "http://127.0.0.1:8080",
                        "http://localhost:8080",
                    ],
                },
            )
            return
        if path == "/api/messages":
            if "refresh" in query:
                poll_once(force=True)
            else:
                poll_once(force=False)
            json_response(
                self,
                HTTPStatus.OK,
                {"messages": load_messages(), "config": format_public_config()},
            )
            return

        text_response(self, HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        path, query = safe_query(self.path)
        xgj_path = xgj_route_path(path)

        if xgj_path.startswith("/goofish/"):
            handle_xgj_request(self, xgj_path, query)
            return

        if path == "/api/sms-webhook":
            client = self.client_address[0] if self.client_address else "unknown"
            if not rate_limit_ok("webhook", client, 120, 60):
                json_response(self, HTTPStatus.TOO_MANY_REQUESTS, {"ok": False, "error": "请求过于频繁"})
                return
            supplied_token = self.headers.get("X-Webhook-Token") or query.get("token", [""])[0]
            if not WEBHOOK_SIGNING_KEY and not hmac.compare_digest(supplied_token, WEBHOOK_TOKEN):
                json_response(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "bad token"})
                return
            try:
                raw_body = read_request_body(self)
                if not verify_webhook_signature(self.headers, raw_body):
                    json_response(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "bad signature"})
                    return
                body = parse_webhook_body(raw_body, self.headers.get("Content-Type", ""))
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "bad body"})
                return
            if isinstance(body, list):
                items = [normalize_message(item, "webhook") for item in body if isinstance(item, dict)]
            elif isinstance(body, dict):
                source = "smsforwarder" if "from" in body and ("content" in body or "msg" in body) else "webhook"
                items = [normalize_message(body, source)]
            else:
                items = []
            items, ignored = filter_webhook_messages(items)
            result = upsert_messages(items)
            json_response(self, HTTPStatus.OK, {"ok": True, "ignored": ignored, **result})
            return

        if not self.require_auth():
            return

        if path == "/api/test-message":
            demo = {
                "id": stable_id("demo", time.time()),
                "source": "demo",
                "sender": "106000",
                "recipient": "local",
                "message": "您的验证码是 673463，5 分钟内有效。",
                "receivedAt": utc_now_iso(),
                "createdAt": utc_now_iso(),
                "raw": {"demo": True},
            }
            result = upsert_messages([demo])
            record_audit_log(
                "test_message_created",
                str(demo.get("id", "")),
                {"sender": demo.get("sender"), "recipient": demo.get("recipient")},
                self.client_address[0] if self.client_address else "",
            )
            json_response(self, HTTPStatus.OK, {"ok": True, "message": demo, **result})
            return

        if path == "/api/settings":
            try:
                body = read_json_body(self)
                if not isinstance(body, dict):
                    raise ValueError("请求内容不正确")
                settings = save_admin_settings(body)
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
                return
            record_audit_log(
                "settings_updated",
                "card_defaults",
                settings,
                self.client_address[0] if self.client_address else "",
            )
            json_response(self, HTTPStatus.OK, {"ok": True, "settings": settings})
            return

        if path == "/api/agents":
            try:
                body = read_json_body(self)
                if not isinstance(body, dict):
                    raise ValueError("请求内容不正确")
                agent = save_agent(agent_from_body(body))
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
                return
            record_audit_log(
                "agent_saved",
                str(agent.get("id", "")),
                {"name": agent.get("name"), "ratePercent": agent.get("ratePercent")},
                self.client_address[0] if self.client_address else "",
            )
            json_response(self, HTTPStatus.OK, {"ok": True, "agent": agent})
            return

        if path == "/api/agents/toggle":
            try:
                body = read_json_body(self)
                agent_id = str(body.get("id", "")).strip() if isinstance(body, dict) else ""
                enabled = coerce_bool(body.get("enabled"), True) if isinstance(body, dict) else True
                if not agent_id or not set_agent_enabled(agent_id, enabled):
                    json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "代理不存在"})
                    return
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
                return
            record_audit_log(
                "agent_toggled",
                agent_id,
                {"enabled": enabled},
                self.client_address[0] if self.client_address else "",
            )
            json_response(self, HTTPStatus.OK, {"ok": True})
            return

        if path == "/api/agents/delete":
            try:
                body = read_json_body(self)
                agent_id = str(body.get("id", "")).strip() if isinstance(body, dict) else ""
                if not agent_id or not delete_agent(agent_id):
                    json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "代理不存在"})
                    return
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
                return
            record_audit_log(
                "agent_deleted",
                agent_id,
                {},
                self.client_address[0] if self.client_address else "",
            )
            json_response(self, HTTPStatus.OK, {"ok": True})
            return

        if path == "/api/goods":
            try:
                body = read_json_body(self)
                if not isinstance(body, dict):
                    raise ValueError("请求内容不正确")
                product = save_goods_product(goods_from_body(body))
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
                return
            record_audit_log(
                "goods_saved",
                str(product.get("goodsNo", "")),
                {"goodsName": product.get("goodsName"), "priceCents": product.get("priceCents")},
                self.client_address[0] if self.client_address else "",
            )
            json_response(self, HTTPStatus.OK, {"ok": True, "goods": admin_goods_payload(product)})
            return

        if path == "/api/goods/toggle":
            try:
                body = read_json_body(self)
                goods_no = str(body.get("goodsNo", "")).strip() if isinstance(body, dict) else ""
                enabled = coerce_bool(body.get("enabled"), True) if isinstance(body, dict) else True
                if not goods_no or not set_goods_enabled(goods_no, enabled):
                    json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "商品不存在或不可修改"})
                    return
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
                return
            record_audit_log(
                "goods_toggled",
                goods_no,
                {"enabled": enabled},
                self.client_address[0] if self.client_address else "",
            )
            json_response(self, HTTPStatus.OK, {"ok": True})
            return

        if path == "/api/goods/delete":
            try:
                body = read_json_body(self)
                goods_no = str(body.get("goodsNo", "")).strip() if isinstance(body, dict) else ""
                if not goods_no or not delete_goods_product(goods_no):
                    json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "商品不存在或不可删除"})
                    return
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
                return
            record_audit_log(
                "goods_deleted",
                goods_no,
                {},
                self.client_address[0] if self.client_address else "",
            )
            json_response(self, HTTPStatus.OK, {"ok": True})
            return

        if path == "/api/stock/import":
            try:
                body = read_json_body(self)
                if not isinstance(body, dict):
                    raise ValueError("请求内容不正确")
                goods_no = str(body.get("goodsNo", "")).strip()
                items = import_stock_items(goods_no, str(body.get("text", "")), str(body.get("note", "")))
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
                return
            record_audit_log(
                "stock_imported",
                goods_no,
                {"count": len(items)},
                self.client_address[0] if self.client_address else "",
            )
            json_response(self, HTTPStatus.OK, {"ok": True, "count": len(items)})
            return

        if path == "/api/stock/toggle":
            try:
                body = read_json_body(self)
                stock_id = str(body.get("id", "")).strip() if isinstance(body, dict) else ""
                enabled = coerce_bool(body.get("enabled"), True) if isinstance(body, dict) else True
                status = STOCK_AVAILABLE if enabled else STOCK_DISABLED
                if not stock_id or not set_stock_item_status(stock_id, status):
                    json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "库存不存在或已售出"})
                    return
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
                return
            record_audit_log(
                "stock_toggled",
                stock_id,
                {"enabled": enabled},
                self.client_address[0] if self.client_address else "",
            )
            json_response(self, HTTPStatus.OK, {"ok": True})
            return

        if path == "/api/stock/delete":
            try:
                body = read_json_body(self)
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "请求内容不正确"})
                return
            stock_id = str(body.get("id", "")).strip() if isinstance(body, dict) else ""
            if not stock_id or not delete_stock_item(stock_id):
                json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "库存不存在或已售出"})
                return
            record_audit_log(
                "stock_deleted",
                stock_id,
                {},
                self.client_address[0] if self.client_address else "",
            )
            json_response(self, HTTPStatus.OK, {"ok": True})
            return

        if path == "/api/orders/reissue":
            try:
                body = read_json_body(self)
                order_no = str(body.get("orderNo", body.get("order_no", ""))).strip() if isinstance(body, dict) else ""
                if not order_no:
                    raise ValueError("订单号不能为空")
                order = reissue_xgj_stock_order(order_no, self)
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
                return
            json_response(self, HTTPStatus.OK, {"ok": True, "order": order})
            return

        if path == "/api/cards":
            try:
                body = read_json_body(self)
                if not isinstance(body, dict):
                    raise ValueError("请求内容不正确")
                card = save_admin_card(card_from_body(body))
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
                return
            record_audit_log(
                "card_saved",
                str(card.get("card", "")),
                {"phoneNumber": card.get("phoneNumber"), "receiveLimit": card.get("receiveLimit")},
                self.client_address[0] if self.client_address else "",
            )
            json_response(self, HTTPStatus.OK, {"ok": True, "card": admin_card_payload(card, self)})
            return

        if path == "/api/cards/batch":
            try:
                body = read_json_body(self)
                if not isinstance(body, dict):
                    raise ValueError("请求内容不正确")
                cards = create_admin_cards(body)
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError, RuntimeError) as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
                return
            record_audit_log(
                "cards_batch_created",
                str(len(cards)),
                {
                    "count": len(cards),
                    "assignmentMode": str(body.get("assignmentMode", "")),
                    "receiveLimit": body.get("receiveLimit"),
                },
                self.client_address[0] if self.client_address else "",
            )
            json_response(
                self,
                HTTPStatus.OK,
                {
                    "ok": True,
                    "count": len(cards),
                    "cards": [admin_card_payload(card, self) for card in cards],
                },
            )
            return

        if path == "/api/cards/toggle":
            try:
                body = read_json_body(self)
                token = str(body.get("card", "")).strip() if isinstance(body, dict) else ""
                enabled = coerce_bool(body.get("enabled"), True) if isinstance(body, dict) else True
                if not token or not set_admin_card_enabled(token, enabled):
                    json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "卡密不存在"})
                    return
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
                return
            if not token:
                json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "卡密不存在"})
                return
            record_audit_log(
                "card_toggled",
                token,
                {"enabled": enabled},
                self.client_address[0] if self.client_address else "",
            )
            json_response(self, HTTPStatus.OK, {"ok": True})
            return

        if path == "/api/cards/delete":
            try:
                body = read_json_body(self)
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "请求内容不正确"})
                return
            token = str(body.get("card", "")).strip() if isinstance(body, dict) else ""
            if not token or not delete_admin_card(token):
                json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "卡密不存在"})
                return
            record_audit_log(
                "card_deleted",
                token,
                {},
                self.client_address[0] if self.client_address else "",
            )
            json_response(self, HTTPStatus.OK, {"ok": True})
            return

        if path == "/api/phones":
            try:
                body = read_json_body(self)
                if not isinstance(body, dict):
                    raise ValueError("请求内容不正确")
                phone = save_admin_phone(phone_from_body(body))
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
                return
            record_audit_log(
                "phone_saved",
                str(phone.get("id", "")),
                {"phoneNumber": phone.get("phoneNumber"), "enabled": phone.get("enabled")},
                self.client_address[0] if self.client_address else "",
            )
            json_response(self, HTTPStatus.OK, {"ok": True, "phone": phone_payload(phone)})
            return

        if path == "/api/phones/toggle":
            try:
                body = read_json_body(self)
                phone_id = str(body.get("id", "")).strip() if isinstance(body, dict) else ""
                enabled = coerce_bool(body.get("enabled"), True) if isinstance(body, dict) else True
                if not phone_id or not set_admin_phone_enabled(phone_id, enabled):
                    json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "手机号不存在"})
                    return
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
                return
            record_audit_log(
                "phone_toggled",
                phone_id,
                {"enabled": enabled},
                self.client_address[0] if self.client_address else "",
            )
            json_response(self, HTTPStatus.OK, {"ok": True})
            return

        if path == "/api/phones/delete":
            try:
                body = read_json_body(self)
                phone_id = str(body.get("id", "")).strip() if isinstance(body, dict) else ""
                if not phone_id or not delete_admin_phone(phone_id):
                    json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "手机号不存在"})
                    return
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
                return
            record_audit_log(
                "phone_deleted",
                phone_id,
                {},
                self.client_address[0] if self.client_address else "",
            )
            json_response(self, HTTPStatus.OK, {"ok": True})
            return

        if path == "/api/poll":
            result = poll_once(force=True)
            json_response(self, HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_GATEWAY, result)
            return

        text_response(self, HTTPStatus.NOT_FOUND, "Not found")


def main() -> None:
    validate_runtime_security()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ensure_store()
    server = ThreadingHTTPServer((HOST, PORT), SmsDashboardHandler)
    print(f"SMS dashboard: http://{HOST}:{PORT}")
    print(f"Login: {DASHBOARD_USER} / {'*' * len(DASHBOARD_PASSWORD)}")
    if gateway_configured():
        print(f"Gateway pull: {SMS_GATEWAY_BASE_URL}/inbox every {POLL_SECONDS}s")
    else:
        print("Gateway pull: not configured")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
