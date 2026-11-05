from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

def validate_image_size(file):
    maximum_size = 10 * 1024 * 1024

    if file.size > maximum_size:
        raise ValidationError("Image must be 10 MiB or smaller.")

def validate_image_format(file):
    original_position = file.tell()

    try:
        file.seek(0)

        with Image.open(file) as image:
            if image.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValidationError(
                    "Supported image formats: JPEG, PNG, WebP."
                )

            image.verify()

    except (UnidentifiedImageError, OSError, SyntaxError) as error:
        raise ValidationError("Upload a valid image.") from error

    finally:
        file.seek(original_position)
