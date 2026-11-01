from django.contrib import admin
from django.urls import path
from items.views import getData, operateItem, artistAPI, operateArtist

urlpatterns = [
    path("admin/", admin.site.urls),
    path("items/", getData),
    path("items/<int:item_id>/", operateItem, name="operate-item"),
    path("artists/", artistAPI),
    path("artists/<int:item_id>/", operateArtist, name="operate-artist"),
]
