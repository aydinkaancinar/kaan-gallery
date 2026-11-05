from django.db import models
from django.utils.text import slugify
from .validators import validate_image_size, validate_image_format

class Item(models.Model):

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    class Category(models.TextChoices):
        SCULPTURE = "sculpture", "Sculpture"
        VASE = "vase", "Vase"
        KITCHENWARE = "kitchenware", "Kitchenware"
        PRINT = "print", "Print"
        LINOPRESS = "linopress", "Linopress"
        MISCELLANEOUS = "miscellaneous", "Miscellaneous"

    class Fields(models.TextChoices):
        NAME = "name", "Name"
        PRICE = "price", "Price"
        CATEGORY = "category", "Category"
        CREATED = "created", "Created"

    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.MISCELLANEOUS,
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

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:200] or "artwork"
            candidate = base
            number = 2

            while Item.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base}-{number}"
                number += 1
            self.slug = candidate

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
