from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image
from ..validators import validate_image_size, validate_image_format
from unittest.mock import patch
import warnings

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

    def test_fake_jpg(self):

        file = SimpleUploadedFile(
            "fake.jpg",
            b"This is text, not an image.",
            content_type="image/jpeg",
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Upload a valid image.",
        ):
            validate_image_format(file)

    def test_rejects_image_exceeding_pixel_limit(self):
        file = SimpleUploadedFile(
            "large.jpg",
            b"placeholder",
            content_type="image/jpeg",
        )

        with patch("items.validators.Image.open") as open_image:
            image = open_image.return_value.__enter__.return_value
            image.format = "JPEG"
            image.width = 6000
            image.height = 5000

            with self.assertRaisesMessage(
                ValidationError,
                "Image must contain no more than 25 million pixels.",
            ):
                validate_image_format(file)

            image.verify.assert_not_called()

    def test_accepts_image_at_pixel_limit(self):
        file = SimpleUploadedFile(
            "large.jpg",
            b"placeholder",
            content_type="image/jpeg",
        )

        with patch("items.validators.Image.open") as open_image:
            image = open_image.return_value.__enter__.return_value
            image.format = "JPEG"
            image.width = 5000
            image.height = 5000

            validate_image_format(file)

            image.verify.assert_called_once()

    def test_rejects_decompression_bomb_warning(self):
        file = SimpleUploadedFile("large.png", b"placeholder")

        def warn_when_opened(*args, **kwargs):
            warnings.warn(
                "Simulated oversized image",
                Image.DecompressionBombWarning,
            )

        with patch(
            "items.validators.Image.open",
            side_effect=warn_when_opened,
        ):
            with self.assertRaisesMessage(
                ValidationError,
                "Image dimensions exceed safe processing limits.",
            ):
                validate_image_format(file)

    def test_rejects_decompression_bomb_error(self):
        file = SimpleUploadedFile("large.png", b"placeholder")

        with patch(
            "items.validators.Image.open",
            side_effect=Image.DecompressionBombError(
                "Simulated oversized image"
            ),
        ):
            with self.assertRaisesMessage(
                ValidationError,
                "Image dimensions exceed safe processing limits.",
            ):
                validate_image_format(file)
