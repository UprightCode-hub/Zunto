#server/scripts/test_answer.py
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ZuntoProject.settings')
import django
django.setup()

from assistant.processors import QueryProcessor

                        
processor = QueryProcessor()
result = processor.process("How do I create an account?")

print("\n" + "="*60)
print("FULL ANSWER TEST")
print("="*60)
print(f"Query: How do I create an account?")
print(f"\nReply:\n{result['reply']}")
print(f"\nConfidence: {result['confidence']}")
print(f"Explanation: {result['explanation']}")
print(f"FAQ matched: {result['faq']['question'] if result['faq'] else 'None'}")
