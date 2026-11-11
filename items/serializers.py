from rest_framework import serializers
from .models import Item, Artist, ArtworkImage, Category
from django.urls import reverse

class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = ["id", "name", "surname"]

class ArtworkImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    card_image = serializers.SerializerMethodField()
    detail_image = serializers.SerializerMethodField()
    share_image = serializers.SerializerMethodField()

    class Meta:
        model = ArtworkImage
        fields = ["id", "image", "card_image", "detail_image", "share_image", "alt_text", "position"]

    def get_image(self, obj):
        if obj.item.protect_images:
            return image_variant_url(obj.pk, "detail")
        return reverse("artwork-image", kwargs={"image_id": obj.pk})

    def get_card_image(self, obj):
        return image_variant_url(obj.pk, "card")

    def get_detail_image(self, obj):
        return image_variant_url(obj.pk, "detail")

    def get_share_image(self, obj):
        return image_variant_url(obj.pk, "share")


def image_variant_url(image_id, variant):
    return reverse("artwork-image-variant", kwargs={"image_id": image_id, "variant": variant})

class ItemSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(
        slug_field="slug", queryset=Category.objects.all(), required=False,
    )

    class Meta:
        model = Item
        fields = [
            "id",
            "name",
            "price",
            "quantity",
            "created",
            "category",
            "description",
            "artist",
            "tags",
            "status",
            "slug",
            "creation_year",
            "creation_month",
            "display_order",
            "protect_images",
            "artist_details",
            "images",
            "cover_image",
        ]

    artist_details = ArtistSerializer(
        source="artist",
        read_only=True,
    )

    images = ArtworkImageSerializer(
        many=True,
        read_only=True,
    )

    cover_image = serializers.SerializerMethodField()

    def get_cover_image(self, obj):
        images = list(obj.images.all())

        if not images:
            return None

        return ArtworkImageSerializer(
            images[0],
            context=self.context,
        ).data

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Price must be greater than zero."
            )
        return value

    def to_internal_value(self, data):
        data = data.copy()

        category = data.get("category")
        if isinstance(category, str):
            data["category"] = category.strip().lower()

        return super().to_internal_value(data)

    def validate(self, attrs):
        current_year = getattr(self.instance, "creation_year", None)
        current_month = getattr(self.instance, "creation_month", None)

        year = attrs.get("creation_year", current_year)
        month = attrs.get("creation_month", current_month)

        if (year is None) != (month is None):
            raise serializers.ValidationError(
                "Creation year and month must both be provided or both be empty."
            )

        return attrs


class PublicItemSerializer(ItemSerializer):
    class Meta(ItemSerializer.Meta):
        fields = [
            "id",
            "slug",
            "name",
            "description",
            "category",
            "tags",
            "creation_year",
            "creation_month",
            "artist_details",
            "images",
            "cover_image",
        ]
        read_only_fields = fields

class ItemFilterSerializer(serializers.Serializer):
    min_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
    )

    max_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
    )

    category = serializers.SlugRelatedField(
        slug_field="slug", queryset=Category.objects.all(),
        required=False,
    )

    name = serializers.CharField(
        required=False,
        max_length=200,
    )

    order_by = serializers.ChoiceField(
        choices=Item.Fields.choices,
        required=False,
    )

    search = serializers.CharField(
        required=False,
        max_length=200,
    )

    artist = serializers.CharField(
        required=False,
        max_length=200,
    )

    tag = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
    )

    creation_year = serializers.IntegerField(
        min_value=1999,
        max_value=2099,
        required=False,
    )

    creation_month = serializers.IntegerField(
        min_value=1,
        max_value=12,
        required=False,
    )

    created_from = serializers.CharField(
        required=False,
        max_length=7,
    )

    created_to = serializers.CharField(
        required=False,
        max_length=7,
    )

    def _validate_created_from_and_to(self, value):
        if "-" not in value:
            raise serializers.ValidationError(
                "year and month should be separated by -"
            )
        parts = value.split("-")
        if len(parts) != 2:
            raise serializers.ValidationError("Use YYYY-MM format.")
        year, month = parts
        if len(year) != 4:
            raise serializers.ValidationError(
                "year and month should have YYYY-MM format"
            )
        if len(month) != 2:
            raise serializers.ValidationError(
                "year and month should have YYYY-MM format"
            )

        if not (
            year.isascii()
            and year.isdigit()
            and month.isascii()
            and month.isdigit()
        ):
            raise serializers.ValidationError("Use YYYY-MM format.")

        if not 1999 <= int(year) <= 2099:
            raise serializers.ValidationError("Year must be between 1999 and 2099.")

        if not 1 <= int(month) <= 12:
            raise serializers.ValidationError("Month must be between 01 and 12.")
        return value

    def validate_created_from(self, value):
        self._validate_created_from_and_to(value)
        return value

    def validate_created_to(self, value):
        self._validate_created_from_and_to(value)
        return value

    def validate(self, attrs):
        minimum = attrs.get("min_price")
        maximum = attrs.get("max_price")

        if minimum is not None and maximum is not None:
            if minimum > maximum:
                raise serializers.ValidationError(
                    "min_price must not exceed max_price."
                )

        created_from = attrs.get("created_from")
        created_to = attrs.get("created_to")
        if created_from is not None and created_to is not None:
            if created_from > created_to:
                raise serializers.ValidationError(
                    "created_from must not exceed created_to."
                )
        return attrs
