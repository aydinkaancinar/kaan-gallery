from django.core.management.base import BaseCommand, CommandError
from PIL import Image

from items.image_variants import VARIANT_TYPES, generate_variants
from items.models import ArtworkImage


class Command(BaseCommand):
    help = "Generate missing card, detail, and sharing images in artwork storage."

    def handle(self, *args, **options):
        count = failures = original_bytes = 0
        variant_bytes = dict.fromkeys(VARIANT_TYPES, 0)
        for artwork_image in ArtworkImage.objects.select_related("item").iterator():
            image = artwork_image.image
            try:
                paths = generate_variants(
                    image, protected=artwork_image.item.protect_images,
                )
                source_size = image.size
                sizes = {variant: image.storage.size(path) for variant, path in paths.items()}
            except (OSError, ValueError, Image.DecompressionBombError) as error:
                failures += 1
                self.stderr.write(f"Image {artwork_image.pk}: {error}")
                continue
            count += 1
            original_bytes += source_size
            for variant, size in sizes.items():
                variant_bytes[variant] += size

        self.stdout.write(f"{count} images. Originals: {original_bytes:,} bytes.")
        for variant, size in variant_bytes.items():
            self.stdout.write(f"{variant}: {size:,} bytes.")
        if failures:
            raise CommandError(f"{failures} artwork images could not be processed.")
