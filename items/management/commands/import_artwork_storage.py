"""Inventory and copy DB-referenced media without changing DB keys or local files."""
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from items.image_variants import VARIANT_TYPES, variant_path
from items.models import ArtworkImage
from items.storage_gateway import MAX_OBJECT_BYTES, QuotaGatewayStorage


class Command(BaseCommand):
    help = "Inventory local artwork media; optionally copy and verify exact keys through the quota gateway."

    def add_arguments(self, parser):
        parser.add_argument("--source-root", default=str(settings.MEDIA_ROOT))
        parser.add_argument("--report", help="Write a JSON inventory; contains paths and hashes, no credentials.")
        parser.add_argument("--upload", action="store_true", help="Copy and verify; default is local inventory only.")
        parser.add_argument("--gateway-url", default=os.environ.get("ARTWORK_GATEWAY_URL"))
        parser.add_argument("--token-file", help="Read STORAGE_TOKEN from a private .dev.vars file.")

    def handle(self, *args, **options):
        root = Path(options["source_root"]).resolve()
        names = set()
        for image in ArtworkImage.objects.select_related("item").iterator():
            if not image.image.name:
                raise CommandError(f"Image {image.pk} has no source filename.")
            names.add(image.image.name)
            names.update(variant_path(image.image.name, kind, image.item.protect_images) for kind in VARIANT_TYPES)
        rows, errors = [], []
        for name in sorted(names):
            parts = PurePosixPath(name).parts
            path = (root / name).resolve()
            if (not parts or parts[0] not in ("artworks", "artwork-variants")
                    or ".." in parts or "\\" in name or name != PurePosixPath(name).as_posix()
                    or len(name.encode()) > 1024 or any(ord(c) < 32 for c in name)
                    or not path.is_relative_to(root)):
                errors.append(f"Unsafe media path: {name}")
                continue
            if not path.is_file():
                errors.append(f"Missing file: {name}")
                continue
            if path.stat().st_size > MAX_OBJECT_BYTES:
                errors.append(f"File exceeds gateway 10 MiB limit: {name}")
                continue
            data = path.read_bytes()
            rows.append({"name": name, "bytes": len(data), "sha256": sha256(data).hexdigest()})
        total = sum(row["bytes"] for row in rows)
        report = {"files": rows, "bytes": total, "reserved_bytes": total + len(rows) * 8192, "errors": errors}
        if options["report"]:
            Path(options["report"]).write_text(json.dumps(report, indent=2) + "\n")
        self.stdout.write(f"{len(rows)} files; {total:,} bytes; {report['reserved_bytes']:,} bytes including metadata reserve.")
        if errors:
            for error in errors:
                self.stderr.write(error)
            raise CommandError(f"Inventory has {len(errors)} errors. No uploads performed.")
        if not options["upload"]:
            self.stdout.write("Inventory only. No remote requests or changes.")
            return
        token = os.environ.get("ARTWORK_GATEWAY_TOKEN", "")
        if options["token_file"]:
            secret_path = Path(options["token_file"])
            if secret_path.stat().st_mode & 0o077:
                raise CommandError("Token file must be private (chmod 600).")
            for line in secret_path.read_text().splitlines():
                if line.startswith("STORAGE_TOKEN="):
                    token = line.split("=", 1)[1].strip().strip('"').strip("'")
        if not options["gateway_url"] or not token:
            raise CommandError("Set --gateway-url and --token-file (or gateway environment variables).")
        gateway = QuotaGatewayStorage(options["gateway_url"], token)
        uploaded = existing = 0
        for row in rows:
            name = row["name"]
            try:
                # Recheck against the inventory so an edited source cannot be silently imported.
                source = (root / name).resolve()
                if not source.is_relative_to(root):
                    raise ValueError("Source path moved outside the media directory.")
                data = source.read_bytes()
                if len(data) != row["bytes"] or sha256(data).hexdigest() != row["sha256"]:
                    raise ValueError("Local file changed after inventory.")
                created = False
                if not gateway.exists(name):
                    try:
                        # Exact immutable key: Storage.save() may rename collisions.
                        gateway._save(name, ContentFile(data))
                        created = True
                    except FileExistsError:
                        pass  # Concurrent import: verify the existing object below.
                with gateway.open(name, "rb") as remote:
                    digest = sha256(remote.read()).hexdigest()
                if digest != row["sha256"]:
                    raise ValueError("Remote bytes differ; existing object was not replaced.")
                uploaded += int(created)
                existing += int(not created)
                self.stdout.write(f"Verified {uploaded + existing}/{len(rows)}: {name}")
                self.stdout.flush()
            except (OSError, ValueError) as error:
                raise CommandError(f"Stopped at {name}: {error} Rerun to resume; local files are unchanged.") from None
        self.stdout.write(self.style.SUCCESS(f"Verified all {len(rows)} files: {uploaded} uploaded, {existing} already present. Database and local media unchanged."))
