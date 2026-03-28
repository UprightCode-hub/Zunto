from django.test import TestCase

from assistant.processors.query_processor import QueryProcessor


class RAGKnowledgeExpansionPhase6Tests(TestCase):
    def setUp(self):
        self.processor = QueryProcessor()

    def test_new_seller_onboarding_query_hits_new_faq(self):
        results = self.processor._search_faqs_multiple("How do I get started as a new seller on Zunto?")
        self.assertTrue(results)
        questions = [item.get('question', '').lower() for item in results]
        self.assertTrue(any('get started as a new seller' in q for q in questions))

    def test_new_platform_value_query_hits_new_faq(self):
        results = self.processor._search_faqs_multiple("What makes Zunto different from other marketplaces?")
        self.assertTrue(results)
        questions = [item.get('question', '').lower() for item in results]
        self.assertTrue(any('what makes zunto different' in q for q in questions))

    def test_existing_faq_query_still_works(self):
        results = self.processor._search_faqs_multiple("How do I track my order?")
        self.assertTrue(results)
        joined = ' '.join(
            f"{item.get('question', '')} {item.get('answer', '')}".lower()
            for item in results
        )
        self.assertIn('track', joined)
