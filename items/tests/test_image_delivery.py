from io import BytesIO, StringIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image
from ..image_variants import VARIANT_TYPES, variant_path
from ..serializers import ItemSerializer
from ..models import ArtworkImage, Item
from .helpers import (
    FILESYSTEM_TEST_STORAGES, close_test_response, closing_response,
    create_item, login_with_verified_session,
)


class ArtworkImageDeliveryTests(TestCase):
    def setUp(self):
        media_root = TemporaryDirectory()
        self.addCleanup(media_root.cleanup)
        self.enterContext(self.settings(MEDIA_ROOT=media_root.name, STORAGES=FILESYSTEM_TEST_STORAGES))

    def upload(self, color="blue"):
        buffer = BytesIO()
        with Image.new("RGB", (1600, 1200), color=color) as photo:
            exif = photo.getexif()
            exif[274] = 6  # A portrait stored sideways by the camera.
            photo.save(buffer, format="JPEG", exif=exif)
        return SimpleUploadedFile("photo.jpg", buffer.getvalue(), content_type="image/jpeg")

    def test_print_original_is_staff_only_and_all_public_versions_have_watermarks(self):
        item = create_item(category="print", protect_images=True, status=Item.Status.PUBLISHED)
        upload = self.upload()
        original_bytes = upload.read()
        upload.seek(0)
        artwork_image = ArtworkImage.objects.create(item=item, image=upload, alt_text="A drawing")
        original_url = reverse("artwork-image", kwargs={"image_id": artwork_image.pk})
        data = ItemSerializer(item).data["cover_image"]
        self.assertEqual(data["image"], data["detail_image"])

        for method in (self.client.get, self.client.head):
            response = method(original_url)
            self.assertEqual(response.status_code, 404)
            self.assertIn("no-store", response["Cache-Control"])

        staff = get_user_model().objects.create_user(username="drawing-staff", is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(original_url).status_code, 404)
        self.client.logout()
        visitor = get_user_model().objects.create_user(username="drawing-visitor")
        self.client.force_login(visitor)
        self.assertEqual(self.client.get(original_url).status_code, 404)
        self.client.logout()

        dimensions = {"card": (720, 900), "detail": (900, 1200), "share": (1200, 630)}
        for variant in VARIANT_TYPES:
            with self.subTest(variant=variant):
                with closing_response(self.client.get(data[f"{variant}_image"])) as response:
                    self.assertEqual(response.status_code, 200)
                    with Image.open(BytesIO(b"".join(response.streaming_content))) as photo:
                        self.assertEqual(photo.size, dimensions[variant])
                        width, height = photo.size
                        center = photo.convert("RGB").crop((
                            int(width * .35), int(height * .46),
                            int(width * .65), int(height * .54),
                        ))
                        self.assertLess(center.getextrema()[0][1], 10)
                        bottom = photo.convert("RGB").crop((
                            int(width * .4), int(height * .9),
                            int(width * .6), int(height * .99),
                        ))
                        # The watermark is embedded near the bottom, leaving the center clear.
                        self.assertGreater(bottom.getextrema()[0][1], 30)

        login_with_verified_session(self.client, staff)
        with closing_response(self.client.get(original_url)) as response:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.streaming_content), original_bytes)
        staff.is_active = False
        staff.save(update_fields=["is_active"])
        self.assertEqual(self.client.get(original_url).status_code, 404)
        self.client.logout()

        item.status = Item.Status.DRAFT
        item.save(update_fields=["status"])
        for variant in VARIANT_TYPES:
            self.assertEqual(self.client.get(data[f"{variant}_image"]).status_code, 404)

    def test_enabling_protection_replaces_clean_variants_at_existing_public_urls(self):
        item = create_item(category="print", status=Item.Status.PUBLISHED)
        artwork_image = ArtworkImage.objects.create(item=item, image=self.upload(), alt_text="A drawing")
        old_data = ItemSerializer(item).data["cover_image"]
        clean_path = variant_path(artwork_image.image.name, "detail")
        storage = artwork_image.image.storage
        self.assertTrue(storage.exists(clean_path))
        self.assertNotEqual(old_data["image"], old_data["detail_image"])
        with closing_response(self.client.get(old_data["image"])) as response:
            self.assertEqual(response.status_code, 200)
        item.protect_images = True
        item.save(update_fields=["protect_images"])
        protected_path = variant_path(artwork_image.image.name, "detail", protected=True)
        self.assertTrue(storage.exists(protected_path))
        self.assertEqual(self.client.get(old_data["image"]).status_code, 404)
        with closing_response(self.client.get(old_data["detail_image"])) as response:
            self.assertEqual(response.status_code, 200)
            with storage.open(protected_path, "rb") as expected:
                self.assertEqual(b"".join(response.streaming_content), expected.read())
        updated = storage.get_modified_time(protected_path)
        call_command("generate_artwork_variants", stdout=StringIO())
        self.assertEqual(storage.get_modified_time(protected_path), updated)
        # Unchecking also works when the upload initially had only protected copies.
        storage.delete(clean_path)
        item.protect_images = False
        item.save(update_fields=["protect_images"])
        with closing_response(self.client.get(old_data["image"])) as response:
            self.assertEqual(response.status_code, 200)
        with closing_response(self.client.get(old_data["detail_image"])) as response:
            with storage.open(clean_path, "rb") as expected:
                self.assertEqual(b"".join(response.streaming_content), expected.read())

    def test_missing_source_does_not_prevent_unpublishing_a_protected_drawing(self):
        item = create_item(category="print", protect_images=True, status=Item.Status.PUBLISHED)
        artwork_image = ArtworkImage.objects.create(item=item, image=self.upload(), alt_text="A drawing")
        data = ItemSerializer(item).data["cover_image"]
        artwork_image.image.storage.delete(artwork_image.image.name)
        item.status = Item.Status.DRAFT
        item.save(update_fields=["status"])
        self.assertEqual(self.client.get(data["detail_image"]).status_code, 404)

    def test_uploaded_variants_keep_orientation_and_follow_publication(self):
        item = create_item(status=Item.Status.PUBLISHED)
        artwork_image = ArtworkImage.objects.create(item=item, image=self.upload(), alt_text="A pot")
        data = ItemSerializer(item).data["cover_image"]
        self.assertEqual(self.client.get(reverse("artwork-index")).json(), [{
            "slug": item.slug,
            "images": [data["detail_image"]],
        }])

        dimensions = {"card": (720, 900), "detail": (1080, 1440), "share": (1200, 630)}
        for variant, content_type in VARIANT_TYPES.items():
            with self.subTest(variant=variant):
                url = data[f"{variant}_image"]
                response = self.client.get(url)
                with closing_response(response):
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response["Content-Type"], content_type)
                    self.assertIn("no-store", response["Cache-Control"])
                    self.assertIn("private", response["Cache-Control"])
                    with Image.open(BytesIO(b"".join(response.streaming_content))) as photo:
                        self.assertEqual(photo.size, dimensions[variant])
                        self.assertIsNone(photo.getexif().get(274))

        item.status = Item.Status.DRAFT
        item.save(update_fields=["status"])
        self.assertEqual(self.client.get(reverse("artwork-index")).json(), [])
        for variant in VARIANT_TYPES:
            response = self.client.get(data[f"{variant}_image"])
            self.assertEqual(response.status_code, 404)
            self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(self.client.get(data["image"]).status_code, 404)

        staff = get_user_model().objects.create_user(username="variant-admin", is_staff=True)
        login_with_verified_session(self.client, staff)
        with closing_response(self.client.head(data["share_image"])) as response:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(self.client.get(reverse("artwork-index")).json(), [])
        self.assertEqual(artwork_image.image.name, "artworks/photo.jpg")

    def test_backfill_existing_image_and_generate_variants_for_replacement(self):
        item = create_item(status=Item.Status.PUBLISHED)
        artwork_image = ArtworkImage(item=item, alt_text="A pot")
        artwork_image.image.save("photo.jpg", self.upload(), save=False)
        artwork_image.save()
        storage = artwork_image.image.storage
        source = artwork_image.image.name
        detail = variant_path(source, "detail")
        url = ItemSerializer(item).data["cover_image"]["detail_image"]
        missing = self.client.get(url)
        self.assertEqual(missing.status_code, 404)
        self.assertIn("no-store", missing["Cache-Control"])

        call_command("generate_artwork_variants", stdout=StringIO())
        updated = storage.get_modified_time(detail)
        call_command("generate_artwork_variants", stdout=StringIO())
        self.assertEqual(storage.get_modified_time(detail), updated)

        artwork_image.image = self.upload(color="red")
        artwork_image.save(update_fields=["image"])
        self.assertNotEqual(artwork_image.image.name, source)
        with closing_response(self.client.get(url)) as response:
            with Image.open(BytesIO(b"".join(response.streaming_content))) as photo:
                red, _, blue = photo.getpixel((100, 100))
                self.assertGreater(red, blue)

    def test_unpublishing_revokes_public_image_access_but_keeps_staff_access(self):
        # Keep test files separate from real artwork, and remove them afterward.
        with TemporaryDirectory() as media_root:
            with self.settings(MEDIA_ROOT=media_root):
                buffer = BytesIO()
                with Image.new("RGB", (10, 10), color="blue") as image:
                    image.save(buffer, format="PNG")
                image_bytes = buffer.getvalue()

                item = create_item(status=Item.Status.PUBLISHED)
                artwork_image = ArtworkImage.objects.create(
                    item=item,
                    image=SimpleUploadedFile(
                        "test-artwork.png", image_bytes, content_type="image/png",
                    ),
                    alt_text="A blue test image",
                )
                url = reverse("artwork-image", kwargs={"image_id": artwork_image.pk})

                # Published image: anonymous visitors can read the actual bytes.
                response = self.client.get(url)
                try:
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response["Content-Type"], "image/png")
                    self.assertEqual(b"".join(response.streaming_content), image_bytes)
                    self.assertIn("no-store", response["Cache-Control"])
                    self.assertIn("private", response["Cache-Control"])
                finally:
                    close_test_response(response)

                # The same URL must stop working publicly after unpublishing.
                item.status = Item.Status.DRAFT
                item.save(update_fields=["status"])

                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)

                # Private preview remains available to MFA-verified staff.
                staff = get_user_model().objects.create_user(
                    username="image-admin", is_staff=True,
                )
                login_with_verified_session(self.client, staff)

                response = self.client.get(url)
                try:
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(b"".join(response.streaming_content), image_bytes)
                    self.assertIn("no-store", response["Cache-Control"])
                    self.assertIn("private", response["Cache-Control"])
                finally:
                    close_test_response(response)


class CoverImageTests(TestCase):
    def test_item_without_images_has_no_cover(self):
        item = create_item()

        data = ItemSerializer(item).data

        self.assertIsNone(data["cover_image"])

    def test_item_with_multiple_images_cover(self):
        item = create_item()

        ArtworkImage.objects.create(
            item=item,
            image="artworks/first.png",
            alt_text="First image",
            position=5,
        )

        second_image = ArtworkImage.objects.create(
            item=item,
            image="artworks/second.png",
            alt_text="Second, but cover image",
            position=1,
        )

        data = ItemSerializer(item).data

        self.assertEqual(data["cover_image"]["id"], second_image.id)

    def test_item_with_multiple_images_tie_breaker_cover(self):
        item = create_item()

        first_image = ArtworkImage.objects.create(
            item=item,
            image="artworks/first.png",
            alt_text="First image",
            position=1,
        )

        ArtworkImage.objects.create(
            item=item,
            image="artworks/second.png",
            alt_text="Second image",
            position=1,
        )

        data = ItemSerializer(item).data

        self.assertEqual(data["cover_image"]["id"], first_image.id)
