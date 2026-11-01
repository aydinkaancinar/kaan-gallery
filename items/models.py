from django.db import models


class Item(models.Model):

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

class Artist(models.Model):

    name = models.CharField(max_length=200)
    surname = models.CharField(max_length=200)

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
