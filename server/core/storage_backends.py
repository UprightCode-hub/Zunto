"""Object storage backends for Cloudflare R2 with local fallback."""

from __future__ import annotations

import importlib.util
import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible

STORAGES_AVAILABLE = importlib.util.find_spec("storages") is not None
USE_R2 = bool(getattr(settings, "USE_OBJECT_STORAGE", False) and STORAGES_AVAILABLE)

if USE_R2:
    from storages.backends.s3boto3 import S3Boto3Storage


@deconstructible
class BaseR2Storage(S3Boto3Storage if USE_R2 else FileSystemStorage):
    """Shared storage config to avoid duplicated backend wiring."""

    location = ""
    file_overwrite = False

    def __init__(self, *args, **kwargs):
        if USE_R2:
            kwargs.setdefault(
                "bucket_name",
                getattr(settings, "OBJECT_STORAGE_BUCKET_NAME", "") or "zuntomedia",
            )
            kwargs.setdefault("region_name", getattr(settings, "OBJECT_STORAGE_REGION", "auto") or "auto")
            kwargs.setdefault("endpoint_url", getattr(settings, "OBJECT_STORAGE_ENDPOINT_URL", "") or None)
            kwargs.setdefault("access_key", getattr(settings, "OBJECT_STORAGE_ACCESS_KEY_ID", ""))
            kwargs.setdefault("secret_key", getattr(settings, "OBJECT_STORAGE_SECRET_ACCESS_KEY", ""))
            kwargs.setdefault("custom_domain", getattr(settings, "OBJECT_STORAGE_CUSTOM_DOMAIN", "") or None)
            kwargs.setdefault("default_acl", None)
            kwargs.setdefault("file_overwrite", False)
            super().__init__(*args, **kwargs)
            return

        location = kwargs.pop("location", None) or self.location
        base_location = getattr(settings, "MEDIA_ROOT", "")
        if location:
            base_location = os.path.join(base_location, location)
        base_url = kwargs.pop("base_url", None) or getattr(settings, "MEDIA_URL", "/media/")
        if location and not base_url.endswith("/"):
            base_url = f"{base_url}/"
        if location:
            base_url = f"{base_url}{location.strip('/')}/"
        super().__init__(location=base_location, base_url=base_url, *args, **kwargs)


@deconstructible
class PublicMediaStorage(BaseR2Storage):
    """Public objects (no signed URL)."""

    location = "public"
    querystring_auth = False


@deconstructible
class PrivateMediaStorage(BaseR2Storage):
    """Private objects (signed URL required)."""

    location = "private"
    querystring_auth = True
