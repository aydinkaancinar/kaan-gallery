from contextlib import contextmanager

from django.core.signals import request_finished
from django.db import close_old_connections

from ..models import Item
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice

FILESYSTEM_TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def close_test_response(response):
    """Release test-client files without closing TestCase's database transaction."""
    if response.closed:
        return
    # Match Django's test client: real request cleanup must not close the
    # connection that TestCase is holding inside its outer atomic block.
    connected = request_finished.disconnect(close_old_connections)
    try:
        response.close()
    finally:
        if connected:
            request_finished.connect(close_old_connections)


@contextmanager
def closing_response(response):
    try:
        yield response
    finally:
        close_test_response(response)


def login_with_verified_session(client, user):
    device = TOTPDevice.objects.create(
        user=user,
        name="test-authenticator",
        confirmed=True,
    )

    client.force_login(user)

    session = client.session
    session[DEVICE_ID_SESSION_KEY] = device.persistent_id
    session.save()


def create_item(**overrides):
    """Create an item with ordinary defaults; publication remains explicit."""
    values = {"name": "Test artwork", "price": "50.00"}
    values.update(overrides)
    if isinstance(values.get("category"), str):
        values["category_id"] = values.pop("category")
    return Item.objects.create(**values)


def login_as_verified_staff(client):
    """Authenticate price/management tests through the real verified session helper."""
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.create_user(
        username="filter-test-staff", is_staff=True,
    )
    login_with_verified_session(client, user)
    return user
