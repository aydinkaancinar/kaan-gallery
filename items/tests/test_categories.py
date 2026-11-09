from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from ..models import Item, Category
from .helpers import create_item, login_with_verified_session


class ArtworkCategoryTests(APITestCase):
    def test_empty_catalog_has_no_categories(self):
        response = self.client.get(reverse("artwork-categories"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_categories_cover_full_public_catalog_without_duplicates(self):
        for index in range(10):
            create_item(category="vase", status=Item.Status.PUBLISHED)
        create_item(category="print", status=Item.Status.PUBLISHED)
        create_item(category="sculpture")
        response = self.client.get(reverse("artwork-categories"), {
            "category": "vase", "search": "no match", "page": 99,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [
            {"value": "vase", "label": "Vase"},
            {"value": "print", "label": "Print"},
        ])

    def test_unpublishing_last_work_removes_category(self):
        item = create_item(category="kitchenware", status=Item.Status.PUBLISHED)
        self.assertEqual(len(self.client.get(reverse("artwork-categories")).data), 1)
        item.status = Item.Status.DRAFT
        item.save(update_fields=["status"])
        self.assertEqual(self.client.get(reverse("artwork-categories")).data, [])

    def test_verified_staff_also_receive_only_public_categories(self):
        create_item(category="sculpture")
        user = get_user_model().objects.create_user(
            username="category-staff", is_staff=True,
        )
        login_with_verified_session(self.client, user)
        response = self.client.get(reverse("artwork-categories"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])


    def test_custom_category_can_be_assigned_serialized_and_filtered(self):
        from ..serializers import ItemSerializer

        category = Category.objects.create(name="Wall hangings", slug="wall-hangings")
        serializer = ItemSerializer(data={
            "name": "Woven moon", "price": "50.00",
            "category": category.slug, "status": Item.Status.PUBLISHED,
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        item = serializer.save()
        self.assertEqual(item.category, category)
        self.assertEqual(ItemSerializer(item).data["category"], category.slug)
        response = self.client.get(reverse("artwork-categories"))
        self.assertEqual(response.data, [{"value": category.slug, "label": category.name}])
        response = self.client.get("/items/", {"category": category.slug})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [item.pk])

    def test_used_category_cannot_be_deleted(self):
        from django.db.models.deletion import ProtectedError

        item = create_item()
        with self.assertRaises(ProtectedError):
            item.category.delete()

    def test_unknown_category_is_rejected(self):
        from ..serializers import ItemSerializer, ItemFilterSerializer

        serializer = ItemSerializer(data={"name": "Test", "price": "50", "category": "missing"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("category", serializer.errors)
        filters = ItemFilterSerializer(data={"category": "missing"})
        self.assertFalse(filters.is_valid())
