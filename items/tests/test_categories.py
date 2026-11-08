from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from ..models import Item
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
            {"value": "vase", "label": Item.Category.VASE.label},
            {"value": "print", "label": Item.Category.PRINT.label},
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
