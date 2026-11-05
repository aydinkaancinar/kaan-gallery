from django.test import TestCase

from .helpers import create_item


class ItemSlugTests(TestCase):
    def test_creating_item_generates_slug(self):
        item = create_item(name="Moon Jar")

        item.refresh_from_db()

        self.assertEqual(item.slug, "moon-jar")

    def test_creating_item_same_name_generates_slug(self):
        item = create_item(name="Moon Jar")
        item2 = create_item(name="Moon Jar")

        item.refresh_from_db()

        self.assertEqual(item.slug, "moon-jar")
        self.assertEqual(item2.slug, "moon-jar-2")

    def test_renaming_item_preserves_slug(self):
        item = create_item(name="Moon Jar")

        item.name = "Blue Moon Jar"
        item.save()
        item.refresh_from_db()

        self.assertEqual(item.name, "Blue Moon Jar")
        self.assertEqual(item.slug, "moon-jar")
