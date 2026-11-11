from hashlib import sha256
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageCms, ImageDraw, ImageFont, ImageOps

from .validators import MAX_IMAGE_PIXELS


VARIANT_TYPES = {
    "card": "image/webp",
    "detail": "image/webp",
    "share": "image/jpeg",
}
SHARE_SIZE = (1200, 630)


def variant_path(source_name, variant, protected=False):
    source_key = sha256(source_name.encode()).hexdigest()
    extension = "jpg" if variant == "share" else "webp"
    version = "protected-v3" if protected else "v1"
    return f"artwork-variants/{version}/{source_key}/{variant}.{extension}"


def prepare_photo(source):
    if source.width * source.height > MAX_IMAGE_PIXELS:
        raise ValueError("Image exceeds the processing pixel limit.")

    photo = ImageOps.exif_transpose(source)
    alpha = photo.convert("RGBA").getchannel("A") if (
        "A" in photo.getbands() or "transparency" in photo.info
    ) else None
    profile = photo.info.get("icc_profile")
    if profile:
        try:
            photo = ImageCms.profileToProfile(
                photo.convert("RGB") if alpha is not None else photo,
                BytesIO(profile),
                ImageCms.createProfile("sRGB"),
                outputMode="RGB",
            )
        except (ImageCms.PyCMSError, OSError, ValueError):
            photo = photo.convert("RGB")
    else:
        photo = photo.convert("RGB")
    if alpha is not None:
        photo.putalpha(alpha)
    return photo


def watermark(photo):
    photo = photo.convert("RGBA")
    overlay = Image.new("RGBA", photo.size)
    draw = ImageDraw.Draw(overlay)
    text = "kaancinar.com"
    font = ImageFont.load_default(size=max(1, round(photo.width / 12)))
    text_width = draw.textlength(text, font=font)
    font = ImageFont.load_default(size=max(1, round(font.size * photo.width * 0.7 / text_width)))
    padding = max(1, round(min(photo.size) * 0.025))
    draw.text(
        (photo.width / 2, photo.height - padding),
        text,
        font=font,
        anchor="mb",
        fill=(30, 30, 30, 100),
        stroke_width=max(1, round(photo.width / 700)),
        stroke_fill=(255, 255, 255, 110),
    )
    return Image.alpha_composite(photo, overlay)


def render_variant(photo, variant, protected=False):
    output = BytesIO()
    if variant == "card":
        # Match the gallery card's crop while keeping small originals at native size.
        scale = min(photo.width / 4, photo.height / 5, 180)
        size = (max(1, int(scale * 4)), max(1, int(scale * 5)))
        card = ImageOps.fit(photo, size, Image.Resampling.LANCZOS)
        if protected:
            card = watermark(card)
        card.save(output, "WEBP", quality=81)
    elif variant == "detail":
        detail = photo.copy()
        edge = 1200 if protected else 1440
        detail.thumbnail((edge, edge), Image.Resampling.LANCZOS)
        if protected:
            detail = watermark(detail)
        detail.save(output, "WEBP", quality=84)
    else:
        preview = photo.copy()
        preview.thumbnail(SHARE_SIZE, Image.Resampling.LANCZOS)
        if protected:
            preview = watermark(preview)
        canvas = Image.new("RGB", SHARE_SIZE, "#f2efea")
        offset = tuple((outer - inner) // 2 for outer, inner in zip(SHARE_SIZE, preview.size))
        mask = preview.getchannel("A") if preview.mode == "RGBA" else None
        canvas.paste(preview, offset, mask)
        canvas.save(output, "JPEG", quality=85, optimize=True)
    return ContentFile(output.getvalue())


def generate_variants(image, protected=False):
    storage = image.storage
    paths = {variant: variant_path(image.name, variant, protected) for variant in VARIANT_TYPES}
    missing = {variant: path for variant, path in paths.items() if not storage.exists(path)}
    if missing:
        with storage.open(image.name, "rb") as source_file:
            with Image.open(source_file) as source:
                photo = prepare_photo(source)
                for variant, path in missing.items():
                    written = storage.save(path, render_variant(photo, variant, protected))
                    if written != path:
                        # A concurrent backfill may have stored the same variant first.
                        storage.delete(written)
                        if not storage.exists(path):
                            raise OSError("Storage changed the variant filename.")
    return paths
