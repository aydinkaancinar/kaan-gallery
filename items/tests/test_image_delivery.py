from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image
from ..serializers import ItemSerializer
from ..models import ArtworkImage, Item
from .helpers import create_item, login_with_verified_session


class ArtworkImageDeliveryTests(TestCase):
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
                    response.close()

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
                    response.close()


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
