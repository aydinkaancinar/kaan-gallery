from contextlib import closing
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from PIL import Image

from ..models import ArtworkImage, Item
from ..storage_gateway import MAX_OBJECT_BYTES, NoStorageRedirects, QuotaGatewayStorage, StorageUnavailable
from .helpers import FILESYSTEM_TEST_STORAGES, create_item


class GatewayStorageTests(SimpleTestCase):
    def setUp(self):
        self.storage = QuotaGatewayStorage("https://gateway.example.test", "test-secret-" * 4)

    def response(self, data=b"image", headers=None):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = data
        response.headers = headers or {}
        return response

    def test_configuration_requires_an_https_origin_and_strong_secret(self):
        for url in ["http://gateway.test", "https://user:pass@gateway.test", "https://gateway.test/path"]:
            with self.subTest(url=url):
                with self.assertRaises(ImproperlyConfigured):
                    QuotaGatewayStorage(url, "x" * 32)
        with self.assertRaises(ImproperlyConfigured):
            QuotaGatewayStorage("https://gateway.test", "short")
        with self.assertRaisesMessage(ValueError, "no public URLs"):
            self.storage.url("artworks/private.png")

    def test_open_uses_authenticated_gateway_and_preserves_content(self):
        response = self.response()
        with patch("items.storage_gateway.build_opener") as opener:
            opener.return_value.open.return_value = response
            with closing(self.storage.open("artworks/a pot.png")) as file:
                self.assertEqual(file.read(), b"image")
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.method, "GET")
            self.assertEqual(request.get_header("Authorization"), f"Bearer {self.storage.token}")
            self.assertEqual(request.get_header("User-agent"), "KaanGallery-Storage/1.0")
            self.assertTrue(request.full_url.startswith("https://gateway.example.test/v1/objects/"))
            self.assertNotIn("a pot.png", request.full_url)
        response.read.assert_called_once_with(MAX_OBJECT_BYTES + 1)

    def test_metadata_uses_head_without_downloading_the_object(self):
        response = self.response(headers={
            "Content-Length": "123", "Last-Modified": "Mon, 09 Nov 2026 12:00:00 GMT",
        })
        with patch.object(self.storage, "_request", return_value=response) as request:
            self.assertTrue(self.storage.exists("artworks/test.png"))
            self.assertEqual(self.storage.size("artworks/test.png"), 123)
            self.assertEqual(self.storage.get_modified_time("artworks/test.png").year, 2026)
            self.assertTrue(all(call.args[0] == "HEAD" for call in request.call_args_list))
        response.read.assert_not_called()

    def test_gateway_failure_and_network_failure_never_fall_back_to_other_storage(self):
        failures = [
            HTTPError("https://gateway.test", 429, "Limited", {"Retry-After": "3600"}, None),
            HTTPError("https://gateway.test", 503, "Unavailable", {}, None),
            HTTPError("https://gateway.test", 403, "Forbidden", {}, None),
            URLError("unavailable"),
        ]
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                with patch("items.storage_gateway.build_opener") as opener:
                    opener.return_value.open.side_effect = failure
                    with self.assertRaises(StorageUnavailable):
                        self.storage.open("artworks/test.png")
                    self.assertEqual(opener.return_value.open.call_count, 1)
        self.assertIsNone(NoStorageRedirects().redirect_request(None, None, 302, "", {}, "https://other.test"))

    def test_missing_files_are_reported_as_missing_and_deletion_is_idempotent(self):
        with patch.object(self.storage, "_request", side_effect=FileNotFoundError):
            self.assertFalse(self.storage.exists("artworks/missing.png"))
            self.storage.delete("artworks/missing.png")

    def test_write_is_create_only_and_conflicts_get_a_new_name(self):
        response = self.response(b'{"key":"artworks/alternative.png","size":5}')
        with patch.object(self.storage, "_request", side_effect=[FileExistsError, response]) as request:
            with patch.object(self.storage, "exists", side_effect=[False, True, False]):
                name = self.storage.save("artworks/test.png", ContentFile(b"image"), max_length=30)
        self.assertTrue(name.startswith("artworks/test_"))
        self.assertLessEqual(len(name), 30)
        self.assertEqual([call.args[0] for call in request.call_args_list], ["PUT", "PUT"])

    def test_oversized_files_and_oversized_responses_are_rejected(self):
        with patch.object(self.storage, "_request") as request:
            with self.assertRaises(ValueError):
                self.storage._save("artworks/large.png", ContentFile(b"x" * (MAX_OBJECT_BYTES + 1)))
            request.assert_not_called()
        with patch.object(self.storage, "_request", return_value=self.response(b"x" * (MAX_OBJECT_BYTES + 1))):
            with self.assertRaises(StorageUnavailable):
                self.storage.open("artworks/large.png")


class GatewayDeliveryTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.enterContext(self.settings(MEDIA_ROOT=directory.name, STORAGES=FILESYSTEM_TEST_STORAGES))
        output = BytesIO()
        with Image.new("RGB", (32, 24), "blue") as image:
            image.save(output, "PNG")
        self.item = create_item(status=Item.Status.PUBLISHED)
        self.image = ArtworkImage.objects.create(
            item=self.item,
            image=SimpleUploadedFile("test.png", output.getvalue(), content_type="image/png"),
            alt_text="Test image",
        )
        self.url = reverse("artwork-image", kwargs={"image_id": self.image.pk})

    def test_head_checks_metadata_without_reading_image_bytes(self):
        with patch("django.core.files.storage.FileSystemStorage.open") as opened:
            response = self.client.head(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertGreater(int(response["Content-Length"]), 0)
        opened.assert_not_called()

    def test_storage_quota_failure_returns_a_noncacheable_temporary_response(self):
        with patch(
            "django.core.files.storage.FileSystemStorage.open",
            side_effect=StorageUnavailable(3600),
        ):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response["Retry-After"], "3600")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn(self.image.image.name.encode(), response.content)

    def test_unauthorized_request_is_rejected_before_touching_storage(self):
        self.item.status = Item.Status.DRAFT
        self.item.save(update_fields=["status"])
        with patch("django.core.files.storage.FileSystemStorage.open") as opened:
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)
        opened.assert_not_called()
