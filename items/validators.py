from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError
import warnings

MAX_IMAGE_PIXELS = 25_000_000

def validate_image_size(file):
    maximum_size = 10 * 1024 * 1024

    if file.size > maximum_size:
        raise ValidationError("Image must be 10 MiB or smaller.")

def validate_image_format(file):
    original_position = file.tell()

    try:
        file.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(file) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValidationError(
                        "Supported image formats: JPEG, PNG, WebP."
                    )
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise ValidationError(
                        "Image must contain no more than 25 million pixels."
                    )
                image.verify()
    except (
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
    ) as error:
        raise ValidationError(
            "Image dimensions exceed safe processing limits."
        ) from error
    except (UnidentifiedImageError, OSError, SyntaxError) as error:
        raise ValidationError("Upload a valid image.") from error
    finally:
        file.seek(original_position)
