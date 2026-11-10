from datetime import timedelta

from axes.models import AccessAttempt
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.oath import totp


class LoginRateLimitTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.username = "rate-limit-test"
        self.password = "test-password-only"
        user = get_user_model().objects.create_user(
            username=self.username, password=self.password, is_staff=True,
        )
        TOTPDevice.objects.create(user=user, name="default", confirmed=True)
        self.login_url = reverse("two_factor:login")

    def submit_password(self, password):
        self.client.get(self.login_url)
        return self.client.post(self.login_url, {
            "login_view-current_step": "auth",
            "auth-username": self.username,
            "auth-password": password,
            "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
        })

    def reach_limit(self):
        for attempt in range(5):
            response = self.submit_password("incorrect-password")
            self.assertEqual(response.status_code, 200 if attempt < 4 else 429)

    def test_five_failures_block_even_the_correct_password(self):
        self.reach_limit()
        response = self.submit_password(self.password)
        self.assertEqual(response.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_cooldown_restores_access_to_the_mfa_step(self):
        self.reach_limit()
        AccessAttempt.objects.update(
            attempt_time=timezone.now() - timedelta(minutes=16),
        )
        response = self.submit_password(self.password)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["wizard"]["steps"].current, "token")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_complete_mfa_login_clears_failed_passwords(self):
        for _ in range(4):
            self.assertEqual(self.submit_password("incorrect-password").status_code, 200)
        self.assertEqual(
            AccessAttempt.objects.get(username=self.username).failures_since_start, 4,
        )

        response = self.submit_password(self.password)
        self.assertEqual(response.context["wizard"]["steps"].current, "token")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(AccessAttempt.objects.filter(username=self.username).exists())

        device = TOTPDevice.objects.get(user__username=self.username, name="default")
        code = totp(
            device.bin_key, step=device.step, t0=device.t0,
            digits=device.digits, drift=device.drift,
        )
        response = self.client.post(self.login_url, {
            "login_view-current_step": "token",
            "token-otp_token": f"{code:06d}",
            "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
        })
        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)
        self.assertEqual(self.client.session["otp_device_id"], device.persistent_id)
        self.assertFalse(AccessAttempt.objects.filter(username=self.username).exists())

        self.client.logout()
        self.assertEqual(self.submit_password("incorrect-password").status_code, 200)
        self.assertEqual(
            AccessAttempt.objects.get(username=self.username).failures_since_start, 1,
        )

    def test_block_is_specific_to_the_username_and_ip_pair(self):
        self.client = Client(enforce_csrf_checks=True, REMOTE_ADDR="198.51.100.10")
        self.reach_limit()

        self.client = Client(enforce_csrf_checks=True, REMOTE_ADDR="198.51.100.11")
        response = self.submit_password(self.password)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["wizard"]["steps"].current, "token")

        self.username = "another-rate-limit-test"
        user = get_user_model().objects.create_user(
            username=self.username, password=self.password, is_staff=True,
        )
        TOTPDevice.objects.create(user=user, name="default", confirmed=True)
        self.client = Client(enforce_csrf_checks=True, REMOTE_ADDR="198.51.100.10")
        response = self.submit_password(self.password)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["wizard"]["steps"].current, "token")

    def test_blocked_attempts_do_not_extend_the_cooldown(self):
        self.reach_limit()
        attempt = AccessAttempt.objects.get(username=self.username)
        blocked_at = attempt.attempt_time
        response = self.submit_password(self.password)
        self.assertEqual(response.status_code, 429)
        attempt.refresh_from_db()
        self.assertEqual(attempt.attempt_time, blocked_at)
        self.assertEqual(attempt.failures_since_start, 5)

    def test_forwarded_headers_cannot_evade_the_local_ip_limit(self):
        self.reach_limit()
        self.client.defaults["HTTP_X_FORWARDED_FOR"] = "198.51.100.99"
        self.client.defaults["HTTP_CF_CONNECTING_IP"] = "198.51.100.99"
        response = self.submit_password(self.password)
        self.assertEqual(response.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_failed_password_is_redacted_in_stored_attempts(self):
        password = "unique-secret-for-redaction-test"
        self.assertEqual(self.submit_password(password).status_code, 200)
        attempt = AccessAttempt.objects.get(username=self.username)
        self.assertNotIn(password, attempt.post_data)
        self.assertIn("auth-password=********************", attempt.post_data)

    def test_lockout_message_explains_the_wait(self):
        self.reach_limit()
        response = self.submit_password(self.password)
        self.assertContains(response, "15 minutes", status_code=429)
        self.assertEqual(response["Retry-After"], "900")
