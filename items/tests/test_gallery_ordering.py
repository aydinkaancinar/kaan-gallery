from django.contrib import admin
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from ..models import Item
from ..serializers import ItemSerializer
from .helpers import create_item


class GalleryPositionValidationTests(SimpleTestCase):
    def test_position_is_optional_and_can_be_cleared(self):
        for value in [None, 0, 10]:
            with self.subTest(value=value):
                serializer = ItemSerializer(data={
                    "name": "Vase", "price": "25.00", "display_order": value,
                })
                self.assertTrue(serializer.is_valid(), serializer.errors)
                self.assertEqual(serializer.validated_data["display_order"], value)

    def test_negative_position_is_rejected(self):
        serializer = ItemSerializer(data={
            "name": "Vase", "price": "25.00", "display_order": -1,
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("display_order", serializer.errors)

    def test_position_can_be_edited_in_admin_list(self):
        model_admin = admin.site._registry[Item]
        self.assertIn("display_order", model_admin.list_display)
        self.assertIn("display_order", model_admin.list_editable)


class GalleryOrderingTests(APITestCase):
    def artwork(self, **values):
        return create_item(status=Item.Status.PUBLISHED, **values)

    def all_ids(self, **params):
        response = self.client.get("/items/", params)
        self.assertEqual(response.status_code, 200)
        count = response.data["count"]
        ids = [row["id"] for row in response.data["results"]]
        while response.data["next"]:
            response = self.client.get(response.data["next"])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["count"], count)
            ids.extend(row["id"] for row in response.data["results"])
        self.assertEqual(len(ids), count)
        self.assertEqual(len(set(ids)), count)
        return ids

    def test_without_positions_newest_physical_date_first_and_unknown_last(self):
        unknown = self.artwork(name="Unknown")
        old = self.artwork(name="Old", creation_year=2024, creation_month=12)
        later_month = self.artwork(name="May", creation_year=2025, creation_month=5)
        earlier_month = self.artwork(name="March", creation_year=2025, creation_month=3)

        self.assertEqual(self.all_ids(), [later_month.pk, earlier_month.pk, old.pk, unknown.pk])

    def test_position_overrides_date_zero_counts_and_gaps_are_allowed(self):
        newest = self.artwork(name="Newest", creation_year=2026, creation_month=5)
        positioned = self.artwork(name="Older but curated", display_order=20, creation_year=2024, creation_month=1)
        zero = self.artwork(name="First priority", display_order=0)

        self.assertEqual(self.all_ids(), [zero.pk, positioned.pk, newest.pk])

    def test_equal_positions_use_newest_date_then_id_and_unknown_last(self):
        unknown = self.artwork(name="Unknown", display_order=2)
        older = self.artwork(name="Older", display_order=2, creation_year=2024, creation_month=12)
        first = self.artwork(name="Zebra", display_order=2, creation_year=2025, creation_month=3)
        second = self.artwork(name="Apple", display_order=2, creation_year=2025, creation_month=3)

        self.assertEqual(self.all_ids(), [first.pk, second.pk, older.pk, unknown.pk])

    def test_clearing_position_restores_date_order(self):
        older = self.artwork(display_order=1, creation_year=2024, creation_month=1)
        newer = self.artwork(creation_year=2025, creation_month=1)
        self.assertEqual(self.all_ids(), [older.pk, newer.pk])

        older.display_order = None
        older.save(update_fields=["display_order"])

        self.assertEqual(self.all_ids(), [newer.pk, older.pk])

    def test_filters_and_pagination_preserve_curated_order_and_hide_drafts(self):
        ordinary = [
            self.artwork(name=f"Blue vase {month}", category="vase", creation_year=2025, creation_month=month)
            for month in range(1, 7)
        ]
        featured = self.artwork(name="Blue featured vase", category="vase", display_order=1, creation_year=2025, creation_month=1)
        self.artwork(name="Blue bowl", category="kitchenware", display_order=0, creation_year=2025, creation_month=2)
        self.artwork(name="Red vase", category="vase", display_order=0, creation_year=2025, creation_month=2)
        create_item(name="Blue secret vase", category="vase", display_order=0, creation_year=2025, creation_month=2)

        self.assertEqual(
            self.all_ids(category="vase", search="blue", created_from="2025-01", created_to="2025-06"),
            [featured.pk] + [item.pk for item in reversed(ordinary)],
        )

    def test_explicit_backend_sort_still_overrides_curated_default(self):
        featured = self.artwork(name="Featured", display_order=0, price="100.00", creation_year=2024, creation_month=1)
        cheap = self.artwork(name="Cheap", price="10.00", creation_year=2025, creation_month=1)

        self.assertEqual(self.all_ids(), [featured.pk, cheap.pk])
        self.assertEqual(self.all_ids(order_by="price"), [cheap.pk, featured.pk])
        self.assertEqual(self.all_ids(order_by="-creation_date"), [cheap.pk, featured.pk])
