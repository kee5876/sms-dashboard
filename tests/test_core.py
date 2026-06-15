import hashlib
import hmac
import io
import threading
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import app


class CoreRulesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.audit_patch = patch.object(app, "record_audit_log")
        self.audit_patch.start()

    def tearDown(self) -> None:
        self.audit_patch.stop()

    def test_official_webhook_uses_event_id_and_keeps_sim_separate(self) -> None:
        message = app.normalize_message(
            {
                "id": "event-id",
                "event": "sms:received",
                "deviceId": "device-a",
                "payload": {
                    "messageId": "content-id",
                    "sender": "1069",
                    "recipient": None,
                    "simNumber": 1,
                    "message": "验证码 123456",
                },
            }
        )

        self.assertEqual(message["id"], "event-id")
        self.assertEqual(message["recipient"], "")
        self.assertEqual(message["deviceId"], "device-a")
        self.assertEqual(message["simNumber"], "1")

    def test_card_requires_expiry_and_positive_limit(self) -> None:
        base = {"enabled": True, "usedCount": 0}
        self.assertFalse(app.card_usage({**base, "receiveLimit": 0, "expiresAt": ""})["available"])
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        self.assertTrue(app.card_usage({**base, "receiveLimit": 1, "expiresAt": future})["available"])

    def test_manual_and_pool_cards_share_the_same_phone_lease(self) -> None:
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        selected = {
            "card": "SELECTED01",
            "phoneId": "phone-id",
            "phoneNumber": "13800138000",
            "expiresAt": future,
            "receiveLimit": 1,
            "usedCount": 0,
            "enabled": True,
        }
        manual = {**selected, "card": "MANUAL001", "phoneId": ""}

        self.assertEqual(app.card_phone_key(selected), app.card_phone_key(manual))
        with self.assertRaises(ValueError):
            app.assert_card_phone_available(manual, [selected])

    def test_exhausted_unexpired_card_still_holds_phone_lease(self) -> None:
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        exhausted = {
            "card": "USEDUP01",
            "phoneId": "phone-id",
            "phoneNumber": "13800138000",
            "expiresAt": future,
            "receiveLimit": 1,
            "usedCount": 1,
            "enabled": True,
        }
        candidate = {**exhausted, "card": "NEWCARD01", "usedCount": 0}

        self.assertFalse(app.card_usage(exhausted)["available"])
        self.assertTrue(app.card_holds_phone_lease(exhausted))
        with self.assertRaises(ValueError):
            app.assert_card_phone_available(candidate, [exhausted])

    def test_xgj_stock_excludes_exhausted_unexpired_phone_lease(self) -> None:
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        phone = {"id": "phone-id", "phoneNumber": "13800138000", "enabled": True}
        exhausted = {
            "card": "USEDUP01",
            "phoneId": "phone-id",
            "phoneNumber": "13800138000",
            "expiresAt": future,
            "receiveLimit": 1,
            "usedCount": 1,
            "enabled": True,
        }

        with patch.object(app, "load_admin_phones", return_value=[phone]), patch.object(
            app, "load_admin_cards", return_value=[exhausted]
        ):
            self.assertEqual(app.xgj_available_stock(), 0)

    def test_device_and_sim_route_when_recipient_is_missing(self) -> None:
        card = {"phoneId": "phone-id", "phoneNumber": "13800138000", "keywords": ["video"]}
        message = {
            "recipient": "",
            "deviceId": "device-a",
            "simNumber": "1",
            "message": "video code 123456",
        }
        phone = {"id": "phone-id", "deviceId": "device-a", "simNumber": "1"}
        with patch.object(app, "find_admin_phone", return_value=phone):
            self.assertTrue(app.message_matches_user_card(message, card))
            self.assertFalse(app.message_matches_user_card({**message, "simNumber": "2"}, card))

    def test_ambiguous_device_route_is_rejected(self) -> None:
        existing = {"id": "phone-a", "phoneNumber": "13800138000", "deviceId": "device-a", "simNumber": ""}
        candidate = {"id": "phone-b", "phoneNumber": "13900139000", "deviceId": "device-a", "simNumber": "1"}
        with patch.object(app, "load_admin_phones", return_value=[existing]):
            with self.assertRaises(ValueError):
                app.validate_phone_input(candidate)

    def test_admin_json_body_rejects_simple_cross_origin_content_type(self) -> None:
        handler = SimpleNamespace(
            headers={"Content-Type": "text/plain", "Content-Length": "2"},
            rfile=io.BytesIO(b"{}"),
        )
        with self.assertRaises(ValueError):
            app.read_json_body(handler)

    def test_received_time_is_normalized_to_utc(self) -> None:
        self.assertEqual(
            app.normalize_received_at("2030-01-01T08:00:00+08:00"),
            "2030-01-01T00:00:00.000000+00:00",
        )

    def test_webhook_signature_uses_raw_body_and_timestamp(self) -> None:
        body = b'{"event":"sms:received"}'
        timestamp = str(int(time.time()))
        signature = hmac.new(
            b"test-signing-key",
            body + timestamp.encode(),
            hashlib.sha256,
        ).hexdigest()
        with patch.object(app, "WEBHOOK_SIGNING_KEY", "test-signing-key"):
            self.assertTrue(
                app.verify_webhook_signature(
                    {"X-Signature": signature, "X-Timestamp": timestamp},
                    body,
                )
            )
            self.assertFalse(
                app.verify_webhook_signature(
                    {"X-Signature": signature, "X-Timestamp": timestamp},
                    body + b" ",
                )
            )

    def test_customer_message_does_not_expose_sms_body(self) -> None:
        public = app.format_user_message(
            {
                "id": "message-id",
                "sender": "1069",
                "message": "private text, code 654321",
                "receivedAt": "2030-01-01T00:00:00Z",
            }
        )
        self.assertEqual(set(public), {"id", "code", "receivedAt"})
        self.assertEqual(public["code"], "654321")

    def test_xgj_signature_matches_official_example(self) -> None:
        body = b'{"goods_type":1,"goods_no":"12344532"}'
        with patch.object(app, "XGJ_APP_ID", "677859093659717"), patch.object(
            app, "XGJ_APP_SECRET", "wK63PxlOBaY9NoqMksLeZySzGIW25ifA"
        ), patch.object(app, "XGJ_MCH_SECRET", "o9wl81dncmvby3ijpq7eur456zhgtaxs"):
            self.assertEqual(
                app.xgj_sign_raw_body(body, "1724414553", "1001"),
                "fda5954f48ab32b3b271c84450440ead",
            )

    def test_xgj_card_order_returns_user_link(self) -> None:
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        handler = SimpleNamespace(headers={"Host": "example.com"})
        body = {
            "order_no": "GJ10001",
            "goods_no": "sms-code-link",
            "buy_quantity": 1,
            "notify_url": "https://open.goofish.pro/callback",
            "biz_order_no": "XY10001",
        }

        def save_order(order: dict) -> dict:
            return order

        with patch.object(app, "PUBLIC_BASE_URL", "https://sms.example.com"), patch.object(
            app, "xgj_available_stock", return_value=1
        ), patch.object(app, "find_xgj_order", return_value=None), patch.object(
            app,
            "create_admin_cards",
            return_value=[
                {
                    "card": "CARDTOKEN1",
                    "phoneId": "phone-id",
                    "phoneNumber": "13800138000",
                    "expiresAt": future,
                    "receiveLimit": 1,
                    "usedCount": 0,
                    "waitSeconds": 60,
                    "serviceName": "短信验证码接码链接",
                    "keywords": ["验证码"],
                    "enabled": True,
                }
            ],
        ), patch.object(app, "save_xgj_order", side_effect=save_order):
            response = app.create_xgj_card_order(body, handler)

        self.assertEqual(response["code"], 0)
        self.assertEqual(response["data"]["order_no"], "GJ10001")
        self.assertNotIn("card_no", response["data"]["card_items"][0])
        self.assertEqual(
            response["data"]["card_items"][0]["card_pwd"],
            "https://sms.example.com/user?card=CARDTOKEN1",
        )

    def test_xgj_duplicate_order_does_not_issue_another_card(self) -> None:
        existing = {
            "orderNo": "GJ10001",
            "outOrderNo": "XGJORDER",
            "orderType": 2,
            "goodsNo": "sms-code-link",
            "goodsName": "短信验证码接码链接",
            "buyQuantity": 1,
            "orderStatus": 20,
            "orderAmount": 100,
            "orderTime": 1800000000,
            "endTime": 1800000000,
            "cardItems": [{"card_no": "CARDTOKEN1", "card_pwd": "https://sms.example.com/user?card=CARDTOKEN1"}],
        }
        handler = SimpleNamespace(headers={"Host": "example.com"})
        with patch.object(app, "find_xgj_order", return_value=existing), patch.object(
            app, "create_admin_cards"
        ) as create_cards:
            response = app.create_xgj_card_order(
                {"order_no": "GJ10001", "goods_no": "sms-code-link", "buy_quantity": 1},
                handler,
            )

        create_cards.assert_not_called()
        self.assertEqual(response["code"], 0)
        self.assertEqual(response["data"]["out_order_no"], "XGJORDER")
        self.assertEqual(
            response["data"]["card_items"],
            [{"card_pwd": "https://sms.example.com/user?card=CARDTOKEN1"}],
        )

    def test_xgj_stock_order_consumes_inventory(self) -> None:
        handler = SimpleNamespace(headers={"Host": "example.com"}, client_address=("127.0.0.1", 12345))
        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            app, "GOODS_FILE", Path(tmp_dir) / "goods.json"
        ), patch.object(app, "STOCK_FILE", Path(tmp_dir) / "stock_items.json"), patch.object(
            app, "XGJ_ORDERS_FILE", Path(tmp_dir) / "xgj_orders.json"
        ), patch.object(
            app, "AUDIT_FILE", Path(tmp_dir) / "audit_logs.json"
        ), patch.object(
            app, "mysql_ready", return_value=False
        ):
            app.save_goods_product(
                app.goods_from_body(
                    {
                        "goodsNo": "video-card",
                        "goodsName": "Video Card",
                        "priceCents": 250,
                        "enabled": True,
                    }
                )
            )
            imported = app.import_stock_items("video-card", "CARD-A\nCARD-B")
            self.assertEqual(len(imported), 2)

            response = app.create_xgj_card_order(
                {"order_no": "GJ20001", "goods_no": "video-card", "buy_quantity": 2},
                handler,
            )

            self.assertEqual(response["code"], 0)
            self.assertEqual(response["data"]["order_amount"], 500)
            self.assertEqual([item["card_pwd"] for item in response["data"]["card_items"]], ["CARD-A", "CARD-B"])
            self.assertEqual(app.count_stock_items("video-card", app.STOCK_AVAILABLE), 0)
            self.assertEqual(app.count_stock_items("video-card", app.STOCK_SOLD), 2)

    def test_reissue_stock_order_uses_new_inventory(self) -> None:
        handler = SimpleNamespace(headers={"Host": "example.com"}, client_address=("127.0.0.1", 12345))
        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            app, "GOODS_FILE", Path(tmp_dir) / "goods.json"
        ), patch.object(app, "STOCK_FILE", Path(tmp_dir) / "stock_items.json"), patch.object(
            app, "XGJ_ORDERS_FILE", Path(tmp_dir) / "xgj_orders.json"
        ), patch.object(
            app, "AUDIT_FILE", Path(tmp_dir) / "audit_logs.json"
        ), patch.object(
            app, "mysql_ready", return_value=False
        ):
            app.save_goods_product(
                app.goods_from_body(
                    {
                        "goodsNo": "video-card",
                        "goodsName": "Video Card",
                        "priceCents": 100,
                        "enabled": True,
                    }
                )
            )
            app.import_stock_items("video-card", "OLD-CODE\nNEW-CODE")
            app.create_xgj_card_order(
                {"order_no": "GJ20002", "goods_no": "video-card", "buy_quantity": 1},
                handler,
            )

            order = app.reissue_xgj_stock_order("GJ20002", handler)

            self.assertEqual(order["cardItems"][0]["card_pwd"], "NEW-CODE")
            self.assertEqual(app.count_stock_items("video-card", app.STOCK_AVAILABLE), 0)
            self.assertEqual(app.count_stock_items("video-card", app.STOCK_SOLD), 2)

    def test_xgj_card_order_uses_admin_card_defaults(self) -> None:
        handler = SimpleNamespace(headers={"Host": "example.com"})
        body = {"order_no": "GJ10002", "goods_no": "sms-code-link", "buy_quantity": 1}
        captured = {}

        def create_cards(payload: dict) -> list[dict]:
            captured.update(payload)
            return [
                {
                    "card": "CARDTOKEN2",
                    "phoneId": "phone-id",
                    "phoneNumber": "13800138000",
                    "expiresAt": payload["expiresAt"],
                    "receiveLimit": payload["receiveLimit"],
                    "usedCount": 0,
                    "waitSeconds": 60,
                    "serviceName": "短信验证码接码链接",
                    "keywords": ["验证码"],
                    "enabled": True,
                }
            ]

        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            app, "SETTINGS_FILE", Path(tmp_dir) / "settings.json"
        ):
            app.save_admin_settings({"defaultCardExpireMinutes": 2880, "defaultCardReceiveLimit": 3})
            with patch.object(app, "xgj_available_stock", return_value=1), patch.object(
                app, "find_xgj_order", return_value=None
            ), patch.object(app, "create_admin_cards", side_effect=create_cards), patch.object(
                app, "save_xgj_order", side_effect=lambda order: order
            ):
                response = app.create_xgj_card_order(body, handler)

        expires_at = app.parse_datetime(captured["expiresAt"])
        self.assertEqual(response["code"], 0)
        self.assertEqual(captured["receiveLimit"], 3)
        self.assertIsNotNone(expires_at)
        delta = expires_at - datetime.now(timezone.utc)
        self.assertGreater(delta, timedelta(minutes=2879))
        self.assertLess(delta, timedelta(minutes=2881))

    def test_card_expire_minutes_are_limited_to_duration_options(self) -> None:
        self.assertEqual(
            app.normalize_admin_settings({"defaultCardExpireMinutes": 60})["defaultCardExpireMinutes"],
            1440,
        )
        self.assertEqual(
            app.normalize_admin_settings({"defaultCardExpireMinutes": 4320})["defaultCardExpireMinutes"],
            4320,
        )

    def test_xgj_trusted_ip_ranges_include_official_sources(self) -> None:
        self.assertTrue(app.xgj_trusted_client_ip("47.106.99.78"))
        self.assertTrue(app.xgj_trusted_client_ip("112.74.180.30"))
        self.assertFalse(app.xgj_trusted_client_ip("8.8.8.8"))

    def test_xgj_bad_signature_rejects_spoofed_trusted_forwarded_ip(self) -> None:
        body = b"{}"
        timestamp = str(int(time.time()))
        handler = SimpleNamespace(
            headers={
                "Content-Length": str(len(body)),
                "X-Real-IP": "47.106.99.78",
            },
            rfile=io.BytesIO(body),
            wfile=io.BytesIO(),
            client_address=("8.8.8.8", 12345),
            send_response=lambda status: None,
            send_header=lambda key, value: None,
            end_headers=lambda: None,
        )
        query = {"mch_id": ["sms-dashboard"], "timestamp": [timestamp], "sign": ["bad-signature"]}

        with patch.object(app, "XGJ_APP_ID", "677859093659717"), patch.object(
            app, "XGJ_APP_SECRET", "secret"
        ), patch.object(app, "XGJ_MCH_ID", "sms-dashboard"), patch.object(
            app, "XGJ_MCH_SECRET", "merchant-secret"
        ):
            app.handle_xgj_request(handler, "/goofish/user/info", query)

        payload = app.json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertEqual(payload["code"], 401)

    def test_public_bind_requires_public_base_url(self) -> None:
        with patch.object(app, "HOST", "0.0.0.0"), patch.object(
            app, "ALLOW_INSECURE_DEFAULTS", False
        ), patch.object(app, "DASHBOARD_PASSWORD", "strong-password"), patch.object(
            app, "WEBHOOK_TOKEN", "strong-token"
        ), patch.object(app, "WEBHOOK_SIGNING_KEY", "strong-signing-key"), patch.object(
            app, "USER_CARD_TOKEN", ""
        ), patch.object(app, "PUBLIC_BASE_URL", ""):
            with self.assertRaisesRegex(RuntimeError, "PUBLIC_BASE_URL"):
                app.validate_runtime_security()

    def test_duplicate_stock_order_does_not_consume_inventory_twice(self) -> None:
        handler = SimpleNamespace(headers={"Host": "example.com"}, client_address=("127.0.0.1", 12345))
        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            app, "GOODS_FILE", Path(tmp_dir) / "goods.json"
        ), patch.object(app, "STOCK_FILE", Path(tmp_dir) / "stock_items.json"), patch.object(
            app, "XGJ_ORDERS_FILE", Path(tmp_dir) / "xgj_orders.json"
        ), patch.object(
            app, "AUDIT_FILE", Path(tmp_dir) / "audit_logs.json"
        ), patch.object(
            app, "mysql_ready", return_value=False
        ):
            app.save_goods_product(
                app.goods_from_body(
                    {
                        "goodsNo": "video-card",
                        "goodsName": "Video Card",
                        "priceCents": 100,
                        "enabled": True,
                    }
                )
            )
            app.import_stock_items("video-card", "CARD-A\nCARD-B")

            results: list[dict] = []

            def place_order() -> None:
                results.append(
                    app.create_xgj_card_order(
                        {"order_no": "GJ-DUP", "goods_no": "video-card", "buy_quantity": 1},
                        handler,
                    )
                )

            threads = [threading.Thread(target=place_order) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            self.assertEqual([result["code"] for result in results], [0, 0])
            self.assertEqual(app.count_stock_items("video-card", app.STOCK_SOLD), 1)
            self.assertEqual(app.count_stock_items("video-card", app.STOCK_AVAILABLE), 1)
            self.assertEqual(
                {result["data"]["card_items"][0]["card_pwd"] for result in results},
                {"CARD-A"},
            )

    def test_dashboard_order_total_is_not_limited_to_recent_orders(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        orders = [
            {
                "orderNo": f"GJ{index:05d}",
                "outOrderNo": f"XY{index:05d}",
                "goodsNo": "sms-code-link",
                "goodsName": "SMS code link",
                "buyQuantity": 1,
                "orderStatus": 40 if index < 3 else 20,
                "orderAmount": 100,
                "orderTime": 0,
                "cardItems": [],
                "createdAt": now,
                "updatedAt": now,
            }
            for index in range(205)
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            orders_file = Path(tmp_dir) / "xgj_orders.json"
            orders_file.write_text(app.json.dumps(orders), encoding="utf-8")
            with patch.object(app, "XGJ_ORDERS_FILE", orders_file), patch.object(
                app, "mysql_ready", return_value=False
            ), patch.object(app, "load_messages", return_value=[]), patch.object(
                app, "load_admin_cards", return_value=[]
            ), patch.object(
                app, "admin_phone_payloads", return_value=[]
            ), patch.object(
                app, "load_audit_logs", return_value=[]
            ), patch.object(
                app, "xgj_available_stock", return_value=0
            ):
                payload = app.dashboard_payload()

        self.assertEqual(payload["summary"]["ordersTotal"], 205)
        self.assertEqual(payload["summary"]["ordersFailed"], 3)
        self.assertEqual(len(payload["recentOrders"]), 8)


if __name__ == "__main__":
    unittest.main()
