from rest_framework import serializers
from .models import Item, Artist

class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = '__all__'
        
class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = '__all__'

    artist_details = ArtistSerializer(
        source="artist",
        read_only=True,
    )

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

    category = serializers.ChoiceField(
        choices=Item.Category.choices,
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

    def validate(self, attrs):
        minimum = attrs.get("min_price")
        maximum = attrs.get("max_price")

        if minimum is not None and maximum is not None:
            if minimum > maximum:
                raise serializers.ValidationError(
                    "min_price must not exceed max_price."
                )
        return attrs


