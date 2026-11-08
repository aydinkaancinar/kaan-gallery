from django.urls import reverse
from rest_framework.test import APITestCase

from ..models import Item
from .helpers import create_item


class ArtworkDateBoundsTests(APITestCase):
    def test_empty_catalog_returns_null_bounds(self):
        response = self.client.get(reverse("artwork-date-bounds"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {"earliest": None, "latest": None},
        )

    def test_bounds_use_published_dates_across_all_pages(self):
        for year in range(2010, 2021):
            create_item(
                status=Item.Status.PUBLISHED,
                creation_year=year,
                creation_month=11 if year == 2010 else 2,
            )

        create_item(
            creation_year=1999,
            creation_month=1,
        )
        create_item(
            creation_year=2099,
            creation_month=12,
        )
        create_item(status=Item.Status.PUBLISHED)

        response = self.client.get(reverse("artwork-date-bounds"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {"earliest": "2010-11", "latest": "2020-02"},
        )

    def test_single_dated_artwork_has_equal_bounds(self):
        create_item(
            status=Item.Status.PUBLISHED,
            creation_year=2025,
            creation_month=3,
        )

        response = self.client.get(reverse("artwork-date-bounds"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {"earliest": "2025-03", "latest": "2025-03"},
        )
