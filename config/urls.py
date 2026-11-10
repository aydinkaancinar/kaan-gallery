from .health import health
from django.contrib import admin
from django.urls import include, path
from items.views import getData, operateItem, artistAPI, operateArtist, artwork_detail, artwork_image, artwork_index, artwork_date_bounds, artwork_categories
from two_factor.urls import urlpatterns as two_factor_urls
from two_factor.admin import AdminSiteOTPRequired

admin.site.__class__ = AdminSiteOTPRequired

urlpatterns = [
    path("healthz/", health, name="health"),
    path("", include(two_factor_urls)),
    path("admin/", admin.site.urls),
    path("items/", getData),
    path("items/categories/", artwork_categories, name="artwork-categories"),
    path("items/artwork-index/", artwork_index, name="artwork-index"),
    path("items/<int:item_id>/", operateItem, name="operate-item"),
    path("artists/", artistAPI),
    path("artists/<int:item_id>/", operateArtist, name="operate-artist"),
    path(
        "artworks/<slug:slug>/",
        artwork_detail,
        name="artwork-detail",
    ),
    path(
        "artwork-images/<int:image_id>/",
        artwork_image,
        name="artwork-image",
    ),
    path(
        "artwork-images/<int:image_id>/<str:variant>/",
        artwork_image,
        name="artwork-image-variant",
    ),
    path(
        "items/date-bounds/",
        artwork_date_bounds,
        name="artwork-date-bounds",
    ),
]
