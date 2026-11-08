from .helpers import login_as_verified_staff
from rest_framework.test import APITestCase
from ..models import Artist, Item, Tag
from .helpers import create_item


class ItemFilterTest(APITestCase):
    def test_item_list_pagination(self):
        items = [
            create_item(name=f"Item {number}", price="50.00", status=Item.Status.PUBLISHED)
            for number in range(10)
        ]

        first_page = self.client.get("/items/", {"page": 1})

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.data["count"], 10)
        self.assertEqual(len(first_page.data["results"]), 9)
        self.assertIsNotNone(first_page.data["next"])
        self.assertIsNone(first_page.data["previous"])
        self.assertEqual(
            [item["id"] for item in first_page.data["results"]],
            [item.id for item in items[:9]],
        )

        # Follow the link returned by the API to retrieve the next page.
        second_page = self.client.get(first_page.data["next"])

        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(second_page.data["count"], 10)
        self.assertEqual(len(second_page.data["results"]), 1)
        self.assertEqual(second_page.data["results"][0]["id"], items[9].id)
        self.assertIsNone(second_page.data["next"])
        self.assertIsNotNone(second_page.data["previous"])

    def test_inspect_artist_details_queries(self):
        artist = Artist.objects.create(name="Kaan", surname="Cinar")
        tag = Tag.objects.create(name="ceramic")
        for name in ["Bowl", "Jar", "Vase"]:
            item = create_item(name=name, price="50.00", artist=artist, status=Item.Status.PUBLISHED)
            item.tags.add(tag)

        with self.assertNumQueries(4):
            response = self.client.get(
                "/items/",
                {"include_artist": "true"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 3)
        for item_data in response.data["results"]:
            self.assertEqual(
                item_data["artist_details"],
                {"id": artist.id, "name": "Kaan", "surname": "Cinar"},
            )

    def test_multiple_tags_match_any_without_duplicates(self):
        ceramic = Tag.objects.create(name="ceramic")
        handmade = Tag.objects.create(name="handmade")
        wooden = Tag.objects.create(name="wooden")

        jar = create_item(name="Moon Jar", price="100.00", status=Item.Status.PUBLISHED)
        jar.tags.add(ceramic, handmade)
        bowl = create_item(name="Ceramic Bowl", price="50.00", status=Item.Status.PUBLISHED)
        bowl.tags.add(ceramic)
        vase = create_item(name="Handmade Vase", price="75.00", status=Item.Status.PUBLISHED)
        vase.tags.add(handmade)
        unrelated = create_item(name="Wooden Spoon", price="10.00", status=Item.Status.PUBLISHED)
        unrelated.tags.add(wooden)
        create_item(name="Untagged Print", price="20.00", status=Item.Status.PUBLISHED)

        response = self.client.get(
            "/items/",
            {"tag": ["ceramic", "handmade"]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            [item["id"] for item in response.data["results"]],
            [jar.id, bowl.id, vase.id],
        )

    def test_tag_filter_matches_name_case_insensitively(self):
        ceramic = Tag.objects.create(name="ceramic",)
        wooden = Tag.objects.create(name="wooden",)
        jar = create_item(name="Moon Jar", price="100.00",status=Item.Status.PUBLISHED,)
        jar.tags.add(ceramic)
        bowl = create_item(name="Wooden Bowl", price="50.00",status=Item.Status.PUBLISHED,)
        bowl.tags.add(wooden)
        create_item(name="Untagged Vase", price="75.00",status=Item.Status.PUBLISHED,)

        response = self.client.get("/items/", {"tag": "CERAMIC"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [jar.id],
        )

    def test_artist_filter_matches_name_case_insensitively(self):
        kaan = Artist.objects.create(name="Kaan", surname="Cinar")
        maya = Artist.objects.create(name="Maya", surname="Smith")
        kaans_item = create_item(name="Moon Jar", price="100.00", artist=kaan, status=Item.Status.PUBLISHED)
        create_item(name="Vase", price="150.00", artist=maya, status=Item.Status.PUBLISHED)
        create_item(name="Unassigned Bowl", price="50.00", status=Item.Status.PUBLISHED)

        response = self.client.get("/items/", {"artist": "KAAN"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [kaans_item.id],
        )

    def test_list_returns_an_item(self):

        item = create_item(
            name="Magic Bowl",
            price="75.00",
            quantity=2,
         status=Item.Status.PUBLISHED)

        response = self.client.get("/items/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], item.id)

    def test_name_price_category_filter(self):
        login_as_verified_staff(self.client)

        items = [ create_item(**item) for item in [
            {"name": "Magic Bowl", "price": "75.00", "quantity": 2, "category": "kitchenware", "status": Item.Status.PUBLISHED},
            {"name": "Moon Jar", "price": "150.00", "quantity": 4, "category": "vase", "status": Item.Status.PUBLISHED},
            {"name": "Vase", "price": "400.00", "quantity": 10, "category": "vase", "status": Item.Status.PUBLISHED},
            {"name": "Moo Bowl", "price": "75.00", "quantity": 2, "category": "kitchenware", "status": Item.Status.PUBLISHED},
            {"name": "Moo Mug", "price": "35.00", "quantity": 2, "category": "kitchenware", "status": Item.Status.PUBLISHED},
        ] ]

        response = self.client.get(
            "/items/",
            {"name": "moo", 
             "min_price": "40", 
             "category":"kitchenware",
             },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], items[3].id)

    def test_price_range_includes_boundaries(self):
        login_as_verified_staff(self.client)
        below = create_item(name="Below range", price="74.99", quantity=1,status=Item.Status.PUBLISHED,)
        minimum = create_item(name="At minimum", price="75.00", quantity=1,status=Item.Status.PUBLISHED,)
        maximum = create_item(name="At maximum", price="100.00", quantity=1,status=Item.Status.PUBLISHED,)
        above = create_item(name="Above range", price="100.01", quantity=1,status=Item.Status.PUBLISHED,)

        response = self.client.get(
            "/items/",
            {"min_price": "75", "max_price": "100"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            [item["id"] for item in response.data["results"]],
            [minimum.id, maximum.id],
        )

    def test_order_by_price_filter(self):
        login_as_verified_staff(self.client)

        items = [ create_item(**item) for item in [
            {"name": "Magic Blue Bowl", "price": "75.00", "quantity": 2, "category": "kitchenware", "status": Item.Status.PUBLISHED},
            {"name": "Moon Jar", "price": "75", "quantity": 4, "category": "vase", "status": Item.Status.PUBLISHED},
            {"name": "Vase", "price": "75.00", "quantity": 10, "category": "vase", "status": Item.Status.PUBLISHED},
            {"name": "Moo Bowl", "price": "75.00", "quantity": 2, "category": "kitchenware", "status": Item.Status.PUBLISHED},
            {"name": "Moo Mug", "price": "75", "quantity": 2, "category": "kitchenware", "description": "A mug with a blue cow", "status": Item.Status.PUBLISHED},
            {"name": "Apple Vase", "price": "100.00", "quantity": 1, "category": "vase", "status": Item.Status.PUBLISHED},
            {"name": "Zebra Bowl", "price": "50.00", "quantity": 1, "category": "kitchenware", "status": Item.Status.PUBLISHED},
        ] ]

        response = self.client.get(
            "/items/",
            {"order_by": "price", 
             },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 7)
        self.assertEqual(len(response.data["results"]), 7)
        self.assertIsNone(response.data["next"])
        all_results = response.data["results"]
        self.assertEqual(
            [item["id"] for item in all_results],
            [items[6].id, items[0].id, items[3].id, items[4].id, items[1].id, items[2].id, items[5].id],
        )

    def test_inspect_item_list_queries(self):
        tag = Tag.objects.create(name="ceramic")

        for name in ["Bowl", "Jar", "Vase"]:
            item = create_item(name=name, price="50.00", status=Item.Status.PUBLISHED)
            item.tags.add(tag)

        with self.assertNumQueries(4):
            response = self.client.get("/items/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 3)


class BasicItemFilterTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.items = [
            create_item(**item)
            for item in [
                {"name": "Magic Bowl", "price": "75.00", "quantity": 2, "category": "kitchenware", "status": Item.Status.PUBLISHED},
                {"name": "Moon Jar", "price": "150.00", "quantity": 4, "category": "vase", "status": Item.Status.PUBLISHED},
                {"name": "Vase", "price": "400.00", "quantity": 10, "category": "vase", "status": Item.Status.PUBLISHED},
            ]
        ]

    def test_minimum_list_filter(self):
        login_as_verified_staff(self.client)

        items = self.items

        response = self.client.get(
            "/items/",
            {"min_price": "200"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], items[2].id)

    def test_category_filter(self):

        items = self.items

        response = self.client.get(
            "/items/",
            {"category": "kitchenware"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], items[0].id)

    def test_name_filter(self):

        items = self.items

        response = self.client.get(
            "/items/",
            {"name": "moo"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], items[1].id)


class ItemSearchTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.items = [
            create_item(**item)
            for item in [
                {"name": "Magic Blue Bowl", "price": "75.00", "quantity": 2, "category": "kitchenware","status": Item.Status.PUBLISHED},
                {"name": "Moon Jar", "price": "150.00", "quantity": 4, "category": "vase","status": Item.Status.PUBLISHED},
                {"name": "Vase", "price": "400.00", "quantity": 10, "category": "vase","status": Item.Status.PUBLISHED},
                {"name": "Moo Bowl", "price": "75.00", "quantity": 2, "category": "kitchenware","status": Item.Status.PUBLISHED},
                {"name": "Moo Mug", "price": "35.00", "quantity": 2, "category": "kitchenware", "description": "A mug with a blue cow","status": Item.Status.PUBLISHED},
            ]
        ]

    def test_search_filter(self):

        items = self.items

        response = self.client.get(
            "/items/",
            {"search": "BLUE", 
             },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], items[0].id)
        self.assertEqual(response.data["results"][1]["id"], items[4].id)

    def test_search_non_existent_filter(self):

        items = self.items

        response = self.client.get(
            "/items/",
            {"search": "red", 
             },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 0)
