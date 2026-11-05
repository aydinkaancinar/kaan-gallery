from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from ..models import Item
from .helpers import create_item, login_with_verified_session

User = get_user_model()


class ItemPermissionTests(APITestCase):

    def test_admin_can_create_item(self):
        admin = User.objects.create_user(
            username="test-admin",
            password="test-password-only",
            is_staff=True,
        )

        login_with_verified_session(self.client, admin)

        response = self.client.post(
            "/items/",
            {"name": "Admin vase", "price": "25.00", "quantity": 1},
            format="json",
        )

        self.assertEqual(response.status_code, 201)

    def test_non_admin_cannot_create_item(self):
        user = User.objects.create_user(
            username="regular-user",
            password="test-password-only",
            is_staff=False,
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(
            "/items/",
            {"name": "Admin vase", "price": "25.00", "quantity": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Item.objects.filter(name="Permission test vase").exists()
        )

    def test_anonymous_cannot_delete_item(self):
        item = create_item(name="Protected vase", price="25.00")

        response = self.client.delete(f"/items/{item.id}/")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Item.objects.filter(id=item.id).exists())

    def test_anonymous_cannot_patch_item(self):
        item = create_item(name="Protected vase", price="25.00")

        response = self.client.patch(
            f"/items/{item.id}/",
            {"price": "1.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        item.refresh_from_db()
        self.assertTrue(Item.objects.filter(id=item.id).exists())
        self.assertEqual(item.price, Decimal("25.00"))

    def test_admin_can_patch_item(self):
        item = create_item(name="Protected vase", price="25.00")
        admin = User.objects.create_user(
            username="test-admin",
            password="test-password-only",
            is_staff=True,
        )
        login_with_verified_session(self.client, admin)
        response = self.client.patch(
            f"/items/{item.id}/",
            {"price": "30.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertTrue(Item.objects.filter(id=item.id).exists())
        self.assertEqual(item.price, Decimal("30.00"))

    def test_admin_can_delete_item(self):
        item = create_item(name="Protected vase", price="25.00", status=Item.Status.PUBLISHED,)
        admin = User.objects.create_user(
            username="test-admin",
            password="test-password-only",
            is_staff=True,
        )
        login_with_verified_session(self.client, admin)
        response = self.client.delete(
            f"/items/{item.id}/"
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Item.objects.filter(id=item.id).exists())


class ItemAPITests(APITestCase):
    def test_create_rejects_zero_price(self):
        admin = User.objects.create_user(
            username="test-admin",
            password="test-password-only",
            is_staff=True,
        )
        login_with_verified_session(self.client, admin)

        response = self.client.post(
            "/items/",
            {
                "name": "Test vase",
                "price": "0.00",
                "quantity": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("price", response.data)
