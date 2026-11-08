"""Executable specification; see docs/CREATION_DATE_SPEC.md.

These tests intentionally precede the feature implementation. API tests require
migrations for the creation_year/creation_month model fields first.
"""

from .helpers import login_as_verified_staff
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from ..models import Item
from ..serializers import ItemFilterSerializer, ItemSerializer
from .helpers import create_item, login_with_verified_session


class CreationDateValidationTests(SimpleTestCase):
    def payload(self, **overrides):
        return {"name": "Date study", "price": "25.00", **overrides}

    def test_valid_year_and_month_boundaries(self):
        for year in [1999, 2025, 2099]:
            for month in [1, 12]:
                with self.subTest(year=year, month=month):
                    serializer = ItemSerializer(data=self.payload(
                        creation_year=year, creation_month=month,
                    ))
                    self.assertTrue(serializer.is_valid(), serializer.errors)
                    self.assertEqual(serializer.validated_data["creation_year"], year)
                    self.assertEqual(serializer.validated_data["creation_month"], month)

    def test_omitted_date_is_valid(self):
        serializer = ItemSerializer(data=self.payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_both_null_is_valid(self):
        serializer = ItemSerializer(data=self.payload(creation_year=None, creation_month=None))
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_field_values_are_rejected(self):
        for field, values in {
            "creation_year": [1998, 2100, "hello", "2025.5", ""],
            "creation_month": [0, 13, -1, "hello", "1.5", ""],
        }.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    data = self.payload(creation_year=2025, creation_month=3)
                    data[field] = value
                    serializer = ItemSerializer(data=data)
                    self.assertFalse(serializer.is_valid())
                    self.assertIn(field, serializer.errors)

    def test_create_requires_both_components_or_neither(self):
        for fields in [
            {"creation_year": 2025}, {"creation_month": 3},
            {"creation_year": 2025, "creation_month": None},
            {"creation_year": None, "creation_month": 3},
        ]:
            with self.subTest(fields=fields):
                serializer = ItemSerializer(data=self.payload(**fields))
                self.assertFalse(serializer.is_valid())
                self.assertTrue(serializer.errors)

    def test_patch_validates_resulting_date_not_just_submitted_fields(self):
        item = Item(name="Vase", price="25.00", creation_year=2024, creation_month=12)
        for changes in [{"creation_year": 2025}, {"creation_month": 1}, {"name": "New title"}]:
            with self.subTest(changes=changes):
                serializer = ItemSerializer(item, data=changes, partial=True)
                self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_patch_cannot_clear_only_half_of_existing_date(self):
        item = Item(name="Vase", price="25.00", creation_year=2025, creation_month=3)
        for changes in [{"creation_year": None}, {"creation_month": None}]:
            with self.subTest(changes=changes):
                serializer = ItemSerializer(item, data=changes, partial=True)
                self.assertFalse(serializer.is_valid())

    def test_patch_unknown_date_cannot_set_only_one_component(self):
        item = Item(name="Undated", price="25.00")
        for changes in [{"creation_year": 2025}, {"creation_month": 3}]:
            with self.subTest(changes=changes):
                serializer = ItemSerializer(item, data=changes, partial=True)
                self.assertFalse(serializer.is_valid())

    def test_patch_can_clear_both_components(self):
        item = Item(name="Vase", price="25.00", creation_year=2025, creation_month=3)
        serializer = ItemSerializer(item, data={"creation_year": None, "creation_month": None}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_model_field_validators_reject_invalid_ranges(self):
        for year, month, field in [(1998, 3, "creation_year"), (2100, 3, "creation_year"), (2025, 0, "creation_month"), (2025, 13, "creation_month")]:
            with self.subTest(year=year, month=month):
                item = Item(name="Vase", price="25.00", slug="test-vase", creation_year=year, creation_month=month)
                with self.assertRaises(ValidationError) as error:
                    item.full_clean(validate_unique=False, validate_constraints=False)
                self.assertIn(field, error.exception.message_dict)


class CreationDateFilterValidationTests(SimpleTestCase):
    def test_optional_filters_and_ordering_are_accepted(self):
        for params in [{}, {"creation_year": "2025"}, {"creation_month": "3"},
                       {"created_from": "2024-12"}, {"created_to": "2025-03"},
                       {"created_from": "2025-03", "created_to": "2025-03"},
                       {"order_by": "creation_date"}, {"order_by": "-creation_date"}]:
            with self.subTest(params=params):
                serializer = ItemFilterSerializer(data=params)
                self.assertTrue(serializer.is_valid(), serializer.errors)
                # Unknown fields being silently ignored must not satisfy the test.
                for key in params:
                    self.assertIn(key, serializer.validated_data)

    def test_invalid_date_filters_are_rejected(self):
        cases = {
            "creation_year": ["hello", "1998", "2100", "2025.5", ""],
            "creation_month": ["hello", "0", "13", "1.5", ""],
            "created_from": ["2025", "2025-3", "2025-00", "2025-13", "2025-03-01", "hello", "1998-12", ""],
            "created_to": ["2025", "2025-3", "2025-00", "2025-13", "2025-03-01", "hello", "2100-01", ""],
        }
        for key, values in cases.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    serializer = ItemFilterSerializer(data={key: value})
                    self.assertFalse(serializer.is_valid())
                    self.assertIn(key, serializer.errors)

    def test_reversed_date_range_is_rejected(self):
        serializer = ItemFilterSerializer(data={"created_from": "2025-03", "created_to": "2024-12"})
        self.assertFalse(serializer.is_valid())
        self.assertTrue(serializer.errors)


class CreationDateAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.before = create_item(name="Earlier", creation_year=2024, creation_month=11, status=Item.Status.PUBLISHED)
        cls.lower = create_item(name="December", creation_year=2024, creation_month=12, status=Item.Status.PUBLISHED)
        cls.later_name = create_item(name="Zebra vase", creation_year=2025, creation_month=3, category="vase", status=Item.Status.PUBLISHED)
        cls.earlier_name = create_item(name="Apple vase", creation_year=2025, creation_month=3, category="vase", status=Item.Status.PUBLISHED)
        cls.same_name = create_item(name="Apple vase", creation_year=2025, creation_month=3, category="vase", status=Item.Status.PUBLISHED)
        cls.after = create_item(name="After", creation_year=2025, creation_month=4, status=Item.Status.PUBLISHED)
        cls.same_month_other_year = create_item(name="Older March", creation_year=2024, creation_month=3, status=Item.Status.PUBLISHED)
        cls.unknown = create_item(name="Undated", status=Item.Status.PUBLISHED)
        cls.draft = create_item(name="Secret", creation_year=2025, creation_month=3)

    def result_ids(self, **params):
        """Collect all pages; assert pagination stays consistent and loop-free."""
        response = self.client.get("/items/", params)
        self.assertEqual(response.status_code, 200, response.data)
        count = response.data["count"]
        results = list(response.data["results"])
        visited = set()
        while response.data["next"]:
            url = response.data["next"]
            self.assertNotIn(url, visited)
            visited.add(url)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["count"], count)
            results.extend(response.data["results"])
        ids = [item["id"] for item in results]
        self.assertEqual(len(ids), count)
        self.assertEqual(len(set(ids)), count)
        return ids

    def test_filter_by_year(self):
        self.assertCountEqual(self.result_ids(creation_year="2025"), [self.later_name.pk, self.earlier_name.pk, self.same_name.pk, self.after.pk])

    def test_filter_by_month_across_years(self):
        self.assertCountEqual(self.result_ids(creation_month="3"), [self.later_name.pk, self.earlier_name.pk, self.same_name.pk, self.same_month_other_year.pk])

    def test_filter_by_year_and_month(self):
        self.assertCountEqual(self.result_ids(creation_year="2025", creation_month="3"), [self.later_name.pk, self.earlier_name.pk, self.same_name.pk])

    def test_inclusive_range_crosses_year_boundary(self):
        self.assertCountEqual(self.result_ids(created_from="2024-12", created_to="2025-03"), [self.lower.pk, self.later_name.pk, self.earlier_name.pk, self.same_name.pk])

    def test_open_ended_ranges(self):
        self.assertEqual(self.result_ids(created_from="2025-04"), [self.after.pk])
        self.assertCountEqual(self.result_ids(created_to="2024-11"), [self.before.pk, self.same_month_other_year.pk])

    def test_equal_range_bounds_select_one_month(self):
        self.assertCountEqual(self.result_ids(created_from="2025-03", created_to="2025-03"), [self.later_name.pk, self.earlier_name.pk, self.same_name.pk])

    def test_range_with_no_matches(self):
        self.assertEqual(self.result_ids(created_from="2026-01", created_to="2026-12"), [])

    def test_oldest_first_with_name_id_ties_and_unknown_last(self):
        self.assertEqual(self.result_ids(order_by="creation_date"), [self.same_month_other_year.pk, self.before.pk, self.lower.pk, self.earlier_name.pk, self.same_name.pk, self.later_name.pk, self.after.pk, self.unknown.pk])

    def test_newest_first_keeps_name_id_ties_ascending_and_unknown_last(self):
        self.assertEqual(self.result_ids(order_by="-creation_date"), [self.after.pk, self.earlier_name.pk, self.same_name.pk, self.later_name.pk, self.lower.pk, self.before.pk, self.same_month_other_year.pk, self.unknown.pk])

    def test_search_year(self):
        self.assertCountEqual(self.result_ids(search="2025"), [self.later_name.pk, self.earlier_name.pk, self.same_name.pk, self.after.pk])

    def test_search_year_month(self):
        self.assertCountEqual(self.result_ids(search="2025-03"), [self.later_name.pk, self.earlier_name.pk, self.same_name.pk])

    def test_search_date_with_no_matches(self):
        self.assertEqual(self.result_ids(search="2026-09"), [])

    def test_non_date_search_still_searches_text(self):
        self.assertEqual(self.result_ids(search="zebra"), [self.later_name.pk])

    def test_date_search_is_not_a_text_match(self):
        create_item(name="Study 2025-03", description="2025", status=Item.Status.PUBLISHED)
        self.assertCountEqual(self.result_ids(search="2025-03"), [self.later_name.pk, self.earlier_name.pk, self.same_name.pk])

    def test_combines_date_category_text_price_and_sorting(self):
        login_as_verified_staff(self.client)
        self.assertEqual(self.result_ids(creation_year="2025", creation_month="3", category="vase", name="apple", min_price="40", max_price="60", order_by="-creation_date"), [self.earlier_name.pk, self.same_name.pk])

    def test_invalid_parameters_return_400(self):
        for params in [{"creation_month": "13"}, {"creation_year": "hello"},
                       {"created_from": "2025-13"}, {"created_to": "2025-3"},
                       {"created_from": "2025-03", "created_to": "2024-12"}]:
            with self.subTest(params=params):
                response = self.client.get("/items/", params)
                self.assertEqual(response.status_code, 400)

    def test_unknown_date_survives_unfiltered_list_and_serializes_as_null(self):
        self.assertIn(self.unknown.pk, self.result_ids())
        response = self.client.get(f"/items/{self.unknown.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["creation_year"])
        self.assertIsNone(response.data["creation_month"])

    def test_api_create_and_patch_persist_date_without_altering_record_timestamp(self):
        staff = get_user_model().objects.create_user(username="date-admin", is_staff=True)
        login_with_verified_session(self.client, staff)
        response = self.client.post("/items/", {"name": "New date study", "price": "25.00", "creation_year": 2025, "creation_month": 3}, format="json")
        self.assertEqual(response.status_code, 201)
        item = Item.objects.get(pk=response.data["id"])
        self.assertEqual((item.creation_year, item.creation_month), (2025, 3))
        original_timestamp = item.created
        for changes, expected in [({"creation_month": 4}, (2025, 4)), ({"creation_year": 2024}, (2024, 4)), ({"name": "Renamed"}, (2024, 4)), ({"creation_year": None, "creation_month": None}, (None, None))]:
            with self.subTest(changes=changes):
                response = self.client.patch(f"/items/{item.pk}/", changes, format="json")
                self.assertEqual(response.status_code, 200)
                item.refresh_from_db()
                self.assertEqual((item.creation_year, item.creation_month), expected)
                self.assertEqual(item.created, original_timestamp)

    def test_rejected_half_date_patch_leaves_database_unchanged(self):
        staff = get_user_model().objects.create_user(username="invalid-date-admin", is_staff=True)
        login_with_verified_session(self.client, staff)
        response = self.client.patch(f"/items/{self.lower.pk}/", {"creation_month": None}, format="json")
        self.assertEqual(response.status_code, 400)
        self.lower.refresh_from_db()
        self.assertEqual((self.lower.creation_year, self.lower.creation_month), (2024, 12))
