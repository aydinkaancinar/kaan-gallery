from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from ..image_variants import VARIANT_TYPES, variant_path
from ..models import ArtworkImage, Item
from .helpers import (
    FILESYSTEM_TEST_STORAGES, close_test_response, closing_response,
    create_item, login_with_verified_session,
)


def image_upload(name="test.png", image_format="PNG"):
    output = BytesIO()
    with Image.new("RGB", (32, 24), "blue") as image:
        image.save(output, image_format)
    return SimpleUploadedFile(name, output.getvalue(), content_type="image/png")


class UploadSecurityTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.media_root = Path(directory.name)
        self.enterContext(self.settings(MEDIA_ROOT=self.media_root, STORAGES=FILESYSTEM_TEST_STORAGES))
        self.item = create_item()
        self.change_url = reverse("admin:tasks_item_change", args=[self.item.pk])
        self.add_url = reverse("admin:tasks_item_add")
        User = get_user_model()
        self.visitor = User.objects.create_user(username="upload-visitor")
        self.staff = User.objects.create_user(username="upload-staff", is_staff=True)
        self.owner = User.objects.create_superuser(
            username="upload-owner", password="test-upload-password",
        )
        self.inactive_owner = User.objects.create_user(
            username="upload-inactive-owner", is_staff=True, is_superuser=True, is_active=False,
        )

    def form(self, upload):
        return {
            "name": "Uploaded artwork",
            "description": "A test artwork uploaded through admin.",
            "price": "50.00",
            "quantity": "0",
            "category": "miscellaneous",
            "status": Item.Status.DRAFT,
            "images-TOTAL_FORMS": "1",
            "images-INITIAL_FORMS": "0",
            "images-MIN_NUM_FORMS": "0",
            "images-MAX_NUM_FORMS": "1000",
            "images-0-image": upload,
            "images-0-alt_text": "A test drawing",
            "images-0-position": "0",
            "_save": "Save",
        }

    def test_admin_upload_rejects_unverified_and_unprivileged_users(self):
        identities = [
            ("anonymous", None, False, 302),
            ("visitor", self.visitor, False, 302),
            ("verified visitor", self.visitor, True, 302),
            ("password-only owner", self.owner, False, 302),
            ("verified staff without model permissions", self.staff, True, 403),
            ("inactive verified owner", self.inactive_owner, True, 302),
        ]
        for label, user, verified, expected in identities:
            client = Client()
            if verified:
                login_with_verified_session(client, user)
            elif user is not None:
                client.force_login(user)
            for url in (self.add_url, self.change_url):
                with self.subTest(identity=label, url=url):
                    response = client.post(url, self.form(image_upload()))
                    self.assertEqual(response.status_code, expected)
                    if expected == 302:
                        self.assertTrue(response["Location"].startswith(reverse("admin:login")))
                        login_page = client.get(response["Location"])
                        self.assertTrue(login_page["Location"].startswith(reverse("two_factor:login")))
                    self.assertEqual(Item.objects.count(), 1)
                    self.item.refresh_from_db()
                    self.assertEqual(self.item.name, "Test artwork")
                    self.assertEqual(ArtworkImage.objects.count(), 0)
                    self.assertEqual(list(self.media_root.rglob("*")), [])

    def test_verified_owner_can_upload_through_admin_add_and_change_forms(self):
        login_with_verified_session(self.client, self.owner)
        for url in (self.add_url, self.change_url):
            with self.subTest(url=url):
                form = self.form(image_upload())
                form["protect_images"] = "on"
                response = self.client.post(url, form)
                self.assertEqual(
                    response.status_code, 302,
                    response.context["adminform"].form.errors if response.status_code == 200 else None,
                )
                uploaded = ArtworkImage.objects.latest("pk")
                self.assertTrue(uploaded.item.protect_images)
                self.assertTrue(uploaded.image.storage.exists(uploaded.image.name))
                for variant in VARIANT_TYPES:
                    self.assertTrue(uploaded.image.storage.exists(
                        variant_path(uploaded.image.name, variant, protected=True),
                    ))
        self.assertEqual(ArtworkImage.objects.count(), 2)
        self.assertEqual(Item.objects.count(), 2)

    def test_admin_upload_requires_csrf_even_with_verified_owner(self):
        client = Client(enforce_csrf_checks=True)
        login_with_verified_session(client, self.owner)
        response = client.post(self.change_url, self.form(image_upload()))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ArtworkImage.objects.count(), 0)
        self.assertEqual(list(self.media_root.rglob("*")), [])

    def test_admin_upload_rejects_invalid_contents_extensions_and_oversized_files(self):
        login_with_verified_session(self.client, self.owner)
        png = image_upload().read()
        cases = [
            ("disguised text", "fake.jpg", b"This is text, not an image."),
            ("truncated jpeg", "broken.jpg", image_upload(image_format="JPEG").read()[:70]),
            ("unsupported gif", "animation.gif", image_upload(image_format="GIF").read()),
            ("html extension", "image.html", png),
            ("over 10 MiB", "large.png", png + b"\0" * (10 * 1024 * 1024 + 1)),
        ]
        for label, filename, contents in cases:
            with self.subTest(case=label):
                upload = SimpleUploadedFile(filename, contents, content_type="image/jpeg")
                response = self.client.post(self.change_url, self.form(upload))
                self.assertEqual(response.status_code, 200)
                forms = response.context["inline_admin_formsets"][0].formset.forms
                self.assertIn("image", forms[0].errors)
                self.assertEqual(ArtworkImage.objects.count(), 0)
                self.assertEqual(list(self.media_root.rglob("*")), [])

    def test_api_nested_images_cannot_upload_or_modify_files(self):
        login_with_verified_session(self.client, self.owner)
        response = self.client.post(
            "/items/",
            '{"name":"API artwork","price":"50.00","images":[{"image":"new.png","alt_text":"Ignored"}]}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(ArtworkImage.objects.count(), 0)
        self.assertEqual(list(self.media_root.rglob("*")), [])
        image = ArtworkImage.objects.create(
            item=self.item, image=image_upload(), alt_text="Original caption",
        )
        source = image.image.name
        response = self.client.patch(
            f"/items/{self.item.pk}/",
            '{"images":[{"image":"replacement.png","alt_text":"Changed caption"}]}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        image.refresh_from_db()
        self.assertEqual(image.image.name, source)
        self.assertEqual(image.alt_text, "Original caption")


class ImageAccessBoundaryTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.enterContext(self.settings(MEDIA_ROOT=directory.name, STORAGES=FILESYSTEM_TEST_STORAGES))
        self.images = []
        for status, protected in [
            (Item.Status.PUBLISHED, False),
            (Item.Status.PUBLISHED, True),
            (Item.Status.DRAFT, False),
        ]:
            item = create_item(status=status, protect_images=protected)
            self.images.append(ArtworkImage.objects.create(
                item=item, image=image_upload(), alt_text="Test artwork",
            ))

    def test_original_and_variant_access_for_each_user_role(self):
        User = get_user_model()
        identities = [
            ("anonymous", None, False, False),
            ("visitor", User.objects.create_user(username="image-visitor"), False, False),
            ("verified visitor", User.objects.create_user(username="image-verified-visitor"), True, False),
            ("password-only staff", User.objects.create_user(username="image-password-staff", is_staff=True), False, False),
            ("verified staff", User.objects.create_user(username="image-verified-staff", is_staff=True), True, True),
            ("inactive staff", User.objects.create_user(username="image-inactive-staff", is_staff=True, is_active=False), True, False),
        ]
        for label, user, verified, privileged in identities:
            client = Client()
            if verified:
                login_with_verified_session(client, user)
            elif user is not None:
                client.force_login(user)
            for image in self.images:
                for variant in (None, *VARIANT_TYPES):
                    kwargs = {"image_id": image.pk}
                    route = "artwork-image"
                    if variant is not None:
                        kwargs["variant"] = variant
                        route = "artwork-image-variant"
                    url = reverse(route, kwargs=kwargs)
                    public = image.item.status == Item.Status.PUBLISHED and (
                        variant is not None or not image.item.protect_images
                    )
                    expected = 200 if privileged or public else 404
                    for method in (client.get, client.head):
                        with self.subTest(role=label, image=image.pk, variant=variant, method=method.__name__):
                            with closing_response(method(url)) as response:
                                self.assertEqual(response.status_code, expected)
                                self.assertIn("no-store", response["Cache-Control"])
                                self.assertIn("private", response["Cache-Control"])

    def test_storage_urls_never_bypass_checked_delivery(self):
        for image in self.images:
            self.assertEqual(self.client.get(image.image.url).status_code, 404)
            for variant in VARIANT_TYPES:
                path = variant_path(image.image.name, variant, image.item.protect_images)
                self.assertEqual(self.client.get(image.image.storage.url(path)).status_code, 404)

    def test_image_delivery_routes_reject_upload_posts(self):
        user = get_user_model().objects.create_superuser(
            username="image-route-owner", password="test-image-route-password",
        )
        login_with_verified_session(self.client, user)
        image = self.images[0]
        urls = [reverse("artwork-image", kwargs={"image_id": image.pk})] + [
            reverse("artwork-image-variant", kwargs={"image_id": image.pk, "variant": variant})
            for variant in VARIANT_TYPES
        ]
        count = ArtworkImage.objects.count()
        source = image.image.name
        for url in urls:
            response = self.client.post(url, {"image": image_upload("attempt.png")})
            self.assertEqual(response.status_code, 405)
            self.assertEqual(ArtworkImage.objects.count(), count)
            image.refresh_from_db()
            self.assertEqual(image.image.name, source)

    def test_unpublishing_revokes_every_previously_accessible_image_url(self):
        image = self.images[0]
        urls = [reverse("artwork-image", kwargs={"image_id": image.pk})] + [
            reverse("artwork-image-variant", kwargs={"image_id": image.pk, "variant": variant})
            for variant in VARIANT_TYPES
        ]
        for url in urls:
            with closing_response(self.client.get(url)) as response:
                self.assertEqual(response.status_code, 200)
        image.item.status = Item.Status.DRAFT
        image.item.save(update_fields=["status"])
        for url in urls:
            for method in (self.client.get, self.client.head):
                response = method(url, HTTP_IF_NONE_MATCH='"old-image"')
                self.assertEqual(response.status_code, 404)
                self.assertIn("no-store", response["Cache-Control"])
