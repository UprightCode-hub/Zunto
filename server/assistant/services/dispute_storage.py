#server/assistant/services/dispute_storage.py
"""Storage abstraction for dispute evidence files."""

from pathlib import Path
from django.conf import settings
from core.storage_backends import PrivateMediaStorage


class DisputeStorageService:
    """Abstracts file storage access so backend can switch to object storage later."""

    backend_name = 'object' if getattr(settings, 'USE_OBJECT_STORAGE', False) else 'local'
    storage = PrivateMediaStorage()

    def build_storage_key(self, file_name: str) -> str:
        safe_name = Path(file_name or 'evidence').name
        return f"private/disputes/{safe_name}"

    def delete(self, file_name: str) -> bool:
        if not file_name:
            return False
        if self.storage.exists(file_name):
            self.storage.delete(file_name)
            return True
        return False


dispute_storage = DisputeStorageService()
