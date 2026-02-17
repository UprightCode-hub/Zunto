#server/confirm_groq_api.py
"""
Improved GROQ API Diagnostic Test
Properly loads Django settings before testing
"""

import os
import sys
from pathlib import Path

                     
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

                          
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ZuntoProject.settings')
import django
django.setup()

                                                   
from django.conf import settings
from groq import Groq

def mask_key(key):
    """Mask API key for display"""
    if not key or len(key) < 10:
        return "***EMPTY***"
    return f"{key[:10]}...{key[-4:]}"

def test_groq_api():
    """Test Groq API connection"""
    print("=" * 60)
    print("🔍 IMPROVED GROQ API DIAGNOSTIC TEST")
    print("=" * 60)
    
                                   
    print("\n1️⃣ Checking Django Settings...")
    groq_key = getattr(settings, 'GROQ_API_KEY', '')
    
    if groq_key:
        print(f"   ✅ GROQ_API_KEY found in Django settings")
        print(f"   📝 Key: {mask_key(groq_key)}")
        print(f"   📏 Key length: {len(groq_key)} characters")
        
        if groq_key.startswith('gsk_'):
            print(f"   ✅ Key format looks correct (starts with 'gsk_')")
        else:
            print(f"   ⚠️  WARNING: Key doesn't start with 'gsk_'")
    else:
        print(f"   ❌ GROQ_API_KEY is empty or not found!")
        print(f"   💡 Check your .env file and python-decouple configuration")
        return False
    
                             
    print("\n2️⃣ Checking .env file...")
    env_path = project_root / '.env'
    
    if env_path.exists():
        print(f"   ✅ .env file exists at: {env_path}")
        
                             
        with open(env_path, 'r') as f:
            env_contents = f.read()
            if 'GROQ_API_KEY' in env_contents:
                print(f"   ✅ GROQ_API_KEY found in .env")
                
                                           
                for line in env_contents.split('\n'):
                    if line.startswith('GROQ_API_KEY='):
                        env_key = line.split('=', 1)[1].strip()
                        print(f"   📝 .env key: {mask_key(env_key)}")
                        
                        if env_key == groq_key:
                            print(f"   ✅ .env key MATCHES Django settings key")
                        else:
                            print(f"   ⚠️  WARNING: .env key DIFFERS from Django settings key!")
            else:
                print(f"   ❌ GROQ_API_KEY not found in .env")
    else:
        print(f"   ❌ .env file not found at: {env_path}")
    
                                 
    print("\n3️⃣ Testing Groq API Connection...")
    
    try:
        print(f"   🔄 Initializing Groq client...")
        client = Groq(api_key=groq_key)
        print(f"   ✅ Groq client initialized")
        
        print(f"   🔄 Sending test request to Groq...")
        
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": "Say 'API connection successful!' in exactly 5 words.",
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.5,
            max_tokens=50,
        )
        
        response = chat_completion.choices[0].message.content
        print(f"   ✅ API Connection SUCCESSFUL!")
        print(f"   📨 Response: {response}")
        return True
        
    except Exception as e:
        print(f"   ❌ API Connection FAILED!")
        print(f"   📋 Error Type: {type(e).__name__}")
        print(f"   📋 Error Message: {str(e)}")
        
        if "connection" in str(e).lower():
            print(f"   💡 DIAGNOSIS: Network/Internet connectivity issue")
            print(f"   💡 SUGGESTIONS:")
            print(f"      - Check your internet connection")
            print(f"      - Try a different network")
            print(f"      - Check if a firewall is blocking the request")
            print(f"      - Visit https://status.groq.com/ to check service status")
        elif "authentication" in str(e).lower() or "401" in str(e):
            print(f"   💡 DIAGNOSIS: Invalid API key")
            print(f"   💡 SUGGESTIONS:")
            print(f"      - Get a new key from https://console.groq.com/keys")
            print(f"      - Update your .env file")
        else:
            print(f"   💡 DIAGNOSIS: Unknown error")
            print(f"   💡 SUGGESTION: Check the full error message above")
        
        return False
    
    finally:
                                             
        print("\n4️⃣ Checking Environment Variables...")
        env_groq_key = os.environ.get('GROQ_API_KEY', '')
        
        if env_groq_key:
            print(f"   ✅ GROQ_API_KEY in environment variables")
            print(f"   📝 Env var: {mask_key(env_groq_key)}")
        else:
            print(f"   ⚠️  GROQ_API_KEY not in environment variables")
            print(f"   ℹ️  This is OK if using python-decouple")

if __name__ == "__main__":
    success = test_groq_api()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED - GROQ API IS WORKING!")
    else:
        print("❌ TESTS FAILED - SEE ERRORS ABOVE")
    print("=" * 60)
    
    print("\n📋 NEXT STEPS:")
    if success:
        print("   1. Your Groq API is configured correctly")
        print("   2. You can now use the assistant features")
        print("   3. Start your Django server: python manage.py runserver")
    else:
        print("   1. Review the error messages above")
        print("   2. Fix the identified issues")
        print("   3. Run this script again to verify")
    print("=" * 60)
