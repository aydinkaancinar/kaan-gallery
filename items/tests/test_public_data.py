from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from ..models import Artist, Item, ArtworkImage
from .helpers import create_item, login_with_verified_session


class PublicDataTests(APITestCase):
    def setUp(self):
        self.public_artist = Artist.objects.create(
            name="Public",
            surname="Artist",
        )
        self.private_artist = Artist.objects.create(
            name="Private",
            surname="Artist",
        )

        self.published = create_item(
            name="Published vessel",
            status=Item.Status.PUBLISHED,
            artist=self.public_artist,
            price="125.00",
            quantity=3,
        )
        create_item(
            name="Draft vessel",
            artist=self.private_artist,
            price="250.00",
            quantity=2,
        )

    def test_public_artwork_responses_omit_management_fields(self):
        responses = [
            self.client.get("/items/"),
            self.client.get(f"/items/{self.published.pk}/"),
            self.client.get(
                reverse(
                    "artwork-detail",
                    kwargs={"slug": self.published.slug},
                )
            ),
        ]

        for response in responses:
            self.assertEqual(response.status_code, 200)

        payloads = [
            responses[0].data["results"][0],
            responses[1].data,
            responses[2].data,
        ]

        expected_fields = {
            "id",
            "slug",
            "name",
            "description",
            "category",
            "tags",
            "creation_year",
            "creation_month",
            "artist_details",
            "images",
            "cover_image",
        }

        for payload in payloads:
            with self.subTest(fields=set(payload)):
                self.assertEqual(set(payload), expected_fields)
                self.assertEqual(
                    set(payload["artist_details"]),
                    {"id", "name", "surname"},
                )

    def test_public_price_queries_are_forbidden(self):
        queries = [
            {"min_price": "100"},
            {"max_price": "200"},
            {"order_by": "price"},
        ]

        for query in queries:
            with self.subTest(query=query):
                response = self.client.get("/items/", query)
                self.assertEqual(response.status_code, 403)

    def test_public_artist_list_excludes_draft_only_artists(self):
        response = self.client.get("/artists/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [artist["id"] for artist in response.data],
            [self.public_artist.pk],
        )

    def test_public_cannot_retrieve_draft_only_artist(self):
        response = self.client.get(
            f"/artists/{self.private_artist.pk}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_artist_becomes_public_when_linked_to_published_work(self):
        create_item(
            status=Item.Status.PUBLISHED,
            artist=self.private_artist,
        )

        response = self.client.get(
            f"/artists/{self.private_artist.pk}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.private_artist.pk)

    def test_verified_staff_keep_management_access(self):
        user = get_user_model().objects.create_user(
            username="privacy-test-staff",
            is_staff=True,
        )
        login_with_verified_session(self.client, user)

        artwork_response = self.client.get(
            f"/items/{self.published.pk}/"
        )
        artist_response = self.client.get(
            f"/artists/{self.private_artist.pk}/"
        )
        price_response = self.client.get(
            "/items/", {"min_price": "100"}
        )

        self.assertEqual(artwork_response.status_code, 200)
        self.assertEqual(
            str(artwork_response.data["price"]), "125.00"
        )
        self.assertEqual(artwork_response.data["quantity"], 3)
        self.assertEqual(artist_response.status_code, 200)
        self.assertEqual(price_response.status_code, 200)

    def test_non_staff_and_password_only_staff_receive_public_access(self):
        for staff in (False, True):
            with self.subTest(is_staff=staff):
                self.client.logout()
                user = get_user_model().objects.create_user(
                    username=f"public-role-{staff}", is_staff=staff,
                )
                self.client.force_login(user)
                self.test_public_artwork_responses_omit_management_fields()
                self.test_public_price_queries_are_forbidden()
                self.test_public_artist_list_excludes_draft_only_artists()
                self.test_public_cannot_retrieve_draft_only_artist()

    def test_price_parameters_are_denied_before_validation(self):
        queries = [
            {"min_price": ""}, {"max_price": "invalid"},
            {"min_price": "100", "max_price": "1"},
        ]
        for query in queries:
            with self.subTest(query=query):
                self.assertEqual(self.client.get("/items/", query).status_code, 403)
        self.assertEqual(
            self.client.get("/items/?order_by=price&order_by=name").status_code, 403,
        )

    def test_unpublishing_last_work_hides_artist(self):
        self.published.status = Item.Status.DRAFT
        self.published.save(update_fields=["status"])
        self.assertEqual(self.client.get("/artists/").data, [])
        self.assertEqual(
            self.client.get(f"/artists/{self.public_artist.pk}/").status_code, 404,
        )

    def test_artist_with_multiple_published_works_is_listed_once(self):
        create_item(status=Item.Status.PUBLISHED, artist=self.public_artist)
        response = self.client.get("/artists/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data], [self.public_artist.pk])

    def test_public_images_keep_protected_urls_and_explicit_fields(self):
        image = ArtworkImage.objects.create(
            item=self.published, image="artworks/test-public.jpg",
            alt_text="A ceramic vessel", position=0,
        )
        response = self.client.get(f"/items/{self.published.pk}/")
        self.assertEqual(response.status_code, 200)
        expected = {
            "id": image.pk,
            "image": reverse("artwork-image", kwargs={"image_id": image.pk}),
            "alt_text": "A ceramic vessel", "position": 0,
        }
        self.assertEqual(response.data["images"], [expected])
        self.assertEqual(response.data["cover_image"], expected)

    def test_verified_staff_can_create_and_update_management_fields(self):
        user = get_user_model().objects.create_user(
            username="management-writer", is_staff=True,
        )
        login_with_verified_session(self.client, user)
        response = self.client.post("/items/", {
            "name": "New managed work", "price": "80.00", "quantity": 4,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        item = Item.objects.get(pk=response.data["id"])
        self.assertEqual(str(item.price), "80.00")
        self.assertEqual(item.quantity, 4)
        self.assertEqual(item.status, Item.Status.DRAFT)
        response = self.client.patch(f"/items/{item.pk}/", {
            "price": "95.00", "quantity": 2,
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        item.refresh_from_db()
        self.assertEqual(str(item.price), "95.00")
        self.assertEqual(item.quantity, 2)

    def test_public_name_and_category_order_do_not_depend_on_price(self):
        self.published.name = "Same name"
        self.published.save(update_fields=["name"])
        cheaper = create_item(
            name="Same name", status=Item.Status.PUBLISHED,
            price="1.00", category=self.published.category,
        )
        for ordering in ("name", "category"):
            with self.subTest(ordering=ordering):
                response = self.client.get("/items/", {"order_by": ordering})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    [row["id"] for row in response.data["results"]],
                    [self.published.pk, cheaper.pk],
                )
