"""
Groq API Diagnostic Script
Tests if your Groq API key is working correctly

Save this as: test_groq_api.py
Run with: python test_groq_api.py
"""

import os
import sys

# Add your Django project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ZuntoProject.settings')
import django
django.setup()

from django.conf import settings
from groq import Groq

print("=" * 60)
print("🔍 GROQ API DIAGNOSTIC TEST")
print("=" * 60)

# Test 1: Check if API key exists in settings
print("\n1️⃣ Checking Django Settings...")
if hasattr(settings, 'GROQ_API_KEY'):
    api_key = settings.GROQ_API_KEY
    print(f"   ✅ GROQ_API_KEY found in settings")
    print(f"   📝 Key starts with: {api_key[:10]}...")
    print(f"   📏 Key length: {len(api_key)} characters")
    
    # Check for common issues
    if api_key.startswith(' ') or api_key.endswith(' '):
        print("   ⚠️  WARNING: API key has leading/trailing spaces!")
        api_key = api_key.strip()
        print("   🔧 Trimmed spaces automatically")
    
    if not api_key.startswith('gsk_'):
        print("   ⚠️  WARNING: Groq API keys usually start with 'gsk_'")
else:
    print("   ❌ GROQ_API_KEY NOT FOUND in settings!")
    print("   💡 Check your settings.py or .env file")
    sys.exit(1)

# Test 2: Check .env file directly
print("\n2️⃣ Checking .env file...")
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(env_path):
    print(f"   ✅ .env file exists at: {env_path}")
    with open(env_path, 'r') as f:
        env_content = f.read()
        if 'GROQ_API_KEY' in env_content:
            print("   ✅ GROQ_API_KEY found in .env")
            # Extract the key from .env
            for line in env_content.split('\n'):
                if line.startswith('GROQ_API_KEY'):
                    env_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                    print(f"   📝 .env key starts with: {env_key[:10]}...")
                    if env_key != api_key:
                        print("   ⚠️  WARNING: .env key differs from settings key!")
        else:
            print("   ⚠️  GROQ_API_KEY not found in .env")
else:
    print(f"   ⚠️  .env file not found at: {env_path}")

# Test 3: Test actual Groq API connection
print("\n3️⃣ Testing Groq API Connection...")
try:
    client = Groq(api_key=api_key)
    print("   ✅ Groq client initialized successfully")
    
    # Make a simple test request
    print("   🔄 Sending test request to Groq...")
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": "Say 'Hello' in exactly one word."
            }
        ],
        max_tokens=10,
        temperature=0.1
    )
    
    result = response.choices[0].message.content
    print(f"   ✅ API Response received: '{result}'")
    print("   🎉 GROQ API IS WORKING PERFECTLY!")
    
except Exception as e:
    print(f"   ❌ API Connection FAILED!")
    print(f"   📋 Error Type: {type(e).__name__}")
    print(f"   📋 Error Message: {str(e)}")
    
    # Check specific error types
    if "401" in str(e) or "Unauthorized" in str(e):
        print("\n   💡 DIAGNOSIS: API Key is Invalid or Expired")
        print("   🔧 SOLUTIONS:")
        print("      1. Go to https://console.groq.com/keys")
        print("      2. Generate a NEW API key")
        print("      3. Update both settings.py AND .env file")
        print("      4. Restart your Django server")
    elif "429" in str(e):
        print("\n   💡 DIAGNOSIS: Rate limit exceeded")
    elif "Connection" in str(e):
        print("\n   💡 DIAGNOSIS: Network/Internet issue")
    else:
        print("\n   💡 DIAGNOSIS: Unknown error - see message above")

# Test 4: Check where Groq is being used in your code
print("\n4️⃣ Checking Groq usage in your code...")
search_dirs = ['assistant']
groq_files = []

for search_dir in search_dirs:
    if os.path.exists(search_dir):
        for root, dirs, files in os.walk(search_dir):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if 'Groq(' in content or 'groq' in content.lower():
                                groq_files.append(filepath)
                    except:
                        pass

if groq_files:
    print(f"   📁 Found Groq usage in {len(groq_files)} files:")
    for file in groq_files[:5]:  # Show first 5
        print(f"      - {file}")
else:
    print("   ⚠️  No Groq usage found in code")

print("\n" + "=" * 60)
print("✅ DIAGNOSTIC COMPLETE")
print("=" * 60)
print("\n📋 SUMMARY:")
print("   1. Check the test results above")
print("   2. If API test failed, get a new key from Groq")
print("   3. Update BOTH settings.py and .env")
print("   4. Restart Django server")
print("\n" + "=" * 60)