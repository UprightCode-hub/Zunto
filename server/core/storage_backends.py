"""Local media storage backends.

These classes remain so existing FileField/ImageField declarations do not need
risky schema changes, but they always use Django's local FileSystemStorage.
"""

from __future__ import annotations

import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class LocalMediaStorage(FileSystemStorage):
    """Local storage base class for media files."""

    storage_location = ""
    file_overwrite = False

    def __init__(self, *args, **kwargs):
        location = kwargs.pop("location", None) or self.storage_location
        base_location = os.path.abspath(str(getattr(settings, "MEDIA_ROOT", "")))
        if location:
            base_location = os.path.join(base_location, location)
        base_url = kwargs.pop("base_url", None) or getattr(settings, "MEDIA_URL", "/media/")
        if location and not base_url.endswith("/"):
            base_url = f"{base_url}/"
        if location:
            base_url = f"{base_url}{location.strip('/')}/"
        super().__init__(location=base_location, base_url=base_url, *args, **kwargs)

    def url(self, name):
        normalized_name = str(name or '').lstrip('/')
        location_prefix = str(getattr(self, 'storage_location', '') or '').strip('/')
        if location_prefix and normalized_name.startswith(f'{location_prefix}/'):
            normalized_name = normalized_name[len(location_prefix) + 1:]
        return super().url(normalized_name)

    def path(self, name):
        normalized_name = str(name or '').lstrip('/').replace('/', os.sep)
        return os.path.join(str(getattr(self, 'base_location', '') or ''), normalized_name)


@deconstructible
class PublicMediaStorage(LocalMediaStorage):
    """Public media files."""

    storage_location = "public"
    querystring_auth = False


@deconstructible
class PrivateMediaStorage(LocalMediaStorage):
    """Private media files."""

    storage_location = "private"
    querystring_auth = True
