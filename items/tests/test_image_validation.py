from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image
from ..validators import validate_image_size, validate_image_format


class ImageSizeValidationTests(SimpleTestCase):
    def test_rejects_image_larger_than_limit(self):
        file = SimpleUploadedFile(
            "oversized.jpg",
            b"x",
            content_type="image/jpeg",
        )
        file.size = 10 * 1024 * 1024 + 1

        with self.assertRaisesMessage(
            ValidationError,
            "Image must be 10 MiB or smaller.",
        ):
            validate_image_size(file)

    def test_accepts_image_exactly_at_limit(self):
        file = SimpleUploadedFile(
            "at-limit.jpg",
            b"x",
            content_type="image/jpeg",
        )
        file.size = 10 * 1024 * 1024

        validate_image_size(file)

class ImageFormatValidationTests(SimpleTestCase):
    def test_accepts_png_image(self):
        buffer = BytesIO()

        with Image.new("RGB", (10, 10), color="blue") as image:
            image.save(buffer, format="PNG")

        file = SimpleUploadedFile(
            "artwork.png",
            buffer.getvalue(),
            content_type="image/png",
        )

        validate_image_format(file)
