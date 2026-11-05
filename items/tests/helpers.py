from ..models import Item
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice


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
    return Item.objects.create(**values)
