from django.contrib.auth import get_user_model
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.test import APIClient, APITestCase
from ..models import Item
from .helpers import login_with_verified_session
from django_otp.oath import totp

User = get_user_model()

# Deferred while gallery features are developed (do not disable existing tests):
# TODO: Additional edge cases: expired numeric OTPs and interrupted login flows.
# TODO: Before deployment: incorrect numeric OTP and replay rejection,
# recovery-code single use, password-only admin/API bypass checks,
# and login rate-limiting enforcement. These remain release requirements.


class SessionSecurityTests(APITestCase):
    def test_staff_post_without_csrf_token_is_rejected(self):
        User.objects.create_user(
            username="session-admin",
            password="test-password-only",
            is_staff=True,
        )

        client = APIClient(enforce_csrf_checks=True)

        logged_in = client.login(
            username="session-admin",
            password="test-password-only",
        )
        self.assertTrue(logged_in)

        response = client.post(
            "/items/",
            {"name": "CSRF test vase", "price": "25.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("CSRF", str(response.data))
        self.assertFalse(
            Item.objects.filter(name="CSRF test vase").exists()
        )

    def test_staff_post_with_csrf_token_succeeds(self):
        admin = User.objects.create_user(
            username="session-admin",
            password="test-password-only",
            is_staff=True,
        )

        client = APIClient(enforce_csrf_checks=True)
        login_with_verified_session(client, admin)

        # The admin page renders a form containing a CSRF token,
        # causing Django to set the CSRF cookie.
        page = client.get("/admin/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("csrftoken", client.cookies)

        token = client.cookies["csrftoken"].value

        response = client.post(
            "/items/",
            {"name": "Valid CSRF vase", "price": "25.00"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            Item.objects.filter(name="Valid CSRF vase").exists()
        )

    def test_admin_login_without_csrf_token_is_rejected(self):
        User.objects.create_user(
            username="login-admin",
            password="test-password-only",
            is_staff=True,
        )

        client = APIClient(enforce_csrf_checks=True)

        response = client.post(
            "/admin/login/",
            {
                "username": "login-admin",
                "password": "test-password-only",
                "next": "/admin/",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertNotIn("_auth_user_id", client.session)

    def test_admin_login_redirects_to_mfa_login(self):
        client = APIClient(enforce_csrf_checks=True)

        response = client.get("/admin/login/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"].split("?")[0],
            reverse("two_factor:login"),
        )

    def test_logout_removes_write_access(self):
        admin = User.objects.create_user(
            username="logout-admin",
            password="test-password-only",
            is_staff=True,
        )

        client = APIClient(enforce_csrf_checks=True)
        login_with_verified_session(client, admin)

        client.get("/admin/")
        token = client.cookies["csrftoken"].value

        response = client.post(
            "/admin/logout/",
            {"csrfmiddlewaretoken": token},
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", client.session)

        response = client.post(
            "/items/",
            {"name": "After logout vase", "price": "25.00"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Item.objects.filter(name="After logout vase").exists()
        )

    def test_staff_without_mfa_cannot_create_item(self):
        User.objects.create_user(
            username="password-only-admin",
            password="test-password-only",
            is_staff=True,
        )

        client = APIClient(enforce_csrf_checks=True)
        self.assertTrue(client.login(
            username="password-only-admin",
            password="test-password-only",
        ))

        client.get("/account/login/")
        token = client.cookies["csrftoken"].value

        response = client.post(
            "/items/",
            {"name": "Unverified vase", "price": "25.00"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Item.objects.filter(name="Unverified vase").exists()
        )

    def test_mfa_verified_staff_can_create_item(self):
        user = User.objects.create_user(
            username="verified-admin",
            password="test-password-only",
            is_staff=True,
        )
        device = TOTPDevice.objects.create(
            user=user,
            name="test-authenticator",
            confirmed=True,
        )

        client = APIClient(enforce_csrf_checks=True)
        self.assertTrue(client.login(
            username="verified-admin",
            password="test-password-only",
        ))

        # Simulate the session state established after successful MFA.
        session = client.session
        session[DEVICE_ID_SESSION_KEY] = device.persistent_id
        session.save()

        page = client.get("/admin/")
        self.assertEqual(page.status_code, 200)
        token = client.cookies["csrftoken"].value

        response = client.post(
            "/items/",
            {"name": "Verified vase", "price": "25.00"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            Item.objects.filter(name="Verified vase").exists()
        )

    def test_password_and_authenticator_code_complete_login(self):
        user = User.objects.create_user(
            username="mfa-admin",
            password="test-password-only",
            is_staff=True,
        )
        device = TOTPDevice.objects.create(
            user=user,
            name="default",
            confirmed=True,
        )

        client = APIClient(enforce_csrf_checks=True)
        login_url = reverse("two_factor:login")

        client.get(login_url)
        csrf_token = client.cookies["csrftoken"].value

        response = client.post(
            login_url,
            {
                "login_view-current_step": "auth",
                "auth-username": "mfa-admin",
                "auth-password": "test-password-only",
                "csrfmiddlewaretoken": csrf_token,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["wizard"]["steps"].current,
            "token",
        )
        self.assertNotIn("_auth_user_id", client.session)

        code = totp(
            device.bin_key,
            step=device.step,
            t0=device.t0,
            digits=device.digits,
            drift=device.drift,
        )

        csrf_token = client.cookies["csrftoken"].value

        response = client.post(
            login_url,
            {
                "login_view-current_step": "token",
                "token-otp_token": f"{code:06d}",
                "csrfmiddlewaretoken": csrf_token,
            },
            format="multipart",
        )

        self.assertRedirects(
            response,
            "/admin/",
            fetch_redirect_response=False,
        )
        self.assertEqual(client.session["_auth_user_id"], str(user.pk))
        self.assertEqual(
            client.session[DEVICE_ID_SESSION_KEY],
            device.persistent_id,
        )

    def test_invalid_authenticator_input_does_not_complete_login(self):
        user = User.objects.create_user(
            username="invalid-code-admin",
            password="test-password-only",
            is_staff=True,
        )
        TOTPDevice.objects.create(user=user, name="default", confirmed=True)

        client = APIClient(enforce_csrf_checks=True)
        login_url = reverse("two_factor:login")

        client.get(login_url)
        # Reach the token step by submitting a valid password first.
        password_response = client.post(
            login_url,
            {
                "login_view-current_step": "auth",
                "auth-username": "invalid-code-admin",
                "auth-password": "test-password-only",
                "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
            },
            format="multipart",
        )
        self.assertEqual(password_response.status_code, 200)
        self.assertEqual(
            password_response.context["wizard"]["steps"].current,
            "token",
        )

        response = client.post(
            login_url,
            {
                "login_view-current_step": "token",
                "token-otp_token": "not-a-code",
                "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["wizard"]["steps"].current,
            "token",
        )
        self.assertTrue(response.context["wizard"]["form"].errors)
        self.assertNotIn("_auth_user_id", client.session)
        self.assertNotIn(DEVICE_ID_SESSION_KEY, client.session)
