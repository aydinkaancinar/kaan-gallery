"""Run the real gallery API with a disposable database and synthetic artwork."""
import os
from io import BytesIO
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"

import django
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connections
from PIL import Image


def seed_catalog():
    from items.models import ArtworkImage, Item

    artworks = [
        ("Browser test vase", "browser-vase", "vase", False, ["blue", "navy"]),
        ("Browser test bowl", "browser-bowl", "kitchenware", False, ["orange"]),
        ("Browser test drawing", "browser-drawing", "print", True, ["green"]),
    ]
    for position, (name, slug, category, protected, colors) in enumerate(artworks):
        item = Item.objects.create(
            name=name,
            slug=slug,
            category_id=category,
            description="Synthetic artwork for browser testing.",
            price="50.00",
            status=Item.Status.PUBLISHED,
            display_order=position,
            creation_year=2026,
            creation_month=position + 1,
            protect_images=protected,
        )
        for index, color in enumerate(colors, start=1):
            output = BytesIO()
            with Image.new("RGB", (1600, 1200), color) as image:
                image.save(output, "JPEG")
            ArtworkImage.objects.create(
                item=item,
                image=SimpleUploadedFile(
                    f"{slug}-{index}.jpg", output.getvalue(), content_type="image/jpeg",
                ),
                alt_text=f"{name}, view {index}",
                position=index,
            )


def main():
    with TemporaryDirectory(prefix="kaan-gallery-browser-") as directory:
        # Configure storage before Django initializes any database connections.
        settings.DATABASES = {
            "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(Path(directory) / "test.sqlite3")},
        }
        settings.MEDIA_ROOT = Path(directory) / "media"
        settings.STORAGES = {
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        }
        django.setup()
        try:
            call_command("migrate", verbosity=0)
            seed_catalog()
            call_command("runserver", "127.0.0.1:8114", use_reloader=False)
        finally:
            connections.close_all()


if __name__ == "__main__":
    main()
