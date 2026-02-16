"""Storage abstraction for dispute evidence files."""

from pathlib import Path
from django.core.files.storage import default_storage


class DisputeStorageService:
    """Abstracts file storage access so backend can switch to object storage later."""

    backend_name = 'local'

    def build_storage_key(self, file_name: str) -> str:
        safe_name = Path(file_name or 'evidence').name
        return f"assistant/dispute_evidence/{safe_name}"

    def delete(self, file_name: str) -> bool:
        if not file_name:
            return False
        if default_storage.exists(file_name):
            default_storage.delete(file_name)
            return True
        return False


dispute_storage = DisputeStorageService()
