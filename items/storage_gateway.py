import base64
from datetime import timezone
from email.utils import parsedate_to_datetime
import json
import mimetypes
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.http import HttpResponse
from django.utils.cache import add_never_cache_headers
from django.utils.deconstruct import deconstructible


MAX_OBJECT_BYTES = 10 * 1024 * 1024


class StorageUnavailable(OSError):
    def __init__(self, retry_after=900):
        super().__init__("Artwork storage is temporarily unavailable.")
        self.retry_after = retry_after


class NoStorageRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, new_url):
        # Storage credentials must stay on the configured gateway.
        return None


class StorageUnavailableMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, StorageUnavailable):
            return None
        response = HttpResponse("Artwork storage is temporarily unavailable.", status=503)
        response["Retry-After"] = str(exception.retry_after)
        response["X-Content-Type-Options"] = "nosniff"
        add_never_cache_headers(response)
        return response


@deconstructible
class QuotaGatewayStorage(Storage):
    """Private storage through the authenticated Worker; no S3 or public URL fallback."""

    def __init__(self, base_url, token, timeout=20):
        origin = urlsplit(base_url)
        if (
            origin.scheme != "https" or not origin.hostname or origin.username or origin.password
            or origin.query or origin.fragment or origin.path not in ("", "/")
        ):
            raise ImproperlyConfigured("ARTWORK_GATEWAY_URL must be an HTTPS origin.")
        if not token or len(token) < 32 or "\n" in token or "\r" in token:
            raise ImproperlyConfigured("ARTWORK_GATEWAY_TOKEN must contain at least 32 characters.")
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _request(self, method, name, body=None):
        encoded = base64.urlsafe_b64encode(name.encode()).decode().rstrip("=")
        request = Request(
            f"{self.base_url}/v1/objects/{encoded}", data=body, method=method,
            headers={"Authorization": f"Bearer {self.token}", "User-Agent": "KaanGallery-Storage/1.0"},
        )
        if body is not None:
            request.add_header("Content-Type", mimetypes.guess_type(name)[0] or "application/octet-stream")
            request.add_header("Content-Length", str(len(body)))
        try:
            return build_opener(NoStorageRedirects()).open(request, timeout=self.timeout)
        except HTTPError as error:
            if error.code == 404:
                error.close()
                raise FileNotFoundError("Artwork image not found.") from None
            if error.code == 409:
                error.close()
                raise FileExistsError("Artwork object already exists.") from None
            retry_after = error.headers.get("Retry-After", "900")
            error.close()
            try:
                retry_after = max(1, min(86400, int(retry_after)))
            except (ValueError, TypeError):
                retry_after = 900
            raise StorageUnavailable(retry_after) from None
        except (URLError, socket.timeout, TimeoutError):
            raise StorageUnavailable() from None

    def _open(self, name, mode="rb"):
        if mode not in ("r", "rb"):
            raise ValueError("Artwork storage files are read-only; use save() to create a new object.")
        with self._request("GET", name) as response:
            data = response.read(MAX_OBJECT_BYTES + 1)
        if len(data) > MAX_OBJECT_BYTES:
            raise StorageUnavailable()
        return ContentFile(data, name=name)

    def _save(self, name, content):
        chunks = []
        size = 0
        for chunk in content.chunks():
            size += len(chunk)
            if size > MAX_OBJECT_BYTES:
                raise ValueError("Artwork files must be 10 MiB or smaller.")
            chunks.append(chunk)
        body = b"".join(chunks)
        with self._request("PUT", name, body) as response:
            try:
                json.load(response)
            except (ValueError, UnicodeError):
                raise StorageUnavailable() from None
        return name

    def save(self, name, content, max_length=None):
        for _ in range(3):
            try:
                return super().save(name, content, max_length=max_length)
            except FileExistsError:
                # Repeat Django's available-name selection with the caller's length limit.
                continue
        raise StorageUnavailable()

    def exists(self, name):
        try:
            with self._request("HEAD", name):
                return True
        except FileNotFoundError:
            return False

    def size(self, name):
        with self._request("HEAD", name) as response:
            try:
                size = int(response.headers["Content-Length"])
            except (ValueError, TypeError):
                raise StorageUnavailable() from None
        if size < 0 or size > MAX_OBJECT_BYTES:
            raise StorageUnavailable()
        return size

    def get_modified_time(self, name):
        with self._request("HEAD", name) as response:
            try:
                timestamp = parsedate_to_datetime(response.headers["Last-Modified"])
            except (ValueError, TypeError, IndexError):
                raise StorageUnavailable() from None
        return timestamp.astimezone(timezone.utc)

    def delete(self, name):
        try:
            with self._request("DELETE", name):
                pass
        except FileNotFoundError:
            pass

    def url(self, name):
        raise ValueError("Private artwork storage has no public URLs.")
