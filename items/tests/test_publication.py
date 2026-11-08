from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from ..models import Item
from .helpers import create_item, login_with_verified_session
from django.urls import reverse

User = get_user_model()

class ItemPublicationTests(APITestCase):
    def setUp(self):
        self.draft = create_item(name="Secret blue vase", price="25.00")
        self.published = create_item(
            name="Public blue vase", price="30.00", status=Item.Status.PUBLISHED,
        )

    def test_anonymous_cannot_retrieve_draft(self):
        response = self.client.get(f"/items/{self.draft.id}/")

        self.assertEqual(response.status_code, 404)

    def test_anonymous_can_retrieve_published_item(self):
        response = self.client.get(f"/items/{self.published.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.published.id)

    def test_new_item_defaults_to_draft(self):
        self.assertEqual(self.draft.status, Item.Status.DRAFT)

    def test_anonymous_list_only_includes_published_items(self):
        response = self.client.get("/items/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [self.published.id],
        )

    def test_non_staff_list_only_includes_published_items(self):
        user = User.objects.create_user(username="gallery-visitor")
        self.client.force_authenticate(user=user)

        response = self.client.get("/items/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [self.published.id],
        )

    def test_staff_list_includes_drafts_and_published_items(self):
        staff = User.objects.create_user(username="gallery-admin", is_staff=True)
        login_with_verified_session(self.client, staff)

        response = self.client.get("/items/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertCountEqual(
            [item["id"] for item in response.data["results"]],
            [self.draft.id, self.published.id],
        )

    def test_public_search_excludes_matching_drafts(self):
        response = self.client.get("/items/", {"search": "blue"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [self.published.id],
        )

    def test_public_pagination_counts_only_published_items(self):
        for number in range(9):
            create_item(
                name=f"Public work {number}", price="50.00",
                status=Item.Status.PUBLISHED,
            )

        first_page = self.client.get("/items/")

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.data["count"], 10)
        self.assertEqual(len(first_page.data["results"]), 9)
        self.assertIsNotNone(first_page.data["next"])
        second_page = self.client.get(first_page.data["next"])
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(second_page.data["count"], 10)
        self.assertEqual(len(second_page.data["results"]), 1)
        self.assertIsNone(second_page.data["next"])
        returned_ids = [
            item["id"]
            for item in first_page.data["results"] + second_page.data["results"]
        ]
        self.assertNotIn(self.draft.id, returned_ids)
        self.assertEqual(len(set(returned_ids)), 10)

    def test_staff_can_retrieve_draft(self):
        staff = User.objects.create_user(
            username="gallery-staff",
            is_staff=True,
        )
        login_with_verified_session(self.client, staff)

        response = self.client.get(f"/items/{self.draft.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.draft.id)

    def test_public_can_retrieve_published_artwork_by_slug(self):
        response = self.client.get(
            reverse(
                "artwork-detail",
                kwargs={"slug": self.published.slug},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.published.id)

    def test_public_cannot_retrieve_draft_by_slug(self):
        response = self.client.get(
            reverse(
                "artwork-detail",
                kwargs={"slug": self.draft.slug},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_staff_without_mfa_cannot_retrieve_draft(self):
        staff = User.objects.create_user(
            username="unverified-staff",
            is_staff=True,
        )

        self.client.force_login(staff)

        response = self.client.get(f"/items/{self.draft.pk}/")

        self.assertEqual(response.status_code, 404)

    def test_staff_without_mfa_cannot_retrieve_draft_by_slug(self):
        staff = User.objects.create_user(
            username="unverified-slug-staff",
            is_staff=True,
        )
        self.client.force_login(staff)

        response = self.client.get(
            reverse(
                "artwork-detail",
                kwargs={"slug": self.draft.slug},
            )
        )

        self.assertEqual(response.status_code, 404)
