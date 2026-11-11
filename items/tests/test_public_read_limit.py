from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, RequestFactory, TestCase, override_settings

from items.public_read_limit import client_ip
from .helpers import login_with_verified_session


@override_settings(PUBLIC_READ_LIMIT_ENABLED=True, PUBLIC_READ_LIMIT_TRUST_XFF=True)
class PublicReadLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.clock = patch("items.public_read_limit.time.time", return_value=1200)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.addCleanup(cache.clear)

    def test_image_limit_returns_429_before_missing_image_lookup(self):
        with patch.dict("items.public_read_limit.LIMITS", {"image": (2, 10)}):
            client = Client(REMOTE_ADDR="192.0.2.1")
            self.assertEqual(client.get("/artwork-images/999/card/").status_code, 404)
            self.assertEqual(client.head("/artwork-images/999/card/").status_code, 404)
            response = client.get("/artwork-images/999/card/")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "60")
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_global_limit_counts_different_clients(self):
        with patch.dict("items.public_read_limit.LIMITS", {"catalog": (10, 2)}):
            for address in ("192.0.2.1", "192.0.2.2"):
                self.assertEqual(Client(REMOTE_ADDR=address).get("/items/categories/").status_code, 200)
            self.assertEqual(Client(REMOTE_ADDR="192.0.2.3").get("/items/categories/").status_code, 429)

    def test_staff_health_and_writes_do_not_use_public_read_budget(self):
        staff = get_user_model().objects.create_user(username="limited-admin", is_staff=True)
        client = Client()
        login_with_verified_session(client, staff)
        with patch.dict("items.public_read_limit.LIMITS", {"catalog": (1, 1)}):
            self.assertEqual(client.get("/items/categories/").status_code, 200)
            self.assertEqual(client.get("/items/categories/").status_code, 200)
            self.assertEqual(client.get("/healthz/").status_code, 200)

    def test_uses_render_client_address_and_rejects_invalid_forwarded_address(self):
        request = RequestFactory().get(
            "/items/", HTTP_X_FORWARDED_FOR="198.51.100.3, 203.0.113.4",
            REMOTE_ADDR="192.0.2.1",
        )
        self.assertEqual(client_ip(request), "198.51.100.3")
        request.META["HTTP_X_FORWARDED_FOR"] = "not-an-address, 203.0.113.4"
        self.assertEqual(client_ip(request), "192.0.2.1")
        with override_settings(PUBLIC_READ_LIMIT_TRUST_XFF=False):
            self.assertEqual(client_ip(request), "192.0.2.1")
