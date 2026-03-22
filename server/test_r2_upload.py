import os
from django.core.files.base import ContentFile
import django
import boto3

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ZuntoProject.settings")
django.setup()

from core.storage_backends import PublicMediaStorage, PrivateMediaStorage
from django.conf import settings

# Initialize storage
public_storage = PublicMediaStorage()
private_storage = PrivateMediaStorage()

# Create test content
content = ContentFile(b"This is a test file for R2 storage.")

# Test filenames (no prefix — storage location is already set on the class)
public_file_name = "test_file.txt"
private_file_name = "test_file.txt"

# Upload to public storage
public_storage.save(public_file_name, content)
print(f"Uploaded to public storage: {public_file_name}")

# Upload to private storage
private_storage.save(private_file_name, content)
print(f"Uploaded to private storage: {private_file_name}")

# Generate public URL
public_url = public_storage.url(public_file_name)
print(f"Public file URL: {public_url}")

# Generate private signed URL using boto3
s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.OBJECT_STORAGE_ACCESS_KEY_ID,
    aws_secret_access_key=settings.OBJECT_STORAGE_SECRET_ACCESS_KEY,
    endpoint_url=settings.OBJECT_STORAGE_ENDPOINT_URL,
)

bucket_name = settings.OBJECT_STORAGE_BUCKET_NAME

signed_url = s3_client.generate_presigned_url(
    'get_object',
    Params={'Bucket': bucket_name, 'Key': f"private/{private_file_name}"},
    ExpiresIn=60  # URL valid for 60 seconds
)

print(f"Private file signed URL: {signed_url}")