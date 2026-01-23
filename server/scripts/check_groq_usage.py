import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ZuntoProject.settings')
django.setup()

from decouple import config
from django.conf import settings
from assistant.processors.local_model import LocalModelAdapter

print("="*50)
print("GROQ API KEY TESTS")
print("="*50)

# Test 1
key1 = os.environ.get('GROQ_API_KEY', 'NOT FOUND')
print(f"1. os.environ: {key1[:20]}..." if key1 != 'NOT FOUND' else "1. os.environ: NOT FOUND")

# Test 2
key2 = config('GROQ_API_KEY', default='NOT FOUND')
print(f"2. python-decouple: {key2[:20]}..." if key2 != 'NOT FOUND' else "2. python-decouple: NOT FOUND")

# Test 3
key3 = getattr(settings, 'GROQ_API_KEY', 'NOT FOUND')
print(f"3. Django settings: {key3[:20]}..." if key3 != 'NOT FOUND' else "3. Django settings: NOT FOUND")

# Test 4
adapter = LocalModelAdapter.get_instance()
print(f"\n4. LocalModelAdapter:")
print(f"   - Available: {adapter.is_available()}")
print(f"   - Initialized: {adapter.is_initialized}")
print(f"   - Client exists: {adapter.client is not None}")