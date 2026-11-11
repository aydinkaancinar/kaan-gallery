from django.db import models
from django.utils.text import slugify
from .validators import validate_image_size, validate_image_format
from django.core.validators import MaxValueValidator, MinValueValidator
from .image_variants import generate_variants

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["position", "name"]

    def __str__(self):
        return self.name


class Item(models.Model):

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    class Fields(models.TextChoices):
        NAME = "name", "Name"
        PRICE = "price", "Price"
        CATEGORY = "category", "Category"
        CREATED = "created", "Created"
        CREATION_DATE_ASCENDING = "creation_date", "Creation date: oldest first"
        CREATION_DATE_DESCENDING = "-creation_date", "Creation date: newest first"

    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    category = models.ForeignKey(
        "Category",
        to_field="slug",
        db_column="category",
        on_delete=models.PROTECT,
        default="miscellaneous",
        related_name="items",
    )
    description = models.CharField(max_length=200, default="")
    artist = models.ForeignKey(
        "Artist",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )
    tags = models.ManyToManyField(
        "Tag",
        blank=True,
        related_name="items",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    slug = models.SlugField(
        max_length=220,
        blank=True,
        unique=True,
    )
    creation_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1999), MaxValueValidator(2099)]
    )
    creation_month = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )

    display_order = models.PositiveIntegerField(
        "Gallery position",
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Lower numbers appear first. Leave blank to order by creation date.",
    )
    protect_images = models.BooleanField(
        default=False,
        help_text="Watermark public images and keep originals staff-only.",
    )

    class Meta:
        ordering = [
            models.F("display_order").asc(nulls_last=True),
            models.F("creation_year").desc(nulls_last=True),
            models.F("creation_month").desc(nulls_last=True),
            "id",
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:200] or "artwork"
            candidate = base
            number = 2

            while Item.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base}-{number}"
                number += 1
            self.slug = candidate

        fields = kwargs.get("update_fields")
        if not self._state.adding and (fields is None or "protect_images" in fields):
            previous = Item.objects.only("protect_images").get(pk=self.pk)
            if previous.protect_images != self.protect_images:
                for artwork_image in self.images.all():
                    generate_variants(artwork_image.image, protected=self.protect_images)
        super().save(*args, **kwargs)

class Artist(models.Model):

    name = models.CharField(max_length=200)
    surname = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.name} {self.surname}".strip()

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"{self.name}".strip()

class ArtworkImage(models.Model):
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="images",
    )
    alt_text = models.CharField(max_length=200)
    position = models.PositiveIntegerField(default=0)
    image = models.ImageField(
        upload_to="artworks/",
        validators=[validate_image_size, validate_image_format],
    )

    class Meta:
        ordering = ["position", "id"]

    def save(self, *args, **kwargs):
        fields = kwargs.get("update_fields")
        if self.image and (fields is None or "image" in fields):
            if not self.image._committed:
                # Use the actual storage key, including any replacement suffix.
                self.image.save(self.image.name, self.image.file, save=False)
                self._pending_variant_source = self.image.name
            if getattr(self, "_pending_variant_source", None) == self.image.name:
                generate_variants(self.image, protected=self.item.protect_images)
                self._pending_variant_source = None
        super().save(*args, **kwargs)
