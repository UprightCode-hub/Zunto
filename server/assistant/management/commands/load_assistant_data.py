from django.core.management.base import BaseCommand
from pathlib import Path
import json
import yaml


class Command(BaseCommand):
    help = 'Load assistant FAQ and rules data (validates files exist)'
    
    def handle(self, *args, **options):
        base_dir = Path(__file__).parent.parent.parent
        faq_path = base_dir / 'data' / 'faq.json'
        rules_path = base_dir / 'data' / 'rules.yaml'
        
        # Check FAQ file
        if not faq_path.exists():
            self.stdout.write(self.style.ERROR(f'FAQ file not found: {faq_path}'))
        else:
            try:
                with open(faq_path, 'r', encoding='utf-8') as f:
                    faq_data = json.load(f)
                    faq_count = len(faq_data.get('faqs', []))
                self.stdout.write(self.style.SUCCESS(f'✓ Loaded {faq_count} FAQs from {faq_path}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error loading FAQ: {e}'))
        
        # Check rules file
        if not rules_path.exists():
            self.stdout.write(self.style.ERROR(f'Rules file not found: {rules_path}'))
        else:
            try:
                with open(rules_path, 'r', encoding='utf-8') as f:
                    rules_data = yaml.safe_load(f)
                    rules_count = len(rules_data.get('rules', []))
                self.stdout.write(self.style.SUCCESS(f'✓ Loaded {rules_count} rules from {rules_path}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error loading rules: {e}'))
        
        self.stdout.write(self.style.SUCCESS('\nAssistant data validation complete!'))
        self.stdout.write('Note: Data is loaded from files at runtime. No database import needed.')
