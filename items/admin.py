from django.contrib import admin
from .models import Item, Artist, Tag, ArtworkImage
from django import forms
from django.db import models
from django.urls import reverse
from django.utils.html import format_html

class ArtworkImageInline(admin.StackedInline):
    model = ArtworkImage
    extra = 1
    fields = ["image", "image_link", "alt_text", "position"]
    readonly_fields = ["image_link"]

    # A plain upload widget avoids displaying the raw storage URL.
    formfield_overrides = {
        models.ImageField: {"widget": forms.FileInput},
    }

    @admin.display(description="Current image")
    def image_link(self, obj):
        if not obj.pk or not obj.image:
            return "No image uploaded."

        url = reverse("artwork-image", kwargs={"image_id": obj.pk})

        return format_html('<a href="{}">View image</a>', url)

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ["name", "id", "category", "artist", "price", "quantity", "status"]
    search_fields = ["name", "description", "artist__name", "tags__name"]
    list_filter = ["category", "status"]
    list_select_related = ["artist"]
    filter_horizontal = ["tags"]
    list_editable = ["status"]
    inlines = [ArtworkImageInline]
admin.site.register(Artist)
admin.site.register(Tag)
