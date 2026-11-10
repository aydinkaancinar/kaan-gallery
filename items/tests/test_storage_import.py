from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from items.image_variants import VARIANT_TYPES, variant_path
from items.models import ArtworkImage
from .helpers import create_item


class FakeGateway:
    def __init__(self):
        self.files = {}
        self.fail_name = None
        self.writes = []

    def exists(self, name):
        return name in self.files

    def _save(self, name, content):
        if name == self.fail_name:
            raise OSError("Temporary outage")
        if name in self.files:
            raise FileExistsError()
        self.files[name] = content.read()
        self.writes.append(name)
        return name

    def open(self, name, mode):
        return ContentFile(self.files[name])


class StorageImportTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = "artworks/import.png"
        ArtworkImage.objects.bulk_create([ArtworkImage(item=create_item(), image=self.source)])
        self.names = sorted([self.source] + [variant_path(self.source, kind) for kind in VARIANT_TYPES])
        for name in self.names:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode())
        self.gateway = FakeGateway()

    def run_import(self, upload=True):
        with patch("items.management.commands.import_artwork_storage.QuotaGatewayStorage", return_value=self.gateway) as factory:
            call_command("import_artwork_storage", source_root=str(self.root), upload=upload,
                         gateway_url="https://gateway.test", stdout=StringIO(), stderr=StringIO())
            return factory

    @patch.dict("os.environ", {"ARTWORK_GATEWAY_TOKEN": "x" * 40})
    def test_partial_upload_resumes_without_renaming_or_rewriting(self):
        self.gateway.fail_name = self.names[1]
        with self.assertRaises(CommandError):
            self.run_import()
        self.assertEqual(self.gateway.writes, self.names[:1])
        self.gateway.fail_name = None
        self.run_import()
        self.assertEqual(self.gateway.writes, self.names)
        self.run_import()
        self.assertEqual(self.gateway.writes, self.names)
        self.assertEqual(ArtworkImage.objects.get().image.name, self.source)
        for name in self.names:
            self.assertEqual(self.gateway.files[name], (self.root / name).read_bytes())

    @patch.dict("os.environ", {"ARTWORK_GATEWAY_TOKEN": "x" * 40})
    def test_mismatched_existing_object_stops_without_overwrite(self):
        self.gateway.files[self.names[0]] = b"different"
        with self.assertRaisesMessage(CommandError, "Remote bytes differ"):
            self.run_import()
        self.assertEqual(self.gateway.writes, [])
        self.assertEqual(self.gateway.files[self.names[0]], b"different")

    def test_missing_file_prevents_all_remote_work_and_inventory_is_offline(self):
        factory = self.run_import(upload=False)
        factory.assert_not_called()
        (self.root / self.source).unlink()
        with patch("items.management.commands.import_artwork_storage.QuotaGatewayStorage") as factory:
            with self.assertRaisesMessage(CommandError, "No uploads performed"):
                self.run_import()
            factory.assert_not_called()
